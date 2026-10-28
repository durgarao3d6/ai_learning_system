import React, { useEffect } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useExamStore } from '../../stores/examStore'

export const ExamGuard: React.FC = () => {
  const attemptStatus = useExamStore((state) => state.attemptStatus)
  const attemptId = useExamStore((state) => state.attemptId)
  const navigate = useNavigate()

  useEffect(() => {
    if (attemptStatus === 'in_progress') {
      const handleBeforeUnload = (e: BeforeUnloadEvent) => {
        e.preventDefault()
        e.returnValue = 'You cannot leave the exam. Please return to your exam.'
        return e.returnValue
      }

      window.addEventListener('beforeunload', handleBeforeUnload)
      return () => {
        window.removeEventListener('beforeunload', handleBeforeUnload)
      }
    }
  }, [attemptStatus])

  if (attemptStatus === 'in_progress') {
    return (
      <div className="exam-guard-overlay">
        <div className="exam-dialog-card card">
          <div className="exam-dialog-badge">Exam In Progress</div>
          <h2 className="exam-dialog-title">Active Exam Session</h2>
          <p className="exam-dialog-message">
            You cannot leave the exam. Please return to your exam.
          </p>
          <div className="exam-dialog-actions">
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                if (attemptId) {
                  navigate(`/quiz/attempt/${attemptId}`)
                } else {
                  navigate(-1)
                }
              }}
            >
              Return to Exam
            </button>
          </div>
        </div>
      </div>
    )
  }

  return <Outlet />
}

export default ExamGuard
