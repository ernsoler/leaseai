const faqs = [
  {
    q: 'Is my lease data secure?',
    a: 'Yes. Your PDF is encrypted in transit and at rest. It is permanently deleted from our servers within 24 hours of upload, regardless of whether an analysis is completed.',
  },
  {
    q: 'What types of leases do you support?',
    a: 'US residential rental agreements in PDF format. We support fixed-term and month-to-month leases. Commercial leases are not currently supported.',
  },
  {
    q: 'How accurate is the analysis?',
    a: 'Very accurate for identifying common risk clauses, but AI is not infallible. We strongly recommend using this as a starting point for a conversation with a licensed attorney, not a replacement for one.',
  },
  {
    q: 'How long are my results stored?',
    a: 'Analysis results are stored for 30 days so you can review them. After 30 days, results are permanently deleted.',
  },
];

export default function FAQ() {
  return (
    <section className="bg-gray-50 py-20">
      <div className="max-w-3xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
          Frequently asked questions
        </h2>
        <div className="space-y-4">
          {faqs.map((faq, i) => (
            <details key={i} className="bg-white rounded-xl border border-gray-200 group">
              <summary className="px-6 py-4 font-semibold text-gray-900 cursor-pointer list-none flex justify-between items-center">
                {faq.q}
                <span className="text-gray-400 group-open:rotate-180 transition-transform text-sm">
                  ▼
                </span>
              </summary>
              <div className="px-6 pb-5 text-gray-500 text-sm leading-relaxed">{faq.a}</div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
