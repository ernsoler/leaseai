import { useState } from 'react';
import UploadZone from './UploadZone';
import { useUpload } from '../../hooks/useUpload';
import { submitAnalysis } from '../../lib/api';

type FlowState = 'idle' | 'uploading' | 'ready' | 'submitting' | 'error';

interface Props {
  onAnalysisStarted: (analysisId: string, userId: string) => void;
}

export default function PaymentFlow({ onAnalysisStarted }: Props) {
  const [flowState, setFlowState] = useState<FlowState>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { state: uploadState, s3Key, upload } = useUpload();

  async function handleFile(file: File) {
    setSelectedFile(file);
    setFlowState('uploading');
    await upload(file);
    setFlowState('ready');
  }

  async function handleAnalyze() {
    if (!s3Key) return;
    setFlowState('submitting');
    try {
      const { analysis_id, user_id } = await submitAnalysis(s3Key);
      onAnalysisStarted(analysis_id, user_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit. Please try again.');
      setFlowState('error');
    }
  }

  if (flowState === 'error') {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">{error ?? 'Something went wrong'}</p>
        <button
          onClick={() => { setFlowState('idle'); setError(null); }}
          className="px-6 py-3 bg-brand-600 text-white rounded-xl hover:bg-brand-700"
        >
          Try again
        </button>
      </div>
    );
  }

  if (flowState === 'submitting') {
    return (
      <div className="text-center py-8">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-600">Submitting your lease for analysis...</p>
      </div>
    );
  }

  if (flowState === 'ready' || flowState === 'uploading') {
    return (
      <div>
        {selectedFile && (
          <div className="mb-8 p-4 bg-green-50 border border-green-200 rounded-xl text-center">
            <span className="text-green-700 font-medium">✓ {selectedFile.name}</span>
            <span className="text-green-600 text-sm ml-2">
              ({selectedFile.size >= 1024 * 1024
                ? `${(selectedFile.size / 1024 / 1024).toFixed(1)} MB`
                : `${Math.round(selectedFile.size / 1024)} KB`}) — ready for analysis
            </span>
          </div>
        )}
        {flowState === 'uploading' || uploadState === 'uploading' ? (
          <div className="text-center py-6">
            <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-gray-500 text-sm">Uploading securely...</p>
          </div>
        ) : (
          <div className="text-center">
            <button
              onClick={handleAnalyze}
              disabled={uploadState !== 'done'}
              className="px-8 py-4 bg-brand-600 text-white text-lg font-semibold rounded-xl hover:bg-brand-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Analyze My Lease
            </button>
            <p className="text-gray-400 text-sm mt-3">Free · Usually takes 30–90 seconds</p>
          </div>
        )}
      </div>
    );
  }

  return <UploadZone onFile={handleFile} />;
}
