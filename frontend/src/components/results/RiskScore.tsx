import type { RiskScore as RiskScoreType } from '../../types/analysis';

interface Props {
  riskScore: RiskScoreType;
}

function getColor(score: number): string {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#eab308';
  if (score >= 40) return '#f97316';
  return '#ef4444';
}

function getLabel(score: number): string {
  if (score >= 80) return 'Low Risk';
  if (score >= 60) return 'Moderate';
  if (score >= 40) return 'High Risk';
  return 'Very Risky';
}

function CircularGauge({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = getColor(score);

  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={radius} fill="none" stroke="#f3f4f6" strokeWidth="12" />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
        />
        <text
          x="70"
          y="65"
          textAnchor="middle"
          fill={color}
          fontSize="28"
          fontWeight="bold"
        >
          {score}
        </text>
        <text x="70" y="85" textAnchor="middle" fill="#6b7280" fontSize="12">
          /100
        </text>
      </svg>
      <span className="text-sm font-semibold mt-1" style={{ color }}>
        {getLabel(score)}
      </span>
    </div>
  );
}

function SubScoreBar({ label, score }: { label: string; score: number }) {
  const color = getColor(score);
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span className="font-semibold" style={{ color }}>
          {score}
        </span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className="h-2 rounded-full transition-all"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function RiskScore({ riskScore }: Props) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
        Risk Score
      </h3>
      <div className="flex flex-col items-center mb-6">
        <CircularGauge score={riskScore.overall} />
        <p className="text-xs text-gray-400 mt-2 text-center">Higher score = safer lease</p>
      </div>
      <SubScoreBar label="Financial Risk" score={riskScore.breakdown.financial_risk} />
      <SubScoreBar label="Termination Risk" score={riskScore.breakdown.termination_risk} />
      <SubScoreBar label="Maintenance Risk" score={riskScore.breakdown.maintenance_risk} />
      <SubScoreBar label="Legal Risk" score={riskScore.breakdown.legal_risk} />
    </div>
  );
}
