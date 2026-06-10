---
name: linear-placement-metric
description: "Vol-211 Phase 0b — the veteran's '231/258 linear placement adjacencies' metric DECODED: 231 and 258 are exactly the cumulative adjacency totals of the BORDER-FIRST scan (60-cell ring then interior row-major) at depths 143 and 156; row-major prefixes on 16- and 14-wide rectangles skip both values (parity). Measured: our bf_bw records are 258/258 (perfect prefix to depth 216-221!); community 469/470s are 247-248/258 (Blackwood spreads breaks early). Veteran milestone #2 already exceeded by our existing boards under this convention."
status: built
metadata:
  type: concept
---

# Linear-placement metric (veteran milestone #2) — decoded + measured

**Origin**: vol-121 veteran hint ("231/258 linear placement adjacencies",
convention unknown); vol-211 Phase 0b decoded and instrumented it.
**Files**: `scripts/v211_cloister/lpa_curve.py`.

## The convention (derived, then numerically confirmed)

Define the **border-first scan**: the 60-cell border ring in ring order, then
the 196 interior cells row-major. Cumulative prefix-adjacency totals along
this scan: 60 after the ring; each interior cell adds +2 (left+up, the border
ring supplying the missing side at row edges), +3 at interior row-last cells
(right-border edge), +3/+4 on the bottom row (bottom-border edges).

- total(d=143) = **231** (border + 5 interior rows + 13 cells)
- total(d=156) = **258** (border + 6 interior rows + 12 cells)

**Parity lemma**: row-major prefixes of a 16-wide board take values
{…,230,232,233,235,…} and of a 14-wide {…,229,230,232,…} — both SKIP 231 and
258. No w×h rectangle has exactly 231 or 258 adjacencies (2wh−w−h=231 or 258
has no integer solutions for h≤16). So the veteran's numbers are *only*
realizable on the border-first ladder — strong evidence this is his solver's
scan order (consistent with Blackwood-line border-first solvers).

Reading: "231/258" = 231 matched of the 258 prefix adjacencies at scan-depth
156 (60 border + 96 interior cells), i.e. a 27-mismatch budget at that
frontier.

## Measurement (complete record boards, 2026-06-10)

| board | matched@156 (/258) | matched@143 (/231) | max perfect-prefix depth | final |
|---|--:|--:|--:|--:|
| our V125 461 (bf_bw off110) | **258/258** | 231/231 | **220** | 461 |
| our V181 460 | 258/258 | 231/231 | 221 | 460 |
| our vol-60 459 | 258/258 | 231/231 | 216 | 459 |
| our V129 463 | 241/258 | 214/231 | 60 | 463 |
| McGavin 469 | 247/258 | 220/231 | 68 | 469 |
| Blackwood+Bucas 469 | 247/258 | 220/231 | 69 | 469 |
| Blackwood 470 ×2 | 248/258 | 221/231 | 64-72 | 470 |

## Findings

1. **Milestone #2 is already exceeded** by our bf_bw-pipeline boards under
   this convention: 258/258 at the veteran point, perfect border-first
   prefixes to depth **216-221 of 256**. (If the veteran meant "deepest
   perfect frontier reachable *during search*", our boards exhibit ≥216 as a
   completed artifact — stronger.)
2. **Two mismatch geographies**: our bf_bw boards push perfection deep and
   pay ALL mismatches in the last ~36 scan cells (pool-depletion wall, cf.
   [[transept-strip-assignment]] rows-10-15 collapse). Blackwood-line boards
   spread breaks early (perfect prefix only 64-72) and finish higher overall.
   Depth-greedy perfection is NOT how the 469-470s are built — they sacrifice
   early-prefix perfection for global budget placement.
3. Our 463 (V129, ALNS-born) has non-bf geography: mismatches include
   early-scan cells (perfect prefix 60 = just the ring).
4. Diagnostic now exists for any pipeline: `lpa_curve.py` reports
   matched@143/@156 + max perfect-prefix depth per board.

## Implication for CLOISTER (vol-211)

The interior bottleneck is the interior COMPLETION: bf_bw proves rows 1-10 of
the interior can be perfect under a perfect border, and the damage
concentrates where piece supply is exhausted. The standalone interior attack
([[cloister-standalone-interior]]) frees the border constraint entirely; its
max-II search must specifically beat the END-GAME, not the opening.

## Linked

- [[three-milestones-from-veteran]] (milestone #2 = this page)
- [[cloister-standalone-interior]] (milestone #3, vol-211 main track)
- [[transept-strip-assignment]] (pool-depletion wall)
- [[blackwood-algorithm]] (why community boards have early breaks)
