# Proctoring Engine Architecture

## 1. Design Overview
The `ProctorEngine` is an isolated, framework-agnostic TypeScript module responsible for tracking candidate integrity during an online examination. 

### Why Class-Based instead of React Hooks?
1. **Framework Independence / Portability**:
   Writing `ProctorEngine` as a pure JS/TS class allows it to run seamlessly inside:
   - A standard React web application.
   - An Electron desktop shell (Phase 7) without rewriting detection logic.
   - Headless background workers or browser automation runners.
2. **Lifecycle Decoupling**:
   React hooks are tightly coupled to the component re-render lifecycle. Hook-based event listeners can lead to accidental unbinding, multiple subscriptions, or missed events during state updates. A singleton class instance manages an explicit `.start()`, `.stop()`, and `.flush()` lifecycle.

---

## 2. API Contract

```typescript
export interface ViolationEvent {
  sequence_number: number
  event_type: 'tab_switch' | 'fullscreen_exit' | 'no_face' | 'multiple_faces' | 'looking_away'
  timestamp: string
  metadata?: Record<string, any>
}

export class ProctorEngine {
  start(): void
  stop(): void
  onViolation(callback: (event: ViolationEvent) => void): void
  flush(): Promise<void>
}
```

---

## 3. Threat Model: Evidence Signals vs Cryptographic Proof
Browser APIs (`visibilitychange`, `blur`, `fullscreenchange`) are client-side constructs that can theoretically be simulated or bypassed by advanced tampering. Therefore, the backend treats every incoming violation as an **evidence signal** with monotonic sequence numbers and server-side validation rather than unassailable cryptographic proof.
