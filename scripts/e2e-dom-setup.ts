/**
 * IdeaExists e2e DOM bootstrap — imported FIRST by a suite runner.
 *
 * Why this is its own module, and why it must be the first import:
 *
 * Several upstream packages capture a global at *module-evaluation* time rather
 * than at render time. The one that bit here is Radix's layout-effect shim:
 *
 *     var useLayoutEffect2 = globalThis?.document ? React.useLayoutEffect : () => {};
 *
 * When a runner installs jsdom inline, esbuild has already hoisted every
 * `import` above that code, so Radix (and anything else that resolves a global
 * once) is evaluated against a world with no `document` — its portal's
 * `useLayoutEffect` becomes a no-op, `mounted` never flips, and every dialog and
 * popover silently renders nothing. Importing this module first guarantees the
 * DOM globals exist before React, Radix, next-themes or the app code loads.
 *
 * Keep it side-effect-only apart from `setReducedMotion`, which the suites need
 * to drive the harness's reduced-motion state.
 */

import { JSDOM } from "jsdom";

const dom = new JSDOM(
  "<!DOCTYPE html><html><head></head><body><div id='root'></div></body></html>",
  { url: "http://localhost:3000/", pretendToBeVisual: true },
);

const g = globalThis as unknown as Record<string, unknown>;
const w = dom.window as unknown as Record<string, unknown>;

g.IS_REACT_ACT_ENVIRONMENT = true;
g.window = dom.window;
g.document = dom.window.document;
// Node >=21 defines its OWN `navigator` global (a getter with no setter), so a
// plain assignment silently leaves Node's Navigator in place — and then app code
// reading a bare `navigator.clipboard` gets Node's, not the DOM's. Redefine it.
Object.defineProperty(globalThis, "navigator", {
  configurable: true,
  writable: true,
  value: dom.window.navigator,
});
// `self` is what React's client runtime and next/link read in a browser; without
// it every render that touches a `next/link` throws "self is not defined".
g.self = dom.window;

/**
 * Move jsdom's constructors onto the Node global scope — but only the ones Node
 * does not already provide, so Node's own `URL` / `Blob` / `AbortSignal` (which
 * `lib/api.ts` needs for `AbortSignal.timeout`) survive untouched. Event
 * constructors are overwritten deliberately: a `new MouseEvent()` must be the
 * same class the jsdom nodes dispatch and React listens for.
 */
const FROM_WINDOW: readonly string[] = [
  // DOM core
  "HTMLElement", "Element", "Node", "NodeList", "DocumentFragment", "Text", "Comment",
  // events (overwritten: React's synthetic system needs jsdom's classes)
  "Event", "CustomEvent", "MouseEvent", "KeyboardEvent", "PointerEvent", "FocusEvent",
  "InputEvent", "UIEvent", "AnimationEvent", "TransitionEvent", "DragEvent", "WheelEvent",
  // element interfaces React/props touch
  "HTMLInputElement", "HTMLTextAreaElement", "HTMLButtonElement", "HTMLAnchorElement",
  "HTMLDivElement", "HTMLSpanElement", "HTMLParagraphElement", "HTMLSelectElement",
  "HTMLOptionElement", "HTMLFormElement", "HTMLImageElement", "HTMLLabelElement",
  "HTMLTableElement", "SVGElement",
  // misc the Radix portal/focus-scope path reads
  "DOMRect", "DOMRectReadOnly", "DOMParser", "MutationObserver", "getComputedStyle",
  "getSelection", "sessionStorage", "localStorage",
];
const OVERWRITE = new Set(["Event", "CustomEvent", "MouseEvent", "KeyboardEvent"]);
for (const key of FROM_WINDOW) {
  if (typeof w[key] === "undefined") continue;
  if (g[key] !== undefined && !OVERWRITE.has(key)) continue;
  g[key] = w[key];
}

// --- matchMedia with a controllable reduced-motion state ---------------------

let reducedMotionState = false;
const mediaListeners = new Set<(e: unknown) => void>();

w.matchMedia = function (query: string) {
  const isReduced = query.includes("prefers-reduced-motion");
  return {
    matches: isReduced ? reducedMotionState : false,
    media: query,
    onchange: null,
    addListener: (cb: (e: unknown) => void) => { mediaListeners.add(cb); },
    removeListener: (cb: (e: unknown) => void) => { mediaListeners.delete(cb); },
    addEventListener: (_evt: string, cb: (e: unknown) => void) => { mediaListeners.add(cb); },
    removeEventListener: (_evt: string, cb: (e: unknown) => void) => { mediaListeners.delete(cb); },
    dispatchEvent: () => true,
  };
};

/** Flip the harness's `prefers-reduced-motion` and notify every subscriber. */
export function setReducedMotion(reduced: boolean): void {
  reducedMotionState = reduced;
  mediaListeners.forEach((cb) => cb({ matches: reduced }));
}

// --- observers, rAF, scrolling ----------------------------------------------

const MockIntersectionObserver = class IntersectionObserver {
  constructor(public callback: (entries: unknown[], observer: unknown) => void) {}
  observe() { this.callback([{ isIntersecting: true }], this); }
  unobserve() {}
  disconnect() {}
};

const MockResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

w.IntersectionObserver = MockIntersectionObserver;
w.ResizeObserver = MockResizeObserver;
g.IntersectionObserver = MockIntersectionObserver;
g.ResizeObserver = MockResizeObserver;

// Radix (tabs, presence) calls `requestAnimationFrame` unqualified, so it has
// to exist on the NODE global scope too, not just on `window`.
g.requestAnimationFrame = w.requestAnimationFrame = (cb: FrameRequestCallback) =>
  setTimeout(cb, 16) as unknown as number;
g.cancelAnimationFrame = w.cancelAnimationFrame = (id: number) => clearTimeout(id);
w.scrollTo = () => {};
g.scrollTo = () => {};
(dom.window.Element.prototype as unknown as Record<string, unknown>).scrollIntoView = () => {};

export { dom };
