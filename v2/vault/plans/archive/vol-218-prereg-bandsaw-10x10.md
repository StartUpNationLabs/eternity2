# Vol-218 pre-registration — BANDSAW @ 10×10 (M0–M5) + fugacity side gate

Registered 2026-06-12T13:13:35Z, BEFORE any measurement code ran.
Canonical copy: this file (vault). A timestamped copy goes to
`output/vol-218/prereg_20260612T131335/` at first run.

USER DIRECTION being implemented: "take that problem on smaller scale
and be very rigorous." Vehicle = `band-split-exact-solve`
(BACKLOG vol-218). NOT full-solution enumeration (the 8×8-rig
directive stands — sub-problem rigor only: band enumerations, endgame
joins, instrument comparisons).

## Instances (fixed)

- `generate_with_solution(GeneratorConfig{ size: 10, interior_colors: 8, seed })`
  for **seeds 101..=108** (8 instances). Vol-35 convention (10×10,
  8 colors); known differences from E2 stated in §Transfers.
- 5 hints = the canonical solution's placements at positions
  (col,row): **(2,2)=22, (7,2)=27, (4,5)=54, (2,7)=72, (7,7)=77** —
  scaled analog of E2's (2,2),(13,2),(7,8),(2,13),(13,13).
  All work is 5/5-hint strict.
- Stage structure: **entries = perfect rows 0–5** (60 cells, hints
  22/27/54 obeyed, hint pieces bucket-excluded elsewhere);
  **endgame = rows 6–9** (40 cells, pool = the 40 unused pieces,
  hints 72/77 forced).
- Cost convention (identical to stage4_finish): each cell pays its N
  edge and its W edge; board-edge sides are structural (candidates
  filtered); so the endgame pays exactly 76 edges (10 join + 30 N +
  36 W). Full-board score out of 180 interior edges.

## Entry population (fixed protocol, selection-free)

Per instance: row-major perfect-walk DFS generator, randomized value
order per restart (seeded by instance seed + restart counter), 60 s ×
1 thread, bank every distinct (frontier, pool) state at depth 60,
cap 200 unique entries. If an instance yields < 20 entries, extend
budget ×4 ONCE and report. 8 instances run in parallel (8 cores max).
M1/M2 grid = first 20 entries per instance in generation order;
M4 = the full bank.

## M0 — machinery gate (before any M1–M5 number is reported)

Brute-force selftest on reduced instances (5×5, 4 colors, last-2-rows
and last-3-rows): exhaustive enumeration cross-checks (a) exact
distinct-piece count at every budget b, (b) repeats-allowed count,
(c) exact min-break, (d) BANDSAW min-break. All must match exactly.
Plus 10×10 invariants: every banked entry rescored (60 cells, 0
breaks, 5/5 hints, no dup pieces).

## M1 — relaxation-gap curve (the distinctness instrument's target)

Per entry, band depth n ∈ {1,2,3,4} (rows 6..5+n; n=4 includes bottom
border), budget b ∈ {0,1,2,3}:
- `N_exact(n,b)` = # distinct-piece fillings with cost ≤ b
- `N_relax(n,b)` = same count, repeats allowed (transfer DP, same
  forced cells, same cost convention)
- plus per-entry `gap@b*` = log10(N_relax(4,b*) / N_exact(4,b*)) at
  b* = exact min-break (N_exact ≥ 1 by definition there).
Report distributions (min/med/max over 20×8 entries) by (n,b);
**phantom-feasible rate** = P[N_exact=0 ∧ N_relax>0] by (n,b).

Registered predictions:
- **P1.1**: median log10(N_relax/N_exact) (entries with N_exact>0)
  strictly increases with n at every fixed b.
- **P1.2**: phantom-feasible rate increases with n at fixed b.
- Size of the gap at n=4 is exploratory (reported, not gated).

## M2 — exactness gate (HARD; 16×16 deployment is conditional on it)

For every entry in the M1 grid (≥ 20 × 8 = 160): BANDSAW min-break
(meet-in-the-middle, two 2-row bands, hash join on (complement-pool
mask, interface vector), iterative deepening on total budget) must
equal exhaustive B&B min-break (mini_bb run to exhaustion, no caps;
loud cap report excludes the entry and counts against exhaust rate).
- **Gate: 100% equality on all B&B-exhausted entries; exhaust rate
  ≥ 90%** (else the testbed is mis-sized; re-scope loudly).
- Any mismatch = machinery bug: fix and rerun the WHOLE grid; a
  persistent mismatch = binding failure; 16×16 deployment blocked.

## M3 — join scaling (the 16×16 deployment decision data)

Per entry at final ID budget B: top/bottom enumeration sizes (raw
fillings and distinct (set, vector) keys), join-candidate pairs,
matched pairs, wall-clock BANDSAW vs wall-clock exhaustive B&B.
Report distributions; growth vs B and vs board size (12×12 stretch).
Registered decision rule for 16×16 deployment: M2 passed AND median
BANDSAW wall-clock ≤ 10× median B&B at 10×10 AND projected 16×16
top-side key count at budget floor+2 < 10^8. (Projection method
reported with the data; the rule is the registered intent.)

## M4 — instrument ordering (the strategic measurement)

Population = full bank per instance. Instruments, each ranking
ascending:
1. **relaxed floor** — repeats-allowed tropical min-break, rows 6–9;
2. **greedy label** — best total from mini_bb at 100 ms budget;
3. **exact min-break** — BANDSAW (ceiling instrument).
Cohorts: top-10 per instrument + random-10 (RNG seed 7). Every cohort
member gets its exact min-break computed. Cohort achieved = min and
median exact total.

Registered predictions:
- **P4.1**: greedy cohort beats floor cohort on median achieved
  exact min-break in ≥ 6/8 instances (vol-217's refutation transfers
  as an ORDERING).
- **P4.2**: floor cohort ≈ random cohort (|median diff| ≤ 1 break)
  in ≥ 5/8 instances (floors don't see distinctness at the endgame
  boundary).
- **P4.3**: exact cohort beats greedy cohort in ≥ 6/8 instances
  (selection headroom exists above the greedy label).

## M5 — stretch (exploratory, reported but ungated)

(a) MIRROR@10×10: generation with break budget β ∈ {2,4} allowed in
rows 0–1 only, perfect rows 2–5, matched generation compute;
compare exact full-board totals achievable from top cohorts vs the
perfect-top population. (b) 12×12 (10 colors) scaling point for M3.

## Side gate — fugacity-corrected counts vs the 149 measured labels

Estimator: equal-case fugacity-corrected count over the REAL 16×16
stage-4 region (rows 12–15; 64 cells = 64-piece pool; hints forced),
b-axis profile; per-entry score = **corrected floor** = smallest b
with corrected count ≥ 1. χ-convergence checks pre-registered
(χ ∈ {2,4,6,8}; vol-210 artifact lesson) — a score that moves with χ
at the report point is NOT reported as a result.
- **S1 (gate)**: Spearman ρ(corrected floor, greedy label) ≥ 0.35 on
  the n=127 non-DNF labeled entries
  (`output/vol-217/stage3_bank_*/greedy_labels.jsonl`).
- **S2 (calibration, exploratory)**: median corrected floor within
  [0.5×, 1.5×] of median measured label (44–52 band) — does the
  correction SEE the distinctness wall that moves floors 6–9 → 40s?

## Transfers / does-not-transfer (standing, repeated in every writeup)

TRANSFERS: machinery correctness, scaling laws, instrument ORDERING.
DOES NOT TRANSFER: absolute constants and difficulty (vol-35: size
governs landscape). Known instance differences from E2: generator
draws ALL edges (incl. border-ring) from one 8-color pool (E2: 5
dedicated border colors + 17 interior); 22.5 edges/color at 10×10 vs
E2's 28.2. LIGHTHOUSE caveat (vol-184) noted: heuristic bidirectional
MERGE was refuted; BANDSAW differs by EXACT complementary-pool
accounting — the join-size measurement is the test, not an
assumption.
