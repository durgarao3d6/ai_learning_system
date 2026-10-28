import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { login, TokenResponse } from '../api/auth'
import { useAuthStore } from '../stores/authStore'

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [clientError, setClientError] = useState<string | null>(null)

  const loginStore = useAuthStore((state) => state.login)
  const navigate = useNavigate()

  const mutation = useMutation<TokenResponse, AxiosError<{ detail?: string | unknown }>, { email: string; password: string }>({
    mutationFn: (credentials) => login(credentials.email, credentials.password),
    onSuccess: (data) => {
      loginStore(data.access_token, data.refresh_token, data.user)
      navigate('/')
    },
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setClientError(null)

    if (!email.trim() || !password) {
      setClientError('Please enter both email and password.')
      return
    }

    mutation.mutate({ email, password })
  }

  // Derive error message from mutation or client validation
  let apiErrorMessage: string | null = null
  if (mutation.isError) {
    const detail = mutation.error.response?.data?.detail
    if (typeof detail === 'string') {
      apiErrorMessage = detail
    } else if (detail) {
      apiErrorMessage = JSON.stringify(detail)
    } else {
      apiErrorMessage = mutation.error.message || 'Login failed. Please verify your credentials.'
    }
  }

  const activeError = clientError || apiErrorMessage

  return (
    <div className="auth-container">
      <div className="card auth-card">
        <div className="auth-header">
          <div className="brand-logo">
            Learn<span>Smart</span>
          </div>
          <h1>Welcome Back</h1>
          <p>Sign in to access your proctored quizzes and library</p>
        </div>

        {activeError && <div className="form-alert-error">{activeError}</div>}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              className="input-field"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={mutation.isPending}
              autoComplete="email"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="input-field"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={mutation.isPending}
              autoComplete="current-password"
              required
            />
          </div>

          <button
            type="submit"
            className="btn-primary"
            style={{ width: '100%', marginTop: '0.5rem' }}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="auth-footer">
          Don&apos;t have an account? <Link to="/register">Create an account</Link>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
