import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { LibraryPage } from './pages/LibraryPage'
import { CreateQuizPage } from './pages/CreateQuizPage'
import { ExamScreenPage } from './pages/ExamScreenPage'
import { PreCheckPage } from './pages/PreCheckPage'
import { ResultsPage } from './pages/ResultsPage'
import { Layout } from './components/Layout'
import { AuthGuard } from './routes/guards/AuthGuard'
import { ExamGuard } from './routes/guards/ExamGuard'

export const App: React.FC = () => {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Authenticated routes guarded by AuthGuard and ExamGuard */}
      <Route element={<AuthGuard />}>
        {/* Fullscreen Exam Session & Pre-check (Outside Sidebar Layout) */}
        <Route path="/precheck" element={<PreCheckPage />} />
        <Route path="/exam/:attemptId" element={<ExamScreenPage />} />

        <Route element={<ExamGuard />}>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/library" replace />} />
            <Route path="library" element={<LibraryPage />} />
            <Route path="quiz/create" element={<CreateQuizPage />} />
            <Route path="results/:attemptId" element={<ResultsPage />} />
            <Route
              path="progress"
              element={
                <div className="placeholder-page">
                  <h2>Progress</h2>
                  <p>Progress — coming in Phase 6</p>
                </div>
              }
            />
          </Route>
        </Route>
      </Route>

      {/* Fallback unknown route */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
