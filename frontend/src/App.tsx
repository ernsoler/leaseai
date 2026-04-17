import { useEffect, useState } from 'react';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import Hero from './components/landing/Hero';
import HowItWorks from './components/landing/HowItWorks';
import FAQ from './components/landing/FAQ';
import DemoAnalysis from './components/demo/DemoAnalysis';
import PaymentFlow from './components/upload/PaymentFlow';
import AnalysisResults from './components/results/AnalysisResults';
import { useAnalysis } from './hooks/useAnalysis';

// ── Scanning animation shown while AI is running ──────────────────────────────
const ANALYSIS_STEPS = [
  { label: 'Extracting lease text', duration: 8 },
  { label: 'Identifying clauses and obligations', duration: 18 },
  { label: 'Scoring risk by clause type', duration: 22 },
  { label: 'Checking for missing protections', duration: 16 },
  { label: 'Building your report', duration: 36 },
];

function AnalysisPollingScreen() {
  const [elapsed, setElapsed] = useState(0);
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let cumulative = 0;
    for (let i = 0; i < ANALYSIS_STEPS.length - 1; i++) {
      cumulative += ANALYSIS_STEPS[i].duration;
      if (elapsed < cumulative) { setActiveStep(i); return; }
    }
    setActiveStep(ANALYSIS_STEPS.length - 1);
  }, [elapsed]);

  const totalEstimate = 90;
  const progressPct = Math.min(Math.round((elapsed / totalEstimate) * 100), 95);
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  const elapsedLabel = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;

  return (
    <>
      <style>{`
        @keyframes scan {
          0%   { top: 0%;   opacity: 1; }
          48%  { top: 88%;  opacity: 1; }
          50%  { top: 88%;  opacity: 0; }
          52%  { top: 0%;   opacity: 0; }
          54%  { top: 0%;   opacity: 1; }
          100% { top: 0%;   opacity: 1; }
        }
        .animate-scan { animation: scan 2.8s ease-in-out infinite; }
      `}</style>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 max-w-xl mx-auto">
        {/* Document scanner */}
        <div className="flex justify-center mb-8">
          <div className="relative w-20 h-28 bg-gray-50 border-2 border-gray-200 rounded-md shadow-sm overflow-hidden">
            <div className="p-2 pt-3 space-y-2">
              {[100, 75, 100, 90, 60, 100, 80].map((w, i) => (
                <div
                  key={i}
                  className="h-1.5 rounded"
                  style={{ width: `${w}%`, backgroundColor: i % 3 === 2 ? '#c7d2fe' : '#d1d5db' }}
                />
              ))}
            </div>
            <div
              className="animate-scan absolute left-0 right-0 h-0.5 bg-brand-500"
              style={{ boxShadow: '0 0 6px 2px rgba(99,102,241,0.4)' }}
            />
          </div>
        </div>

        {/* Live badge */}
        <div className="flex items-center justify-center gap-2 mb-6">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-500 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-600" />
          </span>
          <span className="text-sm font-semibold text-brand-700 uppercase tracking-wide">
            Live analysis in progress
          </span>
        </div>

        <h2 className="text-2xl font-bold text-gray-900 text-center mb-2">
          Analyzing your lease
        </h2>
        <p className="text-center text-gray-500 text-sm mb-8">
          Hang tight — this is your real lease being analyzed, not the demo.
        </p>

        {/* Step list */}
        <ol className="space-y-3 mb-8">
          {ANALYSIS_STEPS.map((step, i) => {
            const isDone = i < activeStep;
            const isActive = i === activeStep;
            return (
              <li key={step.label} className="flex items-center gap-3">
                <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                  {isDone ? (
                    <svg className="w-5 h-5 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : isActive ? (
                    <div className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-gray-300" />
                  )}
                </div>
                <span className={
                  isDone ? 'text-sm text-gray-400 line-through'
                    : isActive ? 'text-sm font-semibold text-gray-900'
                      : 'text-sm text-gray-400'
                }>
                  {step.label}
                </span>
              </li>
            );
          })}
        </ol>

        {/* Progress bar */}
        <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden mb-3">
          <div
            className="h-full bg-brand-500 rounded-full transition-all duration-1000 ease-linear"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-400">
          <span>Elapsed: {elapsedLabel}</span>
          <span>{progressPct}%</span>
        </div>

        <p className="text-center text-gray-400 text-xs mt-6">
          Most analyses complete in 30–90 seconds. You can keep this tab open.
        </p>
      </div>
    </>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  // Support returning to the page via URL params (e.g. after a tab refresh)
  const params = new URLSearchParams(window.location.search);
  const [analysisId, setAnalysisId] = useState<string | null>(params.get('analysis_id'));
  const [userId, setUserId] = useState<string | null>(params.get('user_id'));

  const { state: pollState, result, error: pollError } = useAnalysis(analysisId, userId);

  function handleAnalysisStarted(id: string, uid: string) {
    // Update URL silently so a page refresh can resume polling
    window.history.replaceState({}, '', `/?analysis_id=${id}&user_id=${uid}`);
    setAnalysisId(id);
    setUserId(uid);
    // Scroll to the upload section so the loading animation is visible
    document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth' });
  }

  function handleReset() {
    window.history.replaceState({}, '', '/');
    setAnalysisId(null);
    setUserId(null);
  }

  // Determine what to render in the upload section
  const uploadSection = (() => {
    if (analysisId && userId) {
      if (pollState === 'done' && result) {
        return (
          <div>
            <div className="mb-6 px-4 py-3 bg-green-50 border border-green-200 rounded-xl flex items-center gap-3 max-w-xl mx-auto">
              <svg className="w-5 h-5 text-green-600 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              <div>
                <p className="text-sm font-semibold text-green-800">Your lease analysis is ready</p>
                <p className="text-xs text-green-600">This is the real analysis of your uploaded lease — not a demo.</p>
              </div>
            </div>
            <AnalysisResults analysis={result} />
            <div className="mt-8 text-center">
              <button
                onClick={handleReset}
                className="px-6 py-3 border border-gray-300 text-gray-600 rounded-xl hover:bg-gray-50"
              >
                Analyze another lease
              </button>
            </div>
          </div>
        );
      }

      if (pollState === 'error') {
        return (
          <div className="text-center p-8 max-w-md mx-auto">
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-red-600" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Analysis could not complete</h2>
            <p className="text-red-600 mb-6 text-sm">{pollError}</p>
            <button
              onClick={handleReset}
              className="px-6 py-3 bg-brand-600 text-white rounded-xl hover:bg-brand-700"
            >
              Start over
            </button>
          </div>
        );
      }

      // pending / processing — show scanning animation
      return <AnalysisPollingScreen />;
    }

    // No analysis running — show upload form
    return <PaymentFlow onAnalysisStarted={handleAnalysisStarted} />;
  })();

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main>
        <Hero />
        <HowItWorks />
        <section id="demo">
          <DemoAnalysis />
        </section>
        <section id="upload" className="py-20 bg-white">
          <div className="max-w-4xl mx-auto px-4">
            {!analysisId && (
              <>
                <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
                  Analyze your lease
                </h2>
                <p className="text-center text-gray-500 mb-12">
                  Upload your PDF and get a full risk report in 60 seconds.
                </p>
              </>
            )}
            {uploadSection}
          </div>
        </section>
        <FAQ />
      </main>
      <Footer />
    </div>
  );
}
