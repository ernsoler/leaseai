import { useState } from 'react';
import { getUploadUrl, uploadToS3 } from '../lib/api';

type UploadState = 'idle' | 'uploading' | 'done' | 'error';

export function useUpload() {
  const [state, setState] = useState<UploadState>('idle');
  const [s3Key, setS3Key] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function upload(file: File) {
    setState('uploading');
    setError(null);
    try {
      const { upload_url, s3_key } = await getUploadUrl('application/pdf');
      await uploadToS3(upload_url, file);
      setS3Key(s3_key);
      setState('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
      setState('error');
    }
  }

  function reset() {
    setState('idle');
    setS3Key(null);
    setError(null);
  }

  return { state, s3Key, error, upload, reset };
}
