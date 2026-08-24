### Task 6: Role-based download surface and visual polish

**Files:**
- Modify: `frontend/web/src/components/research/DirectDownloads.tsx`
- Modify: `frontend/web/src/components/research/DownloadCatalog.tsx`
- Modify: `frontend/web/src/layout/Header.tsx`
- Modify: `frontend/web/src/styles/global.css`

**Interfaces:**
- `DirectDownloads({ project, role })` only creates artifacts allowed by `rolePermissions(role)`.
- `Header` displays role badge and calls `logout()` to return to `/login`.

- [ ] **Step 1: Make the Word report available to both roles; do not render CSV/BI controls to clients.**
- [ ] **Step 2: Add a compact client delivery label and PM operations label to the header.**
- [ ] **Step 3: Style login, session list/detail, active BI bar/focus card, artifact availability, and responsive behavior using the existing black/white/Apple-blue system.**
- [ ] **Step 4: Run `npm test` and `npm run build`; check the Vite routes `/login`, `/projects`, project results, and a session detail route.**

## Plan self-review

- Spec coverage: Tasks 1–3 cover role entry and guarding; Tasks 2 and 4 cover session visibility/details; Task 5 covers BI interaction; Task 6 covers role-aware artifacts and UI.
- No placeholders: Every task names concrete source paths, interfaces, checks, and commands.
- Type consistency: All tasks use `UserRole`, `ResearchSession`, `RolePermissions`, and `getFocusedEvidence` as defined in their producer task.
