# Provider Pattern — LLM and Embeddings

## What it is

A thin `Protocol` interface that sits between business logic and any vendor SDK.
All services that need an LLM or embeddings depend on the interface, never on a
concrete implementation.

## Why we need it

Without an abstraction, calling Ollama looks like this scattered across the codebase:

```python
# BAD — vendor SDK imported directly in business logic
import ollama
response = ollama.chat(model="llama3", messages=[...])
```

When you want to switch to OpenAI in production, you hunt down every call site.
You also cannot unit-test the service without a running Ollama instance.

With a provider interface:

```python
# GOOD — business logic depends on the interface
class GenerationService:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate_questions(self, chunks, config):
        return await self.llm.complete(messages, QuestionList)
```

Switching to OpenAI = swap the injected instance. Tests use a `FakeLLMProvider`.

## The interfaces

```python
# app/services/providers/base.py

from typing import Protocol, TypeVar, runtime_checkable
from dataclasses import dataclass

T = TypeVar("T")

@dataclass
class Message:
    role: str   # "system" | "user" | "assistant"
    content: str

@runtime_checkable
class LLMProvider(Protocol):
    """
    Wraps any LLM backend.
    `schema` is a Pydantic model class — the provider must return a validated instance.
    Using Pydantic here enforces structured output at the interface level,
    so callers never deal with raw JSON parsing.
    """
    async def complete(self, messages: list[Message], schema: type[T]) -> T: ...

@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Wraps any embedding backend.
    Returns a list of float vectors, one per input text.
    Dimensionality is provider-specific; callers must not hardcode it.
    """
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    def dimensions(self) -> int: ...
```

### Why `Protocol` instead of ABC?

`Protocol` enables structural subtyping — a class satisfies the interface if it has
the right methods, without inheriting from a base class. This means third-party
wrappers can be used without modification. `runtime_checkable` allows `isinstance`
checks if needed in tests or factory code.

## Concrete implementations

```
app/services/providers/
  base.py               # Protocol definitions above
  ollama_provider.py    # OllamaLLMProvider
  openai_provider.py    # OpenAILLMProvider
  sentence_transformer_provider.py  # SentenceTransformerEmbeddingProvider
  openai_embedding_provider.py      # OpenAIEmbeddingProvider
```

Each file contains exactly one class and nothing else — easy to locate and test.

## Configuration and registration

```python
# app/config.py
class Settings(BaseSettings):
    LLM_PROVIDER: str = "ollama"          # "ollama" | "openai" | "anthropic"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    EMBEDDING_PROVIDER: str = "sentence_transformer"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
```

```python
# app/dependencies.py — provider factory, called once at startup
def get_llm_provider(settings: Settings) -> LLMProvider:
    match settings.LLM_PROVIDER:
        case "ollama":   return OllamaLLMProvider(settings)
        case "openai":   return OpenAILLMProvider(settings)
        case _:          raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")

def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    match settings.EMBEDDING_PROVIDER:
        case "sentence_transformer": return SentenceTransformerEmbeddingProvider(settings)
        case "openai":               return OpenAIEmbeddingProvider(settings)
        case _:                      raise ValueError(...)
```

## Switching providers in practice

Dev (default `.env`):
```
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=sentence_transformer
```

Production `.env`:
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_PROVIDER=sentence_transformer   # stays local — no per-embed API cost
```

Zero business logic changes. The only files touched are `.env` and possibly
`app/dependencies.py` if a new provider type is added.

## Testing

```python
class FakeLLMProvider:
    """Returns a fixed response — used in unit tests."""
    async def complete(self, messages, schema):
        return schema.model_validate(FIXTURE_RESPONSE)
```

Because services accept the `Protocol`, `FakeLLMProvider` satisfies it without
any inheritance. Tests run instantly with no external process.
