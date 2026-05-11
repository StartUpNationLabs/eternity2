# Research notes — vol. 3

Continuation of `RESEARCH_NOTES_2.md` (which closes 2026-05-11 with the
σ-bijection / Blackwood-decoded findings). Read the vol. 2 SESSION CLOSE
section for the snapshot of state, the verified facts about Blackwood's
record being 1-clue not 5-clue, the σ bijection saved to
`output/blackwood_decoded.json`, and the next-session priorities.

## Mindset for this volume

- This vol is for **innovation, not replication.** Memory line says:
  the user explicitly values novelty over polish. Past vols ended up
  proposing "port libblackwood's tricks." Resist that.
- Vol. 2 demonstrated a powerful pattern: when stuck, re-examine the
  *modeling decisions* hiding under the standard formulation, not the
  *algorithms* used to solve that formulation. Bugs in pinning,
  mis-identification of the SOTA target, color-labeling assumption,
  the prefix-determinism trap — all came from unexamined assumptions.
- Cheap experiments first. 30-line diagnostics can falsify expensive
  hypotheses. Trust strong negative results — change approach class,
  not parameters.

## Carry-over state (verified end of vol. 2)

- **Constrained baseline**: ~447-450 with all 5 hints pinned on official
  E2. Best from a single 6-sample harvest: 450/480. A 30-minute megarun
  with Houdayer-in-PT is running at session close; result will be in
  `v2/output/pt_e2_<timestamp>_<score>of480.{json,url.txt}`.
- **Community SOTA 470 is on 1-clue** (central pin only), NOT 5-clue.
  Established via σ-bijection decode + libblackwood code review.
  5-clue community SOTA unknown publicly.
- **Plateau is upstream of SA.** CP+greedy_fill produces a globally-
  wrong prefix that local repair can't fix; the prefix dominates the
  PT outcome. Even with random-shuffle-CP diversifying borders (55/60
  border cells different across samples), plateaus stay 443-444.
- **σ bijection saved** to `output/blackwood_decoded.json` — Blackwood's
  470 board re-encoded in our pieces.txt color labeling. Use for
  prefix_compare and any future reference experiments.
- **Bucas URL rendering FIXED** by dropping motifs_order from generated
  URLs; default Bucas labels match pieces.txt.
- **Two CP bugs FIXED** end of vol. 2:
  (1) parallel CP path was silently ignoring hints,
  (2) PT/SA had no hint-pinning machinery.
  Both fixed via `apply_symmetry_and_hints` extraction and
  `SaConfig::pinned_positions` / `PtConfig::pinned_positions`.

## Methodology rule (carried over from vol. 1+2)

Every experiment writes one section here with:
- **H** — hypothesis in one sentence.
- **Setup** — corpus, runs/cell, profiles compared.
- **Result** — JSON path + headline numbers.
- **Verdict** — kept / dropped / iterated, with one-line reason.

Negative results count.

---

## Seven inversions to try (proposed end of vol. 2, ranked by EV)

Each is a *reformulation*, not a tweak. They invert one assumption
buried in the standard cell-as-variable / piece-as-value framing.
For each: hypothesis, what we'd build, signal we'd look for.

### Inversion 1 — Piece-as-variable CP

**Standard**: cells are variables, pieces are domain values; MRV picks
the most-constrained cell.

**Inverted**: pieces are variables (256 of them), domain values are
(cell, rotation) placements; MRV picks the most-constrained piece —
the piece with the fewest legal placements remaining. **Different
search tree, different pruning dynamics.**

**Why this might matter for the plateau**: our prefix-determinism
problem says CP+greedy_fill always picks the same canonical sequence
of *cells* and fills them with locally-good pieces, ending up in a
globally-wrong prefix. With piece-as-variable, CP picks the most-
constrained *piece* first and commits its placement — the constraint
direction reverses, and the canonical sequence is over pieces (which
have asymmetric piece-classes: corner/edge/inner) not cells. The
resulting prefix is structurally different.

**What we'd build**: add `VariableOrder::PieceMrv` to
`crates/solver-engine/src/lib.rs`. Build a lookup `piece_id → Vec<(cell,
rotation)>` once and maintain it incrementally on backtrack. ~1 day.

**Cheap test**: run pt_e2 with the new profile on 6 seeds; compare
plateau distribution to deterministic baseline (mean 448.2, best 450).
If plateau shifts even by ±2 edges, we've found a real lever. If
identical, it doesn't matter.

**Bias**: this is most likely to produce a slight improvement, not a
breakthrough. But it's the cheapest fundamental change available.

---

### Inversion 2 — Edge-variable formulation ★ highest novelty

**Standard**: search assigns cells to (piece, rotation).

**Inverted**: search assigns **the 480 interior edges to colors**.
Variables: 480 edges, each with domain {1..22, ⊥} (⊥ = unmatched).
Constraints: for each cell, the 4 edges around it must collectively
be the 4-tuple of some unused piece (under any rotation).

**Why this might break the plateau**: our plateau states have a sharp
structural signature — 30 specific unmatched edges. In an
edge-variable formulation, the plateau is **directly addressable**:
"30 of our 480 edge-variables are ⊥; can we replace any of those ⊥'s
with a non-⊥ value while maintaining consistency?" This is a question
the cell-variable formulation cannot ask directly. Local moves in
edge-space target edge-flips, not piece-swaps; the geometry is
fundamentally different.

**Why this is genuinely novel**: every E2 solver in the literature
(libblackwood, ttu, Verhaard, Salassa et al.'s MaxClique, Kovalsky's
SDP, the Ansótegui SAT encoding) uses cell-as-variable as primary. The
"dual" SAT encoding (Ansótegui 2008) uses edge variables in addition
to cell variables for channeling; nobody has built the edge-only
primary search. The plateau structure (30 specific bad edges) gives a
direct *handle* in this formulation that doesn't exist elsewhere.

**What we'd build**: a new solver, not a config tweak. ~3-5 days for
a clean prototype. Variables, propagator (cell-consistency: for each
cell, the 4 adjacent edges must permit some valid piece-rotation under
remaining pieces), search engine, scoring. Reuse pieces.txt and the
hint set.

**Cheap test**: start tiny — implement edge-CP on a 6×6 generated
puzzle first. If it converges fast there, scale to 16×16.

**Bias**: highest probability of being the actual structural insight
we've been looking for. The unmatched edges in plateau states are
*the right object* in this formulation. Worth real time.

---

### Inversion 3 — Color-strand topology decomposition

**Standard**: solve all 22 colors simultaneously via piece placement.

**Inverted**: solve the **22 color-strand layout problems
independently**, then intersect.

For each color c ∈ {1..22}, the puzzle restricts to: "where do color c's
N_c piece-sides go?" This is a 1-dimensional pattern (color c forms a
"strand" across the board). Each subproblem has ~24× fewer variables.

The hard part: intersection. Each cell's 4 sides must be jointly
consistent with one piece. Solve via Lagrangian decomposition — dual
prices on the cell-consistency constraints.

**Why this might matter**: each color subproblem is small enough to
solve to optimality with standard techniques. The combined Lagrangian
gives a tight upper bound (much tighter than the trivial 480 we
computed) AND a primal feasibility recovery procedure.

**What we'd build**: 22 small CSPs + a Lagrangian-iteration outer
loop. Week+ engineering. Probably needs scipy/PyTorch for the dual
updates.

**Bias**: speculative. The independence assumption may be too weak.
But if it works it's a publishable result.

---

### Inversion 4 — Domain decomposition (top-down macro)

**Standard**: bottom-up, place pieces, hope global solution emerges.

**Inverted**: divide the 16×16 board into 4 quadrants (8×8 each).
Solve each independently with **boundary-color budget constraints**
(the right edge of NW must have a color-count compatible with the
left edge of NE). Each sub-problem is much smaller. Iterate via
Schwarz-style boundary-negotiation if quadrants disagree.

**Why this might matter**: the plateau lives in the central 6×6, which
straddles all 4 quadrants. With quadrant solves, the central region is
the *boundary* of every subproblem, where boundary-budget constraints
are most informative.

**What we'd build**: 4 sub-CPs + a boundary-coordinator. The
coordination is the hard part (it's a CSP itself, but small).
Engineering: 1-2 weeks. Real domain decomposition for combinatorial
optimization exists (Hooker's "Decomposition and Constraint
Programming") but not for E2.

**Bias**: novel, speculative. Probably won't break 470, but worth
trying if Inversions 1-2 don't pan out.

---

### Inversion 5 — ML-predicted cell ordering

**Standard**: cell visit order is hand-picked (BorderFirstMrv) or
hand-tuned (Blackwood's 5040-permutation experiment).

**Inverted**: train a small model to predict which cells will end up
in *disagreement components* across plateau dumps. Then commit those
cells LAST.

**Data available**: we have 6 pinned plateau dumps + 20 unpinned. The
topology diagnostic already computed per-cell variance. That's the
training signal.

**Why this might matter**: Blackwood's "scheduled relaxations" trick
is exactly this: he hand-picks 10 late cells where mismatches are
allowed. We'd replace his manual tuning with data-driven prediction.
And we already have the data.

**What we'd build**: tiny MLP or gradient-boosted classifier (sklearn
or pytorch), trained on plateau-dump cell features. Inference: rank
cells, commit in confidence-descending order. ~3 days including data
prep.

**Bias**: feels like the most direct "do what Blackwood does, but
automatically." Lower novelty than 1-2 but lower risk.

---

### Inversion 6 — Continuous relaxation + Sinkhorn projection

**Standard**: integer assignment, glassy discrete landscape.

**Inverted**: each cell holds a **fractional mixture** of pieces, weights
summing to 1. Edge colors are weighted sums. Matched-edge objective is
smooth in the weights. **Gradient descent** in this continuous space,
with periodic Sinkhorn-normalization back to doubly-stochastic
piece-cell assignments.

**Why this might matter**: the discrete plateau may be a saddle in the
continuous space rather than a basin. Kovalsky-Glasner-Basri 2014 did
the SDP version (rank-1 lift); we'd do the unconstrained version with
PyTorch + Sinkhorn for projection. Different objective surface,
different attractors.

**What we'd build**: PyTorch script, ~200 LOC. Sinkhorn iteration for
projecting onto the assignment polytope. Round to a discrete
assignment periodically to score.

**Bias**: speculative. Continuous relaxations of NP-hard problems
often plateau too, but the failure mode is different and the
diagnostic signals (gradient norms, Hessian eigenvalues) are
informative even if it doesn't beat discrete.

---

### Inversion 7 — Solve 0-clue, filter for our 5 hints

**Standard**: pin hints, solve constrained.

**Inverted**: solve **0-clue** E2 (highest symmetry, largest search
space). From the solutions found, **filter** for ones that happen to
match our 5 hint positions. Keep those.

**Why this might matter**: pinning breaks D4 symmetry partially in a
weird way; full symmetry might enable cleaner search dynamics. If the
0-clue solver finds many near-solutions with various pieces at the
hint cells, some of them will coincidentally satisfy our hints.

**What we'd build**: nothing new — run our existing pipeline with
`--no-pin-hints` and a much larger seed sweep. Half-day to test.

**Bias**: probably won't beat the constrained search budget-wise,
because 0-clue is strictly more degrees of freedom. But cheap to
falsify.

---

## Honest ranking (per implementation-day EV)

1. **Inversion 1 (piece-as-variable)** — 1 day; cheapest fundamental
   change; tells us something about CP ordering for E2.
2. **Inversion 2 (edge variables)** ★ — 3-5 days; highest probability
   of structural insight; the unmatched edges in plateau states are
   the right object to address. **Best research bet.**
3. **Inversion 5 (ML-guided cell ordering)** — 3-4 days; replicates
   Blackwood's empirical tuning automatically.
4. **Inversion 4 (domain decomposition)** — week+; high novelty,
   publishable if it works.
5. **Inversion 6 (continuous relaxation)** — 2-3 days; different
   failure mode, informative either way.
6. **Inversion 3 (color-strand decomposition)** — week+; speculative.
7. **Inversion 7 (0-clue filter)** — half day; falsification test.

## Recommended starting move for the next session

**Inversion 1 first** (~1 day): build `VariableOrder::PieceMrv` in
the existing engine, run pt_e2 on 6 seeds, compare plateau to
baseline. Outcome shapes Inversion 2 effort:
- If plateau shifts ≥2 edges: piece-ordering matters; Inversion 2
  (more expensive) is more likely to pay off.
- If plateau identical: ordering is irrelevant; jump straight to
  Inversion 2 (which changes the variables themselves, not the order).

Either way, **commit to Inversion 2 as the multi-day project for the
next session.** Edge-variable formulation is the genuine cross-domain
reformulation we kept proposing but never built. Vol. 2 spent its budget
on calibration; vol. 3 should spend it on this.

---

## (entries follow as experiments run)
