"""Vector storage wrapper using ChromaDB or fallback cosine memory store."""

import uuid
from typing import Any

from app.services.providers.base import EmbeddingProvider


class VectorStoreService:
    """Manages dense chunk embeddings and similarity search."""

    def __init__(self, embedding_provider: EmbeddingProvider, collection_name: str = "notes_rag"):
        self.embedding_provider = embedding_provider
        self.collection_name = collection_name
        self._memory_chunks: dict[str, dict[str, Any]] = {}
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            self.has_chroma = True
        except Exception:
            self.has_chroma = False

    async def add_chunks(self, document_id: uuid.UUID, chunks: list[dict]):
        """Embed and persist chunks in vector index."""
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        embeddings = await self.embedding_provider.embed(texts)

        for idx, (c, emb) in enumerate(zip(chunks, embeddings, strict=False)):
            chunk_id = c.get("id") or str(uuid.uuid4())
            doc_id_str = str(document_id)

            if self.has_chroma:
                try:
                    self.collection.add(
                        ids=[chunk_id],
                        embeddings=[emb],
                        documents=[c["text"]],
                        metadatas=[{
                            "document_id": doc_id_str,
                            "page": c.get("page_number", 1) or 1,
                            "heading": c.get("heading", "") or "",
                        }],
                    )
                    continue
                except Exception:
                    pass

            # In-memory fallback
            self._memory_chunks[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": doc_id_str,
                "text": c["text"],
                "embedding": emb,
                "page_number": c.get("page_number", 1),
                "heading": c.get("heading", ""),
            }

    async def search(self, query: str, document_ids: list[str], top_k: int = 15) -> list[dict]:
        """Perform semantic similarity query."""
        q_emb = (await self.embedding_provider.embed([query]))[0]

        if self.has_chroma:
            try:
                where_filter = (
                    {"document_id": {"$in": document_ids}}
                    if len(document_ids) > 1
                    else {"document_id": document_ids[0]}
                )
                res = self.collection.query(
                    query_embeddings=[q_emb],
                    n_results=top_k,
                    where=where_filter,
                )
                results = []
                if res and res.get("ids") and res["ids"][0]:
                    for cid, text, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0], strict=False):
                        results.append({
                            "chunk_id": cid,
                            "document_id": meta.get("document_id"),
                            "text": text,
                            "score": 1.0 - (dist if dist is not None else 0.5),
                            "page_number": meta.get("page"),
                            "heading": meta.get("heading"),
                        })
                    return results
            except Exception:
                pass

        # Fallback memory search with cosine similarity
        results = []
        for cid, data in self._memory_chunks.items():
            if data["document_id"] in document_ids:
                sim = self._cosine_sim(q_emb, data["embedding"])
                results.append({
                    "chunk_id": cid,
                    "document_id": data["document_id"],
                    "text": data["text"],
                    "score": sim,
                    "page_number": data["page_number"],
                    "heading": data["heading"],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def delete_document_vectors(self, document_id: str):
        """Remove chunks belonging to deleted document."""
        if self.has_chroma:
            try:
                self.collection.delete(where={"document_id": document_id})
            except Exception:
                pass
        self._memory_chunks = {
            cid: val for cid, val in self._memory_chunks.items() if val["document_id"] != document_id
        }

    def _cosine_sim(self, v1: list[float], v2: list[float]) -> float:
        import math
        dot = sum(a * b for a, b in zip(v1, v2, strict=False))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        return dot / (n1 * n2) if (n1 and n2) else 0.0
