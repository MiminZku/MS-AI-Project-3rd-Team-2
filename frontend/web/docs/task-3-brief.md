### Task 3: First-screen login and guarded routes

**Files:**
- Modify: `frontend/web/src/pages/Login.tsx`
- Modify: `frontend/web/src/App.tsx`
- Create: `frontend/web/src/auth/RequireRole.tsx`

**Interfaces:**
- `Login` calls `login("pm" | "client")` and navigates to `/projects`.
- `RequireRole` renders `Navigate` to `/login` when `role === null`; it wraps `Layout` and all product routes.

- [ ] **Step 1: Replace the dashboard external redirect with `useRole().login(activeRole)`.**
- [ ] **Step 2: Make `/login` a standalone dark login screen with concise role capability copy and no persisted credentials.**
- [ ] **Step 3: Place `RoleProvider` around `RouterProvider`; route `/login` outside the guarded app shell; wrap `/` in `RequireRole`.**
- [ ] **Step 4: Build with `npm run build`; verify `/` returns the login page before role choice and login sends either role to `/projects`.**

