"""
Sarvam service — Indian-language Speech-to-Text, Text-to-Speech, and
Translation, using the official `sarvamai` Python SDK.

Reference (verified against docs.sarvam.ai on integration date):
  - Auth: `api_subscription_key` (also accepts `Authorization: Bearer`), handled by the SDK.
  - STT:  client.speech_to_text.transcribe(file=..., model="saaras:v3", language_code=...)
  - TTS:  client.text_to_speech.convert(text=..., language_code=..., model="bulbul:v3", speaker=...)
          -> returns base64-encoded WAV audio in `audios[0]`.
  - Translate: client.text.translate(input=..., source_language_code=..., target_language_code=...)
"""

from __future__ import annotations

import io

from sarvamai import SarvamAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.core.exceptions import UpstreamProviderError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SarvamService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)

    # -- Speech to Text --------------------------------------------------

    @retry(reraise=True, stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=6))
    def transcribe(self, *, audio_bytes: bytes, filename: str) -> tuple[str, str | None]:
        """Returns (transcript, detected_language_code)."""
        try:
            response = self._client.speech_to_text.transcribe(
                file=(filename, io.BytesIO(audio_bytes)),
                model=self._settings.SARVAM_STT_MODEL,
            )
        except Exception as exc:  # SDK raises provider-specific exceptions
            logger.error("Sarvam STT error: %s", exc)
            raise UpstreamProviderError(
                "Speech-to-text provider (Sarvam) failed to process the audio.",
                details={"provider": "sarvam", "reason": str(exc)},
            ) from exc

        transcript = getattr(response, "transcript", None) or ""
        language_code = getattr(response, "language_code", None)

        if not transcript.strip():
            raise UpstreamProviderError(
                "Speech-to-text returned an empty transcript. Please try re-recording clearly.",
                details={"provider": "sarvam"},
            )
        return transcript.strip(), language_code

    # -- Text to Speech ----------------------------------------------------

    @retry(reraise=True, stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=6))
    def synthesize(
        self, *, text: str, language_code: str, speaker: str | None = None
    ) -> tuple[str, int]:
        """Returns (base64_wav_audio, sample_rate)."""
        try:
            response = self._client.text_to_speech.convert(
                text=text,
                target_language_code=language_code,
                model=self._settings.SARVAM_TTS_MODEL,
                speaker=speaker or self._settings.SARVAM_TTS_SPEAKER,
            )
        except Exception as exc:
            logger.error("Sarvam TTS error: %s", exc)
            raise UpstreamProviderError(
                "Text-to-speech provider (Sarvam) failed to synthesize audio.",
                details={"provider": "sarvam", "reason": str(exc)},
            ) from exc

        audios = getattr(response, "audios", None) or []
        if not audios:
            raise UpstreamProviderError(
                "Text-to-speech provider returned no audio.",
                details={"provider": "sarvam"},
            )
        return audios[0], 22050

    # -- Translation ---------------------------------------------------

    @retry(reraise=True, stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=6))
    def translate(
        self, *, text: str, source_language_code: str, target_language_code: str
    ) -> tuple[str, str]:
        """Returns (translated_text, detected_source_language_code)."""
        if source_language_code == target_language_code:
            return text, source_language_code

        try:
            response = self._client.text.translate(
                input=text,
                source_language_code=source_language_code,
                target_language_code=target_language_code,
                model=self._settings.SARVAM_TRANSLATE_MODEL,
            )
        except Exception as exc:
            logger.error("Sarvam translate error: %s", exc)
            raise UpstreamProviderError(
                "Translation provider (Sarvam) failed to translate the text.",
                details={"provider": "sarvam", "reason": str(exc)},
            ) from exc

        translated_text = getattr(response, "translated_text", None) or ""
        detected_source = getattr(response, "source_language_code", source_language_code)

        if not translated_text.strip():
            raise UpstreamProviderError(
                "Translation provider returned empty text.",
                details={"provider": "sarvam"},
            )
        return translated_text.strip(), detected_source
