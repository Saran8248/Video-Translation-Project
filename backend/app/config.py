import os
from pathlib import Path
import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
SEGMENT_DIR = STORAGE_DIR / "segments"
EXPORT_DIR = STORAGE_DIR / "exports"
TEMP_DIR = STORAGE_DIR / "temp"

for d in [STORAGE_DIR, UPLOAD_DIR, SEGMENT_DIR, EXPORT_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{STORAGE_DIR / 'dubbing.db'}"

# FFmpeg detection
try:
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

DEFAULT_SOURCE_LANGUAGE = "de"
DEFAULT_TARGET_LANGUAGE = "ta-IN"

# Default voice mappings for Tamil
DEFAULT_TAMIL_VOICES = {
    "speaker_1": "ta-IN-ValluvarNeural",  # Male Tamil voice
    "speaker_2": "ta-IN-PallaviNeural",   # Female Tamil voice
}

SUPPORTED_LANGUAGES = [
    {"code": "ta-IN", "name": "Tamil (India)", "locale": "ta-IN"},
    {"code": "hi-IN", "name": "Hindi (India)", "locale": "hi-IN"},
    {"code": "te-IN", "name": "Telugu (India)", "locale": "te-IN"},
    {"code": "ml-IN", "name": "Malayalam (India)", "locale": "ml-IN"},
    {"code": "kn-IN", "name": "Kannada (India)", "locale": "kn-IN"},
    {"code": "en-US", "name": "English (US)", "locale": "en-US"},
    {"code": "de-DE", "name": "German (Germany)", "locale": "de-DE"},
    {"code": "es-ES", "name": "Spanish (Spain)", "locale": "es-ES"},
    {"code": "fr-FR", "name": "French (France)", "locale": "fr-FR"},
]
