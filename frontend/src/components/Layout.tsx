import React, { useState, useEffect } from 'react'
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export const Layout: React.FC = () => {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const navigate = useNavigate()
  const location = useLocation()
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  useEffect(() => {
    if (location.state?.alertMessage) {
      setToastMessage(location.state.alertMessage)
      const timer = setTimeout(() => {
        setToastMessage(null)
        // Clear history state so toast does not reappear on refresh
        window.history.replaceState({}, document.title)
      }, 4000)
      return () => clearTimeout(timer)
    }
  }, [location.state])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userInitial = user?.email ? user.email.charAt(0).toUpperCase() : 'U'

  return (
    <div className="app-layout">
      {/* Left Sidebar */}
      <aside className="app-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            Learn<span>Smart</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <NavLink
            to="/library"
            className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
          >
            <svg
              className="nav-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
              <path d="M6 6h10" />
              <path d="M6 10h10" />
            </svg>
            <span>Library</span>
          </NavLink>

          <NavLink
            to="/quiz/create"
            className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
          >
            <svg
              className="nav-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="16" />
              <line x1="8" y1="12" x2="16" y2="12" />
            </svg>
            <span>Create Quiz</span>
          </NavLink>

          <NavLink
            to="/progress"
            className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
          >
            <svg
              className="nav-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            <span>Progress</span>
          </NavLink>
        </nav>

        {user && (
          <div className="sidebar-footer">
            <div className="user-profile-badge">
              <div className="user-avatar">{userInitial}</div>
              <div className="user-info">
                <span className="user-email" title={user.email}>
                  {user.email}
                </span>
                <span className="user-role">{user.role || 'Learner'}</span>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Area */}
      <div className="app-main">
        {/* Topbar */}
        <header className="app-topbar">
          <div className="topbar-title">LearnSmart</div>
          <div className="topbar-actions">
            <button
              type="button"
              className="btn-secondary btn-logout"
              onClick={handleLogout}
            >
              Log out
            </button>
          </div>
        </header>

        {/* Dynamic Nested Content */}
        <main className="app-content">
          <Outlet />
        </main>
      </div>

      {toastMessage && (
        <div className="toast-notification toast-warning" role="alert">
          {toastMessage}
        </div>
      )}
    </div>
  )
}

export default Layout
