import { client } from './client'
import { QuizPublic } from './quiz'

export interface DocumentItem {
  id: string
  filename: string
  file_type: string
  file_size_bytes: number
  status: 'processing' | 'ready' | 'failed' | 'ocr_required'
  error_message?: string | null
  total_pages: number
  total_chunks: number
}

export interface GenerateNotesQuizParams {
  document_ids: string[]
  subtopic_filter?: string
  num_questions: number
  difficulty: 'easy' | 'medium' | 'hard'
  question_types: ('mcq' | 'true_false' | 'short_answer')[]
  time_limit_minutes: number
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await client.post<DocumentItem>('/api/v1/documents', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return res.data
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const res = await client.get<DocumentItem[]>('/api/v1/documents')
  return res.data
}

export async function deleteDocument(id: string): Promise<void> {
  await client.delete(`/api/v1/documents/${id}`)
}

export async function generateNotesQuiz(params: GenerateNotesQuizParams): Promise<QuizPublic> {
  const res = await client.post<QuizPublic>('/api/v1/quizzes/generate/notes', params)
  return res.data
}
