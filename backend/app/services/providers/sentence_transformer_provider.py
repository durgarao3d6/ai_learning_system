"""SentenceTransformer embedding provider implementation."""

from typing import Any

from sentence_transformers import SentenceTransformer


class SentenceTransformerEmbeddingProvider:
    """In-process embedding provider using sentence-transformers."""

    def __init__(
        self,
        settings: Any = None,
        model_name: str | None = None,
    ) -> None:
        if settings is not None and hasattr(settings, "EMBEDDING_MODEL"):
            resolved_model = settings.EMBEDDING_MODEL
        elif model_name is not None:
            resolved_model = model_name
        else:
            resolved_model = "all-MiniLM-L6-v2"

        self.model_name = resolved_model
        self.model = SentenceTransformer(self.model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Encode texts into dense vector embeddings."""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

    def dimensions(self) -> int:
        """Return the embedding dimension of the loaded model."""
        dim = self.model.get_sentence_embedding_dimension()
        return int(dim) if dim is not None else 384
