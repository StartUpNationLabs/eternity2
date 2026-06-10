# Current Volume — Vol-212 — CLOISTER-II: border-anchored break-DFS

**Status**: drafted at vol-211 close (2026-06-10). Strict-canonical (5/5
hints) is the primary track per user directive; bar = **461** (community has
verified 5/5 460s; ours 458).

## Why this (the vol-211 result that forces it)
Vol-211 proved: (a) the standalone interior is highly solvable with break-DFS
+ exact endgames (II=356 unhinted / 351 hinted in minutes — both best-ever);
(b) **rim-compatibility is an interior property worth ~14 attachable IB**
(control: Bucas-469's interior re-attaches to exactly 469; ours cap at IB
34-39) and it is NOT collectable post-hoc (λ-proxy, tie-breaks, alternation
all ≤ +1). ⇒ The border must constrain the interior DURING construction.
The community strict-460s came from border-first WITHOUT our endgame
machinery — that headroom is the target.

## Binding items (≤3)

1. **Refactor first**: `crates/cloister/` clean crate (interior model / DFS /
   endgames / SA / border-MIP as modules; unit tests on 4×4-6×6 generated
   puzzles + the validated vol-211 numbers as regression). Perf pass: bitset
   candidate intersection in the DFS hot loop; per-color indexing in
   tail2's column_pairs. Port, don't re-derive. (User asked for this; do it
   BEFORE the campaign so the long compute runs through the fast version.)
2. **CLOISTER-II**: border-anchored break-DFS — fix a perfect frame
   (BB=60; from border-MIP or vol-76 frames), interior scan where IB edges
   are REAL edges (rim side vs fixed border inward color enters the
   cost/break budget), exact-tail scoring rim sides too, 5/5 hints forced.
   Sweep frames × seeds × schedules; anytime-minimize total breaks.
   **Record check: total = 480 − breaks ≥ 461 with 5/5 ⇒ strict record.**
   Verify any candidate with verify_board + interior_split before claiming.
3. **Campaign + variance discipline**: ≥8 seeds per config, report
   min/median/max; sweep frame choice (it is a first-class axis); persist
   everything (history.csv pattern); throughput arithmetic BEFORE multi-day
   commitments (CLAUDE.md rule — the 176-plateau of vol-122 A1 is the
   baseline this must beat, and vol-211's machinery is the reason to expect
   it can).

## Audit-at-open compliance
- INVENTIONS_BACKLOG §I milestone-3: status flips to `built-standalone`
  (vol-211); milestone-2 metric: `built+exceeded`; A1/B3 fold into
  CLOISTER-II (same decomposition, correct direction).
- The vol-210 "decision point" (single-machine exhausted) is superseded in
  scope: vol-211 found a genuinely new, productive machine-local frontier.

## Linked
- [[cloister-standalone-interior]] (vol-211 main concept + the rim result)
- [[linear-placement-metric]], [[blackwood-algorithm]], [[lp-ub-478-basins]]
- session: [[vol-211]]
