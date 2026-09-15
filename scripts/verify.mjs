// Canonical test runner — `npm test` at the repo root (cross-shell, no path games).
// Spawns absolute paths directly; fails the root run if any suite fails.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// venv layout differs by platform: Scripts\python.exe (Windows) vs bin/python (POSIX).
const py = [
  path.join(root, "backend", ".venv", "Scripts", "python.exe"),
  path.join(root, "backend", ".venv", "bin", "python"),
].find((p) => existsSync(p));
const frontend = path.join(root, "frontend");

let failed = 0;

function run(name, cmd, args, cwd, opts = {}) {
  const r = spawnSync(cmd, args, { cwd, stdio: "inherit", ...opts });
  console.log(`\n[${r.status === 0 ? "PASS" : "FAIL"}] ${name} (exit ${r.status})`);
  if (r.status !== 0) failed = 1;
}

// A missing venv otherwise surfaces as an opaque spawn ENOENT (or, worse, an
// import error from a venv that exists but has no app deps installed).
if (!py) {
  const pyExe = process.platform === "win32" ? "Scripts\\python.exe" : "bin/python";
  console.error(
    `\n[FAIL] backend venv missing at backend/.venv\n` +
      `       python -m venv backend/.venv && ` +
      `backend/.venv/${pyExe} -m pip install -r backend/requirements.txt`,
  );
  process.exit(1);
}

run("backend smoke", py, ["-m", "tests.smoke"], path.join(root, "backend"));
// Node >=23 strips the TS types natively, so this runs the real module.
run(
  "frontend sort check",
  process.execPath,
  ["--disable-warning=MODULE_TYPELESS_PACKAGE_JSON", path.join(root, "scripts", "sort-check.ts")],
  root,
);
// npm is npm.cmd on Windows, and .cmd shims can't spawn directly (post-CVE-2024-27980
// Node rejects them without a shell) — a shell invocation resolves both platforms.
// ALLOW_LOCALHOST_BUILD: next.config.ts refuses a prod build with localhost API/SITE
// defaults; this test build is exactly that intentional local case.
run("frontend lint + build", "npm", ["test"], frontend, {
  shell: true,
  env: { ...process.env, ALLOW_LOCALHOST_BUILD: "1" },
});
run(
  "frontend e2e verification",
  process.execPath,
  [path.join(root, "scripts", "e2e-verify.mjs")],
  root,
);

console.log(failed ? "\nRESULT: FAILURES PRESENT" : "\nRESULT: ALL PASS");
process.exitCode = failed;
