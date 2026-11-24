import React, { useState, useEffect } from 'react';
import { Sliders, Volume2, Mic, Users, Music, ArrowRight, Loader2, BookOpen, Globe2, Sparkles, CheckCircle2 } from 'lucide-react';
import { VoiceOption, CreateJobPayload } from '../types';
import { fetchVoices } from '../api';

interface JobConfigProps {
  assetId: string;
  onStartJob: (payload: CreateJobPayload) => Promise<void>;
  isStarting: boolean;
  disabled?: boolean;
}

export const JobConfig: React.FC<JobConfigProps> = ({ assetId, onStartJob, isStarting, disabled }) => {
  const [sourceLang, setSourceLang] = useState('auto');
  const [targetLang, setTargetLang] = useState('ta-IN');
  const [mode, setMode] = useState<'single_speaker' | 'multi_speaker'>('multi_speaker');
  const [register, setRegister] = useState<'conversational' | 'formal'>('conversational');
  const [preserveBg, setPreserveBg] = useState(true);

  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [spk1Voice, setSpk1Voice] = useState('ta-IN-ValluvarNeural');
  const [spk2Voice, setSpk2Voice] = useState('ta-IN-PallaviNeural');

  useEffect(() => {
    fetchVoices().then((v) => {
      setVoices(v);
      if (v.length > 0) {
        const male = v.find((x) => x.id === 'ta-IN-ValluvarNeural') || v.find((x) => x.gender === 'male' && x.locale.includes('ta'));
        const female = v.find((x) => x.id === 'ta-IN-PallaviNeural') || v.find((x) => x.gender === 'female' && x.locale.includes('ta'));
        if (male) setSpk1Voice(male.id);
        if (female) setSpk2Voice(female.id);
      }
    }).catch(console.error);
  }, []);

  const handleStart = () => {
    onStartJob({
      video_asset_id: assetId,
      source_language: sourceLang,
      target_language: targetLang,
      mode: mode,
      preserve_background_audio: preserveBg,
      register: register,
      voice_mapping: {
        speaker_1: spk1Voice,
        ...(mode === 'multi_speaker' ? { speaker_2: spk2Voice } : {}),
      },
    });
  };

  return (
    <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-xl">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Sliders className="w-5 h-5 text-sky-400" />
          2. Dubbing Configuration & Language Routing
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Auto-detects languages per sentence: German becomes Spoken Tamil; English is preserved; French/Spanish become English.
        </p>
      </div>

      {/* Multilingual Routing Information Banner */}
      <div className="mb-5 p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-300">
        <span className="font-semibold text-sky-400 flex items-center gap-1.5 mb-1.5">
          <Globe2 className="w-3.5 h-3.5" />
          Intelligent Language Routing Rules:
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2">
          <div className="bg-emerald-950/30 border border-emerald-500/30 p-2 rounded-lg">
            <span className="font-bold text-emerald-300 block mb-0.5">German (DE)</span>
            <span className="text-slate-400">→ Natural Spoken Tamil (ta-IN)</span>
          </div>
          <div className="bg-sky-950/30 border border-sky-500/30 p-2 rounded-lg">
            <span className="font-bold text-sky-300 block mb-0.5">English (EN)</span>
            <span className="text-slate-400">→ Kept in English (en-US)</span>
          </div>
          <div className="bg-indigo-950/30 border border-indigo-500/30 p-2 rounded-lg">
            <span className="font-bold text-indigo-300 block mb-0.5">French / Spanish (FR/ES)</span>
            <span className="text-slate-400">→ Converted to English (en-US)</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Source Language & Tamil Register */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Audio Language Mode
            </label>
            <select
              value={sourceLang}
              onChange={(e) => setSourceLang(e.target.value)}
              disabled={disabled}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="auto">Auto-detect per sentence (Recommended)</option>
              <option value="de">German (Deutsch - de)</option>
              <option value="en">English (English - en)</option>
              <option value="fr">French (Français - fr)</option>
              <option value="es">Spanish (Español - es)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-emerald-400" />
              Tamil Register Style
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRegister('conversational')}
                className={`py-2 px-3 rounded-xl text-xs font-medium border text-center transition-all ${
                  register === 'conversational'
                    ? 'border-emerald-500 bg-emerald-500/10 text-emerald-300 font-semibold'
                    : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                Conversational (பேச்சு)
              </button>
              <button
                type="button"
                onClick={() => setRegister('formal')}
                className={`py-2 px-3 rounded-xl text-xs font-medium border text-center transition-all ${
                  register === 'formal'
                    ? 'border-emerald-500 bg-emerald-500/10 text-emerald-300 font-semibold'
                    : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                Formal (எழுத்து)
              </button>
            </div>
          </div>
        </div>

        {/* Diarization & Mode */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <Users className="w-4 h-4 text-sky-400" />
              Dubbing Mode (Diarization)
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setMode('single_speaker')}
                className={`py-2 px-3 rounded-xl text-xs font-medium border text-center transition-all ${
                  mode === 'single_speaker'
                    ? 'border-sky-500 bg-sky-500/10 text-sky-300 font-semibold'
                    : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                Single Voice-over
              </button>
              <button
                type="button"
                onClick={() => setMode('multi_speaker')}
                className={`py-2 px-3 rounded-xl text-xs font-medium border text-center transition-all ${
                  mode === 'multi_speaker'
                    ? 'border-sky-500 bg-sky-500/10 text-sky-300 font-semibold'
                    : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:text-slate-200'
                }`}
              >
                Multi-Speaker (AI)
              </button>
            </div>
          </div>

          <div className="pt-1">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={preserveBg}
                onChange={(e) => setPreserveBg(e.target.checked)}
                className="w-4 h-4 rounded text-sky-500 bg-slate-950 border-slate-700 focus:ring-0 focus:ring-offset-0"
              />
              <span className="text-xs text-slate-300 font-medium flex items-center gap-1">
                <Music className="w-3.5 h-3.5 text-sky-400" />
                Sidechain Audio Ducking (Retains Music & Ambience)
              </span>
            </label>
          </div>
        </div>

        {/* Speaker Voice Selection */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <Mic className="w-4 h-4 text-indigo-400" />
              Speaker 1 (Male: Tamil + English)
            </label>
            <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-xs space-y-1">
              <div className="text-slate-300 flex items-center justify-between">
                <span>Tamil Voice:</span>
                <span className="font-mono text-emerald-400 font-medium">Valluvar (ta-IN Male)</span>
              </div>
              <div className="text-slate-300 flex items-center justify-between">
                <span>English Voice:</span>
                <span className="font-mono text-sky-400 font-medium">Guy (en-US Male)</span>
              </div>
            </div>
          </div>

          {mode === 'multi_speaker' && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Mic className="w-4 h-4 text-purple-400" />
                Speaker 2 (Female: Tamil + English)
              </label>
              <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-xs space-y-1">
                <div className="text-slate-300 flex items-center justify-between">
                  <span>Tamil Voice:</span>
                  <span className="font-mono text-emerald-400 font-medium">Pallavi (ta-IN Female)</span>
                </div>
                <div className="text-slate-300 flex items-center justify-between">
                  <span>English Voice:</span>
                  <span className="font-mono text-sky-400 font-medium">Jenny (en-US Female)</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-slate-800 flex justify-end">
        <button
          type="button"
          onClick={handleStart}
          disabled={disabled || isStarting}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-600 hover:to-indigo-700 text-white shadow-lg shadow-sky-500/25 disabled:opacity-50 transition-all cursor-pointer"
        >
          {isStarting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Initializing Task...
            </>
          ) : (
            <>
              Start Multilingual AI Dubbing Pipeline
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
