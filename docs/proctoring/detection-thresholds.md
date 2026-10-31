# Proctoring: Detection Thresholds & False-Positive Mitigations

## 1. Detection Threshold Matrix

| Signal | Trigger Condition | Debounce / Grace Window | False-Positive Risk & Mitigation |
|---|---|---|---|
| **Tab Switch (`visibilitychange`)** | `document.visibilityState === 'hidden'` | 0s (Instant detection) | High confidence; user switched tab or minimized window. |
| **Window Blur (`blur`)** | Window loses focus without hiding tab | 2.0s delay | Operating system notification popups or permission prompts. Handled by 2-second grace delay. |
| **Fullscreen Exit** | `document.fullscreenElement === null` | 3.0s grace period | Accidental ESC press. Dialog prompts candidate to return to fullscreen before striking. |
| **No Face Detected** | Face absent from camera frame for > 5.0s | Continuous evaluation at 3 fps | Low lighting or temporary head tilt. Only triggers after 5 consecutive seconds of absence. |
| **Multiple Faces** | More than 1 face present in frame for > 2.0s | 2.0s confirmation | Passerby behind candidate. Must persist for 2 consecutive seconds to count as strike. |

---

## 2. Server-Enforced Maximum Strikes
By default, an exam configures `max_strikes = 3`:
- **Strike 1 & 2**: A blocking modal halts exam questions and alerts the candidate of the violation.
- **Strike 3**: The server marks `status = 'auto_submitted'`, finalizes answers recorded up to that moment, and renders the disqualification report.
