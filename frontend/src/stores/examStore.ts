import { create } from 'zustand'

export interface ExamState {
  attemptId: string | null
  attemptStatus: 'idle' | 'not_started' | 'in_progress' | 'completed'
  strikeCount: number
  timerEndsAt: number | null // epoch ms
  isFullscreen: boolean
  setAttempt: (id: string, status: ExamState['attemptStatus']) => void
  incrementStrike: () => void
  setFullscreen: (v: boolean) => void
  reset: () => void
}

const initialState = {
  attemptId: null,
  attemptStatus: 'idle' as const,
  strikeCount: 0,
  timerEndsAt: null,
  isFullscreen: false,
}

export const useExamStore = create<ExamState>((set) => ({
  ...initialState,
  setAttempt: (id: string, status: ExamState['attemptStatus']) =>
    set({ attemptId: id, attemptStatus: status }),
  incrementStrike: () =>
    set((state) => ({ strikeCount: state.strikeCount + 1 })),
  setFullscreen: (isFullscreen: boolean) => set({ isFullscreen }),
  reset: () => set(initialState),
}))

export const examStore = useExamStore
