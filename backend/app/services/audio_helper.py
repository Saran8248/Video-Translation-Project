import os
import subprocess
from pathlib import Path
from pydub import AudioSegment
from ..config import FFMPEG_EXE

def load_audio_safely(file_path: str) -> AudioSegment:
    """
    Loads an audio file safely into an AudioSegment.
    If the file is not a WAV, converts it to WAV via FFmpeg first so Python's
    built-in wave module loads it directly without needing ffprobe.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    if path.suffix.lower() == ".wav":
        return AudioSegment.from_file(str(path), format="wav")

    # If it's MP3 or AAC or other format, convert to a temporary WAV using FFmpeg
    temp_wav = path.with_suffix(".tmp.wav")
    try:
        cmd = [
            FFMPEG_EXE, "-y",
            "-i", str(path),
            "-ac", "2",
            "-ar", "44100",
            "-f", "wav",
            str(temp_wav)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and temp_wav.exists():
            sound = AudioSegment.from_file(str(temp_wav), format="wav")
            return sound
        else:
            return AudioSegment.from_file(str(path))
    finally:
        if temp_wav.exists():
            try:
                os.remove(temp_wav)
            except Exception:
                pass
