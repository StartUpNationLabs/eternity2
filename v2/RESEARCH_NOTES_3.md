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
  E2. Best from a single 6-sample harvest: 450/480.
- **30-minute megarun result** (closed-out at session end): CP+PT+Houdayer
  at full power for 28 min PT (1680s, 48661 rounds, all 8 cores) gives
  **449/480**. Houdayer fired 9577 times across all replica pairs (24%
  accept rate on coldest pair) and contributed **zero** improvement.
  The plateau is utterly stable. The 6-sample harvest's lucky 450 was
  effectively the ceiling our pipeline reaches.
  Report: `v2/output/pt_e2_1778519359_449of480.{json,url.txt}`.
  Log: `v2/output/megarun_30min.log`.
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

---

## Observation from 30-min megarun (mid-run, 2026-05-11)

While Inversion 1-7 are the agenda, the megarun PT log shows something
worth investigating early in vol. 3:

**Houdayer keeps proposing the same swap every round.** At t≈230s, the
cold-pair Houdayer move finds:
  - pair (0,1): component size 86, scores (448, 449)
  - pair (1,2): component size 92, scores (446, 449)
... and these same numbers repeat at rounds 6350, 6355, 6360, 6385,
6655, 6660, ...

With energy-preserving swaps (joint_delta=0 confirmed offline), the
swap teleports the joint state but doesn't change which adjacent-pair
disagreement components are admissible. Worse: with subsequent
replica-exchange acceptance, the system may be **reverting** to the
same state, making each Houdayer firing a no-op in the long run.

**Hypothesis for vol. 3**: Houdayer-in-PT as implemented is being
neutralised by the next replica-exchange round. The naive integration
fires Houdayer THEN replica-exchange in the same round; the exchange
undoes the swap.

**Fixes to try**:
  - Apply Houdayer ONLY between paired replicas at the SAME temperature
    (microcanonical, but currently we use adjacent-T pairs).
  - Track recently-swapped components and forbid re-swapping the same
    component within K rounds.
  - Skip replica-exchange for the pair we just Houdayered.

This is a small experiment for the next session before committing to
Inversion 2 work. Or it can be punted entirely if Inversion 2 makes
the whole PT pipeline obsolete.

---

## 2026-05-11 — Session decision: skip Inversion 1, commit to Inversion 2

**H**: cell-as-variable ordering tweaks won't move the 449-450 plateau,
because vol. 2's random-shuffle CP already varied border cells 55/60
across seeds and plateaus stayed 443-444 — that *is* the Inversion 1
signal, in everything but name. Re-doing it under PieceMrv would
re-confirm the same negative result. Higher EV: spend the session on
Inversion 2 (edge-variable formulation).

**User instruction**: "do what's best even if it takes a lot of time."
This is the genuine cross-domain reformulation vol. 2 kept proposing.

**Verdict**: skip Inv. 1. Build Inv. 2.

## Inversion 2 — design

### Model

- **Variables**: the 480 interior edges of the 16×16 board.
  Boundary edges (64 of them, on the outer perimeter) are not
  variables — they're fixed to BORDER. Each interior edge is shared
  by exactly 2 cells.
- **Domain**: {1..22} (the 22 interior colors). NOT including ⊥.
  Unmatched edges in partial states arise from being *unassigned*,
  not from an explicit ⊥ value. This makes the formulation a
  partial MAX-CSP (find the assignment that assigns the most edges
  while respecting constraints), not a satisfiability CSP.
- **Constraint (cell-consistency)**: for each cell c, the (≤4)
  variables around it must take values such that **some unused
  piece, in some rotation, has exactly that 4-tuple of edge
  colors** (with boundary-facing sides forced to BORDER). Boundary
  sides count as fixed inputs to the lookup.
- **Constraint (piece-uniqueness)**: each piece may satisfy at most
  one cell. This is the alldiff that couples otherwise-local cell
  constraints. Without it, edge-CP factors into per-cell trivia.

### Why edge-as-variable changes the dynamics

In cell-CP, deciding "place piece P at cell c with rotation r" commits
*4 edge values at once*. The branch is wide (256 cells × ~256 piece
candidates × 4 rotations = ~250K rows initially) and each branch is a
big commitment. CP picks the canonical-first cell and burns through it,
producing the deterministic prefix that the plateau diagnostic flagged.

In edge-CP, deciding "edge e takes color k" commits *1 unit*. The
branch is narrow (22 colors). The whole board's 480 commitments
are made one-by-one, with each commitment forcing propagation through
the two adjacent cell-consistency constraints. The unmatched edges in
plateau states are *directly addressable*: each ⊥ slot is one edge
variable, and we can ask "would any color value here be cell-consistent?"
That's a question the cell formulation can't ask without enumerating
all (piece, rot) candidates for the cell.

### Search structure: branch-and-bound

- **Score**: # of assigned edge variables in the partial assignment.
  Max = 480.
- **Branching**: pick an unassigned edge with smallest live-color
  domain (edge-MRV). Branch over colors in the live domain.
- **Propagation**: after assigning edge e := k, for each of e's two
  adjacent cells, recompute the cell-consistency lookup. If a cell's
  4 surrounding edges (assigned + unassigned) admit no unused piece in
  any rotation, the cell becomes infeasible → prune the branch.
- **Cascade**: edge-MRV may shrink: when one of a cell's edges is
  fixed, the other 3's live colors are restricted to those that
  appear in *some* unused-piece-rotation with the fixed edge.
- **Bound**: upper-bound = total_edges - count(infeasible cells × ≥1).
  Loose. Tightening this is a v2 task.
- **Best-partial**: track max-score partial seen; on timeout, return
  that.

### Lookup tables (precomputed once)

- `edge_4tuple_to_pieces: HashMap<[Color;4], Vec<(PieceId, Rotation)>>`
  — given the 4 edges around a cell (in cell-frame: top, right, bot,
  left), which pieces in which rotations match? Wildcard support for
  unassigned: 4 entries means specific match; some entries mean "any
  color"; we'll either expand the wildcards on lookup or use a
  more clever indexing scheme.
- Alternative: per-cell, per-side, per-color "feasibility bitmask"
  over (piece-id × rotation) — 256 × 4 × 22 × (256×4 bits) ≈ 22 MB.
  Negligible. Lets us do cell-consistency in O(piece-rotation-bitmask
  AND across 4 sides) ≈ ~32 u64 AND ops. Very fast.

I'll start with the bitmask table — it's the right data structure for
the propagator hot path.

### Score recovery (edge → board)

A complete (or partial) edge assignment doesn't directly produce a
board with pieces. To recover: for each cell c whose 4 edges are
assigned, look up matching pieces in `edge_4tuple_to_pieces`. If
multiple, solve the residual alldiff (small post-processing matching
problem). For cells with unassigned edges, leave the cell empty in
the recovered board.

Score under this recovery = matched edges (the proxy quantity we've
been optimizing all along) — so the edge-CP "score = assigned-edges"
exactly equals the standard E2 score, modulo the alldiff recoverability.

### Crate layout

- New crate: `crates/edge-solver/`. Self-contained, depends on
  `eternity2-core`, `eternity2-events`, `eternity2-solver-trait`.
- Does NOT modify `solver-engine`. If edge-CP is a dud, we keep it as
  a documented dead branch; if it works, we wire it into the registry.

### Validation plan

1. 6×6 generated puzzle, interior_colors=5. Solve via edge-CP. Confirm
   recovered board matches a known cell-CP solution (or any valid
   one). Pure satisfiability test.
2. 16×16 official E2 with 5 hints translated into pinned edge values.
   Run with a 60-second budget. Compare best-partial-score to the
   cell-CP baseline (~449-450).
3. If competitive or better, integrate with PT pipeline as a CP-phase
   replacement and rerun megarun.

### Risks / open questions

- **Score-bound tightness**: simple bounds may make B&B effectively a
  random walk through edge assignments. May need to add domain-
  reduction propagators or a smarter bound. Punt until we see how it
  behaves on 6×6.
- **Alldiff coupling**: piece-uniqueness ties cells; the propagator
  has to track *which pieces are used so far in this partial*. With
  many wildcard cells (most unassigned), this is loose. Tightening
  it might need per-piece-per-side color budget counting (similar to
  GAColor's incremental machinery).
- **6×6 hints don't exist**: we'll test 6×6 unconstrained
  (satisfiability) first, then add 5-clue mock-hints for a structural
  test before scaling.

### Stop-conditions

If edge-CP on 6×6 unconstrained doesn't solve within 60 s, the
propagator is too weak; redesign before scaling. If it solves 6×6 but
on 16×16 plateaus at the same 449 as cell-CP, the *formulation*
isn't the lever — the plateau is in piece-color-distribution, not
search-space-shape. Document and move to Inversion 5 or 6.

---

## 2026-05-11 — Inversion 2 v1 experiment 1: edge-CP on 16×16 E2

**H**: edge-as-variable CP can find a full 480/480 edge-coloring on
official E2 within seconds, but recovering a feasible board (with
piece-uniqueness) is where most of the score is lost.

**Setup**: new crate `eternity2-edge-solver`, v1 alldiff-deferred (no
piece-uniqueness propagation during search). Run via new bin
`edge_cp_e2 --seconds 30`. Edge-MRV heuristic (tightest adjacent cell
first); insertion-order value (color) ordering. Greedy alldiff at
recovery time.

**Result** (`v2/output/edge_cp_e2_1778523407_117of480.{json,url.txt}`):

| metric | value |
|---|---|
| outcome | AllAssigned |
| search edge-score | 480/480 |
| nodes | 15,908,030 |
| backtracks | 0 |
| elapsed | 23.9s |
| placed cells (after greedy recovery) | 104/256 |
| matched edges (after recovery) | 117/480 |

For comparison, cell-CP (`gacolor_ac3_par`) reaches 449/480 on the
same puzzle. Cell-CP solves *both* edge-coloring AND piece-uniqueness
simultaneously and plateaus high; edge-CP solves edge-coloring
trivially but only 21.6% of the assigned colors translate into
feasible piece placements via greedy recovery.

**Verdict (qualitative)**: this is exactly the result the design
predicted: **edge-coloring is the easy half; the alldiff is where
E2's hardness lives**. The 480-edge search has zero backtracks — the
constraints aren't binding. The real engine is piece-uniqueness.

This reframes the entire research question. In cell-CP, alldiff and
edge-color matching are entangled — we couldn't separate their
contributions to the plateau. Now we can. The 449-vs-117 gap shows
how much *coupling* between alldiff and edge-matching contributes to
finding feasible boards.

**Next steps**:
  1. Smarter recovery: bipartite max-matching instead of greedy. This
     might lift 117 to several hundred without changing search.
  2. v1.1 sound alldiff propagator: Hall's condition / per-cell
     piece-set + global matching feasibility. Naïve cell-collapse is
     unsound (single-cell experiment confirmed: dies at 5/480).
  3. Hint translation: pin the 5 official hints into edge-variable
     assignments. Will shrink the search space and might force
     piece-conflicts earlier.

**Note on the "0 backtracks" data**: the search ran 15.9M nodes
without backtracking because **MRV + insertion order happens to find
a self-consistent coloring trivially** on this puzzle. That's evidence
that the edge-coloring problem on 22 colors with our heuristic is
loosely constrained. The total of 31.8M propagations is essentially
forward-checking work; the algorithm walks the DAG of choice points
once.

---

## 2026-05-11 — Inversion 2 v1.1: SOUND Hall-1 alldiff propagator

**Diagnostic from experiment 1**: every cell was fully-determined and
had exactly 1 piece candidate, but matching only placed 104/256
because *many cells claimed the same piece*. The edge-coloring was a
big lie — most "matches" used overlapping pieces. **The unsound naïve
piece-commit propagator was the right impulse but wrong mechanism.**

### Hall-1 design

Sound propagator: after each `assign`, scan all cells; for each cell
whose `cell_rows_alive[c] ∩ available_rows` has bits from exactly one
piece, record that cell→piece claim. If two distinct cells claim the
same piece, **the partial is infeasible** — fail. This is the
*pigeonhole-singleton* slice of Hall's condition: when |N(S)| < |S|
because |S|=2 and |N(S)|=1.

Compact, sound, conservative. It catches the obvious alldiff
violations without committing pieces eagerly (the unsound move).

### Result (`v2/output/edge_cp_e2_1778523779_335of480.{json,url.txt}`)

60-second run:
| metric | v1 (no alldiff) | v1.1 (Hall-1) |
|---|---|---|
| outcome | AllAssigned | TimedOut |
| best edge-score (search) | 480/480 | 360/480 |
| matched edges (recovered) | 117 | **335** |
| placed cells | 104 | **185** |
| nodes | 15.9M | 3.3M |
| backtracks | 0 | 2.4M |

**2.86× improvement on recovered edge score, 1.78× on placed cells.**

180-second budget yields the same 360 edge-score, 335 recovered —
**the propagator finds a plateau by 60s and doesn't budge with 3× more
budget**. The plateau is real, not budget-limited.

### Comparison to cell-CP

Cell-CP (gacolor_ac3_par): 449/480 in ~10s.
Edge-CP (Hall-1): 335/480 in 60s, plateaus there.

Cell-CP wins on this puzzle. Why? Cell-CP enforces alldiff *natively*
in its branching: every commit picks a piece and removes it from
circulation. Edge-CP's Hall-1 catches the simplest alldiff violations
(pigeonhole-2) but misses subtler ones (e.g., 3 cells claiming 2
pieces). The search exhausts feasibility through Hall-1 but the
search tree is still polluted with infeasible-but-Hall-1-passing
states.

### Smaller puzzles (validation)

8×8 generated (interior_colors=6, 30s): 111/112 edges, 55/64 cells.
10×10 generated (interior_colors=8, 60s): 174/180 edges, 85/100 cells.

Edge-CP gets very close to complete on small puzzles but plateaus
just below perfect. Same dynamic as 16×16: alldiff weak-propagation
keeps the search churning on infeasible partials.

### Verdict

**Inversion 2 v1.1 is *not* better than cell-CP** on E2's 5-clue
problem. But:

1. The cell-CP plateau (449) and the edge-CP plateau (335) are at
   *different scores*. They're solving genuinely different
   relaxations, and they have **different failure modes**:
   - Cell-CP: piece-uniqueness enforced; some edge-color constraints
     unsatisfiable in the canonical search order.
   - Edge-CP+Hall-1: edge-color satisfiable; piece-uniqueness violated
     in subtler-than-pigeonhole-2 ways.
2. The 335 score is **higher than any single-pass non-cell-CP method
   we've tried**. PT+Houdayer on a cell-CP seed plateaus at 449.
   Random SA on a CP seed: ~390. Edge-CP+Hall-1 alone: 335. We
   haven't yet *seeded* PT with an edge-CP partial.

### Next steps

1. **Stronger alldiff**: bipartite-matching feasibility check during
   search (real Hall's condition). Run after every K assigns; if no
   feasible matching exists, prune. O(V·E) per check, K~10-100.
2. **Seed PT/SA with the edge-CP partial**: the 185 placed cells from
   edge-CP could be a *different* local minimum basin than cell-CP's
   449-partials. Cross-pollinating may exit either basin.
3. **Hint translation**: pin the 5 official hints into edge colors at
   the start. The hint cells force 16-20 edge values, shrinking
   search space.


