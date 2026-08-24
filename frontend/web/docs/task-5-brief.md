### Task 5: Click-to-focus BI interaction

**Files:**
- Modify: `frontend/web/src/components/research/InsightDashboard.tsx`
- Modify: `frontend/web/src/mock/researchProjects.ts`
- Modify: `frontend/web/src/lib/researchInsights.ts`
- Modify: `frontend/web/src/lib/researchInsights.test.ts`

**Interfaces:**
- `InsightDashboard({ project, role, linkedSession })` receives the active role and optional selected session.
- `getFocusedEvidence(project, mode, theme)` returns `{ theme, summary, quote, sessionCount, nextAction }`.

- [ ] **Step 1: Write a failing test that selects `반복 입력` and expects its summary and next action.**

```ts
expect(getFocusedEvidence(project, "evidence", "반복 입력").nextAction).toContain("확인");
```

- [ ] **Step 2: Run `npm test -- researchInsights` and verify the missing helper fails.**
- [ ] **Step 3: Add focused evidence metadata to the project fixture and implement the pure helper.**
- [ ] **Step 4: Turn every visible bar into a button with `aria-pressed`; update the focus card on click or Enter/Space.**
- [ ] **Step 5: Hide the operational session-state lens for clients; synchronize the focus card when a permitted session is selected.**
- [ ] **Step 6: Run `npm test -- researchInsights` and verify it passes.**

