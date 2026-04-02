import io
import asyncio
import tempfile
import os
from typing import Dict
from providers.stt.base import BaseSTTProvider


class WhisperAdapter(BaseSTTProvider):

    def __init__(self, model: str = "base", language: str = "en"):
        self.model_name = model
        self.language = language
        self._model = None

    def _load_model(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_name)
        return self._model

    async def transcribe(self, audio_bytes: bytes) -> str:
        result = await self._run_transcription(audio_bytes)
        return result.get("text", "").strip()

    async def transcribe_with_confidence(self, audio_bytes: bytes) -> Dict:
        result = await self._run_transcription(audio_bytes)
        text = result.get("text", "").strip()
        segments = result.get("segments", [])
        avg_confidence = 0.0
        if segments:
            scores = [s.get("avg_logprob", 0) for s in segments]
            avg_confidence = sum(scores) / len(scores)
            avg_confidence = max(0.0, min(1.0, (avg_confidence + 1.0)))
        return {
            "text": text,
            "confidence": avg_confidence,
            "language": result.get("language", self.language)
        }

    async def _run_transcription(self, audio_bytes: bytes) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, audio_bytes)

    def _transcribe_sync(self, audio_bytes: bytes) -> dict:
        model = self._load_model()
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            result = model.transcribe(
                tmp_path,
                language=self.language,
                fp16=False
            )
            return result
        finally:
            os.unlink(tmp_path)