// Canonical test runner — `npm test` at the repo root (cross-shell, no path games).
// Spawns absolute paths directly; fails the root run if any suite fails.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const py = path.join(root, "backend", ".venv", "Scripts", "python.exe");
const frontend = path.join(root, "frontend");

let failed = 0;

function run(name, cmd, args, cwd) {
  const r = spawnSync(cmd, args, { cwd, stdio: "inherit" });
  console.log(`\n[${r.status === 0 ? "PASS" : "FAIL"}] ${name} (exit ${r.status})`);
  if (r.status !== 0) failed = 1;
}

// A missing venv otherwise surfaces as an opaque spawn ENOENT (or, worse, an
// import error from a venv that exists but has no app deps installed).
if (!existsSync(py)) {
  console.error(
    `\n[FAIL] backend venv missing at ${py}\n` +
      `       python -m venv backend/.venv && ` +
      `backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt`,
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
// .cmd files can't spawn directly in Node — route through cmd.exe /c
run("frontend lint + build", "cmd.exe", ["/d", "/s", "/c", "npm test"], frontend);

console.log(failed ? "\nRESULT: FAILURES PRESENT" : "\nRESULT: ALL PASS");
process.exitCode = failed;
