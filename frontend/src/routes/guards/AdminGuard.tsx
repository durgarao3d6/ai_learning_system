import React, { useEffect } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

export const AdminGuard: React.FC = () => {
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    if (!isAdmin) {
      // Trigger user-visible toast or notification
      console.warn('Access denied: Administrator privileges required.')
    }
  }, [isAdmin])

  if (!isAdmin) {
    return (
      <Navigate
        to="/"
        replace
        state={{ alertMessage: 'Access denied: Administrator privileges required.' }}
      />
    )
  }

  return <Outlet />
}

export default AdminGuard
