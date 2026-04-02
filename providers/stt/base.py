from abc import ABC, abstractmethod
from typing import Dict


class BaseSTTProvider(ABC):

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes
    ) -> str:
        pass

    @abstractmethod
    async def transcribe_with_confidence(
        self,
        audio_bytes: bytes
    ) -> Dict:
        pass