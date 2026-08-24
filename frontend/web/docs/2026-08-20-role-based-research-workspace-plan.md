# Role-based Research Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make login the first screen and provide PM and client versions of the research workspace, sessions, BI, and downloads.

**Architecture:** Keep the app mock-only. A small React context holds the selected demo role for the current tab; pure permission and session helpers decide what each view can render. Project results own the selected session and pass it to a reusable BI component, whose selected bar exposes a focused evidence card without navigation.

**Tech Stack:** React 19, React Router 6, TypeScript, Vitest, Vite, `@phosphor-icons/react`.

## Global Constraints

- Change only `frontend/web/`.
- Do not call a backend API or persist role or credentials in local/session storage.
- PM can see full session data and Word/CSV exports; client can see delivery-safe summary and Word export only.
- Use `src/mock/` for every project, session, transcript, and report fixture.
- No external CDN fonts.

---

### Task 1: Role state and permission helpers

**Files:**
- Create: `frontend/web/src/auth/RoleContext.tsx`
- Create: `frontend/web/src/lib/roleAccess.ts`
- Test: `frontend/web/src/lib/roleAccess.test.ts`

**Interfaces:**
- Produces `UserRole = "pm" | "client"`, `rolePermissions(role)`, and `RoleProvider` / `useRole()`.
- `RolePermissions` includes `viewFullTranscript`, `viewOperationalSessions`, `viewPowerBiDataset`, `viewRecording`, and `viewObserverControls` booleans.

- [x] **Step 1: Write the failing permission test**

```ts
import { expect, it } from "vitest";
import { rolePermissions } from "./roleAccess";

it("keeps raw research controls inside the PM workspace", () => {
  expect(rolePermissions("pm").viewPowerBiDataset).toBe(true);
  expect(rolePermissions("client").viewPowerBiDataset).toBe(false);
  expect(rolePermissions("client").viewFullTranscript).toBe(false);
});
```

- [x] **Step 2: Run `npm test -- roleAccess` and verify the import fails.**

- [x] **Step 3: Implement the pure access table and a context that exposes this shape.**

```ts
export const rolePermissions = (role: UserRole): RolePermissions =>
  role === "pm"
    ? { viewFullTranscript: true, viewOperationalSessions: true, viewPowerBiDataset: true, viewRecording: true, viewObserverControls: true }
    : { viewFullTranscript: false, viewOperationalSessions: false, viewPowerBiDataset: false, viewRecording: false, viewObserverControls: false };
```

- [x] **Step 4: Run `npm test -- roleAccess` and verify it passes.**

### Task 2: Typed session fixtures and role-filtered lookup

**Files:**
- Create: `frontend/web/src/mock/researchSessions.ts`
- Create: `frontend/web/src/lib/researchSessions.ts`
- Test: `frontend/web/src/lib/researchSessions.test.ts`

**Interfaces:**
- Produces `ResearchSession`, `SessionStatus`, `getProjectSessions(projectId, role)`, and `getResearchSession(projectId, sessionId, role)`.
- Each fixture includes participant segment, scheduled/completed state, timing, themes, approved quotes, a PM-only note, and a linked dashboard theme.

- [x] **Step 1: Write the failing visibility test.**

```ts
it("excludes unapproved and operational sessions from client delivery", () => {
  expect(getProjectSessions("workflow-discovery", "pm")).toHaveLength(4);
  expect(getProjectSessions("workflow-discovery", "client")).toHaveLength(2);
});
```

- [x] **Step 2: Run `npm test -- researchSessions` and verify the missing helper fails.**

- [x] **Step 3: Add four realistic mock sessions and filter them with the caller role.**

```ts
export const getProjectSessions = (projectId: string, role: UserRole) =>
  researchSessions.filter((session) => session.projectId === projectId && (role === "pm" || session.clientVisible));
```

- [x] **Step 4: Run `npm test -- researchSessions` and verify it passes.**

### Task 3: First-screen login and guarded routes

**Files:**
- Modify: `frontend/web/src/pages/Login.tsx`
- Modify: `frontend/web/src/App.tsx`
- Create: `frontend/web/src/auth/RequireRole.tsx`

**Interfaces:**
- `Login` calls `login("pm" | "client")` and navigates to `/projects`.
- `RequireRole` renders `Navigate` to `/login` when `role === null`; it wraps `Layout` and all product routes.

- [x] **Step 1: Replace the dashboard external redirect with `useRole().login(activeRole)`.**
- [x] **Step 2: Make `/login` a standalone dark login screen with concise role capability copy and no persisted credentials.**
- [x] **Step 3: Place `RoleProvider` around `RouterProvider`; route `/login` outside the guarded app shell; wrap `/` in `RequireRole`.**
- [x] **Step 4: Build with `npm run build`; verify `/` returns the login page before role choice and login sends either role to `/projects`.**

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

- [x] **Step 1: Render session rows with status, segment, duration, complete time, selected state, and permitted artifact badges.**
- [x] **Step 2: Add a session panel under the project BI that links to its route.**
- [x] **Step 3: Render PM detail with full transcript, research note, recording placeholder, observer controls, and full evidence.**
- [x] **Step 4: Render client detail with the approved digest, approved quotes, and themes only. Do not mount transcript, recording, or controls in this branch.**
- [x] **Step 5: Add the nested session route and verify both roles with a valid and a client-restricted session URL.**

### Task 5: Click-to-focus BI interaction

**Files:**
- Modify: `frontend/web/src/components/research/InsightDashboard.tsx`
- Modify: `frontend/web/src/mock/researchProjects.ts`
- Modify: `frontend/web/src/lib/researchInsights.ts`
- Modify: `frontend/web/src/lib/researchInsights.test.ts`

**Interfaces:**
- `InsightDashboard({ project, role, linkedSession })` receives the active role and optional selected session.
- `getFocusedEvidence(project, mode, theme)` returns `{ theme, summary, quote, sessionCount, nextAction }`.

- [x] **Step 1: Write a failing test that selects `반복 입력` and expects its summary and next action.**

```ts
expect(getFocusedEvidence(project, "evidence", "반복 입력").nextAction).toContain("확인");
```

- [x] **Step 2: Run `npm test -- researchInsights` and verify the missing helper fails.**
- [x] **Step 3: Add focused evidence metadata to the project fixture and implement the pure helper.**
- [x] **Step 4: Turn every visible bar into a button with `aria-pressed`; update the focus card on click or Enter/Space.**
- [x] **Step 5: Hide the operational session-state lens for clients; synchronize the focus card when a permitted session is selected.**
- [x] **Step 6: Run `npm test -- researchInsights` and verify it passes.**

### Task 6: Role-based download surface and visual polish

**Files:**
- Modify: `frontend/web/src/components/research/DirectDownloads.tsx`
- Modify: `frontend/web/src/components/research/DownloadCatalog.tsx`
- Modify: `frontend/web/src/layout/Header.tsx`
- Modify: `frontend/web/src/styles/global.css`

**Interfaces:**
- `DirectDownloads({ project, role })` only creates artifacts allowed by `rolePermissions(role)`.
- `Header` displays role badge and calls `logout()` to return to `/login`.

- [x] **Step 1: Make the Word report available to both roles; do not render CSV/BI controls to clients.**
- [x] **Step 2: Add a compact client delivery label and PM operations label to the header.**
- [x] **Step 3: Style login, session list/detail, active BI bar/focus card, artifact availability, and responsive behavior using the existing black/white/Apple-blue system.**
- [x] **Step 4: Run `npm test` and `npm run build`; check the Vite routes `/login`, `/projects`, project results, and a session detail route.**

## Plan self-review

- Spec coverage: Tasks 1–3 cover role entry and guarding; Tasks 2 and 4 cover session visibility/details; Task 5 covers BI interaction; Task 6 covers role-aware artifacts and UI.
- No placeholders: Every task names concrete source paths, interfaces, checks, and commands.
- Type consistency: All tasks use `UserRole`, `ResearchSession`, `RolePermissions`, and `getFocusedEvidence` as defined in their producer task.
