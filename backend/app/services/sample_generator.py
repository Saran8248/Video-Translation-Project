import os
import uuid
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydub import AudioSegment
import edge_tts
from ..config import UPLOAD_DIR, TEMP_DIR, FFMPEG_EXE
from .audio_helper import load_audio_safely

logger = logging.getLogger(__name__)

# German Slang & Conversational Interview
SAMPLE_GERMAN_DIALOGUE = [
    {
        "speaker": "speaker_1",
        "voice": "de-DE-ConradNeural",
        "text": "Moin! Alles klar bei dir? Willkommen zu unserem Interview heute.",
        "pause_after": 1000
    },
    {
        "speaker": "speaker_2",
        "voice": "de-DE-KatjaNeural",
        "text": "Na klar, ich freue mich sehr! Alles läuft absolut nach Plan.",
        "pause_after": 1200
    },
    {
        "speaker": "speaker_1",
        "voice": "de-DE-ConradNeural",
        "text": "Hast du Bock auf die neuen Features oder gibt es Probleme?",
        "pause_after": 1000
    },
    {
        "speaker": "speaker_2",
        "voice": "de-DE-KatjaNeural",
        "text": "Kein Problem, das ist echt geil! Keine Ahnung warum sich manche Sorgen machen.",
        "pause_after": 1000
    }
]

# Multilingual Conversation: German + English + French
SAMPLE_MULTILINGUAL_DIALOGUE = [
    {
        "speaker": "speaker_1",
        "voice": "de-DE-ConradNeural",
        "text": "Guten Tag! Alles klar? Willkommen zu unserer internationalen Konferenz.",
        "pause_after": 1000
    },
    {
        "speaker": "speaker_2",
        "voice": "en-US-JennyNeural",
        "text": "Hello everyone! I am very glad to join this session today.",
        "pause_after": 1200
    },
    {
        "speaker": "speaker_1",
        "voice": "fr-FR-HenriNeural",
        "text": "Bonjour! Merci beaucoup pour votre excellente présentation.",
        "pause_after": 1000
    },
    {
        "speaker": "speaker_2",
        "voice": "en-US-JennyNeural",
        "text": "Thank you very much. Our team is working hard to ensure steady progress.",
        "pause_after": 1000
    }
]

class SampleGeneratorService:
    def __init__(self, ffmpeg_bin: str = FFMPEG_EXE):
        self.ffmpeg_bin = ffmpeg_bin

    async def _render_dialogue_video(self, dialogue_items: List[Dict[str, Any]], title: str, subtitle: str, output_path: Optional[str] = None) -> str:
        if not output_path:
            filename = f"sample_video_{uuid.uuid4().hex[:8]}.mp4"
            target_file = UPLOAD_DIR / filename
        else:
            target_file = Path(output_path)

        composite_audio = AudioSegment.silent(duration=500)
        temp_files = []

        try:
            for item in dialogue_items:
                tmp_mp3 = TEMP_DIR / f"dlg_{uuid.uuid4().hex[:8]}.mp3"
                temp_files.append(tmp_mp3)
                try:
                    comm = edge_tts.Communicate(item["text"], item["voice"])
                    await comm.save(str(tmp_mp3))
                    seg_sound = load_audio_safely(str(tmp_mp3))
                    composite_audio += seg_sound
                    composite_audio += AudioSegment.silent(duration=item.get("pause_after", 1000))
                except Exception as e:
                    logger.warning(f"Failed to generate TTS item {item['text']}: {e}")

            total_duration_sec = (len(composite_audio) / 1000.0) + 0.5
            wav_audio_path = TEMP_DIR / f"sample_audio_{uuid.uuid4().hex[:8]}.wav"
            temp_files.append(wav_audio_path)
            composite_audio.export(str(wav_audio_path), format="wav")

            # Render 720p H.264 video with background visual
            cmd = [
                self.ffmpeg_bin, "-y",
                "-f", "lavfi",
                "-i", f"color=c=0x1e1b4b:s=1280x720:d={total_duration_sec:.2f}",
                "-i", str(wav_audio_path),
                "-vf", f"drawtext=text='{title}':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=200,drawtext=text='{subtitle}':fontsize=24:fontcolor=0x38bdf8:x=(w-text_w)/2:y=280",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(target_file)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                cmd_fallback = [
                    self.ffmpeg_bin, "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=0x1e1b4b:s=1280x720:d={total_duration_sec:.2f}",
                    "-i", str(wav_audio_path),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    str(target_file)
                ]
                subprocess.run(cmd_fallback, check=True)

            return str(target_file)
        finally:
            for f in temp_files:
                if f and Path(f).exists():
                    try:
                        os.remove(f)
                    except Exception:
                        pass

    async def generate_german_interview_video(self, output_path: Optional[str] = None) -> str:
        """
        Generates German interview with conversational slang and idioms.
        """
        return await self._render_dialogue_video(
            dialogue_items=SAMPLE_GERMAN_DIALOGUE,
            title="German Slang & Conversational Interview",
            subtitle="Translating German to Natural Spoken Tamil (ta-IN)",
            output_path=output_path
        )

    async def generate_multilingual_interview_video(self, output_path: Optional[str] = None) -> str:
        """
        Generates multilingual video with German, English, and French speech.
        Tests: German -> Tamil, English -> English, French -> English.
        """
        return await self._render_dialogue_video(
            dialogue_items=SAMPLE_MULTILINGUAL_DIALOGUE,
            title="Multilingual Interview (German, English, French)",
            subtitle="German -> Tamil | English -> English | French -> English",
            output_path=output_path
        )

sample_generator = SampleGeneratorService()
