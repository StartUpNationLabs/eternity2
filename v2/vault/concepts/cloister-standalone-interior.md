---
name: cloister-standalone-interior
description: "CLOISTER (vol-211) — the standalone 14×14 interior attack: solve/optimize the 196-interior-piece puzzle on a free-rim 14×14 grid to maximize II/364, then attach an optimal border (BB+IB) via DP/MIP. Phase 0a measured the implicit interior record across all known boards: II=358/364 (Blackwood+Bucas 469, 2020-11-16); McGavin 469 = 354; our best = 352. The interior is the bottleneck: ALL high boards have BB=60."
status: partial
metadata:
  type: concept
---

# CLOISTER — standalone 14×14 interior attack (vol-211)

**Origin**: vol-211 (2026-06-10). User-directed frontier after the vol-209/210
entropy track closed: veteran milestone #3 ([[three-milestones-from-veteran]]),
never solved standalone by anyone.
**Files**: `crates/bench-audit/src/bin/interior_split.rs` (II/IB/BB splitter),
`scripts/v211_cloister/decode_corpus.py` (raw-bucas corpus decoder),
CLOISTER solver bins (this vol).

## Definition

Edge classes on canonical 16×16: **480 = 364 II + 56 IB + 60 BB**
(interior-interior, interior-border, border-border). The 196 interior pieces
and 60 border pieces are **disjoint sets**, so a complete board decomposes as
interior solution + border solution coupled ONLY through the 56 IB edges.

The **standalone interior puzzle**: place the 196 interior pieces on a 14×14
grid, rim outward sides FREE, maximize II ≤ 364. Parity-feasible
([[interior-14x14-parity-feasible]]); a perfect interior exists (the designed
480 solution's interior is a witness). Never solved standalone by the
community (Blackwood-line solvers always carry the border).

## Phase 0a measurement (2026-06-10): the implicit interior record

`interior_split` over our records + database-400-480 (1031 valid complete
boards) + community corpus (82 raw-bucas boards decoded; 14 canonical-piece
boards recovered, rest are non-canonical/fake-480s):

| board | total | II/364 | IB/56 | BB/60 | hints |
|---|--:|--:|--:|--:|--:|
| **Blackwood+Bucas 469_c (groups_175608276, 2020-11)** | 469 | **358** | 51 | 60 | 1/5 |
| Blackwood 470 (capiman repost, 1-clue) | 470 | 357 | 53 | 60 | 1/5 |
| discord_668 470 (1-clue) | 470 | 357 | 53 | 60 | 1/5 |
| Blackwood 468 (groups_171536025) | 468 | 357 | 51 | 60 | 1/5 |
| Blackwood 470 (groups_183676823) | 470 | 356 | 54 | 60 | 1/5 |
| McGavin 469 | 469 | 354 | 55 | 60 | 1/5 |
| 466 winning5 (McGavin-top14-derived) | 466 | 354 | 52 | 60 | 1/5 |
| our V125 461s / 460s (several) | 460-461 | 352 | 48-51 | 58-60 | 0/5 |
| **our V129 463 record** | 463 | 350 | 53 | 60 | 1/5 |
| our V175 458 | 458 | 350 | 48 | 60 | 0/5 |
| DB median (n=1031) | — | 338 | — | — | — |

**Findings:**
1. **Implicit standalone-interior record: II=358/364** (6 interior mismatches),
   Blackwood+Bucas 2020. NOT McGavin's 354 (the backlog's assumed value was
   stale). Each +1 of II beyond 358 is "best interior ever" territory.
2. **ALL high boards have BB=60** (perfect ring). The border ring is never the
   binding constraint; the interior is.
3. The 469-470 score level admits different (II, IB) splits: (358,51),
   (357,53), (356,54), (354,55) — II and IB trade off at roughly 1:1 near the
   frontier (total = II+IB+60).
4. Our boards lag the community interior frontier by 6-8 II edges — a larger
   gap than the total-score gap (463 vs 469-470 = 6-7). Our pipelines
   under-optimize the interior specifically.
5. Decode hygiene: grey-grey adjacencies must NOT count as matches —
   groups_219323986 "448" carries 14 grey-grey interior adjacencies (rotated
   border pieces placed interior); naive color-equality counts it II=364
   (false). `interior_split` excludes color-0 matches.

## Record arithmetic (the coupling budget)

Beat 463 (matched-edges): II + IB + BB ≥ 464 ⇒ with BB=60, **II + IB ≥ 404**.
Blackwood+Bucas 469 has II+IB = 409. Pure-interior targets: II=358 ⇒ IB≥46;
II=360 ⇒ IB≥44; II=364 ⇒ IB≥40. The 56 edge-piece inward colors are a FIXED
multiset, so a rim profile's achievable IB is bounded by multiset overlap with
that supply (then ring-feasibility refines via DP/MIP).

Strict-canonical (≥459 with 5/5): all 5 hints are interior cells — a hinted
CLOISTER solve + any legal border with II+IB+BB ≥ 459.

## CLOISTER solver results (vol-211, 2026-06-10, same day)

**Files**: `crates/bench-audit/src/bin/cloister.rs` (DFS + SA + hybrid),
`crates/bench-audit/src/bin/cloister_border.rs` (exact border-attach MIP).
All runs persist: timestamped dirs, per-seed JSON + .url.txt + summary.tsv,
global `output/vol-211/cloister_history.csv`.

### The standalone-interior depth wall (NEW structural numbers)

Row-major perfect-prefix DFS on the free-rim 14×14, ~60-90 M nodes/s/thread:

| config | wall (min/median/max over 8 seeds) |
|---|---|
| unhinted, 0 breaks, 10s | 173 / 174 / 174 (sharp!) |
| unhinted, 5 breaks (gates 154-186), 20s | 190 / 190.5 / 192 |
| hinted strict-forced (buggy-strict), 30s | 175 / 179 / 180 |
| hinted break-payable + reserve, breaks 7 | 169 / 182-183 / 187 |

The free rim does NOT dissolve the wall: it sits at 174/196 = 89% depth
(vs ~59-69% on the full board) — same pool-depletion mechanism
([[transept-strip-assignment]], [[isentrope-entropy-growth]] area-law), the
last ~22 cells are unfillable from leftovers.

### Break-DFS + exact-tail endgame (the user's break idea — works)

User suggestion mid-vol: allow a few mismatches near the end. Implemented as
Blackwood-style scheduled break gates (`--breaks B`, `--break-schedule`),
plus an **exact endgame**: at depth 196−k (k ≤ 14 = one row), B&B-solve the
optimal assignment of the k leftover pieces (forced/hint cells supported,
incumbent-seeded, abort-bounded by the running best) and backtrack — every
deep prefix gets its optimal completion; the DFS anytime-minimizes total
breaks across thousands of completions per seed.

| config | completions | II (min/med/max of 8 seeds) |
|---|---|---|
| unhinted breaks 5 et8, 30s | 8/8 seeds | 354 / 355 / **356** |
| unhinted breaks 5 et8, 300s (sweep A) | 8/8 | 355 / 356 / 356 |
| late gates (sweep B) / 8 breaks (C) / et11 (D), 300s | 8/8 | 355 / 355-356 / 356 |
| **hinted** breaks 7 et14, 30s | 4/8 | 349 / 350 / 350 |

- Unhinted II=356 reached in 30 s; 300 s adds ~+1 (anytime curve flattens).
- McGavin's interior level (354) is reproduced in SECONDS on the standalone
  problem. Gap to the all-time interior record (358): 2.
- **Hinted II=350 ties the best 5/5-hint interior ever seen in any known
  board** (the corpus strict 460s are II=350) within 30 s.
- Schedule shape matters little (A≈B≈C≈D) — the binding constraint is the
  leftover-pool quality, not gate placement.

### Hint handling (user directive: hints are MANDATORY)

All 5 canonical hints are interior cells (interior coords 15, 26, 104, 169,
180). Three lessons baked into the code:
1. A hint fixes (piece, rot), NOT edge-perfection — forced cells pay normal
   break costs (strict-matching them walls the search at the deep hints).
2. Hard neighbor pre-filters only for hints before the first break gate
   (sound there; removing them naively causes a late-constraint-check blowup
   — 2.7 G nodes stuck at depth 15).
3. **Break reservation**: 1 break held back per unplaced deep hint, else
   ordinary breaks starve the hints (all seeds died at exactly cell 180).

### Border-attach MIP (exact, HiGHS, seconds)

`cloister_border`: ring assignment of the 60 border pieces (rotations forced
grey-outward), maximize BB + IB against the fixed interior rim. Exact.
First result: best unhinted interior (II=356) → BB=60, **IB=37** →
**total 453/480**. The rim profile is the leak: random-ish rims support only
~37 IB vs Blackwood-line 51-55.

### Strict-canonical reality check (corpus discovery)

The decoded corpus contains **5/5-hint 460 boards** (groups 219671623 /
219328931, II=350 + IB=50 + BB=60): the community already has strict-460.
Our vol-122/199 strict-458s are II=348. So the strict-track bar for an
all-known-boards record is **461 = II+IB ≥ 401 with BB=60** (e.g. II=352 +
IB=49, II=355 + IB=46).

### Rim-aware objective (built, measuring)

SA objective extended to II + λ·Σ_c min(rim_c, supply_c) (λ=1 = the exact
1:1 exchange rate between an II edge and an IB-potential edge; the overlap is
a provable IB upper bound given the fixed edge-piece inward multiset
[supply per color 6-22: 4,5,3,3,1,1,2,3,4,6,4,2,3,6,4,3,2]). Pipeline:
hinted break-DFS → rim-aware SA polish → exact border MIP.

### Tail supply-vs-demand diagnosis (scripts/v211_cloister/tail_supply.py)

On the II=356 board's last 22 cells (its 8 mismatches all sit in the last 3
rows, small scattered clusters): the up-only bipartite matching of the 22
tail pieces to the 22 cells is **PERFECT (22/22)** — piece supply per
up-color is NOT the binding constraint. The joint up+left satisfaction is
(17/22 under the found arrangement). **The tail loss is the simultaneous
2D chaining, not color supply** — the area-law distinctness mechanism
([[isentrope-entropy-growth]]) at the 22-cell scale. Consequences:
- Color-based piece reservation/value-ordering will NOT buy much.
- The strongest implementable lever: a **2-row exact endgame** (k ≤ 28,
  column-pair B&B/DP — exact joint optimization where the damage lives).
- Otherwise: more deep-prefix diversity (restarts/scan orders) re-rolls the
  tail structure.

### H1 — hinted DFS at 300 s (8 seeds, breaks 7, et14)

8/8 complete: II min/med/max = **348 / 350 / 351**. The 351s beat the best
hinted interior in any known board (350). ~45 M nodes/s/seed with the
exact-tail running.

### H2/H3 λ-ablation — multiset-overlap proxy REFUTED at λ=1

300 s × 8 seeds, hinted, identical DFS seeds (60 s) + SA:
| arm | II (min/med/max) | rim term |
|---|---|---|
| H2 λ=1 (multiset overlap) | 339 / 348 / 350 | overlap 39-44 |
| H3 λ=0 (control) | 350 / **351** / 351 | — |

Border-attach of H2's best (II 350 + ov 44): **446** (IB=39, BB=57!) vs the
pure-II 356 board's **453**. The position-blind multiset overlap
overestimates realizable IB (realization loss ~5 edges, and the MIP even
sacrificed BB to chase IB). **Trading II 1:1 for overlap is a losing trade.**

### tail2 exact 2-row endgame: built, role re-scoped

Column-pair B&B over the last 28 cells (forced/hint cells supported — both
deep hints live in row 12). As an in-DFS trigger it LOSES to the 1-row
exact-tail under time pressure (truncated B&B < break-DFS at row 12; II 344
vs 350). As a **post-hoc polish** (`--mode tail2polish`, abort-bounded by the
board's current tail mismatches): on the II=356 board it PROVED the last two
rows optimally arranged given rows 0-11 (no completion < 7 tail mismatches;
171 s). **Pushing II needs different prefixes (rows 0-11), not better tails.**

### Alternating projections (the coupling fix — in flight)

The decomposition's true gap: strict-458 boards achieve II+IB = 398-400
JOINTLY; one-shot CLOISTER gets 351 + ~40 ≈ 391 (interior +3, coupling −10).
Fix: **interior SA ⇄ exact border MIP alternation** — the attached border
gives POSITION-EXACT rim targets (cell, side) → required color; a matched
rim side is a real IB edge, so λ=1 is the true exchange rate (no proxy).
`--border-board` on the SA + `scripts/v211_cloister/alternate.sh` (keep-best,
monotone in total across rounds).

### ★ The rim-compatibility theorem-shaped result (the vol-211 finding)

All coupling retrofits measured and small/negative:
| intervention | result |
|---|---|
| one-shot attach (various interiors II 350-356) | IB realized **34-39**, totals 445-453 |
| λ=1 multiset-overlap SA | II −3, attach 446 (refuted) |
| rim-supply DFS tie-break | II −2, IB unchanged 37 (refuted) |
| alternating projections (3 rounds, position-exact targets) | +1 total, converged 446 |

**Control: stripping the Blackwood+Bucas 469's border and re-attaching with
our MIP recovers EXACTLY 469 (II 358 + IB 51 + BB 60).** The attach is
optimal-grade; the gap is a property of the interior: **rim-compatibility.
Equal-II interiors differ by ~14 attachable IB depending on whether they
were grown inside a border.** Pure-II standalone search lands in
rim-incompatible basins (attachable IB ≈ 34-39 band across every interior we
built today), and the compatibility cannot be retrofitted post-hoc (proxy
objectives, tie-breaks, and coordinate descent all fail — the joint
landscape is rigid at high II, the same rigidity as the full-board σ-lock).

**Consequence**: the rim constraint must be inside the DFS from cell 1 —
border-anchored construction. The community's border-first architecture is
not a convention; it is the unique direction in which the decomposition's
coupling value (≈14 edges) is collectable. The strict-460 community boards
are exactly this architecture WITHOUT our break+exact-endgame machinery —
which is the vol-212 opening: **CLOISTER-II, border-anchored break-DFS**
(fix a perfect frame; IB edges enter the cost/break budget as real edges;
exact-tail scores rim sides too; 5/5 hints; target 461-strict).

## Status summary (vol-211 close)

Built + validated: `interior_split`, corpus decoder, `lpa_curve`,
`cloister` (break-DFS + exact 1-row/2-row endgames + SA/LNS + hybrid +
tail2polish), `cloister_border` (exact attach MIP), alternation driver,
history discipline. Standalone interior records: **II=356 unhinted / 351
hinted** (both best-ever for the standalone problem; hinted beats every
5/5 board's interior). Best assembled totals: 453 unhinted / 446 hinted
(5/5, verified). Records unchanged (463 / 458-strict ours; 460-strict
community) — the gap is now precisely characterized as rim-compatibility.

## What's open (vol-212)

- **CLOISTER-II border-anchored break-DFS** (the collectable ~14 IB edges).
- Clean-crate refactor + perf pass (bitset candidates; tail2 per-color
  indexing) BEFORE the long campaign.
- Frame choice as a search axis (which perfect border to anchor on; vol-76
  frames / border-MIP-generated; hint-compatible).

## Linked

- [[three-milestones-from-veteran]] — the milestone this implements
- [[interior-14x14-parity-feasible]] — parity feasibility (vol-122)
- [[isentrope-entropy-growth]] — the area-law that frames the difficulty
- [[blackwood-algorithm]] — the community method whose boards hold the record
- [[lp-ub-478-basins]] — border-class enumeration (the BB=60 side)
