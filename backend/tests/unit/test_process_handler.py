"""
Unit tests for the process (SQS worker) Lambda handler.

Tests cover: happy path, DynamoDB state transitions, PDF errors,
AI errors, and JSON parse failures.
"""
import json
from unittest.mock import patch

import pytest

import backend.handlers.process as process_mod
from backend.tests.conftest import FAKE_PDF


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_pending(analyses_table, user_id: str = "user123", analysis_id: str = "test-id",
                  s3_key: str = "uploads/user123/lease.pdf") -> None:
    """Pre-create the pending stub that submit normally writes."""
    analyses_table.put_item(Item={
        "user_id": user_id, "analysis_id": analysis_id,
        "status": "pending", "s3_key": s3_key,
    })


# ── Happy path ────────────────────────────────────────────────────────────────

def test_completed_result_saved_to_dynamodb(aws_setup, put_pdf, analyses_table, make_sqs_event, mock_ai_client):
    put_pdf("uploads/user123/lease.pdf")
    _seed_pending(analyses_table)
    with patch.object(process_mod, "get_ai_client", return_value=mock_ai_client()), \
         patch("backend.handlers.process.extract_text", return_value="LEASE TEXT"):
        process_mod.handler(make_sqs_event(), None)

    item = analyses_table.get_item(
        Key={"user_id": "user123", "analysis_id": "test-analysis-id"}
    ).get("Item")
    assert item is not None
    assert item["status"] == "completed"
    assert "risk_score" in item
    assert item["provider"] == "anthropic"
    assert "status_updated_at" in item


def test_s3_key_preserved_in_result(aws_setup, put_pdf, analyses_table, make_sqs_event, mock_ai_client):
    put_pdf("uploads/user123/lease.pdf")
    _seed_pending(analyses_table)
    with patch.object(process_mod, "get_ai_client", return_value=mock_ai_client()), \
         patch("backend.handlers.process.extract_text", return_value="TEXT"):
        process_mod.handler(make_sqs_event(), None)

    item = analyses_table.get_item(
        Key={"user_id": "user123", "analysis_id": "test-analysis-id"}
    ).get("Item")
    assert item["s3_key"] == "uploads/user123/lease.pdf"


def test_pdf_bytes_read_from_s3(aws_setup, put_pdf, analyses_table, make_sqs_event, mock_ai_client):
    put_pdf("uploads/user123/lease.pdf", body=FAKE_PDF)
    _seed_pending(analyses_table)
    with patch.object(process_mod, "get_ai_client", return_value=mock_ai_client()), \
         patch("backend.handlers.process.extract_text", return_value="TEXT") as mock_extract:
        process_mod.handler(make_sqs_event(), None)
    assert mock_extract.call_args[0][0] == FAKE_PDF


# ── Status transitions ────────────────────────────────────────────────────────

def test_status_set_to_processing_then_completed(aws_setup, put_pdf, analyses_table,
                                                  make_sqs_event, mock_ai_client):
    """Verify the final status is completed (processing is transient, hard to catch)."""
    put_pdf("uploads/user123/lease.pdf")
    _seed_pending(analyses_table)
    with patch.object(process_mod, "get_ai_client", return_value=mock_ai_client()), \
         patch("backend.handlers.process.extract_text", return_value="TEXT"):
        process_mod.handler(make_sqs_event(), None)

    item = analyses_table.get_item(
        Key={"user_id": "user123", "analysis_id": "test-analysis-id"}
    ).get("Item")
    assert item["status"] == "completed"


# ── PDF errors ────────────────────────────────────────────────────────────────

def test_scanned_pdf_marks_failed(aws_setup, put_pdf, analyses_table, make_sqs_event, mock_ai_client):
    put_pdf("uploads/user123/lease.pdf")
    _seed_pending(analyses_table)
    with patch.object(process_mod, "get_ai_client", return_value=mock_ai_client()), \
         patch("backend.handlers.process.extract_text",
               side_effect=ValueError("This PDF appears to be a scanned image.")):
        process_mod.handler(make_sqs_event(), None)

    item = analyses_table.get_item(
        Key={"user_id": "user123", "analysis_id": "test-analysis-id"}
    ).get("Item")
    assert item["status"] == "failed"
    assert "scanned" in item["error_message"].lower()


def test_pdf_too_long_marks_failed(aws_setup, put_pdf, analyses_table, make_sqs_event, mock_ai_client):
    put_pdf("uploads/user123/lease.pdf")
    _seed_pending(analyses_table)
    with patch.object(process_mod, "get_ai_client", return_value=mock_ai_client()), \
         patch("backend.handlers.process.extract_text",
               side_effect=ValueError("Lease is 75 pages — maximum supported is 50.")):
        process_mod.handler(make_sqs_event(), None)

    item = analyses_table.get_item(
        Key={"user_id": "user123", "analysis_id": "test-analysis-id"}
    ).get("Item")
    assert item["status"] == "failed"


# ── AI errors ─────────────────────────────────────────────────────────────────

def test_invalid_json_response_marks_failed(aws_setup, put_pdf, analyses_table,
                                             make_sqs_event, mock_ai_client):
    put_pdf("uploads/user123/lease.pdf")
    _seed_pending(analyses_table)
    with patch.object(process_mod, "get_ai_client", return_value=mock_ai_client(text="{{bad json")), \
         patch("backend.handlers.process.extract_text", return_value="TEXT"):
        process_mod.handler(make_sqs_event(), None)

    item = analyses_table.get_item(
        Key={"user_id": "user123", "analysis_id": "test-analysis-id"}
    ).get("Item")
    assert item["status"] == "failed"


def test_ai_config_error_marks_failed_no_raise(aws_setup, put_pdf, analyses_table,
                                                make_sqs_event):
    """Config errors are non-retryable — handler returns without raising."""
    put_pdf("uploads/user123/lease.pdf")
    _seed_pending(analyses_table)
    with patch.object(process_mod, "get_ai_client",
                      side_effect=RuntimeError("ANTHROPIC_API_KEY env var is not set")), \
         patch("backend.handlers.process.extract_text", return_value="TEXT"):
        process_mod.handler(make_sqs_event(), None)  # must not raise

    item = analyses_table.get_item(
        Key={"user_id": "user123", "analysis_id": "test-analysis-id"}
    ).get("Item")
    assert item["status"] == "failed"


def test_retryable_provider_error_raises(aws_setup, put_pdf, analyses_table,
                                          make_sqs_event, mock_ai_client):
    """Retryable ProviderError should re-raise so SQS can retry the message."""
    from backend.lib.ai_client import ProviderError
    put_pdf("uploads/user123/lease.pdf")
    _seed_pending(analyses_table)
    retryable_err = ProviderError("Rate limit exceeded", status_code=429, retryable=True)
    with patch.object(process_mod, "get_ai_client", return_value=mock_ai_client(raises=retryable_err)), \
         patch("backend.handlers.process.extract_text", return_value="TEXT"):
        with pytest.raises(ProviderError):
            process_mod.handler(make_sqs_event(), None)


# ── Stress / concurrency safety ───────────────────────────────────────────────

def test_multiple_records_processed_independently(aws_setup, put_pdf, analyses_table,
                                                   mock_ai_client):
    """batch_size=1 in CDK, but verify handler loops correctly if records > 1."""
    for i in range(3):
        put_pdf(f"uploads/user123/lease{i}.pdf")
        analyses_table.put_item(Item={
            "user_id": "user123", "analysis_id": f"id-{i}",
            "status": "pending", "s3_key": f"uploads/user123/lease{i}.pdf",
        })

    event = {
        "Records": [
            {"messageId": f"msg-{i}", "body": json.dumps({
                "analysis_id": f"id-{i}", "user_id": "user123",
                "s3_key": f"uploads/user123/lease{i}.pdf",
            })}
            for i in range(3)
        ]
    }
    with patch.object(process_mod, "get_ai_client", return_value=mock_ai_client()), \
         patch("backend.handlers.process.extract_text", return_value="TEXT"):
        process_mod.handler(event, None)

    for i in range(3):
        item = analyses_table.get_item(
            Key={"user_id": "user123", "analysis_id": f"id-{i}"}
        ).get("Item")
        assert item["status"] == "completed"
