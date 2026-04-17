import type { KeyDate } from '../../types/analysis';

interface Props {
  keyDates: KeyDate[];
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr + 'T00:00:00');
  const now = new Date();
  return Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

export default function KeyDatesTimeline({ keyDates }: Props) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
        Key Dates
      </h3>
      <div className="space-y-4">
        {keyDates.map((d, i) => {
          const days = daysUntil(d.date);
          const isUrgent = d.notice_required !== null && days < 90 && days > 0;
          return (
            <div
              key={i}
              className={`flex gap-4 pb-4 ${
                i < keyDates.length - 1 ? 'border-b border-gray-100' : ''
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                  isUrgent ? 'bg-red-500' : 'bg-brand-400'
                }`}
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 text-sm">{d.event}</div>
                <div className="text-xs text-gray-500 mt-0.5">{formatDate(d.date)}</div>
                {d.notice_required && (
                  <div
                    className={`text-xs mt-1 ${
                      isUrgent ? 'text-red-600 font-medium' : 'text-amber-600'
                    }`}
                  >
                    {d.notice_required}
                  </div>
                )}
              </div>
              <div
                className={`text-xs font-medium flex-shrink-0 ${
                  days < 0 ? 'text-gray-400' : days < 90 ? 'text-red-500' : 'text-gray-500'
                }`}
              >
                {days < 0 ? `${Math.abs(days)}d ago` : days === 0 ? 'Today' : `${days}d`}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
