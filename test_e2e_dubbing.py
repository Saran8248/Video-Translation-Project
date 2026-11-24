import os
import sys
import time
import asyncio
from pathlib import Path

# Set up paths
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.app.database import init_db, SessionLocal, VideoAsset, DubbingJob, Export
from backend.app.services.sample_generator import sample_generator
from backend.app.services.media_service import media_service
from backend.app.services.pipeline import pipeline_worker
from backend.app.routers.dubbing import create_dubbing_job, get_job_status, get_job_segments, update_segment, start_export
from backend.app.schemas import CreateJobRequest, SegmentUpdate
from fastapi import BackgroundTasks

def run_test():
    print("=" * 60)
    print("AI VIDEO DUBBING: END-TO-END VERIFICATION TEST")
    print("=" * 60)

    # 1. Initialize DB
    print("\n[1/6] Initializing database...")
    init_db()
    db = SessionLocal()

    # 2. Generate German Interview Sample Video
    print("\n[2/6] Generating German Interview test video...")
    t0 = time.time()
    sample_video_path = asyncio.run(sample_generator.generate_german_interview_video())
    print(f"Generated sample video in {time.time() - t0:.2f}s: {sample_video_path}")
    assert Path(sample_video_path).exists(), "Sample video file does not exist"

    # Inspect media
    info = media_service.inspect_media(sample_video_path)
    print(f"Media Info: Duration={info['duration_ms']}ms, Res={info['width']}x{info['height']}, FPS={info['fps']}, Codec={info['video_codec']}/{info['audio_codec']}")

    # Create VideoAsset in DB
    asset = VideoAsset(
        id="vid_test_sample_01",
        user_id="user_default_01",
        storage_key=sample_video_path,
        duration_ms=info["duration_ms"],
        meta_info=info,
        status="ready"
    )
    db.merge(asset)
    db.commit()

    # 3. Create Dubbing Job (German -> Spoken Tamil, Multi-Speaker)
    print("\n[3/6] Creating Dubbing Job (German -> Tamil, Multi-Speaker)...")
    req = CreateJobRequest(
        video_asset_id=asset.id,
        source_language="de",
        target_language="ta-IN",
        mode="multi_speaker",
        preserve_background_audio=True,
        voice_mapping={
            "speaker_1": "ta-IN-ValluvarNeural",
            "speaker_2": "ta-IN-PallaviNeural"
        },
        speech_register="conversational"
    )
    bg = BackgroundTasks()
    res = create_dubbing_job(req, bg, db)
    job_id = res["id"]
    print(f"Dubbing Job created: ID={job_id}, Status={res['status']}")

    # 4. Run Pipeline Worker
    print("\n[4/6] Executing AI Dubbing Pipeline (STT -> Diarize -> Translate -> TTS -> Sync -> Mux)...")
    t_pipe_start = time.time()
    pipeline_worker.run_pipeline(job_id)
    print(f"Pipeline execution finished in {time.time() - t_pipe_start:.2f}s")

    # Verify status
    job_status = get_job_status(job_id, db)
    print(f"Final Job Status: {job_status.status}, Progress: {job_status.progress}%, Stage: {job_status.current_stage}")
    assert job_status.status == "completed", f"Job failed: {job_status.error_message}"

    # 5. Verify Segments and Translations
    print("\n[5/6] Verifying Timed Speech Segments & Spoken Tamil Translations...")
    segments_resp = get_job_segments(job_id, db)
    segments = segments_resp.segments
    print(f"Total Segments extracted: {len(segments)}")
    for i, s in enumerate(segments):
        audio_dur = s.audio_segment.duration_ms if s.audio_segment else 0
        speed = s.audio_segment.speed_factor if s.audio_segment else 1.0
        print(f"  [{i+1}] {s.start_ms}ms-{s.end_ms}ms ({s.speaker_id}):")
        print(f"      Original (DE): \"{s.source_text}\"")
        print(f"      Tamil Dub (TA): \"{s.translated_text}\"")
        print(f"      Audio: {audio_dur}ms, Time-stretch factor={speed:.2f}x")

    assert len(segments) > 0, "No segments found"

    # 6. Verify Exported MP4 Video
    print("\n[6/6] Verifying Exported MP4 Video...")
    export = db.query(Export).filter(Export.job_id == job_id).first()
    assert export is not None, "Export record not found"
    assert Path(export.storage_key).exists(), f"Export file missing at {export.storage_key}"

    export_info = media_service.inspect_media(export.storage_key)
    print(f"Exported MP4 verified: Path={export.storage_key}")
    print(f"  File size: {export.file_size / 1024:.1f} KB")
    print(f"  Export duration: {export_info['duration_ms']}ms (original: {info['duration_ms']}ms)")
    print(f"  Export video codec: {export_info['video_codec']}, audio codec: {export_info['audio_codec']}")

    # 7. Test Segment Edit & Re-export
    print("\n[Bonus Test] Testing Interactive Segment Edit & Re-export...")
    first_seg = segments[0]
    new_text = "வணக்கம்! இன்றைய நேர்காணலுக்கு உங்களை அன்புடன் வரவேற்கிறோம்."
    update_segment(job_id, first_seg.id, SegmentUpdate(translated_text=new_text), db)
    print(f"Edited segment {first_seg.id} translated_text to: \"{new_text}\"")
    
    pipeline_worker.export_from_segments(job_id)
    updated_job = get_job_status(job_id, db)
    assert updated_job.status == "completed", "Re-export failed"
    print("Re-export completed successfully!")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_test()
