# Optimization Ideas from a Blank Starting Position (2026-05-16)

User's prompt: "have you enumerated all your ideas for optimization
from a blank starting position?" — answer: NO, this session built on
existing infrastructure. This page enumerates ideas as if starting
fresh. A trace for the user when they return.

## Approach axes (each independent dimension)

1. **Search algorithm class**:
   - Backtracking (DFS, with propagation)
   - Local search (ALNS, SA, tabu, large neighborhood)
   - MIP / SAT (constraint encodings)
   - SDP / LP relaxations
   - Genetic / evolutionary
   - Reinforcement learning (self-play, MCTS)
   - Quantum-annealing-flavored (tested as dead-end before)
   - **Hybrid**: any pair-combination

2. **Constraint propagation**:
   - AC-3, NS-1, gacolor (built)
   - Edge-color BP / SP (built, refuted)
   - Lookahead-1 / k-consistency (untested)
   - Color-rare propagator (vol-7)
   - **Per-shell propagator** (untested, suggested by vol-74 CAS)

3. **Variable ordering** (which cell to fill next):
   - MRV (built)
   - Border-first (vol-13 measured + 11)
   - Hint-centric (vol-14 refuted)
   - Spiral-out (vol-14)
   - **Color-rare-first** (untested)
   - **Random + restart** (untested)

4. **Value ordering** (which piece to try):
   - LCV (built)
   - Random (built)
   - Edge-BP marginals (built, +0 lift)
   - Learned (NN, vol-29 = teacher)
   - **σ-cycle informed** (untested — requires oracle)

5. **Schedule discipline** (when to relax constraints):
   - Blackwood break-indexes (built)
   - Per-shell schedule (vol-74 CAS-greedy)
   - **Adaptive schedule** (untested)

6. **Topology / structure exploitation**:
   - Hamilton frames (vol-12, refuted as solved-up-to)
   - Fiedler / spectral (vol-65, bi-cluster only)
   - Group-theoretic σ-cycle moves (analyzed but not built)
   - **Mismatch homology β₁** (vol-18, refuted)

7. **Bound techniques**:
   - Border LP UB (built, tight on border)
   - Cluster MIP (built, tight only with defect-density)
   - PSM polytope (vol-65, gives 480 trivial)
   - **Lasserre hierarchy** (untested, days of work)
   - **Lagrangian decomposition** (untested)

## Untried approaches (high-value if blank slate)

### A. SDP relaxation of edge-matching
Semidefinite programming on the edge-matching constraint graph.
Would give a tighter UB than LP relaxation. Days of formulation
work; uncertain solver performance at canonical scale.

### B. Continuous-relaxation gradient descent
Treat piece-positions as continuous (soft assignments) and use
gradient descent on a smooth approximation of the edge-match
score. Then round to nearest discrete assignment. Standard
"continuous relaxation of combinatorial optimization" approach.
Untested on E2.

### C. RL self-play with curriculum learning
Train a neural network to play E2 placement game, starting from
small grid sizes (4×4, 6×6) and growing to canonical 16×16.
Months of training compute.

### D. Multi-agent search
Multiple independent solvers run in parallel, each exploring a
different basin (forced-corner-perm-class). Periodically swap
information. May discover basins our single-solver doesn't reach.

### E. Joint piece-set + cell-set MIP
Build a custom MIP that allows piece SWAPS between in-region and
out-of-region (not just permutations within region). This is the
specific tooling missing for σ-cycle moves.

### F. Group-theoretic σ-cycle enumeration
Compute the full S₂₅₆ orbit structure under the canonical 5-clue
constraint. Enumerate all "good" σ-cycles between basins. Use
character theory or Cayley graph traversal.

### G. Spectral basin discovery
Compute the spectrum of the σ-permutation Markov chain restricted
to high-score boards. Eigenvectors might reveal hidden basin
structure.

### H. Energy-based MCMC at high T
Run very-high-temperature MCMC explicitly to get acceptance of
σ-cycle sub-moves. T = 50-100 (much higher than usual). May
slowly mix between basins where T=1 cannot.

### I. Hint augmentation
What if we treat one of our high-score records as additional
"hints" and search for a 470 around it? The MIP rigidity proofs
say no halo ≤ 4 improvement exists, but with augmented hints maybe
the search explores different parts of state space.

### J. Symmetry-breaking constraints
Add explicit constraints that fix one σ-cycle representative per
orbit. May reduce search space to ~24× smaller (one per corner-perm
class).

## Approaches we've tried but could re-attempt with new tooling

- **Blackwood algorithm** (vol-15-17): need the Bucas C unrolled
  port to reach 295M nps single-thread. Currently at 367k nps —
  800× too slow.
- **Blackwood-then-CSP composition**: failed because Blackwood's
  break-indexes are unsound under joe_csp constraints (vol-15
  finding). Could be unblocked with a propagator-aware Blackwood.
- **CAS (Concentric Annular Solving)**: bounded at 433-436 due to
  piece-availability under greedy commit (vol-74). Joint shell-
  pair MIP (4× cost) might break this bound.

## Approaches refuted in vault

- Homotopy-ALNS (β₁ = 0 on records)
- BLGS Basin-Level Genetic Search (≤ 469)
- Hint-centric scan order
- σ-cycle subset application from oracle (always reduces score)
- Random-region MIPs (LP loose without defect density)

## Budget reality check

- Single agent on 8-core M1: ~80M-bench-fast nps × 5 min = 400 G nodes/min
- Blackwood reaches 295M nps × 1 month = 12 quadrillion nodes
- McGavin's 469 was reached after weeks-months of compute on his
  Blackwood port. Our compute budget is fundamentally smaller.

## What I would do tomorrow if starting fresh

1. **Port libblackwood** (Bucas's unrolled C) — would unlock the
  295M-nps engine that found 469 in the first place. ~2 weeks.
2. **Build joint-piece-set+cell-set MIP** — directly testable
  σ-cycle moves. ~1 week.
3. **SDP/Lasserre LP UB on canonical E2** — first sound UB <
  476. ~1 month research + tooling.
4. **Multi-agent search forcing all 24 corner perms** — covers
  full landscape. ~1 day to build, days-weeks to run.

The other ideas (RL, gradient, group-theoretic) are months of
research-engineering work each.

## Standing 459 = real ceiling under current tooling

Everything in the proven-rigid set tonight (vols 80-101) is
SOUND mathematics. The 459 ceiling is not "haven't searched
enough" — it's "structurally caged by σ-cycle indecomposability
+ MIP rigidity + corner-perm class commitment". Beating it
requires structural-new tooling, not more compute on existing
methods.
