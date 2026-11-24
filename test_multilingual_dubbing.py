import os
import sys
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.app.database import init_db, SessionLocal, VideoAsset, DubbingJob, Export
from backend.app.services.sample_generator import sample_generator
from backend.app.services.media_service import media_service
from backend.app.services.stt_service import stt_service
from backend.app.services.translation import translation_service
from backend.app.services.tts_service import tts_service
from backend.app.services.sync_service import sync_service
from backend.app.services.pipeline import pipeline_worker
from backend.app.routers.dubbing import create_dubbing_job, get_job_status, get_job_segments
from backend.app.schemas import CreateJobRequest
from fastapi import BackgroundTasks

def run_all_tests():
    print("=" * 70)
    print("MULTILINGUAL AI VIDEO DUBBING PIPELINE: VERIFICATION SUITE")
    print("=" * 70)

    # -------------------------------------------------------------
    # TEST 1: German-to-Tamil Translation & Slang/Idioms
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing German-to-Tamil Translation & Slang/Idiom Handling...")
    german_samples = [
        "Alles klar",
        "Na und?",
        "Keine Ahnung",
        "Ich habe keinen Bock",
        "Das ist echt geil",
        "Moin Moin! Wie geht es Ihnen?",
        "Wir können anfangen, alles läuft nach Plan"
    ]
    for text in german_samples:
        tamil_dub, target_lang = translation_service.route_and_translate(text, "de")
        print(f"  DE: '{text}'")
        print(f"  -> TA ({target_lang}): '{tamil_dub}'")
        assert target_lang == "ta-IN", f"Expected ta-IN, got {target_lang}"
        assert len(tamil_dub) > 0, "Translation should not be empty"

    # -------------------------------------------------------------
    # TEST 2: Other Languages -> English Translation & English Preservation
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing English Preservation and Other Languages to English...")
    # English speech kept in English
    en_sample = "Hello everyone! The project is moving ahead on schedule."
    en_out, en_lang = translation_service.route_and_translate(en_sample, "en")
    print(f"  EN: '{en_sample}' -> ({en_lang}): '{en_out}'")
    assert en_lang == "en-US", f"Expected en-US, got {en_lang}"
    assert en_out == en_sample, "English speech should be preserved"

    # French speech to English
    fr_sample = "Bonjour! Merci beaucoup pour votre excellente présentation."
    fr_out, fr_lang = translation_service.route_and_translate(fr_sample, "fr")
    print(f"  FR: '{fr_sample}' -> ({fr_lang}): '{fr_out}'")
    assert fr_lang == "en-US", f"Expected en-US for French, got {fr_lang}"
    assert len(fr_out) > 0, "French translation should not be empty"

    # Spanish speech to English
    es_sample = "Hola, muchas gracias por venir a nuestra reunión hoy."
    es_out, es_lang = translation_service.route_and_translate(es_sample, "es")
    print(f"  ES: '{es_sample}' -> ({es_lang}): '{es_out}'")
    assert es_lang == "en-US", f"Expected en-US for Spanish, got {es_lang}"
    assert len(es_out) > 0, "Spanish translation should not be empty"

    # -------------------------------------------------------------
    # TEST 3: Multi-Speaker Voice Consistency Across Languages
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing Multi-Speaker Voice Consistency Across Languages...")
    # Speaker 1 (Male): German -> Tamil voice, French/English -> English voice
    spk1_ta = tts_service.resolve_speaker_voice("speaker_1", "ta-IN", gender="male")
    spk1_en = tts_service.resolve_speaker_voice("speaker_1", "en-US", gender="male")
    print(f"  Speaker 1 (Male): Tamil Voice='{spk1_ta}', English Voice='{spk1_en}'")
    assert "Valluvar" in spk1_ta or "Kumar" in spk1_ta or "Anbu" in spk1_ta, "Speaker 1 Tamil voice should be male"
    assert "Guy" in spk1_en or "Christopher" in spk1_en, "Speaker 1 English voice should be male"

    # Speaker 2 (Female): German -> Tamil voice, English -> English voice
    spk2_ta = tts_service.resolve_speaker_voice("speaker_2", "ta-IN", gender="female")
    spk2_en = tts_service.resolve_speaker_voice("speaker_2", "en-US", gender="female")
    print(f"  Speaker 2 (Female): Tamil Voice='{spk2_ta}', English Voice='{spk2_en}'")
    assert "Pallavi" in spk2_ta or "Saranya" in spk2_ta or "Venba" in spk2_ta, "Speaker 2 Tamil voice should be female"
    assert "Jenny" in spk2_en or "Aria" in spk2_en, "Speaker 2 English voice should be female"

    # -------------------------------------------------------------
    # TEST 4: Streaming Audio Timeline Assembly (O(1) Memory)
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Streaming Audio Timeline Assembly for Long Videos...")
    test_timeline = Path("storage/temp/test_timeline.wav")
    dummy_segments = []
    # Test assembling 10 minutes (600,000 ms) timeline
    t0_sync = time.time()
    sync_service.assemble_dubbed_timeline(
        aligned_segments=dummy_segments,
        total_duration_ms=600000,
        output_timeline_path=str(test_timeline)
    )
    t_sync = time.time() - t0_sync
    print(f"  Generated 10-minute silent timeline streamingly in {t_sync:.3f}s: {test_timeline}")
    assert test_timeline.exists(), "Timeline file not created"
    test_dur = stt_service.get_wav_duration_ms(str(test_timeline))
    print(f"  Verified Timeline duration: {test_dur}ms (~10 min)")
    assert 599000 <= test_dur <= 601000, f"Timeline duration mismatch: {test_dur}"
    if test_timeline.exists():
        os.remove(test_timeline)

    # -------------------------------------------------------------
    # TEST 5: End-to-End Multilingual Pipeline Execution
    # -------------------------------------------------------------
    print("\n[TEST 5] Executing Complete End-to-End Multilingual Dubbing Pipeline...")
    init_db()
    db = SessionLocal()

    # Generate multilingual test video (German + English + French)
    print("  Generating multilingual test video (DE + EN + FR)...")
    sample_video = asyncio.run(sample_generator.generate_multilingual_interview_video())
    assert Path(sample_video).exists(), "Sample video generation failed"
    media_info = media_service.inspect_media(sample_video)
    print(f"  Sample Video: {media_info['width']}x{media_info['height']}, {media_info['duration_ms']}ms, {media_info['fps']}fps")

    asset = VideoAsset(
        id=f"vid_test_{int(time.time())}",
        user_id="user_default_01",
        storage_key=sample_video,
        duration_ms=media_info["duration_ms"],
        meta_info=media_info,
        status="ready"
    )
    db.merge(asset)
    db.commit()

    # Create job with Auto-detect language routing
    req = CreateJobRequest(
        video_asset_id=asset.id,
        source_language="auto",
        target_language="ta-IN",
        mode="multi_speaker",
        preserve_background_audio=True,
        speech_register="conversational"
    )
    bg = BackgroundTasks()
    res = create_dubbing_job(req, bg, db)
    job_id = res["id"]
    print(f"  Dubbing Job started: ID={job_id}")

    # Run the 12-step pipeline
    t_pipe = time.time()
    pipeline_worker.run_pipeline(job_id)
    print(f"  Pipeline completed in {time.time() - t_pipe:.2f}s")

    # Verify Job status
    job_stat = get_job_status(job_id, db)
    print(f"  Job Status: {job_stat.status}, Progress: {job_stat.progress}%, Stage: '{job_stat.current_stage}'")
    assert job_stat.status == "completed", f"Job failed: {job_stat.error_message}"

    # Verify Segments and Language Routing
    seg_resp = get_job_segments(job_id, db)
    segs = seg_resp.segments
    print(f"  Total Segments: {len(segs)}")
    for i, s in enumerate(segs):
        print(f"    [{i+1}] {s.start_ms}ms-{s.end_ms}ms ({s.speaker_id}) | Route: {s.source_language.upper()} -> {s.target_language}:")
        print(f"         Source: \"{s.source_text}\"")
        print(f"         Dubbed: \"{s.translated_text}\"")
        # Validate that German mapped to Tamil and non-German mapped to English
        if s.source_language == "de":
            assert s.target_language == "ta-IN", f"German segment should map to ta-IN, got {s.target_language}"
        elif s.source_language in ["en", "fr", "es"]:
            assert s.target_language == "en-US", f"Non-German segment should map to en-US, got {s.target_language}"

    # Verify Final Exported MP4
    export = db.query(Export).filter(Export.job_id == job_id).first()
    assert export is not None, "Export not found in DB"
    assert Path(export.storage_key).exists(), "Export file missing"
    exp_info = media_service.inspect_media(export.storage_key)
    print(f"  Exported MP4 verified: Path='{export.storage_key}'")
    print(f"    Duration: {exp_info['duration_ms']}ms, Resolution: {exp_info['width']}x{exp_info['height']}")
    print(f"    Video Codec: {exp_info['video_codec']}, Audio Codec: {exp_info['audio_codec']}")

    db.close()
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
