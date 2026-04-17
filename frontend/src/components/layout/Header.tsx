export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2">
          <span className="text-2xl">📋</span>
          <span className="font-bold text-xl text-gray-900">LeaseAI</span>
        </a>
        <nav className="flex items-center gap-6">
          <a href="#demo" className="text-gray-500 hover:text-gray-900 text-sm font-medium hidden sm:block">
            See demo
          </a>
          <a
            href="#upload"
            className="px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors"
          >
            Analyze my lease
          </a>
        </nav>
      </div>
    </header>
  );
}
