import { useState, useEffect, useRef } from 'react';
import { getAnalysis } from '../lib/api';
import type { AnalysisResult } from '../types/analysis';

type PollState = 'idle' | 'polling' | 'done' | 'error';

const POLL_INTERVAL_MS = 3000;
const MAX_POLLS = 100; // ~5 minutes

export function useAnalysis(analysisId: string | null, userId: string | null) {
  const [state, setState] = useState<PollState>('idle');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!analysisId || !userId) return;

    setState('polling');
    pollCount.current = 0;

    async function poll() {
      if (pollCount.current >= MAX_POLLS) {
        setState('error');
        setError('Analysis is taking too long. Please check back later.');
        return;
      }
      pollCount.current++;

      try {
        const data = (await getAnalysis(analysisId!, userId!)) as AnalysisResult;
        if (data.status === 'completed') {
          setResult(data);
          setState('done');
          return;
        }
        if (data.status === 'failed') {
          setState('error');
          setError('Analysis failed. Please try again or contact support.');
          return;
        }
        // awaiting_payment / pending / processing — keep polling
        timer.current = setTimeout(poll, POLL_INTERVAL_MS);
      } catch {
        setState('error');
        setError('Could not fetch analysis results. Please refresh the page.');
      }
    }

    void poll();

    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [analysisId, userId]);

  return { state, result, error };
}
