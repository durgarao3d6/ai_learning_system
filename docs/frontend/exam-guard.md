# Frontend: ExamGuard Route Protection & Browser Boundaries

## 1. Why Route-Level Guards Over Component State?
Component-level checks (e.g. `useEffect` redirects inside `ExamPage`) allow the React tree to partially mount and expose routes before canceling navigation. 

Using React Router v6 `<Route element={<ExamGuard />}>`:
- Completely intercepts transitions to unauthorized routes before subtrees mount.
- Keeps exam state evaluation centralized in Zustand (`examStore.ts`).

---

## 2. Navigation Interception Mechanics
When an attempt is in status `in_progress`:
1. **React Router Navigation**:
   Any attempt to click a sidebar link (`/library`, `/progress`, `/create`) is blocked. A warning modal prompts: *"An active exam is in progress. Leaving this page will submit your exam or register a violation."*
2. **Browser Reload / Tab Close (`beforeunload`)**:
   An event listener attaches `e.preventDefault()` and sets `e.returnValue = ''`, triggering the browser's standard confirmation prompt ("Leave site? Changes you made may not be saved").
3. **Copy, Paste, Right-Click, Print Suppression**:
   Listeners block `contextmenu`, `copy`, `paste`, and `keydown` for `Ctrl+P`/`Cmd+P` on the exam route to deter casual copying.
