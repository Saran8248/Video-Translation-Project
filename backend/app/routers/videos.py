import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db, VideoAsset, User
from ..schemas import UploadSessionRequest, UploadSessionResponse, VideoAssetResponse
from ..config import UPLOAD_DIR
from ..services.media_service import media_service
from ..services.sample_generator import sample_generator

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])

@router.post("/upload-session", response_model=UploadSessionResponse)
def create_upload_session(req: UploadSessionRequest, db: Session = Depends(get_db)):
    """
    Creates a signed upload session / asset record.
    """
    user = db.query(User).first()
    user_id = user.id if user else "user_default_01"

    asset_id = f"vid_{uuid.uuid4().hex[:12]}"
    filename = f"{asset_id}_{req.filename}"
    storage_path = str(UPLOAD_DIR / filename)

    asset = VideoAsset(
        id=asset_id,
        user_id=user_id,
        storage_key=storage_path,
        duration_ms=0,
        meta_info={},
        status="awaiting_upload"
    )
    db.add(asset)
    db.commit()

    return UploadSessionResponse(
        video_asset_id=asset_id,
        upload_url=f"/api/v1/videos/{asset_id}/direct-upload",
        storage_key=storage_path
    )

@router.post("/upload", response_model=VideoAssetResponse)
async def upload_video_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Direct multipart file upload with automatic media inspection.
    """
    user = db.query(User).first()
    user_id = user.id if user else "user_default_01"

    asset_id = f"vid_{uuid.uuid4().hex[:12]}"
    clean_filename = f"{asset_id}_{file.filename}"
    dest_path = UPLOAD_DIR / clean_filename

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    media_info = media_service.inspect_media(str(dest_path))

    asset = VideoAsset(
        id=asset_id,
        user_id=user_id,
        storage_key=str(dest_path),
        duration_ms=media_info.get("duration_ms", 0),
        meta_info=media_info,
        status="ready"
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return VideoAssetResponse(
        id=asset.id,
        duration_ms=asset.duration_ms,
        metadata=asset.meta_info,
        status=asset.status,
        created_at=asset.created_at
    )

@router.post("/{asset_id}/direct-upload", response_model=VideoAssetResponse)
async def upload_direct_session(asset_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Video asset session not found")

    dest_path = Path(asset.storage_key)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    media_info = media_service.inspect_media(str(dest_path))
    asset.duration_ms = media_info.get("duration_ms", 0)
    asset.meta_info = media_info
    asset.status = "ready"
    db.commit()
    db.refresh(asset)

    return VideoAssetResponse(
        id=asset.id,
        duration_ms=asset.duration_ms,
        metadata=asset.meta_info,
        status=asset.status,
        created_at=asset.created_at
    )

@router.get("/{asset_id}")
def get_video_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Video asset not found")
    return {
        "id": asset.id,
        "duration_ms": asset.duration_ms,
        "metadata": asset.meta_info,
        "status": asset.status,
        "stream_url": f"/api/v1/videos/{asset.id}/stream"
    }

@router.get("/{asset_id}/stream")
def stream_video(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset or not Path(asset.storage_key).exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(asset.storage_key, media_type="video/mp4")

@router.post("/sample/generate", response_model=VideoAssetResponse)
async def generate_sample_german_video(db: Session = Depends(get_db)):
    """
    Generates a sample German interview video for immediate testing.
    """
    user = db.query(User).first()
    user_id = user.id if user else "user_default_01"

    asset_id = f"vid_sample_{uuid.uuid4().hex[:8]}"
    sample_path = await sample_generator.generate_german_interview_video()

    media_info = media_service.inspect_media(sample_path)

    asset = VideoAsset(
        id=asset_id,
        user_id=user_id,
        storage_key=sample_path,
        duration_ms=media_info.get("duration_ms", 12000),
        meta_info=media_info,
        status="ready"
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return VideoAssetResponse(
        id=asset.id,
        duration_ms=asset.duration_ms,
        metadata=asset.meta_info,
        status=asset.status,
        created_at=asset.created_at
    )

@router.post("/sample/generate-multilingual", response_model=VideoAssetResponse)
async def generate_sample_multilingual_video(db: Session = Depends(get_db)):
    """
    Generates a sample Multilingual interview video (German + English + French).
    """
    user = db.query(User).first()
    user_id = user.id if user else "user_default_01"

    asset_id = f"vid_multi_{uuid.uuid4().hex[:8]}"
    sample_path = await sample_generator.generate_multilingual_interview_video()

    media_info = media_service.inspect_media(sample_path)

    asset = VideoAsset(
        id=asset_id,
        user_id=user_id,
        storage_key=sample_path,
        duration_ms=media_info.get("duration_ms", 16000),
        meta_info=media_info,
        status="ready"
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return VideoAssetResponse(
        id=asset.id,
        duration_ms=asset.duration_ms,
        metadata=asset.meta_info,
        status=asset.status,
        created_at=asset.created_at
    )
