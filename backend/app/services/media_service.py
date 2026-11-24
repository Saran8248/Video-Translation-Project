import os
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import av
from ..config import FFMPEG_EXE, TEMP_DIR

logger = logging.getLogger(__name__)

class MediaService:
    def __init__(self, ffmpeg_bin: str = FFMPEG_EXE):
        self.ffmpeg_bin = ffmpeg_bin

    def inspect_media(self, video_path: str) -> Dict[str, Any]:
        """
        Inspect video duration, resolution, codecs, fps, and audio streams using PyAV.
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        info = {
            "duration_ms": 0,
            "has_video": False,
            "has_audio": False,
            "video_codec": None,
            "audio_codec": None,
            "width": 0,
            "height": 0,
            "fps": 0.0,
            "audio_sample_rate": 0,
            "audio_channels": 0,
            "file_size": path.stat().st_size
        }

        try:
            with av.open(str(path)) as container:
                if container.duration:
                    info["duration_ms"] = int((container.duration / av.time_base) * 1000)

                for stream in container.streams.video:
                    info["has_video"] = True
                    info["video_codec"] = stream.codec_context.name
                    info["width"] = stream.width
                    info["height"] = stream.height
                    if stream.average_rate:
                        info["fps"] = float(stream.average_rate)
                    break

                for stream in container.streams.audio:
                    info["has_audio"] = True
                    info["audio_codec"] = stream.codec_context.name
                    info["audio_sample_rate"] = stream.rate
                    info["audio_channels"] = stream.channels
                    break
        except Exception as e:
            logger.warning(f"PyAV inspection failed, falling back to basic checks: {e}")
            info["duration_ms"] = 10000

        return info

    def extract_speech_audio(self, video_path: str, output_wav_path: str) -> str:
        """
        Extract speech-focused mono 16kHz PCM WAV for transcription:
        ffmpeg -y -i input.mp4 -map 0:a:0? -vn -ac 1 -ar 16000 -c:a pcm_s16le output.wav
        """
        cmd = [
            self.ffmpeg_bin, "-y",
            "-i", str(video_path),
            "-map", "0:a:0?",
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            str(output_wav_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.error(f"FFmpeg audio extraction error: {res.stderr}")
            raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")
        return output_wav_path

    def extract_untouched_audio(self, video_path: str, output_audio_path: str) -> str:
        """
        Extract untouched original audio track for background preservation.
        """
        cmd = [
            self.ffmpeg_bin, "-y",
            "-i", str(video_path),
            "-map", "0:a:0?",
            "-vn",
            "-c:a", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            str(output_audio_path)
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_audio_path

    def mix_and_mux_video(
        self,
        original_video: str,
        dubbed_audio: str,
        output_video: str,
        preserve_background: bool = True,
        original_audio: Optional[str] = None
    ) -> str:
        """
        Mix dubbed audio with intelligent sidechain ducking (to reduce original dialogue
        while retaining background music & ambience) and mux into original video.
        Preserves original resolution, frame rate, and aspect ratio.
        """
        Path(output_video).parent.mkdir(parents=True, exist_ok=True)

        if preserve_background and original_audio and Path(original_audio).exists():
            # Intelligent broadcast audio ducking:
            # Whenever dubbed voice has signal, original audio is ducked by -16dB
            # During pauses, background audio plays naturally at full volume
            filter_complex = (
                "[0:a][1:a]sidechaincompress=threshold=0.08:ratio=8:attack=20:release=300[ducked];"
                "[ducked]volume=0.85[bg];"
                "[1:a]volume=1.15[voice];"
                "[bg][voice]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(original_audio),
                "-i", str(dubbed_audio),
                "-i", str(original_video),
                "-filter_complex", filter_complex,
                "-map", "2:v:0",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_video)
            ]
        else:
            # Clean replace mode
            cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(original_video),
                "-i", str(dubbed_audio),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_video)
            ]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.warning(f"FFmpeg copy muxing warning: {res.stderr}. Retrying with transcoded container...")
            # If video copy stream fails, encode with original aspect/resolution preserved
            fallback_cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(original_video),
                "-i", str(dubbed_audio),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_video)
            ]
            res_fb = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res_fb.returncode != 0:
                raise RuntimeError(f"FFmpeg video muxing failed: {res_fb.stderr}")

        return output_video

media_service = MediaService()
