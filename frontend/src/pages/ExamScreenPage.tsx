import React, { useEffect, useState, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { getQuiz, saveAnswer, submitAttempt, QuizPublic, QuestionPublic } from '../api/quiz'
import { useExamStore } from '../stores/examStore'

export const ExamScreenPage: React.FC = () => {
  const { attemptId } = useParams<{ attemptId: string }>()
  const [searchParams] = useSearchParams()
  const quizId = searchParams.get('quizId')
  const navigate = useNavigate()
  const examStore = useExamStore()

  const [quiz, setQuiz] = useState<QuizPublic | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [flags, setFlags] = useState<Record<string, boolean>>({})
  const [timeLeft, setTimeLeft] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [offline, setOffline] = useState(!navigator.onLine)

  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    const handleOnline = () => setOffline(false)
    const handleOffline = () => setOffline(true)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    if (!quizId) return
    getQuiz(quizId).then((data) => {
      setQuiz(data)
      setTimeLeft(data.time_limit_minutes * 60)
      if (attemptId) {
        examStore.setAttempt(attemptId, 'in_progress', Date.now() + data.time_limit_minutes * 60 * 1000)
      }
    })
  }, [quizId, attemptId])

  // Timer countdown
  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0) return
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev !== null && prev <= 1) {
          clearInterval(timer)
          handleAutoSubmit()
          return 0
        }
        return prev ? prev - 1 : 0
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [timeLeft])

  const handleAutoSubmit = async () => {
    if (!attemptId) return
    setSubmitting(true)
    try {
      await submitAttempt(attemptId)
      examStore.reset()
      navigate(`/results/${attemptId}`)
    } catch (err) {
      console.error('Failed auto submit:', err)
    }
  }

  const handleAnswerChange = (questionId: string, val: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: val }))

    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
    debounceTimerRef.current = setTimeout(async () => {
      if (!attemptId) return
      setSaving(true)
      try {
        await saveAnswer(attemptId, {
          question_id: questionId,
          submitted_answer: val,
          is_flagged: !!flags[questionId],
        })
      } catch (e) {
        console.warn('Autosave failed:', e)
      } finally {
        setSaving(false)
      }
    }, 400)
  }

  const toggleFlag = async (questionId: string) => {
    const nextFlag = !flags[questionId]
    setFlags((prev) => ({ ...prev, [questionId]: nextFlag }))
    if (attemptId) {
      await saveAnswer(attemptId, {
        question_id: questionId,
        submitted_answer: answers[questionId] || '',
        is_flagged: nextFlag,
      })
    }
  }

  const handleSubmit = async () => {
    if (!attemptId) return
    if (!window.confirm('Are you sure you want to finalize and submit your quiz?')) return

    setSubmitting(true)
    try {
      await submitAttempt(attemptId)
      examStore.reset()
      navigate(`/results/${attemptId}`)
    } catch (err) {
      alert('Failed to submit. Please check connection and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!quiz) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading quiz session...</div>
  }

  const currentQ: QuestionPublic | undefined = quiz.questions[currentIndex]
  const answeredCount = Object.keys(answers).filter((k) => !!answers[k]?.trim()).length
  const minutes = Math.floor((timeLeft || 0) / 60)
  const seconds = (timeLeft || 0) % 60

  return (
    <div style={{ maxWidth: '800px', margin: '1.5rem auto', padding: '1rem' }}>
      {offline && (
        <div style={{ backgroundColor: '#f59e0b', color: '#1a1d27', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem', fontWeight: 600 }}>
          Offline Mode: Answers are buffered locally and will sync when reconnected.
        </div>
      )}

      {/* Top Header Status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>{quiz.title}</h2>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Topic: {quiz.topic} • {answeredCount} of {quiz.questions.length} answered {saving && '• Autosaving...'}
          </span>
        </div>
        <div style={{ fontSize: '1.25rem', fontWeight: 700, color: (timeLeft || 0) < 120 ? '#ef4444' : 'var(--accent)' }}>
          ⏱ {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
        </div>
      </div>

      {/* Progress Navigator Bar */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
        {quiz.questions.map((q, idx) => {
          const isAns = !!answers[q.id]?.trim()
          const isFlg = !!flags[q.id]
          const isCurrent = idx === currentIndex
          return (
            <button
              key={q.id}
              onClick={() => setCurrentIndex(idx)}
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '6px',
                border: isCurrent ? '2px solid var(--accent)' : '1px solid var(--border)',
                backgroundColor: isFlg ? '#fbbf24' : isAns ? '#10b981' : 'var(--bg-card)',
                color: isFlg || isAns ? '#000' : '#fff',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              {idx + 1}
            </button>
          )
        })}
      </div>

      {/* Question Card */}
      {currentQ && (
        <div className="card" style={{ padding: '2rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Question {currentIndex + 1} of {quiz.questions.length} ({currentQ.type.toUpperCase()})
            </span>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => toggleFlag(currentQ.id)}
              style={{ fontSize: '0.875rem' }}
            >
              {flags[currentQ.id] ? '🚩 Flagged' : '🏳️ Flag for Review'}
            </button>
          </div>

          <h3 style={{ marginBottom: '1.5rem', lineHeight: 1.4 }}>{currentQ.text}</h3>

          {/* Options for MCQ / True False */}
          {currentQ.type === 'mcq' && currentQ.options && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {currentQ.options.map((opt, i) => (
                <label
                  key={i}
                  style={{
                    padding: '1rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    backgroundColor: answers[currentQ.id] === opt ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-primary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                  }}
                >
                  <input
                    type="radio"
                    name={`q-${currentQ.id}`}
                    value={opt}
                    checked={answers[currentQ.id] === opt}
                    onChange={() => handleAnswerChange(currentQ.id, opt)}
                  />
                  <span>{opt}</span>
                </label>
              ))}
            </div>
          )}

          {currentQ.type === 'true_false' && (
            <div style={{ display: 'flex', gap: '1rem' }}>
              {['True', 'False'].map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => handleAnswerChange(currentQ.id, opt)}
                  style={{
                    flex: 1,
                    padding: '1rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    backgroundColor: answers[currentQ.id] === opt ? 'var(--accent)' : 'var(--bg-primary)',
                    color: '#fff',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}

          {currentQ.type === 'short_answer' && (
            <div>
              <textarea
                className="input-field"
                rows={4}
                placeholder="Type your explanation or concise answer here..."
                value={answers[currentQ.id] || ''}
                onChange={(e) => handleAnswerChange(currentQ.id, e.target.value)}
              />
            </div>
          )}
        </div>
      )}

      {/* Footer Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          className="btn-secondary"
          disabled={currentIndex === 0}
          onClick={() => setCurrentIndex((prev) => prev - 1)}
        >
          Previous
        </button>

        {currentIndex === quiz.questions.length - 1 ? (
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={submitting}
            style={{ backgroundColor: '#10b981' }}
          >
            {submitting ? 'Submitting...' : 'Finalize & Submit'}
          </button>
        ) : (
          <button
            className="btn-primary"
            onClick={() => setCurrentIndex((prev) => prev + 1)}
          >
            Next Question
          </button>
        )}
      </div>
    </div>
  )
}
export default ExamScreenPage
