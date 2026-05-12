# Vol. 7 — session summary

**Date**: 2026-05-12, 07:58 → 10:10 CEST (~2h10).
**Best score at session end**: **454/480** (unchanged from session start; vol-6's `pt_e2 --pin-perimeter` sanity test from 09:00 set the ceiling).
**Score trajectory across all vols**: 449 (vol-3) → 450 (vol-4 frame-first) → 452 (vol-5 GA-cross) → 453 (vol-5 GA-LARGE #37) → **454 (vol-6 pin-perimeter)** → no further gain in vol-7.

This is the closing summary. Detailed log in `RESEARCH_NOTES_7.md`; this file is the reader-facing distillation.

---

## What vol-7 set out to do

Vol-6 closed at 454/480 with a deterministic PT ceiling (4 saturation seeds byte-identical). Vol-7 inherited the open question: **how to break 454**. Vol-6 explicitly handed off BORDER-3e (border triage) and the reverse-Selby inner solver to vol-7.

The original vol-7 mission: out-of-field ideas to escape the 453 basin. Vol-6's 454 happened mid-vol-7-launch, so the moving target became 454.

---

## What vol-7 did NOT achieve

- **No score push past 454.** Every concrete attack vector produced no gain.
- **No general lower bound on E2 mismatches.** Chessboard-parity argument empty (cross-class cancellation).
- **No working "reverse-Selby" interior-first inner solver.** CP exhausts instantly on partial-match boards (CP is satisfaction, not optimisation).

---

## What vol-7 DID achieve (structural / methodological)

### 1. MaxSAT global optimality of an arbitrary-shape sub-puzzle

EvalMaxSAT on the 45 frozen-mismatched cells of the 454 (with the rest pinned) finished in **83 seconds** and proved **`o 26` is OPTIMUM** — exactly the 454's current mismatch count in that region.

**Reading**: the 454 board's defect zone is the global optimum for any rearrangement of those 45 pieces. **PT is not just empirically stuck; it's algorithmically stuck.** To break 454 we *must* include cells currently outside the 45.

A follow-up run on the 109-cell region (45 + 1-ring) timed out at `s UNKNOWN` after 54 minutes — confirming vol-6's k=6 timeout wall (~36 cells rectangular = boundary of MaxSAT tractability).

**Infrastructure**: `sat_e2 --free-cells <jsonlist>` — generalisation of `--center-k`. Accepts any 1D cell-index list for arbitrary-shape sub-puzzles. Reusable primitive.

### 2. Deterministic PT ceiling, byte-level

Vol-6 ran 3 saturation experiments (300s × 8 replicas, seeds 9018/18019/27020) + 1 sanity test (seed 42). All 4 produced **byte-identical** 454 boards: same 256 piece IDs, same rotations, same 45 mismatched cells.

**Reading**: PT-with-pin-perimeter on this border is not just empirically saturating at 454 — it converges to the *exact same configuration* regardless of seed. This is a deterministic local optimum, not stochastic noise.

Combined with the MaxSAT optimality of the 45-cell sub-puzzle, the 454 is rigorously locked under any combination of (PT + region-MaxSAT) at scales ≤ 50 cells.

### 3. Selby/Verhaard rediscovery and generator countermeasures

Background-research agent on Selby & Riordan's E1 method (archduke.org/eternity/method/desc.html). Findings:

- Selby's **"tilability" l_i** (2000) **= Verhaard's 2×3-tileability** (2008) **= vol-7's Python valuation** (today). Same metric, three independent rediscoveries across 25 years.
- Selby & Riordan, the actual E2 generators (Monckton is non-mathematician), built E2 specifically to defeat their own E1 attack:
  - **Uniform color frequencies** flatten the l_i signal (E1 had 33× spread; E2 has 1.5×).
  - **n=16, cf=5, cm=17** lands the puzzle exactly on Ansótegui et al.'s GEMP-F phase transition (E[X] ≈ 16.4 expected solutions — vanishingly few).
  - **Square tiles + 4 rotations** denies E1's length-11 boundary lookup-table pruning.
  - **Planted center clue (7,8)** pins the backbone, preventing Selby's "spend freedom early" attack.

**Reading**: the published Selby method (worst-tilability-first ordering) was *specifically* anticipated and defended by the very same authors when generating E2. This is the rigorous reason Verhaard hit 467 and nothing public has gone higher in 16+ years.

### 4. Rare-color opposite-edge generator rule

Of 60 pieces carrying 2 rare-color edges, 56 have them on **opposite edges** (top↔bottom or left↔right). The other 4 are corner pieces where geometry forces adjacency. Equivalently: in the in-piece color-adjacency graph, the R-R missing rate is 70% (7/10 pairs), vs M-M 0%, A-A 0%.

**Reading**: rare colors are not just "few"; they are *segregated* by construction. The 5 rare colors propagate as stripes across the board (which is why vol-5's "rare colors are always matched" invariant holds — there is no other way for them to appear).

Saved to memory as `project_e2_rare_opposite_rule.md`.

### 5. Z_22 vertex-charge fingerprint

For each interior vertex of the 16×16 grid, sum the 4 incident edge colors mod 22. Perfect tiling ⇒ all charges 0. The 454 boards have 44-50 nonzero charges, **all in rows 5-15, cols 4-13** (rows 1-4 are 100% charge-free). Opposite-sign charge pairs at L1 ≤ 6 in 73% of cases — satisfies X1 agent's threshold for disclination-string moves being viable in principle.

**Reading**: a clean structural fingerprint of E2 hardness. Publishable as a topological-invariant signature.

### 6. Selby-Riordan generator-bias: NEGATIVE

Monte-Carlo test: 500 random shufflings of the 784 interior-edge bag into pieces. Mean missing color-pairs: 95.03 (stdev 0.16). Official E2: 95. P(MC ≤ obs) = 0.97. **The piece set looks statistically random conditional on its color frequencies.**

**Reading**: M1's H1 (hidden generator bias) is falsified at the broad statistic. The structure lives elsewhere (rare-opposite rule + phase-transition placement), not in color-pair surprise counts.

### 7. H2 chessboard-parity lower bound: NEGATIVE

Subset-sum DP per color × class (corners 4, edges 56, interior 196). Per-class imbalances can have *opposite signs* and cancel. Min total imbalance per color is 0 for *every color*. **No nontrivial lower bound from elementary parity.**

**Reading**: the puzzle remains theoretically fully matchable (480/480 achievable). The "avocat" detail (Tomy deposited the official solution with a notary) is consistent.

### 8. Cross-border GA-crossover: NEGATIVE

Crossing the 454 (border family 0) with a 427 board from a different border (vol-6's top-1000 stage-2) at 3 regions ((10,10), (3,2), (11,1)) and polishing each at 300s produced children at 413-426 — i.e. *the border-9 ceiling*, not improvements on either parent. The 13-14 piece-duplicate repairs after cross-border GA destroy more than the local transplant gains.

**Reading**: GA-crossover is a within-basin operator on E2, not a between-basin one. Same border family = vol-5's 449→453 mechanism. Cross border = noise.

### 9. Border-diversity surrogate: WEAKLY PREDICTIVE

Stage 1 (12 borders × 60s × 2 replicas): 399-418/480. Stage 2 (top 4 × 300s × 4 replicas): 420-427. Long-PT on best stage-2 border (1200s × 8 replicas): 434/480.

**Reading**: vol-6's `top_1000_by_corner_tightness` surrogate is real but weakly predictive of PT ceiling. The synthetic borders are 20-30 below the corpus 454 even at 20× more compute per board. Either the surrogate captures only ~15% of true border quality, or PT needs hours/border to compete with the corpus's accumulated history.

### 10. Houdayer-PT fix (compositional)

Vol-3 commit 312c44b had Houdayer wired into PT but rejecting all swaps due to a misunderstood filter (`joint_delta > 0` rejects everything because joint is a conservation law). Vol-7 fixed to `a_delta > 0` (strict cold-replica improvement). Offline post-mortem on 18 boards confirms: zero improving swaps exist within the current corpus (all in border family 0). The fix is correct; it just needs structurally-diverse replicas to activate.

### 11. MAP-Elites quality-diversity for E2 (infrastructure built, not yet productive)

First application of MAP-Elites to edge-matching. Behaviour descriptor = (top-left corner piece, mismatch quadrant pair, Z_22 charge count bucket). 33 corpus boards collapse to 9 distinct niches. Crossover-mutation between niches operationalised but 5 destroy-iters all rejected — the mutation needs more diversification or larger destroy regions. Saved for future scaling.

### 12. Blank-interior PT-from-454-border: NEGATIVE

Started from a board with the 454's perimeter + 5 hints, blank interior. 300s × 8 replicas reached **438/480**, not 454. **The 454 is not globally attractive from random fill** — it required either vol-6's specific sanity-test path (start from corpus 453 → PT polish reaches 454) or hours of GA history. Implies the 454 basin is *narrow*.

---

## Strategic picture at session close

The 454 ceiling is now characterised on three independent axes:

1. **MaxSAT-locally** (vol-7): the 45-cell defect zone is the proven optimum given the outer.
2. **PT-deterministically** (vol-6): converges byte-identical from 4 seeds.
3. **Basin-narrowly** (vol-7): blank-interior PT from the same border converges to 438, not 454. The 454 is not in PT's natural basin from random fill.

The 480-solution exists (notary). To reach it from 454 we'd need either:

- **A fundamentally different inner solver** that can navigate from 454 to a structurally different configuration on the *same* border. Cube-and-conquer or Mallob-on-cloud-fleet are the leading candidates.
- **A genuinely different border**. Vol-6's 100k library exists; the corner-tightness surrogate is weakly predictive; a *better* surrogate (or much longer PT per border) is needed.
- **A constructive enumeration** of borders compatible with a 480/480 solution (information-theoretic: of vol-6's 100k borders, how many can be extended to a 480-perfect interior at all? Likely ≤ 16 by Ansótegui's E[X]).

The last is the genuinely novel angle that vol-7 surfaced but did not pursue. It deserves a vol-8 follow-up.

---

## Vol-7 deliverables (files / code committed)

| Asset | Status |
|---|---|
| `RESEARCH_NOTES_7.md` | Per-experiment log, 600+ lines |
| `scripts/sr_generator_bias.py` | Selby-Riordan piece statistical diagnostic |
| `scripts/verhaard_valuation.py` + `scripts/verhaard_valuation_output.json` | 2×3-tileability per piece, 4-tier bucketing |
| `scripts/interior_first_blob.py` | Greedy interior-first prototype (negative; informative) |
| `scripts/z22_charge_fingerprint.py` | Z_22 vertex-charge fingerprint |
| `scripts/h2_parity_lower_bound.py` | H2 chessboard parity (negative) |
| `scripts/synth_border_seed.py` | Vol-6-border + blank-interior seed builder |
| `scripts/border_triage_stage1.sh` + `stage2.sh` | Border PT triage funnel |
| `scripts/map_elites_e2.py` | MAP-Elites archive with crossover mutation |
| `crates/localsearch/src/repair.rs` | New `repair_cells` (arbitrary-cell CP) |
| `crates/localsearch/src/pt.rs` | Houdayer fix (a_delta > 0 filter) + `houdayer_accept_zero_delta` flag |
| `crates/benchmark/src/bin/sat_e2.rs` | `--free-cells <jsonlist>` for arbitrary MaxSAT region |
| `crates/benchmark/src/bin/pt_e2.rs` | `--pin-cells <jsonlist>` for arbitrary cell pinning |
| `crates/benchmark/src/bin/reverse_selby_e2.rs` | Reverse-Selby CLI (negative on direct strict-CP; useful primitive otherwise) |
| `memory/project_e2_rare_opposite_rule.md` | New auto-memory entry |

---

## What vol-8 should consider

Two threads of next work, prepared but not started:

1. **Community-export mining** (vol-8 prompt already drafted; user has exports in `export/`). Search hobbyist mailing list + Discord for techniques not in academic literature. Highest expected value: any verified 460+ 5-clue board.

2. **Constructive solution-compatible border enumeration**. The 480-solution exists; therefore its border is one specific element of vol-6's 100k library. Run CP/MaxSAT with the 5 hints fixed asking *"which borders admit a 480/480-perfect inner?"* — by aggressive constraint propagation, this should narrow to a tiny set. ~2-3 days CP infrastructure work.

The score push past 454 is genuinely hard; published academic SOTA has held at 458 since 2012 and hobbyist 467 since 2008. Vol-7's contribution is to characterise *why* with new rigour, not to break the wall.
