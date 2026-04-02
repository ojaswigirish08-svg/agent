import os
import asyncio
import boto3
from providers.tts.base import BaseTTSProvider


class PollyAdapter(BaseTTSProvider):

    def __init__(self, voice_id: str, engine: str, language_code: str):
        self.voice_id = voice_id
        self.engine = engine
        self.language_code = language_code
        self.client = boto3.client(
            "polly",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "ap-south-1")
        )

    async def synthesize(self, text: str) -> bytes:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> bytes:
        response = self.client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=self.voice_id,
            Engine=self.engine,
            LanguageCode=self.language_code
        )
        return response["AudioStream"].read()