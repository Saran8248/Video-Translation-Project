import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import init_db
from .routers import videos, dubbing, voices
from .config import STORAGE_DIR

app = FastAPI(
    title="Video Translation & AI Dubbing API",
    description="Full-stack AI video dubbing system for Tamil and multilingual voice-over dubbing",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
def on_startup():
    init_db()

# Include routers
app.include_router(videos.router)
app.include_router(dubbing.router)
app.include_router(voices.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "video-translation-ai-dubbing"}

# If frontend build exists, serve it
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
