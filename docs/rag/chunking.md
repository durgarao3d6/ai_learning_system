# RAG: Heading-First Token Chunking

## 1. Problem with Naive Splitting
Standard character or token splitting ignores document structure. It often splits paragraphs across sentences or severs a definition from its heading. For example, a heading like "3.1 Backpropagation" might end up in chunk $N$, while the actual equation ends up in chunk $N+1$, depriving the embedding model of context.

## 2. Heading-Aware Strategy
Our chunker adheres to the following sequence:
1. **Structural Segmentation**:
   Using `PyMuPDF` or `python-docx`, text is first segmented by document headings (H1, H2, H3 or font-size heuristics in PDF).
2. **Token Window Splitting**:
   If a heading section exceeds the chunk window (target: ~500 tokens), it is recursively split along paragraph and sentence boundaries.
3. **Overlapping**:
   A 50-token overlap between adjacent chunks ensures that multi-sentence propositions or transitions are preserved across boundaries.
4. **Metadata Enrichment**:
   Each chunk retains:
   - `document_id`: Foreign key to parent document.
   - `page_number`: Original page for easy student reference.
   - `heading`: Structural breadcrumb (e.g. "Chapter 4 > Dynamic Programming").
