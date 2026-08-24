# Dashboard Anonymous Interview IDs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let PMs create interview sessions using an anonymous participant ID and prevent historical session titles from appearing in the dashboard.

**Architecture:** Add a pure identity helper that normalizes and validates new participant IDs and formats existing server session IDs for display. `SessionForm` uses the helper for client-side validation, preserves the existing API `title` contract, and never renders a server-provided session title in the session list.

**Tech Stack:** React 19, TypeScript, Vitest, Vite.

## Global Constraints

- Work only on `codex/dashboard-project-creation`; do not modify `main`.
- Do not change the backend API schema; `POST /api/sessions` continues to receive `title`.
- New IDs accept only 3–40 uppercase English letters, digits, and hyphens.
- Dashboard session rows must not render `session.title`.

---

### Task 1: Add anonymous-session identity helpers

**Files:**

- Create: `frontend/dashboard/src/lib/sessionIdentity.ts`
- Test: `frontend/dashboard/src/lib/sessionIdentity.test.ts`

**Interfaces:**

- Produces: `normalizeParticipantId(value: string): string`
- Produces: `validateParticipantId(value: string): string | null`
- Produces: `formatSessionReference(sessionId: string): string`

- [ ] **Step 1: Write the failing test**

```ts
import { expect, it } from "vitest";
import { formatSessionReference, validateParticipantId } from "./sessionIdentity";

it("accepts normalized anonymous IDs and rejects name-like values", () => {
  expect(validateParticipantId(" int-001 ")).toBeNull();
  expect(validateParticipantId("김민수")).toContain("영문 대문자");
});

it("formats existing sessions from only their immutable server ID", () => {
  expect(formatSessionReference("8f9c-11")).toBe("인터뷰 · 8f9c-11");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/lib/sessionIdentity.test.ts`

Expected: FAIL because `./sessionIdentity` does not exist.

- [ ] **Step 3: Write minimal implementation**

```ts
const PARTICIPANT_ID_PATTERN = /^[A-Z0-9-]{3,40}$/;

export function normalizeParticipantId(value: string) {
  return value.trim().toUpperCase();
}

export function validateParticipantId(value: string) {
  return PARTICIPANT_ID_PATTERN.test(normalizeParticipantId(value))
    ? null
    : "참가자 ID는 3~40자의 영문 대문자, 숫자, 하이픈만 사용할 수 있습니다.";
}

export function formatSessionReference(sessionId: string) {
  return `인터뷰 · ${sessionId}`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/lib/sessionIdentity.test.ts`

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/dashboard/src/lib/sessionIdentity.ts frontend/dashboard/src/lib/sessionIdentity.test.ts
git commit -m "feat(dashboard): add anonymous session identity helpers"
```

### Task 2: Apply anonymous identity policy to the session form

**Files:**

- Modify: `frontend/dashboard/src/components/SessionForm.tsx`
- Modify: `frontend/dashboard/src/components/SessionForm.test.tsx`

**Interfaces:**

- Consumes: `normalizeParticipantId`, `validateParticipantId`, and `formatSessionReference` from `src/lib/sessionIdentity.ts`.
- Produces: an API payload where `title` is a validated anonymous ID.

- [ ] **Step 1: Write the failing test**

```tsx
it("uses participant IDs and excludes person-name examples from the PM form", () => {
  const markup = renderToStaticMarkup(<SessionForm role="pm" onCreated={() => undefined} />);

  expect(markup).toContain("참가자 ID");
  expect(markup).toContain("INT-001");
  expect(markup).not.toContain("인터뷰 세션 이름");
  expect(markup).not.toContain("김OO");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/components/SessionForm.test.tsx`

Expected: FAIL because the existing form still renders `인터뷰 세션 이름` and `김OO`.

- [ ] **Step 3: Write minimal implementation**

```tsx
const [participantId, setParticipantId] = useState("");

const normalizedParticipantId = normalizeParticipantId(participantId);
const participantIdError = validateParticipantId(normalizedParticipantId);
if (participantIdError) {
  setError(participantIdError);
  return;
}

await createSession({ title: normalizedParticipantId, duration_minutes: duration, study_id: projectId, question_script: "" });
```

Change the form label to `참가자 ID`, use `INT-001` as its placeholder, and use `formatSessionReference(session.id)` in every session-list row instead of `session.title`.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `npm test -- src/components/SessionForm.test.tsx src/lib/sessionIdentity.test.ts`

Expected: PASS, all focused tests.

- [ ] **Step 5: Run production verification**

Run: `npm test && npm run build`

Expected: the full dashboard test suite and TypeScript/Vite production build pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/dashboard/src/components/SessionForm.tsx frontend/dashboard/src/components/SessionForm.test.tsx
git commit -m "feat(dashboard): require anonymous participant IDs"
```
