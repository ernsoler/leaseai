interface Props {
  redFlags: string[];
  missingClauses: string[];
}

export default function RedFlags({ redFlags, missingClauses }: Props) {
  return (
    <div className="space-y-4 mb-6">
      {redFlags.length > 0 && (
        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-6">
          <h3 className="text-red-800 font-bold text-lg mb-4 flex items-center gap-2">
            ⚠️ Red Flags ({redFlags.length})
          </h3>
          <ul className="space-y-2">
            {redFlags.map((flag, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-red-700">
                <span className="flex-shrink-0 mt-0.5 font-bold">•</span>
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {missingClauses.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
          <h3 className="text-amber-800 font-bold mb-3 flex items-center gap-2">
            📋 Missing Protections ({missingClauses.length})
          </h3>
          <ul className="space-y-2">
            {missingClauses.map((clause, i) => (
              <li key={i} className="flex items-start gap-3 text-sm text-amber-700">
                <span className="flex-shrink-0 font-bold">•</span>
                <span>{clause}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
