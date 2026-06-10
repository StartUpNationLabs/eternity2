# Prompt — vol-212 session (drafted at vol-211 close, 2026-06-10)

Copy the block below as the opening message for a fresh session.

---

You are a senior researcher attacking **Eternity II** (canonical 5-clue,
Selby-Riordan) in this repo. This session continues the 14×14 plan: vol-211
(CLOISTER) cracked the standalone interior and measured exactly where the
remaining value sits. **The goal: beat the strict-canonical record — total
≥461 with all 5 hints (HINTS ARE MANDATORY, user directive). Secondary:
≥464 matched-edges.** Reducing the search space beats searching faster; you
have all rights and all compute on this machine.

## Verified state (do NOT re-derive; vol-211 measured all of this)

Records: ours 463 matched-edges (1/5 hints) / 458 strict; **community strict
record = 460** (5/5, 2023 groups thread, 2 boards verified LEGAL — vol-211
discovery; the bar is 461, not 459). Community matched ceiling 469.

Edge accounting: 480 = 364 II + 56 IB + 60 BB; interior (196) and border
(60) piece sets are disjoint, coupled ONLY through 56 IB edges. All high
boards have BB=60.

Vol-211 CLOISTER results (`crates/bench-audit/src/bin/cloister.rs`,
`cloister_border.rs`, `interior_split.rs`; outputs + history in
`output/vol-211/`, key concept `vault/concepts/cloister-standalone-interior.md`):
- Standalone free-rim 14×14: DFS wall 174/196 (sharp). Break-DFS (scheduled
  gates) + exact 1-row endgame B&B → **complete interiors II=356 unhinted /
  351 hinted in minutes** (351 beats every known 5/5 board's interior; the
  only higher interior anywhere is 358 inside the Blackwood+Bucas 469).
- Exact border-attach MIP (HiGHS, proven optimal): our interiors accept only
  **IB 33-39** → best assembled **455/480 unhinted, 446/480 strict-5/5**.
- ★ **Rim-compatibility**: control re-attach of the Bucas-469 interior
  recovers EXACTLY 469 (IB=51). Equal-II interiors differ by ~14 attachable
  IB. The property is created by growing the interior INSIDE a border and is
  NOT retrofittable — λ=1 multiset-overlap (−3 II, refuted), rim-supply DFS
  tie-break (−2 II, refuted), position-exact alternating projections (+1,
  converges 446). Border-side algorithmics are DONE (attach is exact).
- tail2polish PROVED the 356's last-2-rows optimal given its prefix ⇒ II
  improves only via prefix diversity; pure-II grinding costs ~10× compute
  per +1 II and is worth only +1 total each — the rim carries ~14.
- Veteran metric #2 ("231/258") decoded (border-first scan ladder) and
  already exceeded ([[linear-placement-metric]]).

## The plan (CURRENT-VOL.md is binding; ≤3 items)

1. **Refactor FIRST** (user-approved): `crates/cloister/` clean crate —
   interior model / DFS / endgames / SA / border-MIP as modules; unit tests
   on generated 4×4-6×6 + vol-211 numbers as regression (wall 174, II 356
   @30s unhinted, attach obj 97-99, Bucas control = 469). Perf pass: bitset
   candidate intersection in the DFS hot loop (~2-5×), per-color indexing in
   tail2's column_pairs. Port, don't re-derive.
2. **CLOISTER-II: border-anchored break-DFS** (the vol-212 invention; name
   it). Fix a PERFECT ring (BB=60; generate via the attach MIP or vol-76
   frames), then run the break-DFS over the interior where the 56 IB edges
   are REAL edges: rim side vs the fixed border's inward color enters the
   cost/break budget from cell 1; exact-tail scores rim sides too; 5/5
   hints forced (all hint machinery exists: break-payable hints, gated
   pre-filters, 1-break reservation per deep hint at cells 169/180, hint
   pieces excluded from free cells). Anytime-minimize total breaks.
   **Record condition: total = 480 − breaks ≥ 461 with 5/5 hints.**
   The community strict-460s ARE this architecture without break-scheduling
   or exact endgames — that machinery gap is the headroom.
3. **Breadth campaign** (user-ratified exploration design): 30-300 s budgets
   across (frame × seed × schedule × scan) portfolio — NO long single-tree
   runs (+1 II per ~10× compute, measured). The frame is a first-class axis:
   each perfect ring re-rolls the problem; sample diversely, measure
   per-frame II+IB completion distributions, double down on fat tails.
   Explore BETTER: limited-discrepancy-style prefix exploration instead of
   left-biased DFS restarts; boustrophedon scan (border anchoring breaks the
   rotation isomorphism that made column-major redundant on the free rim).

## Implementation lessons (hard-won — do not re-learn)

- Hints fix (piece, rot), NOT edge perfection — forced cells pay break
  costs; strict-matching them walls the search at the deep hints.
- Removing neighbor pre-filters naively → late-constraint-check blowup
  (2.7 G nodes stuck at depth 15). Hard filters are sound only for hints
  before the first break gate.
- Reserve breaks for unplaced deep hints or ordinary breaks starve them
  (every seed died at exactly cell 180).
- Grey-grey adjacencies must never count as matches (corpus "448" artifact).
- tail2 (2-row exact) as in-DFS trigger loses to 1-row under time pressure
  (truncated B&B < break-DFS at row 12); its role is post-hoc polish — and
  needs per-color indexing before it's affordable in-loop.
- The attach MIP sometimes correctly prefers BB=57-58 + more IB; force
  BB=60 only as a probe (`--require-bb60`).
- Output discipline: timestamped dirs, per-seed JSON + .url.txt, global
  `cloister_history.csv` — keep appending to it.

## Read first

1. `vault/plans/CURRENT-VOL.md` (vol-212 binding items + exploration design)
2. `vault/concepts/cloister-standalone-interior.md` (all vol-211 numbers)
3. `vault/sessions/vol-211.md` (compact journal)
4. `vault/E2_KNOWN_FACTS.md` §Records (corrected: community strict-460,
   interior records)
5. Memory: `project_e2_vol211_cloister_2026_06_10`

## Discipline (load-bearing)

- Verify every record candidate: `verify_board` (256/256 unique, 5/5 hints,
  0 border violations) + `interior_split` before any claim.
- ≥8 seeds per config; report min/median/max. Single-seed ≠ result.
- Timestamped output paths; never overwrite; append `cloister_history.csv`.
- Throughput arithmetic BEFORE any multi-day commitment. The baseline to
  beat: vol-122 A1's 176-cell plateau (plain CSP-fill from clean borders);
  vol-211's break+endgame machinery is the reason to expect better — but
  measure the bordered wall FIRST (cheap), then size the campaign.
- One named invention per volume; vault notes AS YOU GO; honest negatives
  are deliverables (vol-211's rim-compatibility result came from three
  refuted retrofits).

Start by reading the four vault files, do the refactor (item 1) with the
regression numbers as the acceptance gate, measure the bordered-interior
wall with the ported machinery (the cheap decisive measurement), then build
CLOISTER-II and launch the breadth campaign. Aim: a verified 461-strict
board, or the rigorous characterization of why the bordered wall resists —
either is a real deliverable.
