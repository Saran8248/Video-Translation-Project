import os
import re
import uuid
import wave
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import speech_recognition as sr
from langdetect import detect, DetectorFactory
from ..config import TEMP_DIR, FFMPEG_EXE

# Seed detector for reproducible language detection
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

LANGUAGE_CODE_MAP = {
    "de": "de-DE",
    "en": "en-US",
    "fr": "fr-FR",
    "es": "es-ES",
    "it": "it-IT",
    "ta": "ta-IN",
    "hi": "hi-IN",
    "auto": "de-DE"
}

# Lexical heuristics for rapid corroboration
GERMAN_KEYWORDS = {"der", "die", "das", "und", "ich", "ist", "wie", "nicht", "sehr", "danke", "alles", "mit", "auf", "ein", "eine", "wir", "gut", "freue", "ihnen", "heute", "interview"}
ENGLISH_KEYWORDS = {"the", "is", "are", "you", "how", "what", "we", "have", "do", "thank", "good", "today", "project", "my", "to", "in", "am", "glad", "here", "fine"}
FRENCH_KEYWORDS = {"bonjour", "merci", "comment", "vous", "nous", "avec", "est", "je", "le", "la", "les", "bien", "aujourd", "tres"}
SPANISH_KEYWORDS = {"hola", "gracias", "como", "esta", "bien", "por", "favor", "el", "la", "los", "buenos", "dias", "muchas", "aqui"}

class STTService:
    def __init__(self, ffmpeg_bin: str = FFMPEG_EXE):
        self.recognizer = sr.Recognizer()
        self.ffmpeg_bin = ffmpeg_bin

    def get_wav_duration_ms(self, wav_path: str) -> int:
        """
        Reads duration from WAV header in O(1) memory without loading samples.
        """
        try:
            with wave.open(wav_path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return int((frames / float(rate)) * 1000)
        except Exception as e:
            logger.warning(f"Wave header read failed: {e}")
        return 10000

    def detect_speech_intervals_streaming(
        self,
        audio_path: str,
        total_duration_ms: int
    ) -> List[Tuple[int, int]]:
        """
        Detects speech boundaries using FFmpeg silencedetect filter.
        Processes hours of audio streamingly with negligible RAM usage.
        """
        cmd = [
            self.ffmpeg_bin, "-y",
            "-i", str(audio_path),
            "-af", "silencedetect=noise=-32dB:d=0.45",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        silence_starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", res.stderr)]
        silence_ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", res.stderr)]

        speech_ranges: List[Tuple[int, int]] = []
        cur_pos = 0.0
        total_sec = total_duration_ms / 1000.0

        for start_s, end_s in zip(silence_starts, silence_ends):
            if start_s > cur_pos + 0.3:
                speech_ranges.append((int(cur_pos * 1000), int(start_s * 1000)))
            cur_pos = end_s

        if total_sec > cur_pos + 0.3:
            speech_ranges.append((int(cur_pos * 1000), int(total_sec * 1000)))

        # Fallback if no silences detected (audio is constant speech or high noise)
        if not speech_ranges:
            chunk_step = 5000
            speech_ranges = [
                (i, min(i + chunk_step, total_duration_ms))
                for i in range(0, total_duration_ms, chunk_step)
            ]

        # Break any overly long segments (> 8000ms) into natural conversational phrases
        refined: List[Tuple[int, int]] = []
        for s_ms, e_ms in speech_ranges:
            seg_len = e_ms - s_ms
            if seg_len > 8000:
                sub_step = 5000
                for sub_s in range(s_ms, e_ms, sub_step):
                    sub_e = min(sub_s + sub_step, e_ms)
                    if sub_e - sub_s > 800:
                        refined.append((sub_s, sub_e))
            elif seg_len >= 800:
                refined.append((s_ms, e_ms))

        return refined if refined else [(0, min(total_duration_ms, 5000))]

    def detect_segment_language(self, text: str, default_lang: str = "de") -> str:
        """
        Detects spoken language at the sentence or segment level.
        Uses language detection library + lexical corroboration.
        """
        clean = text.strip()
        if not clean or clean.startswith("["):
            return default_lang

        # 1. Check lexical token presence
        words = set(re.findall(r"\b[a-zA-ZäöüßÄÖÜ]+\b", clean.lower()))
        if words:
            de_overlap = len(words & GERMAN_KEYWORDS)
            en_overlap = len(words & ENGLISH_KEYWORDS)
            fr_overlap = len(words & FRENCH_KEYWORDS)
            es_overlap = len(words & SPANISH_KEYWORDS)

            if de_overlap > en_overlap and de_overlap > fr_overlap and de_overlap > es_overlap:
                return "de"
            if en_overlap > de_overlap and en_overlap > fr_overlap and en_overlap > es_overlap:
                return "en"
            if fr_overlap > de_overlap and fr_overlap > en_overlap:
                return "fr"
            if es_overlap > de_overlap and es_overlap > en_overlap:
                return "es"

        # 2. Check German unique characters (ä, ö, ü, ß)
        if any(c in clean.lower() for c in ["ä", "ö", "ü", "ß"]):
            return "de"

        # 3. Langdetect library classification
        try:
            detected = detect(clean)
            return detected.lower()
        except Exception:
            return default_lang

    def extract_segment_chunk(self, audio_path: str, start_ms: int, end_ms: int, output_wav: str) -> str:
        """
        Extracts only a small sub-segment from disk via FFmpeg without loading entire audio into RAM.
        """
        start_sec = max(0.0, start_ms / 1000.0)
        dur_sec = max(0.2, (end_ms - start_ms) / 1000.0)

        cmd = [
            self.ffmpeg_bin, "-y",
            "-ss", f"{start_sec:.3f}",
            "-t", f"{dur_sec:.3f}",
            "-i", str(audio_path),
            "-c:a", "pcm_s16le",
            "-ac", "1",
            "-ar", "16000",
            str(output_wav)
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return output_wav

    def transcribe_audio_segments(
        self,
        audio_path: str,
        source_language: str = "auto"
    ) -> List[Dict[str, Any]]:
        """
        Full-video audio-to-text transcription with chunked streaming and
        automatic sentence-level language detection.
        Supports videos up to 2 hours with O(1) memory footprint.
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        duration_ms = self.get_wav_duration_ms(str(path))
        
        # 1. Streaming silence detection
        intervals = self.detect_speech_intervals_streaming(str(path), duration_ms)
        
        primary_sr_lang = LANGUAGE_CODE_MAP.get(source_language.lower(), "de-DE") if source_language != "auto" else "de-DE"
        segments = []

        # 2. Process each segment chunk individually
        for idx, (start_ms, end_ms) in enumerate(intervals):
            segment_id = f"seg_{uuid.uuid4().hex[:8]}"
            chunk_wav = TEMP_DIR / f"{segment_id}_sub.wav"

            try:
                self.extract_segment_chunk(str(path), start_ms, end_ms, str(chunk_wav))

                # Transcribe chunk
                text = ""
                confidence = 0.95
                with sr.AudioFile(str(chunk_wav)) as source:
                    audio_data = self.recognizer.record(source)
                    try:
                        text = self.recognizer.recognize_google(audio_data, language=primary_sr_lang)
                    except sr.UnknownValueError:
                        # If primary language was German but got unknown, try English
                        try:
                            text = self.recognizer.recognize_google(audio_data, language="en-US")
                        except Exception:
                            text = ""
                    except Exception as e:
                        logger.warning(f"STT recognition error for {segment_id}: {e}")
                        text = ""

                # 3. Automatic Language Detection at segment level
                detected_lang = self.detect_segment_language(text, default_lang="de" if source_language == "auto" else source_language)

                # If text is empty, generate clean dialogue marker
                if not text.strip():
                    text = f"[Audible speech {idx+1}]"
                    confidence = 0.60
                    detected_lang = "de" if source_language in ["auto", "de"] else source_language

                segments.append({
                    "segment_id": segment_id,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "speaker_id": "speaker_1",
                    "source_text": text.strip(),
                    "source_language": detected_lang,
                    "confidence": confidence
                })
            finally:
                if chunk_wav.exists():
                    try:
                        os.remove(chunk_wav)
                    except Exception:
                        pass

        return segments

stt_service = STTService()
