// Automated E2E verification test suite runner for IdeaExists (R1 - R4 requirements).
// Invoked via `node scripts/e2e-verify.mjs` or `npm test`.

import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frontendNodeModules = path.join(root, "frontend", "node_modules");

console.log("==========================================");
console.log("  IdeaExists E2E Verification Suite (Tiers 1-4)");
console.log("==========================================\n");

// Ensure NODE_PATH includes frontend/node_modules for resolution
const env = {
  ...process.env,
  NODE_PATH: process.env.NODE_PATH
    ? `${process.env.NODE_PATH}${path.delimiter}${frontendNodeModules}`
    : frontendNodeModules,
};

const result = spawnSync(
  "npx",
  ["tsx", "--tsconfig", "frontend/tsconfig.json", "scripts/e2e-verify-runner.ts"],
  {
    cwd: root,
    env,
    shell: true,
    stdio: "inherit",
  }
);

if (result.status !== 0) {
  console.error(`\n[FAIL] E2E Verification failed with exit code ${result.status}`);
  process.exit(result.status ?? 1);
} else {
  console.log("\n[PASS] All E2E Verification tests passed successfully!");
  process.exit(0);
}
