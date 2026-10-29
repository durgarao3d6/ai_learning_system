"""Hybrid retrieval engine combining Vector similarity, BM25, and Re-ranking."""

from app.schemas.document import RetrievedChunk
from app.services.vector_store import VectorStoreService


class RetrievalService:
    """Executes hybrid vector + BM25 search with reciprocal rank fusion and diversity filtering."""

    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store

    async def retrieve_relevant_chunks(
        self,
        query: str,
        document_ids: list[str],
        top_k: int = 8,
    ) -> list[RetrievedChunk]:
        """Hybrid search blending dense vectors and keyword scoring."""
        # Step 1: Semantic Vector Search (Top 20)
        vector_candidates = await self.vector_store.search(query, document_ids, top_k=20)

        # Step 2: BM25 Keyword Scoring
        scored_candidates = self._score_bm25_fusion(query, vector_candidates)

        # Step 3: Re-rank & Diversity Filter (Top-K)
        selected = self._mmr_diversity_filter(scored_candidates, top_k=top_k)

        return [
            RetrievedChunk(
                chunk_id=c["chunk_id"],
                document_id=c["document_id"],
                text=c["text"],
                score=c.get("final_score", 0.0),
                page_number=c.get("page_number"),
                heading=c.get("heading"),
            )
            for c in selected
        ]

    def _score_bm25_fusion(self, query: str, candidates: list[dict]) -> list[dict]:
        """Combine dense score with keyword token matching using reciprocal rank fusion."""
        q_tokens = set(query.lower().split())

        for idx, c in enumerate(candidates):
            c_text_tokens = c["text"].lower().split()
            kw_matches = sum(1 for t in q_tokens if t in c_text_tokens)
            bm25_proxy = kw_matches / (len(q_tokens) or 1)

            # RRF Combination: dense rank + keyword match
            dense_rank = idx + 1
            rrf_score = (1.0 / (60 + dense_rank)) + (bm25_proxy * 0.02)
            c["final_score"] = rrf_score

        candidates.sort(key=lambda x: x["final_score"], reverse=True)
        return candidates

    def _mmr_diversity_filter(self, candidates: list[dict], top_k: int) -> list[dict]:
        """Ensure chunk diversity across different pages/headings."""
        selected: list[dict] = []
        seen_headings: set[str] = set()

        for c in candidates:
            if len(selected) >= top_k:
                break
            h = c.get("heading") or ""
            # Prioritize distinct headings/sections
            if h and h in seen_headings and len(selected) < top_k // 2:
                continue
            selected.append(c)
            if h:
                seen_headings.add(h)

        # Fill remaining slots if any
        if len(selected) < top_k:
            for c in candidates:
                if c not in selected:
                    selected.append(c)
                if len(selected) >= top_k:
                    break

        return selected
