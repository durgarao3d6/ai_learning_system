import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { generateQuiz, createAttempt } from '../api/quiz'

export const CreateQuizPage: React.FC = () => {
  const navigate = useNavigate()
  const [topic, setTopic] = useState('')
  const [numQuestions, setNumQuestions] = useState(5)
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium')
  const [questionTypes, setQuestionTypes] = useState<('mcq' | 'true_false' | 'short_answer')[]>([
    'mcq',
    'true_false',
  ])
  const [timeLimit, setTimeLimit] = useState(15)
  const [mode, setMode] = useState<'practice' | 'exam'>('practice')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleToggleType = (type: 'mcq' | 'true_false' | 'short_answer') => {
    if (questionTypes.includes(type)) {
      if (questionTypes.length > 1) {
        setQuestionTypes(questionTypes.filter((t) => t !== type))
      }
    } else {
      setQuestionTypes([...questionTypes, type])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const quiz = await generateQuiz({
        topic,
        num_questions: numQuestions,
        difficulty,
        question_types: questionTypes,
        time_limit_minutes: timeLimit,
      })

      const attempt = await createAttempt(quiz.id, mode)
      navigate(`/exam/${attempt.id}?quizId=${quiz.id}`)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to generate quiz. Please check Ollama or server logs.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '640px', margin: '2rem auto', padding: '1rem' }}>
      <div className="card" style={{ padding: '2rem' }}>
        <h2 style={{ marginBottom: '1.5rem', color: 'var(--text-primary)' }}>Create Topic Quiz</h2>

        {error && (
          <div className="form-alert-error" style={{ marginBottom: '1.5rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
              Subject / Topic
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. Modern Web Architecture, Python Data Structures"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Questions Count
              </label>
              <input
                type="number"
                min="1"
                max="20"
                className="input-field"
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value))}
                disabled={loading}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Difficulty
              </label>
              <select
                className="input-field"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as any)}
                disabled={loading}
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
              Question Types
            </label>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              {(['mcq', 'true_false', 'short_answer'] as const).map((t) => (
                <label key={t} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={questionTypes.includes(t)}
                    onChange={() => handleToggleType(t)}
                    disabled={loading}
                  />
                  <span style={{ textTransform: 'capitalize' }}>
                    {t === 'mcq' ? 'Multiple Choice' : t === 'true_false' ? 'True / False' : 'Short Answer'}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Time Limit (Minutes)
              </label>
              <input
                type="number"
                min="1"
                max="180"
                className="input-field"
                value={timeLimit}
                onChange={(e) => setTimeLimit(Number(e.target.value))}
                disabled={loading}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Session Mode
              </label>
              <select
                className="input-field"
                value={mode}
                onChange={(e) => setMode(e.target.value as any)}
                disabled={loading}
              >
                <option value="practice">Practice Mode</option>
                <option value="exam">Exam Mode</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="btn-primary"
            style={{ width: '100%', padding: '0.75rem', fontSize: '1rem' }}
            disabled={loading || !topic.trim()}
          >
            {loading ? 'Generating & Auditing Questions...' : 'Start Quiz'}
          </button>
        </form>
      </div>
    </div>
  )
}
export default CreateQuizPage
