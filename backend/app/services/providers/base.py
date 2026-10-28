"""Protocol definitions for LLM and Embedding providers."""

from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@dataclass
class Message:
    """Chat message representation."""

    role: str  # "system" | "user" | "assistant"
    content: str


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol defining the interface for LLM completion services."""

    async def complete(self, messages: list[Message], schema: type[T]) -> T:
        """Complete a prompt and return a validated Pydantic model instance."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol defining the interface for embedding generation services."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for input texts."""
        ...

    def dimensions(self) -> int:
        """Return the vector dimensionality of this embedding model."""
        ...
