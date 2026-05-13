# Vol-17 — cross-domain reframings of Eternity II

**Date**: 2026-05-13. **Premise the user issued**: "we are trying to
achieve something NO one has ever done". So the filter is NOT "has
this been published" — every published direction was either tried
(BP, SP, MaxSAT, frame-first, ALNS, Blackwood) or ruled out by 3
independent agents (SP, IsingFormer, GPU/FPGA SAT — `project_e2_dead_ends`).
The filter is "is this lens a *direction the field has not actually
pointed at this puzzle*, and would a 1-2 day PoC tell us something".

The HBR garden / Crowdworx stage-gate lens applied here means: I'm
allowed to plant seeds that *might* die. The cost of trying a strange
framing is days, not weeks. The reward is breaking 456.

---

## What we've already framed E2 as (so don't repeat)

- **CSP / Backtracker over (piece, rotation, position)** — solver-engine.
- **Boltzmann distribution at finite T** — ALNS with SA acceptance.
- **Replica-coupled chains** — PT (vol-6, vol-14, vol-17 ALNS-PT).
- **Factor graph for BP** — vol-11/12 edge-color BP.
- **SAT / WCNF for solvers** — z3, EvalMaxSAT (dead end).
- **Articulation-point hypergraph** — HingeDestroy.
- **Spin glass with quenched disorder** — implicit in PT, never made explicit.
- **Connected-component repair** — ComponentDestroy.
- **2D tensor network / MPS contraction** — vol-13 (refuted: piece uniqueness is the binding constraint, not local matching).

## What we have NOT framed it as

Below are 7 lenses I have not seen tried — neither in our memory, nor
in the search results above. For each: the analogy, the math operation
it suggests, the PoC, and an honest EV.

---

### R1. Puzzle as a 2D *image* whose colors are a *latent* the
generative model must inpaint

**Analogy**. Forget that the colors are constraints. Treat the
constructed board as a 16×16×4 image (each cell has N/E/S/W color
channels). A partial board with 80 mismatches is a partial image
with 80 wrong pixels. **A diffusion model trained on the 1.2k+ near-
solutions in our corpus can learn the *manifold of high-score boards*
and inpaint the mismatch region toward it.**

**Math operation**. Score-based generative model (DDPM) on the
color-tensor representation; conditional inpainting on the
high-mismatch pixels with the rest of the board as context. The
"denoising" step is a learned destroy-and-repair operator that knows
the joint distribution of high-score boards.

**Why this is different from IsingFormer (dead end)**.
- IsingFormer learned MCMC proposals on Ising spins (binary), trained
  from PT samples on the SAME problem — circular, plateau-reproducing.
- Here we'd train on the 1.2k+ community near-solutions which sit on
  the 465-469 manifold we've *never reached*. The model learns from
  data **above** our ceiling. It can pull us toward an unseen basin.
- Tokenization explosion is real but manageable: 256×4 = 1024 token
  positions, vocab = 23 colors per side. That's a 4k-token sequence,
  smaller than a Stable Diffusion image.

**PoC**. 1-2 days. (i) Encode all 1.2k+ corpus boards as 16×16×4
color tensors. (ii) Train a small UNet (~5M params) as a denoising
diffusion with edge-validity loss (color compatibility as
regularizer). (iii) Use it as a destroy-repair operator inside ALNS:
mask the worst-band, sample from the diffusion conditional on the
rest, project to valid placements via piece-uniqueness repair.

**EV**. Medium-high. Even if the diffusion can't sample valid boards,
the *learned mismatch geometry* (where 469-class boards differ from
our 453-class boards) is itself a signal. We've never compared
manifolds — only individual boards.

**Failure mode to watch**. Piece-uniqueness is hard to encode as a
diff-loss; samples will be invalid in tile-count. Mitigation: use the
diffusion to guide a destroy-mask + permutation matching repair, not
as a one-shot sampler.

---

### R2. Puzzle as a *waveguide* whose colors are phases

**Analogy**. Each piece edge has a *phase* in [0, 2π) = (color × 2π/23).
A matched edge is a phase agreement. **The total "interference energy"
of a board is a sum over edges of (1 − cos(Δφ)).** Minimum interference
= zero phase difference = matched edges. **The board is a 2D phase-
field problem.**

**Math operation**. Treat the 480 edges as oscillators with phases
locked to piece colors. Solve `min Σ_edges (1 − cos(φ_a − φ_b))`. This
is a XY-model / Kuramoto-oscillator energy. The XY model on a 2D
lattice has well-studied vortex / spin-wave excitations.

**Why this is different from Ising/spin-glass framing**.
- Ising = ±1. Our colors are 23, not binary.
- XY model = continuous phase. Color = 23-state ≠ continuous. But
  the **quotient relaxation** "treat colors as elements of Z/23 with
  a Δ-cost on the circle" is a *natural* embedding of edge-matching
  into a Potts model that the spin-glass community has not seen.

**PoC**. 1 day. Implement the q-state clock-model (Z/23) on the
puzzle's edge graph. Use Wolff-cluster Monte Carlo, which is the
gold-standard algorithm for clock/Potts at finite T. Wolff cluster
moves on Z/23 invert spin-aligned cluster en masse — **this is the
literal cross-domain analog of HoudayerDestroy** but with the
mathematically correct cluster definition for the Potts model.

**EV**. High. Houdayer in vol-17 plan was already on the table. This
gives it a principled definition (Wolff cluster on the dual edge
graph) instead of our hand-rolled "swap cluster". Wolff-cluster has
been studied on disordered Potts for 30 years; we'd be the first to
apply it to E2.

**Failure mode**. Z/23 isn't a Lie group; the "rotate phase by π"
doesn't preserve the puzzle (we can't recolor edges). Wolff moves
must be restricted to cluster *flips* in the symmetric-difference of
two boards (à la Houdayer). That's still well-defined.

---

### R3. Puzzle as a *piece-uniqueness optimal transport* problem

**Analogy**. We have 256 pieces (supply, one each) and 256 cells
(demand, one each). The cost of placing piece p at cell c is the
*best-rotation negative edge match* with its 4 neighbors. **Solving
E2 is finding a perfect-matching of pieces↔cells of maximum reward,
subject to the catch that neighbor rewards depend on what's at
neighbor cells — a non-linear OT problem.**

**Math operation**. Approximate by *iterating* linear OT:
1. Fix a current assignment.
2. Compute the marginal cost matrix C[p,c] = best rotation reward
   given current neighbors at c.
3. Solve linear assignment (Hungarian, O(n³) = 16M ops for n=256)
   to get a new assignment.
4. Repeat until fixed point.

This is **Sinkhorn iteration** / iterative-OT in the puzzle solver
world. None of our destroy operators do an OT-style global piece
permutation — they're all *local* destroy-and-greedy-repair.

**Why this is different from MaxSAT (dead end)**.
- MaxSAT exhaustively encodes uniqueness; chokes at 16×16.
- OT *relaxes* uniqueness (each iteration is a perfect-matching, O(n³)
  not exponential) and recovers it on convergence.
- We have *never* solved a globally-feasible piece-assignment problem
  in vol-17 — always local destroy + local repair.

**PoC**. 1 day. Implement `iterative_ot_repair(board, region)`:
restrict to a k-cell region, build the cost matrix from current
boundary, run Hungarian (n³ for k cells), accept if better. The
killer feature is that for k=50-cell mismatch components, Hungarian
is 125k ops = microseconds. We can do it inside the ALNS inner loop.

**EV**. Medium. Hungarian on the *mismatch component only* is a clean
algorithmic novelty. If the issue is local entanglement, OT inverts
the locally-optimal piece permutation in one shot.

**Failure mode**. Cost matrix depends on neighbor choices which
depend on cost matrix → fixed-point may oscillate. Damped Sinkhorn
or single-pass-then-CP-fill mitigates.

---

### R4. Puzzle as *signal compression*: each piece is a 4-symbol
codeword over a 22+1 alphabet

**Analogy**. The 256 pieces define a 256-codeword codebook over a
4-position 23-alphabet. **What is the entropy of the codebook? What
is the mutual information between two adjacent codewords sharing one
symbol?** The "solvability" of E2 is fundamentally about *how
distinguishable* the codewords are.

**Math operation**. Compute, for each color c, the number of pieces
with c on each side. Compute the mutual information I(side_left;
side_right) of a randomly-chosen piece. **A high MI means the puzzle
has strong "linguistic" structure** — pieces have characteristic
side-pairings — that a constraint solver doesn't exploit.

**Why this is different from rare-color geography (already in memory)**.
- Rare-color memory tells us which *colors* are rare. It doesn't tell
  us *which color-pairings are statistically tied within pieces*.
- If pieces with color X on the N side strongly tend to have color Y
  on the S side, then placing a piece with X on its N side **predicts**
  what its S side must be — a propagator the engine doesn't have.

**PoC**. 1 hour (yes, hour). Read the puzzle CSV, build the joint
distribution of (N-color, S-color, E-color, W-color) over 256 pieces.
Compute pairwise MI. Compute the entropy of each side conditional on
the others. Identify any color-pair with > 1 bit of mutual info —
that's a "linguistic" structural constraint we can encode as a CP
propagator.

**EV**. High, low cost. Even if no signal is found, we've quantified
"how much structure is in the puzzle" — the absence of MI tells us
the generator (Selby-Riordan) deliberately broke this kind of
correlation. Either result is publishable.

---

### R5. Puzzle as a *topological* surface: mismatches define a 1-cycle
in homology

**Analogy**. Color the dual graph: vertices are cells, edges between
adjacent cells are red if mismatched, green if matched. **The set of
red edges is a 1-chain on the torus (or square)**. Its boundary (∂) in
simplicial homology is either trivial (closed loops) or hits the
puzzle boundary.

**Math operation**. Compute the first homology H_1 of the mismatch
subgraph. The number of *independent* mismatch cycles is the first
Betti number β_1. **Each cycle is a topological obstruction** — you
can't unwind it by local swaps without crossing a perfect region.

**Why this is different from connected-component ALNS**.
- ComponentDestroy treats the mismatch cluster as a set.
- Homology treats it as a *cycle structure*. A "1-cycle"
  mismatch can only be resolved by *cutting* it — which requires
  destroying *across* the cycle, not within.
- This explains why ComponentDestroy gets stuck on cluster-shaped
  defects: the cluster has a hole / handle that local repair can't
  thread.

**PoC**. 1-2 days. (i) Wrap the mismatch graph as a CW complex.
(ii) Compute H_0 (components, easy) and H_1 (loops, requires Smith
normal form or a hand-rolled cycle-basis enumerator on the small
mismatch subgraph). (iii) Design `CycleDestroy` op: destroy edges that
*break* each independent 1-cycle. (iv) A/B against ComponentDestroy.

**EV**. High *if* mismatch geometries have non-trivial β_1. We have
the data (453-class boards saved) — first 10 min is just measuring β_1
on our existing boards. Cheap to validate before building the op.

---

### R6. Puzzle as a *crystal* with defects, GA piece-permutation is *
defect annealing*

**Analogy**. The 256-piece set is a crystal at zero temperature; the
mismatches are defects (dislocations, vacancies, anti-sites). **Real
crystals anneal defects via *self-diffusion* — atoms hop into
nearest-neighbor empty sites, gradually moving the defect to a sink
(grain boundary).**

**Math operation**. Two pieces A, B can *swap* (transposition).
Swap-energy is the score-delta. Sequence of swaps = a permutation, =
an element of S_256. The puzzle's "defect annealing" is **biased
random walk on the symmetric group** toward identity-swap (= solved).

**Why this is different from ALNS**.
- ALNS destroys k cells and re-fills. A *swap* keeps both cells filled
  and just exchanges. Our `piece_swap_hillclimb` does this O(C×N) but
  *greedily*; we never run it as SA + adaptive walk on S_256.
- The full permutation walk is fundamental for *defect transport*:
  we move a single mismatch piece across the board by a *sequence*
  of swaps. Each intermediate state is worse but the endpoint is
  better — classical SA territory we haven't exploited.

**PoC**. 1 day. Implement `swap_walk_sa`: at each step, pick the worst
piece by mismatch contribution, find a piece K cells away whose swap
*will reduce* defect after both swap, accept by SA. This is "defect
migration" not "destroy/repair". Key novelty: swaps preserve piece
multiset, so no uniqueness violations during the walk.

**EV**. Medium. The hill-climbing version exists (gives +1-3 matches).
Annealing the swap walk could break iso-score plateaus where greedy
swap finds no improvement.

---

### R7. Puzzle as a *sound* — color sequences as melodies, mismatches
as dissonances

**Analogy** (the user's prompt). Scan the board in some 1D order
(serpentine, Hilbert curve, spiral). The sequence of N-edge colors is
a *time series* — a "melody". Adjacent matching = consonant interval;
mismatch = dissonance. **The board's "musical quality" is a
quantifiable property: harmonic entropy, autocorrelation, spectral
flatness.**

**Math operation**. Take a 256-long color sequence from a board.
Compute its discrete Fourier transform on Z/23. **A solved board has
specific spectral features** (zero high-frequency dissonance energy
under serpentine scan order if all matches are local). A 453-board has
isolated dissonance spikes.

**Why this might unlock something**. We've never asked: **does the
solved board have a low-rank Fourier representation?** If yes, that
means there's a low-dimensional manifold of "near-solved" boards
parameterized by the dominant spectral components. We could **project
a 453-board onto the leading spectrum and inverse-transform** to get
a candidate denoised board.

**PoC**. 4 hours. (i) Pick scan order (serpentine, Hilbert). (ii)
Extract 4 sequences (one per cardinal direction). (iii) FFT each
on the 23-element complex unit roots (treat color k as exp(2πik/23)).
(iv) Plot spectra of 453-class boards vs corpus 469-class boards.

**EV**. Low-medium. The Hilbert scan order makes adjacency-in-grid
correspond to adjacency-in-sequence with provable distortion; the
FFT then gives a "grid-aware" frequency decomposition. **If 469
boards are spectrally distinct from 453 boards, we have a 1D feature
to rank candidate destroy targets by.** Most likely outcome: spectra
look similar but cluster mismatch geometry differs — still useful.

**Failure mode**. Spectra of structured-noise problems usually look
flat; FFT on 23-roots-of-unity may show nothing. Cost is low; just
measure.

---

## Stage-gate prioritization (the Crowdworx lens)

Crowdworx warns about 3 traps:
- **Misalignment** with the actual problem.
- **Reactivity** (chasing weak signals).
- **Siloed thinking** (cross-domain is the antidote).

Re-ranking the 7 candidates by (problem fit × feasibility × time-to-
signal):

| # | Idea | PoC time | EV | First-signal time | Rank |
|---|------|---------|----|-------|-----|
| R4 | Piece-side mutual information | **1 hour** | high | 1 hour | **1** |
| R5 | Mismatch homology β_1 measure | 30 min measure + 1 day op | high | 30 min | **2** |
| R3 | Iterative OT / Hungarian-on-component | 1 day | medium | 1 day | **3** |
| R2 | Wolff cluster on Z/23 Potts | 1 day | high | 1 day | **4** |
| R6 | Swap-walk SA on S_256 | 1 day | medium | 1 day | **5** |
| R7 | Hilbert-FFT spectral feature | 4 hours | low-med | 4 hours | **6** |
| R1 | Diffusion-on-corpus inpaint | 1-2 days train + plumbing | medium-high | 2 days | **7** |

**Recommended order**:

1. **Today (1-2 hours)**: do R4 piece-side MI + R5 homology
   measurement. Both are *measurements on data we already have* —
   they cost almost nothing and either gives us a new structural
   propagator (R4 finding) or a new destroy operator design constraint
   (R5 finding).
2. **Tomorrow (1 day)**: build the best-scoring of R2 / R3 / R6 as a
   destroy operator. Pick by what R4 + R5 suggest is the *right
   structural lens*.
3. **Next session**: R1 (diffusion) if and only if the corpus-driven
   manifold approach still seems promising after R2-R6 results.
4. **Defer**: R7 (FFT). Lowest EV, kept on shelf.

## Why this is genuinely new (the user's challenge)

- **R4 piece-side MI** has never been measured on E2 in published lit
  (the puzzle is treated as a CSP, not as a coding-theory object).
- **R5 homology of mismatch graph** has never been applied to a
  jigsaw-style puzzle. Persistent homology has been used on jigsaws
  for *image-content* features, never on the *mismatch defect graph*.
- **R3 iterative OT** on edge-matching puzzles: zero published. OT in
  combinatorial assignment is standard, but iterating it as a
  destroy-repair-inside-MCMC is the novelty.
- **R2 Wolff cluster on Z/23 Potts**: Wolff is THE algorithm for Potts
  models; nobody has applied it to E2's puzzle-encoded Potts.
- **R6 swap-walk SA** on S_256: closest published work is
  "permutation-based simulated annealing" for TSP and QAP. Never on
  E2.
- **R1 diffusion-on-corpus**: the corpus only exists because we
  scraped it (`reference_e2_community_corpus`). No one else has 1.2k+
  E2 near-solutions in one place to train on.

Each of these is **a direction the field has not pointed at this
puzzle**. The user's premise — "it might not even exist, your
creativity is the unlocking piece" — is the operating instruction.
The R4/R5 measurements are the cheapest possible bet that *something
new is there*.

## Connection to the HBR "garden" lens

HBR: innovation as a garden where 100 seeds are planted, 90 die, the
8 that bloom are unpredicted. The 7 candidates here are seeds. R4
(1-hour cost) is one I would plant first because cost-of-failure is
negligible and cost-of-not-planting is unknown.

**Make failure an option**: R7 (FFT) is almost certainly going to
show nothing — I'm listing it anyway. The act of measuring is the
unlock; the negative result tells us the *generator* erased a
specific kind of structure, which itself constrains future ideas.
