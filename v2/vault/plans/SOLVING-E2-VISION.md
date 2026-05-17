# Solving Eternity II — strategic vision (vol-123)

User clarified 2026-05-17: goal is finding **the way** to solve the puzzle,
not incremental score improvements. Cloud compute on the table if a real
algorithmic candidate needs it.

This document organizes the strategic paths.

## Status (as of vol-123)

- Community ceiling: **469/480** (McGavin 2020 via Blackwood + 12 days compute).
- Our standing: **459 matched-edges, 458 strict-canonical (5/5 hints obeyed)**.
- 122 volumes of exploration, ~16 documented refutations of attack operators,
  rigidity theorem proven for canonical basins.
- The puzzle has NOT been publicly solved in 16+ years since the 2008 contest ended.

## What "the way" means concretely

A METHOD that produces a 480/480 board on canonical 16×16 Selby-Riordan
E2 with 5/5 canonical hints. Not a record-break (471, 473, 478) — the
*solve*.

## Paths organized by theoretical foundation

### Path A — Statistical-mechanics methods

**A1. Survey Propagation (Braunstein-Mézard-Zecchina 2002)**.
SP solves hard random k-SAT near the SAT/UNSAT threshold where every other
algorithm fails. E2's permutation+matching constraints aren't random k-SAT,
but the algorithm's *core idea* (passing surveys over message clusters)
might generalize.
  - **Why it could solve E2**: SP exploits the "clustered" structure of
    near-threshold solutions. E2 has empirically clustered basins (vols
    18-22, 65-99 cooperativity findings).
  - **Why it might not**: E2 isn't random k-SAT; the global piece-uniqueness
    constraint is hard for message-passing.
  - **Effort to validate**: 1-2 weeks. Implementation exists (thibsej GitHub).
  - **Cloud-scale resources needed**: minimal — SP is near-linear.

**A2. Backtracking Survey Propagation (Marino-Parisi-Ricci-Tersenghi 2016)**.
Combines SP with backtracking to escape SP's failure modes.
  - **Why it could solve E2**: combines best of both worlds.
  - **Effort**: 2-3 weeks if A1 works.

**A3. Replica-symmetry-breaking analysis.**
Formal RSB on E2 partition function would tell us whether it's solvable
at all by polynomial-time message-passing. If RSB-1 (one-step) suffices,
SP works; if higher RSB needed, message-passing fundamentally insufficient.
  - **Effort**: math-heavy, multi-week.

### Path B — Tensor-network methods

**B1. W1 PEPS-Lagrangian (current track)**.
2D PEPS with Lagrangian on piece-uniqueness. Solves 4×4 (1s) and 6×6 (5min).
Canonical 16×16 untested at scale.
  - **Why it could solve E2**: properly handles global piece constraint.
    No theoretical reason it can't scale.
  - **Why it might not**: chi-truncation may lose too much information.
    PEPS contraction is provably approximate.
  - **Effort**: 2-4 weeks more.
  - **Cloud-scale resources needed**: GPU + 64-128 GB RAM for chi=256+
    on canonical.

**B2. Hyperoptimized PEPS (Gray-Chan 2024 directly)**.
The actual paper formulation. We adapted it to E2 in W1; pure Gray-Chan
might work better for the *partition function* counting but harder for
piece-extraction.
  - **Effort**: 1-2 weeks variant of B1.

### Path C — Algebraic methods

**C1. W3 Kovalsky-Glasner-Basri Vandermonde-LP (never built)**.
Exponential change of variables T_i = e^{t_i}, polynomial color
constraints, Birkhoff-von Neumann LP relaxation iterated. Validated up
to 8×8 in the 2014 paper; never canonical-scale.
  - **Why it could solve E2**: completely different relaxation — algebraic
    rather than statistical.
  - **Effort**: 2-3 weeks to build + validate.

**C2. Decision procedures (CDCL with custom propagators)**.
Vol-25 found vol-12/14 propagators marginal. A new theory-aware propagator
(piece-supply Hall, color-pair Hall) might give multiplicative pruning
gains.
  - **Effort**: 1-2 weeks per propagator.

### Path D — Brute force at scale

**D1. blackwood-fast (vol-106) at sustained scale**.
84M nps single-thread. With 32 cores × 1 year = 8.4e15 placements. The
canonical state space is 256! × 4^256 ≈ 10^658. Brute force won't reach
0 mismatches but might do better than 469 if pruners are aggressive.
  - **Why it could solve E2**: McGavin used 295M nps for 12 days to get 469.
    We have 84M nps with parallelism.
  - **Why it might not**: McGavin's 469 was the basin McGavin's algorithm
    naturally led to; pushing further is exponentially harder.
  - **Effort**: ongoing.

**D2. DLX (Algorithm X, Knuth) for exact cover at canonical scale**.
A4 in INVENTIONS_BACKLOG. Never built.
  - **Why it could solve E2**: DLX is provably faster than CSP backtracking
    for exact cover.
  - **Effort**: ~3 days for canonical scale.

### Path E — ML-driven

**E1. RL self-play (PPO + value network)**.
Train an agent to pick value-order during CSP. Reward = max depth/score.
Multi-week.

**E2. GFlowNet-amortized sampling (Kim et al. AISTATS 2025)**.
Direct generation of solutions via flow networks. Multi-week.

**E3. Discrete diffusion (SEDD)**.
Generate boards via reverse diffusion. Multi-week.

### Path F — Hybrid / clever combinations

**F1. SP + tensor-network value-order for CSP**.
Use SP marginals OR PEPS marginals as the value-order heuristic for our
CSP backtracker. If the marginals are *good enough*, the CSP solves the
rest in tractable time.
  - **Why it could solve E2**: leverages the theoretical strength of SP/PEPS
    without requiring them to solve directly.
  - **Effort**: 1 week to wire up after SP or PEPS marginals are dumped.

**F2. Specialized propagators driven by W7 frozen-variable analysis**.
W7 showed 459 basin has 1 frozen cell. Frozen-cell-aware propagators
could fix those cells and propagate. Marginal contribution likely.

## Priority recommendation (METHOD-finding, not record-breaking)

Days 1-7: **Complete W1 canonical-scale validation**.
  - Tune chi (16 → 64 → 256+ on cloud).
  - If converges + marginals correlate with truth → big win.
  - Effort: 7 days CPU + 2 days cloud GPU at chi=256+.

Days 8-14: **Build W2 Survey Propagation on E2 factor graph**.
  - Encode E2 CNF via sat-encoder.
  - Adapt thibsej/SurveyPropagation to consume our CNF.
  - Test SP convergence near canonical's threshold.

Days 15-21: **Build W3 Kovalsky-Glasner Vandermonde-LP**.
  - Implement Julia or Python prototype.
  - Validate on 4×4, 8×8.
  - Scale to canonical.

Days 22-28: **F1 hybrid pipelines**.
  - Best of W1/W2/W3 marginals → CSP value-order → CSP solve.
  - This is the path most likely to actually produce a solved board.

If any path produces marginals or partial that exceed 469 → focus there.

## Cloud compute needs (when bottleneck)

- **W1 canonical**: 64-128 GB RAM machine for chi=256 PEPS. A1 instance class
  on AWS/GCP/Azure. ~$1-2/hour. Estimate: ~50 hours = $50-100.
- **W2 SP**: minimal (near-linear). Local laptop sufficient.
- **W3 Vandermonde-LP**: medium (LP at scale). Local sufficient unless
  iteration count explodes.
- **RL/GFlowNet**: GPU training. ~$0.5-2/hour GPU. Days of training.

## Why this is plausible

E2 has been unsolved publicly for 16+ years not because it's impossible
(it has at least the canonical Selby-Riordan-Tilling solution) but because
the search space is astronomical (10^658). The known methods (CSP, ALNS,
Blackwood, GA, MCMC) all fail near 469.

A fundamentally new algorithmic angle — particularly one with theoretical
backing like SP for near-threshold k-SAT — has a non-trivial chance to
crack it. The probability of any single path solving is maybe 5-20%;
the probability of *some* of A+B+C+E succeeding is higher.

## Linked

- [[../concepts/web-roam-2026-05-17]] (W-series candidates)
- [[../concepts/w1-was-it-promising]] (W1 honest assessment)
- [[INVENTIONS_BACKLOG]] (W1-W8 + others)
- [[CURRENT-VOL]]
