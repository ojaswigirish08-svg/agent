from abc import ABC, abstractmethod
from typing import List, Dict


class BaseLLMProvider(ABC):

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict],
        system_prompt: str = None
    ) -> str:
        pass

    @abstractmethod
    async def generate_json(
        self,
        messages: List[Dict],
        system_prompt: str = None
    ) -> dict:
        pass