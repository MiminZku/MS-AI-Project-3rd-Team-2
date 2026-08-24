import { expect, it } from "vitest";
import { rolePermissions } from "./roleAccess";

it("keeps raw research controls inside the PM workspace", () => {
  expect(rolePermissions("pm").viewPowerBiDataset).toBe(true);
  expect(rolePermissions("client").viewPowerBiDataset).toBe(false);
  expect(rolePermissions("client").viewFullTranscript).toBe(false);
});
