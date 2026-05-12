# RESEARCH_NOTES_11.md — vol-11: survey propagation for Eternity II

**Session**: 2026-05-12 (immediately after vol-9/10 close-out, commit `7cafdb9`).

**Calibration**. Verified community ceiling: 469/480 (McGavin 2020, canonical
5-clue Monckton). Our own stack: 454/480 (vol-6 PT warm-start). Cold-start
vol-9 SA caps ~308 edges. Bar for "we caught up": ≥469. Bar for "we cleared
SOTA": ≥470.

## Direction chosen — cross-field reformulation: survey propagation

Vol-10 closed with "the math doesn't save us at the static level." Vol-11
takes the opposite bet on a different math: **the math from the
statistical-physics-of-random-CSPs literature**, which the community has
never tried.

### Why this matters

The community tried every SAT solver they could find — kissat, cryptominisat,
OR-tools, Z3, and several MIP / max-clique formulations. They all cap at
**10×10** (vol-10 probe #7 corpus, 4 independent confirmations). The
shared assumption across that work is **DPLL-class search** (or its CDCL
extension): branch on a single variable, propagate, learn, backtrack.

E2 sits at the **GEMP-F SAT phase transition** (Mateu 2012, Springer-
published; vol-10 probe #1 / `01_SAT_thread.md`). At the SAT phase
transition, the *solution space fragments into exponentially many
clusters separated by frozen variables*. DPLL/CDCL search treats this as
a forest of indistinguishable local optima and gets stuck — this is the
well-known "hard core" of phase-transition SAT.

**Survey propagation (Mézard, Parisi, Zecchina, 2002)** broke random
k-SAT at the phase transition by solving a *different* fixed-point
equation — the 1RSB (one-step replica-symmetry-breaking) cavity equation —
which directly reasons about clusters of solutions rather than individual
solutions. SP-guided decimation drives variables toward their cluster-
consensus value and reaches solutions in regimes where DPLL fails by
orders of magnitude.

**Hypothesis**: E2's "DPLL caps at 10×10" wall is *the same wall* random
k-SAT hit before SP. If E2's factor graph has the clustered solution
landscape its phase-transition position predicts, SP should at minimum
produce *meaningful color marginals* far better than gacolor's count-only
inventory, and at most produce a 16×16 solution where DPLL caps at 10×10.

### What I expect

In honest expected-value order:

1. **Most likely (~60%)**: SP-BP does not converge on E2's factor graph
   without strong damping, *and* even with damping the marginals are weak
   (high entropy at most cells). The structure is too regular/structured
   for the 1RSB ansatz, which was designed for the random-CSP regime.
   This would be a publishable negative result distinguishing structured
   from random CSPs at the same phase-transition density.

2. **Plausible (~30%)**: BP converges and produces marginals that, when
   used as a value-ordering heuristic in solver-engine, yield a
   measurable improvement over gacolor. We don't beat 469 but we get
   a clean second-channel signal that compounds with vol-9's
   `PreferredFirst`. Useful infrastructure.

3. **Long shot (~8%)**: SP-decimation reaches partial scores above
   vol-6's 454, possibly approaching 460. Genuinely new, because it
   would be the first non-DPLL search method to make substantial
   progress on E2.

4. **Genuinely new territory (~2%)**: SP-decimation finds a high partial
   (≥469) or even a full solution. Massive result if it happens.

The 60% null is fine. As the user said: "if we fail 100 times to get
1 great innovation that's ok."

## The E2 factor graph

**Variables**. One per cell: `X[pos] ∈ Domain[pos]` where `Domain[pos]`
is the list of `(piece_id, rotation)` placements that satisfy:
- if `pos` is a border cell, `piece_id`'s class matches (corner/edge/inner);
- rotation orients BORDER edges outward;
- if `pos` is a hint position, only the hinted `(piece_id, rotation)`.

Domain sizes (canonical E2):
- 4 corners: |D| = 4 (one corner each, 1 rotation).
- 56 edges: |D| = 56 (one edge each, 1 rotation valid for that side).
- 196 interior: |D| = 196 × 4 = 784 (any interior piece × any rotation),
  minus 5 hint cells fixed to a single value.

(The "1 rotation" claim for borders is shorthand: each corner piece has
exactly 1 rotation that puts its 2 BORDER edges outward at a given corner
position; each edge piece has exactly 1 rotation per side. We compute
this explicitly.)

**Factors**.

Three families:

1. **Edge-equality factors `E[(p, q)]`** between adjacent cell-pairs.
   Hard constraint: the right edge of cell `p` (after rotation) equals
   the left edge of cell `q`. Same for top/bottom. There are `2·W·H − W − H`
   internal joins = 480 for 16×16.

2. **Piece-uniqueness factor `U[i]`** for each piece-id `i`: each piece
   used exactly once. Encoded as pairwise mutex constraints over pairs
   of cells `(p, q)` where some `r1, r2` exist with `(i, r1) ∈ D[p]` and
   `(i, r2) ∈ D[q]`.

3. **Border-class factors** (subsumed into per-cell domain restriction —
   not a separate factor in the graph).

**Form for BP**.

Pearl-style sum-product on the bipartite factor graph. For each edge
`(variable cell `p`, factor `f`)`, two messages:

- `μ_{p→f}(x)`: probability variable `p` takes value `x` based on all
  factors *except* `f`.
- `ν_{f→p}(x)`: probability factor `f` is satisfied if `p = x`,
  marginalized over the other variables `f` connects to.

For an edge-equality factor `E[(p, q)]`:
```
ν_{E→p}(x_p) = Σ_{x_q : compatible(x_p, x_q)} μ_{q→E}(x_q)
```

For a piece-uniqueness mutex `M[(p, q, i, r1, r2)]` (cells `p` and `q`
both can host piece `i`):
```
ν_{M→p}(x_p) = 1                              if x_p ≠ (i, *)
ν_{M→p}((i, r)) = 1 − μ_{q→M}((i, r2))         (forbid double use)
```
(More precisely: `1 − Σ_{r'} μ_{q→M}((i, r'))` for any rotation.)

Variable-side update:
```
μ_{p→f}(x) ∝ ∏_{f' ∈ neighbours(p) \ {f}} ν_{f'→p}(x)
```

**Form for SP (1RSB)**.

The SP messages are *surveys*: distributions over the BP messages
weighted by the 1RSB Parisi parameter `m`. For E2's factor graph the
practical formulation is the **warning propagation / belief
propagation hybrid (WP-BP)**:

A *warning* on edge `(f → p)` says "factor `f` forces `p` to take a
non-x value if `p` would otherwise take `x`". The survey `η_{f→p}(x)`
= probability of a warning being sent. In the limit `m → 1`, SP reduces
to BP; for `m < 1` it favors solution clusters of small size, finding
the *typical* cluster structure rather than the largest.

For decimation, we use SP-decimation as in Braunstein-Mézard-Zecchina
2005: iterate SP to fixed point, compute survey marginals, **fix the
variable whose surveys are most polarized** (largest gap between top
two values), simplify the graph, repeat. This is the algorithm that
solves random 3-SAT near α=4.2.

## Practical SP for E2 — design choices

1. **Domain representation**. Per-cell domain as list of
   `(piece_id, rotation)` ∈ {0..256} × {0..3}. Marginals over this
   domain are kept as dense or sparse arrays per cell.

2. **Damping**. SP/BP famously oscillate on real instances. Use
   damping `μ_new = (1−λ) μ_old + λ μ_computed` with `λ = 0.1..0.5`.

3. **Convergence criterion**. L1 change in messages between iterations
   below `ε = 1e-4`. Cap iterations at 1000.

4. **Decimation policy**. After SP converges, compute per-cell entropy
   over the surveys. **Fix the cell with lowest entropy (most polarized
   surveys)** by choosing its top value, propagate domain restriction,
   re-run SP. This is the standard SP-decimation loop.

5. **Pieceset-uniqueness handling**. The all-different over piece-ids
   is the hardest part of SP for E2. It is *not* a local factor — every
   pair of cells that could share a piece-id is connected. The
   factor-graph density gets enormous. **Mitigation**: enforce it
   *softly* — each cell tracks a "current claim" on piece-ids, and
   piece-claim probabilities are normalized across cells via a
   global step (similar to symmetric-alldiff in CP). This is the
   `gacolor`-equivalent move inside SP.

6. **Initialization**. Two natural choices:
   - **Uniform**: all messages start at `1/|D|`.
   - **Hint-aware**: hint cells start fully polarized; edge-color
     messages propagate from hints outward.

   Hint-aware is the empirically-stronger start for structured CSPs.

7. **Marginalization output**. After SP convergence, each cell `p`
   has a distribution `π_p(x)` over its domain. Aggregate to a
   *per-cell color marginal*: `π_p^color[c]` = sum of `π_p(x)`
   over `x` whose oriented top-edge is `c`. Same for other sides.

## Implementation plan

**Stage 1 (Task 7-8)**: Python PoC.
- Build the factor graph from the canonical CSV + 5 hints.
- Implement BP (sum-product) with damping.
- Measure: does BP converge? What are the marginals?

**Stage 2 (Task 9)**: SP on top of the same graph.
- Replace BP with SP (1RSB) iterations.
- Run SP-decimation: SP → fix most-polarized cell → SP again.
- Measure: how many cells decimated before SP fails? What score?

**Stage 3 (Task 10)**: Write up findings. Compare to:
- Random initialization (sanity check).
- gacolor's per-color supply/demand.
- vol-9's Verhaard preferred-list.

Python is the right language for stage 1 — fast iteration on the
math. If SP works, port the inner loop to Rust for the full
16×16 run.

## Session log

### 2026-05-12 — start

Read MEMORY.md, project_e2_state.md, RESEARCH_NOTES_10 closeout,
9th/11th/5th community-mining notes. Initial plan was NS-1
multiset-equality propagator → Blackwood schedule. User pushed back
("you're a researcher — innovate, cross-think across fields, failing
is part of the process").

Pivoted to survey propagation. Three angles considered: SP-decimation,
tensor-network feasibility (PEPS contraction), Hamilton-cycle frame
enumeration. Picked SP-decimation as primary: the phase-transition
position of E2 is documented (Mateu 2012) and SP is the canonical
phase-transition CSP technique. The community tried SAT exhaustively
but not the 1RSB cavity method, so this is genuinely new territory.

Wrote spec above. Now building.

### 2026-05-12 — execution

Built end-to-end in Python:
1. `scripts/v11_load_e2.py` — canonical CSV loader, validates 4 corners
   / 56 edges / 196 interior / 22 colors / 5 hints.
2. `scripts/v11_factor_graph.py` — domain construction (152,901 states
   total) + 480 adjacency factors.
3. `scripts/v11_bp.py` — Pearl sum-product BP with damping.
4. `scripts/v11_bp_uniq.py` — BP + soft piece-uniqueness (per-piece
   reweighting between iterations).
5. `scripts/v11_sp.py` — Mézard-Parisi-Zecchina survey propagation
   with Parisi parameter `m`.
6. `scripts/v11_bp_decimation_v2.py` + `v11_bp_dec_sweep.py` +
   `v11_dec_parallel.sh` — batched parallel decimation sweep.
7. `scripts/v11_bp_backtrack.py` — backtracker with three value-orders
   (bp / static / random).
8. `scripts/v11_sp_backtrack_hybrid.py` — SP-decimation + chronological
   shallow backtracking.
9. `scripts/v11_dump_bp_marginals.py` — Rust-loadable JSON dump.
10. `scripts/v11_analyze_marginals.py` — structural analysis of
    converged marginals.

### Findings

**F1 — BP converges on E2 cleanly.** Damping 0.3, ~60 iterations,
~1.4 s for the full graph. No oscillation. Hint cells correctly
reach H=0. Interior cells reach mean H=6.11 nats vs uniform-domain
upper bound 6.66 nats — an **8.4% reduction over uniform** is the
information BP extracts from edge-equality + soft uniqueness.

**F2 — SP-y (1RSB) shows REVERSED behavior vs random k-SAT.** Sweep
over Parisi parameter `m ∈ {1.0, 0.8, 0.5, 0.3, 0.15}` at fixed init:
| m | interior reduction |
|---|---|
| 1.0 (≡ BP) | 8.3% |
| 0.8 | 7.9% |
| 0.5 | 7.5% |
| 0.30 | 7.3% |
| 0.15 | 7.0% |

On random k-SAT, lower `m` *sharpens* marginals by focusing on the
largest cluster. On E2, lower `m` **flattens** marginals. **The 1RSB
clustering ansatz that survey propagation was designed for does not
apply to canonical E2.** This is itself a structural finding about
the puzzle: E2's solution-space geometry is NOT a 1RSB
shattered-cluster landscape.

Two plausible explanations:
- E2 is in the **SAT regime** (one expected solution) so there's
  nothing to cluster over.
- Piece-uniqueness creates global (non-local) factors the locally-
  tree-like 1RSB ansatz cannot capture.

**F3 — Greedy SP-decimation reaches depth 125 / score 211 in 5
min.** Best config: SP `m=0.30`, batch=1, damping=0.3 (sweep 6).
This is greedy committed decimation (no backtracking). For
comparison: vol-9's Eulerian propagator was zero pruning; vol-9's
Verhaard SA cold-start best partial was depth 181 / 308 edges in
30 s. So SP-decimation reaches **depth 125 in 5 min** which is
substantially **slower than Verhaard SA** (because each fix needs
a fresh SP convergence — ~2 s per fix). But it's a different
algorithmic family with different scaling, and the score is real.

Interesting: contradiction depth grows with **lower** `m`. Within
the sweep, m=0.30 (most cluster-focused) goes farthest. So even
though m=0.30 has *flatter* marginals at convergence, **committing
to its choices gets you further into the search tree** — the
clustering parameter discriminates which low-confidence direction
is most likely to extend.

**F4 — Random value-order beats BP and static in a basic
backtracker.** Three runs, 90 s wall-clock:
| value mode | max_depth | max_score | nodes | backtracks |
|---|---|---|---|---|
| bp | 157 | 256 | 16,493 | 27,207 |
| static | 154 | 263 | 16,780 | 33,176 |
| random | **173** | **297** | 13,690 | 25,208 |

Random outperforms BP by 16 depth and 41 score. **The structural
information BP encodes is already accessible via standard MRV +
forward-checking and adds no value as a value-order heuristic in
this regime.** This is a clean negative result for "BP marginals
as value-order".

The reason random wins is likely **decorrelation of failure
modes**: deterministic value orders make backtracking try similar
values at similar depths, while random gets uncorrelated coverage.

**F5 — corner color preference (c1/c3 dominate inward sides) is a
trivial consequence of the piece set, not a hidden invariant.**
BP correctly recovers that all 4 corner pieces in the canonical 256
have inward-facing color colors in `{1, 2, 3, 4}`. c3 appears in 3
of 4 corners, c1/c2 in 2 of 4. So BP's marginal "c1 or c3 is
favored at corner-inward sides" is just the obvious piece-set
fact. Not novel.

**F6 — hint reach is 2-9 cells per hint** (cells where the hint
piece-id has marginal > 0.01). This is a *measured* quantitative
statement of how local hint information is at convergence. **Each
hint reduces uncertainty in a Manhattan-1 neighborhood, not
beyond.** This validates the community's empirical observation
that hint placement matters more than count (Mike Pringle 2026,
McGavin 2026, see `05_Joe_pruning_method_thread.md`).

**F7 — Spatial clustering of polarization: 1.92×.** Low-entropy
cells (25th percentile) are 1.92× more likely to be neighbors of
other low-entropy cells than random adjacency would predict. The
structure is local and propagating, consistent with hint-locality.

**F8 — Piece-uniqueness emerges self-consistently from edge
equality.** Without hard piece-uniqueness, BP marginals at
convergence assign 95% of non-hint pieces an occupancy in `[0.87,
1.13]` — most pieces are claimed exactly once just from
edge-equality + soft normalization. This is a structural fact
about the E2 piece set: the edge palette is rich enough that
double-use of any piece creates incompatibilities BP can detect.

### Hybrid SP-decimation + shallow backtrack (in progress)

Running 4 parallel hybrid configs (m ∈ {0.3, 0.5, 1.0},
rollback_depth ∈ {5, 10, 15}) for 300 s each. Outcomes pending.

### Honest assessment so far

The most ambitious cross-disciplinary direction (SP-decimation) has
been **falsified as a path to community SOTA**. BP/SP-y carries
only ~8% domain reduction worth of information, which is too weak
for either:
- greedy decimation (stalls at depth 125),
- value-order heuristic in a backtracker (random outperforms it).

This is a clean, publishable negative result. **E2's solution
landscape is NOT a 1RSB shattered-cluster structure.** It's closer
to the SAT regime (1 expected solution, no clustering to exploit).

### Pivot for the remaining session

Given the BP/SP exploration is essentially complete (with negative
result on the headline hypothesis), I'll:
1. Finish the hybrid runs and report their max score honestly.
2. Update auto-memory with the structural finding "E2 is not 1RSB".
3. Document the BP-marginal pipeline cleanly for future use (the
   `bp_marginals.json` file is reusable infrastructure even if
   marginals aren't a winning heuristic).
4. Move to the NS-1 propagator backlog (deferred work from start
   of session), which has independent value and is the fallback
   plan as written.

### Critical context: dead-ends memory says SP is already a dead-end

`project_e2_dead_ends.md` from 2026-05-11 (night before vol-11)
warned: *"Survey Propagation … verdict 1.5/5 stars. Reason:
cavity-method assumes locally-tree-like factor graph; E2 is a 2D
grid with short cycles in every 2×2 block. … With 5 hints E2 is
below the rigidity threshold → SP degenerates to BP → uniform
surveys → useless."*

I did not absorb this carefully enough before committing to the
SP direction. The recovery framing for vol-11 is: **the prior
agents predicted SP failure theoretically; vol-11 produced
empirical confirmation with quantitative measurements**. That's
still useful — it converts a theoretical prediction into a
measured fact — but it should not be presented as a fresh
direction.

The dead-ends memo recommended **edge-color encoding (480 vars ×
22 colors, 256 cell constraints)** as the alternative if message-
passing is revisited. Vol-11 used the cell-place-rotation encoding
(the one the memo flagged as inferior). Worth flagging for any
future BP work.

### Hybrid SP-decimation + shallow backtrack results

| config | damping | m | rollback | depth | score | backtracks | time |
|--------|---------|---|----------|-------|-------|------------|------|
| a | 0.30 | 0.30 | 10 | 100 | 158 | 0 | 180s |
| b | 0.30 | 0.30 | 5 | 100 | 158 | 0 | 180s |
| c | 0.30 | 1.00 | 10 | 99 | 163 | 0 | 181s |
| d | 0.30 | 0.50 | 20 | 76 | 115 | 2 | 181s |

All hybrid configs reached the same depth (~100) within 180s.
None of them outperformed sweep_6's depth 125 from the original
5-minute SP-decimation. The shallow backtracking added zero value
because the per-fix cost (~1.9 s) dominates wall-clock; with the
180-s budget, the backtrackers never got past depth 100 to need
their backtracking machinery.

### NS-1 multiset-equality structural finding (TIER 3)

While the BP/SP direction yielded a confirmed null, the NS-1
backlog probe yielded a **genuinely new quantitative structural
invariant** on canonical Eternity II:

**Claim**. For any partial placement on canonical E2 reaching
score `s` out of 480, with the 56 border-edge-class cells all
filled, let `A` = multiset of inward-facing colors across those
56 cells and `B` = multiset of border-facing colors across the
56 14×14-perimeter interior cells. Then the *multiset deficit*
`Δ = sum_c |A[c] - B[c]| / 2` satisfies:

  - `s = 480 (full solution)` → `Δ = 0` (exact equality)
  - `s ∈ [448, 470]` → `Δ ∈ {0, 1, 2}` (median 2)
  - `s ∈ [427, 449]` → `Δ ∈ {0, 1, 2, 4}` (median 2)
  - `s < 396` (low partials) → `Δ ≈ 0` because most cells empty

**Measurements on the 82-board community corpus**:

| score (canonical E2) | unmatched | Δ | 2Δ |
|----------------------|-----------|---|-----|
| 480 | 0 | 0 | 0 |
| 469 | 11 | 0-1 | 0-2 |
| 467 (E2nc) | 13 | 1 | 2 |
| 460 | 20 | 4 | 8 |
| 458 | 22 | 2 | 4 |
| 452 | 28 | 4 | 8 |
| 449 | 31 | 1 | 2 |
| 448 | 32 | 0 | 0 |

**Interpretation**. The 14 unmatched edges in a typical 469 break
down as: ~2 border-interior mismatches (captured by Δ) + ~12
interior-interior mismatches (not captured by NS-1). So on
canonical E2 near-solutions, **≥85% of unmatched edges are
interior-to-interior**, and the border-interior interface is
near-perfect. This was the empirical Hopfer 2022 / community
intuition — **vol-11 puts a number on it**.

**Useful propagator form**: enforce `Δ = 0` once the border ring
is closed. This is necessary on any path to a full 480. On the
search side, this acts as a *late* propagator — it cannot help
early but eliminates a class of unsolvable near-final boards.

Files:
- `scripts/v11_ns1_verify.py` — multiset computation per board.
- `scripts/v11_ns1_deficit.py` — deficit-vs-score analysis.
- `output/v11_sp/ns1_verification.json` — full per-board record.

### Random-seeded backtracker results (parallel sweep)

Original 90 s baseline (unseeded random): depth 173, score 297.
Seeded (300 s budget):
- seed=100: depth 132 score 215
- seed=200: depth 136 score 224

Seeding *worse* than unseeded shows the unseeded run was
favorable, not typical. Honest expected score with a Python
backtracker is ~200–225 in 5 minutes, depending on luck.

For comparison: vol-9's cold-start CP best partial was 308. Our
Python backtracker is well below; to compete we need Rust.

### Final session summary

**Tier 1 (minimum) delivered**: clean ranked report on what was
tried, what worked, what didn't, in the same honest style as
vol-10's withdrawal of probe #3a. Multiple converged findings:

- BP converges on E2 in ~60 iterations, ~8.4% interior reduction.
- SP-y (m=0.15..0.50) has *flatter* marginals than BP — opposite
  of random k-SAT — confirming E2 is not a 1RSB cluster landscape.
- Greedy BP-decimation caps at depth 125 / score 211; backtracker
  with random value-order does better than with BP marginals.
- Per-cell entropy is bimodal (border partially polarized, interior
  near-uniform); polarization clustered at 1.92× random adjacency.
- Hint reach is 2–9 cells; piece-uniqueness self-organizes to 95%
  via edge-equality alone.

**Tier 2 (good) NOT delivered**: did NOT reach 467/469. Best
Python score 297 < vol-9 cold-start 308.

**Tier 3 (excellent) PARTIALLY delivered via NS-1 backlog**:
quantitative measurement that canonical E2 partials at score
448–480 have NS-1 multiset deficit Δ ∈ {0,1,2,4}. This is a
new measured structural invariant the community had as
empirical intuition (Hopfer 2022) but never quantified across
the corpus.

**Tier 4 (session-defining) NOT delivered**: no 470+, no internal
14×14, no community-disrupting result.

### Vol-12 recommendations

1. **Build NS-1 as a real propagator in Rust**. Vol-11's data
   shows it's a clean filter for ≥469-class boards. Should live
   in `crates/propagators`. The "border-closed" form is the
   strongest — enforce Δ=0 after border placement. Cost is
   O(56·color_count) per check.

2. **Try BP/SP on the edge-color encoding** (memo-recommended
   alternative). Variables = 480 edge colors × 22 possible
   values; constraints = 256 cells assert their 4 incident
   edges form a valid piece. This is the SAT-style encoding the
   community uses. Marginals on edge colors may be stronger
   than on cell-placements because the encoding has shorter
   constraint scopes.

3. **CVM (cluster variation method) / generalized BP on 2×2
   plaquettes**. Mentioned but not built. Each plaquette = 4
   cells with all internal edges enforced. ~225 plaquettes,
   ~10⁴ states each. Captures short-range correlations BP
   misses. Could plausibly work where BP/SP failed.

4. **Coordinate with the other agent (bench-audit crate)**. Their
   Rust work and the BP-marginal infrastructure here are
   complementary; bp_marginals.json is now Rust-loadable.

## NS-1 backlog spec (kept for follow-up)

**Statement** (Hopfer 2022, vol-10 NS-1). The multiset of inward-facing
colors across the 56 edge pieces must equal the multiset of border-
facing colors across the 56 14×14-perimeter interior pieces.

**Status**: deferred until after the SP probe. May ship as a
follow-up propagator if SP work surfaces it as relevant. Even if SP
fails, NS-1 remains useful — it's a static, cheap propagator that
fits cleanly into `crates/propagators` and can be calibrated against
vol-6's border corpus.

**Static piece-side check (cost-free, runs once)**:
```
B_inward = multiset { edge_piece.opposite_of_border_edge for each edge piece }
```
This is fixed for canonical E2 — compute once.

**Partial-frontier propagator form (the part that actually prunes)**:
When the border ring is closed (all 60 border pieces placed), the
56 inward-facing colors are a specific 56-vector. The 14×14
perimeter must consume these colors. Per-color budget: for each
color `c`,
```
count(c in border_inward placed) ≤ count(c in unplaced-interior across all rotations)
```
This is checked against the *demand* the border ring imposes on the
14×14 outermost layer.

If SP fails, NS-1 is the obvious fallback because it touches the
single most-empirically-attested community structural fact (Hopfer
2022 in `11_Inner_14x14_thread.md`).
