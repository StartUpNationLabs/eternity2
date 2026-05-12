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

## Artifacts

- `scripts/v10_pca_piece_cloud.py`
- `scripts/v10_laplacian_spectrum.py`
- `output/v10_math/pca_piece_cloud.{json,txt}`
- `output/v10_math/laplacian_spectrum.{json,txt}`
- `RESEARCH_NOTES_10.md` — this file

No vol-9 files touched. No vol-7 files touched.

## Sources used

- `output/archive/pieces.txt` — canonical 256-piece set (read-only)
- vol-7 memory entries on Selby-Riordan generator and rare-color rule
- vol-8 `RESEARCH_NOTES_8.md` for the 469 ceiling calibration
