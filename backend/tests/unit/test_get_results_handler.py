"""
Unit tests for the get-results Lambda handler.

Seeds DynamoDB via moto and verifies retrieval, 404, and ownership isolation.
"""
import json
from datetime import datetime, timezone

import backend.handlers.get_results as get_results_mod


def _call(analysis_id: str, user_id: str = "user123") -> dict:
    return get_results_mod.handler(
        {"body": "{}", "headers": {}, "pathParameters": {"id": analysis_id},
         "queryStringParameters": {"user_id": user_id}},
        None,
    )


def _seed(analyses_table, user_id: str = "user123", analysis_id: str = "analysis-abc") -> dict:
    item = {
        "user_id":     user_id,
        "analysis_id": analysis_id,
        "created_at":  datetime.now(timezone.utc).isoformat(),
        "risk_score":  {"overall": 72, "breakdown": {}},
        "red_flags":   ["Some issue"],
    }
    analyses_table.put_item(Item=item)
    return item


# ── Happy path ────────────────────────────────────────────────────────────────

def test_returns_200_with_stored_item(aws_setup, analyses_table):
    _seed(analyses_table, analysis_id="ana-001")
    result = _call("ana-001")
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["analysis_id"] == "ana-001"
    assert body["risk_score"]["overall"] == 72


def test_returns_all_stored_fields(aws_setup, analyses_table):
    _seed(analyses_table, analysis_id="ana-full")
    result = _call("ana-full")
    body = json.loads(result["body"])
    assert "created_at" in body
    assert "red_flags" in body


# ── Not found ─────────────────────────────────────────────────────────────────

def test_unknown_analysis_id_returns_404(aws_setup):
    result = _call("does-not-exist")
    assert result["statusCode"] == 404
    assert "not found" in json.loads(result["body"])["error"].lower()


def test_missing_path_parameter_returns_400(aws_setup):
    result = get_results_mod.handler(
        {"body": "{}", "headers": {}, "pathParameters": None,
         "queryStringParameters": {"user_id": "user123"}},
        None,
    )
    assert result["statusCode"] == 400


# ── Ownership isolation ───────────────────────────────────────────────────────

def test_user_cannot_fetch_another_users_analysis(aws_setup, analyses_table):
    """user_b's analysis_id is invisible to user_a because PK includes user_id."""
    _seed(analyses_table, user_id="user_b", analysis_id="ana-private")

    # user_a tries to access user_b's analysis_id
    result = _call("ana-private", user_id="user_a")
    assert result["statusCode"] == 404


def test_same_analysis_id_different_users_are_independent(aws_setup, analyses_table):
    _seed(analyses_table, user_id="alice", analysis_id="shared-id")
    _seed(analyses_table, user_id="bob",   analysis_id="shared-id")

    alice_result = _call("shared-id", user_id="alice")
    bob_result   = _call("shared-id", user_id="bob")

    assert alice_result["statusCode"] == 200
    assert bob_result["statusCode"]   == 200
