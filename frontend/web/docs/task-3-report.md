# Task 3 report: first-screen login and guarded routes

## Delivered behavior

- `RoleProvider` now wraps `RouterProvider`, so the selected `pm` or `client` role exists only in the active React component tree.
- `/login` is a top-level, full-viewport dark screen. It is not nested in `Layout`, so it renders without the site header or footer.
- The login screen provides visibly selectable Project manager and Client controls, capability-specific copy, and one submit action. Submission calls `login(activeRole)` and then navigates in-app to `/projects`.
- `RequireRole` protects the `Layout` route. Consequently `/`, `/about`, `/services`, `/team`, `/contact`, `/projects`, `/projects/:projectId/results`, and `/downloads` redirect to `/login` while no role is selected.
- The prior `VITE_DASHBOARD_URL` / `window.location.href` handoff and credential fields were removed. No task-owned login, auth, or router source uses browser storage, a backend call, or an external redirect.

## TDD evidence

1. Added `src/auth/RequireRole.test.tsx` first.
2. Ran `npm test -- RequireRole` before production code. It failed as expected because `./RequireRole` did not exist.
3. Added `RequireRole.tsx`, then re-ran the focused test. Both assertions passed: anonymous state withholds protected content and an already-selected PM role renders it.

## Verification

Executed from `frontend/web` after implementation:

```text
npm test
Test Files  4 passed (4)
Tests       10 passed (10)

npm run build
tsc --noEmit && vite build
✓ built in 4.75s
```

Also ran a source scan over `src/App.tsx`, `src/auth`, and `src/pages/Login.tsx` for `localStorage`, `sessionStorage`, `VITE_DASHBOARD_URL`, `window.location`, the former localhost dashboard address, and `fetch(`. It returned no matches. `git diff --check` returned no whitespace errors.

## Files changed for Task 3

- `src/App.tsx`
- `src/auth/RequireRole.tsx`
- `src/auth/RequireRole.test.tsx`
- `src/pages/Login.tsx`
- `src/styles/global.css`
- `docs/task-3-report.md`

## Concerns

No blocker. The project does not include a browser DOM/component-test harness, so the focused test validates route-guard rendering in the existing Vitest environment; the login submit sequence is verified by implementation review plus successful TypeScript production build. No test dependencies were added.
