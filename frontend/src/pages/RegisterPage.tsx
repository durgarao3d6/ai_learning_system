import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { register, TokenResponse } from '../api/auth'
import { useAuthStore } from '../stores/authStore'

export const RegisterPage: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [clientError, setClientError] = useState<string | null>(null)

  const loginStore = useAuthStore((state) => state.login)
  const navigate = useNavigate()

  const mutation = useMutation<
    TokenResponse,
    AxiosError<{ detail?: string | unknown }>,
    { email: string; password: string }
  >({
    mutationFn: (credentials) => register(credentials.email, credentials.password),
    onSuccess: (data) => {
      loginStore(data.access_token, data.refresh_token, data.user)
      navigate('/')
    },
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setClientError(null)

    // Client-side validations
    const trimmedEmail = email.trim()
    if (!trimmedEmail) {
      setClientError('Email is required.')
      return
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(trimmedEmail)) {
      setClientError('Please enter a valid email address.')
      return
    }

    if (password.length < 8) {
      setClientError('Password must be at least 8 characters long.')
      return
    }

    if (password !== confirmPassword) {
      setClientError('Passwords do not match.')
      return
    }

    mutation.mutate({ email: trimmedEmail, password })
  }

  // Derive API error message
  let apiErrorMessage: string | null = null
  if (mutation.isError) {
    const detail = mutation.error.response?.data?.detail
    if (typeof detail === 'string') {
      apiErrorMessage = detail
    } else if (detail) {
      apiErrorMessage = JSON.stringify(detail)
    } else {
      apiErrorMessage = mutation.error.message || 'Registration failed. Please try again.'
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
          <h1>Create an Account</h1>
          <p>Get started with proctored quizzes and AI learning</p>
        </div>

        {activeError && <div className="form-alert-error">{activeError}</div>}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="reg-email">Email Address</label>
            <input
              id="reg-email"
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
            <label htmlFor="reg-password">Password</label>
            <input
              id="reg-password"
              type="password"
              className="input-field"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={mutation.isPending}
              autoComplete="new-password"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="reg-confirm-password">Confirm Password</label>
            <input
              id="reg-confirm-password"
              type="password"
              className="input-field"
              placeholder="Repeat your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={mutation.isPending}
              autoComplete="new-password"
              required
            />
          </div>

          <button
            type="submit"
            className="btn-primary"
            style={{ width: '100%', marginTop: '0.5rem' }}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  )
}

export default RegisterPage
