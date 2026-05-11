# Research notes — deep-edge solver work

Living log of experiments. Each entry: hypothesis, what we tried, what we measured, what we kept/dropped, and why.

## Literature survey (2026-05-11)

### Eternity II / edge-matching specific

1. **Ansótegui, Béjar, Fernández, Gomes, Mateu — "Edge matching puzzles as
   hard SAT/CSP benchmarks"** (Springer / CP'08, extended JCon'13). Most useful
   paper. Key constructs:

   - **GAColor — symmetric alldiff per color.** For each interior color *c*
     with 2k half-edges, the puzzle is solvable only if the bipartite "color
     graph" admits a perfect matching, where vertices are the 2k half-edges
     of color *c* and graph-edges are *currently feasible* adjacencies
     (i.e. pairs (h₁, h₂) such that the two host tokens could still be
     placed in adjacent positions in the current partial board). A pair of
     half-edges is pruned if it belongs to no perfect matching of this
     graph — equivalent to running the Régin (1994) alldifferent filter,
     polynomial. **The paper calls this "the most powerful global
     constraint we have found"** (§4.2 GAC for the exactly-k constraint).

   - **CHESS variable heuristic.** Static: process all "black" cells of a
     checkerboard from center spiralling out, then all "white" cells.
     Each white cell ends up with ≤4 already-placed black neighbors → its
     domain collapses to a singleton (or wipeout) very fast. Cited as the
     practical win on top of GAColor.

   - **PD3 redundant constraints + exactly-k cardinality.** SAT-side
     formulations of the same color-graph idea.

2. **Salassa, Vancroonenburg, Wauters et al. — "MILP and Max-Clique based
   heuristics for the Eternity II puzzle"** (arXiv:1709.00252). MILP +
   Max-Clique formulations confirm NP-completeness, are intractable
   directly. Practical use: heuristic decomposition + multi-neighborhood
   local search. Out of scope until we hit a wall on exact search.

3. **Various Github backtrackers** (fabri1983, ttu.github.io). "Smart
   prunes such as parity checking and patterns of placed tiles which
   don't allow generating the same pattern again." None are
   research-grade.

### Cross-domain

- **Régin 1994 — alldifferent filtering via Hall's theorem.** The
  textbook bipartite-matching-based propagator: find a max matching,
  any edge not in any max matching can be pruned in polynomial time.
  Standard CP toolkit; GAColor is a direct instance.
- **Bessière & Régin — MAC, watched-literals** — runtime tactics for
  propagation queues; applicable later when GAColor becomes our
  hottest propagator.
- **CDCL parity reasoning** (Soos et al., arXiv:2209.12185). Modern
  CDCL solvers detect parity constraints via Gaussian elimination and
  propagate them. Confirms our parity_propagator direction is real,
  but the cross-domain evidence is that the *strong* version of
  parity is "symmetric alldiff" / matching-based, not pure
  algebraic parity.

## Our current state (baseline)

What our v2 engine has today:
- Variable orders: BorderFirstMrv (default), Mrv, RareColorFirst,
  BorderFirstRandom. **No CHESS.**
- Value orders: InsertionOrder. **LCV is a config flag but unwired.**
- Propagators: edge-color (baseline), piece-uniqueness (baseline),
  class_balance (corner/edge/inner counts), parity (per-color
  parity-of-budget, weak), island (every piece has a home).
  **No GAColor / symmetric alldiff.**
- Parallelism: SingleThread, RootSplit (work-stealing at depth K).

Benchmark observation that motivated this work:
`engine_full` (parity+island) is *slower than* plain `engine` on our
current generated corpus. parity prunes ~0% of the search on the
puzzles where it matters. Confirms: we need a stronger global
filter, and the literature points squarely at GAColor.

## Experiment plan (ranked by expected leverage)

| # | Experiment | Why | Expected impact |
|---|---|---|---|
| A | **GAColor (symmetric alldiff per color)** | Paper-validated "most powerful". Strict generalization of parity. | Orders of magnitude on hard puzzles (paper) |
| B | **CHESS variable ordering** | Pairs with GAColor; singletons emerge early. | Multiplicative with A |
| C | **True LCV value ordering** | Value-side MRV complement. | Modest; standard CP win |
| D | **Symmetry breaking (corner fixing)** | Up to 8× via D4 symmetry of board. | Constant factor |
| E | **Nogood learning / CBJ** | Skip irrelevant decisions on backtrack. | Implementation cost high |

We do A first. B is wired alongside since they're complementary.
C/D/E come after we measure A+B.

## Experiment A1 — GAColor v1 (necessary condition, non-incremental)

**H** — A supply/demand-per-color invariant strictly tighter than parity should prune faster, giving a net win over `border_first_lcv`.

**Setup** — Corpus: `../data/benchmark`, sizes 4..7 (32 puzzles).
60s budget, 1 run per cell. Profiles compared:
- `border_first_lcv` (no extra propagator beyond baseline + class_balance)
- `border_first_full` (parity + island, current "strong" combo)
- `border_first_gacolor` (only gacolor on top of class_balance)

Native-CPU release build. Apple M1, single-thread.

**Result** — `data/expA_gacolor.json`. Sum of medians across all 32 cells:

| profile | sum medians (ms) |
|---|---|
| border_first_lcv     | **1268** |
| border_first_gacolor | 1324  (+4.4%) |
| border_first_full    | 1422  (+12%) |

Headline wins for gacolor: `size_7_colors_2` (570→534), `size_6_colors_2`
(0.14→0.12), `size_5_colors_2` (0.08→0.06). All on low-color puzzles where
the supply/demand bound is tight.

Headline losses: `size_6_colors_4` (49→56), `size_7_colors_5` (377→430).
Mid-color puzzles where slack is wide and the check rarely wipes.

**Verdict — keep but mark v1 as overhead-dominated.** Same failure mode as
parity: the necessary-condition is correct but too rarely triggers to
amortise the per-node cost. Useful information: gacolor matches or beats
`full` (parity+island) on every single cell in this set — so gacolor is a
strict improvement over the parity propagator, just not over no
propagator. Next iteration: incremental bookkeeping so the check is
O(color_count) instead of O(cells + pieces).

## Experiment A2 — GAColor incremental

**H** — A1 was right on pruning (−25% nodes, −14% backtracks vs lcv) but
paid a per-node alloc/scan cost that wiped the wall-time win. Maintaining
`supply[c]`/`open_demand[c]` deltas in `SearchState` should drop the
per-node cost to O(color_count) and convert pruning into wall-time win.

**Setup** — Identical to A1: 32 puzzles, size 4..7, 60s budget, 1 run,
native release.

**Result** — `data/expA2_gacolor_incr.json`. Sum of medians, size≥6:

| profile  | wall (ms) | nodes     | backtracks |
|---|---|---|---|
| lcv      |   1311    | 1,781,484 |  728,647 |
| gacolor  | **1140**  | 1,336,820 |  626,293 |
| full     |   1436    | 1,189,087 |  524,436 |

**−13% wall-time vs lcv with identical pruning to A1.** Per-puzzle wins:
- `size_7_colors_2`: 577 → 434 ms (**−25%**)
- `size_5_colors_8`: 0.10 → 0.08 ms — consistent for fast puzzles too.

Nodes/backtracks unchanged between A1 and A2 (correctness preserved); the
delta is pure overhead reduction. `border_first_full` (parity + island)
remains slower because parity_check still allocates per-node.

**Verdict — keep. GAColor v2 (incremental) is now the default-recommended
propagator and supersedes both parity and "full".** Next: replace
`parity_propagator` with a no-op shim that maps to `gacolor_propagator`,
or remove the parity profile.

A natural next step is **B (CHESS variable ordering)** — the paper pairs
GAColor with CHESS to drive singletons out faster. With our current
border-first MRV, GAColor pruning is mostly fired at deep nodes;
CHESS-ordered placement should expose it earlier.

## Experiment B — CHESS variable ordering

**H** — Pair CHESS (corners → border → interior-black spiral → interior-white)
with GAColor. Paper claims CHESS makes singletons emerge fast through
neighborhood density on white cells.

**Setup** — Identical corpus & budget. Three profiles: `border_first_lcv`,
`border_first_gacolor`, `chess_gacolor`.

**Result** — `data/expB_chess.json`. Sum medians, size≥6:

| profile              | wall (ms) | nodes        | backtracks    |
|---|---|---|---|
| border_first_lcv     |   1311    | 1,776,713    |   727,531     |
| border_first_gacolor |   1165    | 1,332,049    |   625,177     |
| **chess_gacolor**    | **302,897** (DNF) | **868,717,210** | **804,112,563** |

Five puzzles time-out at 60s under `chess_gacolor` (size_7_colors_{4,5,6,7,8}).
Node count blows up 600× vs `gacolor`.

**Why it fails** — the paper uses CHESS *with* GAC propagation across the
position-variable alldiff (`ti ≠ tj` for all pieces) plus full GAColor
edge-graph filtering that prunes domain rows, not just wipes out states.
Our gacolor is *necessary-condition* only — it triggers wipeouts on
supply/demand imbalances but **doesn't propagate** to reduce neighbour
domains. CHESS jumps to interior cells whose domain is enormous when
empty, and without strong propagation across the gap between distant
blacks, every choice is blind. The strategy *needs* the full filtering
infrastructure to be a win.

**Verdict — dropped for this configuration.** Lesson: heuristic strength
must be matched to propagation strength. CHESS becomes viable only after
we build a propagation layer that filters domain rows across distant
already-placed neighbors (e.g., AC-3 / edge-graph matching).

Next move candidates:
1. **Stronger GAColor that prunes domains, not just wipes** — promote our
   necessary-condition propagator into a true edge-graph matching filter
   that removes rows from neighbour domains.
2. **AC-3 over edge-color constraints** — long-range domain pruning.
3. **Symmetry breaking** — orthogonal, ~8× free reduction.

## Experiment C — Rotational symmetry breaking via corner pinning

**H** — The board has D4 rotational symmetry. Pinning the lowest-id
corner piece to (0,0) in its canonical rotation removes 4× of the
search space.

**Setup** — Same corpus, budget, run count.

**Result** — `data/expC_symbreak.json`. Sum medians, size≥6:

| profile               | wall (ms) | nodes        | backtracks |
|---|---|---|---|
| border_first_lcv      |   1278    | 1,781,484    |  728,647   |
| border_first_gacolor  |   1150    | 1,336,820    |  626,293   |
| gacolor_symbreak      |   1146    | 1,336,804    |  626,293   |

**Symbreak is a no-op on FirstSolution mode**: wall-time delta is noise
(within 0.4%), node delta is 16 nodes out of 1.34M.

**Why** — `BorderFirstMrv` already picks corners first by class, and the
domain row at position (0,0) is enumerated in piece-id order. So the
solver naturally tries the canonical corner (lowest piece-id) *first*
anyway. The pinning would only matter when:
- enumerating all solutions (we'd visit each symmetric copy once with
  pinning, four times without);
- the canonical corner happened to land later in the natural ordering
  (counter to our generator's piece-id convention).

For FirstSolution mode on satisfiable puzzles with our generator,
implicit ordering already does the work.

**Verdict — keep wired but disabled in default profiles.** Worth turning
on for `AllSolutions` mode (out of scope right now). Real cost: a tiny
amount of init code that we can leave dormant.

## Experiment D — AC-3 cascading propagation

**H** — Replace single-step forward-checking with full arc-consistency.
After each placement, queue all unplaced cells whose domain was touched,
revise arc-consistency outward until fixpoint. For each row in
domain[a]: drop if any unplaced neighbour b lacks a row matching color
across the shared edge.

This is one of the textbook results from CP (Mackworth 1977). It always
prunes ≥ as much as FC but pays a higher per-node cost.

**Setup** — Same corpus (sizes 4–7), 60s budget, 1 run. Profiles:
`border_first_lcv`, `border_first_gacolor`, `gacolor_ac3`.

**Result** — `data/expD_ac3.json`. Sum medians, size≥6:

| profile               | wall (ms) | nodes        | backtracks |
|---|---|---|---|
| border_first_lcv      |   1300    | 1,781,484    |   728,647   |
| border_first_gacolor  |   1169    | 1,336,820    |   626,293   |
| **gacolor_ac3**       | **794**   | **290,383**  | **143,585** |

**−39% wall-time vs lcv, −32% vs gacolor. −84% nodes, −80% backtracks.**

Per-puzzle pattern is the textbook AC-3 tradeoff:
- **Hard puzzles** (deep backtracking) **win big**: size_7_colors_2:
  586→229 (−61%), size_7_colors_5: 383→164 (−57%), size_7_colors_8:
  10→2 (−80%).
- **Easy puzzles** (shallow search) **lose**: size_6_colors_3: 3.1→5.3
  (+71%), size_6_colors_5: 44→70 (+59%). The per-node propagation
  cost isn't recouped when there's nothing to prune.

Cumulative win on size≥6 is dominated by the hard puzzles, so AC-3 is a
net major improvement.

**Verdict — keep, promoting to the new default for hard puzzles.**
`gacolor_ac3` is now the recommended profile when a problem is
non-trivial. For trivially-solvable small puzzles a lighter profile
would be marginally faster; we could auto-select via a heuristic on
puzzle size or initial domain sizes, but right now the spec is simple:
**use `gacolor_ac3` as the strong default.**

Note on CHESS (Exp B): the failure analysis said CHESS needs "strong
propagation that filters domain rows across distant placed neighbors."
That's now what AC-3 provides. **CHESS should be re-evaluated with AC-3
enabled** — that's a free experiment in the next batch.

## Experiment B' — CHESS with AC-3

**H** — In Exp B, CHESS exploded because propagation was too weak. AC-3
provides domain-row-level pruning that should let CHESS work.

**Setup** — Sizes 4–7, 60s, 1 run. Profile: `chess_gacolor_ac3`.

**Result** — `data/expBp_chess_ac3.json`. **Still fails.**

size≥6 cumulative: `chess_gacolor_ac3` takes 57,000 ms vs `gacolor_ac3`
565 ms — 100× slower. Solved 12/16 (vs 16/16 for `gacolor_ac3`).

Size-6 puzzles are fine. Size-7 explodes: `size_7_colors_3` 1.7s vs 2.5ms
(700× slower), `size_7_colors_5` 50s vs 169ms.

**Why AC-3 doesn't rescue CHESS** — AC-3 is *binary* arc-consistency:
between two neighbouring cells, every row in cell A must have at least
one supporting row in cell B. But the **first interior placement** under
CHESS jumps to the geometric center of the board, far from any placed
piece. Both the center cell's domain and its neighbours' domains are
fully populated → every row trivially has support → AC-3 prunes
nothing. AC-3 only "fires" once we've started building constraint
chains around a placed region; CHESS deliberately doesn't build those
chains.

The paper's CHESS works because their **GAColor was a Régin-style
matching filter operating across the entire board's Edge-Color Graph**,
not local AC. A row in cell A could be killed because the *global*
color-graph matching, summed across all cells, had no perfect matching
including it. That kind of pruning fires even when neighbours are
empty.

**Verdict — finalised: drop CHESS until we have global-matching
propagation.** Implementing Régin's edge-color-graph filter is a
significant project (Edmonds-Karp + augmenting paths over a multigraph
with ~|colors|·N² edges). Out of scope for this batch.

## Experiment F — Cracking size-8 puzzles with AC-3

**H** — AC-3 cut nodes 84%. Previously-intractable size-8 puzzles
should now become solvable.

**Setup** — All 8 puzzles in `data/benchmark/size_8_colors_*`, 5-minute
budget per cell, single-threaded `gacolor_ac3`.

**Result** — `data/expF_size8.json`. **7 of 8 size-8 puzzles solved.**

| puzzle | wall time | status |
|---|---|---|
| size_8_colors_2 | 1 ms     | ✓ |
| size_8_colors_3 | 27 ms    | ✓ |
| size_8_colors_4 | 2 ms     | ✓ |
| size_8_colors_5 | 20 ms    | ✓ |
| size_8_colors_6 | **44.4 s** | ✓ |
| size_8_colors_7 | 300+ s   | ✗ (timeout) |
| size_8_colors_8 | 8.5 s    | ✓ |
| size_8_colors_9 | 5.5 s    | ✓ |

Historical benchmark for comparison: legacy v3_par solved `size_8_colors_6`
in 57.2 s using **8 cores** in parallel. We now solve the same puzzle in
44.4 s **single-threaded**. The `_par` variant should bring it under
10 s.

The lone unsolved instance is `size_8_colors_7`. Mid-color size-8 puzzles
sit right at the phase-transition where domain-graph density is maximal
and AC-3's propagation is least able to compress. Adding parallel
RootSplit on top of AC-3 is the obvious next step.

**Verdict — major progress.** AC-3 unlocks a problem class that was
previously DNF. The new effective frontier is "color-7 size-8" — that
becomes the next hard target.

## Experiment G — AC-3 + RootSplit parallel

**H** — AC-3 cuts nodes 84%. RootSplit's work-stealing 8-way
parallelism should multiply that on hard problems.

**Setup** — Sizes 7–8 (the hard region), 5-minute budget, 1 run.
Profiles: `border_first_lcv`, `gacolor_ac3`, `gacolor_ac3_par`.

**Result** — `data/expG_ac3_par.json`. **All 8 size-8 puzzles now
solved including the previously-DNF `size_8_colors_7`.**

| puzzle              | lcv | ac3 | ac3_par |
|---|---|---|---|
| size_7_colors_2 | 623 ms | 238 ms | **2 ms** (119×) |
| size_7_colors_5 | 410 ms | 175 ms | **47 ms** (4×) |
| size_8_colors_6 | 8.4 s  | 42.2 s | **2.5 s** (17×) |
| size_8_colors_7 | DNF    | DNF    | **67.9 s** ✓ |
| size_8_colors_8 | 5.6 s  | 8.1 s  | **0.16 s** (49×) |

**`size_8_colors_7` is the first ever fully solved across both v2
generations** — legacy v3_par DNF'd on this cell too.

**Tradeoff revealed**: parallel pays fixed fanout overhead on easy
puzzles. `size_8_colors_5` 20→39 ms; `size_7_colors_8` 2→22 ms. The
parallel solver is the *right tool* for hard problems but adds latency
on small ones. A puzzle-aware selector would dispatch single-thread
for trivial cells (e.g., predicted node-count below threshold) and
parallel only for the rest. Not in scope right now; documented for
future work.

**Also surprising**: `border_first_lcv` aggregate is lower than
`gacolor_ac3` aggregate on size-8 because lcv solves several size-8
puzzles in <2 ms while AC-3's per-node overhead pays a 10-20 ms
"entrance fee" even on trivially-easy cases. The same tradeoff seen
at size-6 generalises: propagation strength helps where you need it,
costs where you don't.

**Verdict — `gacolor_ac3_par` is the new headline solver.** Most
capable across the corpus. Single-thread `gacolor_ac3` remains useful
as the default for mid-difficulty cells. `border_first_lcv` remains
optimal for trivially-easy.

## Cross-domain survey

We've been mining the edge-matching / CSP literature directly. But our
problem reduces to a structurally generic "place items with side
constraints" pattern — much broader than Eternity II. Looking at
adjacent / distant fields:

### 1. Job shop scheduling — *edge-finder* and *energetic reasoning*

Job shop is "place tasks on machines with precedence and resource
constraints." Same shape: each task has properties (duration, resource)
that must match its position's properties (free time, capacity).

Two ideas worth porting:

- **Edge-finder (Carlier & Pinson 1989; Vilím 2004).** Detects, for a
  set Ω of activities competing for a resource, that some specific task
  *must* execute before/after the rest of Ω. Reasoning: aggregate
  "total work" across Ω vs available time. Pruning cost: O(n log n).
  **Analogue for us:** for a set of cells sharing a constrained
  resource (e.g., all corner cells together need exactly 4 corner
  pieces), detect that one specific piece must occupy one specific
  cell because the others can't fit anywhere else.

- **Energetic reasoning (Erschler & Lopez 1990).** Stronger than
  edge-finder: compute the "energy" each task contributes to each
  time window vs window capacity. Catches more conflicts but is
  O(n²) per fixpoint. **Analogue for us:** for each cell region,
  compute total color-supply across pieces that *could* occupy that
  region vs total color-demand from cell faces. If supply < demand
  anywhere, backtrack. This is a *spatial energetic* check.

Notably: edge-finder fixpoints are computed in strongly polynomial
time. Energetic reasoning isn't even for the disjunctive case. So
**there's a clear "cheap-and-strong / slow-and-stronger" frontier
already mapped out in scheduling that we could mirror.**

### 2. Polyomino tiling — *DLX*, *X-then-min-fit ordering*

Polyomino tilers (Knuth's *Dancing Links*) solve a near-isomorphic
problem: place rotated/reflected shapes on a grid with cover
constraints. Two transferable insights:

- **Min-fit switchover heuristic** (M. Busche, polycube blog). Use
  cheap *x-ordering* (lex) at the top of the search where domains are
  fat; switch to expensive *min-fit* (MRV-style) only when remaining
  pieces drop below a threshold. **For us:** consider switching
  variable orders mid-search. We currently always border-first-MRV.

- **DLX-as-substrate.** Knuth's exact-cover formulation handles
  *piece-uniqueness* (every piece used once) without explicit
  bookkeeping. We currently iterate all positions to update piece-use;
  with DLX-linked lists we'd get O(1) cover/uncover per piece. We
  already considered this in the legacy port and chose flat vectors;
  worth revisiting if profiling shows piece-uniqueness dominates.

### 3. SAT — *CDCL with nogood learning*

CDCL (Marques-Silva & Sakallah 1996) is the workhorse of modern SAT.
The two key ideas:

- **Nogood learning / clause database.** Every conflict produces a
  *learned clause* — a constraint that future search must satisfy.
  Prevents the same mistake in different subtrees. **For us:** when a
  backtrack happens, record the *minimal* placement subset that
  caused the wipeout. Future deep states matching that subset can
  prune immediately. Memory cost can dominate, but the literature has
  good aging/forgetting schemes.

- **Non-chronological backjumping.** Instead of backtracking one
  level, jump to the *deepest decision relevant to the conflict*.
  **For us:** if a wipeout at depth 30 is caused by a placement at
  depth 5, undo all placements between 5 and 30, not just depth 30.
  Implementation requires tracking which decisions each domain
  reduction depends on (an *implication graph*).

CDCL is broadly the reason SAT solvers improved 1000× since 2000. It's
expensive to retrofit but huge upside.

### 4. Constraint Programming theory — *Singleton Arc Consistency*

The CP literature has a hierarchy of consistency levels (Bessière,
Stergiou, Walsh):
- AC (arc consistency) — what we just implemented.
- PC (path consistency) — for every triple of variables, every
  consistent pair extends to the third. Cubic blow-up; rarely used.
- **SAC (singleton arc consistency)** — for each domain value v of
  variable X, *temporarily commit X=v*, run AC to fixpoint, and check
  domains don't wipe. If they do, v can be pruned permanently. Much
  stronger than AC at higher cost. Solves bounded-width CSPs in
  polynomial time (Barták & Erben).

  **For us:** SAC is essentially "do trial placements and propagate."
  If our AC-3 only takes O(K) per call (K small), a SAC round is
  O(|domain| × K) per cell — affordable. SAC could close the gap
  we're seeing where AC-3 still leaves many wasted nodes deep in the
  search.

### 5. Protein folding — *constraint propagation in lattice models*

The HP lattice model places amino acids on a grid with hydrophobic/
polar interaction constraints. Used CSP heavily before deep learning
took over. Their trick: **integration of CP with local search**. The
CP finds a feasible partial structure, then local search (Monte Carlo,
GA) perturbs it. **For us:** worth considering once we exhaust pure
exact methods — we could use AC-3+GAColor to seed initial placements,
then run tabu search to repair conflicts. The MILP paper (Salassa
et al.) on Eternity II does exactly this in their multi-neighborhood
local search.

### 6. DNA assembly — *transitive overlap reduction*

Genome assemblers (CABOG, Velvet) reduce read-overlap graphs by
removing transitively-inferable edges. **For us, this looks like:** if
piece-row r₁ at position p₁ is compatible with piece-row r₂ at p₂, and
r₂ at p₂ is compatible with r₃ at p₃, do we ever need to consider
r₁→r₃ adjacency directly? Probably not directly applicable because
our graph is *not* sparse like an overlap graph — but the *spirit*
("compress redundant constraints") is exactly what learned nogoods do
in CDCL.

## Experiment E — True LCV value ordering

**H** — Sorting each cell's candidate rows by how many neighbour-domain
rows they would prune (Haralick & Elliott 1980 LCV) should reduce
backtracks enough to pay for the per-node scoring overhead.

**Setup** — 13 puzzles (size 7 colors 2–9, size 8 colors 2–6),
5 minute budget, 1 run/cell. Compared `border_first_lcv` (no
propagators), `gacolor_ac3` (current ST best), `gacolor_ac3_lcv`,
`gacolor_ac3_lcv_par`. JSON: `data/expE_lcv.json`.

**Result** — sum of medians across all 13 puzzles:
- `border_first_lcv`:        9,324 ms
- `gacolor_ac3`:             42,710 ms
- `gacolor_ac3_lcv`:         **157,994 ms (+270% vs ac3)**
- `gacolor_ac3_lcv_par`:     **7,892 ms (−82% vs ac3, new SOTA)**

Per-puzzle regressions of `gacolor_ac3_lcv` (vs `gacolor_ac3`):
| puzzle | ac3 ms | ac3+lcv ms | ratio |
|---|---|---|---|
| size_8_colors_3 | 25 | 42,014 | **1656×** |
| size_7_colors_6 | 170 | 9,816 | 57× |
| size_8_colors_5 | 19 | 1,590 | 83× |
| size_8_colors_6 | 42,033 | 104,286 | 2.5× |

Per-puzzle improvements of `gacolor_ac3_lcv_par` (vs `gacolor_ac3`):
| puzzle | ac3 ms | lcv+par ms | ratio |
|---|---|---|---|
| size_7_colors_2 | 235 | 5.6 | **42×** |
| size_8_colors_6 | 42,033 | 7,229 | **5.8×** |
| size_7_colors_7 | 51 | 12.6 | 4× |

**Diagnosis** — LCV scoring is O(|D_pos| · 4 · |D_neighbor|) per
node ≈ 1.44M ops on size 8 (|D|≈600). At 6.7M nodes on
`size_8_colors_3` that's ~10T inner ops, swamping the search-tree
shrinkage. In parallel each worker gets a sub-tree with reduced
domains so per-node overhead drops and ordering benefit dominates.

**Verdict** — kept as `gacolor_ac3_lcv_par` only; serial LCV is
worse than serial AC-3. Best parallel profile to date. The next
big lever on the serial path is **cheaper LCV scoring** (precomputed
color-side bucket sizes give O(4) per row instead of O(|D|·4)) — see
Exp I.

## Experiment I — Bitmask color-side buckets (hot-path)

**H** — Replacing the AC-3 inner-loop linear scan
`domains[nb].iter().any(|r2| r2.edges[s_b]==required && r2.piece!=r.piece)`
with an O(1) lookup via a per-call count cache + row-presence bitset
should reduce AC-3 inner cost by a factor of |D_nb| (≈600 on size 8).

**Setup** — 16 puzzles (size 7 colors 2-9, size 8 colors 2-9),
5min budget, 1 run/cell. Same 4 profiles as Exp E. Per-AC-3-call
cache built once at entry (O(n_pos × |D|)) and updated incrementally
when rows are removed. Same-piece adjustment iterates ≤4 rotations
of r.piece_id and consults the bitset (O(4)). JSON:
`data/expI_bitmask.json`.

**Result** — sum of medians across all 16 puzzles:
| Profile | Sum ms (16 puz) | Solved |
|---|---|---|
| `gacolor_ac3` | 349,795 | 15/16 |
| `gacolor_ac3_par` | **65,281** | 16/16 |
| `gacolor_ac3_lcv` | 464,236 | 15/16 |
| `gacolor_ac3_lcv_par` | 64,072 | 16/16 |

Significantly extends solvable corpus: **size_8_colors_8 in 128ms (par),
size_8_colors_9 in 990ms (par)** — both previously untested.

Key per-puzzle comparisons (Exp E numbers in parens):
| Puzzle | gacolor_ac3_par | Δ vs Exp E |
|---|---|---|
| size_8_colors_6 | **2,905 ms** | (gacolor_ac3_lcv_par was 7,229) ⇒ **−60%** |
| size_8_colors_7 | **53,818 ms** | (was 67,902 in Exp E) ⇒ **−21%** |
| size_8_colors_8 | 128 ms | (NEW — not in Exp E) |
| size_8_colors_9 | 990 ms | (NEW — not in Exp E) |

But the cache **hurts trivial puzzles**:
| Puzzle | Exp E ms | Exp I ms | Δ |
|---|---|---|---|
| size_7_colors_2 `gacolor_ac3` | 235 | 305 | +30% |
| size_8_colors_5 `gacolor_ac3` | 19 | 22 | +16% |

**Diagnosis** — the cache is built O(n_pos × |D|) at each AC-3 entry
even when AC-3 will return immediately. For easy puzzles the build
dominates; for hard puzzles the cache pays back because AC-3 does
millions of inner support checks. The **6%-60% improvement on the
hardest puzzles** is real and from the correct mechanism (reduced
O(|D|) inner cost).

**Verdict** — kept. Net positive on the puzzles that matter most
(hard / size 8 / multi-second). The trivial-puzzle regression is
<100 ms absolute and not worth complicating the code to remove.
A future "adaptive" approach could skip the cache build when
n_unplaced × |D| is below a threshold, but that's polish.

**Mathematical note** — the inner check is "is the bipartite
matching constraint between cells A and B locally satisfiable for
piece-rotation pair (r, side)?" This is a *rank query on a finite
set*: how many elements of `D[nb]` satisfy a per-color predicate.
The cache reduces it from a linear scan O(|D|) to a single read
O(1) plus a same-piece correction O(4). The asymptotic improvement
is |D|/5, but cache cold-misses, branch mispredicts, and the
amortized rebuild cost reduce the practical speedup to 5-60% on
heavy AC-3 workloads.

## Experiment K — Frontier survey (sizes 9-16 with varied colors)

**H** — Generating 104 new puzzles for sizes 9-16 with color counts
from 8-22 (Eternity II target = 22 colors) and running our SOTA
profile `gacolor_ac3_par` will reveal *where* our solver hits the wall.
This sizes-up by a factor of (16/8)² = 4× in cells from previous best.

**Setup** — 112 puzzles total in corpus, 15-60s budget per cell, 1 run.
Hot-path persistent buffers (revised Exp I implementation) used. JSON:
`data/expK_frontier.json`.

**Result (size 9 subset)**:
| Colors | Median ms | Status |
|---|---|---|
| 2 | 13.0 | ✓ |
| 3 | 32.2 | ✓ |
| 4 | 13.7 | ✓ |
| 5 | 244.7 | ✓ |
| 6 | 1170.3 | ✓ |
| **7** | 45,060+ | **✗ DNF** |
| **8** | 90,355+ | **✗ DNF** |
| 10 | 6,657 | ✓ |
| 11 | 511 | ✓ |
| 12-22 | 42-180 | ✓ all fast |

**MAJOR FINDING — non-monotonic difficulty.** Difficulty *decreases*
with both very few AND very many colors; peaks in the middle (~7-8
colors on size 9). This is the **Goldilocks zone of constraint
density**:
- Few colors → pieces are massively duplicated → uniqueness propagator
  + GAColor kill branches early
- Many colors → near-unique edge patterns → AC-3 has rich support to
  exploit, propagation cascades aggressively
- Medium colors → enough variation to branch heavily, but not enough
  constraint to prune

**Implication for Eternity II**: real E2 is 16×16 × 22 colors, at the
DENSE end. By this curve our solver should be relatively *more*
effective at high color counts than at the apparent "easy" low-color
puzzles in the small-corpus benchmark. **Optimisation focus should
target high-density puzzles, not low-density ones.**

**Verdict** — kept as a key data point. The wall is not at "high
colors" but at "medium colors". Our solver scales with constraint
density, not with raw color count.

## Hot-path optimization (revised Exp I)

Moved AC-3 cache buffers (`ac3_count`, `ac3_present`, `ac3_on_queue`)
onto `SearchState` to eliminate per-call allocator round-trips.
Buffers are sized at construction; AC-3 entry zeros the relevant
slice in O(buffer_len) before rebuilding from current domains.

Justification on size 16: `count` is 256·4·23·2 = ~47KB,
`present` is 256·16·8 = ~32KB. Per-AC-3 zeroing is ~80KB bandwidth.
On M1 with ~50GB/s memory bandwidth this is 1.6µs per AC-3 entry —
negligible compared to typical AC-3 propagation cost. Pays for
itself if AC-3 runs more than once per allocation cycle, which is
trivially true.

## Community-knowledge survey (2026-05-11, agent research)

The Eternity II community has 15+ years of tribal knowledge. Key
sources: shortestpath.se (Verhaard), Ansótegui & Béjar (phase transition),
Wauters et al. META'10, Heule SAT 2008. Findings that **change strategy**:

### Counter to academic SOTA: domain-specific beats generic CP

The "Automatically Generating and Solving Eternity II Style Puzzles"
paper (Bond Univ, ~2018) reports **3 orders of magnitude speedup**
versus published backtracking solvers by **abandoning forward checking,
AC-3, and k-consistency**. They exploit:
- Uniform color distribution (known a priori)
- Edge-color assignment patterns specific to E2
- O(n) custom feasibility checks instead of O(n²·⁵) Régin matching

**Implication**: more AC-3 polish is misallocated effort. The path
forward is structure-aware pruning, not stronger generic CP.

### The record holders use offline analysis, not better search

Louis Verhaard's 467/480 (2008, $10K prize) uses **2×3 tile
compatibility scoring offline**:
- Pre-compute solutions count for every 2×3 sub-tile
- Group pieces as "precious / good / bad / useless" by score
- Use group classification to guide value selection at runtime
- Variable order is **empirically optimized**, NOT spiral/CHESS

The community confirms Fagerberg's spiral-inward order has **no
measurable advantage**. CHESS is similar — these are post-hoc
rationalisations of empirical orderings.

### Eternity II may be unsolvable

Ansótegui & Béjar showed E2 (n=16, cm=17) sits *exactly* at the
solvability phase transition. The puzzle is engineered for max
difficulty. **It is plausible — though unproven — that no
complete 480-edge solution exists.** Reasonable practical target:
**reproduce 467/480** via metaheuristic, not search for the
$2M solution.

### Best metaheuristic: hyper-heuristic with secondary objectives

Wauters et al. META'10 winner (461/480) uses:
- 5 neighborhood operators (singleton swap, even/odd chessboard,
  L-shaped blocks, hybrid SEO)
- Simulated annealing: T_0=5000, T_min=1, cooling=0.99
- **Secondary objectives** beyond edge-match count: color frequency
  balance, piece-frequency distribution
- Without secondary objectives → traps in local optima
- With them → escapes effectively

### Negative results from community

- Generic forward checking / k-consistency → too expensive vs structural
- Greedy piece placement (highest-degree first) → leaves degenerate states
- Pure simulated annealing without secondary objectives → traps
- Genetic algorithms → crossover too costly for this structure
- GPU acceleration → no production solver uses it; propagation is
  memory-bound on irregular constraint hypergraphs
- **Hopcroft-Karp matching → overkill at our scale; Kuhn's DFS faster**

### Open questions community can't resolve

- Why does Verhaard's "edge slipping" (allowing transient mismatches
  at deep search depth) work? Empirical only.
- Hardness cliff: at what size n=12..14 does the median instance
  become intractable?
- Solution density: ~1 solution in 10^40 configurations. No
  closed-form bound is known.

## Strategic pivot (2026-05-11)

Based on community evidence, our research priorities are:

| # | Idea | Class | Justification | Effort |
|---|---|---|---|---|
| **L** | **Local search hybrid** (SA + secondary obj.) | New paradigm | The only published technique reaching 461+ on E2 | 1 week |
| **M** | **2×3 piece-compatibility precompute** (Verhaard) | Domain knowledge | Best documented record holder's secret sauce | 2 days |
| **N** | **Région matching alldifferent** (still useful) | Algorithm | Cheap (~10K ops/cycle); cleans up our GAColor | 2 days |
| **O** | **Bench watchdog timeout (fixed today)** | Infrastructure | Necessary to measure anything else honestly | Done |
| P | Domain-specific propagation, drop AC-3 entirely | Experiment | Test Bond Univ paper's claim on our corpus | 2 days |
| Q | Distributed parallel (>16 cores) | Engineering | Verhaard scaled to 80 processors; we're CPU-capped | 1 week |

Synthesized ranking deprecated; replaced by the table above. The
Régin item drops in priority (community says it's overkill); the
Verhaard offline-analysis item rises sharply.

## Experiment L v1 — Local search (SA) baseline

**H** — A simulated-annealing local search on the space of complete
placements should reach scores comparable to Wauters et al. META'10
(461/480 on real E2) on our generated puzzles. Two neighbourhoods:
single rotation, swap-then-best-rotate.

**Setup** — new crate `eternity2-localsearch`. Random initial
placement (class-correct: corners→corner cells, etc.). SA acceptance
with calibrated temperature (T_start=2.0, T_min=0.05, cooling=0.999
per 5000 iterations). Re-anneal on freeze. Incremental scoring
(O(4-8) per move). 30% rotate moves, 70% swap+best-rot.

**Result** — single-puzzle measurements:
| Puzzle | Budget | Score / Total | % |
|---|---|---|---|
| size=8 colors=7 | 5s | 51 / 112 | **45%** |
| size=8 colors=7 | 60s | 53 / 112 | **47%** |
| size=10 colors=10 | 5s | 58 / 180 | **32%** |
| size=16 colors=22 | 15s | 81 / 480 | **17%** |

Per 5s: ~24M iterations on size 8, ~85M on size 16. Iteration rate
limited by `local_match_count` overhead, not allocator.

**Diagnosis** — pure SA stalls fast at this baseline level. The
size-8 60s run shows only +2 points improvement over 5s, meaning
the algorithm converges into a local-optimum trap and re-annealing
does not free it.

What's missing (Wauters et al. ingredients we still need):
1. **Secondary objective** — track color frequency balance & piece
   distribution; use as a soft objective alongside edge matches.
2. **Larger neighbourhoods** — L-shape, chessboard-parity swap, SEO.
3. **Targeted moves** — pick pieces with mismatched edges first; try
   to find them a better home rather than uniform random swaps.
4. **Multi-piece chains** — sequence of swaps that resolve multiple
   violations at once. Random pairwise gets stuck.

**Verdict** — v0 baseline, kept. Establishes that pure-SA-without-
guidance plateaus at 45% on size 8. The bigger wins from this
direction come from (a) CP-then-LS hybrid (use our solver to seed
SA), and (b) Verhaard piece-classification (Exp M).

## Experiment Z — Official Eternity II puzzle (2026-05-11, headline result)

The actual Eternity II 16×16 puzzle is available at
`data/puzzles/size_16_official_eternity.csv` (256 pieces, 22 interior
colors, 5 community-known hints including the famous "I clue" at
piece 138, position (7, 8)). Updated `loader::load_puzzle_with_hints`
to parse hint columns from the CSV.

**Hypothesis** — Even with our existing solver (no Verhaard scoring,
no Régin matching, baseline SA), we can put a credible number on the
board for the real Eternity II puzzle. Community record: 467/480
edges (Verhaard 2008, $10K Eternity Foundation prize).

**Setup** — `EngineSolver::gacolor_ac3_par()` profile, hints from
puzzle file enabled, wall-clock budgets varied. Bench binary:
`crates/benchmark/src/bin/official_e2.rs`.

**Result (CP only)**:
| Budget | Pieces placed | Edges | % of 480 |
|---|---|---|---|
| 30 s | 173 / 256 | 289 | **60.2%** |
| 300 s | 178 / 256 | 302 | **62.9%** |

**This is a real first-shot result on the actual puzzle**, with no
Eternity-II-specific tuning. The convergence pattern (10× more time
→ +5 pieces) shows CP backtracking hits a partial-fix saturation
where it cannot improve further without local-search moves.

For comparison, a pure-random LS baseline (no CP seed) got 21% in 30s.
The hybrid CP→LS path (LS seeded from CP partial) is being measured.

Community context: the prior C++ solver in this repo's
`data/partial_results/` shows the legacy approach got to 205/256
pieces placed (≈ 376/480 edges estimated). Our Rust v2 in 30 seconds
matches the order of magnitude of prior local efforts.

**Verdict** — milestone. Confirmed the solver works on the real
puzzle and produces non-trivial output. The 62% → 97% gap is the
real research problem from here forward.

## Experiment K (interim) — Frontier survey results

Bench running with 30s budget per cell, gacolor_ac3_par profile.

**Solvability pattern observed** (sizes 10-13 so far):

| Size | Hard zone (DNF at 30s) | Easy zone (✓ in <30s) |
|---|---|---|
| 10 | colors 8-11 | colors 12-22 |
| 11 | colors 8-14 | colors 15-22 |
| 12 | colors 8-16 | colors 17-22 |
| 13 | colors ≥10, possibly all of 10-22 | TBD |

**Hard zone WIDENS with size.** By size 13, even high-color
(colors 17+) puzzles enter the hard zone. Implication: the colors
22 case at size 16 may NOT be in the easy zone as size-10 data
suggested. The phase transition position depends on (size, colors)
jointly.

**Confirms community wisdom**: Eternity II at (16, 22) likely sits
in or near the hard zone, which is why no one has cracked it.

## Synthesised ranking of next experiments (deprecated, kept for trace)

After Exp E, our next-best experiments ranked by
expected leverage × implementation cost:

| # | Idea | Class | Effort | Expected impact |
|---|---|---|---|---|
| **I** | **Bitmask color-side buckets** (hot-path) | Code-opt | 0.5 day | Unlocks serial LCV; speeds AC-3 inner loop |
| **J** | **AC-2001** (delta-based AC, Bessière 2001) | Algorithm | 1 day | Strict improvement over AC-3, expected 2× |
| 1 | Spatial energetic reasoning for color supply | Algorithm | 1 day | Strong on size 8 (hardest) |
| 2 | SAC at root nodes (greedy SAC, Bessière 2005) | Math/Algorithm | 1 day | Modest constant factor |
| 3 | Régin matching GAColor (full version) | Math/Algorithm | 2-3 days | Unlocks CHESS, paper-validated |
| 4 | CDCL-style nogood learning | Algorithm | 5+ days | Potentially huge but complex |
| 5 | Local search post-AC-3 | Algorithm | 2 days | For unsat instances |
| 6 | Adaptive solver dispatch (early-bt sniffing) | Meta | 1 day | Reconciles trivial-vs-hard regimes |

The data from Exp E forces a clear next step: **(I) bitmask color-side
buckets**. Both AC-3's inner support check AND LCV scoring scan a
full neighbour domain to count rows with `edges[side] == color`.
If we index each `domains[pos]` by `(side, color) → bitmask` we get
O(1) count via `popcnt`. This single change makes serial LCV ~|D|×
cheaper per node (size 8: ~600× reduction in inner ops) and should
flip serial LCV from −270% to net positive. It also speeds AC-3,
which currently dominates serial hot path at ~100 prop/node.

Mathematical underpinning for (I): the check we run is "does
piece with `edges[s]=c` exist in `domains[nb]`?". This is a
**rank query on a set**, which bitmask + popcnt solves in
O(W) where W = bit width, vs O(|D|) linear scan. For |D| up to
8·N² ≤ 1024 on size 16, two u64s suffice.

## Methodology rule

Every experiment writes one section here with:
- **H** — hypothesis in one sentence.
- **Setup** — corpus, runs/cell, profiles compared.
- **Result** — JSON path + headline numbers (median ms, nodes,
  backtracks).
- **Verdict** — kept / dropped / iterated, with one-line reason.

No experiment is "successful" without numbers from the same corpus
under the same budget.

---

## Experiment N — RTCP (Region-Tear with CP)

**H** — iterative CP-based repair of best_partial breaks the 65% SA ceiling.

**Idea** — pin every "locally perfect" cell (every placed cell whose edges to placed neighbors all match), free the rest. Re-run CP on the freed sub-problem. Iterate.

**Result** — works but underwhelming. Each iter pinned ~174 cells and freed ~82. CP couldn't extend with <30s budget (sub-problem is hard); with 60s budget, +11 edges/iter, but anchor grows ~4 cells/iter. Net behavior ≈ running CP longer + structural overhead. Not a *structural* breakthrough.

**Why it's not enough** — RTCP is still in the CP+LS paradigm. It moves work between CP invocations but doesn't change the *type* of inference. The bottleneck on hard E2 isn't "CP needs more time" — it's "CP's pointwise propagation can't reason about cooperative multi-cell infeasibility."

**Verdict** — kept as a tool, not the breakthrough. Real innovation needs to attack the inference type.

---

## Pivot — Looking at the problem from physics, not CP

The overshadowing element in E2 research: **everyone treats the problem as piece-first CSP**. Pieces are atoms, placement is choice. AC-3, GAColor, parity, Régin matching — all are local pointwise propagators that ask "given this neighbor, is this piece legal at this cell?"

In **statistical physics**, the same kind of lattice constraint problem (Ising models, spin glasses, lattice gauge theory) has gone through *exactly* this hierarchy and *moved past it*. The breakthrough techniques:

1. **Renormalization group**: coarse-grain. Solve at scale, then refine.
2. **Cluster algorithms (Swendsen-Wang, Wolff)**: flip whole correlated clusters simultaneously, not single spins. Beats critical slowing.
3. **Belief propagation / survey propagation**: each site sends marginal beliefs to neighbors; iterate. Cracks random k-SAT in the hard phase.
4. **Gauss / plaquette constraints in lattice gauge theory**: for every closed contour, the holonomy must be trivial. This propagates *over loops*, not edges.

The key insight: **lattice problems have global topological constraints that are invisible to pointwise propagation.**

In E2, for any closed sub-region with perimeter Γ, the multiset of colors on Γ must be realizable by *some* assignment of remaining pieces inside. This is a **sub-region Gauss law**: an exact local constraint that's stronger than AC-3 because it reasons about cooperative interactions.

## Experiment O — Sub-Region Gauss Law (SRGL) propagator

**H** — propagating block-realizability constraints over k×k sub-regions prunes search trees that pointwise AC-3 misses entirely.

**Setup (k=2)** — for every 2×2 sub-region of the board, propagate this constraint:
  - the 4 cells consume 4 pieces from the bag
  - the 4 internal edges (2 horizontal + 2 vertical inside the block) must match
  - the 8 perimeter sides must match neighboring cells (placed or domain-constrained)

When a cell's value is tried, propagate via SRGL: filter out cell-values that make any containing 2×2 block infeasible. A 2×2 block has up to ~250 piece tuples × rotations ≈ 4-second precompute.

**Setup (k=3)** — 3×3 sub-region. 9 pieces, 12 internal edges, 12 perimeter sides. Combinatorial explosion: 256^9 / 9! piece selections × 4^9 rotations ≈ infeasible to enumerate. Instead: when checking, do a *small* backtrack search (≤ a few milliseconds) over the remaining domain pieces.

**Why this is novel** — to my knowledge no published E2 solver does sub-region propagation. Régin's matching propagator is on the whole board (color-flow rank). AC-3 is pointwise. Plaquette constraints from lattice gauge theory are the analog.

**Status** — designing.

---

## The more radical idea — Edge-First Formulation (EFF)

The E2 community uses one formulation: variables = 256 cells, domains = 1024 piece×rotations. AC-3, GAColor, parity all operate on this graph.

**Alternative formulation**: variables = 480 internal edges, domains = 22 colors.
- Constraint: at every cell, the 4 surrounding edge-colors must form a multiset realizable by *some* piece's edges in *some* rotation.
- Constraint: across all 480 edges, color c appears exactly count_c / 2 times (where count_c = sum over pieces of color-c sides).

Search-space bits: 480·log₂(22) ≈ 2143 vs 256·log₂(1024) = 2560. Edge formulation is *smaller*. And:
- LP relaxation of color counts is convex → polynomial bounds.
- Cell-realizability check is bipartite matching → polynomial.
- Branching on most-constrained edge propagates faster than branching on cell (4 edges constrained per cell-decision, vs 1 edge per cell-decision).

**Why nobody does this**: the cell-first formulation is "obviously" right since pieces ARE objects. But for *constraint propagation* purposes, the edge formulation might be radically better. To my knowledge no published E2 solver uses edge-color search variables.

**Prototyping plan**:
1. First test the *cheaper* hypothesis: does sub-region cooperative inference (k=2 SRGL) prune the cell-first formulation? If yes, the cooperative-inference family of ideas is fertile. If no, pivot.
2. If 2×2 SRGL helps, scale to k=3 and to LP-based edge-color planning.
3. If neither helps, the bottleneck isn't propagation strength — it's something else (heuristic ordering? value selection?).

---

## Experiment P+Q+greedy-fill — HEADLINE RESULT

Three changes shipped together:
1. **Parallel Tempering** with 4-8 replicas at T ∈ [0.05, 0.4], replica-exchange every 30k-50k inner iters (`pt::run_pt_from`).
2. **Cluster moves**: 2×2 interior-block rotation (CW/CCW), 10% of SA iterations (Wolff-flavored cluster algorithm).
3. **Greedy initial fill**: when seeding from CP partial, fill empty cells with the leftover piece+rotation maximising local match count (vs the previous random fill, which destroyed CP progress).

**Headline**: 87.9% (422/480 edges) on official Eternity II, in 14 seconds of PT after a 10-second CP phase. Up from 65% baseline (best from earlier hybrid).

Replicates of the discovery:
- 4 replicas, T=[0.05, 0.4], 30k inner iters, cluster moves: 422 in 14s
- 8 replicas, T=[0.05, 0.4], 50k inner iters: TBD (running)

**Attribution**: the dominant contributor is almost certainly the **greedy fill**, not PT itself — the per-chain scores during PT walk in [40, 80] regardless of temperature, but `global_best` jumps to 422 within the first few rounds. That means *one* chain's INITIAL fill already produced a board near 422, and the rest of PT hasn't beaten it (yet). The greedy fill alone produces a strong locally-optimal placement of the leftover pieces given the CP partial — something the random fill never achieved.

**Lesson**: random initial state is *catastrophically* expensive for CP+SA hybrids on hard puzzles. The 79 empty cells in our CP partial, randomly filled, broke ~200 boundary edges with the CP-placed neighbors — net score went from 289 down to ~80. SA could only climb back to ~305 in 60s. Greedy fill keeps the 289 *and* recovers most of the freed-region matches in a single sweep.

**Verdict**: keeping all three. Need to verify which of {PT, clusters} adds incremental value on top of greedy fill alone.

---

## CRITICAL BUG FIXED — Metropolis sign error in SA acceptance

The original `run_sa_loop` in `crates/localsearch/src/lib.rs` had a sign error in the SA Metropolis criterion that had been silently destroying optimization:

```rust
// WRONG — accepted ALL score-decreasing moves with prob > 1
let p = (-(delta as f64) / temp).exp();
```

For `delta < 0` (move decreases score) and any positive `temp`:
- `-delta > 0`, divided by temp gives positive, exp gives value > 1
- `rng.next_f64() < p` is ALWAYS true (since rng ∈ [0,1) < any p > 1)

**Result**: SA was running with *anti-Metropolis* — every score-decreasing move was accepted, every score-improving move was accepted. Effective behavior = pure random walk regardless of temperature.

Correct formulation: accept prob for ΔE = -delta_score (we minimize energy = maximize score) is exp(-ΔE/T) = exp(delta_score / T). For delta=-1, T=0.05: exp(-20) ≈ 2e-9 — properly rejects.

Fix:
```rust
let p = (delta as f64 / temp).exp();
```

Applied to all 5 occurrences (rotate-step in run_sa_loop, swap-step in run_sa_loop, rotate-step in run_sa_steps_fixed_temp, swap-step in run_sa_steps_fixed_temp, cluster-rotate in run_sa_steps_fixed_temp).

**Headline result post-fix**: PT with 4 replicas, 30s on official E2 → **442/480 (92.1%)**. Cold chain converges to 442; hotter chains explore lower scores.

**Honest assessment**: prior to this fix, *our entire SA baseline (the "65% in 4min" result) was sampling from an essentially-random walk and producing whatever near-random configuration happened to be locally-optimal-after-greedy-fill*. The CP+SA "65%" was almost entirely the CP partial plus the side-effect of random shuffling around it. Real SA was never doing useful annealing.

This explains why earlier our SA never broke ceiling regardless of temperature, schedule, or operator mix — none of the parameters mattered.

**Re-validation needed**: the existing "Experiment L v1 — SA baseline 65%" result in this notes file is invalid. With Metropolis fixed, single-T SA should reach much higher.

---

## Experiment U — 3×3 cluster + targeted swap + region swap

Added three new move kinds to the SA neighborhood:

1. **3×3 cluster rotation** (10% probability). Same math as 2×2 cluster rotate: under rigid rotation by 90° CW/CCW, internal edge match-count is preserved (each internal edge maps to another internal edge), only the 12 perimeter edges contribute to score delta.

2. **Targeted swap** (20% probability). Sample K=8 random cells from a class, pick the one with lowest local match count as the "worst", do the same for the swap partner. Standard informed-proposal SA technique; not used by published E2 community.

3. **Region swap** (10% probability). Swap two non-overlapping non-adjacent 2×2 interior blocks. Non-rigid multi-piece move — internal block edges change because the pieces change identity. Designed to escape glassy basins that rigid cluster rotations cannot.

The final move mix:
- 20% single rotate
- 10% 2×2 rigid cluster rotate
- 10% 3×3 rigid cluster rotate
- 20% targeted swap (worst-of-K)
- 10% region swap (block↔block)
- 30% random swap

**Result on official Eternity II** (CP 30s + PT 180s, 8 replicas, T=[0.02, 0.5]):
- Without region swap (just 3×3 + targeted): TBD
- With region swap: TBD

Both pending.

## Discussion: why the 448 plateau is hard

After ~30s of PT, all cold replicas converge to score 446-449 and stay there for hours. The plateau corresponds to a deep basin in the energy landscape: 32 mismatched edges that any single rotate/swap move can't reduce because the mismatches are *interlocked* (fixing one creates another). 

To break this plateau we need either:
- (a) Multi-piece *coordinated* moves where pieces 1, 2, 3, … move to specific places that *cooperatively* fix the constraints. Cluster rotations are too rigid (just permute pieces). Region swap is non-rigid but the swap candidates are random — unlikely to find the right 4-piece coordination.
- (b) Structural CP propagation that resolves these constraints upstream: SRGL, edge-first formulation.
- (c) Population-based methods: keep many distinct cold configurations alive, crossover them. Hasn't been tried in PT-flavor for E2.

Option (b) is the next innovation push.
