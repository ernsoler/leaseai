const API_URL = import.meta.env.VITE_API_URL ?? '';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error((err as { error?: string }).error ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function getUploadUrl(
  contentType: string
): Promise<{ upload_url: string; s3_key: string }> {
  return apiFetch('/upload-url', {
    method: 'POST',
    body: JSON.stringify({ content_type: contentType }),
  });
}

export async function uploadToS3(uploadUrl: string, file: File): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    body: file,
    headers: { 'Content-Type': 'application/pdf' },
  });
  if (!res.ok) throw new Error('Upload to S3 failed');
}

export async function submitAnalysis(
  s3Key: string
): Promise<{ analysis_id: string; user_id: string }> {
  return apiFetch('/submit', {
    method: 'POST',
    body: JSON.stringify({ s3_key: s3Key }),
  });
}

export async function getAnalysis(analysisId: string, userId: string): Promise<unknown> {
  return apiFetch(`/analysis/${analysisId}?user_id=${encodeURIComponent(userId)}`);
}
