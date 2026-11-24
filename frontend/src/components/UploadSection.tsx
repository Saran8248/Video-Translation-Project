import React, { useRef, useState } from 'react';
import { Upload, FileVideo, Sparkles, Loader2, CheckCircle2, Globe } from 'lucide-react';
import { VideoAsset } from '../types';
import { uploadVideo, generateSampleVideo, generateMultilingualSampleVideo } from '../api';

interface UploadSectionProps {
  asset: VideoAsset | null;
  onAssetReady: (asset: VideoAsset) => void;
  disabled?: boolean;
}

export const UploadSection: React.FC<UploadSectionProps> = ({ asset, onAssetReady, disabled }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGeneratingMulti, setIsGeneratingMulti] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.type.includes('video') && !file.name.match(/\.(mp4|mov|webm|mkv)$/i)) {
      alert('Please select a valid video file (MP4, WebM, MOV)');
      return;
    }
    try {
      setIsUploading(true);
      const res = await uploadVideo(file);
      onAssetReady(res);
    } catch (err: any) {
      alert(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleSample = async () => {
    try {
      setIsGenerating(true);
      const res = await generateSampleVideo();
      onAssetReady(res);
    } catch (err: any) {
      alert(err.message || 'Failed to generate sample');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleMultilingualSample = async () => {
    try {
      setIsGeneratingMulti(true);
      const res = await generateMultilingualSampleVideo();
      onAssetReady(res);
    } catch (err: any) {
      alert(err.message || 'Failed to generate multilingual sample');
    } finally {
      setIsGeneratingMulti(false);
    }
  };

  return (
    <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-5">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Upload className="w-5 h-5 text-sky-400" />
            1. Video Upload & Media Inspection
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Upload an MP4 video or generate a realistic German interview clip to dub.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleSample}
            disabled={disabled || isUploading || isGenerating || isGeneratingMulti}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-500 to-sky-500 hover:from-indigo-600 hover:to-sky-600 text-white shadow-md shadow-indigo-500/20 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Synthesizing...
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-sky-200" />
                German Slang Clip
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleMultilingualSample}
            disabled={disabled || isUploading || isGenerating || isGeneratingMulti}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white shadow-md shadow-purple-500/20 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isGeneratingMulti ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Synthesizing...
              </>
            ) : (
              <>
                <Globe className="w-3.5 h-3.5 text-pink-200" />
                Multilingual (DE+EN+FR)
              </>
            )}
          </button>
        </div>
      </div>

      {!asset ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
          }}
          onClick={() => !disabled && fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
            dragActive
              ? 'border-sky-500 bg-sky-500/10'
              : 'border-slate-700 hover:border-slate-600 bg-slate-950/40'
          } ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/webm,video/quicktime"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <div className="flex flex-col items-center justify-center gap-3">
            <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400">
              {isUploading ? <Loader2 className="w-6 h-6 animate-spin text-sky-400" /> : <FileVideo className="w-6 h-6" />}
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                {isUploading ? 'Uploading & Inspecting Video...' : 'Drop video here or click to browse'}
              </p>
              <p className="text-xs text-slate-500 mt-1">MP4, MOV or WebM (up to 2 hours supported)</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-950/60 rounded-xl border border-slate-800/80 p-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/60">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-sm font-medium text-slate-200">Video Asset Ready</span>
              <span className="text-xs font-mono bg-slate-800 px-2 py-0.5 rounded text-slate-400">{asset.id}</span>
            </div>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              className="text-xs text-sky-400 hover:text-sky-300 font-medium"
            >
              Replace Video
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/webm,video/quicktime"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3 text-xs">
            <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
              <span className="text-slate-400 block mb-0.5">Duration</span>
              <span className="text-slate-200 font-semibold font-mono">
                {(asset.duration_ms / 1000).toFixed(1)}s ({(asset.duration_ms / 60000).toFixed(1)}m)
              </span>
            </div>
            <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
              <span className="text-slate-400 block mb-0.5">Resolution</span>
              <span className="text-slate-200 font-semibold font-mono">
                {asset.metadata?.width || 1280}x{asset.metadata?.height || 720}
              </span>
            </div>
            <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
              <span className="text-slate-400 block mb-0.5">Codecs</span>
              <span className="text-slate-200 font-semibold font-mono">
                {asset.metadata?.video_codec || 'h264'} / {asset.metadata?.audio_codec || 'aac'}
              </span>
            </div>
            <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
              <span className="text-slate-400 block mb-0.5">Audio Channels</span>
              <span className="text-slate-200 font-semibold font-mono">
                {asset.metadata?.audio_channels || 2} ch ({asset.metadata?.audio_sample_rate || 44100} Hz)
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
