import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..config import TEMP_DIR, EXPORT_DIR, SEGMENT_DIR
from ..database import (
    SessionLocal, DubbingJob, VideoAsset, Speaker, 
    SpeechSegment, TranslatedSegment, AudioSegment, Export, UsageLedger
)
from .media_service import media_service
from .stt_service import stt_service
from .diarization import diarization_service
from .translation import translation_service
from .tts_service import tts_service
from .sync_service import sync_service

logger = logging.getLogger(__name__)

class PipelineWorker:
    def update_job_status(self, db: Session, job_id: str, status: str, stage: str, progress: int, error: Optional[str] = None):
        job = db.query(DubbingJob).filter(DubbingJob.id == job_id).first()
        if job:
            job.status = status
            job.current_stage = stage
            job.progress = progress
            if error:
                job.error_message = error
            db.commit()

    def run_pipeline(self, job_id: str):
        """
        Executes the improved 12-step multilingual AI Dubbing pipeline:
        1. Video upload and audio extraction.
        2. Full-video audio-to-text transcription.
        3. Automatic language detection at sentence or segment level.
        4. Speaker identification and timestamp generation.
        5. German speech -> natural spoken Tamil translation.
        6. Other languages -> English translation (English speech kept in English).
        7. Generate complete translated transcripts.
        8. Tamil text -> Tamil speech generation.
        9. English text -> English speech generation where required.
        10. Match generated audio with original timestamps.
        11. Merge translated audio with the original video.
        12. Export the final dubbed video.
        """
        db = SessionLocal()
        temp_files_to_clean = []
        try:
            job = db.query(DubbingJob).filter(DubbingJob.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            video_asset = db.query(VideoAsset).filter(VideoAsset.id == job.video_asset_id).first()
            if not video_asset:
                raise ValueError("Video asset record not found")

            video_path = video_asset.storage_key
            if not Path(video_path).exists():
                raise FileNotFoundError(f"Video file not found at {video_path}")

            # -------------------------------------------------------------
            # STEP 1: Video inspection & audio extraction (10% - 20%)
            # -------------------------------------------------------------
            self.update_job_status(db, job_id, "processing", "Extracting Speech & Background Audio", 12)
            
            media_info = media_service.inspect_media(video_path)
            video_asset.meta_info = media_info
            video_asset.duration_ms = media_info.get("duration_ms", 0)
            db.commit()

            speech_wav_path = TEMP_DIR / f"{job_id}_speech.wav"
            original_audio_path = TEMP_DIR / f"{job_id}_original_audio.wav"
            temp_files_to_clean.extend([speech_wav_path, original_audio_path])
            
            media_service.extract_speech_audio(video_path, str(speech_wav_path))
            media_service.extract_untouched_audio(video_path, str(original_audio_path))
            
            self.update_job_status(db, job_id, "processing", "Audio Extracted", 20)

            # -------------------------------------------------------------
            # STEP 2 & 3: Full-video transcription & segment language detection (20% - 35%)
            # -------------------------------------------------------------
            self.update_job_status(db, job_id, "processing", "Transcribing & Detecting Spoken Languages", 25)
            
            raw_segments = stt_service.transcribe_audio_segments(
                str(speech_wav_path),
                source_language=job.source_language
            )

            # -------------------------------------------------------------
            # STEP 4: Speaker identification & timestamp generation (35% - 40%)
            # -------------------------------------------------------------
            self.update_job_status(db, job_id, "processing", "Speaker Diarization & Profiling", 35)
            num_speakers = 2 if job.mode == "multi_speaker" else 1
            diarized_segments = diarization_service.estimate_speakers(
                str(speech_wav_path),
                raw_segments,
                num_speakers=num_speakers
            )

            # Speaker gender and voice map cache
            speaker_gender_map = {}
            existing_speakers = db.query(Speaker).filter(Speaker.job_id == job_id).all()
            for spk in existing_speakers:
                speaker_gender_map[spk.speaker_label] = spk.gender

            # Save speech segments into DB
            db_segments = []
            for seg in diarized_segments:
                spk_label = seg.get("speaker_id", "speaker_1")
                if spk_label not in speaker_gender_map:
                    # Assign gender: speaker_1 -> male, speaker_2 -> female
                    gender = "female" if "2" in spk_label else "male"
                    speaker_gender_map[spk_label] = gender
                    new_spk = Speaker(
                        job_id=job_id,
                        speaker_label=spk_label,
                        voice_provider="edge_tts",
                        voice_id=tts_service.resolve_speaker_voice(spk_label, "ta-IN", gender=gender),
                        gender=gender
                    )
                    db.add(new_spk)

                speech_seg = SpeechSegment(
                    job_id=job_id,
                    speaker_id=spk_label,
                    start_ms=seg["start_ms"],
                    end_ms=seg["end_ms"],
                    source_text=seg["source_text"],
                    confidence=seg.get("confidence", 1.0),
                    source_language=seg.get("source_language", "de")
                )
                db.add(speech_seg)
                db_segments.append(speech_seg)

            db.commit()
            self.update_job_status(db, job_id, "processing", "Transcription & Language Detection Complete", 40)

            # -------------------------------------------------------------
            # STEP 5, 6, 7: German -> Tamil & Other Languages -> English Translation (40% - 55%)
            # -------------------------------------------------------------
            self.update_job_status(db, job_id, "processing", "Translating Dialogue (German → Tamil, Other → English)", 45)
            
            translated_records = []
            for idx, s_seg in enumerate(db_segments):
                # Apply required language routing rules:
                # - German -> Spoken Tamil (ta-IN)
                # - English -> Keep English (en-US)
                # - French, Spanish, other -> English (en-US)
                translated_text, target_lang = translation_service.route_and_translate(
                    text=s_seg.source_text,
                    detected_language=s_seg.source_language,
                    register=job.register
                )

                trans_seg = TranslatedSegment(
                    speech_segment_id=s_seg.id,
                    translated_text=translated_text,
                    edited_by_user=False,
                    target_language=target_lang
                )
                db.add(trans_seg)
                translated_records.append((s_seg, trans_seg))

            db.commit()
            self.update_job_status(db, job_id, "processing", "Translation Completed", 55)

            # -------------------------------------------------------------
            # STEP 8 & 9: Tamil text -> Tamil TTS & English text -> English TTS (55% - 80%)
            # -------------------------------------------------------------
            self.update_job_status(db, job_id, "processing", "Synthesizing Multilingual Neural Voices", 60)
            
            audio_records = []
            total_items = len(translated_records)

            for idx, (s_seg, t_seg) in enumerate(translated_records):
                spk_label = s_seg.speaker_id
                gender = speaker_gender_map.get(spk_label, "male")
                
                # Resolve consistent voice for this speaker matching target language
                voice_id = tts_service.resolve_speaker_voice(
                    speaker_id=spk_label,
                    target_language=t_seg.target_language,
                    gender=gender
                )

                out_audio_file = SEGMENT_DIR / f"{job_id}_{t_seg.id}.mp3"
                
                tts_result = tts_service.generate_speech(
                    text=t_seg.translated_text,
                    voice_id=voice_id,
                    output_path=str(out_audio_file)
                )

                audio_seg = AudioSegment(
                    translated_segment_id=t_seg.id,
                    storage_key=tts_result["storage_key"],
                    duration_ms=tts_result["duration_ms"],
                    provider_request_id=tts_result.get("provider_request_id"),
                    speed_factor=1.0
                )
                db.add(audio_seg)
                audio_records.append((s_seg, t_seg, audio_seg))

                cur_progress = 60 + int((idx / max(1, total_items)) * 20)
                self.update_job_status(db, job_id, "processing", f"Synthesizing voice {idx+1}/{total_items}", cur_progress)

            db.commit()
            self.update_job_status(db, job_id, "processing", "Voice Synthesis Completed", 80)

            # -------------------------------------------------------------
            # STEP 10: Timing & audio synchronization with original timestamps (80% - 88%)
            # -------------------------------------------------------------
            self.update_job_status(db, job_id, "processing", "Synchronizing Audio with Original Timestamps", 83)
            
            aligned_list = []
            for s_seg, t_seg, a_seg in audio_records:
                synced_wav = TEMP_DIR / f"synced_{a_seg.id}.wav"
                temp_files_to_clean.append(synced_wav)

                speed_factor = sync_service.fit_segment_to_window(
                    audio_path=a_seg.storage_key,
                    start_ms=s_seg.start_ms,
                    end_ms=s_seg.end_ms,
                    output_synced_path=str(synced_wav)
                )
                a_seg.speed_factor = speed_factor
                aligned_list.append({
                    "audio_path": str(synced_wav),
                    "start_ms": s_seg.start_ms,
                    "end_ms": s_seg.end_ms
                })

            db.commit()

            # Assemble full audio timeline with O(1) memory streaming
            full_timeline_wav = TEMP_DIR / f"{job_id}_full_dubbed.wav"
            temp_files_to_clean.append(full_timeline_wav)
            
            sync_service.assemble_dubbed_timeline(
                aligned_segments=aligned_list,
                total_duration_ms=video_asset.duration_ms,
                output_timeline_path=str(full_timeline_wav)
            )

            # -------------------------------------------------------------
            # STEP 11: Audio mixing & video muxing (88% - 95%)
            # -------------------------------------------------------------
            self.update_job_status(db, job_id, "processing", "Audio Ducking & Video Muxing", 90)
            
            export_filename = f"dubbed_{job_id}.mp4"
            final_export_path = EXPORT_DIR / export_filename

            media_service.mix_and_mux_video(
                original_video=video_path,
                dubbed_audio=str(full_timeline_wav),
                output_video=str(final_export_path),
                preserve_background=job.preserve_background_audio,
                original_audio=str(original_audio_path)
            )

            # -------------------------------------------------------------
            # STEP 12: Validate & export final dubbed video (95% - 100%)
            # -------------------------------------------------------------
            self.update_job_status(db, job_id, "processing", "Validating Rendered MP4", 96)
            
            export_info = media_service.inspect_media(str(final_export_path))
            
            export_entry = Export(
                job_id=job_id,
                storage_key=str(final_export_path),
                format="mp4",
                duration_ms=export_info.get("duration_ms", video_asset.duration_ms),
                file_size=Path(final_export_path).stat().st_size
            )
            db.add(export_entry)

            # Record usage
            db.add(UsageLedger(
                user_id=video_asset.user_id,
                job_id=job_id,
                units=round(export_entry.duration_ms / 60000.0, 2),
                event_type="export"
            ))

            job.status = "completed"
            job.current_stage = "Completed"
            job.progress = 100
            db.commit()
            logger.info(f"Job {job_id} completed successfully!")

        except Exception as e:
            logger.exception(f"Pipeline error for job {job_id}: {e}")
            self.update_job_status(db, job_id, "failed", "Failed", 0, error=str(e))
        finally:
            # Clean up intermediate synced WAV files to prevent disk bloating on long videos
            for f in temp_files_to_clean:
                if f and Path(f).exists():
                    try:
                        os.remove(f)
                    except Exception:
                        pass
            db.close()

    def export_from_segments(self, job_id: str):
        """
        Re-renders final video from existing or edited segments without rerunning STT.
        """
        db = SessionLocal()
        temp_files_to_clean = []
        try:
            job = db.query(DubbingJob).filter(DubbingJob.id == job_id).first()
            if not job:
                return
            video_asset = db.query(VideoAsset).filter(VideoAsset.id == job.video_asset_id).first()
            
            self.update_job_status(db, job_id, "processing", "Re-synthesizing & Muxing Video", 80)

            speaker_gender_map = {s.speaker_label: s.gender for s in job.speakers}

            aligned_list = []
            for s_seg in job.speech_segments:
                t_seg = s_seg.translated_segment
                if not t_seg:
                    continue

                gender = speaker_gender_map.get(s_seg.speaker_id, "male")
                voice_id = tts_service.resolve_speaker_voice(
                    speaker_id=s_seg.speaker_id,
                    target_language=t_seg.target_language,
                    gender=gender
                )

                out_audio = SEGMENT_DIR / f"{job_id}_{t_seg.id}.mp3"
                
                tts_result = tts_service.generate_speech(
                    text=t_seg.translated_text,
                    voice_id=voice_id,
                    output_path=str(out_audio)
                )

                synced_wav = TEMP_DIR / f"synced_{t_seg.id}.wav"
                temp_files_to_clean.append(synced_wav)

                sync_service.fit_segment_to_window(
                    audio_path=str(out_audio),
                    start_ms=s_seg.start_ms,
                    end_ms=s_seg.end_ms,
                    output_synced_path=str(synced_wav)
                )

                aligned_list.append({
                    "audio_path": str(synced_wav),
                    "start_ms": s_seg.start_ms,
                    "end_ms": s_seg.end_ms
                })

            full_timeline_wav = TEMP_DIR / f"{job_id}_full_dubbed.wav"
            temp_files_to_clean.append(full_timeline_wav)

            sync_service.assemble_dubbed_timeline(
                aligned_segments=aligned_list,
                total_duration_ms=video_asset.duration_ms,
                output_timeline_path=str(full_timeline_wav)
            )

            export_filename = f"dubbed_{job_id}.mp4"
            final_export_path = EXPORT_DIR / export_filename
            original_audio_path = TEMP_DIR / f"{job_id}_original_audio.wav"

            media_service.mix_and_mux_video(
                original_video=video_asset.storage_key,
                dubbed_audio=str(full_timeline_wav),
                output_video=str(final_export_path),
                preserve_background=job.preserve_background_audio,
                original_audio=str(original_audio_path) if original_audio_path.exists() else None
            )

            export_info = media_service.inspect_media(str(final_export_path))
            existing_export = db.query(Export).filter(Export.job_id == job_id).first()
            if not existing_export:
                db.add(Export(
                    job_id=job_id,
                    storage_key=str(final_export_path),
                    format="mp4",
                    duration_ms=export_info.get("duration_ms", video_asset.duration_ms),
                    file_size=Path(final_export_path).stat().st_size
                ))
            else:
                existing_export.storage_key = str(final_export_path)
                existing_export.duration_ms = export_info.get("duration_ms", video_asset.duration_ms)
                existing_export.file_size = Path(final_export_path).stat().st_size

            job.status = "completed"
            job.current_stage = "Completed"
            job.progress = 100
            db.commit()

        except Exception as e:
            logger.exception(f"Re-export error: {e}")
            self.update_job_status(db, job_id, "failed", "Export Failed", 0, error=str(e))
        finally:
            for f in temp_files_to_clean:
                if f and Path(f).exists():
                    try:
                        os.remove(f)
                    except Exception:
                        pass
            db.close()

pipeline_worker = PipelineWorker()
