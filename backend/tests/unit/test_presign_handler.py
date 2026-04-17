"""
Unit tests for the presign Lambda handler.

Uses moto S3 — verifies key format, content-type validation, and URL structure.
"""
import json

import backend.handlers.presign as presign_mod
from backend.tests.conftest import BUCKET_NAME


def _call(aws_setup, body: dict) -> dict:
    return presign_mod.handler(
        {"body": json.dumps(body), "headers": {}, "pathParameters": None,
         "requestContext": {"identity": {"sourceIp": "127.0.0.1"}}},
        None,
    )


# ── Happy path ────────────────────────────────────────────────────────────────

def test_returns_200_with_upload_url_and_s3_key(aws_setup):
    result = _call(aws_setup, {"filename": "lease.pdf", "content_type": "application/pdf"})
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "upload_url" in body
    assert "s3_key" in body


def test_s3_key_has_anon_prefix(aws_setup):
    result = _call(aws_setup, {"filename": "lease.pdf", "content_type": "application/pdf"})
    s3_key = json.loads(result["body"])["s3_key"]
    assert s3_key.startswith("uploads/")


def test_s3_key_ends_with_pdf_extension(aws_setup):
    result = _call(aws_setup, {"filename": "my_lease.pdf", "content_type": "application/pdf"})
    s3_key = json.loads(result["body"])["s3_key"]
    assert s3_key.endswith(".pdf")


def test_each_call_generates_unique_s3_key(aws_setup):
    r1 = json.loads(_call(aws_setup, {"filename": "a.pdf", "content_type": "application/pdf"})["body"])
    r2 = json.loads(_call(aws_setup, {"filename": "b.pdf", "content_type": "application/pdf"})["body"])
    assert r1["s3_key"] != r2["s3_key"]


def test_upload_url_references_correct_bucket(aws_setup):
    result = _call(aws_setup, {"filename": "lease.pdf", "content_type": "application/pdf"})
    upload_url = json.loads(result["body"])["upload_url"]
    assert BUCKET_NAME in upload_url


# ── Input validation ──────────────────────────────────────────────────────────

def test_non_pdf_content_type_returns_400(aws_setup):
    result = _call(aws_setup, {"filename": "lease.docx", "content_type": "application/msword"})
    assert result["statusCode"] == 400
    assert "pdf" in json.loads(result["body"])["error"].lower()


def test_empty_body_defaults_to_pdf(aws_setup):
    result = _call(aws_setup, {})
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["s3_key"].endswith(".pdf")
