# Backend: Document Ingestion Architecture

## 1. BackgroundTasks vs Celery
In Phase 3, we execute ingestion using FastAPI's native `BackgroundTasks` rather than introducing Celery and Redis:
- **Low Operational Overhead**: Zero external daemon or broker dependencies (Redis/RabbitMQ) for local development and single-server deployments.
- **Async Efficiency**: File parsing and vector database writes happen in non-blocking async loops.
- **Migration Path**: The ingestion logic is encapsulated in `IngestionService.process_document()`, making the transition to Celery or RQ in Phase 5 straightforward.

## 2. Security Validation
1. **MIME & Magic Bytes Inspection**:
   We inspect initial file header bytes (`%PDF-` for PDFs, `PK\x03\x04` for DOCX) rather than trusting client-provided file extensions.
2. **File Size Capping**:
   Enforces a strict 50 MB threshold to prevent memory exhaustion and Denial of Service.
3. **Scanned PDF Handling**:
   If extracted text is under 50 characters across 3 pages, the document status is set to `ocr_required` rather than failing silently.

## 3. Real-Time Status via Server-Sent Events (SSE)
Instead of continuous client polling, the frontend subscribes to `GET /api/v1/documents/{id}/status` via `EventSource`. The server streams state transitions (`uploaded` → `extracting` → `chunking` → `embedding` → `ready` or `error`) instantly.
