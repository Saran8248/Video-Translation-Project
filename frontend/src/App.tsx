import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { UploadSection } from './components/UploadSection';
import { JobConfig } from './components/JobConfig';
import { ProgressTracker } from './components/ProgressTracker';
import { SegmentEditor } from './components/SegmentEditor';
import { VideoPlayerPreview } from './components/VideoPlayerPreview';
import { VideoAsset, DubbingJob, SegmentItem, CreateJobPayload } from './types';
import { createDubbingJob, fetchJobStatus, fetchJobSegments, retryJob } from './api';

export const App: React.FC = () => {
  const [asset, setAsset] = useState<VideoAsset | null>(null);
  const [job, setJob] = useState<DubbingJob | null>(null);
  const [segments, setSegments] = useState<SegmentItem[]>([]);
  const [isStartingJob, setIsStartingJob] = useState(false);
  const [activeSegmentId, setActiveSegmentId] = useState<string | undefined>(undefined);
  
  const pollTimerRef = useRef<any>(null);

  // Poll job status
  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed') {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      return;
    }

    pollTimerRef.current = setInterval(async () => {
      try {
        const updated = await fetchJobStatus(job.id);
        setJob(updated);

        // Fetch segments if past transcription stage (progress >= 35%)
        if (updated.progress >= 35) {
          const segs = await fetchJobSegments(job.id);
          setSegments(segs);
        }

        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(pollTimerRef.current);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 1500);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [job?.id, job?.status]);

  const handleStartJob = async (payload: CreateJobPayload) => {
    try {
      setIsStartingJob(true);
      const res = await createDubbingJob(payload);
      const initialJob = await fetchJobStatus(res.id);
      setJob(initialJob);
      setSegments([]);
    } catch (err: any) {
      alert(err.message || 'Failed to start job');
    } finally {
      setIsStartingJob(false);
    }
  };

  const handleRetry = async () => {
    if (!job) return;
    try {
      await retryJob(job.id);
      const updated = await fetchJobStatus(job.id);
      setJob(updated);
    } catch (err: any) {
      alert(err.message || 'Retry failed');
    }
  };

  const handleRefreshSegments = async () => {
    if (!job) return;
    try {
      const segs = await fetchJobSegments(job.id);
      setSegments(segs);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTimeUpdate = (curMs: number) => {
    const active = segments.find((s) => curMs >= s.start_ms && curMs <= s.end_ms);
    setActiveSegmentId(active?.id);
  };

  const isJobRunning = job?.status === 'pending' || job?.status === 'processing';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Step 1 & 2: Upload and Configuration */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5">
            <UploadSection
              asset={asset}
              onAssetReady={(newAsset) => {
                setAsset(newAsset);
                setJob(null);
                setSegments([]);
              }}
              disabled={isJobRunning}
            />
          </div>

          <div className="lg:col-span-7">
            {asset ? (
              <JobConfig
                assetId={asset.id}
                onStartJob={handleStartJob}
                isStarting={isStartingJob}
                disabled={isJobRunning}
              />
            ) : (
              <div className="h-full min-h-[220px] rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6 flex flex-col items-center justify-center text-center text-slate-500">
                <p className="text-sm">Upload a video or generate a German interview clip to configure dubbing options.</p>
              </div>
            )}
          </div>
        </div>

        {/* Progress Tracker */}
        {job && (
          <ProgressTracker job={job} onRetry={handleRetry} />
        )}

        {/* Player and Segment Editor */}
        {(job || asset) && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-6">
              <VideoPlayerPreview
                job={job}
                asset={asset}
                segments={segments}
                onTimeUpdate={handleTimeUpdate}
              />
            </div>

            <div className="lg:col-span-6">
              {job ? (
                <SegmentEditor
                  jobId={job.id}
                  segments={segments}
                  onRefresh={handleRefreshSegments}
                  onSelectSegment={(seg) => setActiveSegmentId(seg.id)}
                  activeSegmentId={activeSegmentId}
                />
              ) : (
                <div className="h-full min-h-[300px] rounded-2xl border border-slate-800 bg-slate-900/40 p-6 flex flex-col items-center justify-center text-center text-slate-500 text-xs">
                  Start dubbing to view and edit transcribed speech and Tamil dialogue segments.
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-400">
        AI Video Dubbing Architecture • Built according to TranslateMom Blueprint Specifications
      </footer>
    </div>
  );
};

export default App;
