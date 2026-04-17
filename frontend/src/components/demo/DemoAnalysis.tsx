import { demoAnalysis } from '../../data/demoAnalysis';
import AnalysisResults from '../results/AnalysisResults';

export default function DemoAnalysis() {
  return (
    <div className="bg-gray-50 py-20">
      <div className="max-w-4xl mx-auto px-4">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            See what a real analysis looks like
          </h2>
          <p className="text-gray-500">
            Below is a live demo of an Austin, TX residential lease analysis.
          </p>
        </div>

        <div className="bg-amber-50 border-2 border-amber-300 rounded-xl px-6 py-4 mb-6 flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-4">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-200 text-amber-900 uppercase tracking-wide">
              Demo only
            </span>
            <span className="text-amber-800 font-semibold text-sm">
              Sample analysis — Austin, TX residential lease
            </span>
          </div>
          <span className="hidden sm:block text-amber-400">|</span>
          <span className="text-amber-600 text-sm">Not a real lease. No data submitted.</span>
        </div>

        <AnalysisResults analysis={demoAnalysis} isDemo={true} />

        <div className="mt-10 text-center bg-white rounded-2xl border border-gray-200 p-8">
          <h3 className="text-xl font-bold text-gray-900 mb-2">
            See what&apos;s hiding in YOUR lease
          </h3>
          <p className="text-gray-500 mb-6">
            The demo above is from a real lease type. Yours could have different risks. Know before
            you sign.
          </p>
          <a
            href="#upload"
            className="inline-block px-8 py-4 bg-brand-600 text-white font-semibold rounded-xl hover:bg-brand-700 transition-colors shadow-lg"
          >
            Analyze my lease
          </a>
        </div>
      </div>
    </div>
  );
}
