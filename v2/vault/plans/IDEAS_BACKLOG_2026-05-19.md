# Ideas Backlog — captured 2026-05-19 evening

User directive: "if you have ideas, note them somewhere to not forget them".

This is a working scratch-pad for ideas considered during the autonomous
session that aren't yet vol'd. Move to INVENTIONS_BACKLOG.md when promoted.

## In-flight (running as of 2026-05-19 ~20:15 CEST)

- **V156** — 8 ALNS jobs × 30min on the V155 456 board (basic + basic_lkh
  × seeds 42,1,7,13). Expected finish ~20:41.
- **V157** — V155 with rotation-aware prior (piece_id × rotation × position
  3D prior). Built, running nice'd at low priority alongside ALNS.

## V155 PRIOR family — promising extensions

The V155 +3 lift (453 → 456 from-scratch) shows that empirical priors
from the corpus work. Extensions:

### V158 PAIR-PRIOR  (built, untested)
For each piece pair (p, q) and each direction (H or V), count co-occurrence
in high-score boards as adjacent neighbors. Use as ADDITIONAL prior signal
when placing piece p next to already-placed piece q.

Build: `scripts/v155_prior/build_pair_prior.py` (DONE, 397KB JSON).
Implementation: fork v155_weaving_prior; at each placement, additionally
add `pair_prior[piece_id][neighbor_piece_id]` for each placed neighbor.

### V159 PER-BASIN-PRIOR
Build per-corner-perm prior matrices (one for each of the 18 basin families).
For each basin, do beam-search with that basin's specific prior. This is
"semi-anchored" — the prior says "what would McGavin-(3,2,0,1) look like
at cell X?" — but doesn't pin any specific piece.

### V160 EDGE-COLOR-PRIOR
Build a `color_prior[position][side][color]` matrix from the corpus. For
each cell, the prior says which colors typically appear on each of its
4 sides in high-score boards. Use as additional value-ordering signal.

### V161 HIGH-SCORE-ONLY PRIOR
Currently V155 uses boards with score ≥ 440 (n=938). Build a more selective
prior from score ≥ 459 (n=26) and score ≥ 460 (n=14). Trade sample size
for signal quality. Maybe the smaller-but-sharper prior gives more lift.

### V162 ANTI-PRIOR (escape attractors)
Inverse of PRIOR: prefer LEAST common (piece, position) pairs as tiebreak.
This biases the beam AWAY from corpus attractors, potentially finding
new high-score basins not represented in DB.

## Untried structural ideas

### V163 MATCHED-EDGE-CORRELATION
For each pair of edges (e1, e2) on the board, compute how often they're
BOTH matched in high-score boards. Highly-correlated pairs share basin
membership. Could use as a beam-state hash to dedupe by basin-membership.

### V164 GREEDY ROLLOUT WITH PRIOR
V151 tried rollout-as-ranking but rollout was noisy. Re-try rollout where
the rollout greedy ITSELF uses the prior — should reduce variance.

### V165 BIDIRECTIONAL BEAM
Beam search from row 0 → row 7 AND row 15 → row 8 simultaneously. Meet
at the middle row. Each beam half can use a different scan order or prior.

### V166 ALNS WITH PRIOR-WEIGHTED DESTROY
Modify ALNS's destroy operator to preferentially destroy cells with LOW
prior_sum (cells where the current piece is unusual). High prior cells
are "trusted" and protected.

## Cross-domain ideas (lower priority but interesting)

### V167 NEURAL VALUE NETWORK
Train a tiny neural network on (partial_board, piece_at_cell) → expected
final score. Use as beam-search ranking signal. Avoids the noise of
single-greedy-rollout.

### V168 CONTRASTIVE LEARNING ON BASINS
Learn an embedding where boards in the same basin family are close, and
different basins are far. Use the embedding as a beam dedup signal.

### V169 GRAPH NEURAL NETWORK ON PIECE-COMPAT GRAPH
Train a GNN to predict piece-position assignment from the piece-piece
edge-compatibility graph. Could replace the empirical prior with a
learned one.

## Architectural directions

### Cleaner V155 codebase
The v155_weaving_prior and v157_weaving_prior_rot share 90% code. Extract
common into a `weaving_beam_lib.rs` and have thin variants. Will help when
adding V158, V160, etc.

### Save-best for ALL bins
Add `--save-best` flag pattern from V155 to v151_weaving_beam too. Useful
for any beam → ALNS pipeline.

### Aggregate sweep driver
A script that runs N bins with M configs each and aggregates results into
a single CSV/table. Currently each vol writes its own ad-hoc analysis.

## Strategic observations

- **The V155 458/459 wall hypothesis**: if the corpus doesn't contain
  examples of 458+ patterns in some cells, the prior can't bias toward
  them. The corpus only has 14 boards ≥460. So the prior is mostly
  shaped by 440-459 range — and the beam will tend toward those.
- **Per-basin prior might unlock higher**: if we filter corpus to ≥459
  only (~30 boards), the prior would point to truly-rare structures.
  V161 tests this.
- **Beam saturation at 456**: V155 K=4096 = 456, K=8192 = 456. Either
  beam-diversity-collapse or score-ceiling. Probably both. Larger K
  alone won't break through.

## V155 "Bending" — 7 promising extensions (added 2026-05-19 late evening)

User observation: "very impressed we have an algorithm getting to 450 range
in ≈1 sec; do you plan on digging that idea?". Below: 7 concrete ways to
bend V155.

### V163 GRADIENT-DESCENDED PRIOR  (highest novelty)
After running V155 with prior, identify cells whose placed-piece had LOW
prior(p, c). Re-weight the prior to penalize those cells → re-run V155.
The prior "learns" what V155 itself can't fit, sharpens iteratively.

Implementation: 1 day. Build a Python loop that calls V155 N times,
each time updating the prior matrix.

### V164 CONFLICT-AWARE PRIOR (factor model)
Current prior is unary (piece-position). Add pair-prior (piece-piece adjacency)
and triple-prior. Or train a small probabilistic model (NMF, RBM, embedding)
on the corpus and use its likelihood as the beam ranking.

### V165 STOCHASTIC BEAM (softmax)
Replace top-K hard cutoff with: at each depth, sample K children with
P ∝ exp((score + alpha * prior_sum) / temperature). High temperature
→ exploration; low → exploitation (V155 default).

### V166 BACKTRACKING BEAM
If beam score growth slows below the prior's predicted rate, backtrack
by 32 depths, drop worst K/2 states, re-expand. Beam-with-restarts.

### V167 MULTI-OBJECTIVE BEAM
Maximize (matched_edges, -forbidden_2x2). Pareto-optimal beam.
Forbidden-2x2 minimization (V138) was inert as ALNS objective; might
work as construction objective.

### V168 NEURAL VALUE FUNCTION
Train a small NN (~10k params) on (partial_board → final_score) using
the corpus. Use as ranking signal in beam. The NN learns implicit
patterns the empirical prior misses (e.g., "this corner config tends
to limit interior matching").

### V169 PRIOR-GUIDED ALNS  ← highest leverage
Modify ALNS's destroy operator to prefer cells with LOW prior_sum from
the V155 pipeline. The 460 ceiling held because random destroy doesn't
target "unusual" placements. Prior-guided destroy:
  - destroy(target_cells) where target_cells = top-K low-prior cells
  - or destroy(weighted_random) where P(destroy(c)) ∝ 1 - prior_sum(c)
This is the most direct path to break 460 with existing infrastructure.

### V170 SHARP+DIFFUSED PRIOR
Combine the 459-thresh prior (sharp) with the 440-thresh prior (diffuse)
at different weights per cell. Cells where 459-prior is informative use
sharp; cells where it's near-zero use diffuse. Two-mode prior.

## Why V169 is most leverage

The 460 lift used the corpus prior ONCE at construction. ALNS then
worked blindly on the constructed board. Standard ALNS destroy is
spatially-random; it doesn't know which cells V155 trusted vs guessed.

Prior-guided destroy:
- targets V155's "weak" cells specifically
- preserves V155's "strong" cells (corners, hints, common pairings)
- in 30min, explores neighborhood of trust-weakly-supported cells
- could find 461+ where random ALNS got stuck at 460

Implementation: 1 day. Modify alns_only with `--prior-destroy <path>`
flag; in destroy phase, sample by inverse prior weight.

## Linked

- [[CURRENT-VOL]] (V156 in progress)
- [[INVENTION_NAMES_2026-05-19]] (named inventions)
- [[../sessions/vol-155]] (V155 PRIOR build-up)
- [[../concepts/prior-data-augmented-beam]] (V155 concept)
