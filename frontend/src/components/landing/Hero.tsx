export default function Hero() {
  return (
    <section className="bg-white py-20 md:py-28">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <div className="inline-flex items-center gap-2 bg-brand-50 text-brand-700 text-sm font-medium px-4 py-2 rounded-full mb-8">
          <span>⚡</span>
          <span>AI-powered analysis in 60 seconds</span>
        </div>
        <h1 className="text-4xl md:text-6xl font-extrabold text-gray-900 mb-6 leading-tight">
          Know what you&apos;re signing
          <br />
          <span className="text-brand-600">before you sign it</span>
        </h1>
        <p className="text-xl text-gray-500 mb-10 max-w-2xl mx-auto">
          Upload your lease PDF and get a plain-English risk report that catches hidden traps,
          unfair clauses, and missing protections — in under 60 seconds.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <a
            href="#demo"
            className="px-8 py-4 border-2 border-gray-200 text-gray-700 font-semibold rounded-xl hover:border-gray-300 hover:bg-gray-50 transition-all"
          >
            See a demo analysis
          </a>
          <a
            href="#upload"
            className="px-8 py-4 bg-brand-600 text-white font-semibold rounded-xl hover:bg-brand-700 transition-all shadow-lg"
          >
            Analyze my lease
          </a>
        </div>
        <p className="mt-6 text-sm text-gray-400">
          No account required &middot; Results in 60 seconds
        </p>
      </div>
    </section>
  );
}
