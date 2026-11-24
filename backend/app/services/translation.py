import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from deep_translator import MyMemoryTranslator, GoogleTranslator
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# German Slang, Idioms, Informal Particles & Conversational Phrases
# ---------------------------------------------------------------------------
GERMAN_IDIOMS_AND_SLANG: Dict[str, str] = {
    # Slang & Colloquialisms
    "alles klar": "எல்லாம் சரியா இருக்கு",
    "na und": "அதுக்கென்ன இப்போ?",
    "na und?": "அதுக்கென்ன இப்போ?",
    "keine ahnung": "எனக்கு ஒண்ணும் தெரியல",
    "ich habe keine ahnung": "எனக்கு சுத்தமா ஒண்ணும் தெரியல",
    "ich hab keine ahnung": "எனக்கு சுத்தமா ஒண்ணும் தெரியல",
    "keinen bock": "விருப்பமில்லை",
    "ich habe keinen bock": "எனக்கு சுத்தமா விருப்பமில்லை",
    "ich hab keinen bock": "எனக்கு சுத்தமா விருப்பமில்லை",
    "bock haben": "ஆசையா இருக்கு",
    "ich habe bock": "எனக்கு ரொம்ப ஆசையா இருக்கு",
    "ich hab bock": "எனக்கு ரொம்ப ஆசையா இருக்கு",
    "hau ab": "இங்கிருந்து கிளம்பு",
    "mach's gut": "பார்த்து பத்திரமா போயிட்டு வா",
    "machs gut": "பார்த்து பத்திரமா போயிட்டு வா",
    "moin": "வணக்கம்",
    "moin moin": "வணக்கம்",
    "na klar": "கண்டிப்பா",
    "klar": "கண்டிப்பா",
    "das ist geil": "அட இது ரொம்ப சூப்பரா இருக்கே",
    "echt geil": "ரொம்ப அற்புதம்",
    "geil": "அருமை",
    "so ein quatsch": "தேவையில்லாத வீண் பேச்சு",
    "quatsch": "வீண் பேச்சு",
    "laber keinen quatsch": "தேவையில்லாம உளறாதீங்க",
    "locker bleiben": "பதட்டப்படாம பொறுமையா இருங்க",
    "bleib locker": "பொறுமையா இரு",
    "auf jeden fall": "கண்டிப்பா",
    "auf keinen fall": "வாய்ப்பே இல்ல",
    "komm schon": "வாங்களேன்",
    "was geht ab": "என்ன விஷயம்? என்ன நடக்குது?",
    "was geht": "என்ன விஷயம்?",
    "das gibt's doch gar nicht": "இதை நம்பவே முடியலையே",
    "das gibts doch gar nicht": "இதை நம்பவே முடியலையே",
    "schwein gehabt": "நல்ல வேளை, அதிர்ஷ்டம் அடிச்சிருச்சு",
    "ich verstehe nur bahnhof": "எனக்கு இதுல ஒரு வார்த்தை கூட புரியல",
    "daumen drücken": "நல்லபடியா நடக்கணும்னு வாழ்த்துறேன்",
    "pass auf": "கொஞ்சம் கவனமா இருங்க",
    "halt die klappe": "வாயை மூடு",
    "nicht der rede wert": "பரவாயில்ல, அது ஒண்ணும் பெரிய விஷயம் இல்ல",
    "macht nichts": "பரவாயில்லை, விடுங்க",
    "ach so": "அப்படியா விஷயம்!",
    "genau": "சரியா சொன்னீங்க",
    "wahnsinn": "ஆச்சரியமா இருக்கு",
    "hör mal zu": "நான் சொல்றத கொஞ்சம் கேளுங்க",
    "hör mal": "கொஞ்சம் கேளுங்க",
    "hör zu": "கேளுங்க",
    "kein problem": "பிரச்சனையே இல்லை",
    "kein thema": "விஷயமே இல்லை",

    # Standard greetings and conversational courtesies
    "guten morgen": "காலை வணக்கம்",
    "guten tag": "வணக்கம்",
    "guten abend": "மாலை வணக்கம்",
    "hallo": "வணக்கம்",
    "servus": "வணக்கம்",
    "grüß gott": "வணக்கம்",
    "auf wiedersehen": "மீண்டும் சந்திப்போம்",
    "tschüss": "போயிட்டு வர்றேன்",
    "wie geht es ihnen": "எப்படி இருக்கீங்க?",
    "wie geht es dir": "எப்படி இருக்க?",
    "wie geht's": "எப்படி இருக்கீங்க?",
    "wie gehts": "எப்படி இருக்கீங்க?",
    "sehr gut": "ரொம்ப நல்லா இருக்கு",
    "gut, danke": "நல்லா இருக்கேன், நன்றி",
    "danke schön": "ரொம்ப நன்றி",
    "vielen dank": "ரொம்ப நன்றி",
    "herzlichen dank": "மனமார்ந்த நன்றி",
    "bitte schön": "பரவாயில்லை",
    "bitte": "தயவுசெய்து",
    "ja, natürlich": "ஆமாம், நிச்சயமாக",
    "natürlich": "நிச்சயமாக",
    "wir können anfangen": "நாம இப்போ ஆரம்பிக்கலாம்",
    "willkommen": "வரவேற்கிறோம்",
    "herzlich willkommen": "அன்புடன் வரவேற்கிறோம்",
    "ich freue mich": "எனக்கு ரொம்ப சந்தோஷமா இருக்கு",
    "ich freue mich sehr hier zu sein": "இங்கே இருப்பதில் எனக்கு ரொம்ப சந்தோஷம்",
    "alles läuft absolut nach plan": "எல்லாம் திட்டமிட்டபடி பக்காவா நடக்குது",
    "alles läuft nach plan": "எல்லாம் திட்டமிட்டபடி நடக்குது",
}

# ---------------------------------------------------------------------------
# Spoken Conversational Tamil Transformations
# Converts literary / written Tamil into authentic colloquial Tamil (பேச்சுத் தமிழ்)
# ---------------------------------------------------------------------------
CONVERSATIONAL_TAMIL_RULES: List[Tuple[str, str]] = [
    # Pronouns
    (r"\bநீங்கள்\b", "நீங்க"),
    (r"\bநாங்கள்\b", "நாங்க"),
    (r"\bஅவர்கள்\b", "அவங்க"),
    (r"\bஇவர்கள்\b", "இவங்க"),
    (r"\bஉங்களுக்கு\b", "உங்களுக்கு"),
    (r"\bஎங்களுக்கு\b", "எங்களுக்கு"),
    (r"\bஅவர்களுக்கு\b", "அவங்களுக்கு"),

    # Common verbs & endings
    (r"செய்கிறார்\b", "பண்றாரு"),
    (r"செய்கிறேன்\b", "பண்றேன்"),
    (r"செய்கிறீர்கள்\b", "பண்றீங்க"),
    (r"செய்கிறார்கள்\b", "பண்றாங்க"),
    (r"செய்கிறது\b", "பண்ணுது"),
    (r"வருகிறார்\b", "வர்றாரு"),
    (r"வருகிறேன்\b", "வர்றேன்"),
    (r"வருகிறீர்கள்\b", "வர்றீங்க"),
    (r"வருகிறார்கள்\b", "வர்றாங்க"),
    (r"போகிறார்\b", "போறாரு"),
    (r"போகிறேன்\b", "போறேன்"),
    (r"போகிறீர்கள்\b", "போறீங்க"),
    (r"போகிறார்கள்\b", "போறாங்க"),
    (r"இருக்கிறார்\b", "இருக்காரு"),
    (r"இருக்கிறேன்\b", "இருக்கேன்"),
    (r"இருக்கிறீர்கள்\b", "இருக்கீங்க"),
    (r"இருக்கிறார்கள்\b", "இருக்காங்க"),
    (r"இருக்கிறது\b", "இருக்கு"),
    (r"இருக்கின்றன\b", "இருக்கு"),

    # Particles & phrases
    (r"எப்படி இருக்கிறீர்கள்\?", "எப்படி இருக்கீங்க?"),
    (r"எப்படி இருக்கிறீர்கள்", "எப்படி இருக்கீங்க?"),
    (r"\bமிகவும்\b", "ரொம்ப"),
    (r"\bநன்றாக\b", "நல்லா"),
    (r"\bவிரைவாக\b", "சீக்கிரமா"),
    (r"\bதொடங்குவோம்\b", "ஆரம்பிக்கலாம்"),
    (r"\bஆரம்பிப்போம்\b", "ஆரம்பிக்கலாம்"),
    (r"\bஆம்\b", "ஆமா"),
    (r"\bஇல்லை\b", "இல்ல"),
    (r"\bநன்றி\b", "ரொம்ப நன்றி"),
    (r"\bசரி\b", "சரிங்க"),
    (r"\bஎங்கே\b", "எங்க"),
    (r"\bஎப்போது\b", "எப்போ"),
    (r"\bஎவ்வாறு\b", "எப்படி"),
]

class TranslationService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    def route_and_translate(
        self,
        text: str,
        detected_language: str,
        register: str = "conversational"
    ) -> Tuple[str, str]:
        """
        Implements the core language translation logic required by Section 1:
        - German (de) -> Natural Spoken Tamil (ta-IN)
        - English (en) -> Keep in English (en-US)
        - French (fr) -> Convert into English (en-US)
        - Spanish (es) -> Convert into English (en-US)
        - Any other language -> Convert into English (en-US)

        Returns: (translated_text, target_language_code)
        """
        clean_text = text.strip()
        if not clean_text or clean_text.startswith("["):
            # Empty or acoustic placeholder
            return clean_text, "ta-IN" if detected_language == "de" else "en-US"

        norm_lang = detected_language.lower().split("-")[0]

        # -------------------------------------------------------------
        # 1. German speech -> Spoken Tamil (ta-IN)
        # -------------------------------------------------------------
        if norm_lang == "de":
            tamil_text = self.translate_german_to_tamil(clean_text, register=register)
            return tamil_text, "ta-IN"

        # -------------------------------------------------------------
        # 2. English speech -> Keep in English (en-US)
        # -------------------------------------------------------------
        elif norm_lang == "en":
            # Keep in English, preserve original wording
            return clean_text, "en-US"

        # -------------------------------------------------------------
        # 3. French, Spanish, or any other language -> English (en-US)
        # -------------------------------------------------------------
        else:
            english_text = self.translate_to_english(clean_text, source_lang=norm_lang)
            return english_text, "en-US"

    def translate_german_to_tamil(
        self,
        text: str,
        register: str = "conversational"
    ) -> str:
        """
        Translates German dialogue into natural spoken Tamil.
        Preserves idioms, slang, intention, and conversational tone without literal word-by-word errors.
        """
        clean = text.strip()
        clean_lower = clean.lower().rstrip(".!?,")

        # 1. Exact or fuzzy match in German idioms & slang dictionary
        if clean_lower in GERMAN_IDIOMS_AND_SLANG:
            return GERMAN_IDIOMS_AND_SLANG[clean_lower]

        # Check if text contains a known German idiom/slang phrase
        for phrase, tamil_eq in GERMAN_IDIOMS_AND_SLANG.items():
            if phrase in clean_lower and len(phrase) > 5:
                # If the idiom constitutes most of the sentence, use or substitute it
                if len(phrase) >= len(clean_lower) * 0.65:
                    return tamil_eq

        # 2. Context-aware LLM translation if API key is provided
        if self.openai_api_key or self.gemini_api_key:
            try:
                llm_result = self._translate_with_llm(
                    text=clean,
                    source_lang="German",
                    target_lang="Spoken Tamil (conversational register - பேச்சுத் தமிழ்)",
                    instruction=(
                        "Translate this dialogue into natural spoken Tamil for dubbing. "
                        "Understand German slang, informal speech, idioms, and cultural expressions. "
                        "Avoid literal word-for-word translation. Preserve meaning, emotion, numbers, and speaker intent. "
                        "Do not add explanations or summarize. Keep it concise enough to fit the time window. "
                        "Return only the translated Tamil dialogue."
                    )
                )
                if llm_result:
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM translation fallback: {e}")

        # 3. Neural machine translation via MyMemory / Google Translator
        tamil_raw = self._translate_neural(clean, source_lang="de", target_lang="ta")

        # 4. Apply spoken Tamil conversational rules
        if register == "conversational":
            tamil_raw = self.apply_conversational_tamil(tamil_raw)

        return tamil_raw

    def translate_to_english(self, text: str, source_lang: str) -> str:
        """
        Converts non-German speech (French, Spanish, etc.) into clear, natural English.
        """
        clean = text.strip()
        if not clean:
            return clean

        # 1. Context-aware LLM if available
        if self.openai_api_key or self.gemini_api_key:
            try:
                llm_result = self._translate_with_llm(
                    text=clean,
                    source_lang=source_lang,
                    target_lang="English",
                    instruction=(
                        f"Translate this {source_lang} dialogue into natural, clear English for dubbing. "
                        "Preserve the meaning, speaker intent, and emotional tone. "
                        "Do not add commentary. Return only the translated English dialogue."
                    )
                )
                if llm_result:
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM English translation fallback: {e}")

        # 2. Neural machine translation
        eng_raw = self._translate_neural(clean, source_lang=source_lang, target_lang="en")
        # Clean any HTML entities or artifacts
        eng_clean = re.sub(r'^[>&; ]+', '', eng_raw).strip()
        return eng_clean

    def apply_conversational_tamil(self, text: str) -> str:
        """
        Applies conversational spoken Tamil rules (பேச்சுத் தமிழ்) to translated text.
        """
        result = text
        for pattern, replacement in CONVERSATIONAL_TAMIL_RULES:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def _translate_neural(self, text: str, source_lang: str, target_lang: str) -> str:
        s_code = source_lang.split("-")[0]
        t_code = target_lang.split("-")[0]

        # Try MyMemory
        try:
            src = f"{s_code}-{s_code.upper()}" if s_code in ["de", "en", "es", "fr", "it"] else s_code
            tgt = "ta-IN" if t_code == "ta" else "en-US" if t_code == "en" else t_code
            res = MyMemoryTranslator(source=src, target=tgt).translate(text)
            if res and not res.startswith("MYMEMORY WARNING"):
                # Clean up artifacts
                res = re.sub(r'^[>&; ]+', '', res).strip()
                return res
        except Exception as e:
            logger.debug(f"MyMemory translation exception: {e}")

        # Try GoogleTranslator fallback
        try:
            res = GoogleTranslator(source=s_code, target=t_code).translate(text)
            if res:
                return res.strip()
        except Exception as e:
            logger.debug(f"GoogleTranslator fallback exception: {e}")

        return text

    def _translate_with_llm(self, text: str, source_lang: str, target_lang: str, instruction: str) -> Optional[str]:
        if not self.openai_api_key:
            return None
        import httpx
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": text}
            ],
            "temperature": 0.3
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=12.0)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return None

    # Maintain backward compatibility method
    def translate_segment(
        self,
        text: str,
        source_lang: str = "de",
        target_lang: str = "ta-IN",
        register: str = "conversational"
    ) -> str:
        translated, _ = self.route_and_translate(text, detected_language=source_lang, register=register)
        return translated

translation_service = TranslationService()
