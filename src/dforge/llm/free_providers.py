import os
import json
import httpx
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel
from dforge.llm.provider import BaseLLMProvider, LLMResponse

T = TypeVar("T", bound=BaseModel)


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini API Provider with structured output via JSON schema (free tier)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        headers = {"Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return LLMResponse(content=text, model=self.model)

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> T:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        schema = response_model.model_json_schema()
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return response_model.model_validate_json(text)


class OllamaLLMProvider(BaseLLMProvider):
    """Local Ollama Provider (100% offline, $0 cost, e.g. Qwen 2.5 Coder / Llama 3)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:7b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            text = resp.json().get("response", "")
            return LLMResponse(content=text, model=self.model)

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> T:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            text = resp.json().get("response", "")
            return response_model.model_validate_json(text)
