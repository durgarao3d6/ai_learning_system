import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { generateQuiz, createAttempt } from '../api/quiz'
import { listDocuments, generateNotesQuiz, DocumentItem } from '../api/documents'

export const CreateQuizPage: React.FC = () => {
  const navigate = useNavigate()
  const [sourceMode, setSourceMode] = useState<'topic' | 'notes'>('topic')
  const [topic, setTopic] = useState('')
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [subtopicFilter, setSubtopicFilter] = useState('')

  const [numQuestions, setNumQuestions] = useState(5)
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium')
  const [questionTypes, setQuestionTypes] = useState<('mcq' | 'true_false' | 'short_answer')[]>([
    'mcq',
    'true_false',
  ])
  const [timeLimit, setTimeLimit] = useState(15)
  const [sessionMode, setSessionMode] = useState<'practice' | 'exam'>('practice')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listDocuments().then((docs) => {
      const readyDocs = docs.filter((d) => d.status === 'ready')
      setDocuments(readyDocs)
      if (readyDocs.length > 0) {
        setSelectedDocIds([readyDocs[0].id])
      }
    })
  }, [])

  const handleToggleDoc = (docId: string) => {
    if (selectedDocIds.includes(docId)) {
      if (selectedDocIds.length > 1) {
        setSelectedDocIds(selectedDocIds.filter((id) => id !== docId))
      }
    } else {
      setSelectedDocIds([...selectedDocIds, docId])
    }
  }

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
      let quiz
      if (sourceMode === 'notes') {
        quiz = await generateNotesQuiz({
          document_ids: selectedDocIds,
          subtopic_filter: subtopicFilter.trim() || undefined,
          num_questions: numQuestions,
          difficulty,
          question_types: questionTypes,
          time_limit_minutes: timeLimit,
        })
      } else {
        quiz = await generateQuiz({
          topic,
          num_questions: numQuestions,
          difficulty,
          question_types: questionTypes,
          time_limit_minutes: timeLimit,
        })
      }

      const attempt = await createAttempt(quiz.id, sessionMode)
      if (sessionMode === 'exam') {
        navigate(`/precheck?quizId=${quiz.id}&attemptId=${attempt.id}`)
      } else {
        navigate(`/exam/${attempt.id}?quizId=${quiz.id}&mode=practice`)
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to generate quiz. Please check server logs.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '680px', margin: '2rem auto', padding: '1rem' }}>
      <div className="card" style={{ padding: '2rem' }}>
        <h2 style={{ marginBottom: '1.5rem', color: 'var(--text-primary)' }}>Create Quiz</h2>

        {error && (
          <div className="form-alert-error" style={{ marginBottom: '1.5rem' }}>
            {error}
          </div>
        )}

        {/* Source Toggle Tabs */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '1.5rem', backgroundColor: 'var(--bg-primary)', padding: '0.25rem', borderRadius: '8px' }}>
          <button
            type="button"
            onClick={() => setSourceMode('topic')}
            style={{
              padding: '0.75rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: sourceMode === 'topic' ? 'var(--accent)' : 'transparent',
              color: '#fff',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Topic Mode
          </button>
          <button
            type="button"
            onClick={() => setSourceMode('notes')}
            style={{
              padding: '0.75rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: sourceMode === 'notes' ? 'var(--accent)' : 'transparent',
              color: '#fff',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Notes RAG Mode
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {sourceMode === 'topic' ? (
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Subject / Topic
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. Distributed Systems, Neural Networks"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
                disabled={loading}
              />
            </div>
          ) : (
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Select Study Notes Documents
              </label>
              {documents.length === 0 ? (
                <div style={{ padding: '1rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                  No processed documents found. Please upload course materials in the Library first.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
                  {documents.map((doc) => (
                    <label key={doc.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={selectedDocIds.includes(doc.id)}
                        onChange={() => handleToggleDoc(doc.id)}
                        disabled={loading}
                      />
                      <span>{doc.filename} ({doc.total_chunks} chunks)</span>
                    </label>
                  ))}
                </div>
              )}

              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Focus Subtopic / Keyword (Optional)
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. Section 2.1, Memory Hierarchy"
                value={subtopicFilter}
                onChange={(e) => setSubtopicFilter(e.target.value)}
                disabled={loading}
              />
            </div>
          )}

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
                  <span>
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
                value={sessionMode}
                onChange={(e) => setSessionMode(e.target.value as any)}
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
            disabled={
              loading ||
              (sourceMode === 'topic' && !topic.trim()) ||
              (sourceMode === 'notes' && selectedDocIds.length === 0)
            }
          >
            {loading ? 'Retrieving Passages & Generating Grounded Quiz...' : 'Start Quiz'}
          </button>
        </form>
      </div>
    </div>
  )
}
export default CreateQuizPage
