/**
 * Standalone, framework-agnostic Proctoring Engine.
 * Monotonically tracks tab visibility, window blur, and fullscreen state.
 * Dispatches queued events to backend with offline retry buffering.
 */

export type ProctorEventType =
  | 'tab_switch'
  | 'fullscreen_exit'
  | 'no_face'
  | 'multiple_faces'
  | 'looking_away'

export interface ProctorViolationPayload {
  seq: number
  event_type: ProctorEventType
  occurred_at: string
  metadata?: Record<string, any>
}

export type ViolationListener = (event: ProctorViolationPayload) => void

export class ProctorEngine {
  private attemptId: string
  private seqCounter = 1
  private isRunning = false
  private listeners: ViolationListener[] = []
  private offlineBuffer: ProctorViolationPayload[] = []
  private lastBlurTimestamp = 0
  private lastFullscreenExitTimestamp = 0

  constructor(attemptId: string) {
    this.attemptId = attemptId
    this.loadOfflineBuffer()
  }

  public start(): void {
    if (this.isRunning) return
    this.isRunning = true

    document.addEventListener('visibilitychange', this.handleVisibilityChange)
    window.addEventListener('blur', this.handleWindowBlur)
    document.addEventListener('fullscreenchange', this.handleFullscreenChange)
    window.addEventListener('online', this.handleReconnect)

    // Suppress keyboard shortcuts & context menu on active exam window
    window.addEventListener('contextmenu', this.suppressEvent)
    window.addEventListener('copy', this.suppressEvent)
    window.addEventListener('paste', this.suppressEvent)
    window.addEventListener('keydown', this.handleKeydown)
  }

  public stop(): void {
    if (!this.isRunning) return
    this.isRunning = false

    document.removeEventListener('visibilitychange', this.handleVisibilityChange)
    window.removeEventListener('blur', this.handleWindowBlur)
    document.removeEventListener('fullscreenchange', this.handleFullscreenChange)
    window.removeEventListener('online', this.handleReconnect)

    window.removeEventListener('contextmenu', this.suppressEvent)
    window.removeEventListener('copy', this.suppressEvent)
    window.removeEventListener('paste', this.suppressEvent)
    window.removeEventListener('keydown', this.handleKeydown)
  }

  public onViolation(cb: ViolationListener): () => void {
    this.listeners.push(cb)
    return () => {
      this.listeners = this.listeners.filter((l) => l !== cb)
    }
  }

  public triggerViolation(
    eventType: ProctorEventType,
    metadata?: Record<string, any>
  ): void {
    const payload: ProctorViolationPayload = {
      seq: this.seqCounter++,
      event_type: eventType,
      occurred_at: new Date().toISOString(),
      metadata,
    }

    // Notify registered local listeners (UI alerts, strike increments)
    this.listeners.forEach((fn) => fn(payload))

    // Dispatch to backend API
    this.dispatchViolation(payload)
  }

  private handleVisibilityChange = (): void => {
    if (document.visibilityState === 'hidden') {
      this.triggerViolation('tab_switch', { reason: 'visibility_hidden' })
    }
  }

  private handleWindowBlur = (): void => {
    const now = Date.now()
    // 2-second debounce for OS popups
    if (now - this.lastBlurTimestamp > 2000 && document.visibilityState !== 'hidden') {
      this.lastBlurTimestamp = now
      this.triggerViolation('tab_switch', { reason: 'window_blur' })
    }
  }

  private handleFullscreenChange = (): void => {
    const isFullscreen = !!document.fullscreenElement
    const now = Date.now()
    if (!isFullscreen) {
      if (now - this.lastFullscreenExitTimestamp > 3000) {
        this.lastFullscreenExitTimestamp = now
        this.triggerViolation('fullscreen_exit')
      }
    }
  }

  private handleReconnect = async (): Promise<void> => {
    if (this.offlineBuffer.length > 0) {
      const pending = [...this.offlineBuffer]
      this.offlineBuffer = []
      this.saveOfflineBuffer()

      for (const item of pending) {
        await this.dispatchViolation(item)
      }
    }
  }

  private async dispatchViolation(payload: ProctorViolationPayload): Promise<void> {
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`/api/v1/attempts/${this.attemptId}/violations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        this.offlineBuffer.push(payload)
        this.saveOfflineBuffer()
      }
    } catch {
      // Network failed, queue in offline buffer
      this.offlineBuffer.push(payload)
      this.saveOfflineBuffer()
    }
  }

  private suppressEvent = (e: Event): void => {
    e.preventDefault()
  }

  private handleKeydown = (e: KeyboardEvent): void => {
    // Suppress Ctrl+P / Cmd+P (print), Ctrl+S (save), F12 (dev tools deterrent)
    if (
      (e.ctrlKey || e.metaKey) &&
      ['p', 's', 'c', 'u'].includes(e.key.toLowerCase())
    ) {
      e.preventDefault()
    }
  }

  private saveOfflineBuffer(): void {
    try {
      localStorage.setItem(
        `offline_violations_${this.attemptId}`,
        JSON.stringify(this.offlineBuffer)
      )
    } catch {
      // Ignore storage quota errors
    }
  }

  private loadOfflineBuffer(): void {
    try {
      const raw = localStorage.getItem(`offline_violations_${this.attemptId}`)
      if (raw) {
        this.offlineBuffer = JSON.parse(raw)
      }
    } catch {
      this.offlineBuffer = []
    }
  }
}
