import { client } from './client'

export interface QuestionPublic {
  id: string
  text: string
  type: 'mcq' | 'true_false' | 'short_answer'
  options: string[] | null
  order: number
}

export interface QuizPublic {
  id: string
  title: string
  topic: string
  difficulty: string
  time_limit_minutes: number
  questions: QuestionPublic[]
}

export interface GenerateQuizParams {
  topic: string
  num_questions: number
  difficulty: 'easy' | 'medium' | 'hard'
  question_types: ('mcq' | 'true_false' | 'short_answer')[]
  time_limit_minutes: number
}

export interface AttemptResponse {
  id: string
  quiz_id: string
  status: string
  mode: string
  time_limit_seconds: number
  total_questions: number
}

export interface SaveAnswerParams {
  question_id: string
  submitted_answer: string
  is_flagged?: boolean
}

export interface QuestionResult {
  question_id: string
  text: string
  type: string
  options: string[] | null
  submitted_answer: string | null
  correct_answer: string
  explanation: string
  is_correct: boolean
  score: number
  feedback: string | null
}

export interface AttemptResult {
  attempt_id: string
  quiz_id: string
  title: string
  topic: string
  status: string
  score: number
  total_questions: number
  correct_count: number
  percentage: number
  questions: QuestionResult[]
}

export async function generateQuiz(params: GenerateQuizParams): Promise<QuizPublic> {
  const res = await client.post<QuizPublic>('/api/v1/quizzes/generate', params)
  return res.data
}

export async function getQuiz(id: string): Promise<QuizPublic> {
  const res = await client.get<QuizPublic>(`/api/v1/quizzes/${id}`)
  return res.data
}

export async function createAttempt(quizId: string, mode: 'practice' | 'exam' = 'practice'): Promise<AttemptResponse> {
  const res = await client.post<AttemptResponse>('/api/v1/attempts', {
    quiz_id: quizId,
    mode,
  })
  return res.data
}

export async function saveAnswer(attemptId: string, data: SaveAnswerParams) {
  const res = await client.put(`/api/v1/attempts/${attemptId}/answers`, data)
  return res.data
}

export async function submitAttempt(attemptId: string): Promise<AttemptResult> {
  const res = await client.post<AttemptResult>(`/api/v1/attempts/${attemptId}/submit`)
  return res.data
}

export async function getAttemptResults(attemptId: string): Promise<AttemptResult> {
  const res = await client.get<AttemptResult>(`/api/v1/attempts/${attemptId}/results`)
  return res.data
}
