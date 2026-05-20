---
tags: [meta, index, sessions]
date: 2026-05-20
---

# Missing Session Journals — Index

72 vols don't have a dedicated `vol-NN.md` session journal. Their work IS captured elsewhere (concepts, memory, papers, umbrella pages) — this index points to where.

For an era-grouped overview, see [[TIMELINE]].

## Why these are missing

Three patterns:

1. **Era VI "invention sprint" (vols 63-104)** — work was synthesized into concepts and the rigidity-theorem paper. Per-vol journals were skipped in favor of concept-page-level documentation.
2. **Era X "long compute spree" (vols 130-149)** — multiple vols rolled into single sessions; some have prefixed names like `vol-129-close.md` or `vol-131.md` covering adjacent work.
3. **Single-vol gaps** in otherwise-covered eras (vol-43, 115, 154, 170, 176, 185) — closures or pivot vols where the work fits one concept or session-summary doc.

## Where to find the work for each missing vol

### Era IV→V boundary

| Vol | Work captured in |
|---:|---|
| 43 | `sessions/vol-43-reframing.md` (it exists, just not named `vol-43.md`) |

### Era VI "invention sprint" (63-104)

These vols invented or refined algorithms across the 8+ named approaches. Many produced concept pages directly.

| Vols | Theme | See |
|---|---|---|
| 63 | Temporal-Rewind-Search design | [[temporal-rewind-search]] |
| 64 | invention scaffolding | (rolled into vol-65) |
| 66 | ComponentClusterDestroy | [[component-quotient-destroy]] |
| 67 | Forced-Component-Departure ALNS design | [[forced-component-departure]] |
| 69 | Oracle-Attracted ALNS design | [[oracle-attracted-alns]] |
| 70 | Rigidity-Guided Search | [[rigidity-guided-search]] |
| 71-78 | basin-component analysis, piece-pair freq | [[component-rep-database]] + piece-pair concepts |
| 81-82 | McGavin top/bottom symmetry | [[mcgavin-basin-top-bottom-symmetry]], [[mcgavin-469-mismatch-geometry]] |
| 83-101 | LOCAL RIGIDITY THEOREM (multi-vol synthesis) | [[_umbrella-mcgavin-mip-proofs]], [[mip-local-optimality-459]], [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]] |
| 102-104 | (folded into the 83-101 paper) | [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]] |

### Era VII (115)

| Vol | Work captured in |
|---:|---|
| 115 | [[SYNTHESIS_VOLS_106-115_2026-05-16]] (covers entire era 106-115) |

### Era X "long compute spree" (130-149)

| Vols | Theme | See |
|---|---|---|
| 130 | FILAMENT result | [[filament-lk-2d]] |
| 132-145 | mixed inventions; many concept pages | grep `concepts/v13*.md` or `concepts/v14*.md`; also [[plans/archive/MULTI_VOL_PLAN_2026-05-19]] |
| 146 | close-out; session note exists as `vol-146-close.md` | [[vol-146-close]] |

### Era XI (154, 157-170)

| Vols | Theme | See |
|---|---|---|
| 154 | (close-out / sweep) | search `concepts/` for v154 |
| 157-168 | invention vols (multiple) | individual concept pages |
| 170 | filler / scratch | (no captured content) |

### Era XIII (176, 185)

| Vol | Work captured in |
|---:|---|
| 176 | (gap; minor work) |
| 185 | vault cleanup (no new search) — [[E2_KNOWN_FACTS]] mentions; see git log around 2026-05-20 |

## Adjacent prefixed sessions

These exist as `vol-NN-<theme>.md` instead of `vol-NN.md` — wikilink resolution still works by basename, but they're not in the strict `vol-NN.md` slot:

- `vol-32-457-record-tie.md`, `vol-32-458-NEW-RECORD.md`, `vol-32-WAKE-SUMMARY.md`, `vol-32-blackwood-mrv-discovery.md`, `vol-32-bug-discovery.md`
- `vol-34-OVERVIEW.md`, `vol-34-WAKE-SUMMARY.md`, `vol-34-basin-clustering.md`, `vol-34-landscape-1000.md`, `vol-34-landscape-pilot.md`, `vol-34-record-class-landscape.md`, `vol-34-t1-signal.md`
- `vol-35-457-basin-geometry.md`, `vol-35-T1-plan-detail.md`, `vol-35-WAKE-SUMMARY.md`, `vol-35-basin-family-count.md`, `vol-35-color-ratio.md`, `vol-35-deep458-lottery.md`, `vol-35-family255.md`, `vol-35-high-bound-recovery.md`, `vol-35-pin-hints-bug-retraction.md`, `vol-35-progress.md`, `vol-35-t1b-family-lottery.md`, `vol-35-throughput-clarification.md`
- `vol-36-vanilla-path-ab.md`, `vol-36-vanilla-path-prelim.md`
- `vol-37-pos161-discovery.md`, `vol-37-re-evaluation.md`
- `vol-43-reframing.md`
- `vol-50-pivot-trail.md`
- `vol-119-goal-prompt.md`
- `vol-123-close.md`, `vol-123-final.md`
- `vol-124-end-state.md`, `vol-124-portfolio-results.md`, `vol-124-roaming.md`, `vol-124-roaming-nonpuzzle.md`
- `vol-125-record-summary.md`
- `vol-129-close.md`
- `vol-134-partial.md`
- `vol-146-close.md`

These are the "real" vol-NN session content for those volumes, just under a slightly different filename.

## Decision rationale

Backfilling 72 stub session pages would create noise without adding signal — the work IS captured, just in the canonical concept/memory/paper structure. This index makes the routing explicit.

If a future agent or human asks "what happened in vol-N?":
1. Check `sessions/vol-N.md`. If exists, read it.
2. Else: check this index. Follow the link to the canonical location.
3. Else: `git log --all --oneline | grep "vol-N"` for commit-message-level mentions.

## Linked

- [[TIMELINE]] — era-grouped one-liners for all 188 vols.
- [[SYNTHESIS_VOL_188]] — current state of the project.
- [[../INDEX]] — vault navigation.
