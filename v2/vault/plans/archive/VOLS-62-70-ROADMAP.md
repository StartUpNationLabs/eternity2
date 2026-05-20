# Vols 62-70 — invented-algorithm roadmap

**Directive**: User 2026-05-15: each of vols 61-70 must be a genuinely
new invented algorithm. Vol-61 grandfathered as SOTA-replay calibration;
vol-62 onward strict.

**User return**: end of week (~2026-05-18 to 21). Autonomous run
through that window. ~3-5 days of compute available.

## Why this directive

Vol-60 confirmed our pipeline reaches the matched-edges SOTA (459).
Beating 459 needs a fundamentally different attack. The user's call:
stop tuning known methods, invent new ones. Failure modes are
acceptable (and useful) as long as the algorithm itself is novel.

## Vol-62: Homotopy-ALNS (working title)

**Algorithm sketch**:
1. On any board partial, compute the defect graph: nodes = cells with
   at least one mismatched edge; edges = mismatched edges between them.
2. Compute the first Betti number β₁ of this graph. β₁ = number of
   independent 1-cycles (closed loops bounding planar regions).
3. Each 1-cycle bounds an INTERIOR region of cells. The cycle can be
   "closed" only by re-tiling those interior cells coherently.
4. Identify β₁ generator cycles (basis of cycle space) — there are
   exactly β₁ of them.
5. Define a new destroy operator `CycleClose(cycle_id)`: drop all cells
   in the interior of generator `cycle_id` AND the cycle itself.
   Re-fill via CP or MWPM matching.
6. Iterate: pick the smallest generator first (cheapest fix), close it,
   compute new β₁ (should decrease by 1 if successful).

**Why this is invented**: nobody has published cycle-targeted destroy
operators on E2 (or AFAIK any edge-matching puzzle). Vol-18 R5
measured β₁ on real boards as diagnostic; using it as a destroy
operator is novel.

**Why it might work where prior fails**: random destroy regions don't
respect defect topology. Closing a 1-cycle is a structural commitment
— either it succeeds (basin improves) or fails (clean rollback).

**Build**: 1-2 days. Math (β₁ from edge incidence matrix), then
operator implementation, then ALNS integration.

**Risk**: planar graphs have well-understood β₁ structure; the
"interior" of a cycle may not be uniquely defined (depends on which
face we call "inside"). May need to enumerate both faces and try both.

## Vol-63: Backbone-Adversarial-Repair (working title)

**Algorithm sketch**:
1. Identify backbone = cells where the top-N records agree on the same
   (piece, rotation). Vol-37 found pos 161 + canonical hints + 2
   corners are universal. Build the full backbone from vol-60 data.
2. Run standard ALNS but with TWO modifications:
   - Backbone cells are PINNED (no destroy).
   - An "adversary" maintains a memory of recently-changed cells. With
     probability p, the adversary REVERTS a random recently-changed
     non-backbone cell to its previous state, even if score worsened.
3. The adversary creates synthetic basin-jumping pressure: ALNS can't
   settle into a local optimum because the adversary keeps pushing
   pieces back.

**Why this is invented**: adversarial-perturbation ALNS doesn't exist
in the literature. Backbone-anchoring is also novel (closest is
"hint-augmented ALNS" but hints are user-specified, not learned).

**Why it might work**: pure ALNS converges to local optima within a
basin. The adversary maintains exploration pressure indefinitely. The
backbone ensures we don't lose structural knowledge.

**Build**: 1 day (small extension to existing ALNS).

## Vol-64: Edge-Tension-Relaxation (working title)

**Algorithm sketch**:
1. Replace discrete (piece, rotation) with continuous probability
   distribution over piece-rotations per cell: `x[c] ∈ Δ^768` (the
   simplex).
2. Define edge-tension: for each adjacent cell pair, expected mismatch
   cost = Σ_{p_left, r_left} Σ_{p_right, r_right}
   x[c_left][(p,r)] · x[c_right][(p',r')] · mismatch_cost.
3. Add piece-uniqueness as a soft penalty: λ · max(0, Σ_c x[c][p] - 1)²
   per piece.
4. Initialize uniformly, run gradient descent (Adam-style) to minimize
   total tension + uniqueness penalty.
5. Round to integer at the end (pick argmax piece-rotation per cell,
   resolve conflicts via Hungarian).

**Why this is invented**: similar in spirit to vol-21's Hopfield
attempt but with local edge-pair forces instead of global energy.
Hopfield embeds the whole problem as one quadratic energy; this method
keeps each edge's tension separable.

**Why it might work where Hopfield fails**: local tensions admit
cleaner gradients. The convergence basin is smaller (each cell sees
only 4 neighbours), so gradient descent doesn't get stuck in global
saddle points.

**Build**: 2-3 days (gradient infrastructure in Rust, or Python with
PyTorch for fast prototype).

## Vol-65: Piece-Side-Matching (working title)

**Algorithm sketch**:
1. Build a graph G where nodes = (piece, side, color) triples.
2. Edges connect nodes with identical color AND compatible parity
   (e.g., a "right side" of one piece matches a "left side" of
   another).
3. A complete E2 solution corresponds to a perfect matching in G
   that respects two consistency constraints:
   - Piece consistency: the 4 sides of each piece must all be in the
     matching (each piece used exactly once).
   - Cell consistency: at each cell, the 4 sides used must form a
     valid adjacency (the 4 sides actually facing the 4 neighbours).
4. Solve as a constrained perfect matching problem. Use Hungarian/
   Blossom for the raw matching; add Lagrangian multipliers for
   consistency violations.

**Why this is invented**: E2 is usually formulated as piece-placement
CSP. Reformulating as piece-side perfect matching with consistency is
not in the literature.

**Why it might work**: matching algorithms are polynomial; the hard
part becomes the consistency Lagrangian. If the Lagrangian closes
quickly, we get an exact solver. If not, we get strong bounds.

**Build**: 3-5 days (matching infrastructure + dual decomp).

## Vol-66-70: TBD

Reserved for inventions that emerge during vols 62-65. Each must:
- Have a name not in any existing literature.
- Be a genuinely new mechanism (not "X with Y").
- Build on lessons from prior vols.

## Process per vol

Each vol (62 onwards):
1. **Day 1**: write the algorithm's math spec into
   `vault/concepts/<algo-name>.md`. Define soundness if applicable.
2. **Day 1-2**: implement in Rust or Python prototype.
3. **Day 2-3**: test on canonical E2; measure against the 459.
4. **Day 3**: close vol; write `vault/sessions/vol-NN.md`.

## Constraints

- Use the harness rules in CLAUDE.md (no false bounds, diff before
  narrate, variance reporting, timestamped outputs).
- Use `verify_records.sh` on any claimed records.
- If an idea turns out to be a variant of something named, PIVOT to a
  fresh invention.

## Linked

- Memory: `feedback_vols_61_to_70_invented_algos`
- CLAUDE.md "Vols 61-70 directive" section
