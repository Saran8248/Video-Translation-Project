import React from 'react';
import { Languages, Sparkles, Volume2, Film } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-white tracking-tight">AI Video Dubbing</span>
              <span className="bg-sky-500/20 text-sky-400 text-xs px-2 py-0.5 rounded-full font-medium border border-sky-500/30">
                Tamil & Multilingual
              </span>
            </div>
            <p className="text-xs text-slate-400">German → Spoken Tamil | All Other Languages → English</p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-400">
          <div className="hidden sm:flex items-center gap-1.5 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60">
            <Languages className="w-3.5 h-3.5 text-sky-400" />
            <span>Target: <strong className="text-slate-200">DE → Tamil | Other → English</strong></span>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60">
            <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Neural TTS: <strong className="text-slate-200">Edge-TTS / Azure</strong></span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>API Online</span>
          </div>
        </div>
      </div>
    </header>
  );
};
