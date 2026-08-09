# Adversarial UX Test — "Big Ray" Kowalski vs IdeaExists

**Persona:** Ray "Big Ray" Kowalski, 55. Retired supply-chain exec, informal angel investor. Email + WhatsApp only; his "spreadsheet" is a paper notebook; his wife set up his laptop. Buying into the idea that AI is mostly hype and scams. Reads the news on Facebook.
**His ONE task:** *"My nephew wants me to put money into some startup. Is it real or is it a scam?"* — search it, read the entry, trust the verification, click through to the website.
**Give-up triggers:** jargon, small text, unclear trust signals, more than a few clicks, anything that feels like a con.
**Session:** 2026-08-10, live app at http://localhost:3023 (49 entries, 20 verified).

---

## Step 3 — The Rant (in character)

### Big Ray's Review of "IdeaExists"

**Overall: Maybe. With conditions. I'd use it the way I use Google — but I wouldn't trust it the way it wants me to.**

**THE GOOD (grudging admission):**
- That first line — "A human-kept archive of what exists." — okay, I get it. It's a filing cabinet. I respect a filing cabinet.
- I typed "obsidian" (the thing my nephew's friend builds plugins for) and it found Obsidian. Found it. Eventually.
- The green "Verified" pill with the date it was checked — THAT I understand. Someone looked at it. Like a building inspection. Good.
- No accounts, no "sign up for our newsletter," no cookies nagging. I hate that stuff. It just... works. Rare these days.
- The little note at the bottom — "Dead is a status, not an erasure." Somebody with a personality runs this place. I like that.

**THE BAD (legitimate UX issues):**
- I searched "obsidian" and the FIRST thing it showed me was "Hugging Face Transformers" with 163,000 stars. I don't know what a Hugging Face is and I'm pretty sure it's not Obsidian. Then Obsidian. Then some company called "Avoca" — I've never heard of Avoca, my nephew hasn't heard of Avoca, Avoca has nothing to do with Obsidian. Why are you showing me Avoca?? It's like asking for a plumber and the yellow pages gives you a dentist, a plumber, and a tax accountant. Sorted by how many phone numbers they have.
- I searched "zoom" — everybody knows Zoom — and the page showed me **TWO Zooms side by side**. One says "Verified" in green. The other says "Unverified" in grey. SAME company! SAME description! SAME year! Which one is real, genius? If I can't trust the filing cabinet to have one card per company, I'm not trusting it with my nephew's money.
- Half the cards in this place are grey "Unverified." What does that even mean — nobody checked? Then why is it in the archive? If the whole point is "is this real," and most of the answer is "grey, nobody looked," you've built a shelf of unread files.
- I tried to add a company my nephew's friend started. Clicked "Add startup," it asked me for a website. I didn't have the website handy, so I clicked the big button and... nothing. The button is greyed out like it's asleep. No "you need to type something, dummy." Just nothing. I sat there clicking it three times like an idiot.
- There's a "Details" button on every card AND you can click the name AND there's "Show more" — three different ways to open the same file? Pick one.

**THE UGLY (showstoppers):**
- I hit a page that didn't exist and got a blank-ish page that just said "This page could not be found." No way back. No "go home." If my nephew's friend sends me a broken link to this thing, I'm just gone.
- "Stars." "Founded." "Last checked." You people type in spreadsheet-speak. I don't care about GitHub stars. I care about: is it real, is it still alive, and do they have a website I can call.

**SPECIFIC COMPLAINTS:**
1. **Search:** "obsidian" → Hugging Face Transformers first. "What is wrong with you?" — expected the actual Obsidian first.
2. **Duplicates:** "zoom" → two Zooms, one Verified one Unverified. "Which one do I trust?!" — expected one card per company.
3. **Add form:** empty submit → dead button, no message. "Am I doing it wrong or is this thing broken?" — expected to be told what to do.
4. **404:** dead end, no way home. "Great, now where am I."
5. **Jargon:** "stars," "unverified," "founded" — "speak English, I'm deciding whether to lose money here."

**VERDICT:** "It's a nice little filing cabinet, but half the files are blank, some companies are filed twice with different stamps on 'em, and it keeps showing me the wrong file first. I'd use it — but I'd still call the company myself before I handed over a dime."

---

## Step 4 — The Pragmatism Filter

| # | Complaint | Filter | Verdict |
|---|-----------|--------|---------|
| 1 | Search shows irrelevant results above the exact match | Any busy 35-year-old hits this on the first query | **RED** — search relevance is the core flow |
| 2 | Duplicate Zoom/Pogo with contradictory verification | Anyone comparing entries sees it; trust product = trust data | **RED** |
| 3 | Add form: silent disabled button, no URL validation | Any user, not just Ray; also a form-quality standard | **RED** |
| 4 | Unverified majority = "shelf of unread files" | Partly by design (human gate), but signals a **missing onboarding moment** — no legend explaining what Verified/Unverified mean, no "how this archive is kept" explainer | **GREEN** (feature) + YELLOW (copy) |
| 5 | 404 dead end | Rare on a one-pager, but a genuine dead end | **YELLOW** |
| 6 | Three ways to open details (name / Details / Show more) | "Show more" ≠ "Details" — but the affordance clash is real for everyone | **YELLOW** |
| 7 | Jargon: stars, founded, unverified | "Stars" is arguably jargon; the pills need words, not just colors (already has worded tooltips) | **WHITE** (already mitigated by tooltips; low priority) |
| 8 | "Why is it in the archive if unverified?" | Curator voice exists; needs the legend | **GREEN** (with #4) |
| 9 | Two Zooms "same company, different stamp" — trust | Covered by #2 | — |
| 10 | Small text, spreadsheet-speak | Contrast/geometry measured fine; font scale is a deliberate minimalism choice | **WHITE** |

**RED items:** 3 · **GREEN:** 1 · **YELLOW:** 2 · **WHITE:** 2

---

## Step 5 — Tickets

> Max 10 tickets; RED + GREEN only. YELLOWs in one catch-all below.

### T-1 [RED] Search ranks irrelevant fuzzy matches above the exact-name match
- **Persona quote:** "I asked for a plumber and the yellow pages gave me a dentist, a plumber, and a tax accountant — sorted by how many phone numbers they have."
- **Real issue:** Fuse.js `threshold: 0.4` + `ignoreLocation` produces false positives ("obsidian" → Hugging Face Transformers, Avoca, Zoom — zero shared text), and results are then re-sorted by stars, burying the exact match at #2.
- **Fix:** Tighten threshold (~0.3, location-aware); when a query is present, rank by Fuse relevance score first, stars only as tiebreak. (dogfood Issue #1)
- **Label:** `ux-review` `p0`

### T-2 [RED] Duplicate company entries with contradictory verification
- **Persona quote:** "SAME company, SAME description, one says Verified, one says Unverified. Which one is real, genius?"
- **Real issue:** Pogo ×2, Zoom ×2 in the archive (49 rows / 47 unique). A directory built to disambiguate shows the same company twice with opposite trust verdicts.
- **Fix:** Dedupe on seed (normalize website/GitHub URLs before upsert); one-off merge pass for existing dupes; consider a "merge duplicates" admin action. (dogfood Issue #2)
- **Label:** `ux-review` `p0`

### T-3 [RED] Add-startup form is silently dead on empty submit; accepts garbage URLs
- **Persona quote:** "I clicked the big button three times like an idiot."
- **Real issue:** Submit disabled with no message on empty; `banana` enables it (no URL-format check) — failure deferred to a backend toast.
- **Fix:** Inline helper text under the field ("Enter a website URL to continue"), format validation before enabling submit, red error state on invalid input. (dogfood Issue #4)
- **Label:** `ux-review`

### T-4 [GREEN] Trust legend / "how this archive is kept" explainer
- **Persona quote:** "Half the files are blank... what does grey even mean?"
- **Real issue:** Verified/Unverified pills have worded tooltips, but nothing on the first screen explains the trust model — a cold-start user sees a majority-grey grid and reads it as "unfinished," not "human-gated."
- **Fix:** One-line legend under the hero ("🟢 a human checked it · ⚪ filed, awaiting a human check") or a tooltip on the archive-stat line; expand the curator voice already in the footer. (dogfood Issue #4 context)
- **Label:** `ux-review` `feature`

### T-5 [YELLOW — catch-all]
- **404 dead end** (no way home) — add themed `not-found.tsx`. (dogfood Issue #5)
- **Affordance clash:** card name / "Details" / "Show more" all expand — consider demoting "Show more" to an inline description toggle only. (dogfood Issue #1 context)
- **Grid row-height variance** 293 vs 311px — clamp taglines to 2 lines for uniform rhythm. (dogfood Issue #6)

### WHITE (report only, no tickets)
- "Speak English" (jargon) — mitigated by worded tooltips; fine.
- "I want paper" resistance — product is digital by nature; fine.

---

## Step 6 — Key Evidence

| Screenshot | Shows |
|---|---|
| `search-obsidian-relevance.png` | T-1: irrelevant results ranked above the exact match |
| `dup-zoom-search.png` | T-2: two Zoom cards, Verified vs Unverified |
| `home-initial.png` / `home-dark.png` | Overall polish both themes (the parts Ray grudgingly liked) |

**Tested:** full core loop (search → detail → verify → add), filters, pagination, admin gate, both themes, console.
**Not tested:** "Run verification" batch (side-effectful), seeded adds (LLM), dead-entry visuals (0 in DB).
**Tool caveat:** the automation browser strips multi-param URLs and misclicks on animated layouts — three suspected bugs were traced to the tool, not the app.
