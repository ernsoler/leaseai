"""Tests for Pydantic schema validation."""
import pytest
from backend.lib.schema import LeaseAnalysis


MINIMAL_VALID = {
    "summary": {
        "property_address": "123 Main St",
        "landlord_name": "John Smith",
        "tenant_name": "Jane Doe",
        "lease_start": "2025-02-01",
        "lease_end": "2026-01-31",
        "monthly_rent": 2200.0,
        "security_deposit": 4400.0,
        "lease_type": "fixed",
    },
    "clauses": [
        {
            "id": "clause_001",
            "category": "termination",
            "title": "Early Termination Penalty",
            "original_text": "Tenant shall be liable for all remaining rent...",
            "risk_level": "high",
            "risk_explanation": "Double penalty — remaining rent plus 2 month fee.",
            "recommendation": "Negotiate to remove the additional termination fee.",
            "section_reference": "Section 10",
        }
    ],
    "key_dates": [
        {"event": "Lease start", "date": "2025-02-01", "notice_required": None},
        {"event": "Lease end", "date": "2026-01-31", "notice_required": "60 days"},
    ],
    "financial_summary": {
        "total_monthly_cost": 2200.0,
        "total_move_in_cost": 6600.0,
        "annual_cost": 26400.0,
        "penalties": [
            {"type": "Late fee", "amount": 150.0, "condition": "Payment after 5th of month"}
        ],
    },
    "risk_score": {
        "overall": 45,
        "breakdown": {
            "financial_risk": 50,
            "termination_risk": 20,
            "maintenance_risk": 60,
            "legal_risk": 30,
        },
    },
    "missing_clauses": ["Habitability warranty clause"],
    "red_flags": ["Landlord entry without notice is likely illegal in most states."],
}


def test_valid_analysis_parses():
    analysis = LeaseAnalysis.model_validate(MINIMAL_VALID)
    assert analysis.summary.monthly_rent == 2200.0
    assert analysis.risk_score.overall == 45
    assert len(analysis.clauses) == 1
    assert len(analysis.red_flags) == 1


def test_null_fields_allowed():
    data = dict(MINIMAL_VALID)
    data["summary"] = {**MINIMAL_VALID["summary"], "landlord_name": None, "lease_end": None}
    analysis = LeaseAnalysis.model_validate(data)
    assert analysis.summary.landlord_name is None


def test_risk_score_bounds():
    data = dict(MINIMAL_VALID)
    data["risk_score"] = {
        "overall": 150,  # out of range
        "breakdown": MINIMAL_VALID["risk_score"]["breakdown"],
    }
    with pytest.raises(Exception):
        LeaseAnalysis.model_validate(data)


def test_empty_clauses_and_dates():
    data = {**MINIMAL_VALID, "clauses": [], "key_dates": []}
    analysis = LeaseAnalysis.model_validate(data)
    assert analysis.clauses == []
    assert analysis.key_dates == []


def test_penalty_amount_can_be_string():
    data = dict(MINIMAL_VALID)
    data["financial_summary"] = {
        **MINIMAL_VALID["financial_summary"],
        "penalties": [{"type": "Early termination", "amount": "2 months rent", "condition": "Breaking lease early"}],
    }
    analysis = LeaseAnalysis.model_validate(data)
    assert analysis.financial_summary.penalties[0].amount == "2 months rent"
