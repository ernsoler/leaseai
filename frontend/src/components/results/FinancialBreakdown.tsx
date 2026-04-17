import type { FinancialSummary } from '../../types/analysis';

interface Props {
  financialSummary: FinancialSummary;
}

function fmt(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function FinancialBreakdown({ financialSummary: fs }: Props) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
        Financial Summary
      </h3>

      {/* Summary grid — 3 equal columns, values shrink to fit */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { value: fmt(fs.total_monthly_cost), label: 'Monthly total' },
          { value: fmt(fs.total_move_in_cost), label: 'Move-in cost' },
          { value: fmt(fs.annual_cost),         label: 'Annual cost' },
        ].map(({ value, label }) => (
          <div key={label} className="bg-gray-50 rounded-xl p-3 text-center min-w-0">
            <div className="text-sm font-bold text-gray-900 leading-tight">{value}</div>
            <div className="text-xs text-gray-500 mt-1">{label}</div>
          </div>
        ))}
      </div>

      {/* Penalties */}
      {fs.penalties.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Penalties &amp; Fees
          </h4>
          <div className="space-y-2">
            {fs.penalties.map((penalty, i) => (
              <div
                key={i}
                className={`flex items-start gap-3 text-sm pb-2 ${
                  i < fs.penalties.length - 1 ? 'border-b border-gray-100' : ''
                }`}
              >
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-gray-900">{penalty.type}</span>
                  <p className="text-xs text-gray-400 mt-0.5">{penalty.condition}</p>
                </div>
                <span className="text-gray-700 font-semibold text-right shrink-0 max-w-[45%] break-words">
                  {typeof penalty.amount === 'number' ? fmt(penalty.amount) : penalty.amount}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
