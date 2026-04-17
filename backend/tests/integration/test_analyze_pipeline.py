"""
Integration tests for the full LeaseAI backend pipeline.

Architecture under test (async):
  1. submit      — writes pending stub + enqueues SQS → 200 {analysis_id, user_id}
  2. process     — SQS worker runs the full pipeline → status: completed/failed
  3. get_results — polls DynamoDB by analysis_id + user_id

Only the AI client and PDF parser are mocked (external APIs).
All AWS services use moto (S3, DynamoDB, SQS).

Scenarios covered:
  1. Full pipeline round-trip — submit → process → get_results
  2. Multiple analyses
  3. Wrong user_id returns 404
  4. presign → upload → submit → process flow
  5. Failed analysis (bad AI JSON) stored with status=failed
  6. get_results on unknown/pending ID
"""
import json
from unittest.mock import patch, MagicMock

import backend.handlers.submit      as submit_mod
import backend.handlers.process     as process_mod
import backend.handlers.get_results as get_results_mod
import backend.handlers.presign     as presign_mod

from backend.lib.ai_client import AIResponse
from backend.tests.conftest import BUCKET_NAME, FAKE_PDF, SAMPLE_ANALYSIS, TEST_S3_KEY

USER_ID = "demo"  # matches os.environ["USER_ID"] set in conftest


# ── Pipeline helpers ──────────────────────────────────────────────────────────

def _submit(s3_key: str = TEST_S3_KEY) -> dict:
    return submit_mod.handler(
        {"body": json.dumps({"s3_key": s3_key}), "headers": {}, "pathParameters": None},
        None,
    )


def _process(analysis_id: str, s3_key: str = TEST_S3_KEY,
             ai_text: str | None = None, ai_raises: Exception | None = None) -> None:
    ai = MagicMock()
    ai.PROVIDER = "anthropic"
    ai.model = "claude-haiku-4-5-20251001"
    if ai_raises:
        ai.complete.side_effect = ai_raises
    else:
        ai.complete.return_value = AIResponse(
            text=ai_text if ai_text is not None else json.dumps(SAMPLE_ANALYSIS),
            input_tokens=500, output_tokens=200,
            model="claude-haiku-4-5-20251001", provider="anthropic",
        )
    sqs_event = {
        "Records": [{
            "messageId": "test-msg",
            "body": json.dumps({
                "analysis_id": analysis_id,
                "user_id":     USER_ID,
                "s3_key":      s3_key,
            }),
        }]
    }
    with patch.object(process_mod, "get_ai_client", return_value=ai), \
         patch("backend.handlers.process.extract_text", return_value="LEASE TEXT"):
        process_mod.handler(sqs_event, None)


def _get_results(analysis_id: str, user_id: str = USER_ID) -> dict:
    return get_results_mod.handler(
        {"body": "{}", "headers": {}, "pathParameters": {"id": analysis_id},
         "queryStringParameters": {"user_id": user_id}},
        None,
    )


def _presign() -> dict:
    return presign_mod.handler(
        {"body": json.dumps({"content_type": "application/pdf"}),
         "headers": {}, "pathParameters": None,
         "requestContext": {"identity": {"sourceIp": "127.0.0.1"}}},
        None,
    )


def _run(s3_key: str = TEST_S3_KEY, ai_text: str | None = None) -> tuple[str, dict]:
    """submit + process + return (analysis_id, get_results body)."""
    submit_result = _submit(s3_key)
    assert submit_result["statusCode"] == 200, submit_result["body"]
    resp = json.loads(submit_result["body"])
    assert resp["user_id"] == USER_ID
    analysis_id = resp["analysis_id"]
    _process(analysis_id, s3_key=s3_key, ai_text=ai_text)
    body = json.loads(_get_results(analysis_id)["body"])
    return analysis_id, body


# ── 1. Full pipeline round-trip ───────────────────────────────────────────────

def test_analyze_result_retrievable_via_get_results(aws_setup, put_pdf):
    put_pdf(TEST_S3_KEY)
    analysis_id, body = _run()

    assert body["analysis_id"] == analysis_id
    assert body["status"] == "completed"
    assert body["risk_score"]["overall"] == SAMPLE_ANALYSIS["risk_score"]["overall"]


def test_get_results_returns_full_analysis_structure(aws_setup, put_pdf):
    put_pdf(TEST_S3_KEY)
    _, body = _run()

    for field in ("summary", "clauses", "key_dates", "financial_summary",
                  "risk_score", "missing_clauses", "red_flags"):
        assert field in body, f"Missing field: {field}"


def test_data_integrity_between_submit_and_get_results(aws_setup, put_pdf):
    put_pdf(TEST_S3_KEY)
    _, body = _run()

    assert body["risk_score"]      == SAMPLE_ANALYSIS["risk_score"]
    assert body["red_flags"]       == SAMPLE_ANALYSIS["red_flags"]
    assert body["missing_clauses"] == SAMPLE_ANALYSIS["missing_clauses"]


def test_submit_returns_200_with_ids(aws_setup, put_pdf):
    put_pdf(TEST_S3_KEY)
    result = _submit()
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "analysis_id" in body
    assert body["user_id"] == USER_ID


def test_pending_status_before_process_runs(aws_setup, put_pdf, analyses_table):
    put_pdf(TEST_S3_KEY)
    analysis_id = json.loads(_submit()["body"])["analysis_id"]

    item = analyses_table.get_item(
        Key={"user_id": USER_ID, "analysis_id": analysis_id}
    ).get("Item")
    assert item is not None
    assert item["status"] == "pending"


# ── 2. Multiple analyses ──────────────────────────────────────────────────────

def test_two_analyses_have_distinct_ids(aws_setup, put_pdf):
    key1 = "uploads/20250101-120000/00000000-0000-0000-0000-000000000011.pdf"
    key2 = "uploads/20250101-120001/00000000-0000-0000-0000-000000000022.pdf"
    put_pdf(key1)
    put_pdf(key2)

    id1, _ = _run(key1)
    id2, _ = _run(key2)

    assert id1 != id2
    assert json.loads(_get_results(id1)["body"])["analysis_id"] == id1
    assert json.loads(_get_results(id2)["body"])["analysis_id"] == id2


def test_second_analysis_does_not_overwrite_first(aws_setup, put_pdf, analyses_table):
    key1 = "uploads/20250101-120000/00000000-0000-0000-0000-000000000011.pdf"
    key2 = "uploads/20250101-120001/00000000-0000-0000-0000-000000000022.pdf"
    put_pdf(key1)
    put_pdf(key2)

    id1, _ = _run(key1)
    id2, _ = _run(key2)

    item1 = analyses_table.get_item(Key={"user_id": USER_ID, "analysis_id": id1}).get("Item")
    item2 = analyses_table.get_item(Key={"user_id": USER_ID, "analysis_id": id2}).get("Item")
    assert item1 is not None and item2 is not None
    assert item1["s3_key"] != item2["s3_key"]


# ── 3. Wrong user_id returns 404 ──────────────────────────────────────────────

def test_wrong_user_id_returns_404(aws_setup, put_pdf):
    put_pdf(TEST_S3_KEY)
    analysis_id, _ = _run()

    result = _get_results(analysis_id, user_id="not-demo")
    assert result["statusCode"] == 404


# ── 4. Presign → upload → submit → process flow ───────────────────────────────

def test_presign_key_works_in_submit_and_process(aws_setup):
    s3_key = json.loads(_presign()["body"])["s3_key"]
    aws_setup["s3"].put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=FAKE_PDF)

    submit_result = _submit(s3_key)
    assert submit_result["statusCode"] == 200
    analysis_id = json.loads(submit_result["body"])["analysis_id"]

    _process(analysis_id, s3_key=s3_key)
    result = _get_results(analysis_id)
    assert result["statusCode"] == 200
    assert json.loads(result["body"])["status"] == "completed"


def test_presign_key_format(aws_setup):
    s3_key = json.loads(_presign()["body"])["s3_key"]
    # uploads/{YYYYMMDD-HHMMSS}/{uuid}.pdf
    assert s3_key.startswith("uploads/")
    assert s3_key.endswith(".pdf")
    parts = s3_key.split("/")
    assert len(parts) == 3
    assert len(parts[1]) == 15   # YYYYMMDD-HHMMSS
    assert len(parts[2]) == 40   # uuid.pdf (36 + 4)


def test_each_presign_call_generates_unique_key(aws_setup):
    key1 = json.loads(_presign()["body"])["s3_key"]
    key2 = json.loads(_presign()["body"])["s3_key"]
    assert key1 != key2


# ── 5. Failed analysis — bad AI JSON ─────────────────────────────────────────

def test_bad_ai_json_stores_failed_status(aws_setup, put_pdf, analyses_table):
    put_pdf(TEST_S3_KEY)
    analysis_id = json.loads(_submit()["body"])["analysis_id"]
    _process(analysis_id, ai_text="{{not valid json")

    item = analyses_table.get_item(
        Key={"user_id": USER_ID, "analysis_id": analysis_id}
    ).get("Item")
    assert item["status"] == "failed"
    assert "error_message" in item


def test_failed_item_retrievable_via_get_results(aws_setup, put_pdf):
    put_pdf(TEST_S3_KEY)
    analysis_id = json.loads(_submit()["body"])["analysis_id"]
    _process(analysis_id, ai_text="{{not valid json")

    result = _get_results(analysis_id)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "failed"
    assert "risk_score" not in body


# ── 6. get_results edge cases ─────────────────────────────────────────────────

def test_get_results_404_for_unknown_id(aws_setup):
    assert _get_results("completely-made-up-id")["statusCode"] == 404


def test_get_results_pending_before_processing(aws_setup, put_pdf):
    put_pdf(TEST_S3_KEY)
    analysis_id = json.loads(_submit()["body"])["analysis_id"]

    result = _get_results(analysis_id)
    assert result["statusCode"] == 200
    assert json.loads(result["body"])["status"] == "pending"
