# External Brainstorm Archive — 2026-05-18

**Source**: External LLM conversation. User asked for cross-domain
inventions over 5 rounds. Result: ~25 ideas, some borrowed from
literature (round 1-2), some genuinely invented (rounds 3-5).

**User directive**: "Write them down somewhere and remember to get a look
there when I ask you to innovate." → This file is the canonical
invention reservoir.

**Load order**: When user says "innovate" or autonomous goal needs a
new attack vector, **READ THIS FILE FIRST** along with
`WALL_BREAKING_INVENTIONS.md`.

---

## Standard vs custom in our current stack (round 0)

**Standard / textbook**:
- ALNS (Ropke & Pisinger): destroy → repair → adaptive-weight
- `random_region` = "random removal" destroy op
- `worst_window` / `worst_band` = "worst removal" variant
- SA repair with T=1.0 (textbook acceptance mechanism)
- MWPM (Edmonds blossom) = polynomial-time min-weight perfect matching;
  used in surface-code QEC decoders, applied here to mismatched-edge
  defect pairing
- DFS pre-seed = standard hybrid pattern

**Custom (ours)**:
- `preset basic`, `minimal ops` = our config vocabulary
- `worst_band` with band size 4 = OUR design choice; strip respects 2D
  adjacency better than random-cell removal
- `conflict_driven` = our adaptation of CDCL terminology to a destroy op
- `mwpm_defect_pair` = our adaptation of MWPM to E2 mismatched edges
- `bf_bw`, `Blackwood-fast`, `v17a schedule`, `seed-offset N` = entirely
  internal naming

---

## Round 1 — Repair upgrades + cluster geometry (drop-in)

### A. Repair upgrades (drop-in for SA)

**`tn_exact_repair`** (from tensor-network QEC decoding)
- When destroy gives a band of 4-6 cells with FIXED boundary, that's a
  tiny sub-CSP, quasi-1D.
- Build as tensor network: cells = tensors indexed by piece-orientation,
  shared edges = bonds carrying colour-match constraint, contract
  left-to-right.
- Get **provably optimal** refill of that window, not stochastic guess.
- Why: tensor-network decoders achieve SOTA QEC accuracy by capturing
  correlations matching-based decoders miss.
- Cost: cheap for band width ≤ 6.

**`wfc_repair`** (from Wave Function Collapse)
- Replace random SA fill with WFC's repair primitive: keep each empty
  cell's superposition (still-legal piece-orientations given placed
  neighbours), always collapse cell with LEAST entropy, propagate.
- Front-loads forced cells, surfaces contradictions early.
- On contradiction: backjump to lowest-entropy decision that could've
  caused it, instead of restarting whole repair.

### B. Search-geometry upgrades (cluster-escape)

**Parallel tempering replacing SA**
- Ladder of boards at rising temperatures, all running ALNS, periodic
  replica-exchange swaps.
- Cold replicas exploit, hot ones tunnel across clusters, swaps shuttle
  good structure downward.
- **NOVEL TWIST**: don't temper just SA-temperature — temper destroy
  aggressiveness. Hot replicas run `worst_band{8}` or whole-region
  destroys; cold replicas run `worst_band{2}`. A **neighborhood-size
  ladder**. This appears genuinely novel.

**`sp_frozen_core`** (survey-propagation-guided destroy)
- Stop choosing destroy location purely by current cost.
- Run BP/SP sweep on factor graph → which cells are confidently frozen
  vs paramagnetic/contradicted.
- Destroy everything EXCEPT BP-confident frozen core; repair the rest.
- During repair, decimate: lock frozen cells first, solve outward.
- Genuinely novel for E2 — nobody's pointed SP-guided LNS at this puzzle.

**Constraint-homotopy seeding**
- E2 has sharp hard/easy phase boundary in constraint density.
- Solve a RELAXED puzzle first (allow K colour mismatches, easy phase),
  then anneal K → 0, each relaxed solution seeding the next.
- Walk instance from easy phase into hard phase carrying a solution.

**Disagreement-targeted destroy** (from QEC decoder ensembling)
- Run several cheap repairers (SA, greedy, TN) on same window.
- Consensus cells are probably right; disagreement cells = hard frontier.
- Feed disagreement map back as next destroy target.

### C. The wild one — `flux_loop`
- Surface-code logic: don't fix every physical error, fix the homology
  class.
- Define cheap invariant: for each colour, signed count crossing each
  row/column cut (discrete "flux").
- When board's flux class is incompatible with any solution, local
  operators are mathematically futile.
- Fix: homology-changing macro-move — destroy pieces along a CLOSED
  LOOP through the board, reconnect with cyclic shift, deliberately
  changing the global invariant while barely touching local cost.
- Lifts `mwpm_defect_pair` to the thing QEC decoding is actually about:
  repairing topology.

---

## Round 2 — Five more (more disruptive)

### Cube-and-conquer — exact path
- Most effective method for very hard combinatorial problems via SAT.
- Cracked Erdős discrepancy, Boolean Pythagorean Triples, Schur numbers.
- Two phases: lookahead solver partitions problem into MILLIONS of cubes
  (conjunctions of decisions), CDCL solver solves each.
- Parallelizes beautifully — near-linear speedup on thousands of cores.
- For E2: encode CNF → lookahead split border + outer-ring → kissat per
  cube.
- Deep idea: split only until subproblem becomes CDCL-easy (measured by
  conflict count) → principled replacement for fixed v17a schedule.
- This is the most credible route to a true full 16×16 solve.

### NRPA — single-player game
- Nested Rollout Policy Adaptation. World records in Morpion Solitaire,
  crosswords. Works on graph colouring, RNA folding, retrosynthesis.
- Learns playout policy ONLINE — adapts to instance at hand.
- Each move has a weight; gradient-nudged toward best sequence found at
  each recursion level.
- NRPA's learned weight array = self-improving version of LCV/value-order.
- Use to REPLACE bf_bw as seeder, or loop: NRPA constructs, ALNS
  repairs, NRPA policy learns from repaired.
- Variants: Stabilized-NRPA, Beam-NRPA.

### FunSearch — evolve operators with LLM
- LLM + island-based evolution evolves code for heuristics.
- Made first discoveries in open math problems, beat hand-tuned
  bin-packing heuristics.
- Point at: bf_bw branching/value-order function, new destroy ops as
  Python functions.
- "Invent the inventor".
- Refinements: EoH, EvoTune.

### QUBO / Ising — classical Ising solvers
- Reframe as ground-state search. Binary x[cell,piece,rot], one-hot
  penalties, edge-pair penalties → Ising Hamiltonian.
- Skip quantum hardware. Use quantum-inspired classical solvers:
  - Simulated bifurcation machines
  - Digital annealers (Fujitsu)
  - Parallel-tempering Ising samplers
  - Toshiba SBM
- E2 QUBO: ~262k binaries (fine for classical, choke for hw embedding).

### Streamlining + heavy-tailed restarts
- **Streamlining** (Gomes & Sellmann): add constraints NOT logically
  implied but bias toward STRUCTURED solutions (e.g. force colour into
  regular pattern). Search collapses dramatically if streamliner doesn't
  destroy feasibility.
- **Heavy-tailed restarts**: backtracking has heavy-tailed runtime.
  Randomize bf_bw branching, use **Luby-sequence rapid restarts** to
  harvest lucky-fast tail. One-day change, potentially large payoff.

---

## Round 3 — Genuinely invented (named here)

### PRISM — chromatic dual decomposition
- Stop searching piece placements. Search the EDGE COLOURING, split by
  colour.
- 17 colour layers (interior). Layer C decides which edges are colour C.
- Coupled (each cell has 4 edges, each piece used once).
- Lagrangian decomposition with dual prices λ on coupling constraints.
- Iterate: (1) 17 layers solve independently given prices, parallel;
  (2) update prices on violated couplings; (3) repeat.
- ADMM consensus step reassembles board.
- **Nobody decomposes E2 along COLOUR axis.** Real dual bound for free.
- Scarce colours (5 rare interior, 5 medium) lead the negotiation.
- Risk: non-convex coupling → ADMM convergence not guaranteed; gives
  strong heuristic + bound, not proof.

### CONCRETION — molecular pre-compilation
- Pure counting on PIECE SET, before any board search.
- Colour C on only k edge-slots → k/2 matched adjacencies. When k small,
  very few legal pairings → each forces specific neighbour-pairs.
- Chain: A must touch B, B must touch C → **rigid molecule** with frozen
  internal geometry.
- Iterate to fixed point. Puzzle becomes ~40 rigid molecules + free
  pieces. 4^internal × placement freedom collapses super-exponentially.
- Then run ALNS / cube-and-conquer / PRISM on COMPILED instance.
- **Pure preprocessor — all upside.**
- Risk: E2 designed to minimise exploitable structure → molecules may
  be small (size 2-3). But even modest concretion multiplies downstream.

### GRAIN — polycrystalline annealing
- Metallurgy + DNA tile self-assembly with INVENTORY CONSTRAINT.
- Drop several seeds across board. Each grows locally-perfect crystal
  patch via greedy/WFC attachment.
- All competing for shared piece inventory.
- Crystals expand until they collide → **grain boundaries** (mismatch
  seams).
- A perfect solution = single crystal, zero grain boundaries.
- Score = total grain-boundary energy.
- Destroy = **recrystallisation**: dissolve pieces along boundary back
  to inventory, let adjacent grains regrow.
- Annealing = literal metallurgical (heat boundary, cool slowly).
- PT integrates: hot = many small grains, cold = few large, swaps =
  grain transplants.
- **Nobody models E2 as multiple competing growth fronts with migrating
  defect seams.** Grain boundary is principled destroy target.
- Risk: managing shared inventory across grains is fiddly; grains can
  deadlock over a piece. But deadlock IS signal — proves the two grains
  are chromatically incompatible.

### PALIMPSEST — consensus from search history
- Across thousands of runs, solver visits thousands of high-scoring
  boards. Cloud has signal.
- Adjacency present in every >460 board = almost certainly correct.
- Adjacency present in half = contested.
- Log every near-solution. Build score-weighted frequency map over
  adjacencies. **Palimpsest** — each run overwrites the board, true
  structure shows through.
- Soft-pin high-consensus adjacencies (statistical CONCRETION).
- Aim destroy at low-consensus regions.
- **Counterintuitive**: watch for **consensus traps** — if 99% agree on
  a region but nobody breaks 470, the consensus is the WRONG cluster.
  Deliberately destroy the high-agreement core.
- Distinct from ensemble disagreement (many solvers/instant) and NRPA
  (online policy) — PALIMPSEST mines historical archive, uses
  persistence-across-overwrites as truth signal.
- Risk: survivorship bias — systematic blind spots poison consensus.

**STRATA architecture** = CONCRETION → PRISM/GRAIN → PALIMPSEST → re-prime.

**Moonshot**: DMRG on whole board. Distribution over boards as MPS,
imaginary-time evolution toward ground state of mismatch Hamiltonian.
Round 1 TN was one window; this is the whole 16×16.

---

## Round 4 — Yet more (ordered by author's belief)

### CONCORD — difference map (Veit Elser)
- **Projection method**, not descent. Cracked Sudoku, sphere packing,
  protein folding, bit retrieval.
- Two constraint sets, each easy to project onto:
  - **Set A**: every cell holds exactly one valid piece-orientation.
  - **Set B**: every piece used exactly once + every shared edge consistent.
- Iterate: `x → x + β·[P_A(2·P_B(x) − x) − P_B(x)]`.
- **NOT a descent method** — routinely moves uphill → doesn't get pinned
  in local optima like SA.
- Fixed point ⇒ solution.
- **Cleanest answer to cluster-wall problem.**
- Risk: P_B is itself a matching problem (non-trivial but tractable).
  Tuning β matters.

### ATLAS — pattern-database heuristic (Korf)
- Replace naive mismatch-count objective with precomputed admissible
  heuristic.
- Borrowed from Rubik's cube + 15-puzzle solvers.
- Offline: for every local k-cell patch configuration (k=4-6), precompute
  min number of edge corrections to make consistent with ANY completion.
- Score board = sum of patch-distances → admissible, smoother gradient.
- Powers IDA*/A* with genuine pruning.
- ALSO supercharges ALNS — better gradient, better destroy target.
- Risk: DB size, will compress (Korf-style). Lower bound since ignores
  inventory.

### FILAMENT — Lin-Kernighan for 2D
- Steal TSP's LK. Move = **chain of swaps**:
  - Swap two pieces → repairs one edge but breaks another.
  - Immediately swap to repair THAT edge, breaks new one.
  - Keep extending while cumulative gain positive.
  - Close when chain nets positive overall.
- Chain snakes through board like filament — each link locally bad, whole
  thread a win.
- Not standard for E2 — solvers do block swaps or region destroys, not
  variable-depth exchange chains.
- LK's superpower = escaping local optima fixed-size neighbourhoods can't.
- Risk: bookkeeping intricate; 2D has more chain directions than 1D tour
  — need discipline for which broken edge to chase next.

### TURBO — row/column turbo decoding
- Decode E2 like a modem decodes noise.
- **Rows decoder**: each of 16 rows = 1D edge-matching strip (easy).
- **Columns decoder**: same for columns.
- Each produces soft per-cell beliefs; SWAP extrinsic information; iterate.
- Generalizes round-1 MWPM/BP into a real iterative soft-decision decoder
  with clean 2-component structure matched to grid's two axes.
- Risk: turbo shines when components are near-independent; row/col are
  entangled. Might converge to mush.

### TUNNEL — path-integral quantum annealing
- Sharpens QUBO direction. Replace thermal SA with simulated quantum
  annealing via path-integral Monte Carlo.
- Board = stack of imaginary-time replicas coupled along new dim, with
  transverse-field term.
- Thermal SA crosses barrier by climbing (unlikely if tall).
- QA tunnels through — probability depends on barrier WIDTH, not height.
- E2's clusters are walled by tall-but-thin barriers → tunnelling's home
  turf.
- Near-drop-in upgrade to SA repair.

### VANISH — Nullstellensatz (moonshot)
- E2 as polynomial equations over finite field.
- Solution exists iff system has common zero.
- Hilbert Nullstellensatz yields **certificates of infeasibility** (De
  Loera did this for graph colouring).
- Full board impractical. But as a fast **local infeasibility oracle**
  on small destroyed windows: algebraic "this patch can never be
  completed, stop trying" — could prune brutally.

---

## Round 5 — Last ideas (named, more speculative)

### PROVENANCE — solve the designer
- E2 didn't fall from sky. A person built it — built solution FIRST,
  then cut to pieces and shuffled.
- Hypothesize **generative models** for original grid:
  - Markovian local process?
  - Balanced PRNG?
  - Constructive heuristic?
- For each candidate model, derive **statistical fingerprint** it would
  imprint.
- Test fingerprints against the **piece multiset** (invariant of original
  grid; survives cutting): corner-pattern frequencies, edge-colour
  distributions.
- Identify generative family → sample solution candidates from inferred
  generator conditioned on reproducing exactly this piece set → search
  space orders of magnitude smaller than "all boards".
- Cryptanalysis of puzzle's birth.
- Risk: designers engineered E2 to have no exploitable statistical
  structure. PROVENANCE fights them on fortified ground. But piece-set
  statistics are a real untapped channel.

### THAW — graduated non-convexity
- Deform COST FUNCTION's shape while instance + true optimum stay fixed.
- One-parameter family of objectives:
  - t=0: heavily smoothed surrogate — soft quadratic mismatch penalties,
    fractional/probabilistic piece assignments → near-convex landscape,
    one obvious basin.
  - t=1: true rugged combinatorial objective.
- Slowly raise t, re-optimize from previous optimum each step.
- Minimum traces continuous path from "easy smooth world" → "true rugged
  world".
- Blake-Zisserman trick, never applied to E2.
- Risk: design t=0 so it's smooth AND minimum is near truth; continuation
  path can bifurcate.

### MURMUR — neural cellular automaton
- Each cell = state vector (piece-orientation belief + hidden channels).
- Small shared neural network reads neighbourhood, emits update.
- Iterate CA hundreds of steps.
- Train (Mordvintsev-style) on synthetic solved instances, or
  self-supervised consistency loss.
- Iteration flows boards toward valid tilings, repairing defects locally
  + massively parallel.
- **Learned WFC** where network discovers propagation rule.
- GPU-native, runs standalone or as ALNS repair op.
- Risk: purely local rule struggles with "each piece exactly once" global
  constraint. Mitigation: **pair with CONCORD's global inventory
  projection** — they compose cleanly.

### INTAGLIO — carve away the impossible
- Flip polarity. Stop building solutions. Start REMOVING what can't be
  one.
- Main data: space of still-possible local configurations.
- Main loop: delete configurations proven impossible.
- Mine database of **forbidden mesoscale patterns** — small patches that
  provably appear in no solution. Derive from:
  - Counting arguments
  - Piece multiset
  - Propagation
  - VANISH-style algebraic certificates
- Each forbidden pattern prunes everywhere it would occur.
- Progress measured in **volume of placement space eliminated**, not
  edges matched.
- Carve enough → residual small enough to enumerate.
- **Twin of CONCRETION**: CONCRETION compiles what MUST be, INTAGLIO
  carves what CANNOT. Squeeze space from both sides.
- Risk: forbidden-pattern DB can explode; must carve faster than it
  grows.

### SHADOW — moonshot (probably false but pretty)
- Quasicrystals look aperiodic but are projections of slices of
  HIGHER-DIMENSIONAL periodic lattices (de Bruijn cut-and-project, Penrose
  tilings).
- E2's solution looks aperiodic too.
- Wild hypothesis: is it 2D shadow of something simply periodic in 4D
  or 5D?
- If true: generate candidates by cut-and-project, not search.
- Almost certainly false (E2 is designed pseudo-random, not quasicrystal).
- But the prettiest false thing the brainstormer offered.

---

## Author's ranked bet (for triage)

**Build these first** (~25 ideas total → 3 to build):
1. **CONCORD** (difference map) — most likely to break cluster wall
2. **CONCRETION** (molecular pre-compilation) — pure-upside preprocessor
3. **ATLAS** (pattern-database heuristic) — fixes naive objective, helps
   every other method

**Strong second tier**:
- GRAIN
- Cube-and-conquer (for a true full solve)
- NRPA as seeder

**Wildcards worth one prototype each**:
- INTAGLIO
- PROVENANCE

---

## Notes on overlap with our existing work

Some of these we've ALREADY partly built / measured / refuted:

- **Survey propagation** (`sp_frozen_core`): we measured BP/SP in
  vols 11-12-13 → BP gave 18.84% interior reduction (cell-encoding);
  edge-BP useful as value-order; **SP itself was a dead-end**
  (`project_e2_dead_ends.md`). But BP-guided DESTROY (LNS large
  neighborhood guided by BP) is not yet built.
- **Cube-and-conquer**: T39 in our backlog. We tried kissat (W-SAT)
  in vol-123; never built the lookahead splitter.
- **QUBO**: W15 in old backlog, deleted. May resurrect if D-Wave token
  arrives.
- **Pattern databases**: novel for us.
- **MWPM defect pair**: already in ALNS `minimal` preset.
- **Parallel tempering**: we have `pt_e2`. Don't have the
  **destroy-aggressiveness ladder** twist.
- **Tensor networks**: vol-13 attempted boundary-MPS contraction →
  refuted as full-board method. Per-window TN repair (round 1 idea)
  is genuinely new.
- **Streamlining + heavy-tailed restarts**: not yet built.
- **NRPA**: not yet built.

---

## Build-order recommendation (mine, not the brainstormer's)

Given:
- We have FPL running (V125-T34)
- Standing record is 461 matched-edges / 459 strict / 469 McGavin
  matched-edges on alternate corner-perm
- 1278-board DB for PALIMPSEST analysis

**My top 5 next-actions to invent toward 462+**:

1. **FPL** (current, in progress) — score-conditioned pair log-odds.
2. **PALIMPSEST**: trivially built on top of FPL — same DB, same
   adjacency analysis, but ALSO measure **persistence** of high-score
   pairs across re-runs. Spawn ALNS that destroys the
   high-consensus-but-not-yet-462 cores.
3. **CONCORD** difference map — clean from-scratch implementation.
   Set A (cell-valid) and Set B (piece-uniqueness + edge-consistency)
   projections.
4. **Parallel tempering with destroy-aggressiveness ladder** — a small
   extension to our existing `pt_e2`, swaps replicas with different
   `worst_band{k}` sizes.
5. **FILAMENT** — variable-depth swap chain. Direct port of LK to
   2D-grid. ALNS interface compatible.

These are CONCRETE and BUILDABLE in a single autonomous session each.
The rest of the brainstorm (PROVENANCE, SHADOW, MURMUR) belongs to
multi-week R&D.
