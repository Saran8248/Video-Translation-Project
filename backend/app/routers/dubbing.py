import os
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from ..database import (
    get_db, DubbingJob, VideoAsset, Speaker, 
    SpeechSegment, TranslatedSegment, AudioSegment, Export
)
from ..schemas import (
    CreateJobRequest, JobStatusResponse, SegmentListResponse, 
    SegmentItem, SegmentUpdate, ExportResponse, AudioSegmentOut
)
from ..config import DEFAULT_TAMIL_VOICES
from ..services.pipeline import pipeline_worker

router = APIRouter(prefix="/api/v1/dubbing", tags=["dubbing"])

@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
def create_dubbing_job(
    req: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Creates a new dubbing job with language, mode, voice mapping, and register settings.
    Returns HTTP 202 Accepted with job ID.
    """
    video_asset = db.query(VideoAsset).filter(VideoAsset.id == req.video_asset_id).first()
    if not video_asset:
        raise HTTPException(status_code=404, detail="Video asset not found")

    job = DubbingJob(
        video_asset_id=req.video_asset_id,
        source_language=req.source_language,
        target_language=req.target_language,
        mode=req.mode,
        preserve_background_audio=req.preserve_background_audio,
        register=req.speech_register or "conversational",
        status="pending",
        progress=0,
        current_stage="Job Created"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Setup speaker voice mappings
    voice_map = req.voice_mapping or DEFAULT_TAMIL_VOICES
    spk1_voice = voice_map.get("speaker_1", "ta-IN-ValluvarNeural")
    spk2_voice = voice_map.get("speaker_2", "ta-IN-PallaviNeural")

    spk1 = Speaker(
        job_id=job.id,
        speaker_label="speaker_1",
        voice_provider="edge_tts",
        voice_id=spk1_voice,
        gender="male" if "valluvar" in spk1_voice.lower() or "conrad" in spk1_voice.lower() else "female"
    )
    db.add(spk1)

    if req.mode == "multi_speaker":
        spk2 = Speaker(
            job_id=job.id,
            speaker_label="speaker_2",
            voice_provider="edge_tts",
            voice_id=spk2_voice,
            gender="female" if "pallavi" in spk2_voice.lower() or "katja" in spk2_voice.lower() else "male"
        )
        db.add(spk2)

    db.commit()

    # Launch background processing pipeline
    background_tasks.add_task(pipeline_worker.run_pipeline, job.id)

    return {
        "id": job.id,
        "video_asset_id": job.video_asset_id,
        "status": job.status,
        "progress": job.progress,
        "message": "Dubbing job initiated successfully"
    }

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Read status and progress for a dubbing job.
    """
    job = db.query(DubbingJob).filter(DubbingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Dubbing job not found")

    export_url = f"/api/v1/dubbing/jobs/{job.id}/stream-export" if job.status == "completed" else None

    return JobStatusResponse(
        id=job.id,
        video_asset_id=job.video_asset_id,
        source_language=job.source_language,
        target_language=job.target_language,
        mode=job.mode,
        preserve_background_audio=job.preserve_background_audio,
        speech_register=job.register,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        export_url=export_url
    )

@router.get("/jobs/{job_id}/segments", response_model=SegmentListResponse)
def get_job_segments(job_id: str, db: Session = Depends(get_db)):
    """
    Read source and translated segments with timing and audio preview details.
    """
    job = db.query(DubbingJob).filter(DubbingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Dubbing job not found")

    speech_segments = (
        db.query(SpeechSegment)
        .filter(SpeechSegment.job_id == job_id)
        .order_by(SpeechSegment.start_ms.asc())
        .all()
    )

    items = []
    for s in speech_segments:
        t_seg = s.translated_segment
        t_text = t_seg.translated_text if t_seg else None
        target_lang = t_seg.target_language if t_seg else ("ta-IN" if s.source_language == "de" else "en-US")
        edited = t_seg.edited_by_user if t_seg else False

        audio_out = None
        if t_seg and t_seg.audio_segment:
            a = t_seg.audio_segment
            audio_out = AudioSegmentOut(
                id=a.id,
                storage_key=a.storage_key,
                duration_ms=a.duration_ms,
                speed_factor=a.speed_factor,
                audio_url=f"/api/v1/dubbing/jobs/{job_id}/segments/{s.id}/audio"
            )

        items.append(SegmentItem(
            id=s.id,
            segment_id=s.id,
            job_id=s.job_id,
            speaker_id=s.speaker_id,
            start_ms=s.start_ms,
            end_ms=s.end_ms,
            source_text=s.source_text,
            confidence=s.confidence,
            source_language=s.source_language,
            target_language=target_lang,
            translated_text=t_text,
            edited_by_user=edited,
            audio_segment=audio_out
        ))

    return SegmentListResponse(job_id=job_id, segments=items)

@router.patch("/jobs/{job_id}/segments/{segment_id}")
def update_segment(
    job_id: str,
    segment_id: str,
    update: SegmentUpdate,
    db: Session = Depends(get_db)
):
    """
    Edit translated text or timing or speaker for an individual segment.
    """
    s_seg = db.query(SpeechSegment).filter(
        SpeechSegment.id == segment_id,
        SpeechSegment.job_id == job_id
    ).first()
    if not s_seg:
        raise HTTPException(status_code=404, detail="Segment not found")

    if update.start_ms is not None:
        s_seg.start_ms = update.start_ms
    if update.end_ms is not None:
        s_seg.end_ms = update.end_ms
    if update.speaker_id is not None:
        s_seg.speaker_id = update.speaker_id

    if update.translated_text is not None:
        t_seg = s_seg.translated_segment
        if not t_seg:
            t_seg = TranslatedSegment(
                speech_segment_id=s_seg.id,
                translated_text=update.translated_text,
                edited_by_user=True,
                target_language=s_seg.job.target_language
            )
            db.add(t_seg)
        else:
            t_seg.translated_text = update.translated_text
            t_seg.edited_by_user = True

    db.commit()
    return {"status": "success", "segment_id": segment_id}

@router.post("/jobs/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Retry failed stage or segment.
    """
    job = db.query(DubbingJob).filter(DubbingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Dubbing job not found")

    job.status = "pending"
    job.error_message = None
    job.progress = 0
    job.current_stage = "Retrying pipeline"
    db.commit()

    background_tasks.add_task(pipeline_worker.run_pipeline, job.id)
    return {"status": "retry_initiated", "job_id": job.id}

@router.post("/jobs/{job_id}/export", status_code=status.HTTP_202_ACCEPTED)
def start_export(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start final render using currently saved/edited segments.
    """
    job = db.query(DubbingJob).filter(DubbingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Dubbing job not found")

    job.status = "processing"
    job.current_stage = "Rendering exported video"
    db.commit()

    background_tasks.add_task(pipeline_worker.export_from_segments, job.id)
    return {"status": "export_initiated", "job_id": job.id}

@router.get("/jobs/{job_id}/download")
def download_export(job_id: str, db: Session = Depends(get_db)):
    """
    Get authorized download for final dubbed MP4.
    """
    export = db.query(Export).filter(Export.job_id == job_id).first()
    if not export or not Path(export.storage_key).exists():
        raise HTTPException(status_code=404, detail="Exported video file not available")

    return FileResponse(
        export.storage_key,
        media_type="video/mp4",
        filename=f"dubbed_video_{job_id}.mp4"
    )

@router.get("/jobs/{job_id}/stream-export")
def stream_export(job_id: str, db: Session = Depends(get_db)):
    """
    Streams the exported video for the preview player.
    """
    export = db.query(Export).filter(Export.job_id == job_id).first()
    if not export or not Path(export.storage_key).exists():
        raise HTTPException(status_code=404, detail="Export not ready")

    return FileResponse(export.storage_key, media_type="video/mp4")

@router.get("/jobs/{job_id}/segments/{segment_id}/audio")
def get_segment_audio(job_id: str, segment_id: str, db: Session = Depends(get_db)):
    """
    Streams individual segment audio for preview.
    """
    s_seg = db.query(SpeechSegment).filter(
        SpeechSegment.id == segment_id,
        SpeechSegment.job_id == job_id
    ).first()
    if not s_seg or not s_seg.translated_segment or not s_seg.translated_segment.audio_segment:
        raise HTTPException(status_code=404, detail="Segment audio not found")

    audio_path = s_seg.translated_segment.audio_segment.storage_key
    if not Path(audio_path).exists():
        raise HTTPException(status_code=404, detail="Audio file missing")

    return FileResponse(audio_path, media_type="audio/mpeg")
