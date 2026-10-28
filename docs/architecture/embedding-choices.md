# Embedding Choices — In-Process `all-MiniLM-L6-v2` with Zero-Code OpenAI Migration

## What it is
We use the local, open-source `sentence-transformers/all-MiniLM-L6-v2` model running in-process for generating vector embeddings in development and default deployments. All embedding operations are mediated by an `EmbeddingProvider` Protocol, allowing an instant, zero-code transition to cloud providers like OpenAI (`text-embedding-3-small` or `text-embedding-3-large`) strictly through configuration.

## Why we need it / Why this approach
Embedding generation is a core pipeline step in Retrieval-Augmented Generation (RAG). Every uploaded lecture note or document must be chunked and converted into dense numerical vectors.
1. **Zero per-embed API cost**: Ingestion runs frequently during student note uploads. A single 50-page document sliced into 500 chunks sent to an external API incurs recurring monetary cost and rate-limit concerns. While OpenAI charges ~$0.02 per 1M tokens for `text-embedding-3-small`, repeated testing, re-indexing, and multiple users accumulate tangible costs. A local model costs $0.00.
2. **In-process execution without network latency**: Local embeddings run inside the FastAPI Python process on CPU. There are no HTTP round-trips, no TLS handshakes, no DNS lookups, no third-party downtime, and no rate-limit 429 throttling. For a batch of 100 chunks, `all-MiniLM-L6-v2` processes in ~80ms on standard modern CPU hardware.
3. **Offline development and testing**: Developers and CI test runners can run the full ingestion and retrieval suite completely offline with no API keys, no internet connection, and zero external service dependencies.
4. **Lightweight footprint**: `all-MiniLM-L6-v2` has only 22 million parameters and produces 384-dimensional embeddings. The model weights require under 90MB of disk space and under 300MB of RAM, making it easily runnable on any developer laptop or cheap cloud instance without requiring a GPU.
5. **Decoupled dimensionality**: Different models output vectors of different sizes (e.g., 384 for MiniLM vs 1536 for OpenAI `text-embedding-3-small`). The `EmbeddingProvider` protocol exposes a `.dimensions()` method. Chroma collections and vector indexes retrieve dimensionality dynamically at runtime, preventing hardcoded vector size bugs.

## Alternatives considered
| Option | Why rejected |
|---|---|
| OpenAI embeddings (`text-embedding-3-small/large`) from day one | Incurs monetary cost per chunk, requires an active internet connection and valid API keys for every developer, introduces latency over the wire, and subjects tests to external rate limits. |
| Self-hosted TEI (Text Embeddings Inference) or Ollama embeddings | Adds another daemon or Docker container process to manage locally, defeating the goal of zero-friction onboarding. |
| Larger local models (`e5-mistral-7b-instruct` or `bge-large-en-v1.5`) | Model size exceeds 1.5GB to 14GB, requiring dedicated GPU VRAM and causing unacceptably slow CPU inference times (>2 seconds per chunk). |
| Static TF-IDF or BM25 only | Lacks semantic understanding. Fails to capture synonyms, paraphrasing, or conceptual matches between student questions and study notes. |

## Implementation details

The architecture defines the contract in `backend/app/services/providers/base.py` and implements concrete adapters in `backend/app/services/providers/`.

### 1. The `EmbeddingProvider` Protocol
```python
# backend/app/services/providers/base.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class EmbeddingProvider(Protocol):
    """
    Wraps any embedding backend.
    Returns a list of float vectors, one per input text.
    Dimensionality is provider-specific; callers must never hardcode it.
    """
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate dense vector embeddings for a list of input texts."""
        ...

    def dimensions(self) -> int:
        """Return the vector dimensionality (e.g. 384 for MiniLM, 1536 for OpenAI)."""
        ...
```

### 2. Concrete Implementation: Local SentenceTransformers
```python
# backend/app/services/providers/sentence_transformer_provider.py
import asyncio
from sentence_transformers import SentenceTransformer
from app.config import Settings
from app.services.providers.base import EmbeddingProvider

class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings):
        # Model is loaded once at worker initialization
        self.model_name = settings.EMBEDDING_MODEL  # default: "sentence-transformers/all-MiniLM-L6-v2"
        self.model = SentenceTransformer(self.model_name)
        self._dim = self.model.get_sentence_embedding_dimension()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Run CPU-bound PyTorch inference in an async worker thread
        embeddings = await asyncio.to_thread(
            self.model.encode,
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def dimensions(self) -> int:
        return self._dim
```

### 3. Concrete Implementation: OpenAI Embeddings
```python
# backend/app/services/providers/openai_embedding_provider.py
from openai import AsyncOpenAI
from app.config import Settings
from app.services.providers.base import EmbeddingProvider

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL  # default: "text-embedding-3-small"
        self._dim = 1536 if "large" not in self.model else 3072

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model,
        )
        return [record.embedding for record in response.data]

    def dimensions(self) -> int:
        return self._dim
```

### 4. Chroma Collection Initialization Using Dynamic Dimensions
```python
# backend/app/services/rag/vector_store.py
import chromadb
from app.services.providers.base import EmbeddingProvider

class VectorStoreService:
    def __init__(self, client: chromadb.ClientAPI, embedding_provider: EmbeddingProvider):
        self.client = client
        self.provider = embedding_provider

    def get_or_create_collection(self, quiz_id: str):
        # Dimensions are queried from the provider, never hardcoded to 384 or 1536
        return self.client.get_or_create_collection(
            name=f"quiz_docs_{quiz_id}",
            metadata={"hnsw:space": "cosine", "dimensions": self.provider.dimensions()}
        )
```

### 5. Switching Providers via Configuration
Switching from local embeddings to OpenAI requires zero code modifications:

```bash
# In .env:
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## Tradeoffs and known limitations
1. **Semantic quality gap on long, complex documents**: `all-MiniLM-L6-v2` has a maximum context window of 256 tokens and exhibits lower semantic precision on complex academic or technical terminology compared to state-of-the-art models like `text-embedding-3-large` or `bge-large-en-v1.5`. We compensate for this in Phase 3 by adding a cross-encoder re-ranking step.
2. **First-run download**: On the very first run, PyTorch downloads the model weights (~90MB) from Hugging Face Hub. In restricted corporate or offline-first CI networks, the model cache directory must be pre-populated or mounted as a volume.
3. **CPU blocking in async event loop**: Model inference is CPU-bound and GIL-holding. All calls to `model.encode()` must be dispatched via `asyncio.to_thread()` to prevent blocking FastAPI's asynchronous event loop.
4. **Vector space migration**: Switching embedding models invalidates all previously generated Chroma vector embeddings. If `EMBEDDING_PROVIDER` is changed in an existing environment, existing document collections must be fully re-indexed.
