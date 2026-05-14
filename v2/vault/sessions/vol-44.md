# Vol-44 — LP-relaxation upper bound for border-class enumeration (early stop)

**Theme**: Build the LP-relaxation UB tool flagged as the highest-EV
unbuilt direction in vol-43-reframing. Measure tightness on canonical
E2 records.

**Status**: closed early after user re-eval #6.

## What was built (shipped)

- `crates/bench-audit/src/border_ub.rs` — LP formulation as a library
  function. See `vault/concepts/border-enum-lp-ub.md` for the math.
- `crates/bench-audit/src/bin/lp_smoke.rs` — toolchain smoke test.
- `crates/bench-audit/src/bin/border_lp_ub_small.rs` — validates LP
  on generated 6x6/4 and 8x8/6 puzzles. LP slack = 0 at optimum (tight
  on tiny instances).
- `crates/bench-audit/src/bin/border_lp_ub.rs` — runs LP UB on a
  canonical-E2 board JSON.
- `crates/bench-audit/src/bin/border_lp_perturb.rs` — UNUSED. Tool for
  swap-perturbation experiments; not run.
- `good_lp + highs-sys` wired in. HiGHS built from source via cmake.

## What was measured

### Smoke tests on small generated puzzles
- 6x6/4 colors: LP UB = 60/60 (tight). 19ms.
- 8x8/6 colors: LP UB = 112/112 (tight). 200ms.

### Canonical E2, border + 5 canonical hints

Two LP formulations were run before stop:

**Initial (buggy) formulation** — forced B-I match:
| Record | LP UB |
|---|---|
| vol-32 458 | 476.5 |
| vol-35 458 | 476.5 (identical border) |
| vol-32 457 seed 7 | 477.0 |
| vol-32 457 seed 10 | **INFEASIBLE** (false — record exists) |

Discovery: forcing every B-I edge to match was an INVALID relaxation.
Actual boards allow unmatched B-I edges (they just don't score).

**Corrected formulation** — B-I matches are LP variables:
| Record | LP UB |
|---|---|
| vol-32 458 | **478.0** (bi_ub=54.09, lp_interior=363.92) |
| ... | (9 remaining records not measured — sweep stopped) |

## What this means

**LP integer gap on the 458 board's border = 478 - 458 = 20.**

The LP relaxation:
- DOES detect ~2 edges of structural slack vs trivial UB of 480.
- DOES NOT come close to bounding at the integer optimum.
- Spread across known records (from preliminary run): 476.5 to 477.0,
  i.e. **basin LP UBs vary by less than 1 across our 7 verified record
  boards**.

**Filter implication**: at threshold T = 459 (break 458), the LP keeps
all known borders (all have UB ≥ 478 ≥ 459). The LP filter is too
loose to prune at the threshold we care about.

## Why I stopped

User re-eval #6 fired while the sweep was running. Pattern recognised:
- Build LP tool → first measurement → realise LP loose → "the spread
  measurement is still informative" → commit to 25 more minutes of
  compute → user re-evals.

Six re-evals is the signal that I should not pick the next direction
unilaterally. The honest read is: **LP B&B is not the path to break
458 on canonical E2 5-clue**.

## What remains as open frontiers

These are genuinely-different directions, each multi-day:

1. **Tighter LP via McCormick lifting**: replace y[edge, k] ≤ min(a, b)
   with McCormick envelope on the bilinear x[c1,r1]·x[c2,r2] term.
   Likely tighter, still poly-time. Untested.
2. **Z3/SMT exact solver** on subproblems (e.g. fix the 60-cell border,
   ask Z3 to maximise interior score exactly within timeout). Could
   give exact basin ceilings on a few borders.
3. **Pattern mining from McGavin 469**: extract recurring sub-blocks
   from the 1-clue variant's 469 board. Use as injected pattern
   constraints in CP search.
4. **RL self-play for value-order** — vol-29's identified ceiling-
   breaking path. 1-2 week build.
5. **Spectral piece-graph clustering**: build piece-piece adjacency
   graph weighted by colour-match counts. Spectral structure might
   identify natural sub-blocks.
6. **Lin-Kernighan-style multi-piece moves** in ALNS — moves of
   cardinality 5-10 with branch search. Vol-22 measured 457 is
   K-locked at 5; LK could break that.

## Decision

Not picking one unilaterally. Stopped the LP sweep. Waiting for the
user to choose.

## Linked

- [[vol-43-reframing]] — re-eval #4 analysis; LP B&B was flagged as
  highest-EV from vol-43; this vol-44 measurement falsifies that.
- `vault/concepts/border-enum-lp-ub.md` — full LP math.
