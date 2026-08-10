// 320px reflow check via CDP Emulation.setDeviceMetricsOverride (headless Chrome)
// Usage: node reflow-check.mjs <url> [width]
const url = process.argv[2] || "http://localhost:3024/";
const width = parseInt(process.argv[3] || "320", 10);

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";

const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const port = 9333;
const chrome = spawn(chromePath, [
  "--headless=new", "--no-sandbox", "--disable-gpu",
  `--remote-debugging-port=${port}`, "about:blank",
], { stdio: "ignore" });

const sleep = ms => new Promise(r => setTimeout(r, ms));
let page;
for (let i = 0; i < 40; i++) {
  try {
    page = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" })).json();
    break;
  } catch { await sleep(250); }
}
if (!page) { console.log("FAIL: chrome did not start"); chrome.kill(); process.exit(1); }

const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const send = (method, params = {}) => new Promise((res, rej) => {
  const mid = ++id;
  pending.set(mid, { res, rej });
  ws.send(JSON.stringify({ id: mid, method, params }));
});
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const p = pending.get(m.id);
    pending.delete(m.id);
    m.error ? p.rej(new Error(m.error.message)) : p.res(m.result);
  }
};
await new Promise(r => ws.onopen = r);

await send("Emulation.setDeviceMetricsOverride", { width, height: 800, deviceScaleFactor: 1, mobile: true });
await send("Page.navigate", { url });
await sleep(3500);
const res = await send("Runtime.evaluate", {
  expression: `JSON.stringify((() => {
    const sw = document.documentElement.scrollWidth;
    const iw = window.innerWidth;
    const wide = [...document.querySelectorAll('*')]
      .map(el => ({ t: el.tagName, w: el.getBoundingClientRect().width, minW: getComputedStyle(el).minWidth, cls: (el.className||'').toString().slice(0,40) }))
      .filter(o => o.minW !== '0px' && parseFloat(o.minW) > 320)
      .slice(0, 8);
    return { sw, iw, hScroll: sw > iw, wideElements: wide };
  })())`,
  returnByValue: true,
});
console.log("RESULT", res.result.value);
chrome.kill();
process.exit(0);
