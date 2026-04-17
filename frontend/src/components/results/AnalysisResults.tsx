import type { AnalysisResult } from '../../types/analysis';
import RedFlags from './RedFlags';
import RiskScore from './RiskScore';
import ClauseCard from './ClauseCard';
import FinancialBreakdown from './FinancialBreakdown';
import KeyDatesTimeline from './KeyDatesTimeline';

interface Props {
  analysis: AnalysisResult;
  isDemo?: boolean;
}

function SummaryCard({ summary }: { summary: AnalysisResult['summary'] }) {
  const fmt = (n: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

  const rows: [string, string | null][] = [
    ['Property', summary.property_address],
    ['Landlord', summary.landlord_name],
    ['Tenant', summary.tenant_name],
    [
      'Term',
      summary.lease_start && summary.lease_end
        ? `${summary.lease_start} – ${summary.lease_end}`
        : null,
    ],
    ['Monthly Rent', summary.monthly_rent != null ? fmt(summary.monthly_rent) : null],
    ['Security Deposit', summary.security_deposit != null ? fmt(summary.security_deposit) : null],
    ['Lease Type', summary.lease_type],
  ];

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
        Lease Summary
      </h3>
      <dl className="space-y-2 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4">
            <dt className="text-gray-500 flex-shrink-0">{label}</dt>
            <dd className="text-gray-900 font-medium text-right">
              {value ?? <span className="text-gray-400 font-normal">Not found</span>}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

const riskOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export default function AnalysisResults({ analysis, isDemo = false }: Props) {
  const sortedClauses = [...analysis.clauses].sort(
    (a, b) => (riskOrder[a.risk_level] ?? 4) - (riskOrder[b.risk_level] ?? 4)
  );

  return (
    <div className="space-y-6">
      <RedFlags redFlags={analysis.red_flags} missingClauses={analysis.missing_clauses} />

      <div className="grid md:grid-cols-2 gap-6">
        <RiskScore riskScore={analysis.risk_score} />
        <SummaryCard summary={analysis.summary} />
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Risky Clauses ({analysis.clauses.length} found, sorted by severity)
        </h3>
        {sortedClauses.map((clause) => (
          <ClauseCard key={clause.id} clause={clause} />
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <KeyDatesTimeline keyDates={analysis.key_dates} />
        <FinancialBreakdown financialSummary={analysis.financial_summary} />
      </div>

      {isDemo ? (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
          <p className="text-xs text-amber-700 font-medium">
            This is a static demo — no real lease was uploaded or analyzed.
            Upload your own PDF above to get your personalized report.
          </p>
        </div>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-center">
          <p className="text-xs text-gray-500">
            This is an AI-generated analysis for informational purposes only. It is not legal
            advice. Consult a licensed attorney before making decisions about your lease.
          </p>
        </div>
      )}
    </div>
  );
}
