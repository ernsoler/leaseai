import { useState } from 'react';
import type { Clause } from '../../types/analysis';

interface Props {
  clause: Clause;
}

const riskConfig = {
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-100 text-red-700',
    dot: '🔴',
  },
  high: {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    badge: 'bg-orange-100 text-orange-700',
    dot: '🟠',
  },
  medium: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    badge: 'bg-yellow-100 text-yellow-700',
    dot: '🟡',
  },
  low: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    badge: 'bg-green-100 text-green-700',
    dot: '🟢',
  },
};

export default function ClauseCard({ clause }: Props) {
  const [expanded, setExpanded] = useState(false);
  const config = riskConfig[clause.risk_level];

  return (
    <div className={`rounded-xl border ${config.border} ${config.bg} overflow-hidden mb-3`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-4 flex items-center gap-3"
      >
        <span className="text-lg flex-shrink-0">{config.dot}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-900 text-sm">{clause.title}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${config.badge}`}>
              {clause.risk_level.toUpperCase()}
            </span>
            <span className="text-xs text-gray-400">{clause.section_reference}</span>
          </div>
          <span className="text-xs text-gray-500">{clause.category}</span>
        </div>
        <span className="text-gray-400 text-sm flex-shrink-0">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-3 border-t border-gray-200 space-y-4">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              Original Text
            </p>
            <p className="text-sm text-gray-700 bg-white rounded-lg p-3 border border-gray-200 italic">
              &ldquo;{clause.original_text}&rdquo;
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              Why This Is Risky
            </p>
            <p className="text-sm text-gray-700">{clause.risk_explanation}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              What To Do
            </p>
            <p className="text-sm text-gray-700">{clause.recommendation}</p>
          </div>
        </div>
      )}
    </div>
  );
}
