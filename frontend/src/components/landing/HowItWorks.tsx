const steps = [
  {
    icon: '📤',
    title: 'Upload your lease',
    description:
      'Drop your PDF rental agreement. We accept standard US residential leases up to 20MB.',
  },
  {
    icon: '🤖',
    title: 'AI analyzes every clause',
    description:
      'Our AI reads every clause against current landlord-tenant law, looking for hidden risks and missing protections.',
  },
  {
    icon: '📊',
    title: 'Get your risk report',
    description:
      'Review a plain-English breakdown of risky clauses, key dates, financial obligations, and what to negotiate.',
  },
];

export default function HowItWorks() {
  return (
    <section className="bg-gray-50 py-20">
      <div className="max-w-5xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">How it works</h2>
        <p className="text-center text-gray-500 mb-14">Three steps to understanding your lease</p>
        <div className="grid md:grid-cols-3 gap-8">
          {steps.map((step, i) => (
            <div key={i} className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
              <div className="text-4xl mb-4">{step.icon}</div>
              <div className="text-sm font-semibold text-brand-600 mb-2">Step {i + 1}</div>
              <h3 className="text-lg font-bold text-gray-900 mb-3">{step.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
        <p className="text-center text-sm text-gray-400 mt-10">
          🔒 Your document is analyzed and permanently deleted within 24 hours
        </p>
      </div>
    </section>
  );
}
