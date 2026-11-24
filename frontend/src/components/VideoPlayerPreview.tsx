import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, Download, Volume2, Film, CheckCircle, ExternalLink } from 'lucide-react';
import { DubbingJob, VideoAsset, SegmentItem } from '../types';
import { getDownloadUrl } from '../api';

interface VideoPlayerPreviewProps {
  job: DubbingJob | null;
  asset: VideoAsset | null;
  segments: SegmentItem[];
  onTimeUpdate?: (currentTimeMs: number) => void;
}

export const VideoPlayerPreview: React.FC<VideoPlayerPreviewProps> = ({
  job,
  asset,
  segments,
  onTimeUpdate,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeTrack, setActiveTrack] = useState<'dubbed' | 'original'>('dubbed');
  const [currentCaption, setCurrentCaption] = useState<string>('');

  const isDubbedReady = job && job.status === 'completed';
  const originalUrl = asset ? `/api/v1/videos/${asset.id}/stream` : '';
  const dubbedUrl = job ? `/api/v1/dubbing/jobs/${job.id}/stream-export` : '';

  // Determine current video source
  const videoSrc = activeTrack === 'dubbed' && isDubbedReady ? dubbedUrl : originalUrl;

  const handleTime = () => {
    if (!videoRef.current) return;
    const curMs = videoRef.current.currentTime * 1000;
    if (onTimeUpdate) onTimeUpdate(curMs);

    // Find active segment for synchronized subtitle display
    const activeSeg = segments.find((s) => curMs >= s.start_ms && curMs <= s.end_ms);
    if (activeSeg) {
      setCurrentCaption(
        activeTrack === 'dubbed' && activeSeg.translated_text
          ? activeSeg.translated_text
          : activeSeg.source_text
      );
    } else {
      setCurrentCaption('');
    }
  };

  return (
    <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Film className="w-5 h-5 text-sky-400" />
            4. Player & Synchronized Dub Preview
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Compare original German audio with translated Tamil dubbed output.
          </p>
        </div>

        {/* Audio Track Selector */}
        <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
          <button
            type="button"
            onClick={() => setActiveTrack('dubbed')}
            disabled={!isDubbedReady}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTrack === 'dubbed' && isDubbedReady
                ? 'bg-sky-500 text-white font-semibold shadow-sm'
                : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
            }`}
          >
            Tamil Dubbed Audio
          </button>
          <button
            type="button"
            onClick={() => setActiveTrack('original')}
            disabled={!asset}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTrack === 'original'
                ? 'bg-slate-800 text-white font-semibold'
                : 'text-slate-400 hover:text-slate-200 disabled:opacity-40'
            }`}
          >
            Original Audio
          </button>
        </div>
      </div>

      {/* Video Container */}
      <div className="relative aspect-video rounded-xl overflow-hidden bg-black border border-slate-800/80 group flex items-center justify-center">
        {videoSrc ? (
          <>
            <video
              ref={videoRef}
              src={videoSrc}
              controls
              onTimeUpdate={handleTime}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              className="w-full h-full object-contain"
            />
            {/* Live Subtitle Overlay */}
            {currentCaption && (
              <div className="absolute bottom-14 left-1/2 -translate-x-1/2 max-w-[90%] bg-black/80 backdrop-blur-sm text-white px-4 py-2 rounded-lg text-center text-sm font-medium shadow-lg pointer-events-none transition-all">
                {currentCaption}
              </div>
            )}
          </>
        ) : (
          <div className="text-center p-6 text-slate-500 text-xs">
            Upload or generate a video to preview playback.
          </div>
        )}
      </div>

      {/* Export / Download Bar */}
      {isDubbedReady && (
        <div className="mt-5 p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 to-teal-950/40 border border-emerald-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <CheckCircle className="w-5 h-5" />
            </div>
            <div>
              <span className="text-sm font-semibold text-emerald-200 block">
                Dubbing Successfully Rendered
              </span>
              <span className="text-xs text-slate-400">
                MP4 • H.264 Video • AAC Audio • Tamil (ta-IN)
              </span>
            </div>
          </div>

          <a
            href={getDownloadUrl(job.id)}
            download={`dubbed_${job.id}.mp4`}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-xs bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/20 transition-all cursor-pointer"
          >
            <Download className="w-4 h-4" />
            Download Dubbed MP4
          </a>
        </div>
      )}
    </div>
  );
};
