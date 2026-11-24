import React, { useState } from 'react';
import { Play, Pause, Save, Check, RefreshCw, Volume2, User, Clock, Edit3, Sparkles } from 'lucide-react';
import { SegmentItem } from '../types';
import { updateSegment, exportJob } from '../api';

interface SegmentEditorProps {
  jobId: string;
  segments: SegmentItem[];
  onRefresh: () => void;
  onSelectSegment?: (segment: SegmentItem) => void;
  activeSegmentId?: string;
}

export const SegmentEditor: React.FC<SegmentEditorProps> = ({
  jobId,
  segments,
  onRefresh,
  onSelectSegment,
  activeSegmentId,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const [audioElem, setAudioElem] = useState<HTMLAudioElement | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const startEdit = (seg: SegmentItem) => {
    setEditingId(seg.id);
    setEditText(seg.translated_text || '');
  };

  const saveEdit = async (seg: SegmentItem) => {
    try {
      setIsSaving(true);
      await updateSegment(jobId, seg.id, {
        translated_text: editText,
      });
      setEditingId(null);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to update segment');
    } finally {
      setIsSaving(false);
    }
  };

  const togglePlayAudio = (seg: SegmentItem) => {
    if (!seg.audio_segment?.audio_url) return;

    if (playingAudioId === seg.id && audioElem) {
      audioElem.pause();
      setPlayingAudioId(null);
      return;
    }

    if (audioElem) {
      audioElem.pause();
    }

    const audio = new Audio(seg.audio_segment.audio_url);
    audio.play();
    setAudioElem(audio);
    setPlayingAudioId(seg.id);

    audio.onended = () => {
      setPlayingAudioId(null);
    };
  };

  const handleReExport = async () => {
    try {
      setIsExporting(true);
      await exportJob(jobId);
      alert('Re-render initiated! The updated audio and timing will be muxed into the video.');
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  const formatMs = (ms: number) => {
    const totalSec = ms / 1000;
    const mins = Math.floor(totalSec / 60);
    const secs = (totalSec % 60).toFixed(2);
    return `${mins}:${secs.padStart(5, '0')}`;
  };

  return (
    <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-5">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Edit3 className="w-5 h-5 text-sky-400" />
            3. Segment Review & Spoken Tamil Editor
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Review timed dialogue, listen to synthesized Tamil speech, or refine text and timing.
          </p>
        </div>

        <button
          onClick={handleReExport}
          disabled={isExporting}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white shadow-md shadow-emerald-500/20 disabled:opacity-50 transition-all cursor-pointer"
        >
          {isExporting ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4 text-emerald-200" />
          )}
          Re-render & Export Dubbed Video
        </button>
      </div>

      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
        {segments.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500">
            No segments yet. Start the dubbing pipeline to generate transcript and translations.
          </div>
        ) : (
          segments.map((seg, idx) => {
            const isEditing = editingId === seg.id;
            const isPlaying = playingAudioId === seg.id;
            const isSelected = activeSegmentId === seg.id;

            return (
              <div
                key={seg.id}
                onClick={() => onSelectSegment && onSelectSegment(seg)}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-sky-950/40 border-sky-500/60 ring-1 ring-sky-500/30'
                    : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-mono text-slate-400 font-semibold">#{idx + 1}</span>
                    <span className="flex items-center gap-1 font-mono bg-slate-900 px-2 py-0.5 rounded text-sky-400 border border-slate-800">
                      <Clock className="w-3 h-3" />
                      {formatMs(seg.start_ms)} → {formatMs(seg.end_ms)}
                    </span>
                    <span
                      className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium ${
                        seg.speaker_id === 'speaker_1'
                          ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                          : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                      }`}
                    >
                      <User className="w-3 h-3" />
                      {seg.speaker_id}
                    </span>
                    {/* Multilingual Routing Badge */}
                    <span
                      className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${
                        seg.source_language.toLowerCase().includes('de')
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40'
                          : seg.source_language.toLowerCase().includes('en')
                          ? 'bg-sky-950/60 text-sky-300 border-sky-500/40'
                          : 'bg-purple-950/60 text-purple-300 border-purple-500/40'
                      }`}
                    >
                      {seg.source_language.toUpperCase()} → {(seg.target_language || (seg.source_language === 'de' ? 'ta-IN' : 'en-US')).substring(0, 2).toUpperCase()}
                    </span>
                    {seg.edited_by_user && (
                      <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded">
                        Edited
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {seg.audio_segment?.audio_url && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          togglePlayAudio(seg);
                        }}
                        className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg border transition-all ${
                          isPlaying
                            ? 'bg-emerald-500 text-white border-emerald-400 shadow-sm'
                            : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-600'
                        }`}
                      >
                        {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                        <span>{isPlaying ? 'Playing' : 'Listen'}</span>
                      </button>
                    )}

                    {!isEditing ? (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          startEdit(seg);
                        }}
                        className="text-xs text-sky-400 hover:text-sky-300 p-1"
                      >
                        Edit
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          saveEdit(seg);
                        }}
                        disabled={isSaving}
                        className="flex items-center gap-1 text-xs bg-sky-500 text-white px-2 py-1 rounded-lg font-medium hover:bg-sky-600"
                      >
                        <Check className="w-3 h-3" />
                        Save
                      </button>
                    )}
                  </div>
                </div>

                {/* Source Original Text */}
                <div className="text-xs text-slate-400 mb-2 pl-2 border-l-2 border-slate-700">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-0.5">
                    Original ({seg.source_language.toUpperCase()}):
                  </span>
                  <span className="font-sans text-slate-300">{seg.source_text}</span>
                </div>

                {/* Target Translated Text */}
                <div className={`text-sm pl-2 border-l-2 ${seg.target_language?.includes('en') ? 'border-sky-400' : 'border-emerald-400'}`}>
                  <span className={`text-[10px] uppercase font-bold tracking-wider block mb-0.5 ${seg.target_language?.includes('en') ? 'text-sky-400' : 'text-emerald-400'}`}>
                    {seg.target_language?.includes('en') ? 'English Dialogue (Dubbed / Preserved):' : 'Spoken Tamil Dubbed Dialogue:'}
                  </span>
                  {isEditing ? (
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      rows={2}
                      className="w-full bg-slate-900 border border-sky-500 rounded-lg p-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                    />
                  ) : (
                    <p className="text-slate-100 font-medium leading-relaxed">
                      {seg.translated_text || '—'}
                    </p>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
