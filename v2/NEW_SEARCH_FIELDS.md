# New search fields for an unsolved Eternity II attack

Date: 2026-05-13

This is a deliberately open-ended research map. Existing code and notes are evidence, not a cage.

The innovation-process frame from Crowdworx is useful operationally: scout weak signals, define strategic search fields, run idea challenges, evaluate with explicit gates, then execute only the ideas whose metrics move. For this puzzle, that means no more vague "try AI" or "try waves". Every strange representation must become a measurable solver signal.

## What the crawl says

External anchors:

- Crowdworx frames innovation as strategy -> ideation -> evaluation -> execution, with trend scouting, search fields, idea challenges, stage gates, and measurable project work.
- Wauters et al. describe Eternity II as a max-edge optimization problem and report that multi-objective hyper-heuristics beat default-objective-only local search.
- Salassa et al. show MILP and Max-Clique formulations are too hard directly but useful as decompositions and very large neighborhoods.
- Population annealing literature says rough spin-glass landscapes can be attacked by resampling whole populations across temperature schedules.
- GNN-for-Max-CSP literature is relevant, but should be used as a policy or proposal generator, not trusted as a standalone solver.

Local anchors:

- Static math is mostly dead: PCA, static Laplacian, BP, and MPS relaxations are flat or paramagnetic.
- Dynamic structure is alive: CP schedule determines piece-to-region assignment; same-schedule ALNS mostly shuffles within regions.
- The defect geometry matters: high-scoring boards concentrate mismatches near the top.
- Current ALNS plateaus quickly; same fixed board needs different basin moves, not more wall-clock.

## Strategic search fields

### Field A: Defect signal dynamics

View a board as a 16x16 defect image and as row/column waveforms.

Hypothesis: 469-class boards have a distinct defect spectrum, not just fewer defects. If true, ALNS should optimize toward the spectrum before it optimizes exact edge matches.

Prototype added:

- `scripts/board_signal_probe.py`
- outputs mismatch PGM images, row/column profiles, radial FFT energy, and optional WAV sonification.

First measurement:

| board | score | row profile | low FFT | mid FFT | high FFT |
|---|---:|---|---:|---:|---:|
| our v17 chunk 19 | 453 | `[4,17,12,6,8,7,0,...]` | 0.370 | 0.300 | 0.330 |
| community McGavin | 469 | `[1,2,4,7,8,0,0,...]` | 0.298 | 0.395 | 0.307 |

Interpretation: the 469 is not just "top cluster smaller"; it has a smoother ramp into rows 2-4 and different spectral mass. That can become a target function.

Next build:

- Corpus signal atlas: compute these features for every `output/community_corpus/*.json` and every local 440+ board.
- Train no model first. Cluster by FFT rings, row profile, largest component, and score.
- If 469s form a separable cluster, add `DefectSpectrumAcceptance`: accept iso-score moves only if they move the defect signal toward the 469 centroid.

Stage gate: if signal features predict score/basin better than raw mismatch count on held-out boards, wire into ALNS.

### Field B: Population annealing over whole boards

ALNS/SA currently walks one board. Population annealing treats the run as an evolving ensemble, resampling boards by energy and preserving diversity.

Why this is new here:

- Parallel tempering swaps chains. Population annealing resamples successful states and kills unproductive lineages.
- E2 has strong basin lock-in; resampling can amplify rare partial basin escapes without waiting for one chain to discover everything.

Algorithm sketch:

1. Start with N Blackwood partials from different schedules/noise seeds.
2. Fill each to a board.
3. At beta steps, run K local moves per board.
4. Weight by composite energy:
   - edge mismatches
   - 469 defect-spectrum distance
   - region piece-set novelty
   - rare-color ring consistency
5. Resample with diversity caps.
6. Periodically run CP/MaxSAT repair on the elite frontier only.

Stage gate: in 1 hour, PA must produce either higher best score than the same CPU budget ALNS portfolio, or a demonstrably different piece-region assignment.

### Field C: Learned proposal generator, not learned solver

A neural solver is likely too weak. A proposal generator may be useful.

Represent the puzzle as a heterogeneous graph:

- cell nodes
- piece nodes
- color nodes
- edge-slot nodes
- constraints as hyperedges

Train self-supervised on:

- community 469/470/480 boards
- local 440-456 boards
- generated smaller puzzles where solutions are known

Output:

- probabilities for piece-region assignment
- probabilities for destroy sets
- probabilities for swap candidates

Use it only to propose ALNS moves. Score and feasibility remain classical.

Stage gate: learned proposals must improve "new best per 1,000 repairs" over random/worst-window/conflict-driven on fixed boards.

### Field D: Piece-region transport

The key structural finding is that same-schedule ALNS conserves piece sets per row-region. So the unsolved move is not local repair; it is moving the correct pieces across regional barriers.

Model this as optimal transport:

- source: current region piece multiset
- target: empirical region multiset distribution from 469/470 boards
- cost: boundary compatibility, color demand, and known local score loss

Then execute a controlled region transport:

1. choose 10-30 pieces to move between regions
2. solve a min-cost matching for replacement pieces
3. repair the boundary with SA/CP
4. accept temporary large score drops if the region assignment moves toward 469-class transport distance

Stage gate: create a board with lower immediate score but higher post-ALNS ceiling than the original.

### Field E: Audio/signal-guided human-in-the-loop

Sound is not magic. But audio can expose patterns humans miss in tables.

Concrete use:

- row scan pitch = row defect count
- column scan pitch = column defect count
- timbre/noise = largest component size or high-frequency energy

If 469-class boards have an audible "signature", use it for triage and anomaly spotting across thousands of runs. This is a research instrument, not a solver.

Stage gate: if humans or simple classifiers can distinguish 469-ish vs 453-ish boards from sound/signal features, keep it. If not, kill it.

### Field F: Constraint holography

Static BP/MPS failed because global piece uniqueness is the real rigidity. Build a "hologram" of that global constraint as a low-rank state.

Idea:

- maintain a vector of piece-supply shadow prices
- after each partial solve/ALNS batch, update prices by over/under-use pressure
- inject prices into CP value ordering and local-search energy

This is like Lagrangian relaxation of all-different, but tuned online by the actual basin trajectory.

Stage gate: shadow prices must change piece-region assignments, not merely reorder equivalent moves.

## Immediate execution plan

1. Build the signal atlas over local and community boards.
2. Test whether FFT/row-profile features separate 469/470 boards from 440-456 boards.
3. If yes, implement `DefectSpectrumAcceptance` as an ALNS neutral-move criterion.
4. In parallel, design a minimal population-annealing runner using whole boards and fixed-step deterministic repair.
5. Only after those two are measured, decide whether to build GNN proposals or piece-region transport first.

## Working rule

Every representation must answer this:

> Does it produce a move, an acceptance rule, a schedule, or a pruning certificate?

If it only produces a beautiful picture, it is instrumentation. If it changes which states we visit, it is a solver component.
