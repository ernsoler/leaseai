export type RiskLevel = 'critical' | 'high' | 'medium' | 'low';

export interface Clause {
  id: string;
  category: string;
  title: string;
  original_text: string;
  risk_level: RiskLevel;
  risk_explanation: string;
  recommendation: string;
  section_reference: string;
}

export interface KeyDate {
  event: string;
  date: string;
  notice_required: string | null;
}

export interface Penalty {
  type: string;
  amount: number | string;
  condition: string;
}

export interface FinancialSummary {
  total_monthly_cost: number;
  total_move_in_cost: number;
  annual_cost: number;
  penalties: Penalty[];
}

export interface RiskBreakdown {
  financial_risk: number;
  termination_risk: number;
  maintenance_risk: number;
  legal_risk: number;
}

export interface RiskScore {
  overall: number;
  breakdown: RiskBreakdown;
}

export interface LeaseSummary {
  property_address: string | null;
  landlord_name: string | null;
  tenant_name: string | null;
  lease_start: string | null;
  lease_end: string | null;
  monthly_rent: number | null;
  security_deposit: number | null;
  lease_type: 'fixed' | 'month-to-month' | null;
}

export interface AnalysisResult {
  analysis_id: string;
  status: 'awaiting_payment' | 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  summary: LeaseSummary;
  clauses: Clause[];
  key_dates: KeyDate[];
  financial_summary: FinancialSummary;
  risk_score: RiskScore;
  missing_clauses: string[];
  red_flags: string[];
}
