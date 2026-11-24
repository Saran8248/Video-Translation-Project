import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, 
    ForeignKey, Text, DateTime, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from .config import DATABASE_URL

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, default="demo@videotranslate.ai")
    auth_provider_id = Column(String(255), nullable=True, default="local")
    created_at = Column(DateTime, default=datetime.utcnow)

    videos = relationship("VideoAsset", back_populates="user")
    usage_entries = relationship("UsageLedger", back_populates="user")

class VideoAsset(Base):
    __tablename__ = "video_assets"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    storage_key = Column(String(500), nullable=False)
    duration_ms = Column(Integer, default=0)
    meta_info = Column(JSON, default=dict)  # codecs, resolution, fps, etc.
    status = Column(String(50), default="uploaded")  # uploaded, inspecting, ready, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="videos")
    dubbing_jobs = relationship("DubbingJob", back_populates="video_asset")

class DubbingJob(Base):
    __tablename__ = "dubbing_jobs"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_asset_id = Column(String(36), ForeignKey("video_assets.id"), nullable=False)
    source_language = Column(String(20), default="de")
    target_language = Column(String(20), default="ta-IN")
    mode = Column(String(50), default="single_speaker")  # single_speaker, multi_speaker
    preserve_background_audio = Column(Boolean, default=True)
    register = Column(String(50), default="conversational")  # conversational, formal
    status = Column(String(50), default="pending")  # pending, extracting, transcribing, translating, synthesizing, mixing, completed, failed
    progress = Column(Integer, default=0)
    current_stage = Column(String(100), default="Upload")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    video_asset = relationship("VideoAsset", back_populates="dubbing_jobs")
    speakers = relationship("Speaker", back_populates="job", cascade="all, delete-orphan")
    speech_segments = relationship("SpeechSegment", back_populates="job", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="job", cascade="all, delete-orphan")

class Speaker(Base):
    __tablename__ = "speakers"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("dubbing_jobs.id"), nullable=False)
    speaker_label = Column(String(50), nullable=False)  # speaker_1, speaker_2
    voice_provider = Column(String(50), default="edge_tts")
    voice_id = Column(String(100), nullable=False)
    gender = Column(String(20), default="male")

    job = relationship("DubbingJob", back_populates="speakers")

class SpeechSegment(Base):
    __tablename__ = "speech_segments"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("dubbing_jobs.id"), nullable=False)
    speaker_id = Column(String(50), default="speaker_1")
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    source_text = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)
    source_language = Column(String(20), default="de")

    job = relationship("DubbingJob", back_populates="speech_segments")
    translated_segment = relationship("TranslatedSegment", back_populates="speech_segment", uselist=False, cascade="all, delete-orphan")

class TranslatedSegment(Base):
    __tablename__ = "translated_segments"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    speech_segment_id = Column(String(36), ForeignKey("speech_segments.id"), nullable=False)
    translated_text = Column(Text, nullable=False)
    edited_by_user = Column(Boolean, default=False)
    target_language = Column(String(20), default="ta-IN")

    speech_segment = relationship("SpeechSegment", back_populates="translated_segment")
    audio_segment = relationship("AudioSegment", back_populates="translated_segment", uselist=False, cascade="all, delete-orphan")

class AudioSegment(Base):
    __tablename__ = "audio_segments"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    translated_segment_id = Column(String(36), ForeignKey("translated_segments.id"), nullable=False)
    storage_key = Column(String(500), nullable=False)
    duration_ms = Column(Integer, default=0)
    provider_request_id = Column(String(100), nullable=True)
    speed_factor = Column(Float, default=1.0)

    translated_segment = relationship("TranslatedSegment", back_populates="audio_segment")

class Export(Base):
    __tablename__ = "exports"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("dubbing_jobs.id"), nullable=False)
    storage_key = Column(String(500), nullable=False)
    format = Column(String(20), default="mp4")
    duration_ms = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("DubbingJob", back_populates="exports")

class UsageLedger(Base):
    __tablename__ = "usage_ledger"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    job_id = Column(String(36), ForeignKey("dubbing_jobs.id"), nullable=True)
    units = Column(Float, default=0.0)  # minutes, chars, or requests
    event_type = Column(String(50), nullable=False)  # transcription, translation, tts, export
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="usage_entries")

def init_db():
    Base.metadata.create_all(bind=engine)
    # Ensure default user exists
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            default_user = User(
                id="user_default_01",
                email="admin@videotranslate.ai",
                auth_provider_id="local"
            )
            db.add(default_user)
            db.commit()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
