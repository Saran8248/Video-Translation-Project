export interface VideoAsset {
  id: string;
  duration_ms: number;
  metadata: {
    duration_ms?: number;
    has_video?: boolean;
    has_audio?: boolean;
    video_codec?: string;
    audio_codec?: string;
    width?: number;
    height?: number;
    fps?: number;
    audio_sample_rate?: number;
    audio_channels?: number;
    file_size?: number;
  };
  status: string;
  created_at: string;
}

export interface DubbingJob {
  id: string;
  video_asset_id: string;
  source_language: string;
  target_language: string;
  mode: 'single_speaker' | 'multi_speaker';
  preserve_background_audio: boolean;
  register: 'conversational' | 'formal';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  current_stage: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
  export_url?: string;
}

export interface AudioSegmentOut {
  id: string;
  storage_key: string;
  duration_ms: number;
  speed_factor: number;
  audio_url?: string;
}

export interface SegmentItem {
  id: string;
  segment_id: string;
  job_id: string;
  speaker_id: string;
  start_ms: number;
  end_ms: number;
  source_text: string;
  confidence: number;
  source_language: string;
  target_language?: string;
  translated_text?: string;
  edited_by_user: boolean;
  audio_segment?: AudioSegmentOut;
}

export interface VoiceOption {
  id: string;
  name: string;
  gender: string;
  locale: string;
  language: string;
  provider: string;
}

export interface CreateJobPayload {
  video_asset_id: string;
  source_language: string;
  target_language: string;
  mode: 'single_speaker' | 'multi_speaker';
  preserve_background_audio: boolean;
  voice_mapping: Record<string, string>;
  register: 'conversational' | 'formal';
}
