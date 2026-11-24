import React from 'react';
import { CheckCircle2, Clock, AlertCircle, RefreshCw, Loader2, Sparkles } from 'lucide-react';
import { DubbingJob } from '../types';

interface ProgressTrackerProps {
  job: DubbingJob;
  onRetry: () => void;
}

const STAGES = [
  { id: 'extract', name: 'Inspect & Extract', min: 10, max: 20 },
  { id: 'transcribe', name: 'Transcribe & Diarize', min: 20, max: 40 },
  { id: 'translate', name: 'Spoken Tamil Translation', min: 40, max: 55 },
  { id: 'tts', name: 'Neural TTS Synthesis', min: 55, max: 80 },
  { id: 'sync', name: 'Timing Alignment & Muxing', min: 80, max: 95 },
  { id: 'export', name: 'Validate & Final Export', min: 95, max: 100 },
];

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({ job, onRetry }) => {
  const isFailed = job.status === 'failed';
  const isDone = job.status === 'completed';

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white">Pipeline Progress:</span>
            <span className="text-xs font-mono bg-sky-500/20 text-sky-300 px-2.5 py-0.5 rounded-full border border-sky-500/30 font-medium">
              Task #{job.id}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Current Stage: <strong className="text-sky-300">{job.current_stage || 'Processing'}</strong>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-2xl font-bold font-mono text-white">
            {job.progress}%
          </span>
          {isFailed && (
            <button
              onClick={onRetry}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/20 text-rose-300 border border-rose-500/30 hover:bg-rose-500/30 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry Stage
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-950 rounded-full h-3 p-0.5 overflow-hidden border border-slate-800 mb-6">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isFailed
              ? 'bg-rose-500'
              : isDone
              ? 'bg-emerald-500'
              : 'bg-gradient-to-r from-sky-500 via-indigo-500 to-emerald-400'
          }`}
          style={{ width: `${Math.max(4, job.progress)}%` }}
        ></div>
      </div>

      {/* Stage Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {STAGES.map((stg) => {
          const completed = job.progress >= stg.max || isDone;
          const active = job.progress >= stg.min && job.progress < stg.max;

          return (
            <div
              key={stg.id}
              className={`p-2.5 rounded-xl border transition-all text-xs ${
                completed
                  ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
                  : active
                  ? 'bg-sky-950/30 border-sky-500/40 text-sky-200 ring-1 ring-sky-500/20'
                  : 'bg-slate-950/40 border-slate-800/80 text-slate-500'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] text-slate-400">{stg.min}-{stg.max}%</span>
                {completed ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : active ? (
                  <Loader2 className="w-3.5 h-3.5 text-sky-400 animate-spin" />
                ) : (
                  <Clock className="w-3.5 h-3.5 text-slate-600" />
                )}
              </div>
              <span className="font-medium block leading-tight">{stg.name}</span>
            </div>
          );
        })}
      </div>

      {isFailed && job.error_message && (
        <div className="mt-4 p-3 rounded-xl bg-rose-950/30 border border-rose-800/50 flex items-start gap-2.5 text-xs text-rose-300">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <strong className="block text-rose-200 font-semibold mb-0.5">Stage Execution Failed:</strong>
            {job.error_message}
          </div>
        </div>
      )}
    </div>
  );
};
