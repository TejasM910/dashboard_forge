"""LLM Provider abstraction supporting Zero-Cost options (Gemini Free Tier, Ollama, Mock)."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMResponse(BaseModel):
    content: str
    parsed: Optional[Any] = None
    tokens_used: int = 0
    model: str = "mock"


class BaseLLMProvider(ABC):
    """Abstract interface for LLM calls with structured output and cost/token awareness."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Generate unstructured text completion."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> T:
        """Generate structured output validated against a Pydantic model."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider for unit tests, offline runs, and CI ($0 cost)."""

    def __init__(self, canned_responses: Optional[Dict[str, Any]] = None):
        self.canned_responses = canned_responses or {}

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        content = self.canned_responses.get("text", "Mock LLM text response")
        return LLMResponse(content=content, tokens_used=10, model="mock")

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> T:
        if response_model.__name__ in self.canned_responses:
            data = self.canned_responses[response_model.__name__]
            if isinstance(data, str):
                return response_model.model_validate_json(data)
            return response_model.model_validate(data)
        
        # Provide minimal valid default instantiation if possible
        try:
            return response_model()
        except Exception:
            raise ValueError(f"No canned response provided for model {response_model.__name__}")
