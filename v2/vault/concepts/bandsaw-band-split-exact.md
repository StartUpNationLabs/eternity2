---
name: bandsaw-band-split-exact
description: "Vol-218 named invention: BANDSAW — band-split exact endgame solve via meet-in-the-middle with exact complementary-pool accounting (tops keyed by (pool mask, interface vector); bottoms enumerated per complement-pool group), iterative deepening from admissible tropical floors. Validated at 10×10 (user-directed rigor): exact within b*≲6; beyond it the budget-B tree grows ~×20/break — and suffix-pruned ID-B&B DOMINATES the MITM (12 s vs DNF at b*=6). The durable instruments: tropical-suffix tables (exact min-plus column-state bounds) and exact distinctness-aware LB certificates from completed ID rounds."
status: built
metadata:
  type: concept
---

# BANDSAW — band-split exact endgame solving (and what beat it)

**Origin**: vol-218 binding 2 (user-directed: "take that problem on
smaller scale and be very rigorous"); implements
`band-split-exact-solve` (BACKLOG, vol-217 close).

**Files**: `crates/bench-audit/src/mini.rs` (machinery + selftests),
`crates/bench-audit/src/bin/{mini_gen,mini_lab,fugacity_lab}.rs`,
prereg `vault/plans/archive/vol-218-prereg-bandsaw-10x10.md`.

## Definition

Exact min-break completion of a 2h-row endgame band given (frontier,
pool, forced hints), by meet-in-the-middle:

1. enumerate the top h rows at budget B, keyed
   (pool-mask, south-interface vector) → min cost; budget reduced by
   the bottom band's tropical floor (admissible);
2. group tops by pool mask; per distinct mask enumerate the bottom
   h rows from EXACTLY the complement pool (the LIGHTHOUSE-hazard
   fix: exact complementary-pool accounting, no heuristic merge);
3. hash-join on interface vectors, total = c_T + c_B + H(v_T, v_B);
4. iterative deepening on B from max(relax floor, top floor + bottom
   floor); a completed joinless round at budget B is an EXACT
   certificate b* > B.

All enumeration is COLUMN-MAJOR (vertical coupling binds per column;
row-major free rows are ~1e8× wider) and pruned by
**tropical-suffix tables**: backward min-plus DP giving, per column c
and per entering east-color state, the exact repeats-allowed minimum
remaining cost — an admissible bound for distinct-piece search
(selftests: suffix floor ≡ relax floor; prune changes no counts).
Formulation note: backward over rows with mismatch charges attached
to OUTPUT axes — point reads + A/B/C/D class mins, no exclusion
tables (the vol-217 "exact 2D exclusion" trap avoided by
construction).

## Measured (vol-218, 10×10 testbed, 8 instances, prereg M0–M4)

- **M0**: all machinery brute-force selftested (exact counts, relax
  DP, bb, bandsaw, suffix). Catches: shuffled-pieces rot table;
  the clue-wall (d34) in naive generators.
- **M2 (exactness gate), controlled b*-graded family** (canonical
  prefix, 0–6 corrupted frontier columns): bandsaw ≡ ID-B&B on every
  mutually-decided rung. Zero wrong answers anywhere.
- ★ **The exactness wall**: budget-B enumeration trees grow ~×20 per
  budget unit (b1 ≈ 20 made mechanical). Blind perfect-prefix
  entries (floors 4–6, b* ≥ 8): unpruned bandsaw caps 4e9 nodes
  INSIDE round 6; suffix-pruned completes rounds 6–7 in ~94 s, still
  caps. Enumerability of conditioned sub-problems is REAL near
  cost 0 and dissolves with damage budget — quantifying why SOTA
  boards confine damage to one band: every spent break re-inflates
  the conditioned tree ×~20.
- ★ **Suffix-pruned ID-B&B dominates the MITM**: ladder rung b*=6 —
  bb proves optimality in 12.4 s where bandsaw caps at 179 s. Rung
  scaling bb: 0/0/2/19/263/12,407 ms for b* = 0..6 (×13–50 per
  rung). The MITM pays full enumeration of BOTH halves; a
  single-sided proof tree with the same tropical bounds needs only
  one optimum + an exhaustion proof. (LIGHTHOUSE precedent
  re-understood: exact bidirectional enumeration costs the product
  even when the merge is exact.)
- **M1 relaxation-gap curve**: see [[vol-218]] — phantom-feasible
  74–83% by 2–3 rows; median gap ×6–8 at ONE row, ×10³–10⁴ at two,
  ∞ at three. The repeats relaxation is fiction exactly where
  selection needs it.

## What survives as durable instruments

1. **Tropical-suffix tables** — exact, µs–ms, admissible column-state
   bounds; turn slack-ceiling B&B from 600 s+ DNF into seconds-scale
   proofs at small b*; portable to the 16×16 stage-4 endgame and to
   any band sub-problem.
2. **Exact LB certificates** — every completed ID round (bb or saw)
   certifies b* > B with distinctness fully accounted. The first
   instrument in the program that bounds finishability from BELOW
   honestly (relax floors cannot: M1).
3. **The b*-graded corruption ladder** — a controlled-difficulty
   exactness gate for any future endgame solver.

## Open

- M3/M4 full distributions (8 instances) — in flight at write time.
- 16×16 deployment decision per prereg rule (M2 ✓ on decided set;
  wall-clock + join-size data pending).
- Fugacity side gate: 10×10 equal-case validation vs exact counts,
  then the registered 16×16 ρ bar (or its honest deferral).

## Linked

[[CURRENT-VOL]], [[vol-218]], [[staged-fullboard-construction]],
[[crossing-oracle]], [[fugacity-corrected-counts]],
[[isentrope-entropy-growth]]
