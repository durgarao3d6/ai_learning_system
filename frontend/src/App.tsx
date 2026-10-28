import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { LibraryPage } from './pages/LibraryPage'
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
        <Route element={<ExamGuard />}>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/library" replace />} />
            <Route path="library" element={<LibraryPage />} />
            <Route
              path="quiz/create"
              element={
                <div className="placeholder-page">
                  <h2>Create Quiz</h2>
                  <p>Create Quiz — coming in Phase 2</p>
                </div>
              }
            />
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
