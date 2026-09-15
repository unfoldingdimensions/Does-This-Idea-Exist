# IdeaExists Revamp Plan

## Product direction

Reframe IdeaExists from a binary startup directory into:

> **Find products that already exist, understand the closest alternatives, and decide what would be meaningfully different before you build.**

Keep “Does this startup exist?” as the memorable entry-point question and brand personality, but make the core output a research result—not a yes/no badge.

The primary audience is founders, indie hackers, product strategists, and investors researching a real product idea. The Curator remains an internal/operator role rather than the public product persona.

## The killer workflow

A first-time user should be able to complete this in under two minutes:

1. Enter a product name, URL, GitHub repository, or plain-English idea.
2. Receive results grouped into:
   - **Direct matches** — products doing essentially the same thing.
   - **Closest alternatives** — products solving the same problem differently.
   - **Related products** — adjacent tools worth studying.
3. See why each result matched.
4. Open a product dossier containing:
   - What it does.
   - Target user and problem.
   - Website, demo, docs, and GitHub links.
   - Activity and freshness signals.
   - Human review date.
   - Evidence sources.
   - Caveats and unknowns.
5. Select up to three products for comparison.
6. Answer: **What would be different about your version?**
7. Share or export the research.

The success event is not “the user clicked a card.” It is:

> **The user found a relevant existing product and understood how it relates to their idea.**

---

## Product truth model

The current `Verified` state should no longer carry multiple meanings. Track these evidence dimensions separately:

- **Website reachable** — the primary URL responded.
- **Product evidence found** — a product, demo, docs, or repository was found.
- **Repository active** — recent repository activity exists, where applicable.
- **Company identity confirmed** — the claimed product and company appear to correspond.
- **Human reviewed** — a curator inspected the available evidence.
- **Last checked** — when automated checks were most recently performed.
- **Status history** — how the product changed over time.

Retain the current archive states for compatibility, but change the public copy so “human reviewed” means only that the displayed evidence was inspected. It must not imply legitimacy, quality, funding, safety, customer traction, or investment value.

Add a prominent “How this archive works” explanation:

- **Unverified:** filed, awaiting review.
- **Reachable:** the URL responded; this is not an endorsement.
- **Dead:** repeated checks found the product unavailable.
- **Human reviewed:** a curator inspected the available evidence.
- **Unknown:** the archive does not have enough evidence to make a claim.

---

## Phase 1 — establish the product contract and baseline

Before adding new data or major features:

- Record current archive counts.
- Audit duplicate domains and repositories.
- Record category distribution.
- Record verified, unverified, and dead proportions.
- Measure data freshness.
- Inventory populated fields.
- Identify which values are sourced, inferred, or LLM-generated.
- Define the supported query types:
  - Product name.
  - Website URL.
  - GitHub URL.
  - Plain-English idea.
- Define the difference between a product, company, project, repository, and domain.
- Document that the first audience is founders doing competitive research, not general startup browsing.

Preserve the current local-first deployment and admin-token model while keeping the data model compatible with a future hosted read-only archive.

### Keep

- Local-first architecture.
- No accounts by default.
- Human review.
- Dead entries retained.
- Conservative link verification.
- Warm archive identity.
- Existing cards and admin tooling.
- Current seed data where it is accurate.

### Change

- Binary “exists” framing into research and alternatives.
- Generic `Verified` meaning into evidence-based signals.
- Stars as a primary ranking signal into secondary metadata.
- Modal-only details into canonical product dossiers.
- LLM-generated prose treated as fact into provenance-aware summaries.

### Defer

- Broad uncontrolled scraping.
- Accounts.
- Comments and community moderation.
- Votes and leaderboards.
- Funding-heavy metadata.
- AI-generated verdicts.
- Decorative work that does not improve research completion.

---

## Phase 2 — fix data integrity and search

### Duplicate and identity cleanup

The existing URL normalization is a good foundation, but it should be extended with:

- Canonical domain.
- Normalized GitHub owner/repository.
- Redirect destination tracking.
- Alias URLs.
- Duplicate candidates based on name, domain, repository, and description similarity.
- An admin duplicate-review queue.
- Conservative merge behavior that preserves:
  - The strongest verification state.
  - Historical review records.
  - Alternate URLs.
  - Source provenance.

Do not automatically merge ambiguous companies that merely share a name.

### Search quality

Search should classify and rank matches in this order:

1. Exact product name.
2. Exact domain.
3. Phrase or name match.
4. Tagline match.
5. Problem-description match.
6. Category or keyword match.
7. Fuzzy fallback.

Stars may be used only as a tiebreaker. An exact or strong textual match must never be buried beneath a popular but irrelevant repository.

Each result should eventually show a short explanation such as:

- “Exact name match.”
- “Matches your idea’s product category.”
- “Similar problem description.”
- “Same audience, different approach.”

Add regression tests for:

- Exact product names.
- Domains.
- Multi-word ideas.
- Synonyms.
- Unrelated fuzzy matches.
- Empty results.
- Duplicate records.

When the archive outgrows the current client-side search ceiling, move search to SQLite FTS5 or another server-side search implementation.

---

## Phase 3 — build the research-result experience

### Query types

Support these query modes:

- **Name:** `Obsidian`
- **URL:** `https://example.com`
- **GitHub repository**
- **Idea:** `A private team knowledge base that turns meetings into searchable decisions`

Initially, free-text ideas should use deterministic local search:

- Extract meaningful terms.
- Search names, taglines, descriptions, categories, and aliases.
- Rank exact and phrase matches strongly.
- Use category and keyword overlap.
- Avoid requiring an LLM for every search.

Semantic or LLM-backed search should be introduced only after deterministic search has been measured against real queries.

### Result sections

Replace one undifferentiated card grid with:

1. **Best matches**
2. **Closest alternatives**
3. **Related products**
4. **No strong match found**

The no-match state should remain useful:

> “No close match found. That does not mean the idea is new. Try broader terms, review related categories, or submit a product for the Curator to investigate.”

### Product dossier

Evolve the existing detail view into a research dossier containing:

- Product summary.
- Problem and target user.
- “Why this matched.”
- Evidence and source links.
- Website, product, docs, and GitHub actions.
- Activity signals.
- Human review date.
- Similar products and alternatives.
- Historical status.
- Explicit limitations and unknowns.
- A visible caveat: “This is research evidence, not an endorsement.”

Keep the modal for fast browsing, but add a stable canonical route such as:

```text
/products/obsidian
```

Stable routes are needed for sharing, bookmarking, future SEO, and a possible hosted archive.

---

## Phase 4 — add evidence and provenance

Add fields incrementally to the SQLite model:

- `entity_type`
- `canonical_domain`
- `aliases`
- `problem_statement`
- `target_users`
- `product_url`
- `docs_url`
- `demo_url`
- `pricing_model`
- `activity_checked_at`
- `activity_summary`
- `last_human_reviewed_at`
- `review_notes`

Prefer a separate evidence table over storing all claims in the startup row:

```text
evidence
- id
- startup_id
- evidence_type
- source_url
- captured_at
- claim
- value
- provenance
- confidence
- reviewed_at
```

Examples of evidence include:

- GitHub repository creation date.
- Latest commit or release date.
- Repository archived state.
- Homepage claims.
- Wayback first snapshot.
- Automated reachability result.
- Curator confirmation that a product can be accessed.

LLM-generated descriptions should be labeled as machine-drafted until a human confirms them. Generated prose must not be treated as ground truth without supporting evidence.

---

## Phase 5 — build comparison and decision support

Add a local-only comparison flow:

- Select up to three products.
- Compare:
  - Problem.
  - Audience.
  - Product type.
  - Category.
  - Core workflow.
  - Product availability.
  - Activity.
  - Review freshness.
  - Evidence quality.
- Store selections in localStorage.
- Export to Markdown, JSON, and CSV.

Add a “What would be different?” section with prompts around:

- Target customer.
- Distribution.
- Workflow.
- Business model.
- Technical approach.
- Geography.
- Privacy.
- Integrations.
- Narrower use case.

The product should help users continue after discovering that an idea already exists rather than simply discouraging them.

---

## Phase 6 — enrich data carefully

Do not begin with uncontrolled internet scraping. It creates stale data, duplicate entities, legal and terms-of-service risk, attribution problems, and long-term maintenance burden.

Use this source order:

1. Existing archive.
2. GitHub API and repository activity.
3. Existing website metadata and redirect checks.
4. Wayback metadata.
5. Curated URL lists.
6. Permitted public APIs or datasets.
7. Carefully selected scraping only where permitted and justified.

Every imported fact should record:

- Source URL.
- Capture date.
- Import method.
- Whether it was human-reviewed.
- Whether it is a fact, inference, or generated summary.

Build one source adapter at a time. Each adapter should support:

- Deduplication.
- Rate limits.
- Retry and backoff.
- Resumable jobs.
- Import reports.
- Provenance preservation.

Recommended first external sources:

- GitHub API for repository and activity metadata.
- Wayback metadata for historical existence.
- Public directories only when their terms permit reuse.
- Product Hunt or similar sources only through permitted APIs or data access.
- Curated URL lists for high-value categories.

Do not build a giant scraper before the product workflow has proven demand.

---

## Phase 7 — discoverability and retention

Once the research workflow is useful:

- Add indexable product pages.
- Add category pages.
- Add alternatives pages for high-quality records.
- Add example searches to the landing page.
- Add “recently added.”
- Add “recently verified.”
- Add “recently marked dead.”
- Add a change feed or RSS/JSON export.
- Add “request this product” to no-result states.
- Consider privacy-preserving usage measurement only if validation requires it.

The local-first model can remain the default while allowing a hosted read-only archive later.

Do not add accounts, comments, votes, leaderboards, or community moderation until the core research workflow demonstrates repeat usage.

---

## Validation plan

Test with 10–20 founders, indie hackers, product strategists, or investors using real ideas.

Measure:

- Whether they find a relevant product.
- Whether the first result is useful.
- Whether they understand why it matched.
- Whether they open evidence links.
- Whether they compare products.
- Whether they export or share the result.
- Whether they return for another idea.
- Whether they understand “verified” correctly.
- Whether they would use the tool again instead of Google.
- Whether they would contribute a missing product.

### Initial quality targets

- Exact product matches appear first.
- No duplicate identity has conflicting public statuses.
- At least 80% of test queries have a relevant result in the first three results.
- Every trust claim has visible evidence or explicitly says “unknown.”
- New users understand the trust model without personal explanation.
- A user completes search-to-dossier in under two minutes.
- Users research multiple ideas during the same session.

The strongest validation signal is repeated research, not compliments about the interface.

### Core funnel events

Track locally or through privacy-preserving measurement:

- Search started.
- Search produced a strong match.
- Result opened.
- Evidence link clicked.
- Comparison started.
- Export or share used.
- Missing product requested.
- Return within 7 days.
- Return within 30 days.

---

## Implementation order

1. Baseline data and product-contract document.
2. Duplicate and identity audit.
3. Search relevance regression suite.
4. Trust copy and archive explanation.
5. Research result sections.
6. Evidence and provenance schema.
7. Product dossier and stable URLs.
8. Comparison and export.
9. GitHub and Wayback activity enrichment.
10. One permitted external source adapter.
11. Founder usability testing.
12. Iteration based on failed searches and observed user behavior.

The first implementation slice should **not** be scraping or semantic AI search. It should be:

> **Audit the current data, remove identity conflicts, improve search explanations, and make the trust model precise.**

---

## Stop conditions

Pause feature expansion and reassess if:

- Users cannot find relevant results for real ideas.
- The archive cannot maintain evidence freshness.
- Human review backlog grows faster than it can be resolved.
- Users interpret the product as a guarantee or scam detector.
- No test users return for a second research session.
- Data acquisition creates more maintenance cost than user value.

The product should earn the right to become a larger public directory by proving that it helps people make better product decisions first.
