# RESEARCH_NOTES_10.md — vol-10: mathematical / geometric probes (side-quest)

**Session**: 2026-05-12, runs concurrently with vol-9 (vol-9 is doing the
algorithmic build of Eulerian propagator + Verhaard SA; vol-10 is purely
analytical, no overlap with vol-9 files).
**Calibration**: same as vol-9 — verified community ceiling is 469/480.
**Mandate**: test whether mathematical / geometric reframing surfaces
structural invariants we have been missing. Two cheap probes confirmed
with the user; both are "tells-you-something-either-way" experiments.

## Mission statement

User question (paraphrased): "could a more mathematical or geometric way of
seeing the problem lead to better results — or the other way around?"

Answer hypothesis going in:
- *Geometric*: there are mathematical objects (piece point-clouds, graph
  Laplacians, Morse-saddle counts) the community and academic literature
  never computed. They are cheap to compute. They could either surface a
  new structural invariant or — equally interesting — prove the
  Selby-Riordan generator engineered the puzzle to defeat them.
- *Operational counter*: the community has historically advanced by craft
  moves (Verhaard swap-annealing, Blackwood scheduled relaxation, Hopfer
  piece-budget), not theorems. The right answer might be more ablations,
  not more math.

Vol-10 ships the two cheapest *geometric* probes first. If both come back
negative, that swings the balance toward the operational track for vol-11.

## Probes performed

### Probe #1 — PCA on the piece-histogram point-cloud

**Setup**. Embed each of the 256 pieces as a length-23 histogram vector
(count of each color across its 4 edges, order ignored). The full matrix
is 256×23. We also compute a restricted version on the 196 interior
pieces over 22 colors (dropping border-'a' which only appears on
corners/edges).

**Code**: `scripts/v10_pca_piece_cloud.py`.
**Outputs**: `output/v10_math/pca_piece_cloud.{json,txt}`.

**Raw results**:

| Matrix              | k for 80% var | k for 90% | k for 95% | top-3 var-ratio |
|---------------------|--------------:|----------:|----------:|----------------:|
| All 256 × 23        | 14            | 17        | 19        | 0.248           |
| Interior 196 × 22   | 12            | 14        | 15        | 0.251           |

**Baseline comparison**. For 256 iid-uniform multinomial draws of size 4
over 22 colors, the expected per-PC variance ratio is 1/22 ≈ 0.0455. The
observed top-1 PC ratio (interior) is 0.0856 → **1.88× the iid baseline**.

**Interpretation**.

The interior piece cloud is **mildly anisotropic**: it shows ~2× the
spread along the dominant direction that pure uniformity would produce,
but it requires **12 of 22 principal components to capture 80% of its
variance**. Compare:

- A strong 3-cluster structure: top-3 would explain >70% of variance.
- A flat (iid-uniform) cloud: top-3 would explain ~14%.
- E2 interior: top-3 explain **25.1%** — between the two, much closer to
  uniform.

**This confirms the Selby-Riordan flatness hypothesis quantitatively**
for the first time on our stack. Vol-7's M1 agent surfaced the qualitative
claim ("generator flattens 2×3 tileability"); probe #1 puts a number on it
at the histogram level. The puzzle was engineered against any heuristic
that hopes to cluster pieces into "types" — the structure is diffuse
across all 22 color axes, not concentrated in 2-3 dominant ones.

**Operational implication**. Histogram-based piece-grouping heuristics
will not beat 1.88×-uniform performance. **Verhaard's 2×2-tilings metric
is the right granularity**, not histograms — it captures pairwise
co-occurrence (interactions between two pieces), which is invisible to
single-piece histograms. vol-9's #2 build is on the right axis.

The interior cloud's top-1 PC loadings are spread across many colors with
no single dominant axis — there is no "rare-color principal direction"
visible at the histogram level. This is **not** a falsification of
[[project_e2_rare_opposite_rule]] (the rare-color rule is about *piece
edge configuration*, not histograms); it just says you can't see the rule
in this projection.

**Negative finding status**: probe #1 result is **partial**. It rules out
strong low-dimensional histogram structure but is consistent with subtler
pairwise structure. Closes the door on "piece histograms" as a feature
class; leaves "pairwise piece interactions" open.

### Probe #2 — graph Laplacian spectrum of the constraint graph

**Setup**. The 256 cells of the 16×16 grid form the vertices; the 480
internal joins form the edges. We computed three Laplacians:

1. **L₀**: plain (uniform-weight) grid Laplacian. Reference.
2. **L_freq**: weights ∝ 1 / (sum of squared color frequencies) on the
   piece set. Captures static color-pair-collision difficulty.
3. **L_avail**: weights ∝ (number of piece-rotation pairs compatible
   with each color-pair). Captures static piece-availability.

**Code**: `scripts/v10_laplacian_spectrum.py`.
**Outputs**: `output/v10_math/laplacian_spectrum.{json,txt}`.

**Raw results**.

| Laplacian | λ₂ (algebraic connectivity) |
|-----------|----------------------------:|
| L₀ (grid) | 0.0384293 |
| L₀ analytic 2(1 − cos π/16) | 0.0384293 |
| L_freq | (rescaled L₀) |
| L_avail | (rescaled L₀) |

**Numerical λ₂ matches the analytic 16-path Laplacian Kronecker-sum
prediction to <1e-9** — confirms the eigendecomposition is correct, and
confirms there is no topological surprise in the grid.

The piece-set's color statistics are **spatially homogeneous**: every
internal join sees the same expected difficulty in the static analysis.
This makes L_freq and L_avail uniformly scaled copies of L₀ — no spatial
bottleneck emerges from static color/piece statistics.

**Interior color-collision probability** (Σ_c freq_c² over the 22
interior colors) = **0.0482**, vs the random-uniform 22-color baseline
of 1/22 = **0.0455**. Interior colors are uniform to within 6% — the
generator equalized them on purpose.

**Fiedler-vector partition**. The grid's λ₂ is **degenerate** (λ₂ = λ₃ =
0.0384, by symmetry). When eigenvalues are degenerate, the numerical
eigenvector basis is an arbitrary rotation within the degenerate
eigenspace; the diagonal cut numpy produced is mathematically valid but
no more meaningful than a vertical or horizontal mid-cut would be. **This
is not a finding; it's an artifact of the degeneracy.** Disregard.

**Interpretation**.

The plain grid Laplacian, with any spatially-homogeneous edge weighting,
produces a spectrum that *does not predict any of the empirical features
we care about*: it does not localize the corners-vs-interior asymmetry
(vol-5 finding), it does not predict the 449-453 plateau (vol-6), it does
not predict Hopfer's 202-206 stall, and it does not predict the 469
ceiling.

This means: **the search obstructions are NOT properties of the static
constraint graph**. They are **dynamic**: they emerge from the alldiff
(piece-uniqueness) constraint and the history-dependent local color
budgets that develop during search. The graph is just a substrate.

**Implications for direction**:

- **Static spectral analysis of the bare grid is closed as a research
  direction.** It will not surface structural invariants we can use.
- **Dynamic spectral analysis** — a Laplacian indexed by *partial-board
  state*, or a Laplacian on the *configuration graph* (states + 1-piece-
  swap edges) — is open and was not attempted. This is much harder
  (configuration graph has ~10⁴⁰⁰ nodes; needs sampling or a sparse
  representation) but it's the only spectral angle that *could* see the
  obstruction since the obstruction is dynamic.
- **The piece-availability Laplacian** is the right object **only if you
  let edge weights depend on what's already placed** — i.e., a sequence
  of Laplacians L(t) parameterized by placement depth. This is
  computable from vol-6/7's plateau corpus. **A genuine open question
  surfaced by probe #2**: does λ₂(L(t)) drop sharply at t≈202 (the
  Hopfer stall)? That would be the spectral signature of the obstruction.

**Negative finding status**: probe #2 result is **strong negative for
static analysis, suggestive positive for dynamic analysis**. Static
spectral direction closes; dynamic spectral direction opens (and is the
new candidate for vol-11).

## What vol-10 changes

**For vol-9** (in flight): no impact. Vol-9 is implementing the Eulerian
propagator (anr_56 2007) and Verhaard SA (2008). Both are independent of
the probes. The Verhaard 2×2-tilings metric is *confirmed* to be at the
right granularity by probe #1: histograms are too crude, pair counts are
where the structure lives.

**For memory**: two updates worth making:

1. **The Selby-Riordan flatness claim from vol-7 M1 is now quantified**:
   piece-cloud top-1 PC is only 1.88× the iid-uniform baseline; 12 of 22
   PCs needed for 80% of variance. The generator's design intent is
   visible in the eigenspectrum.
2. **Static spectral / geometric structural invariants are ruled out.**
   Save the energy of future agents on this. The puzzle is geometrically
   homogeneous at the static level; obstructions are dynamic.

**For vol-11+ (candidate directions surfaced)**:

- **Dynamic spectral analysis**: λ₂(L(t)) on placement-depth-indexed
  Laplacians, computed from vol-6/7 plateau samples. Half-day of work
  if we accept noisy estimates from corpus subsampling.
- **Pairwise piece-interaction PCA**: 2×2-tilings count matrix
  (196×196 if we restrict to interior pairs), then PCA *on the
  interaction matrix*, not the histograms. Verhaard's metric is the
  natural distance; PCA on its pairwise table would say whether
  *Verhaard's metric itself* is low-rank. This is the right direction
  to chase if histograms turned out too coarse.
- **Morse-saddle counting on the plateau corpus** (was originally
  proposed alongside probes #1 and #2). Vol-7's MAP-Elites archive +
  vol-6's 100k boards have the data; counting critical points by Morse
  index is a few hundred lines of Python. Still on the table for
  vol-11.

## Honest meta-conclusion

**The math is not going to save us alone**, at least not the static math.
The Selby-Riordan generator was effective: the puzzle's static geometry
is engineered to be featureless. Where the math *might* help is at the
**dynamic** level, where the alldiff constraint and the history-dependent
local color budgets create non-static structure that static analysis is
blind to.

This **reinforces the operational track** that vol-9 is on. Verhaard's
swap-annealing on a piece-set is, in disguise, an attempt to *create*
useful structure that the static geometry refuses to provide — by picking
180 pieces whose pairwise interactions are above average, you
*manufacture* anisotropy where the natural piece set has none. That's a
much subtler argument for the same algorithm, and it suggests:

- The right success metric for vol-9's SA inner loop is **explicit
  pairwise-interaction variance maximization**, not just total 2×2-tile
  count. A 180-piece subset with high *variance* in pairwise scores
  forces the backtracker to encounter sharper signals during search.
- The Verhaard "loser group" trick (place worst performers first) makes
  sense from this angle: it puts the algorithmic structure where the
  geometric structure is missing.

## Probe #3 — pairwise piece-interaction PCA (added in this session)

**Motivation**. Vol-10's interpretation of probe #1 flagged "pairwise
piece interactions" as the candidate next direction. Probe #3 tests
whether the pair-level interaction matrix is low-rank.

### Probe #3a — first attempt (histogram-collapsed)

**Setup**. For each ordered pair (i, j) of interior pieces, compute
M[i, j] = number of (rot_i, rot_j, adjacency) triples for which the
shared edge between i and j matches (4 rotations × 4 rotations ×
4 adjacency types = up to 64).

**Code**: `scripts/v10_pairwise_interaction_pca.py`.
**Outputs**: `output/v10_math/pairwise_pca.{json,txt}`,
`pairwise_interaction_matrix.npy`.

**Result**. M has rank **exactly 17**; top-10 PCs capture 80% of
variance. *Initially this looked like strong low-rank structure*.

**Algebraic check**. Direct calculation confirmed M = 4·H·Hᵀ exactly,
where H is the 196×22 interior-piece color histogram matrix from
probe #1. Reasoning: summing over the 4 rotations destroys positional
information; each rotation visits every edge at every position once;
so the rotation-summed pair score collapses to the inner product of
histograms.

**Honest finding**: probe #3a is **algebraically identical to probe #1**.
The rank-17 result is forced by H being 196×22 with H's spectrum
already known from probe #1 (top-PC ratio 1.88× iid baseline). Probe
#3a is not a new probe; it's probe #1 in a different basis. Discard
its naive interpretation.

### Probe #3b — position-aware (piece-rotation level)

**Motivation**. The right pair-level metric must NOT sum over rotations
— that's where the positional information lives. Treat each (piece,
rotation) as a separate entity: 196 × 4 = 784 piece-rotation tokens.

**Setup**. M₃[(i, r), (j, s)] = number of adjacency types (NESW) for
which the shared edge between piece-rotation (i, r) and (j, s) matches.
This is a 784×784 symmetric integer matrix with entries in {0..4}.

**Structural decomposition**. Each piece-rotation (i, r) maps to a
length-88 feature vector φ(i, r) over the 88 (color, position)
combinations (22 colors × 4 positions). With P the 88×88 permutation
swapping E↔W and N↔S blocks, we have **M₃ = Φ · P · Φᵀ** exactly
(verified by direct numerical equality).

**Rank result**.
- rank(M₃) = **65** out of 88 maximum.
- rank(Φ) = **65** as well — the 23-dimension deficit comes from
  linear dependencies among (color, position) features in the
  canonical piece set, NOT from M₃'s outer-product structure.

**Signed spectrum** (important correction from initial run).
M₃ is **not** positive semidefinite: its 65 nontrivial eigenvalues
split into **33 positive (max 184.8) and 32 negative (min -64.8)**.
This is mathematically correct: M₃ counts matches with a permutation
P that swaps E↔W and S↔N, which is not a PSD operator.

The honest measure of compressibility on a signed spectrum is the
Frobenius energy fraction (cumulative |λ|² / Σ|λ|²), not the
positive-only sum:

| k (by |λ|²) | cumvar |
|------------:|-------:|
| 16 | 50% |
| **37** | **80%** |
| 48 | 90% |
| 55 | 95% |
| 63 | 99% |

**Top |λ| by magnitude**: 184.8 (dominant by 2.6×), then a flat band
69.8 → 56.6 (alternating signs), then a long tail.

### Probe #3 — interpretation (corrected, twice)

**First-pass interpretation was wrong** (over-claimed 23/65 dims for
80% by dropping negative eigenvalues from the sum). The honest answer
is **37/65 ≈ 57% effective dimensionality** when negative eigenvalues
are counted — modest compression, not strong.

**Genuine residual finding**: among 88 possible (color, position)
features that a piece-rotation can carry, the canonical E2 set spans
only **65 independent combinations**. There are 23 linear
dependencies in the position-color feature matrix — the generator did
not fully randomize across (color, position). This is **real and
structural**.

But within that 65-dim subspace, the spectrum is **not** strongly
concentrated. M₃'s pair-interaction landscape is roughly half-rank
within the structurally-bounded subspace, with no dominant low-dim
archetype to exploit.

**Operational implication for vol-9 Verhaard SA — revised**:

The earlier draft proposed a fitness term β · variance_projection
onto the "top 23 PCs". With the corrected accounting, that recipe is
**less attractive** than I claimed: the top-37 PCs already include
both strongly-positive and strongly-negative directions of comparable
magnitude, and choosing only "top-by-magnitude" PCs would distort the
metric.

**A more defensible use** of the eigenstructure:
- The **rank-65 fact** can be used as a sanity invariant: any
  candidate piece set should span a 65-dim subspace; checking
  rank(Φ_subset) is O(180 × 88³) and cheap.
- The **23-dim dependency structure** identifies specific (position,
  color) features that are linearly redundant. These dependencies
  encode constraints the generator left in the piece set — they
  might be expressible as graph-theoretic statements about color
  flow, which would be testable with vol-9's existing color-count
  propagators. **This is the right vol-11+ follow-up.**
- The β · projection term I proposed earlier is **withdrawn** as a
  concrete vol-9 recommendation until we understand what the
  positive vs negative eigenvalues mean structurally. The math is
  honest but the operational story is not yet clear.

### What probe #3 changes in the meta-conclusion

Vol-10's earlier meta said "the math doesn't save us at the static
level" and recommended vol-9 stay on the operational track. Probe #3b
**does NOT meaningfully walk that back**:

- **Single-piece histograms are flat** (probe #1: 1.88× iid).
- **Pair-level with rotations summed is the same as histograms** (#3a:
  algebraic identity to probe #1).
- **Position-aware pair-level has 23 linear dependencies in the
  88-dim feature space** (#3b genuine finding). But within the
  resulting 65-dim subspace, the eigenspectrum is **mildly**
  compressible (37/65 dims for 80% Frobenius energy).

The rank-65 fact is real but it's not a knob vol-9 can directly turn.
The earlier draft of probe #3's recommendation (β · projection-
variance term in Verhaard SA's fitness function) was based on a wrong
accounting of the signed spectrum and is withdrawn.

**Net effect on vol-10's meta-conclusion**: nearly unchanged.
The static-spectral direction remains essentially closed; probe #3b
surfaced one structural fact (rank-65) but no immediately usable
operational signal. The operational track that vol-9 is on remains
the right priority.

**For vol-11+**: the rank-65 structure deserves investigation as a
graph-theoretic / constraint-propagation object (the 23 dependencies
in Φ encode invariants the generator left in the piece set; these
might be expressible as color-flow statements vol-9's propagators
can check). Non-linear extensions (kernel PCA, autoencoders) might
surface stronger structure but the cost-benefit looks weak given how
modest the linear result is.

## Probe #4 — significant pieces (verifies a Discord claim we missed)

**Provenance**. `onesmallstep` posted in Discord on 2025-01-18 and again
on 2026-01-29: "pieces 17 and 38 are significant, as is piece 62
internally. 17 and 38 have one unique edge pattern facing inwards, so
you know your second ring can only have one of each of those patterns
facing outwards. And 62 is the only internal piece that doesn't
connect to any hint." Vol-8's corpus mining grep'd for scores and named
techniques but missed this — it's exactly the kind of structural craft
move vol-8's catalogue ranked as "high P(>454)" but no specific
instance was extracted.

**Direct verification on the canonical piece set**.
Code: `scripts/v10_verify_significant_pieces.py`.
Output: `output/v10_math/significant_pieces.{json,txt}`.

| Claim | Verdict | Detail |
|------|--------|--------|
| Piece 17 has a unique inward edge color | **CONFIRMED** | piece 17 = `ackf`; color `k` appears as inward-facing on this piece alone among 56 edge pieces |
| Piece 38 has a unique inward edge color | **CONFIRMED** | piece 38 = `aelf`; color `l` appears as inward-facing on this piece alone |
| Exactly 17 and 38 have this property | **CONFIRMED** | no other edge piece carries a globally-rare-frequency-1 inward color |
| Piece 62 connects to no hint | **CONFIRMED** | piece 62 = `ggko`; cannot adjacent-match any of {139, 181, 208, 249, 254} in any of 4 rotations × 4 adjacency types |
| Piece 62 is the unique such interior | **CONFIRMED** | 195 of 196 interior pieces can adjacent-match at least one hint; piece 62 is the lone exception |

All five claims hold **exactly** on the canonical piece data. No
ambiguity, no statistical caveats — these are forced structural facts.

**Generalization (full ranking)**.

Edge pieces by rarest inward color:

| inward-color frequency ≤ | # edge pieces | IDs |
|-------------------------:|--------------:|------|
| 1 | 2 | **17, 38** |
| 2 | 8 | 9, 17, 22, 23, 36, 38, 39, 60 |
| 3 | 23 | 7, 8, 9, 14, 16, 17, 18, 22, 23, 24, 25, 29, 32, 36, 37, 38, 39, 40, 41, 46, 52, 59, 60 |

Interior pieces by hint-adjacency count (out of 5 hints):

| # hints matched | # interior pieces |
|---------------:|------------------:|
| 0 | **1** (piece 62 — the singleton) |
| 1 | 18 |
| 2 | 37 |
| 3 | 68 |
| 4 | 59 |
| 5 | 13 |

The distribution is roughly bell-shaped around 3 of 5, with piece 62 as
the lone outlier at zero.

### Operational implications — concrete, immediate

These are **propagator-grade exact constraints**, not heuristic
preferences. They are usable today:

**Constraint A (force from piece 17)**. In any valid solution:
- The cell *interior-adjacent* to piece 17's placement on the border has
  color `k` on its 17-facing edge. Color `k` is a *globally unique*
  inward edge color, so the cell adjacent to piece 17 is the **only**
  cell in the entire 16×16 with color `k` on that side.
- This **single-occurrence constraint on color `k`** can be propagated:
  whenever any interior piece-rotation with color `k` on some side gets
  considered, its placement is restricted to exactly the cell adjacent
  to piece 17 (and only with `k` on the correct side).
- Symmetrically for **color `l` and piece 38**.

**Constraint B (forbidden positions for piece 62)**. In any valid
solution, piece 62 cannot be cell-adjacent to any of the 5 hint pieces
in any rotation. With 5 hint positions in the canonical scenario, this
**forbids up to 5 × 4 = 20 cells × 4 rotations = 80 (cell, rotation)
placements** for piece 62 (some hint-adjacent cells may coincide if
hints are themselves adjacent, but the canonical 5 are not).

These two constraints **do not interact** — they constrain different
pieces and different cells. Both can be added as propagators
independently.

### How much pruning is this worth? (corrected after color-frequency check)

The first draft of this section over-claimed (said "color `k` appears
only twice in the whole puzzle"). **Correction**: color `k` has **48
total occurrences across all edges of all pieces** — it is *not* a
globally rare color. What's rare is `k` **on an edge piece's inward
side**: only piece 17 has this. Same for `l` on piece 38.

The honest constraint:

- **Constraint A1 (piece 17)**: piece 17 = `ackf` has its `a` (border)
  at one position and the cyclically-opposite position is `k`. **Under
  any rotation, that opposite-position character is preserved** by
  cyclic structure — so piece 17 always faces `k` inward, no matter
  which border (N/E/S/W) it sits on. The second-ring cell adjacent to
  piece 17 must therefore carry `k` on the side facing 17.
- **Constraint A2 (piece 38)**: piece 38 = `aelf`, opposite-of-`a` is
  `l`. Always faces `l` inward.
- **Constraint A3 (counting all edges with `a`-opposite preserved)**:
  by the cyclic-rotation argument, **every edge piece's "inward
  color" is fixed across rotations**. The unique-inward property of
  17 and 38 is therefore the **unique-globally-rare-inward** property,
  not a rotation-dependent fact.
- **Constraint A → second-ring partitioning**: piece 17's second-ring
  neighbor must come from the **44 interior pieces containing color
  `k`** on at least one edge. Piece 38's must come from the **42**
  containing `l`. Without 17 and 38 in the border, the second-ring
  cell adjacent to them would be unconstrained — with them, it's
  ≤44/196 = 22% of the interior pool. Modest, not dramatic.
- **Constraint B (piece 62)**: piece 62 cannot be cell-adjacent to any
  of the 5 hint pieces. Forbids ≤5 × 4 = 20 cells × 4 rotations = 80
  (cell, rotation) placements pre-search.

**These are real propagator-grade constraints, but more modest than my
first draft implied**. They reduce search-space domain sizes by ~78%
(for the second-ring cells adjacent to 17 and 38) and ~14% for piece
62's domain. Useful — and free, structurally — but not order-of-
magnitude search compression.

### Deeper structural fact uncovered

The cyclic-rotation argument above reveals a *more general* invariant:
**every edge piece has a deterministic inward color, independent of
rotation**. That means we can precompute the **inward-color
multiset of the 56 edge pieces** — a length-22 vector. The second
ring's outward-facing edge colors must form exactly this multiset.

This gives a **multiset-equality propagator** at the boundary between
the first and second rings: at any partial placement of the second
ring, the multiset of second-ring-outward colors placed so far must be
consistent with the inward-color multiset of the edge pieces already
placed. **This is a strict equality constraint** — much stronger than
the Eulerian connectivity check vol-9 found vacuous, because the
multiset equality is not generator-defeated (it follows from piece
identity, not piece-set statistics).

### What probe #4 changes in vol-10's meta-conclusion

The meta-conclusion from earlier ("static math doesn't save us") is
**partially overturned**. There exists static *structural* information
the puzzle does not defeat — but it lives at the **per-piece** level
(specific edge-color rarity, specific connectivity to hints), not at
the **per-puzzle spectrum** level. Probes #1, #2, #3 were looking at
the wrong granularity: they aggregated across pieces; the structure is
local-to-specific-pieces.

This reframes the "operational vs mathematical" question from earlier:
the productive math is **combinatorial structural analysis of
individual pieces**, not spectral analysis of aggregate matrices. The
community knew this; we re-derived it the hard way.

## Artifacts

- `scripts/v10_pca_piece_cloud.py` — probe #1
- `scripts/v10_laplacian_spectrum.py` — probe #2
- `scripts/v10_pairwise_interaction_pca.py` — probe #3a (kept for
  reproducing the algebraic-collapse finding)
- `scripts/v10_save_position_color_pcs.py` — probe #3b eigenbasis
- `scripts/v10_verify_significant_pieces.py` — probe #4 verification
- `output/v10_math/pca_piece_cloud.{json,txt}` — probe #1 results
- `output/v10_math/laplacian_spectrum.{json,txt}` — probe #2 results
- `output/v10_math/pairwise_pca.{json,txt}` — probe #3a results
- `output/v10_math/pairwise_interaction_matrix.npy` — 196×196 rotation-
  collapsed M (probe #3a)
- `output/v10_math/phi_matrix_784x88.npy` — Φ embedding matrix
- `output/v10_math/eigenvalues_65.npy` — signed eigenvalues of M₃
- `output/v10_math/piece_rotation_projection_784x33.npy` — projections
  (kept for reproducibility, NOT recommended as a vol-9 fitness signal)
- `RESEARCH_NOTES_10.md` — this file

No vol-9 files touched. No vol-7 files touched.

## Sources used

- `output/archive/pieces.txt` — canonical 256-piece set (read-only)
- vol-7 memory entries on Selby-Riordan generator and rare-color rule
- vol-8 `RESEARCH_NOTES_8.md` for the 469 ceiling calibration
