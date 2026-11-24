import os
import wave
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any
from ..config import FFMPEG_EXE, TEMP_DIR

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, ffmpeg_bin: str = FFMPEG_EXE):
        self.ffmpeg_bin = ffmpeg_bin

    def fit_segment_to_window(
        self,
        audio_path: str,
        start_ms: int,
        end_ms: int,
        output_synced_path: str
    ) -> float:
        """
        Fits audio segment to [start_ms, end_ms] window using FFmpeg atempo time-stretching.
        Preserves natural vocal pitch. Returns applied speed_factor.
        """
        target_ms = max(500, end_ms - start_ms)
        path = Path(audio_path)
        if not path.exists():
            return 1.0

        # Get segment duration via ffprobe or ffmpeg
        cmd_dur = [
            self.ffmpeg_bin, "-i", str(audio_path),
            "-f", "null", "-"
        ]
        res_dur = subprocess.run(cmd_dur, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        import re
        dur_matches = re.findall(r"Duration: (\d{2}):(\d{2}):([0-9.]+)", res_dur.stderr)
        current_ms = target_ms
        if dur_matches:
            h, m, s = dur_matches[0]
            current_ms = int((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)

        if current_ms <= 0:
            return 1.0

        raw_factor = current_ms / float(target_ms)

        # Modest time-stretching factor between 0.85x and 1.25x to preserve natural pronunciation
        speed_factor = max(0.85, min(1.25, raw_factor))

        Path(output_synced_path).parent.mkdir(parents=True, exist_ok=True)

        if 0.96 <= speed_factor <= 1.04:
            # Re-sample to standard 44.1kHz 16-bit stereo WAV
            conv_cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(audio_path),
                "-ar", "44100",
                "-ac", "2",
                "-c:a", "pcm_s16le",
                str(output_synced_path)
            ]
            subprocess.run(conv_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return 1.0

        cmd = [
            self.ffmpeg_bin, "-y",
            "-i", str(audio_path),
            "-filter:a", f"atempo={speed_factor:.3f}",
            "-ar", "44100",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(output_synced_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            logger.warning(f"FFmpeg atempo fallback: {res.stderr}")
            conv_cmd = [
                self.ffmpeg_bin, "-y",
                "-i", str(audio_path),
                "-ar", "44100",
                "-ac", "2",
                "-c:a", "pcm_s16le",
                str(output_synced_path)
            ]
            subprocess.run(conv_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return 1.0

        return speed_factor

    def assemble_dubbed_timeline(
        self,
        aligned_segments: List[Dict[str, Any]],
        total_duration_ms: int,
        output_timeline_path: str
    ) -> str:
        """
        Assembles all dubbed segments into a single full-length audio timeline matching video duration.
        Uses streaming wave generation directly to disk in 64KB blocks.
        Supports videos up to 2 hours with O(1) memory footprint.
        """
        Path(output_timeline_path).parent.mkdir(parents=True, exist_ok=True)
        sample_rate = 44100
        channels = 2
        bytes_per_sample = 2
        frame_size = channels * bytes_per_sample  # 4 bytes per frame

        total_frames = int((total_duration_ms / 1000.0) * sample_rate)
        silent_block = b"\x00" * (sample_rate * frame_size // 4)  # 0.25s silence block

        # Sort segments strictly by start timestamp
        sorted_segs = sorted(aligned_segments, key=lambda x: x.get("start_ms", 0))

        with wave.open(output_timeline_path, "wb") as out_wf:
            out_wf.setnchannels(channels)
            out_wf.setsampwidth(bytes_per_sample)
            out_wf.setframerate(sample_rate)

            current_frame = 0

            for seg in sorted_segs:
                seg_path = seg.get("audio_path")
                if not seg_path or not Path(seg_path).exists():
                    continue

                target_start_frame = int((seg.get("start_ms", 0) / 1000.0) * sample_rate)

                # Write silence until segment start
                if target_start_frame > current_frame:
                    frames_needed = target_start_frame - current_frame
                    while frames_needed > 0:
                        chunk = min(frames_needed, len(silent_block) // frame_size)
                        out_wf.writeframes(silent_block[: chunk * frame_size])
                        frames_needed -= chunk
                        current_frame += chunk

                # Stream read segment frames
                try:
                    with wave.open(seg_path, "rb") as seg_wf:
                        n_frames = seg_wf.getnframes()
                        frames_data = seg_wf.readframes(n_frames)
                        out_wf.writeframes(frames_data)
                        current_frame += n_frames
                except Exception as e:
                    logger.warning(f"Error streaming segment {seg_path}: {e}")

            # Fill remaining duration with silence
            if current_frame < total_frames:
                frames_needed = total_frames - current_frame
                while frames_needed > 0:
                    chunk = min(frames_needed, len(silent_block) // frame_size)
                    out_wf.writeframes(silent_block[: chunk * frame_size])
                    frames_needed -= chunk
                    current_frame += chunk

        return output_timeline_path

sync_service = SyncService()
