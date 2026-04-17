"""Pydantic schemas for LeaseAI analysis response validation."""
from __future__ import annotations
from typing import Optional, Union
from pydantic import BaseModel, Field


class LeaseSummary(BaseModel):
    property_address: Optional[str] = None
    landlord_name: Optional[str] = None
    tenant_name: Optional[str] = None
    lease_start: Optional[str] = None
    lease_end: Optional[str] = None
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    lease_type: Optional[str] = None  # "fixed" | "month-to-month"


class Clause(BaseModel):
    id: str
    category: str  # rent|deposit|maintenance|termination|renewal|pets|subletting|liability|insurance|utilities|parking|modifications|entry_access|other
    title: str
    original_text: str
    risk_level: str  # low|medium|high|critical
    risk_explanation: str
    recommendation: str
    section_reference: Optional[str] = None


class KeyDate(BaseModel):
    event: str
    date: Optional[str] = None
    notice_required: Optional[str] = None


class Penalty(BaseModel):
    type: str
    amount: Union[float, str]
    condition: str


class FinancialSummary(BaseModel):
    total_monthly_cost: Optional[float] = None
    total_move_in_cost: Optional[float] = None
    annual_cost: Optional[float] = None
    penalties: list[Penalty] = Field(default_factory=list)


class RiskBreakdown(BaseModel):
    financial_risk: int
    termination_risk: int
    maintenance_risk: int
    legal_risk: int


class RiskScore(BaseModel):
    overall: int = Field(ge=1, le=100)
    breakdown: RiskBreakdown


class LeaseAnalysis(BaseModel):
    summary: LeaseSummary
    clauses: list[Clause] = Field(default_factory=list)
    key_dates: list[KeyDate] = Field(default_factory=list)
    financial_summary: FinancialSummary
    risk_score: RiskScore
    missing_clauses: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
