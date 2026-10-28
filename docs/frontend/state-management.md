# Frontend State Management — Zustand for Client State, React Query for Server State

## What it is
The frontend architecture explicitly divides state into two distinct categories: **Client State** (transient UI flags, active exam timers, proctoring violation counters, and auth sessions) managed via **Zustand**, and **Server State** (remote data such as quizzes, attempts, and document chunks fetched from the API) managed via **TanStack React Query**.

## Why we need it / Why this approach
Conflating server-cached data with local interactive client state is the root cause of complexity, race conditions, and synchronization bugs in single-page applications:
1. **The fundamental difference in state paradigms**:
   - *Server State* is owned remotely by the backend database. The frontend only holds a temporary, potentially stale snapshot. It requires cache invalidation, deduplication of concurrent requests, background synchronization on window focus, retry logic on network glitches, and loading/error status indicators.
   - *Client State* is owned entirely by the browser. It is synchronous, local, and immediate (e.g., whether the exam webcam preview modal is open, or current question index).
2. **Why Zustand for client state**:
   - Redux Toolkit demands massive boilerplate: defining actions, reducers, slices, complex selectors, dispatch calls, and wrapping the app in top-level `<Provider>` components.
   - Zustand provides a lightweight (<1kB), hook-based store. Stores can be read and updated anywhere—even outside React components (such as within Axios request interceptors).
   - Zustand integrates seamlessly with TypeScript and provides official middleware like `persist` to synchronize auth tokens to `localStorage` automatically.
3. **Why React Query for server state**:
   - Replaces the fragile and boilerplate-heavy `useEffect + fetch + useState` pattern.
   - Automatically manages in-flight request deduplication: if three components request the active quiz details simultaneously, React Query issues only a single HTTP network request.
   - Provides out-of-the-box cache invalidation, automatic polling, window focus refetching, and optimistic mutations for question answering.
4. **Why not Zustand for server state**: Zustand has no built-in knowledge of cache freshness, time-to-live (`staleTime`), network retry policies, or asynchronous query deduplication. Forcing Zustand to manage server state requires manually writing hundreds of lines of fetching, caching, and error-handling logic that React Query handles declaratively.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Redux Toolkit for all state | Excessive boilerplate (slices, reducers, dispatchers, selectors); heavy bundle footprint; unnecessary ceremony for the application scope. |
| React Context API for global state | Triggers re-renders across all consuming child components whenever any single value in context updates, unless heavily wrapped in custom memoization wrappers. |
| Zustand for all state (client + server) | Requires manually writing request deduplication, cache expiration, retry algorithms, and background refetching logic. |
| Raw `useEffect` + `useState` | Prone to memory leaks, race conditions with unmounted components, duplicate fetch calls, and zero cross-component caching. |

## Implementation details

Client state stores reside in `frontend/src/store/`, while server query hooks reside in `frontend/src/hooks/queries/` or `frontend/src/api/`.

### 1. Client State with Zustand (`frontend/src/store/authStore.ts`)
The authentication store manages tokens and current user information, synchronized to `localStorage` via the `persist` middleware:

```typescript
// frontend/src/store/authStore.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: 'student' | 'admin';
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,

      setTokens: (accessToken, refreshToken) =>
        set({ accessToken, refreshToken, isAuthenticated: true }),

      setUser: (user) => set({ user }),

      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'quiz-auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
```

### 2. Server State with React Query (`frontend/src/hooks/queries/useQuiz.ts`)
Fetching quiz details uses `useQuery`, providing automatic caching, error handling, and typed returns:

```typescript
// frontend/src/hooks/queries/useQuiz.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';

export interface Question {
  id: string;
  text: string;
  options: string[];
}

export interface QuizDetail {
  id: string;
  title: string;
  timeLimitMinutes: number;
  proctoringEnabled: boolean;
  questions: Question[];
}

export const useQuiz = (quizId: string) => {
  return useQuery<QuizDetail, Error>({
    queryKey: ['quiz', quizId],
    queryFn: async () => {
      const response = await apiClient.get(`/quizzes/${quizId}`);
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // Data remains fresh for 5 minutes
    retry: 2,                 // Automatically retry network failures twice
    enabled: Boolean(quizId), // Prevent execution until quizId is provided
  });
};

// Optimistic answer submission mutation
export const useSubmitAnswer = (attemptId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ questionId, selectedIndex }: { questionId: string; selectedIndex: number }) => {
      const response = await apiClient.post(`/attempts/${attemptId}/answers`, {
        question_id: questionId,
        selected_index: selectedIndex,
      });
      return response.data;
    },
    onSuccess: () => {
      // Invalidate attempt progress query to reflect recorded answer
      queryClient.invalidateQueries({ queryKey: ['attempt', attemptId] });
    },
  });
};
```

### 3. Usage Inside a Component (`frontend/src/pages/QuizPage.tsx`)
```tsx
// frontend/src/pages/QuizPage.tsx
import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuiz } from '../hooks/queries/useQuiz';

export const QuizPage: React.FC = () => {
  const { quizId } = useParams<{ quizId: string }>();
  const { data: quiz, isLoading, isError, error } = useQuiz(quizId || '');

  if (isLoading) return <div className="spinner">Loading quiz questions...</div>;
  if (isError) return <div className="error-banner">Failed to load quiz: {error.message}</div>;
  if (!quiz) return null;

  return (
    <div className="quiz-container">
      <h1>{quiz.title}</h1>
      <p>Time Limit: {quiz.timeLimitMinutes} minutes</p>
      <div className="questions-list">
        {quiz.questions.map((q, idx) => (
          <div key={q.id} className="question-card">
            <h3>Q{idx + 1}: {q.text}</h3>
            <ul>
              {q.options.map((opt, oIdx) => (
                <li key={oIdx}>{opt}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## Tradeoffs and known limitations
1. **Mental model learning curve**: Developers accustomed to placing everything into a single Redux store must adjust to deciding whether a piece of data belongs in Zustand or React Query. Rule of thumb: If it originates from an API endpoint, it belongs in React Query; if it originates from user UI interaction or client environment, it belongs in Zustand.
2. **Local storage security**: Storing Zustand state in `localStorage` exposes sensitive JWT tokens to client-side scripts. Mitigated by strict Content Security Policies (CSP) and planned migration to HttpOnly cookies.
3. **Cache synchronization during active exams**: React Query's default behavior refetches queries on window focus (`refetchOnWindowFocus: true`). During an active proctored exam, an intentional blur/focus event could trigger unwanted background refetches. Exam query hooks must explicitly set `refetchOnWindowFocus: false` to avoid disturbing active exam timers.
