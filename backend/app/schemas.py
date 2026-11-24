from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class UploadSessionRequest(BaseModel):
    filename: str
    file_size: Optional[int] = None
    content_type: Optional[str] = "video/mp4"

class UploadSessionResponse(BaseModel):
    video_asset_id: str
    upload_url: str
    storage_key: str

class VideoAssetResponse(BaseModel):
    id: str
    duration_ms: int
    metadata: Dict[str, Any]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VoiceMapping(BaseModel):
    speaker_1: Optional[str] = "ta-IN-ValluvarNeural"
    speaker_2: Optional[str] = "ta-IN-PallaviNeural"

class CreateJobRequest(BaseModel):
    video_asset_id: str
    source_language: str = "de"
    target_language: str = "ta-IN"
    mode: str = "single_speaker"  # single_speaker, multi_speaker
    preserve_background_audio: bool = True
    voice_mapping: Optional[Dict[str, str]] = None
    speech_register: Optional[str] = Field("conversational", alias="register")

    model_config = ConfigDict(populate_by_name=True)

class JobStatusResponse(BaseModel):
    id: str
    video_asset_id: str
    source_language: str
    target_language: str
    mode: str
    preserve_background_audio: bool
    speech_register: str = Field("conversational", alias="register")
    status: str
    progress: int
    current_stage: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    export_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class TranslatedSegmentOut(BaseModel):
    id: str
    translated_text: str
    edited_by_user: bool
    target_language: str

    model_config = ConfigDict(from_attributes=True)

class AudioSegmentOut(BaseModel):
    id: str
    storage_key: str
    duration_ms: int
    speed_factor: float
    audio_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SegmentItem(BaseModel):
    id: str
    segment_id: str
    job_id: str
    speaker_id: str
    start_ms: int
    end_ms: int
    source_text: str
    confidence: float
    source_language: str
    target_language: Optional[str] = "ta-IN"
    translated_text: Optional[str] = None
    edited_by_user: bool = False
    audio_segment: Optional[AudioSegmentOut] = None

    model_config = ConfigDict(from_attributes=True)

class SegmentListResponse(BaseModel):
    job_id: str
    segments: List[SegmentItem]

class SegmentUpdate(BaseModel):
    translated_text: Optional[str] = None
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    speaker_id: Optional[str] = None

class VoiceOption(BaseModel):
    id: str
    name: str
    gender: str
    locale: str
    language: str
    provider: str

class ExportResponse(BaseModel):
    job_id: str
    export_id: str
    storage_key: str
    format: str
    download_url: str
    duration_ms: int
