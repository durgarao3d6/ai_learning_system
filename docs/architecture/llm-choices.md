# LLM Choices — Why Ollama for Dev, OpenAI for Prod

## Dev: Ollama

Ollama runs open-weight models locally via a Docker container or native binary.

Why we use it for development:
- No API key required — new contributors can clone and run immediately
- No per-token cost during development and testing
- Responses are deterministic enough for iterative prompt tuning
- Works offline, so ingestion + generation tests don't need internet
- The `ollama pull llama3.2` model is small enough (~2 GB) to run on most dev laptops

Recommended dev model: `llama3.2` (3B) for speed, `llama3.1:8b` for quality.

```bash
# Start Ollama
ollama serve

# Pull the model once
ollama pull llama3.2
```

The backend connects to `http://localhost:11434` by default (configurable via `OLLAMA_BASE_URL`).

## Prod: OpenAI (or any provider)

OpenAI's structured output mode (`response_format={"type": "json_schema", ...}`) guarantees
the response matches a JSON schema. This is critical for quiz generation — a malformed question
JSON is a user-facing failure.

Ollama's JSON mode is less reliable for complex schemas, so for production workloads we
recommend switching to OpenAI `gpt-4o-mini` (cost-effective) or `gpt-4o` (higher quality).

Because all LLM calls go through the `LLMProvider` interface, switching is one env var:
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

## Why not hardcode one provider

If we hardcode Ollama, production deployments need a GPU server just for inference.
If we hardcode OpenAI, local development costs money and requires internet.
The provider abstraction gives us both without any coupling.

## Structured output across providers

The `LLMProvider.complete()` interface accepts a Pydantic schema and always returns
a validated model instance. Each provider implementation handles structured output
differently:

| Provider | Mechanism |
|---|---|
| Ollama | `format="json"` + parse + Pydantic validate |
| OpenAI | `response_format=json_schema` (native structured output) |
| Anthropic | Tool-use trick — schema passed as a tool definition |

All of this complexity is hidden inside the provider class. Callers just pass a Pydantic model.
