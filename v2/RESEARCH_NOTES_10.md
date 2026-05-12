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

## Probe #5 — careful re-mining of community corpus (the things we missed)

**Motivation**. Vol-8 grep'd for scores and named techniques. Probe #4
showed we missed a major Discord post by grepping the wrong keywords.
User pushed back: re-read the corpus carefully for similar misses.

**Method**. Intent-keyword greps (artifact: `output/v10_remine/*.txt`):
- `forcing_claims.txt` — "the only", "exactly one", "always", "must be"
- `importance_claims.txt` — "important/significant/key piece"
- `specific_piece_mentions.txt` — `piece #?[0-9]+`
- `ring_structure.txt` — "ring", "shell", "onion", "core"
- `multiset_budget.txt` — "color budget", "frequency", "distribution"
- `proofs_invariants.txt` — "theorem", "invariant", "necessary"
- `insights.txt` — "noticed", "trick is", "key is"
- `symmetry.txt` — "parity", "chirality", "orbit"
- `obstructions.txt` — "stuck", "stall", "wall", "barrier"
- `personal_observations.txt` — "I noticed", "It turns out"

### What probe #5 surfaced

**1. The "xtal shell ladder" (groups.io 105182887, 2007-09-30).**
xtal computed and published the exact onion-decomposition difficulty
ladder for E2 *under random-shell-fill-then-backtrack*:

| Shell | Cum. edges | Cum. pieces | Δ pieces | xtal's empirical time |
|------:|-----------:|------------:|---------:|-----------------------|
| 1 (border) | 60 | 60 | 60 | seconds |
| 2 | 168 | 112 | 52 | minutes |
| 3 | 260 | 156 | 44 | hours |
| **4** | **336** | **192** | **36** | **never reached complete** |
| 5 | 396 | 220 | 28 | — |
| 6 | 440 | 240 | 20 | — |
| 7 | 468 | 252 | 12 | — |
| 8 (center) | 480 | 256 | 4 | — |

**Significance**. xtal's 2007 stall at 192 placed is in Hopfer's 2021
202-206 band — same wall, 14 years apart, independent observation. This
is the **strongest empirical evidence we have that the obstruction is
located at the shell-3-to-shell-4 boundary**. It motivates a focused
study of the *third-to-fourth ring transition* as the critical regime.

**2. "Rotation Sets" subculture (groups.io 2007-2008).**
A "Rotation Set" = an assignment of one rotation per piece such that
for each color: count(N) = count(S) AND count(E) = count(W) across the
whole set. This is dvholten's later-named **EMPI #2** invariant.

Community results (eternitynut, Dave Clark, antminder, dietergehrke,
moucherostre, the_solva — 2007 to 2008):
- Astronomical number of valid Rotation Sets exist for canonical E2.
- antminder reported a checker at **4200 rotation-sets/sec** by 2008.
- **Using rotation-sets as backtracker seed produced max 56 placed**
  — *worse* than ordinary top-down backtracking.

**Significance**. **EMPI #2 is necessary but very far from sufficient.**
The community already explored using rotation-sets as a feasibility
oracle and it failed. **This forecloses a research direction we might
have tried**: precomputing rotation sets to seed search is a known
dead end. Save the energy.

The deeper point: dvholten's 2013 "tile-set tileability oracle"
question (groups.io 105203289) — "is there a property of the
unordered tile set that decides whether it can form a square, faster
than backtracking?" — is **STILL OPEN as of 2013** and has not been
answered in the corpus since.

**3. dvholten's edge-matching puzzle invariants** (groups.io
105203289, 2013-05-13). Named formally in this thread:

- **EMPI #1**: every color must appear an even number of times across
  all edges of all pieces. (Trivially satisfied for any well-formed
  edge-matching puzzle, since each internal join contributes 2 sides.)
- **EMPI #2**: there must exist a rotation assignment such that for
  each color, count(N)=count(S) AND count(E)=count(W).

Plus dvholten's **q2 open problem**: distinguish a valid puzzle from
a color-swapped (broken) puzzle by tile-set property alone, without
backtracking.

**Significance**. EMPI #1/#2 are now **named** in the community
lexicon. EMPI #2 is computable, expensive (rotation-assignment
satisfiability — likely the right framing is a flow network or
constraint program). We do not currently use it as a propagator;
**neither did any community member successfully**.

**4. Michael Bastion's "KEY tile" claim** (groups.io 105187400,
2008-01-31). Claimed there is exactly one tile that "sets the board"
— not one of the 5 known hints. Bastion knew which tile but never
disclosed; possibly a deliberate misdirection per his own caveat.
**Unfalsifiable from this thread alone.** Worth lower priority than
provable structural facts but worth keeping for future eye-test of
plateau corpus boards.

Same thread also surfaces a verifiable observation: **"two types of
combinations: one had more high-numbered tiles on the left hand side
while the other had more high-numbered tiles at the top"** — a
**spatial bias in piece-ID distribution** across plateau states. This
is testable on vol-6/7's plateau corpus.

**5. Michael Field "parity" subculture** (multiple threads,
2008-2010). The community has its own "parity" idea distinct from
vol-7's H2 chessboard-parity. Field's parity is **pattern parity** —
a per-color-position constraint, related to EMPI #2 but applied
locally (per-row, per-column, per-region). Multiple threads
("Hole filling", "Is this obvious?", "Analysis of edge pieces",
"2x2s"). Field's own assessment in 105190624 (2008-04-20): *"The
problem with parity is that you can usually only prove with certainty
[…]"* — he never published a working propagator.

**Significance**. Worth a separate vol-11 probe specifically on
"Michael Field's parity papers" to see if any of the local-parity
ideas produce non-vacuous propagators on the canonical piece set.

**6. xp2 "checkerboard half-placement" idea** (Discord, 2026-01-29).
Place pieces on one color of a chessboard-coloring of the 16×16 grid
(128 cells); backtrack the other 128. This halves the immediate
branching depth. onesmallstep claims "If you can get a working
checkerboard at least halfway down the board, you're almost
guaranteed a solution." Untested in the corpus; **could be a vol-11
build**.

**7. onesmallstep "1216 2×2 sub-tilings in the top-left corner"
(Discord, 2026-01-29).** Concrete count of 2×2 tilings using only
hint pieces + their neighbours in the upper-left quadrant. Verifiable;
not currently in our propagator suite. Direct vol-11 candidate.

**8. Markus Zajc "possibility matrix"** (groups.io 105192710,
2008-09-10). The MRV (most-restricted variable) heuristic, named
explicitly. Vol-7 already uses MRV; this confirms vol-7's variable
ordering was reinventing well-known craft. Not a new finding for us.

**9. Johannes Lindé "invariants" hint** (groups.io 105198823 +
105201420, 2010-2011). Claimed to have studied invariants but
admitted he lacked math skills to attack them. **Vague; discount as
aspiration** unless he ever published.

### Methodological note

**Six discrete structural ideas missed in vol-8.** All were in the
community corpus before 2014. Vol-8's grep methodology was wrong:
score- and method-name-centric grep misses *structural claims* and
*folkloric observations*. A complete corpus mining needs both axes:
score/method *and* intent-keyword.

The vol-8 catalogue still stands for what it covered (Verhaard SA,
Blackwood scheduled relaxation, anr_56 Eulerian, etc.). Probe #5 adds
six new entries to the community-technique catalogue:

| # | Technique / fact | Source | Status |
|---|---|---|---|
| C-1 | xtal shell ladder + shell-4 wall | xtal 2007 | empirical, replicable today |
| C-2 | Rotation Sets / EMPI #2 oracle | eternitynut et al. 2007-2008 | known dead-end as seed |
| C-3 | EMPI #1/#2 formal invariants | dvholten 2013 | named, EMPI #2 unused as propagator |
| C-4 | "Tileability oracle" open problem | dvholten 2013 | OPEN, would be transformative |
| C-5 | M. Field "pattern parity" | M. Field 2008-2010 | partial; unclaimed propagator |
| C-6 | xp2 checkerboard half-placement | xp2 2026 | untested |

## Probe #7 — groups.io top-thread per-thread reading

User pushed back on grep methodology, then suggested using a `docs/`
folder if notes get too big. Probe #7 implements that: read complete
groups.io threads (using `scripts/v10_thread_reader.py`) and dump
structured notes under `docs/community-mining/`. One file per major
thread or theme.

**Threads read end-to-end so far** (out of 2346 total, of which ~30
have ≥25 messages):

| # | Thread | Msgs | Date range | Note file |
|---|--------|-----:|-----------|-----------|
| 1 | SAT | 82 | 2011-2026 | [01_SAT_thread.md](docs/community-mining/01_SAT_thread.md) |
| 4 | Design the hardest puzzle | 54 | 2007-08 | [02_Design_the_hardest_thread.md](docs/community-mining/02_Design_the_hardest_thread.md) |
| 13 | Algorithmic Challenges related to E2 | 44 | 2010-06+ | [03_Algorithmic_Challenges_thread.md](docs/community-mining/03_Algorithmic_Challenges_thread.md) |
| 17 | Interior Rectangles | 40 | 2008-03 | [04_Interior_Rectangles_thread.md](docs/community-mining/04_Interior_Rectangles_thread.md) |
| 60 | A method to prune E2 search space by 17-30%+ | 26 | 2026-01 | [05_Joe_pruning_method_thread.md](docs/community-mining/05_Joe_pruning_method_thread.md) |
| 46 | Estimated number of solutions w/ and w/o hints | 28 | 2024-01 | [06_Solution_count_estimates_thread.md](docs/community-mining/06_Solution_count_estimates_thread.md) |
| 32 | Two-stage solution process | 32 | 2025-05 | [07_Two_stage_solution_thread.md](docs/community-mining/07_Two_stage_solution_thread.md) |
| 20 | Highest points (of 480) with 5 hints | 38 | 2023-03 | [08_Highest_5hints_thread.md](docs/community-mining/08_Highest_5hints_thread.md) |
| 28 | EternityII Solver (Blackwood release) | 34 | 2020-09+ | [09_Blackwood_solver_thread.md](docs/community-mining/09_Blackwood_solver_thread.md) |

**Most session-defining single findings (cross-thread)**:

1. **The canonical E2 solution count** (probe #6, msg from McGavin):
   ~14,702 expected solutions with just the start piece; ~4×10^-8 with
   the 5 hints → **the canonical 5-hint E2 almost certainly has
   exactly 1 solution**. Authoritative source: Peter McGavin's C
   implementation of Brendan's Complex Theory.

2. **Brendan Owen's complete model** (Two-stage thread, May 2025):
   - 10^38 distinct outer frame configurations
   - 10^34 inner 14×14 solutions
   - 10^59 nodes searched to find one inner solution
   - 10^-27 conditional matching probability between any specific
     border and any specific interior

3. **Blackwood's complete 469 algorithm** (Blackwood thread, Nov 2020,
   msg #31): heuristic-side exhaustion at piecewise-linear rates +
   12 scheduled break indices `[201, 206, 211, 216, 221, 225, 229, 233,
   237, 239, 241, 256]` + parameter `heuristic_sides = [17, 2, 18]`.

4. **Joe's prune-back-to-depth-150 policy** (Joe thread, Jan 2026):
   17-49% search-space reduction on the E2-like puzzle. Immediately
   adoptable in vol-9's backtracker.

5. **The shape-and-teeth invariant** (lindstrom thread, May 2011, via
   McGavin): partial-board state can be fingerprinted by exposed-edge
   colors + remaining-piece-set. If two partial states have identical
   fingerprints, the sub-tree only needs searching once. Not in our
   solver-engine.

6. **The 17-color phase transition formal anchor** (SAT thread, Jan
   2023, Carles Mateu): E2 is GEMP-F with SAT phase-transition at 17
   interior colors. Selby-Riordan picked 17 colors deliberately.

7. **Marijn Heule's 2008 SAT-encoding paper** is the canonical
   reference: `http://www.cs.cmu.edu/~mheule/publications/eternity.pdf`.

8. **The "shell ladder" with shell-4 wall** (probe #5 C-1, plus
   confirmation in Interior Rectangles thread): each onion ring inward
   is harder; shell 4 (192 placed) is the wall. Aligns with Hopfer's
   202-206 band and Joe's "70% time at depth >150" finding.

**Methodological note**: the per-thread approach is producing roughly
3-5 substantive items per thread. At 30 substantive threads × 4 items
each → ~120 distinct facts to absorb. The vol-8 grep got perhaps 15-20
of these. Per-thread reading is **far more productive**, at the cost
of context.

## Probe #6 — full Discord end-to-end read (1198 messages, 2021-11 → 2026-05)

**Method**. Read the entire Discord export start-to-finish in 4 chunks
(350 messages each), no grep filtering. User pushed back after probe #5
that grep misses signal; full read confirms many additional substantive
items missed by both vol-8 grep and probe #5 intent-keyword grep.

### New high-value findings

**A. Joshua Blackwood is in the Discord and talked extensively** (Nov
2024). Direct first-hand statements from the 470-holder:
- "470 took 1 month on my home PC."
- "Maybe 150 hours in total" of work, spread over ~3 months during COVID.
- "No hints" for his 470.
- **"Algorithm makes enormous improvements. Good logic makes you
  1000000x better at solving partial solutions."** (verbatim).
- His earlier hardware: AMD Threadripper 3970x. Now comparable to
  desktop CPUs (9950x, 14900k).
- **Empirical scaling laws** (Dec 2021): *"a 471 will be 10^19 times
  harder than a 458"*, *"getting 1 fewer break is about 30-50x harder"*.
- "I've never tried for a 471. Stopped my efforts at 470."
- **His 470 code is on GitHub for everybody to see** —
  `github.com/jblackwood345/EternityII_Solver`.

These are direct, first-person, on-the-record. **Strongest empirical
calibration source we have for the regime above 467.**

**B. Stall-point ladder** (multiple independent observers, 2007-2026):

| Stall ~depth | Observer | Year |
|------:|----------|----:|
| ~76-83 | onesmallstep (linear, can backtrack to 76 but stuck above last hint) | 2024 |
| ~84 | onesmallstep (linear backtrackers get stuck around piece 84) | 2025 |
| ~175 | onesmallstep (internal 14×14: gets to 175 then slows) | 2026 |
| ~192 | xtal (shell 4 wall, never complete shell 4) | 2007 |
| ~197-217 | onesmallstep (197 with all hints, 217 spiral-in slow) | 2025-2026 |
| ~202-206 | Hopfer (stall band on naive backtracker) | 2021 |
| ~213-221 | Hopfer (jump 5-8 pieces then die) | 2021 |
| ~225-230 | reinout_ (4 separate 229s found, no 230) | 2025 |

This is the **empirical scaling ladder of the obstruction**, attested
across 19 years and at least 5 independent observers. The two
phenomena to explain: (1) why does each stall band exist?
(2) why is each one harder than the last by ~30-50x?

Vol-9 / vol-11 could fit a model: if each stall is empirically
~50x harder than the last, the geometric sequence 460 → 461 → ... 470
predicts the 470 record took ~50^10 ≈ 10^17 nodes — consistent with
Blackwood's 1-month home-PC run if his node rate is ~100M/s. Sanity
check: 100M nodes/s × 86400s × 30 days ≈ 2.6×10^14, off by 10^3 —
but he had threading and pruning; order-of-magnitude consistent.

**C. Concrete inter-piece compatibility tables** (onesmallstep Jan 24,
2026). Published in the Discord:

- The **9 border pieces** that can connect directly to piece 62: {5,
  10, 17, 19, 26, 27, 30, 49, 53}. For each, how many rotations of
  piece 62 fit (2, 1, 1, 1, 2, 2, 1, 2, 1 respectively).
- The **interior-piece-adjacent-to-each-corner** tables: corners 1 &
  2 share {5, 7, 15, 22, 24, 25, 37, 42, 45, 50, 52, 57}; corner 3 has
  {6, 11, 19, 20, 26, 31, 33, 40, 43, 49, 51}; corner 4 has {9, 16,
  27, 28, 29, 32, 41, 44, 56, 60}.
- **23 interior pieces are "unused"** in this enumeration — they
  cannot sit immediately adjacent to any corner: {8, 10, 12, 13, 14,
  17, 18, 21, 23, 30, 34, 35, 36, 38, 39, 46, 47, 48, 53, 54, 55, 58,
  59}.

**This is propagator-grade data already computed by the community**.
We can verify and embed it directly.

**D. The "complete internal 14×14" open problem** (onesmallstep,
multiple posts 2025-2026). After the border ring is placed, the
remaining 196 cells form a 14×14 interior sub-puzzle constrained by
inward-facing border colors. **"Nobody has found a complete internal
14×14"** in 19 years. onesmallstep's best is 175/196 placed.

This is a **specific, well-defined sub-problem** that vol-11 could
attack independently of the full puzzle. Either:
1. Find a complete 14×14 interior: this would be the first ever, and
   would directly enable extending to a full 256.
2. Prove no complete 14×14 exists for the canonical border ring:
   this would be an **impossibility result** comparable to the
   Mutilated Chessboard for the inner sub-problem.

Either outcome is a publishable finding.

**E. The "1216 top-left 2×2s with hints on"** computation (onesmallstep,
Jan 27, 2026). Exhaustively enumerated 1216 valid 2×2 corner
configurations under the canonical hint placements. **Zip file shared
as Discord attachment**. Worth verifying our solver computes the same
number. Also worth using as a **regression test** for any propagator.

**F. Border ring scarcity** (onesmallstep Jan 29, 2026): *"I've never
managed to find five complete outer rings."* Combined with vol-6's
~100k borders sampled, this gives a calibration: total border count
is well above 100k but onesmallstep's specific search method finds
≤4. Either his search method is too restrictive, or **the constraint
that the border permits a *valid* second ring drastically reduces
the count**. Worth resolving.

**G. Disagreement on hint utility** (multiple speakers, 2025): both
**onesmallstep** (*"I'm starting to wonder if those are the hints. I
get better results by not using them"*) and **reinout_** confirmed
the official top scores (Blackwood 470) **did not use the hints**.
**The community quietly believes the 5 official hints may be a
hindrance** for high partial scores, while still being mandatory for
the canonical scenario. This is a methodological warning we should
record — vol-9's Verhaard SA may want to test both with-hints and
without-hints regimes.

**H. Active research group** (dimkadimon9892, Jul 16, 2025). Claims a
group working on **Beam Search + ML-learned state-evaluation
functions** for combinatorial puzzles, planning to apply to E2.
Two arxiv papers referenced:
- `arxiv.org/abs/2502.13266`
- `arxiv.org/abs/2502.18663`
**This is the only research-group announcement in the entire Discord.**
Worth fetching the papers for vol-11 to know the prior art.

**I. JonkerVolgenant > Hungarian** (reinout_, Jul 16, 2025). For
matching-based metaheuristics, JonkerVolgenant is faster than
Hungarian and produces the same solution. Worth updating vol-7's
ALNS+MWPM machinery if it uses Hungarian.

**J. MIP / Max Clique cap at 7×7** (reinout_, Jul 27, 2025). Integer
programming and maximum-clique formulations work well up to ~7×7 but
do not scale to 16×16. Vol-7's MaxSAT was already empirically
verifying this; reinout_ confirms it's the consensus.

**K. Solver portfolios in active use** (onesmallstep, multiple):
- Java solver from 2009 (Eternity Editor) — used by many.
- SpecBAS solver (his own, 80s BASIC re-implementation).
- `puzzlingaddiction.com/et2js/worker3.html` and `worker16.html` —
  JavaScript browser solvers.
- `github.com/GrafSpiel/CUBETS/tree/main` — Python solver named
  CUBETS (described as "broken but works"; mentions ZLA phase, local
  search, SAT subproblems).
- `github.com/jwortmann/Eternity2Puzzles.jl` — Julia package, GUI.
- `github.com/StartUpNationLabs/eternity2` — the user's own C++
  solver, posted by neoteristis (= user) Apr 2025.

**This is a third-party-solver catalog** vol-8 missed entirely.

**L. Heuristic recommendation: "use up certain colors early on"**
(reinout_, Jul 27, 2025). Concrete advice for backtracker heuristic:
prioritize placing pieces with **rare colors** early. Aligns with
vol-7's `project_e2_rare_opposite_rule.md` discovery; **confirms
the community arrived at a related heuristic empirically**.

**M. The 2007 arthur089454 SAT/CNF posting** (Nov 30, 2021). A user
posted **explicit CNF clauses** for E2, including encoding
piece-position variables x_{i,j} and color-position variables y_{j,c}
with at-most-one constraints. Looks like a paper-style SAT
formulation. Worth retrieving — could indicate vol-7's MaxSAT
formulation was unique or partly reinvented from this.

### Items still unresolved

- onesmallstep's *"with neighbour checking"* custom solver: code
  not shared explicitly. Mechanism is a strong AC-3-like adjacent
  feasibility check.
- The two 470 boards "are almost the same" claim: testable on the two
  decoded 470 JSONs in `output/community_corpus/`.
- The "e202.txt file in this server" referenced by quinnkindaexists
  (Feb 25, 2025): community piece-data file shared via Discord
  attachments, may have notation we should match.
- Bastion's 2008 "KEY tile" (still uncited and undisclosed).
- arxiv papers 2502.13266 and 2502.18663: not yet fetched.

### Updated catalogue

The probe #5 catalogue C-1 through C-6 expands by:

| # | Technique / fact | Source | Status |
|---|---|---|---|
| C-7 | Blackwood scaling laws (50x per break, 10^19 total) | jblackwood3 2021 | empirical, calibration anchor |
| C-8 | Concrete connectivity tables for piece-62 + corners | onesmallstep 2026 | directly usable; verify on our data |
| C-9 | "Complete internal 14×14" open sub-problem | onesmallstep 2025-26 | well-defined; vol-11 candidate |
| C-10 | 1216 top-left 2×2s with hints | onesmallstep 2026 | regression test data |
| C-11 | Hint-utility debate: top scores didn't use hints | onesmallstep, jblackwood3 | methodological note |
| C-12 | JonkerVolgenant > Hungarian | reinout_ 2025 | algorithm replacement |
| C-13 | Beam Search + ML eval (active research group) | dimkadimon 2025 | unpublished work in progress |
| C-14 | arthur089454 SAT/CNF formulation (2021) | discord | needs detailed reading |

### Methodological reflection

**Three passes** on this corpus produced three different catalogues:
- Vol-8 (score- and method-name-grep): 5 community techniques.
- Probe #5 (intent-keyword grep): 6 additional items.
- Probe #6 (full read): 14 additional items + 1 calibration anchor.

**Returns are still increasing on the full-read pass.** This means the
intent-keyword sieve was missing roughly **2-3x the signal** that
existed. Recommendation: **for high-value, bounded-size corpora
(Discord = 1198 messages, groups.io threads ≤ 50 messages each), full
read is the correct method**. Grep is only for corpora too large to
read (e.g., the 11k groups.io messages as a single bag — but per-thread
reading is still feasible).

Next session should consider full reading of the remaining
high-signal threads from probes #5 catalogue items C-1 to C-6 (the
xtal shell-ladder thread, dvholten EMPI thread, Rotation Sets
subculture threads) for full context.

## Next steps for vol-9 / vol-11 (from probes #4, #5, #6)

These are concrete, ready-to-build propagators. They are independent —
each can be implemented and tested in isolation.

### NS-1: edge-piece inward-color multiset equality propagator

**Statement**. The 56 edge pieces have rotation-invariant inward
colors. Their multiset M_in (a length-22 vector counting how many
edge pieces inward-face each color) is a **fixed property of the
puzzle**, computable once. In any valid solution, the multiset of
*second-ring outward-facing colors* must equal M_in *exactly*.

**Strength**. Strict equality, not inequality. Not generator-defeated
(follows from piece identity). At any partial placement of the
second ring, deviation from M_in by even one element is an immediate
prune.

**Cost**. O(1) to compute M_in upfront. O(1) per second-ring piece
placement to update a running count. Negligible runtime overhead.

**Where it plugs in**. `crates/solver-engine/src/propagators/` as a
new `second_ring_multiset_eq` function. Wired into EngineConfig as
a bool toggle (per the vol-9 convention).

**Expected gain**. Unknown without measurement, but it's the
strongest static-equality propagator surfaced in any vol so far.
Probably nonzero where Eulerian was vacuous, because this constraint
depends on which edge pieces are placed (not just whether the border
is closeable).

### NS-2: piece-17 and piece-38 second-ring forcing propagators

**Statement (NS-2a)**. Piece 17's inward edge is always color `k`. So
the second-ring cell adjacent to piece 17 must carry color `k` on the
side facing piece 17. The 44 interior pieces containing `k` on at
least one edge are the only candidates for that cell; the other
196−44 = 152 interior pieces are forbidden from sitting adjacent to
piece 17 in the second ring.

**Statement (NS-2b)**. Same for piece 38 and color `l`: 42 candidates,
154 forbidden.

**Cost**. O(1): precompute the candidate lists for `k` and `l` once.
At the search-time placement of piece 17 (resp. 38), apply the
domain reduction to the adjacent second-ring cell.

**Where it plugs in**. Either as a static domain restriction during
problem setup, or as a propagator hook fired on piece-17/38
placement.

**Expected gain**. Modest (~78% domain restriction on two specific
second-ring cells), but free.

### NS-3: piece-62 anti-hint forbidden positions propagator

**Statement**. Piece 62 cannot sit cell-adjacent to any of the 5 hint
pieces in any rotation with any of 4 adjacency types. Pre-search,
remove these (cell, rotation) entries from piece 62's domain.

**Cost**. O(1) lookup of forbidden cells (the 4 cell-neighbours of
each hint position, intersected with positions where the
adjacency-rotation actually triggers the forbidden match).

**Where it plugs in**. Initial-domain pruning during search setup.

**Expected gain**. ~14% domain restriction for piece 62.

### NS-4 (research, not propagator): generalize NS-1 to inner rings

The multiset-equality argument for the first/second-ring boundary may
extend: for each ring boundary in a spiral or onion decomposition, the
inward-facing multiset of the outer ring must equal the outward-facing
multiset of the inner ring. This is the **ring-boundary multiset
chain** — a sequence of strict equality propagators, one per ring.

The strength of each propagator depends on **how anisotropic the
multiset is** at that ring depth. The first-ring inward multiset is
maximally anisotropic (only border-adjacent colors); deeper rings
become more uniform as Selby-Riordan flatness kicks in. So expect
diminishing returns inward — but the first 2-3 ring boundaries
might all be useful.

**Cost**. A few hours of analysis to compute multisets per ring depth
and check if any inner-ring inversion is similarly forcing.

### NS-5 (methodology): re-mine the community corpus for missed claims

**DONE in probe #5.** Six discrete missed ideas surfaced. See probe
#5 section for catalogue C-1 through C-6.

### NS-6: shell-3-to-shell-4 transition focused study

**Statement**. xtal (2007) and Hopfer (2021) independently observed
the wall at ~192-206 placed pieces, which corresponds to **completing
shell 3 → starting shell 4**. This is the most-empirically-attested
obstruction in 19 years of community work. Focus a vol-11 study on
this specific transition: what happens to color-budget anisotropy,
local rotation-set feasibility, and mismatch distribution as the
search crosses shell-3-to-shell-4? Use vol-6/7's plateau corpus as
data.

**Why this isn't redundant with vol-7**. Vol-7 used PT/MAP-Elites
*globally*. NS-6 is a *focused depth-conditional study*. Different
question, different data slice.

### NS-7: EMPI #2 as a partial-board feasibility propagator

**Statement**. dvholten's EMPI #2 says: a valid set has some rotation
assignment with balanced N/S and E/W counts per color. For a
*partial* board (some pieces fixed, others free), the propagator
asks: do the **unplaced pieces, in some rotation, balance the
*deficit* the placed pieces leave**? If no, prune.

**Why this isn't redundant with the failed "rotation-set seeding"**.
The 2008 community tried EMPI #2 *as a global seeding constraint* —
generated valid rotation sets then tried to extend. That failed
because too many rotation sets exist. NS-7 inverts: use EMPI #2 as a
*pruning* check during backtracking, not a seeding source.

**Cost**. Per-backtrack, EMPI #2 reduces to a network-flow
feasibility check on the remaining piece pool — polynomial.
Estimated 1-2 days Rust if integrated cleanly into the propagator
suite.

**Expected gain**. Unknown; depends on how anisotropic the deficits
become as search progresses. Worth trying after shell 3.

### NS-8: piece-ID spatial bias check on plateau corpus

**Statement**. Bastion (2008) observed that plateau states cluster
into two visual types: "high-numbered tiles on the left" vs.
"high-numbered tiles at the top". Easy to verify on vol-6/7's
plateau JSONs in `output/v6_plateaus/` (if extant) or vol-7's MAP-
Elites archive.

**Cost**. ~1 hour Python. Plot the centroid of placed piece-IDs per
plateau, see if the distribution is bimodal.

**Why it matters**. If the bimodal structure exists, the two modes
correspond to two distinct basins of attraction in the search
landscape. This is a **structural fact about the search trajectory**
that nobody has measured. Could justify a dual-strategy portfolio.

Status of NS-1 through NS-8: **proposed, not assigned**. Vol-9 may
pick these up when its Verhaard SA run completes; vol-11 may build
them as its mission.

### NS-9: verify the two 470 boards "are almost the same"

**Statement** (onesmallstep, Jul 2025). The two known 470 boards
(Blackwood's and the Jef-Bucas variant) are visually/structurally
nearly identical. Decoded JSONs are at
`output/community_corpus/groups_183676823_470.json` and
`output/community_corpus/groups_197822677_470.json`. Cell-by-cell
diff would quantify the overlap.

**Cost**. 30 minutes Python. Use existing `scripts/compare_boards.py`.

**Why it matters**. If two near-identical 470s exist, the 470
attractor is **narrow** — vol-9's PT/SA may converge there
deterministically and miss the 471 escape route entirely. Vol-7's
finding that PT has a deterministic ceiling on a given border is
consistent with this. Specifically: the 471 may require **leaving
the 470 attractor**, not improving within it.

### NS-10: solve the internal 14×14 sub-problem

**Statement** (onesmallstep, multiple posts). Given a complete border
ring with valid inward-facing colors, the **14×14 interior is a
self-contained sub-puzzle** with 196 cells and 360 internal joins.
**No-one has ever found a complete one** in 19 years.

**Approaches**:
1. Vol-7's MaxSAT machinery already optimised a 45-cell sub-puzzle.
   Scaling to 196 cells with the 14×14 boundary as fixed external
   constraint is technically feasible — same encoding, just bigger.
2. Verhaard SA (vol-9's main build) restricted to the 196 interior
   pieces is exactly the natural fit. Run vol-9 with `--only-
   interior` after fixing a known-good 470 border.
3. Existence-or-impossibility: if MaxSAT can prove infeasibility for
   the specific border in the 470, that's the strongest possible
   negative result and points to the impossibility of 480/480 with
   that border.

**Cost**. Variable. The MaxSAT impossibility attempt is bounded by
solver runtime; the constructive attempt is open-ended.

### NS-11: read the arxiv papers 2502.13266 and 2502.18663

**Cost**. 1 hour each.
**Why it matters**. The only active-research-group reference in the
Discord. Beam Search + ML eval is genuinely novel for E2 and could
either be a great direction for us or a dead-end someone else is
about to confirm. Either is useful information.

### NS-12: fetch and decode the Discord attachments

**Specifically**:
- `Top-left_2x2s_with_all_hints.zip` (onesmallstep, Jan 27 2026) — 1216
  pre-enumerated 2×2 corner configs.
- `2x2s_1_with_hints_on-1.zip` (onesmallstep, Jan 28 2026) — followup.
- `piece_62_possibilities.png` (Jan 18, 2025) — visual annotation of
  piece 62's connection structure.

All are public Discord CDN attachments. Worth caching locally.

### NS-13: try the without-hints regime for vol-9's SA

**Statement**. Multiple speakers (onesmallstep, jblackwood3, reinout_)
confirm the canonical 470 and several 469s were found **without
using the 5 official hints**. The hints may be a hindrance for high
partial scores even though they are mandatory for the canonical
scenario.

**Cost**. Trivial: an existing flag on vol-9's solver, if not already
present.

**Why it matters**. If vol-9's Verhaard SA performs significantly
better without hints, we have a falsifiable test of the
"hints-are-a-hindrance" hypothesis. Either outcome is useful.

**Priority ranking for vol-11** (revised):
1. **NS-1** (edge-piece inward multiset equality) — strongest static
   propagator, cheapest to build.
2. **NS-9** (verify two 470 boards are nearly identical) — 30
   minutes, calibrates the 470-attractor structure.
3. **NS-13** (without-hints regime) — trivial flag, tests an
   empirical claim from the community SOTA holders.
4. **NS-12** (fetch Discord attachments) — propagator-grade reference
   data already computed by the community.
5. **NS-7** (EMPI #2 as partial-board propagator).
6. **NS-2/3** (piece 17/38/62 forcing).
7. **NS-11** (arxiv papers).
8. **NS-10** (internal 14×14 sub-problem) — long-running but
   publishable result.
9. **NS-8** (spatial bias on plateaus) — diagnostic.
10. **NS-6** (shell-4 transition study).
11. **NS-4** (generalize multiset chain to inner rings).

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
