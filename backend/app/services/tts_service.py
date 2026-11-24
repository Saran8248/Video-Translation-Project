import os
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import edge_tts
from pydub import AudioSegment
from ..config import SEGMENT_DIR, TEMP_DIR
from .audio_helper import load_audio_safely

logger = logging.getLogger(__name__)

AVAILABLE_VOICES: List[Dict[str, str]] = [
    # Tamil Voices
    {"id": "ta-IN-ValluvarNeural", "name": "Valluvar (Tamil Male)", "gender": "male", "locale": "ta-IN", "language": "Tamil", "provider": "edge_tts"},
    {"id": "ta-IN-PallaviNeural", "name": "Pallavi (Tamil Female)", "gender": "female", "locale": "ta-IN", "language": "Tamil", "provider": "edge_tts"},
    {"id": "ta-LK-KumarNeural", "name": "Kumar (Sri Lanka Male)", "gender": "male", "locale": "ta-LK", "language": "Tamil", "provider": "edge_tts"},
    {"id": "ta-LK-SaranyaNeural", "name": "Saranya (Sri Lanka Female)", "gender": "female", "locale": "ta-LK", "language": "Tamil", "provider": "edge_tts"},
    {"id": "ta-SG-AnbuNeural", "name": "Anbu (Singapore Male)", "gender": "male", "locale": "ta-SG", "language": "Tamil", "provider": "edge_tts"},
    {"id": "ta-SG-VenbaNeural", "name": "Venba (Singapore Female)", "gender": "female", "locale": "ta-SG", "language": "Tamil", "provider": "edge_tts"},

    # English Voices
    {"id": "en-US-GuyNeural", "name": "Guy (English Male)", "gender": "male", "locale": "en-US", "language": "English", "provider": "edge_tts"},
    {"id": "en-US-JennyNeural", "name": "Jenny (English Female)", "gender": "female", "locale": "en-US", "language": "English", "provider": "edge_tts"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher (English Male)", "gender": "male", "locale": "en-US", "language": "English", "provider": "edge_tts"},
    {"id": "en-US-AriaNeural", "name": "Aria (English Female)", "gender": "female", "locale": "en-US", "language": "English", "provider": "edge_tts"},

    # Other Languages
    {"id": "hi-IN-MadhurNeural", "name": "Madhur (Hindi Male)", "gender": "male", "locale": "hi-IN", "language": "Hindi", "provider": "edge_tts"},
    {"id": "hi-IN-SwaraNeural", "name": "Swara (Hindi Female)", "gender": "female", "locale": "hi-IN", "language": "Hindi", "provider": "edge_tts"},
    {"id": "de-DE-ConradNeural", "name": "Conrad (German Male)", "gender": "male", "locale": "de-DE", "language": "German", "provider": "edge_tts"},
    {"id": "de-DE-KatjaNeural", "name": "Katja (German Female)", "gender": "female", "locale": "de-DE", "language": "German", "provider": "edge_tts"},
]

# Consistent Voice Profiles per Speaker Identity
SPEAKER_VOICE_PROFILES = {
    "speaker_1": {
        "gender": "male",
        "ta": "ta-IN-ValluvarNeural",
        "en": "en-US-GuyNeural"
    },
    "speaker_2": {
        "gender": "female",
        "ta": "ta-IN-PallaviNeural",
        "en": "en-US-JennyNeural"
    },
    "speaker_3": {
        "gender": "male",
        "ta": "ta-LK-KumarNeural",
        "en": "en-US-ChristopherNeural"
    },
    "speaker_4": {
        "gender": "female",
        "ta": "ta-LK-SaranyaNeural",
        "en": "en-US-AriaNeural"
    }
}

class TTSService:
    def __init__(self):
        self.voices = AVAILABLE_VOICES

    def get_available_voices(self, language_prefix: Optional[str] = None) -> List[Dict[str, str]]:
        if not language_prefix:
            return self.voices
        lp = language_prefix.lower()
        return [v for v in self.voices if lp in v["locale"].lower() or lp in v["id"].lower() or lp in v["language"].lower()]

    def resolve_speaker_voice(
        self,
        speaker_id: str,
        target_language: str,
        gender: Optional[str] = None,
        custom_voice_map: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Determines the consistent neural voice for a speaker based on target language
        and speaker gender/profile.
        Ensures the same speaker retains their characteristic voice throughout the video.
        """
        lang = target_language.lower().split("-")[0]
        spk_key = speaker_id.lower() if speaker_id else "speaker_1"

        # Check if custom voice explicitly mapped for this speaker
        if custom_voice_map and spk_key in custom_voice_map:
            v_id = custom_voice_map[spk_key]
            # If mapped voice matches the target language, use it
            if lang in v_id.lower():
                return v_id

        # Determine gender
        profile = SPEAKER_VOICE_PROFILES.get(spk_key, SPEAKER_VOICE_PROFILES["speaker_1"])
        spk_gender = (gender or profile["gender"]).lower()

        if lang == "ta":
            return "ta-IN-PallaviNeural" if spk_gender == "female" else "ta-IN-ValluvarNeural"
        else:
            return "en-US-JennyNeural" if spk_gender == "female" else "en-US-GuyNeural"

    async def generate_speech_async(
        self,
        text: str,
        voice_id: str = "ta-IN-ValluvarNeural",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates high quality neural speech for a segment.
        Returns duration_ms and storage path.
        """
        clean_text = text.strip()
        if not clean_text:
            clean_text = "வணக்கம்" if "ta" in voice_id.lower() else "Hello"

        if not output_path:
            out_file = SEGMENT_DIR / f"tts_{uuid.uuid4().hex[:10]}.mp3"
        else:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)

        req_id = f"req_{uuid.uuid4().hex[:8]}"

        try:
            communicate = edge_tts.Communicate(clean_text, voice_id)
            await communicate.save(str(out_file))

            # Inspect duration with safe audio loader
            audio = load_audio_safely(str(out_file))
            duration_ms = len(audio)

            return {
                "storage_key": str(out_file),
                "duration_ms": duration_ms,
                "provider_request_id": req_id,
                "voice_id": voice_id,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Edge-TTS synthesis error for '{clean_text}' ({voice_id}): {e}")
            # Fallback to gTTS if edge-tts fails
            try:
                from gtts import gTTS
                lang = "ta" if "ta" in voice_id.lower() else "en"
                tts = gTTS(text=clean_text, lang=lang)
                tts.save(str(out_file))
                audio = load_audio_safely(str(out_file))
                return {
                    "storage_key": str(out_file),
                    "duration_ms": len(audio),
                    "provider_request_id": req_id,
                    "voice_id": "gtts_fallback",
                    "status": "success"
                }
            except Exception as e_fb:
                raise RuntimeError(f"TTS synthesis failed: {e_fb}")

    def generate_speech(self, text: str, voice_id: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        return asyncio.run(self.generate_speech_async(text, voice_id, output_path))

tts_service = TTSService()
