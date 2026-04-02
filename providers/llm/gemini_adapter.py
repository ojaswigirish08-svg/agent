import json
import os
from typing import List, Dict
from providers.llm.base import BaseLLMProvider


class GeminiAdapter(BaseLLMProvider):

    def __init__(self, model: str, temperature: float, max_tokens: int):
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        from google import genai
        from google.genai import types
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.types = types

    async def generate(
        self,
        messages: List[Dict],
        system_prompt: str = None
    ) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_sync, messages, system_prompt)

    async def generate_json(
        self,
        messages: List[Dict],
        system_prompt: str = None
    ) -> dict:
        if system_prompt:
            system_prompt += "\n\nRespond ONLY with valid JSON. No markdown, no backticks, no explanation."
        else:
            system_prompt = "Respond ONLY with valid JSON. No markdown, no backticks, no explanation."
        response = await self.generate(messages, system_prompt)
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip().rstrip("```").strip()
        return json.loads(clean)

    def _generate_sync(
        self,
        messages: List[Dict],
        system_prompt: str = None
    ) -> str:
        prompt = self._build_prompt(messages, system_prompt)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=self.types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens
            )
        )
        return response.text

    def _build_prompt(
        self,
        messages: List[Dict],
        system_prompt: str = None
    ) -> str:
        parts = []
        if system_prompt:
            parts.append(f"SYSTEM: {system_prompt}\n")
        for msg in messages:
            role = "USER" if msg["role"] == "user" else "ASSISTANT"
            parts.append(f"{role}: {msg['content']}")
        return "\n".join(parts)