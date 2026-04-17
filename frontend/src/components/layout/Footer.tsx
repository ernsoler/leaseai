export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-400 py-12">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-start gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-2xl">📋</span>
              <span className="text-white font-bold text-lg">LeaseAI</span>
            </div>
            <p className="text-sm max-w-xs">
              AI-powered lease analysis for tenants. Know what you are signing.
            </p>
          </div>
          <div className="text-sm space-y-2 max-w-sm">
            <p className="text-white font-medium">Legal disclaimer</p>
            <p className="text-xs text-gray-500">
              LeaseAI provides AI-generated analysis for informational purposes only. This is not
              legal advice. Consult a licensed attorney before making decisions about your lease.
            </p>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-gray-800 text-xs text-gray-600">
          &copy; {new Date().getFullYear()} LeaseAI. Built with React + AWS Lambda + Claude AI.
          Open source portfolio project.
        </div>
      </div>
    </footer>
  );
}
