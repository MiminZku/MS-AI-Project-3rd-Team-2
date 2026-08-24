### Task 1: Role state and permission helpers

**Files:**
- Create: `frontend/web/src/auth/RoleContext.tsx`
- Create: `frontend/web/src/lib/roleAccess.ts`
- Test: `frontend/web/src/lib/roleAccess.test.ts`

**Interfaces:**
- Produces `UserRole = "pm" | "client"`, `rolePermissions(role)`, and `RoleProvider` / `useRole()`.
- `RolePermissions` includes `viewFullTranscript`, `viewOperationalSessions`, `viewPowerBiDataset`, `viewRecording`, and `viewObserverControls` booleans.

- [ ] **Step 1: Write the failing permission test**

```ts
import { expect, it } from "vitest";
import { rolePermissions } from "./roleAccess";

it("keeps raw research controls inside the PM workspace", () => {
  expect(rolePermissions("pm").viewPowerBiDataset).toBe(true);
  expect(rolePermissions("client").viewPowerBiDataset).toBe(false);
  expect(rolePermissions("client").viewFullTranscript).toBe(false);
});
```

- [ ] **Step 2: Run `npm test -- roleAccess` and verify the import fails.**

- [ ] **Step 3: Implement the pure access table and a context that exposes this shape.**

```ts
export const rolePermissions = (role: UserRole): RolePermissions =>
  role === "pm"
    ? { viewFullTranscript: true, viewOperationalSessions: true, viewPowerBiDataset: true, viewRecording: true, viewObserverControls: true }
    : { viewFullTranscript: false, viewOperationalSessions: false, viewPowerBiDataset: false, viewRecording: false, viewObserverControls: false };
```

- [ ] **Step 4: Run `npm test -- roleAccess` and verify it passes.**

