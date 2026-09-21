#!/usr/bin/env node
// render.mjs - the liveness funnel's renderer: one process, N jobs, NO judging.
//
// WHY THIS EXISTS: the HTTP pass cannot see client-rendered truth. Round 4 of
// the 2026-09-18 audit settled 16 of 18 UNKNOWN rows with a real browser
// (client-rendered SPAs that answer an empty shell to a scripted client, GoDaddy
// landers that only exist after JS, SiteGround's 202-with-empty-body captcha).
// That pass ran by hand from a vendored copy; this file is it, in the repo.
//
// The judging lives in Python (scripts/liveness_rules.py) so an HTTP capture and
// a rendered capture are decided by the SAME rules - this process only renders
// and reports what the browser saw.
//
// usage: node render.mjs <jobs.json> <out.jsonl>
//   jobs.json: {"chromePath": "C:\\...\\chrome.exe", "timeoutMs": 35000,
//               "waitMs": 1500, "maxChars": 400000,
//               "jobs": [{"id": 123, "url": "https://example.com"}, ...]}
//   out.jsonl: one line per job, always - a failure is data, not a crash:
//   {"id":123, "url":"...", "ok":true, "status":200, "final_url":"...",
//    "title":"...", "h1":"...", "visible":"...", "html":"...", "error":""}
//
// The visible text comes from document.body.innerText (what a human sees -
// doctrine 7: scan visible text, not raw HTML), and the rendered DOM is
// included (capped) so the class-B CMS-shell rules can see artefacts that only
// exist in markup, exactly as they can for an HTTP capture.
import fs from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
let puppeteer;
try {
  puppeteer = require("puppeteer-core");
} catch {
  console.error("puppeteer-core is not installed: cd scripts/render && npm install");
  process.exit(2);
}

const [jobsPath, outPath] = process.argv.slice(2);
if (!jobsPath || !outPath) {
  console.error("usage: node render.mjs <jobs.json> <out.jsonl>");
  process.exit(2);
}
const cfg = JSON.parse(fs.readFileSync(jobsPath, "utf8"));
const jobs = cfg.jobs || [];
const timeoutMs = cfg.timeoutMs || 35000;
const waitMs = cfg.waitMs ?? 1500;
const maxChars = cfg.maxChars || 400000;

if (!cfg.chromePath || !fs.existsSync(cfg.chromePath)) {
  console.error(`chrome not found: ${cfg.chromePath || "(none given)"} - ` +
    "pass --chrome or set CHROME_PATH");
  process.exit(2);
}

const out = fs.createWriteStream(outPath, { encoding: "utf8" });
const write = (obj) => out.write(JSON.stringify(obj) + "\n");

const browser = await puppeteer.launch({
  executablePath: cfg.chromePath,
  headless: true,
  args: [
    "--no-first-run", "--no-default-browser-check", "--disable-background-network",
    "--disable-sync", "--disable-extensions", "--mute-audio", "--no-sandbox",
  ],
});

let done = 0;
try {
  for (const job of jobs) {
    const row = {
      id: job.id, url: job.url, ok: false, status: null, final_url: "",
      title: "", h1: "", visible: "", html: "", error: "",
      rendered_at: new Date().toISOString(),
    };
    let page;
    try {
      // per-job pre-goto gap from the Python politeness schedule (doctrine 10)
      const pre = Number(job.waitMs) || 0;
      if (pre > 0) await new Promise((r) => setTimeout(r, pre));
      page = await browser.newPage();
      await page.setUserAgent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36");
      const resp = await page.goto(job.url, {
        waitUntil: "networkidle2", timeout: timeoutMs,
      });
      if (waitMs > 0) await new Promise((r) => setTimeout(r, waitMs));
      const seen = await page.evaluate((cap) => ({
        title: document.title || "",
        h1: (document.querySelector("h1")?.textContent || "").trim().slice(0, 200),
        visible: (document.body?.innerText || "").replace(/\s+/g, " ").trim()
          .slice(0, 60000),
        html: (document.documentElement?.outerHTML || "").slice(0, cap),
        finalUrl: location.href,
      }), maxChars);
      row.ok = true;
      row.status = resp ? resp.status() : null;
      Object.assign(row, seen, { final_url: seen.finalUrl });
    } catch (err) {
      row.error = String(err && err.message ? err.message : err).slice(0, 240);
    } finally {
      if (page) await page.close().catch(() => {});
    }
    write(row);
    done += 1;
    if (done % 5 === 0 || done === jobs.length) {
      console.error(`rendered ${done}/${jobs.length}`);
    }
  }
} finally {
  await browser.close().catch(() => {});
  out.end();
}
