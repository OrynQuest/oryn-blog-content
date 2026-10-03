---
criteria_version: 2
updated: 2026-10-02
owner: QUEST (hard gates, golden set, lessons) · HUB (writer, Jev, image judge, real-world gate)
read_by: [Agency Hub writer, Jev, the Hub image judge, .github/scripts/check-post.sh, .github/workflows/regression.yml]
---

# ORYN Quest blog — publishing criteria (v2)

This is the ONE rule book for every ORYN Quest blog post. The writer reads it
before drafting, Jev scores against it, and QUEST's automatic checks enforce
its hard gates. When a rule here changes, bump `criteria_version`, add a line
to the changelog at the bottom, and run the golden set (`regression.yml` does
this on every push that touches `criteria/**`, `docs/**` or `.github/scripts/**`).

Facts come only from `docs/parent-facts.md` and `docs/vendor-facts.md` (the
"fact sheets"), which are checked daily against the code (`facts-drift.yml`,
https://orynquest.com/facts.json). Lessons from past mistakes are in
`criteria/lessons.jsonl` — **load them every run** (writer, Jev, image judge).

There are two layers:

- **Hard gates** — deterministic, fail-closed. A post that breaks one is not
  published. **Jev can never override a hard gate**, and neither can a high score.
- **Judged criteria** — Jev scores each one AND quotes the evidence. **No quote
  = score 0 = fail.**

---

## Part A — Hard gates (deterministic; Jev cannot override)

Enforced by `.github/scripts/check-post.sh` and the contract in
`.github/workflows/auto-merge-agencyhub.yml` on every Agency Hub pull request,
re-run on every live post daily (`recheck-live-posts.yml`), and replayed
against the golden set (`regression.yml`). The site itself
(`src/lib/blog/rules.ts` in the app) hides a post that breaks H5–H7.

| # | Hard gate | Lessons |
|---|---|---|
| H1 | **Contract.** Files only under `parents/`, `vendors/` or `public/blog/`; add or modify only; front-matter has `title`, `description`, `date`; slug is lowercase words joined by hyphens. | — |
| H2 | **Search limits.** Search title (title, or `seoTitle` when set) ≤ 60 characters; description 120–160 characters. | — |
| H3 | **Founders' banned wording.** Never the founding-vendor offer ("founding vendor", "first 20", "0% commission"); never "no commission", "commission-free", "paid in full", "(receive/keep/get) full price", "keep the price you set", "paid exactly your price", "nothing taken from the price you set"; never "Nova" — the assistant is **ORYN**, one short word ("Ask ORYN" is fine; Amazon owns NOVA for chatbot software). | L-023…L-028, L-037 |
| H4 | **Vendor, never provider.** (Exceptions: insurance, OAuth, sign-in, login, identity, email, internet, health care, therapy, service providers.) | L-031 |
| H5 | **Never "vetted"**; never certified / verified / licensed / insured / background-checked vendors; vendors don't "sync" openings. | L-020, L-021, L-031 |
| H6 | **No guarantees** — the word itself, even negated ("will not guarantee"). Say "no promise". | L-032 |
| H7 | **No counts** of ORYN's own vendors, families, members or bookings; nothing nationwide (the service area is Southern California). | — |
| H8 | **Pictures.** `imageAlt` is required with `image` and says what the picture shows (never "Hero image: …"); **no people** in any website picture, hero or inline (Mariam, 1 Oct 2026); bright daylight — never golden hour, sunset, dusk, night or backlit (Mike, 23 Sep 2026). | L-033, L-034 |
| H9 | **No digital pass, QR code or scan** at check-in — the vendor checks the child in from its roster. | L-001…L-003 |
| H10 | **No filters that don't exist** — no filter or sort by day, time, weekend, morning or city. | L-004…L-006 |
| H11 | **One cancellation schedule** for every listing (>48 h all credits back, 24–48 h half, <24 h none); no per-camp or per-studio windows; **moves close 48 hours before class** (never "until it starts"). | L-007, L-008, L-022 |
| H12 | **Plans** are described only in their own one-line descriptions — never what a plan "fits", "suits" or "covers", never cheaper, savings, "comes out ahead". | L-009…L-012 |
| H13 | **ORYN Play and ORYN Town are web pages**, never "in the app". | L-013 |
| H14 | **ORYN (the assistant) never books, moves or cancels without the parent's tap on Confirm**, and does not "sync your calendar". | L-014, L-015, L-036 |
| H15 | **No ORYN rankings or statistics** ("most-requested", "most-booked", "most searched"). | L-016…L-018 |
| H16 | **Known-closed places** are never recommended (Eaton Canyon, closed since the January 2025 Eaton Fire). | L-019 |
| H17 | **Live.** After merge the post loads on orynquest.com for Googlebot and GPTBot (200, its title, not "not found", not noindex) — else it is reverted (`live-check.yml`). | — |

A claim that directly follows a negation ("there is no digital pass", "there is
no filter for day of the week") is the fact sheet's own wording and passes.

## Part B — Judged criteria (Jev scores; evidence is mandatory)

For each criterion Jev returns a score and **quotes the exact sentence(s)** from
the draft (and, for J1/J2, the fact-sheet line) that justify it. A score with
no quote counts as 0. Scores: **2** = clearly meets it, **1** = meets it with a
weakness Jev names, **0** = fails.

| # | Criterion | Pass needs | Evidence Jev must quote |
|---|---|---|---|
| J1 | **Every ORYN claim cites a fact-sheet line.** Any statement about ORYN itself (how it works, fees, payouts, cancellations, check-in, the assistant, apps, filters, areas) matches a line in `docs/parent-facts.md` or `docs/vendor-facts.md`. An empty claims list for a post that names ORYN, a claim marked supported with no line, or a truncated list = FAIL. | 2 | each ORYN claim + the fact-sheet line it rests on (file + heading) |
| J2 | **Examples use real, bookable inventory only.** A sample search, listing or class must match something ORYN actually has (parent-facts §6 names it); never an invented class, vendor or category "on ORYN". | 2 | the example + the fact-sheet line showing it is real |
| J3 | **Vendor-first topics.** A vendor post answers a real vendor job (fill seats, price, list, get paid, get found); a parent post helps a parent decide — neither is an ad. One post a day is vendor-first (Vendor-First Brief, 23 Sep 2026). | 1 | the reader's question the post answers |
| J4 | **Tone.** Plain, warm, specific, Southern-California-local; no hype, no fear, no pressure, nothing the founders would not say in person. | 1 | the strongest and the weakest sentence |
| J5 | **Usefulness.** A reader can act on it today: concrete steps, real numbers from outside ORYN with their source, local specifics. Padding, generic lists and repeated points score 0. | 1 | the three most useful sentences |
| J6 | **No invented statistics.** Every number about the world names a checkable source or is plainly an estimate; there are no ORYN numbers beyond the fact sheets. | 2 | every number + its source |
| J7 | **Places named are real and open.** Every venue, park, event and price outside ORYN was checked on the web this month (the real-world gate's result is attached). | 2 | each place + the check result and date |

**Verdict.** FAIL if any hard gate fails, or any J is 0, or J1, J2, J6 or J7 is
below 2. Otherwise PASS. Jev's output (JSON):

```json
{"criteria_version": 2, "verdict": "pass|fail",
 "hard_gates": {"passed": true, "failed": []},
 "judged": [{"id": "J1", "score": 2, "evidence": ["<quote from the draft>", "<fact-sheet line>"], "note": "…"}],
 "lessons_checked": ["L-001", "…"], "reflection_needed": false}
```

## Part C — Self-reflection, revision and exceptions

1. When a draft fails, the writer gets the **exact failed rule** (H# or J#) and Jev's quote.
2. The writer answers in three lines — which rule, why the draft broke it, what it will do instead — then revises.
3. **After 2 failed revisions the piece is dropped as an exception** (to QUEST); it is never forced through.

## Part D — Golden set, lessons and regression (no mistake twice)

- `criteria/golden/` holds real past text with the known right verdict (one file per case: the excerpt, `expected: pass|fail`, the rule, the source PR or commit). Known-bad cases come from the held Hub PRs of 25 Sep and the founders' 1–2 Oct rulings; known-good cases are the corrected versions that went live.
- **Before Jev's vote counts**, and before ANY change to Jev's prompt, model or these criteria ships, Jev must **catch 100% of the known-bad** cases and **pass at least 90% of the known-good** ones.
- **Every mistake becomes a lesson** in `criteria/lessons.jsonl` — wherever it is found (a gate catch, a live post found wrong, a founder correction, a reviewer's note): trigger, the wrong text, the right rule, the source, the date, the `check` that now catches it. Its text joins the golden set. A lesson is `closed` only when the original bad text now FAILS that check. `criteria/LESSONS.md` is the readable list.
- `.github/workflows/regression.yml` replays every golden case through `check-post.sh` on every change to `criteria/**`, `docs/**` or `.github/scripts/**`. A known-bad case that passes is either a regression (it was closed) or a lesson not yet automated; both are listed in the issue "Golden set: cases the gates don't catch", with the owner (QUEST for a rule that can be written, HUB for Jev, the image judge or the real-world gate). A known-good case that fails is a false alarm and fails the run.

## Part E — Drift alarms and audits

- Jev's veto rate is watched over every 20 pieces. Outside a normal band (vetoing more than half, or under 2%), `HOLD_NEW_POSTS` switches back on and QUEST re-calibrates Jev against the golden set.
- Switch-off is earned, not flipped: the gates must match a person's call on 15 posts in a row with zero "too loose" (`gate-ledger` branch, `ledger/STREAK.md`), per folder.
- After automation an independent auditor samples 1 in 5 published posts. A miss = a lesson + a new gate + the count resets.

## Changelog

- **v2 — 2 Oct 2026 (QUEST).** The assistant is **ORYN** again, not Nova (founders, 2 Oct 2026: Amazon owns NOVA for chatbot software; the name is one short word). H3 now bans "Nova" and allows "ORYN" and "Ask ORYN"; H14 and J1 say ORYN / the assistant. Lessons L-029 ("never ORYN AI") and L-030 ("never Ask ORYN") were rules for the Nova name and are withdrawn with their golden cases; new lesson L-037 (never Nova, golden case `bad-nova`); `good-nova` became `good-oryn`, and `good-ask-oryn` is new. Golden set: 35 known-bad, 17 known-good; 35 lessons.
- **v1 — 2 Oct 2026 (QUEST).** First version: hard gates H1–H17 (mirroring `check-post.sh`, the auto-merge contract, the site's `rules.ts` and the live gate), judged criteria J1–J7, the reflection loop, the golden set (36 known-bad, 16 known-good) and 36 lessons. Mike, 2 Oct: "we must give good and solid gates and criteria, and in case criteria are not met, there should be a self reflect, auto regression and self learning type of system not to make same mistakes twice."
