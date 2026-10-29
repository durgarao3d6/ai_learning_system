import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAttemptResults, AttemptResult } from '../api/quiz'

export const ResultsPage: React.FC = () => {
  const { attemptId } = useParams<{ attemptId: string }>()
  const [results, setResults] = useState<AttemptResult | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!attemptId) return
    getAttemptResults(attemptId)
      .then((data) => setResults(data))
      .finally(() => setLoading(false))
  }, [attemptId])

  if (loading) {
    return <div style={{ padding: '3rem', textAlign: 'center' }}>Loading attempt score and feedback...</div>
  }

  if (!results) {
    return <div style={{ padding: '3rem', textAlign: 'center' }}>Results not found or exam still in progress.</div>
  }

  const isPassing = results.percentage >= 70

  return (
    <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem' }}>
      {/* Overview Card */}
      <div className="card" style={{ padding: '2rem', textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ margin: '0 0 0.5rem 0' }}>Quiz Completed</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          {results.title} • Topic: {results.topic}
        </p>

        <div style={{ display: 'inline-block', padding: '1.5rem 2.5rem', borderRadius: '12px', backgroundColor: 'var(--bg-primary)', marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '3rem', fontWeight: 800, color: isPassing ? 'var(--success)' : 'var(--error)' }}>
            {results.percentage}%
          </div>
          <div style={{ color: 'var(--text-secondary)' }}>
            {results.correct_count} of {results.total_questions} questions correct
          </div>
        </div>

        <div>
          <Link to="/quiz/create" className="btn-primary" style={{ textDecoration: 'none', display: 'inline-block', marginRight: '1rem' }}>
            Retake / New Quiz
          </Link>
          <Link to="/library" className="btn-secondary" style={{ textDecoration: 'none', display: 'inline-block' }}>
            Back to Library
          </Link>
        </div>
      </div>

      {/* Question by Question Review */}
      <h2 style={{ marginBottom: '1rem' }}>Review & Explanations</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {results.questions.map((q, idx) => (
          <div
            key={q.question_id}
            className="card"
            style={{
              padding: '1.5rem',
              borderLeft: `5px solid ${q.is_correct ? 'var(--success)' : 'var(--error)'}`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <span style={{ fontWeight: 600 }}>Question {idx + 1}</span>
              <span style={{ fontWeight: 600, color: q.is_correct ? 'var(--success)' : 'var(--error)' }}>
                {q.is_correct ? '✓ Correct (1.0)' : `✗ Score: ${q.score}`}
              </span>
            </div>

            <p style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>{q.text}</p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem', fontSize: '0.95rem' }}>
              <div style={{ padding: '0.75rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)' }}>
                <strong style={{ color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Your Answer:</strong>
                <span>{q.submitted_answer || '<No Answer Provided>'}</span>
              </div>
              <div style={{ padding: '0.75rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)' }}>
                <strong style={{ color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Correct Answer:</strong>
                <span style={{ color: 'var(--success)' }}>{q.correct_answer}</span>
              </div>
            </div>

            {q.feedback && (
              <div style={{ fontSize: '0.9rem', marginBottom: '0.75rem', color: 'var(--accent)' }}>
                <strong>Feedback:</strong> {q.feedback}
              </div>
            )}

            <div style={{ padding: '0.75rem', borderRadius: '6px', backgroundColor: 'rgba(255,255,255,0.03)', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--text-primary)' }}>Explanation:</strong> {q.explanation}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
export default ResultsPage
