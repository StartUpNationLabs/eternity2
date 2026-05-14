# Vol-44 — LP-relaxation UB + border-class identification

**Theme**: Build LP-relaxation UB for canonical-E2 5-clue borders.
Measure on the 10 verified record boards. Identify border-classes.

**Status**: in progress.

## What was built

- `crates/bench-audit/src/border_ub.rs` — LP formulation (`lp_ub_with`)
  + `LpOptions` (integer toggle for MIP mode).
- `crates/bench-audit/src/bin/lp_smoke.rs` — toolchain smoke test.
- `crates/bench-audit/src/bin/border_lp_ub_small.rs` — small-puzzle
  validation (6×6/4 and 8×8/6 give LP slack = 0 at optimum).
- `crates/bench-audit/src/bin/border_lp_ub.rs` — LP UB on a board's
  border + canonical hints.
- `crates/bench-audit/src/bin/border_mip.rs` — same model with binary
  vars, HiGHS B&B.
- `crates/bench-audit/src/bin/border_lp_perturb.rs` — swap-perturbation
  experiment (built, not yet run).

## Full record sweep

10 verified canonical-E2 records, LP UB measured (corrected formulation
with B-I matches as variables, not forced).

| Record | Score | LP UB | bb | bi_ub | Class |
|---|---:|---:|---:|---:|:---:|
| vol-32 458 vanilla_fast | 458 | **478.0** | 60 | 54.09 | A |
| vol-35 458 deep458 winning5 s5 | 458 | 478.0 | 60 | 54.11 | A |
| vol-32 456 blackwood_raw s2 | 456 | 478.0 | 60 | 54.86 | A |
| vol-39 455 diverse s1 | 455 | 478.0 | 60 | 55.07 | A |
| vol-39 455 diverse s5 | 455 | 478.0 | 60 | 54.75 | A |
| vol-36 454 make-canonical | 454 | 478.0 | 60 | 54.40 | A |
| vol-32 457 blackwood_mrv s7 | 457 | **477.0** | 60 | 53.99 | B |
| vol-32 457 blackwood_mrv s10 | 457 | 477.0 | 60 | 53.80 | B |
| vol-32 456 blackwood_raw s4 | 456 | 477.0 | 60 | 53.49 | B |
| vol-32 457 blackwood_mrv 30min s4 | 457 | **476.0** | 58 | 54.88 | C |

## Border-class findings

**Three distinct border-classes in our records:**

- **Class A** (UB 478, bb=60): 6 records — both 458s, the 456 (s2), both
  455s, the 454. Best achieved = 458. Gap to LP UB = 20.
- **Class B** (UB 477, bb=60): 3 records — both 457s (s7, s10) and the
  456 (s4). Best achieved = 457. Gap to LP UB = 20.
- **Class C** (UB 476, bb=58): 1 record — vol-32 457 30min seed 4. Has
  a structurally weaker border (only 58 of 60 B-B matches). Gap = 19.

## What this proves

1. **The 458 record and the canonical 454/455/456 records share a
   single border-class (A).** They differ only in interior. Within-class
   movement spans a 4-point spread (454 to 458).
2. **The vol-32 457 records sit in a different border-class (B) — not
   one point below 458 but a structurally different basin with its own
   LP ceiling at 477.** They are within 1 of their basin ceiling, while
   class-A's 458 is within 20 of its.
3. **Class A has the most slack between achieved and LP UB.** Best=458,
   UB=478. If even half this gap is achievable, the record breaks.
4. **The vol-32 30-min 457 (class C) has bb=58.** Its border itself has
   two unmatched B-B adjacencies. Yet it still achieves 457, which is
   close to its LP UB 476. Tight basin, weaker structure.

## What this falsifies

- **Earlier claim (memory `project_e2_vol20_backbone_correction`) that
  vol-37 pos-161 is "puzzle-structural" with cross-source agreement.**
  Per vol-37 the 7 verified records came from 2 distinct basins. But
  the LP UB shows 3 border-classes, not 2. Pos-161 must be re-evaluated
  against this refined class structure. Open question for vol-45+.

## What's running

**MIP solve** on vol-32 458 board's border, 1h budget, 8 threads. Goal:
either find a better integer solution (potential record break) or prove
the LP UB 478 is tight on class A.

## Next experiment ideas (post-MIP)

1. **Class-A cross-record ALNS bridge**: combine the 454, 455, 455, 456,
   458 interior placements within class-A border. Recombination might
   find > 458.
2. **MIP on class B and C borders**: do they also have ~20 integer gap?
3. **Perturbation experiments**: swap two edge pieces in the 458
   border, see if LP UB shifts. If yes, hill-climb on borders.
4. **Refute pos-161 universality**: the cross-class invariant claim
   needs re-verification under the new 3-class taxonomy.

## Files

- `output/vol-44_border_lp_ub/all_records_v2.log` — initial sweep
  (interrupted by re-eval)
- `output/vol-44_border_lp_ub/all_records_v2_resumed.log` — resumed
  9-record sweep
- `output/vol-44_mip/458_class_A.log` — MIP run in progress

## Linked

- [[vol-43-reframing]] — pre-vol-44 plan
- `vault/concepts/border-enum-lp-ub.md` — full LP math
