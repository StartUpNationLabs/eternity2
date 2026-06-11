---
name: midden-damage-geometry
description: "MIDDEN (vol-215): damage-geometry search — mismatches may only be PAID at cells in a mask S; search over S's SHAPE (rows/cols/dispersed/color-driven) and co-design with sacrifice pieces. Generalizes every known damage control (our depth gates, Verhaard slip arrays, Blackwood relaxations are all WHEN; MIDDEN is WHERE). No prior art found in vault, community, or academic sources."
status: partial
metadata:
  type: concept
---

# MIDDEN — damage-geometry confinement and search

**Origin**: vol-215 (2026-06-11), invented in response to the user's
"invent new stuff never seen before" directive. **Files**:
`crates/cloister/src/dfs.rs` (`break_cells` mask in both break-open
levels), `endgame.rs` (`exact_tail` confinement: non-mask tail cells
admit only 0-mismatch candidates; `TAIL_INFEASIBLE` sentinel guards
the anytime recorder), `cloister2 --break-cells rows:|cols:|cells:`.

## The observation behind it

Every damage-control mechanism in E2 history is TEMPORAL: our gate
schedules, Verhaard's slip arrays, Blackwood's scheduled relaxations
all say *when* (at which search depth) a mismatch may be paid. Under
row-major scans "late" ≈ "bottom rows" — which is why every high board
ever made (both community strict-460s included: breaks at depths
171-195 = rows 12-13 exactly) has its damage compressed in the last
rows. That geometry is an ARTIFACT of the shared control variable, not
a property of the puzzle. Nobody has searched over damage PLACEMENT.

## Definition

`break_cells`: a per-cell mask S. Break candidates (cost 1 and 2) are
admissible only at cells ∈ S — at ANY scan depth (the schedule still
caps the budget and may add temporal gates on top). The exact tail
honors S exactly: tail cells ∉ S only accept 0-mismatch placements;
if no S-respecting completion exists the tail returns
`TAIL_INFEASIBLE` (never recorded). Forced cells (hints) are exempt.
Semantics: S = cells allowed to PAY (mismatches attribute to the
later-scan cell, matching `schedule-from-board`).

## The search this enables (vol-215 program)

1. **Witness-replication control**: S = rows 12-13 (28 cells), budget
   20 — witness-proven to admit 460 on strict460a.
2. **Geometry sweep**: columns, double-seam rows, dispersed lattices,
   ring patterns, per-column staircases — same budget, same frame:
   does ANY geometry beat the rows-12-13 default that temporal gating
   forced on everyone?
3. **Deficit-driven S**: place the midden where LEDGER says the rare
   colors pile up (cells adjacent to surplus demands).
4. **Sacrifice co-design**: choose the ~20 worst-tilability pieces AND
   the burial cells that absorb their colors; the residual 176-piece
   problem must complete perfectly (composes with QUOTA and LADDER).

## Measurements

**Sweep 1 (strict460a hinted, budget 20, gates open, 300 s × 8 per
geometry): 0 completions everywhere — with a structural find inside.**

| S (28 cells each) | wall (min/med/max depth) |
|---|---|
| rows:12,13 (witness shape) | 153/153/158 — the perfect wall: S deeper than the wall is unreachable |
| rows:6,7 | 148/153/156 |
| cols:6,7 | 125/152/153 |
| **dispersed (every 7th cell)** | **167/167/174** |

★ **Dispersed damage availability extends the perfect-walk wall
153 → 167-174 (+14 to +21)** — sparse break opportunities along the
whole walk keep the pool healthy far deeper than any contiguous
geometry. It fails only at the endgame (nothing absorbs row-13
damage). The witness shape is UNREACHABLE for an unguided walk —
confirming vol-213's account of why only perfect-prefix lotteries (or
witness guidance) ever reach it. Hybrid v2 (dispersed ∪ tail rows,
density sweep) queued.

QUOTA A/B same night (v1 hinted tail2, 96:20:0.25): 446/447/449 vs
control 446/447/448 — marginal at this single config.

**Sweep 2 (hybrids, dispersed ∪ tail, budget 20 gates-open)**: still 0
completions; walls 162-178 (D10+tail max 178 — 4 cells short of the
trigger). All-zero gates drain the budget early ⇒ temporal × spatial
composition needed (gate the dispersed region, keep the tail open).
Density: sparser ≥ denser (D10 ≥ D7 > D5).

**ladder5 run-1 invalidated by a ranker bug**, now fixed: the frame
JSON is a FULL board, so the ranker's "ring" included the witness
interior — `breaks_of`/`deficit_of` measured divergence-from-witness
(280 fake breaks ⇒ budget-292 schedules). ⚠ All ladder3/2c deficit
scores were computed with this pollution — the "deficit scoring null"
verdicts are REOPENED. Fixed ranker: d155 probe prefix = deficit 0,
breaks 6. ladder5b (budget-14 probes) relaunched.

**ladder5b (fixed ranker): rung-2 walls 159-167, 0 completions — third
straight completion-failure of the composition.** Anti-thrash call
(vol-43-reframing): config iteration stopped at dawn; overnight
deciders launched instead — (a) hybrid choke diagnosis (where exactly
does the 168-182 region kill walks? per-depth death histograms,
8 × 60 s), (b) the never-run incumbent extension (d146-seed63 at
3600 s × 8 — does the 451 basin extend?). Morning analysis decides
MIDDEN v3 (temporal × spatial gating) vs pivot.

## Linked

[[replay-prior-over-cost]] (witness damage anatomy),
[[ledger-color-deficit]], [[ladder-prefix-racing]],
[[cloister-ii-border-anchored]], [[scan-order]]
