import React, { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getQuiz } from '../api/quiz'

export const PreCheckPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const quizId = searchParams.get('quizId')
  const attemptId = searchParams.get('attemptId')
  const navigate = useNavigate()

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [hasCamera, setHasCamera] = useState<boolean | null>(null)
  const [hasConsent, setHasConsent] = useState(false)
  const [quizTitle, setQuizTitle] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (quizId) {
      getQuiz(quizId).then((q) => setQuizTitle(q.title))
    }
    requestCamera()
    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream
        stream.getTracks().forEach((t) => t.stop())
      }
    }
  }, [quizId])

  const requestCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
      }
      setHasCamera(true)
    } catch {
      setHasCamera(false)
    }
  }

  const handleStartExam = async () => {
    if (!hasConsent) {
      setError('You must accept the proctoring consent to enter Exam Mode.')
      return
    }

    try {
      // Enter Fullscreen
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen()
      }
      navigate(`/exam/${attemptId}?quizId=${quizId}&mode=exam`)
    } catch (err) {
      setError('Fullscreen permission is required to launch Proctored Exam Mode.')
    }
  }

  return (
    <div style={{ maxWidth: '640px', margin: '2rem auto', padding: '1rem' }}>
      <div className="card" style={{ padding: '2rem' }}>
        <h2 style={{ marginBottom: '0.5rem' }}>Proctored Exam Pre-Check</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          {quizTitle || 'Exam Session'}
        </p>

        {error && (
          <div className="form-alert-error" style={{ marginBottom: '1.25rem' }}>
            {error}
          </div>
        )}

        {/* Video Preview */}
        <div
          style={{
            width: '100%',
            height: '240px',
            backgroundColor: '#000',
            borderRadius: '8px',
            overflow: 'hidden',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {hasCamera ? (
            <video
              ref={videoRef}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              muted
            />
          ) : (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '1rem' }}>
              📷 Camera not detected or permission denied.
              <br />
              <button
                type="button"
                className="btn-secondary"
                onClick={requestCamera}
                style={{ marginTop: '0.5rem' }}
              >
                Retry Camera
              </button>
            </div>
          )}
        </div>

        {/* Rules & Consent Checklist */}
        <div style={{ backgroundColor: 'var(--bg-primary)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
          <strong>Proctoring Rules & Integrity Checks:</strong>
          <ul style={{ margin: '0.5rem 0 0 1.25rem', padding: 0, color: 'var(--text-secondary)' }}>
            <li>Fullscreen is enforced throughout the examination.</li>
            <li>Tab switches or window minimizations count as recorded strikes.</li>
            <li>Maximum 3 strikes before the exam is automatically submitted.</li>
            <li>Clipboard operations (copy/paste) and shortcuts are disabled.</li>
          </ul>
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={hasConsent}
            onChange={(e) => setHasConsent(e.target.checked)}
          />
          <span style={{ fontSize: '0.9rem' }}>
            I understand and consent to in-browser proctoring monitoring.
          </span>
        </label>

        <button
          className="btn-primary"
          style={{ width: '100%', padding: '0.75rem', fontSize: '1rem' }}
          disabled={!hasConsent}
          onClick={handleStartExam}
        >
          Enter Fullscreen & Begin Exam
        </button>
      </div>
    </div>
  )
}
export default PreCheckPage
