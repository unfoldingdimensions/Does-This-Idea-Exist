// Canonical test runner — `npm test` at the repo root (cross-shell, no path games).
// Spawns absolute paths directly; fails the root run if any suite fails.
import { spawnSync } from "node:child_process";
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

run("backend smoke", py, ["-m", "tests.smoke"], path.join(root, "backend"));
// .cmd files can't spawn directly in Node — route through cmd.exe /c
run("frontend lint + build", "cmd.exe", ["/d", "/s", "/c", "npm test"], frontend);

console.log(failed ? "\nRESULT: FAILURES PRESENT" : "\nRESULT: ALL PASS");
process.exitCode = failed;
