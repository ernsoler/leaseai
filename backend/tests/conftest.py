"""
Shared pytest fixtures for LeaseAI backend tests.

This file is auto-discovered by pytest for every test under backend/tests/.
It does two things at module level (before any test imports):
  1. Sets the env vars that handler modules read at import time.
  2. Exposes reusable fixtures for moto S3/DynamoDB, fake users,
     and AI client mocks.

Structure:
  conftest.py          ← you are here
  unit/                ← single-handler tests
  integration/         ← multi-handler pipeline tests
"""
import os
import json

# ── Set env vars before handler modules are imported ─────────────────────────
# Handler modules read these at module level (e.g. BUCKET_NAME = os.environ[...])
# conftest.py is collected before test modules, so this runs first.
os.environ.setdefault("BUCKET_NAME",          "test-leaseai-bucket")
os.environ.setdefault("ANALYSES_TABLE",       "leaseai-analyses-test")
os.environ.setdefault("USER_ID",              "demo")
os.environ.setdefault("ANALYSES_QUEUE_URL",   "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue")
os.environ.setdefault("AWS_DEFAULT_REGION",    "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID",     "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("ANTHROPIC_API_KEY",     "test-key")

# Prompt env vars — injected directly so tests never hit S3
os.environ.setdefault("SYSTEM_PROMPT",         "You are a lease analyst. Return valid JSON only.")
os.environ.setdefault("USER_PROMPT_TEMPLATE",  "Analyze this lease:\n<<<LEASE_TEXT>>>")

# ─────────────────────────────────────────────────────────────────────────────

import pytest
import boto3
from moto import mock_aws
from unittest.mock import MagicMock

from backend.lib.ai_client import AIResponse

# ── Constants ─────────────────────────────────────────────────────────────────
BUCKET_NAME    = os.environ["BUCKET_NAME"]
ANALYSES_TABLE = os.environ["ANALYSES_TABLE"]
REGION         = os.environ["AWS_DEFAULT_REGION"]
FAKE_PDF       = b"%PDF-1.4 fake pdf content for testing"
# Canonical test S3 key matching the presign format: uploads/{YYYYMMDD-HHMMSS}/{uuid}.pdf
TEST_S3_KEY    = "uploads/20250101-120000/00000000-0000-0000-0000-000000000001.pdf"

# ── Minimal valid analysis payload (used across many tests) ───────────────────
SAMPLE_ANALYSIS = {
    "summary": {
        "property_address": "123 Main St, Austin, TX 78701",
        "landlord_name":    "John Smith Properties LLC",
        "tenant_name":      "Jane Doe",
        "lease_start":      "2025-02-01",
        "lease_end":        "2026-01-31",
        "monthly_rent":     2200.0,
        "security_deposit": 4400.0,
        "lease_type":       "fixed",
    },
    "clauses": [
        {
            "id":               "clause_001",
            "category":         "termination",
            "title":            "Early Termination Penalty",
            "original_text":    "Tenant shall be liable for all remaining rent.",
            "risk_level":       "high",
            "risk_explanation": "Double penalty clause.",
            "recommendation":   "Remove the termination fee.",
            "section_reference": "Section 10",
        }
    ],
    "key_dates": [
        {"event": "Lease start", "date": "2025-02-01", "notice_required": None}
    ],
    "financial_summary": {
        "total_monthly_cost": 2200.0,
        "total_move_in_cost": 6600.0,
        "annual_cost":        26400.0,
        "penalties": [],
    },
    "risk_score": {
        "overall": 45,
        "breakdown": {
            "financial_risk":   55,
            "termination_risk": 25,
            "maintenance_risk": 60,
            "legal_risk":       40,
        },
    },
    "missing_clauses": ["Renter's insurance clause"],
    "red_flags":       ["Landlord entry without notice — potentially illegal."],
}


# ── Cache hygiene ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_prompt_cache():
    """Clear the prompt cache before every test to prevent cross-test leakage."""
    from backend.lib.prompt_store import _read_bundled
    _read_bundled.cache_clear()
    yield
    _read_bundled.cache_clear()


# ── Core AWS fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def aws_setup():
    """
    Start moto, create S3 bucket + DynamoDB tables, re-wire module-level
    boto3 clients in every handler to point at the in-memory fakes.

    Yields a dict with live boto3 clients/resources for assertions:
        {
            "s3":              boto3 S3 client,
            "dynamo":          boto3 DynamoDB resource,
            "analyses_table":  DynamoDB Table object,
            "users_table":     DynamoDB Table object,
        }
    """
    with mock_aws():
        s3     = boto3.client("s3",       region_name=REGION)
        dynamo = boto3.resource("dynamodb", region_name=REGION)

        # S3 bucket
        s3.create_bucket(Bucket=BUCKET_NAME)

        # leaseai-analyses-test
        dynamo.create_table(
            TableName=ANALYSES_TABLE,
            KeySchema=[
                {"AttributeName": "user_id",     "KeyType": "HASH"},
                {"AttributeName": "analysis_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id",     "AttributeType": "S"},
                {"AttributeName": "analysis_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Upload placeholder prompts so S3-backed prompt_store works if needed
        s3.put_object(
            Bucket=BUCKET_NAME, Key="prompts/system.txt",
            Body=os.environ["SYSTEM_PROMPT"].encode(),
        )
        s3.put_object(
            Bucket=BUCKET_NAME, Key="prompts/user_template.txt",
            Body=os.environ["USER_PROMPT_TEMPLATE"].encode(),
        )

        # SQS queue
        sqs = boto3.client("sqs", region_name=REGION)
        queue = sqs.create_queue(QueueName="test-queue")
        queue_url = queue["QueueUrl"]
        os.environ["ANALYSES_QUEUE_URL"] = queue_url

        # Re-wire module-level clients so handlers use the moto fakes
        import backend.handlers.process     as process_mod
        import backend.handlers.get_results as get_results_mod
        import backend.handlers.presign     as presign_mod
        import backend.handlers.submit      as submit_mod

        fresh_s3  = boto3.client("s3",  region_name=REGION)
        fresh_sqs = boto3.client("sqs", region_name=REGION)

        process_mod.s3_client      = fresh_s3
        process_mod.dynamodb       = dynamo
        get_results_mod.dynamodb   = dynamo
        presign_mod.s3_client      = fresh_s3
        submit_mod.dynamodb        = dynamo
        submit_mod.sqs_client      = fresh_sqs

        yield {
            "s3":             s3,
            "sqs":            sqs,
            "queue_url":      queue_url,
            "dynamo":         dynamo,
            "analyses_table": dynamo.Table(ANALYSES_TABLE),
        }


# ── Helper fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def put_pdf(aws_setup):
    """
    Returns a callable that uploads a fake PDF to moto S3.
    Usage: put_pdf("uploads/user123/abc.pdf")
    """
    def _put(key: str, body: bytes = FAKE_PDF) -> str:
        aws_setup["s3"].put_object(Bucket=BUCKET_NAME, Key=key, Body=body)
        return key
    return _put


@pytest.fixture
def analyses_table(aws_setup):
    """Direct access to the moto analyses DynamoDB table."""
    return aws_setup["analyses_table"]


@pytest.fixture
def mock_ai_client():
    """
    Returns a factory that produces a MagicMock AIClient.
    Usage:
        client = mock_ai_client()                         # valid JSON response
        client = mock_ai_client(text="bad json")          # force parse error
        client = mock_ai_client(raises=Exception("oops")) # force exception
    """
    def _factory(
        text: str | None = None,
        raises: Exception | None = None,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-6",
    ) -> MagicMock:
        client = MagicMock()
        client.PROVIDER = provider
        client.model    = model
        if raises:
            client.complete.side_effect = raises
        else:
            client.complete.return_value = AIResponse(
                text=text if text is not None else json.dumps(SAMPLE_ANALYSIS),
                input_tokens=1000,
                output_tokens=500,
                model=model,
                provider=provider,
            )
        return client
    return _factory


@pytest.fixture
def make_sqs_event():
    """Returns a callable that builds a fake SQS Lambda event (one record)."""
    def _make(
        analysis_id: str = "test-analysis-id",
        user_id: str = "user123",
        s3_key: str = "uploads/user123/lease.pdf",
        message_id: str = "msg-001",
    ) -> dict:
        return {
            "Records": [{
                "messageId": message_id,
                "body": json.dumps({
                    "analysis_id": analysis_id,
                    "user_id":     user_id,
                    "s3_key":      s3_key,
                }),
            }]
        }
    return _make
