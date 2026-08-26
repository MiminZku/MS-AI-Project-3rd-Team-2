import { cp, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dashboardDir = resolve(webDir, "..", "dashboard");
const dashboardDist = resolve(dashboardDir, "dist");
const outputDir = resolve(webDir, "dist", "dashboard");
function run(args, cwd) {
  const result = spawnSync("npm", args, {
    cwd,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

run(["run", "build"], webDir);
if (!existsSync(resolve(dashboardDir, "node_modules"))) {
  run(["ci"], dashboardDir);
}
run(["run", "build"], dashboardDir);

await rm(outputDir, { recursive: true, force: true });
await cp(dashboardDist, outputDir, { recursive: true });
