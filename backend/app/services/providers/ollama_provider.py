"""Ollama LLM provider implementation."""

from typing import Any

import httpx
from pydantic import BaseModel

from app.services.providers.base import Message, T


class OllamaLLMProvider:
    """LLM provider using local Ollama instance with structured JSON mode."""

    def __init__(
        self,
        settings: Any = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        if settings is not None:
            self.base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
            self.model = getattr(settings, "OLLAMA_MODEL", "llama3.2")
        else:
            self.base_url = base_url or "http://localhost:11434"
            self.model = model or "llama3.2"
        self.timeout = timeout

    async def complete(self, messages: list[Message], schema: type[T]) -> T:
        """Call Ollama /api/chat with format='json' and validate against schema."""
        endpoint = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "format": "json",
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
            except Exception as exc:
                raise RuntimeError(f"Ollama API request failed: {exc}") from exc

        try:
            data = response.json()
            message_content = data.get("message", {}).get("content", "")
            if isinstance(schema, type) and issubclass(schema, BaseModel) or hasattr(schema, "model_validate_json"):
                return schema.model_validate_json(message_content)
            else:
                import json
                parsed = json.loads(message_content)
                if hasattr(schema, "model_validate"):
                    return schema.model_validate(parsed)
                return parsed  # type: ignore[return-value]
        except Exception as exc:
            raise RuntimeError(
                f"Failed to parse and validate Ollama response into {schema}: {exc}"
            ) from exc
