"""OpenAI LLM provider stub for Phase 2."""

from typing import Any

from app.services.providers.base import Message, T


class OpenAILLMProvider:
    """Stub implementation of LLMProvider for OpenAI."""

    def __init__(
        self,
        settings: Any = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        if settings is not None:
            self.api_key = getattr(settings, "OPENAI_API_KEY", "")
            self.model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        else:
            self.api_key = api_key or ""
            self.model = model or "gpt-4o-mini"

    async def complete(self, messages: list[Message], schema: type[T]) -> T:
        """Generate structured completion via OpenAI (Phase 2 stub)."""
        raise NotImplementedError("OpenAI provider is configured in Phase 2")
