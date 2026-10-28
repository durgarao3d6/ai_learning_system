# Frontend Routing — Router-Level Guards (`AuthGuard`, `ExamGuard`, `AdminGuard`) with React Router

## What it is
Navigation and view access in the React application are controlled using router-level route guards (`AuthGuard`, `ExamGuard`, and `AdminGuard`) built around React Router v6's `<Outlet />` composition pattern. Protected components are prevented from ever mounting or executing unless all route-level authorization and state criteria are satisfied.

## Why we need it / Why this approach
Securing frontend routes requires intercepting navigation before the target component lifecycle begins:
1. **The flaw of component-level checks**: A common anti-pattern is placing redirect logic inside individual page components (e.g., `if (!token) return <Navigate to="/login" />`). This approach is fundamentally flawed:
   - The protected component mounts briefly before the redirect executes.
   - Any child component hooks, initialization effects (`useEffect`), and state dispatches run on mount, often firing network requests to protected API endpoints with missing credentials and causing flash-of-unauthorized-content (FOUC).
   - Placing checks in every page leads to widespread code duplication and inevitable developer omission on newly added pages.
2. **Router-level protection with `<Outlet />`**: Router-level guards act as gatekeeper layout components. If the condition fails, the guard renders a redirection component or an error view; the child route component declared inside `<Outlet />` is **never mounted**. No hooks execute, no premature network calls fire, and no DOM is leaked.
3. **`ExamGuard` — Preventing mid-exam navigation**: Students must not inadvertently click the browser back button or an internal navigation link while an exam attempt is `in_progress`. `ExamGuard` listens to active exam state and router transitions:
   - It intercepts internal router navigation and presents a blocking confirmation dialog ("An active exam is in progress. Navigating away will submit your attempt.").
   - It pairs with the window `beforeunload` event for external reloads or tab closures.
4. **`AdminGuard` — Role-based access control (RBAC)**: Checks that the authenticated user possesses the `admin` role before mounting administrative dashboards or question-bank management interfaces. Unauthorized students are routed to an explicit 403 Forbidden page rather than an ambiguous empty screen.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Component-level checks inside `useEffect` | Leaks protected UI during the initial mount cycle; fires initial API calls before redirect; high boilerplate across every route. |
| Higher-Order Components (HOCs, e.g. `withAuth(MyComponent)`) | Cumbersome TypeScript typings; adds unnecessary component tree nesting; obsolete in React Router v6 layout patterns. |
| Route guards as full security boundaries | Misleading assumption. All frontend code and client-side variables can be manipulated in the browser developer tools. Route guards are purely a UX and navigation-safety mechanism. The backend API must enforce authentication and authorization on every endpoint. |

## Implementation details

Route guards are implemented in `frontend/src/routes/guards/` and combined in `frontend/src/routes/index.tsx`.

### 1. `AuthGuard` (`frontend/src/routes/guards/AuthGuard.tsx`)
Prevents unauthenticated users from accessing protected student pages:

```tsx
// frontend/src/routes/guards/AuthGuard.tsx
import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

export const AuthGuard: React.FC = () => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    // Redirect to login while preserving the attempted location for post-login redirect
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // User is authenticated; safely mount protected child routes
  return <Outlet />;
};
```

### 2. `AdminGuard` (`frontend/src/routes/guards/AdminGuard.tsx`)
Restricts management routes to users with `admin` privileges:

```tsx
// frontend/src/routes/guards/AdminGuard.tsx
import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

export const AdminGuard: React.FC = () => {
  const { user, isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== 'admin') {
    // Render an explicit 403 Forbidden view instead of a blank screen or login redirect
    return <Navigate to="/403" replace />;
  }

  return <Outlet />;
};
```

### 3. `ExamGuard` (`frontend/src/routes/guards/ExamGuard.tsx`)
Prevents accidental navigation away from an ongoing proctored exam:

```tsx
// frontend/src/routes/guards/ExamGuard.tsx
import React, { useEffect, useState } from 'react';
import { Outlet, useBlocker } from 'react-router-dom';
import { useExamStore } from '../../store/examStore';

export const ExamGuard: React.FC = () => {
  const { attemptStatus } = useExamStore();
  const isExamActive = attemptStatus === 'in_progress';
  const [showExitModal, setShowExitModal] = useState(false);

  // React Router v6 blocker for client-side navigation
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      isExamActive && currentLocation.pathname !== nextLocation.pathname
  );

  useEffect(() => {
    if (blocker.state === 'blocked') {
      setShowExitModal(true);
    }
  }, [blocker.state]);

  // Window beforeunload listener for browser refresh or tab close
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isExamActive) {
        e.preventDefault();
        e.returnValue = ''; // Standard browser confirmation prompt
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isExamActive]);

  return (
    <>
      <Outlet />
      {showExitModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <h3>Warning: Exam in Progress</h3>
            <p>
              Navigating away will immediately flag a violation or submit your attempt.
              Are you sure you want to leave?
            </p>
            <button onClick={() => { setShowExitModal(false); blocker.reset?.(); }}>
              Stay on Exam
            </button>
            <button onClick={() => { setShowExitModal(false); blocker.proceed?.(); }}>
              Leave Exam
            </button>
          </div>
        </div>
      )}
    </>
  );
};
```

### 4. Router Hierarchy (`frontend/src/routes/index.tsx`)
```tsx
// frontend/src/routes/index.tsx
import { createBrowserRouter } from 'react-router-dom';
import { AuthGuard } from './guards/AuthGuard';
import { AdminGuard } from './guards/AdminGuard';
import { ExamGuard } from './guards/ExamGuard';

import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { ExamScreenPage } from '../pages/ExamScreenPage';
import { AdminDashboardPage } from '../pages/AdminDashboardPage';
import { ForbiddenPage } from '../pages/ForbiddenPage';

export const router = createBrowserRouter([
  // Public routes
  { path: '/login', element: <LoginPage /> },
  { path: '/403', element: <ForbiddenPage /> },

  // Protected student routes (AuthGuard required)
  {
    element: <AuthGuard />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/dashboard', element: <DashboardPage /> },

      // Exam routes protected by both AuthGuard and ExamGuard
      {
        element: <ExamGuard />,
        children: [
          { path: '/exam/:attemptId', element: <ExamScreenPage /> },
        ],
      },

      // Admin routes protected by AdminGuard (nested inside AuthGuard)
      {
        element: <AdminGuard />,
        children: [
          { path: '/admin', element: <AdminDashboardPage /> },
        ],
      },
    ],
  },
]);
```

## Tradeoffs and known limitations
1. **Route guards provide UX protection, not data security**: Any determined user can open browser developer tools, modify the Zustand store in memory, or force React Router to render an admin component. Route guards protect user flow and prevent accidental navigation. Genuine authorization must be enforced on every backend API endpoint via JWT verification and database role checks.
2. **`useBlocker` limitations**: React Router's `useBlocker` hook requires data routers created via `createBrowserRouter`. It does not function with legacy `<BrowserRouter>` element trees.
3. **Browser tab close behavior**: While `beforeunload` prompts the user with a native browser dialog before closing a tab, modern browsers do not allow customizing the confirmation dialog text to prevent phishing.
