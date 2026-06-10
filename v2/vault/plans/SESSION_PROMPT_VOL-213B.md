# Session prompt — vol-213 continuation (drafted at 2026-06-10 close)

You are a senior researcher attacking **Eternity II** (canonical 5-clue,
Selby-Riordan) in this repo. Vol-212 closed same-day (CLOISTER-II built,
validated, characterized); vol-213 is OPEN with the seam/priors/witness
results banked. **Goal unchanged: strict-canonical record — total ≥461
with all 5 hints (HINTS MANDATORY). Secondary: ≥464 matched-edges.
INNOVATION toward solving E2 (480) is the standing directive — record
chasing is the measuring stick, not the destination.**

## Verified state (do NOT re-derive; vols 212-213 measured all of this)

Records: ours 463 matched (1/5 hints) / **458 strict**; community strict
record **460** (2 boards, both verified); target 461. Today's
strict-architecture ladder: 450 unguided / **457 witness-guided**
(verified + rescored; `output/vol-213/cloister2_dfs_20260610T133153/
T457_II351_IB46_strict460a_seed4.json`).

**Toolchain**: `crates/cloister/` (`eternity2-cloister`), 18 tests, fully
regression-gated against vol-211. Bin `cloister2`: modes dfs/sa/hybrid/
tail2polish; `--frame <file|dir>` (bordered), `--tail2`, `--tail2-cap`,
`--exact-tail K`, `--scan row|boustro|seam:N`, `--max-disc`,
`--prior-boards <dir>`, `--schedule-from-board <board>`, `--hints`.
Bins `attach2` (exact border MIP), `frame_ub` (LP UB — builder stalls,
see item 3). History CSV + timestamped dirs (UTC tags!) throughout.

**CLOISTER-II facts** ([[cloister-ii-border-anchored]], [[vol-212]],
[[vol-213]]):
- Border-anchored construction COLLECTS the rim coupling: IB 48-55
  realized vs 34-39 post-hoc ceiling. The vol-211 ★ prediction confirmed.
- Unguided plateau **450-strict / 453-unhinted** — invariant to compute
  (+1/decade at 2 h), recipe shape, scan geometry (seam {6,7,12} ≤
  row-major; seam:12 fixes hinted reliability 8/8, no total gain), frame
  identity (5 viable frames, ONE 444-450 band), self-pool priors
  (asymptote null). Naive LDS refuted (chokes at depth 83-103).
- Hinted recipe that works: tail2 trigger 168 (absorbs both row-12 deep
  hints), gates 120-168, breaks 8. et14 (trigger 182) needs gates ≥
  reach; bordered wall is 153 ≈ 2.5 cells/break.
- ★ **Witness anatomy**: the community strict-460s are PERFECT-171-CELL
  prefixes (all 20 breaks at row-major depths 167/171-195); their 2-row
  tails are unimprovable within 4×10⁹ B&B nodes (both boards). Witness
  priors alone → 452×8; + witness gates (`--schedule-from-board`) + et14
  → 455-457, saturates at 60 s. Divergence cap: break candidates are NOT
  prior-ordered. Early extra gates DILUTE (452-454).
- ★ **Frame pool**: hint-compat census 1/500 vol-76 frames (0.2%).
  Killer pinpointed: interior (0,1) must match frame-N + corner-E +
  hint15-S simultaneously (same at (0,12)/hint26). ≥75k frames exist
  (Hamilton LB) ⇒ ≥150 compatible expected. Early gates (first ≤14)
  bypass at 1-3 break cost (f300/f350 → full-strength band). f160 (the
  1/500) lands mid-band ⇒ frame identity irrelevant at v1 recipe.

## The plan (≤3 binding; write CURRENT-VOL accordingly)

1. **REPLAY mode (prior-over-cost)** — the live 460+ shot. In dfs.rs's
   priors branch (~15 lines): when `break_open`, ALSO drain break-segment
   candidates into the per-depth buffer; sort by (Reverse(weight), cost);
   gate behind `--prior-over-cost`. Effect: the witness walk takes its
   break pieces AT its break cells (no cost-0-subtree detour) ⇒ exact
   replay to depth 182, exact tail ≥ its row 13, THEN anytime backtracking
   explores the perfect-prefix NEIGHBORHOOD with exact endgames. Run on
   both witnesses (460a/b), 8 seeds × 300 s, then hours if the curve
   moves. Every board ≥458: verify_board + rescore + interior_split
   before any claim; provenance (witness-derived) stated in the vault.
2. **Hint-compatible frame GENERATOR** — unlock the frame pool. Extend
   the border MIP (or a small ring-DFS): BB=60 + the four chain-feasibility
   constraints baked in (there must EXIST interior pieces satisfying the
   (0,1)/(0,12) top chains and the deep-hint-adjacent cells given the
   ring's inward colors — encode as: for each such cell, ≥1 compatible
   (piece,rot) among interior pieces; or generate-and-probe: enumerate
   diverse BB=60 rings, 6 s hinted probe, keep survivors). Target: 50+
   compatible frames; run the v1 recipe census; the question is whether
   ANY frame escapes the 444-450 band (vol-212's uniform-band claim is
   5-frame-based — widen or refute it).
3. **Choke-map instrument + auto-gates** (user idea, honest expectation:
   reliability + small gains): per-depth death histograms from epoch
   ends (the DFS already tracks max_depth; add depth-of-death counts per
   epoch), emit per-(frame, scan, hinted) choke profiles; place gates AT
   measured chokes instead of hand-spread; report whether auto-gates beat
   hand gates (≥8 seeds, min/med/max). Also answers "are hint positions
   the choke?" quantitatively (seam:12 evidence says reliability yes,
   totals no — verify on the wider frame pool).

Standing invitation (pick up if items finish or stall): **PREFIX VAULT**
— bank deep perfect prefixes (≥160) found across all runs as restart
seeds with fresh tie-breaks (the perfect-171 prefixes exist but are
measure-tiny in shuffle space; banking concentrates search where it
matters). And `frame_ub` direct-HiGHS builder (good_lp one-at-a-time
constraint adds stalled at 44 CPU-min; calibrate on Bucas-469 → 409 and
strict460a hinted → 400) for per-frame ceiling certificates.

## Implementation lessons (hard-won today — do not re-learn)

- Run-dir timestamps are **UTC**; local = UTC+2. Use `ps lstart` for wall
  arithmetic, not dir tags.
- Bitset candidates are SLOWER than the per-(color,color) lists (0.64×,
  measured head-to-head) — the lists ARE the precomputed intersection.
  Don't rebuild that idea.
- tail2-in-DFS needs cap 30k (50M = 0 completions); its trigger at 168
  fires BEFORE depth-171 witness prefixes end — witness work uses et14.
- Priors order ONLY cost-0 candidates today (that's the replay-mode gap).
- Hint pre-filters are sound (and strong) only pre-first-gate; deep-hint
  reservation starves without them; seam:12 puts both deep hints in the
  closure row (8/8 reliability) if you need that.
- 8 cores max TOTAL across all processes (user directive). zsh does not
  word-split `$VAR` — quote schedules.
- The attach MIP sometimes prefers BB<60 + more IB; `--require-bb60` to
  force.

## Read first

1. `vault/plans/CURRENT-VOL.md` (update it: vol-213 binding items above)
2. `vault/sessions/vol-213.md` (day-1 journal: all numbers cited here)
3. `vault/concepts/cloister-ii-border-anchored.md` (architecture + plateau)
4. Memory: `project_e2_vol212_cloister_ii_2026_06_10` (incl. vol-213
   addenda)

## Discipline (load-bearing)

- ≥8 seeds, min/median/max; single-seed ≠ result. Verify + independently
  rescore every ≥458 candidate BEFORE any claim; state witness provenance.
- Timestamped outputs; append the global cloister history CSV; never
  overwrite.
- Honest negatives are deliverables — today produced nine and they carved
  the search space precisely. Take vault notes AS YOU GO.
- One named invention per volume (REPLAY/generator are vol-213; PREFIX
  VAULT would open vol-214). No limiting thoughts on ambition — the
  puzzle HAS a 480 solution.
