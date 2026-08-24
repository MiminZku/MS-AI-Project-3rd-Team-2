### Task 2: Typed session fixtures and role-filtered lookup

**Files:**
- Create: `frontend/web/src/mock/researchSessions.ts`
- Create: `frontend/web/src/lib/researchSessions.ts`
- Test: `frontend/web/src/lib/researchSessions.test.ts`

**Interfaces:**
- Produces `ResearchSession`, `SessionStatus`, `getProjectSessions(projectId, role)`, and `getResearchSession(projectId, sessionId, role)`.
- Each fixture includes participant segment, scheduled/completed state, timing, themes, approved quotes, a PM-only note, and a linked dashboard theme.

- [ ] **Step 1: Write the failing visibility test.**

```ts
it("excludes unapproved and operational sessions from client delivery", () => {
  expect(getProjectSessions("workflow-discovery", "pm")).toHaveLength(4);
  expect(getProjectSessions("workflow-discovery", "client")).toHaveLength(2);
});
```

- [ ] **Step 2: Run `npm test -- researchSessions` and verify the missing helper fails.**

- [ ] **Step 3: Add four realistic mock sessions and filter them with the caller role.**

```ts
export const getProjectSessions = (projectId: string, role: UserRole) =>
  researchSessions.filter((session) => session.projectId === projectId && (role === "pm" || session.clientVisible));
```

- [ ] **Step 4: Run `npm test -- researchSessions` and verify it passes.**

