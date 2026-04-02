from abc import ABC, abstractmethod


class BaseTTSProvider(ABC):

    @abstractmethod
    async def synthesize(
        self,
        text: str
    ) -> bytes:
        pass