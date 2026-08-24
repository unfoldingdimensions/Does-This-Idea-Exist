
## 2026-08-24 - Explicit noopener in external links
**Vulnerability:** External links using `target="_blank"` without explicit `noopener`. Although modern browsers implicitly add `noopener` for `target="_blank"`, explicitly setting it ensures cross-browser protection against reverse tabnabbing (where a newly opened tab can manipulate the original window's location).
**Learning:** The codebase relied on `rel="noreferrer"` without explicit `noopener` for external links. While functionally mitigating the risk in most modern clients, explicit declaration is the established security standard.
**Prevention:** Always use `rel="noopener noreferrer"` when using `target="_blank"` for external links.
