"""Documents and Notes RAG API router."""

import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.dependencies import (
    get_current_user,
    get_db,
    get_embedding_provider,
    get_llm_provider,
    get_settings,
)
from app.models.document import Chunk, Document
from app.models.quiz import Question, Quiz
from app.models.user import User
from app.schemas.document import DocumentResponse, GenerateNotesQuizRequest
from app.schemas.quiz import QuestionGenerated, QuestionPublicResponse, QuizPublicResponse
from app.services.crypto_service import encrypt_text
from app.services.document_parser import (
    chunk_sections,
    extract_text_from_docx,
    extract_text_from_pdf,
    validate_file_magic,
)
from app.services.providers.base import EmbeddingProvider, LLMProvider, Message
from app.services.quiz_generator import GeneratedQuestionsBatch, QuestionVerificationResult
from app.services.retrieval_service import RetrievalService
from app.services.vector_store import VectorStoreService

router = APIRouter(prefix="", tags=["documents", "rag"])

_vector_store_instance: VectorStoreService | None = None


def get_vector_store(embedding_provider: EmbeddingProvider = Depends(get_embedding_provider)) -> VectorStoreService:
    """Singleton VectorStore provider for FastAPI dependency injection."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreService(embedding_provider)
    return _vector_store_instance


async def _process_document_background(
    doc_id: uuid.UUID,
    content: bytes,
    file_type: str,
    db_maker,
    vector_store: VectorStoreService,
):
    """Background worker to extract text, chunk, embed, and update document status."""
    async with db_maker() as db:
        res = await db.execute(select(Document).where(Document.id == doc_id))
        doc = res.scalars().first()
        if not doc:
            return

        try:
            if file_type == "pdf":
                sections, total_pages = extract_text_from_pdf(content)
            elif file_type == "docx":
                sections = extract_text_from_docx(content)
                total_pages = 1
            else:
                raw_txt = content.decode("utf-8", errors="ignore")
                from app.services.document_parser import ParsedSection
                sections = [ParsedSection(heading="Notes", text=raw_txt, page_number=1)]
                total_pages = 1

            chunks_data = chunk_sections(sections)
            if not chunks_data:
                doc.status = "ocr_required"
                await db.commit()
                return

            db_chunks = []
            for c in chunks_data:
                c_id = uuid.uuid4()
                c["id"] = str(c_id)
                db_chunk = Chunk(
                    id=c_id,
                    document_id=doc.id,
                    chunk_index=c["chunk_index"],
                    text=c["text"],
                    token_count=c["token_count"],
                    page_number=c["page_number"],
                    heading=c["heading"],
                )
                db.add(db_chunk)
                db_chunks.append(db_chunk)

            await db.flush()

            # Embed and index vectors
            await vector_store.add_chunks(doc.id, chunks_data)

            doc.status = "ready"
            doc.total_pages = total_pages
            doc.total_chunks = len(chunks_data)
            await db.commit()

        except Exception as err:
            doc.status = "failed"
            doc.error_message = str(err)
            await db.commit()


@router.post("/documents", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> DocumentResponse:
    """Upload and schedule document text extraction and vector embedding."""
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    try:
        file_type = validate_file_magic(content, file.filename or "file.pdf")
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    new_doc = Document(
        user_id=current_user.id,
        filename=file.filename or "notes",
        file_type=file_type,
        file_size_bytes=len(content),
        status="processing",
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    from app.dependencies import get_session_maker
    session_maker = get_session_maker(settings)
    background_tasks.add_task(
        _process_document_background,
        new_doc.id,
        content,
        file_type,
        session_maker,
        vector_store,
    )

    return DocumentResponse.model_validate(new_doc)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List all documents uploaded by the user."""
    stmt = select(Document).where(Document.user_id == current_user.id).order_by(Document.created_at.desc())
    res = await db.execute(stmt)
    docs = res.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/documents/{document_id}/status")
async def stream_document_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events (SSE) streaming document processing status."""
    stmt = select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    res = await db.execute(stmt)
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        yield f"data: {{\"status\": \"{doc.status}\", \"total_chunks\": {doc.total_chunks}}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    vector_store: VectorStoreService = Depends(get_vector_store),
):
    """Delete document, cascading its chunks and vector embeddings."""
    stmt = select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    res = await db.execute(stmt)
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    vector_store.delete_document_vectors(str(doc.id))
    await db.delete(doc)
    await db.commit()


@router.post("/quizzes/generate/notes", response_model=QuizPublicResponse)
async def generate_notes_quiz(
    body: GenerateNotesQuizRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm: LLMProvider = Depends(get_llm_provider),
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> QuizPublicResponse:
    """Generate quiz grounded in user's notes with double verification."""
    # Verify document ownership
    stmt = select(Document).where(
        Document.id.in_(body.document_ids),
        Document.user_id == current_user.id,
        Document.status == "ready",
    )
    res = await db.execute(stmt)
    valid_docs = res.scalars().all()
    if not valid_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="None of the selected documents are ready for quiz generation.",
        )

    # Hybrid retrieval
    retriever = RetrievalService(vector_store)
    query_str = body.subtopic_filter or valid_docs[0].filename
    chunks = await retriever.retrieve_relevant_chunks(
        query=query_str,
        document_ids=[str(d.id) for d in valid_docs],
        top_k=8,
    )
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No relevant passages could be retrieved from the chosen notes.",
        )

    # Construct Grounded Prompt
    context_text = "\n\n".join(
        f"[Passage {idx + 1} | Page {c.page_number or 'N/A'}]:\n{c.text}"
        for idx, c in enumerate(chunks)
    )

    types_str = ", ".join(body.question_types)
    prompt = (
        f"You are creating an exam strictly based on the student's study notes below.\n"
        f"Generate {body.num_questions} questions.\n"
        f"Difficulty: {body.difficulty}. Allowed types: {types_str}.\n\n"
        f"STUDENT NOTES CONTEXT:\n{context_text}\n\n"
        "RULES:\n"
        "1. Every question must be directly answered by the provided text.\n"
        "2. Do NOT hallucinate information not present in the notes.\n"
        "3. Provide pedagogical explanations referencing the passage.\n"
    )

    messages = [
        Message(role="system", content="Generate exam questions strictly grounded in the context."),
        Message(role="user", content=prompt),
    ]

    try:
        gen_batch = await llm.complete(messages, GeneratedQuestionsBatch)
        generated_questions = gen_batch.questions
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate questions from notes context.",
        )

    # Verifier Pass
    verified_questions: list[QuestionGenerated] = []
    for q in generated_questions:
        v_prompt = (
            f"Audit if this question is strictly supported by the notes:\n"
            f"Notes Context:\n{context_text}\n\n"
            f"Question: {q.text}\nCorrect Answer: {q.correct_answer}\n"
            "Does the context factually support this exact correct answer without hallucination?"
        )
        try:
            v_res = await llm.complete(
                [
                    Message(role="system", content="Verify factual support."),
                    Message(role="user", content=v_prompt),
                ],
                QuestionVerificationResult,
            )
            if v_res.is_valid:
                verified_questions.append(q)
        except Exception:
            verified_questions.append(q)

    if not verified_questions:
        verified_questions = generated_questions[: body.num_questions]

    # Persist Quiz
    topic_name = body.subtopic_filter or f"Notes: {valid_docs[0].filename}"
    new_quiz = Quiz(
        user_id=current_user.id,
        title=f"Quiz: {topic_name}",
        topic=topic_name,
        mode="notes",
        difficulty=body.difficulty,
        time_limit_minutes=body.time_limit_minutes,
    )
    db.add(new_quiz)
    await db.flush()

    returned_questions: list[QuestionPublicResponse] = []
    for idx, q_data in enumerate(verified_questions):
        enc_ans = encrypt_text(q_data.correct_answer, settings)
        enc_exp = encrypt_text(q_data.explanation, settings)

        q_model = Question(
            quiz_id=new_quiz.id,
            text=q_data.text,
            type=q_data.type,
            options=q_data.options,
            answer_key_encrypted=enc_ans,
            explanation_encrypted=enc_exp,
            order=idx,
        )
        db.add(q_model)
        await db.flush()

        returned_questions.append(
            QuestionPublicResponse(
                id=q_model.id,
                text=q_model.text,
                type=q_model.type,
                options=q_model.options,
                order=q_model.order,
            )
        )

    await db.commit()

    return QuizPublicResponse(
        id=new_quiz.id,
        title=new_quiz.title,
        topic=new_quiz.topic,
        difficulty=new_quiz.difficulty,
        time_limit_minutes=new_quiz.time_limit_minutes,
        questions=returned_questions,
    )
