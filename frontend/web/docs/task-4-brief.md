### Task 4: Session list and role-aware detail screen

**Files:**
- Create: `frontend/web/src/components/research/SessionList.tsx`
- Create: `frontend/web/src/components/research/SessionDetail.tsx`
- Create: `frontend/web/src/pages/ResearchSession.tsx`
- Modify: `frontend/web/src/pages/ResearchResults.tsx`
- Modify: `frontend/web/src/App.tsx`

**Interfaces:**
- `SessionList({ projectId, selectedSessionId, onSelect })` displays a vertical list and invokes `onSelect(session)`.
- `ResearchSession` resolves `/projects/:projectId/sessions/:sessionId`, redirects to its role-permitted project results when unavailable, and renders `SessionDetail`.

- [ ] **Step 1: Render session rows with status, segment, duration, complete time, selected state, and permitted artifact badges.**
- [ ] **Step 2: Add a session panel under the project BI that links to its route.**
- [ ] **Step 3: Render PM detail with full transcript, research note, recording placeholder, observer controls, and full evidence.**
- [ ] **Step 4: Render client detail with the approved digest, approved quotes, and themes only. Do not mount transcript, recording, or controls in this branch.**
- [ ] **Step 5: Add the nested session route and verify both roles with a valid and a client-restricted session URL.**

