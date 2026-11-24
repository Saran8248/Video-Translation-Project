import { VideoAsset, DubbingJob, SegmentItem, VoiceOption, CreateJobPayload } from './types';

const API_BASE = '/api/v1';

export async function uploadVideo(file: File): Promise<VideoAsset> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/videos/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Video upload failed');
  }
  return res.json();
}

export async function generateSampleVideo(): Promise<VideoAsset> {
  const res = await fetch(`${API_BASE}/videos/sample/generate`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to generate sample video');
  }
  return res.json();
}

export async function generateMultilingualSampleVideo(): Promise<VideoAsset> {
  const res = await fetch(`${API_BASE}/videos/sample/generate-multilingual`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to generate multilingual sample video');
  }
  return res.json();
}

export async function fetchVoices(locale?: string): Promise<VoiceOption[]> {
  const url = locale ? `${API_BASE}/voices?locale=${encodeURIComponent(locale)}` : `${API_BASE}/voices`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch voices');
  return res.json();
}

export async function createDubbingJob(payload: CreateJobPayload): Promise<{ id: string; status: string }> {
  const res = await fetch(`${API_BASE}/dubbing/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create dubbing job');
  }
  return res.json();
}

export async function fetchJobStatus(jobId: string): Promise<DubbingJob> {
  const res = await fetch(`${API_BASE}/dubbing/jobs/${jobId}`);
  if (!res.ok) throw new Error('Failed to fetch job status');
  return res.json();
}

export async function fetchJobSegments(jobId: string): Promise<SegmentItem[]> {
  const res = await fetch(`${API_BASE}/dubbing/jobs/${jobId}/segments`);
  if (!res.ok) throw new Error('Failed to fetch segments');
  const data = await res.json();
  return data.segments;
}

export async function updateSegment(
  jobId: string,
  segmentId: string,
  patch: { translated_text?: string; start_ms?: number; end_ms?: number; speaker_id?: string }
): Promise<void> {
  const res = await fetch(`${API_BASE}/dubbing/jobs/${jobId}/segments/${segmentId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error('Failed to update segment');
}

export async function retryJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/dubbing/jobs/${jobId}/retry`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to retry job');
}

export async function exportJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/dubbing/jobs/${jobId}/export`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to initiate export');
}

export function getDownloadUrl(jobId: string): string {
  return `${API_BASE}/dubbing/jobs/${jobId}/download`;
}
