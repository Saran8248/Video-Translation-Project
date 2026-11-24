# Video Translation & AI Dubbing Platform (Tamil & Multilingual)

A full-stack, enterprise-grade AI video dubbing system built following the **TranslateMom Technical Blueprint**. It automatically transcribes spoken audio with timestamps, performs speaker diarization, translates dialogue into natural spoken Tamil (with conversational vs. formal register support), synthesizes neural voices with gender and speaker mapping, dynamically fits audio to original speech windows via time-stretching (`atempo`), ducks/preserves background music, and muxes the result into high-definition MP4.

---

## 🚀 Key Features

1. **Complete Video Dubbing Pipeline**:
   - **Upload & Media Inspection**: Automatic validation of codecs, resolution, FPS, channels, and sample rate via PyAV and FFmpeg.
   - **Speech-to-Text with Timestamps**: High-accuracy transcription returning timed segments `[start_ms, end_ms]`.
   - **Speaker Diarization**: Estimates speaker turns and neutral labels (`speaker_1`, `speaker_2`) using acoustic zero-crossing rates and energy modeling.
   - **Context-Aware Spoken Tamil Translation**: Translates into natural spoken Tamil with colloquial register options (conversational vs. formal).
   - **Neural Text-to-Speech (TTS)**: Broadcast-quality voices for Tamil (`ta-IN-ValluvarNeural`, `ta-IN-PallaviNeural`, `ta-LK`, `ta-SG`) with male/female mapping, plus Hindi, English, German, and Spanish.
   - **Timing & Audio Synchronization**: Modest time-stretching via FFmpeg `atempo` (factors between 0.85x and 1.25x) to fit target segments without pitch distortion.
   - **Audio Mixing & Video Muxing**:
     - *Basic mode*: Cleanly replaces source speech.
     - *Advanced mode*: Ducks background music and mixes synthesized dialogue.
     - Encoded into H.264 video + AAC audio MP4.

2. **Interactive UI & Segment Editor**:
   - Modern React + TypeScript + Tailwind CSS dark-themed dashboard.
   - Live multi-stage progress tracking (0–100%) matching blueprint milestones.
   - Interactive transcript editor with inline text editing, speaker selection, and segment audio preview.
   - Native HTML5 video player with dual-track toggle (Original Audio vs. Tamil Dubbed Audio) and live synchronized subtitle overlay.
   - Built-in **"Quick Test: Generate German Interview"** button to generate a 2-speaker German interview clip and test dubbing in 1-click.

3. **REST API (Section 6 Blueprint Compliant)**:
   - `POST /api/v1/videos/upload-session` & `POST /api/v1/videos/upload`: Upload video and inspect streams.
   - `POST /api/v1/dubbing/jobs`: Create job with language, mode, and voice settings (returns HTTP 202 Accepted).
   - `GET /api/v1/dubbing/jobs/{id}`: Read status and progress.
   - `GET /api/v1/dubbing/jobs/{id}/segments`: Read source and translated timed segments.
   - `PATCH /api/v1/dubbing/jobs/{id}/segments/{segmentId}`: Edit translated text or timing.
   - `POST /api/v1/dubbing/jobs/{id}/retry`: Retry failed stage or job.
   - `POST /api/v1/dubbing/jobs/{id}/export`: Re-render final video from updated segments.
   - `GET /api/v1/dubbing/jobs/{id}/download`: Download final MP4.
   - `GET /api/v1/voices`: Query neural voices filtered by locale.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2 |
| **Database** | SQLite / PostgreSQL via SQLAlchemy ORM (Users, VideoAssets, DubbingJobs, Speakers, Segments, Exports, UsageLedger) |
| **Media Engine** | FFmpeg 9.0, PyAV, Pydub |
| **Speech Recognition** | SpeechRecognition (Google STT), Faster-Whisper / OpenAI Whisper API |
| **Translation** | Deep Translator (MyMemory, Google) + OpenAI LLM context prompt |
| **Text-to-Speech** | Edge-TTS (Microsoft Azure Neural Voices) & gTTS fallback |

---

## ⚡ Quick Start

### 1. Run the Application
The single runner serves the FastAPI backend and built React frontend together:
```bash
python run.py
```
Open your web browser at:
- **Application UI**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Run the End-to-End Automated Test
Verify the full pipeline (generate German video -> transcribe -> diarize -> translate to Tamil -> synthesize TTS -> time-stretch -> mix/mux MP4 -> edit segment -> re-export):
```bash
python test_e2e_dubbing.py
```

### 3. Frontend Development (Optional)
If modifying the React frontend:
```bash
cd frontend
npm run dev
```
Runs at [http://localhost:3000](http://localhost:3000) with automatic proxying to the FastAPI backend.
