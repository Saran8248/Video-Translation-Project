from typing import List, Optional
from fastapi import APIRouter, Query
from ..services.tts_service import tts_service
from ..schemas import VoiceOption

router = APIRouter(prefix="/api/v1/voices", tags=["voices"])

@router.get("", response_model=List[VoiceOption])
def list_voices(locale: Optional[str] = Query(None, description="Filter by locale or language, e.g. ta-IN or ta")):
    """
    Returns available neural TTS voices with gender, language, and locale.
    """
    voices = tts_service.get_available_voices(locale)
    return [
        VoiceOption(
            id=v["id"],
            name=v["name"],
            gender=v["gender"],
            locale=v["locale"],
            language=v["language"],
            provider=v["provider"]
        )
        for v in voices
    ]
