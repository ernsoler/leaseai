"""
Lambda: process
SQS-triggered heavy worker — downloads the PDF, extracts text, calls the AI
provider, validates the result, and writes the final item to DynamoDB.

Triggered by the SQS analyze-jobs queue (batch_size=1).
No HTTP response — returns None on success; raises on unrecoverable error so
SQS will route the message to the DLQ after max_receive_count exhausted.
"""
import os
import json
import time
import logging
import decimal
import backoff
import boto3
from datetime import datetime, timezone

from backend.lib.pdf_parser import extract_text
from backend.lib.model_router import get_model_config
from backend.lib.ai_client import get_ai_client, AIResponse, estimate_cost, ProviderError
from backend.lib.prompt_store import get_system_prompt
from backend.lib.schema import LeaseAnalysis
from backend.prompts.lease_analysis import build_analysis_prompt
from backend.lib.constants import AnalysisStatus

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

BUCKET_NAME = os.environ["BUCKET_NAME"]
ANALYSES_TABLE = os.environ["ANALYSES_TABLE"]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _strip_markdown_json(text: str) -> str:
    """Strip markdown code fences that some models wrap around JSON output.

    Handles:  ```json\\n{...}\\n```  and  ```\\n{...}\\n```
    Returns the raw text unchanged if no fences are detected.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        # Drop the opening fence line (```json or ```)
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1:]
        # Drop the closing fence
        if stripped.endswith("```"):
            stripped = stripped[: stripped.rfind("```")]
    return stripped.strip()


def _on_json_backoff(details: dict) -> None:
    logger.warning(
        "AI provider returned invalid JSON, retrying... "
        "provider=%s model=%s attempt=%d",
        details["args"][0].PROVIDER, details["args"][0].model, details["tries"],
    )


def _on_provider_backoff(details: dict) -> None:
    logger.warning(
        "Retryable provider error, backing off... "
        "provider=%s model=%s attempt=%d wait=%.1fs",
        details["args"][0].PROVIDER, details["args"][0].model,
        details["tries"], details["wait"],
    )


def _giveup_non_retryable(exc: ProviderError) -> bool:
    """Tell backoff to stop retrying non-retryable provider errors immediately."""
    return not exc.retryable


@backoff.on_exception(
    backoff.expo,
    ProviderError,
    max_tries=6,       # up to ~5 min of retries within the 900s Lambda timeout
    max_value=120,     # cap individual waits at 2 min; overload can last minutes
    jitter=backoff.full_jitter,
    giveup=_giveup_non_retryable,
    on_backoff=_on_provider_backoff,
)
@backoff.on_exception(
    backoff.constant,
    json.JSONDecodeError,
    max_tries=1,
    interval=0,
    on_backoff=_on_json_backoff,
)
def _call_ai(client, prompt: str) -> AIResponse:
    """Call the AI client and return a validated AIResponse (text must be valid JSON).

    Retryable ProviderErrors (overloaded, rate-limit, timeout) are retried up to
    3 times with exponential backoff + jitter before propagating to the caller.
    Non-retryable errors and JSONDecodeError are raised immediately.
    """
    ai_response = client.complete(
        system=get_system_prompt(), user=prompt, max_tokens=8192)
    if not ai_response.text.strip():
        # Defence-in-depth: complete() should raise ProviderError for empty text,
        # but if the SDK returns empty content without raising (e.g. an error event
        # delivered in the stream body that the SDK absorbs into an empty message),
        # catch it here and retry as a transient failure.
        logger.warning(
            "Empty response from AI provider=%s model=%s — treating as retryable",
            client.PROVIDER, client.model,
        )
        raise ProviderError(
            "Analysis service unavailable. Please try again.", status_code=503, retryable=True)
    cleaned = _strip_markdown_json(ai_response.text)
    if cleaned != ai_response.text.strip():
        logger.warning(
            "Stripped markdown code fences from AI response provider=%s model=%s",
            client.PROVIDER, client.model,
        )
        ai_response = AIResponse(
            text=cleaned,
            input_tokens=ai_response.input_tokens,
            output_tokens=ai_response.output_tokens,
            model=ai_response.model,
            provider=ai_response.provider,
        )
    # validate; raises JSONDecodeError if not valid JSON
    json.loads(ai_response.text)
    return ai_response


def _log_cost(
    analysis_id: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    estimated = estimate_cost(model, input_tokens, output_tokens)
    logger.info(
        "COST_LOG analysis_id=%s provider=%s model=%s "
        "input_tokens=%d output_tokens=%d estimated_cost_usd=%.6f",
        analysis_id, provider, model, input_tokens, output_tokens, estimated,
    )


def _set_status(table, user_id: str, analysis_id: str, status: str, **extra_attrs) -> None:
    """Update only the status (and any extra attributes) on an existing DynamoDB item.

    Always stamps status_updated_at so stuck jobs are detectable.
    """
    now = datetime.now(timezone.utc).isoformat()
    update_expr_parts = ["#st = :status", "status_updated_at = :updated_at"]
    expr_attr_names = {"#st": "status"}
    expr_attr_values: dict = {":status": status, ":updated_at": now}

    for key, value in extra_attrs.items():
        placeholder = f":{key}"
        update_expr_parts.append(f"{key} = {placeholder}")
        expr_attr_values[placeholder] = value

    table.update_item(
        Key={"user_id": user_id, "analysis_id": analysis_id},
        UpdateExpression="SET " + ", ".join(update_expr_parts),
        ExpressionAttributeNames=expr_attr_names,
        ExpressionAttributeValues=expr_attr_values,
    )


# ── Core processing logic ─────────────────────────────────────────────────────

def _process_message(msg: dict) -> None:
    """Process a single SQS message payload."""
    analysis_id = msg["analysis_id"]
    user_id = msg["user_id"]
    s3_key = msg["s3_key"]
    created_at = msg.get("created_at") or datetime.now(
        timezone.utc).isoformat()

    table = dynamodb.Table(ANALYSES_TABLE)
    _set_status(table, user_id, analysis_id, AnalysisStatus.PROCESSING)
    logger.info("Processing analysis_id=%s user_id=%s s3_key=%s",
                analysis_id, user_id, s3_key)

    model_config = get_model_config()
    provider = model_config.provider
    model = model_config.model_id
    try:
        ai_client = get_ai_client(provider=provider, model=model)
    except (ImportError, RuntimeError, ValueError) as e:
        logger.error(
            "Failed to initialise AI client analysis_id=%s: %s", analysis_id, e)
        _set_status(table, user_id, analysis_id, AnalysisStatus.FAILED,
                    error_message="Service configuration error. Please contact support.")
        return

    logger.info("Downloading s3://%s/%s", BUCKET_NAME, s3_key)
    s3_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    pdf_bytes = s3_obj["Body"].read()

    parse_start = time.time()
    try:
        lease_text = extract_text(pdf_bytes)
    except ValueError as e:
        logger.error("PDF extraction failed analysis_id=%s: %s",
                     analysis_id, e)
        _set_status(table, user_id, analysis_id,
                    AnalysisStatus.FAILED, error_message=str(e))
        return  # non-retryable — bad PDF content
    parse_duration = time.time() - parse_start
    logger.info("PDF parsing took %.2fs, extracted %d chars",
                parse_duration, len(lease_text))

    prompt = build_analysis_prompt(lease_text)
    ai_start = time.time()
    try:
        ai_response = _call_ai(ai_client, prompt)
        raw_analysis = json.loads(ai_response.text)
    except json.JSONDecodeError:
        logger.error(
            "AI returned invalid JSON provider=%s model=%s analysis_id=%s",
            provider, model, analysis_id,
        )
        _set_status(
            table, user_id, analysis_id, AnalysisStatus.FAILED,
            error_message="Analysis could not be completed. Please try again.",
        )
        return
    except ProviderError as e:
        logger.error(
            "AI provider error provider=%s model=%s analysis_id=%s error=%s",
            provider, model, analysis_id, e,
        )
        if e.retryable:
            # Raise so SQS visibility timeout expires and the message is retried
            raise
        _set_status(table, user_id, analysis_id,
                    AnalysisStatus.FAILED, error_message=e.public_message)
        return
    except Exception as e:
        logger.error(
            "AI provider unexpected error provider=%s model=%s analysis_id=%s error=%s",
            provider, model, analysis_id, e,
        )
        # Treat unknown errors as retryable — raise to let SQS retry
        raise

    ai_duration = time.time() - ai_start
    logger.info(
        "AI call took %.2fs provider=%s model=%s "
        "input_tokens=%d output_tokens=%d analysis_id=%s",
        ai_duration, provider, model,
        ai_response.input_tokens, ai_response.output_tokens, analysis_id,
    )
    _log_cost(analysis_id, provider, model,
              ai_response.input_tokens, ai_response.output_tokens)

    try:
        validated = LeaseAnalysis.model_validate(raw_analysis)
        result_payload = validated.model_dump()
    except Exception as e:
        logger.warning(
            "Pydantic validation failed analysis_id=%s: %s", analysis_id, e)
        result_payload = raw_analysis
        result_payload["_validation_warning"] = str(e)

    result_payload["analysis_id"] = analysis_id

    dynamo_item = json.loads(
        json.dumps({
            "user_id":           user_id,
            "analysis_id":       analysis_id,
            "status":            AnalysisStatus.COMPLETED,
            "status_updated_at": datetime.now(timezone.utc).isoformat(),
            "created_at":        created_at,
            "s3_key":            s3_key,
            "provider":          provider,
            "model":             model,
            **result_payload,
        }, default=str),
        parse_float=decimal.Decimal,
    )
    table.put_item(Item=dynamo_item)

    logger.info("Saved completed analysis_id=%s user_id=%s",
                analysis_id, user_id)


# ── Lambda entry point ────────────────────────────────────────────────────────

def handler(event: dict, context) -> None:
    """SQS-triggered handler. Processes each record independently.

    On unrecoverable errors per-record: marks DynamoDB as failed and continues.
    On retryable errors: raises so SQS retries the batch (batch_size=1, so safe).
    """
    for record in event.get("Records", []):
        msg = json.loads(record["body"])
        logger.info(
            "Received SQS record analysis_id=%s messageId=%s",
            msg.get("analysis_id"), record.get("messageId"),
        )
        _process_message(msg)
