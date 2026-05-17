# INVENTIONS BACKLOG

The systematic list of unexplored / partly-explored attacks on canonical 5-clue Selby-Riordan Eternity II.

**Established 2026-05-17** after vol-121 saturated every "anchor on existing 459/469" approach (joint MIPs, ALNS variants, MaxSAT — all Δ=0).

## Binding user directives (2026-05-17)

1. **STOP mixing previous 459 / 469 basins. Really stop.**
2. **Go engineering / inventor mode. You have a MONTH.**
3. **Spending 5 days on a single invention is OK.** Don't pre-shrink scope or pre-estimate "too long" — that's the [[../../CLAUDE|CLAUDE.md]] no-limiting-thoughts rule. If an invention seems "weeks-long", just start.

These supersede default "comfort-lottery" tendencies. If a vol task is ALNS-on-existing-basin or MIP-region-of-existing-basin, it violates directive 1 — pivot.

## How to use this page

Each invention has:
- **Status**: `unbuilt` / `partial` / `built-untested` / `built-tested` / `refuted` / `wont-do`
- **What's the idea** (one paragraph)
- **Why genuinely different** (escapes the "anchor on existing basin" trap)
- **Concrete first step** (a 1-day proof-of-concept that decides whether to invest deeper)
- **EV / effort estimate**
- **Linked vault pages**

**Picking order**: scan top-to-bottom; pick the topmost `unbuilt` or `partial` with effort ≤ available compute budget. Bias toward `partial` (momentum).

**Update discipline**: when an invention transitions status, edit its block here (don't quietly delete). When refuted, add the refutation reason. New inventions go at the bottom or in a thematic section.

---

## A. Generative / non-anchored basin discovery

### A1. Border-DP basin generation — status: `partial` (vol-122)

**Idea.** Generate partial boards backwards: enumerate (corner-perm × corner-rot) → solve border ring via 4-side chain DP → piece-unique 60-matched border → hand the 60-cell partial to interior solver.

**Why different.** Forward CSP search anchored on hint constraints produces correlated partials. Border-DP enumerates the 60-matched border space independently of hints. Yields combinatorially diverse starting points.

**Done (vol-122).** 24 corner-rot configs admit chain-UB=60; 50 piece-unique 60-borders sampled, all with distinct interior-color profiles; 5 dumped as `output/vol-122/border_partial_perm{0..4}_b{0..4}.json`. ALNS-direct from border partial = 403/480 (T3 attempt). **PIPELINE MISMATCH IDENTIFIED**: ALNS needs near-complete starting board, not 60-cell sparse partial. Per-border LP-UB on perm0 = 480 (LP allows perfect from this border).

**Next steps (revised).**
1. **Build CSP-fill from border partial as hints.** Wrapper bin that loads 60-cell partial as engine `Hints`, runs `joe_depth150_bp_par` or `vanilla_fast --pin-hints` variant, dumps ~200+cell completed partial.
2. ALNS basic 30min from each CSP-filled partial × multiple seeds.
3. If ANY reaches ≥460 matched-edges, that's a basin discovery beyond corpus.
4. Enumerate MANY more borders (thousands), group by interior-color profile, repeat pipeline per profile representative.
5. Per-border interior MIP (with full piece freedom on interior) — gives integer ceiling per border config.

**EV.** Medium-high. Border-DP yields combinatorially diverse partials. Bottleneck is the interior solver, not border generation.

**Effort.** Wrapper bin: 1 day. Sweep: ongoing.

**Concept**: [[../concepts/inv3-border-dp-seed]].

### A2. Random-path basin sweep — status: `built-untested` (vol-121 T2 invention, vol-122 T1 first use)

**Idea.** `vanilla_path --path-mode border-first-random --path-seed N`. Each path-seed → structurally distinct CSP search tree via Fisher-Yates interior shuffle.

**Why different.** Vol-60 thread-id-offset only shuffles per-step candidate buckets. Random-path actually permutes cell order → structurally different CSP trees.

**Done.** Invention shipped (vol-121 T2). vol-122 T1 in flight: 16 path-seeds × 5min × 8 threads + 32 ALNS basic × 5min.

**Next steps.**
1. Analyze T1 results: distribution of final ALNS scores per seed.
2. Pure random (not border-first-random) for comparison.
3. Mass-scale: 100 path-seeds × 30min vanilla × 8 threads (overnight).

**EV.** Medium. Path-order may not change basin equivalence class but cheap to test.

**Effort.** Already shipped; just runs.

### A3. Systematic corner-perm × corner-rot × seed sweep — status: `partial`

**Idea.** Each corner perm has 1-4 valid rotations per corner = up to 4⁴ = 256 corner-rot configs per perm × 24 perms = ~6000 configs. Vol-60 sampled only 24 partials × 4 seeds. Most configs unexplored.

**Why different.** Vol-60/119 stopped at 1-4 ALNS seeds per partial. Systematic sweep covers the corner-rot × seed cartesian.

**Done.** A1 border-DP enumerates corner-rot configs internally.

**Next steps.**
1. Top-level driver: for each (perm, corner-rot, path-seed), run pipeline.
2. Sample 100 random tuples per overnight.
3. Statistics + outliers = new basins.

**EV.** Medium. McGavin had specific (3,2,0,1) perm + specific rotation; other configs unexplored.

**Effort.** Driver: half-day. Compute: ongoing.

### A4. Hypergraph exact-cover via DLX (Knuth Algorithm X) — status: `unbuilt`

**Idea.** Formulate as exact cover: vertices = (cell, color-pair), hyperedges = pieces covering 4 (cell, color-pair) vertices when placed at position+rotation. Puzzle solved iff exact cover exists.

**Why different.** DLX is provably faster for exact cover than CSP backtracking. Rarely applied at this scale.

**Next steps.**
1. Minimal DLX in Rust on 4×4/6×6 (1 day).
2. Scale to 8×8 → 12×12 → 16×16 (1-2 days).
3. Adapt for MAX-matched (canonical E2 isn't pure exact-cover).

**EV.** Medium. DLX is asymptotically better; canonical E2 isn't pure exact-cover so adapted form needed.

**Effort.** ~3 days for canonical-scale.

### A5. Bidirectional search (corners-in + center-out, meet in middle) — status: `unbuilt`

**Idea.** Two CSP searches: corners growing inward + center growing outward. They MEET at a 14-cell ring.

**Why different.** All current search is unidirectional. Meeting-in-the-middle halves effective depth.

**Next steps.**
1. Specify meeting ring rigorously.
2. Implement two synchronized frontiers with periodic merge attempts.
3. Test on 8×8 generated puzzles.

**EV.** Medium-high IF meeting ring is small enough to enumerate.

**Effort.** ~5 days.

### A6. Iterative widening (concentric frames) — status: `partial` (vol-4 baseline)

**Idea.** Vol-4 did 2-level (border, then interior). Extend to 8 concentric squares (16→14→12→10→8→6→4→2). Each ring is much smaller; memoize ring solutions by inward color profile.

**Done.** Vol-4 set basin-450 with 2-level. Higher-level unbuilt.

**Next steps.**
1. Define rings, compute per-ring CSP size.
2. Solve outermost ring (= A1 border-DP).
3. Recurse + memoize.

**EV.** Medium. Memoization-based DP needed for tractability.

**Effort.** ~1 week.

---

## B. Stronger upper-bound attacks

### B1. Per-row LP-UB — status: `unbuilt`

**Idea.** Per-row LP-UB on each of 16 rows, sum minus border-double-count. Compare to vol-44 full-board UB=478.

**Why different.** Adds row-locality the full-board LP relaxes.

**Next steps.** Reuse `border_lp_ub` infra, restrict to one row, run on all 16, sum.

**EV.** Low-medium.

**Effort.** 1 day.

### B2. Lifted-LP B&P&C — status: `refuted-design` / `unbuilt-implementation`

**Idea.** Branch-and-price-and-cut with Lagrangian piece-uniqueness penalty.

**Done.** Vol-47/52/53 partial designs; McCormick formulation refuted. Full B&P&C unbuilt.

**Next steps.** Minimal B&P&C on 6×6/8×8 → measure LP-INT gap reduction → scale.

**EV.** Medium. Tighter UB doesn't directly find records.

**Effort.** 3-4 weeks.

### B3. Interior LP-UB per border profile — status: `unbuilt`

**Idea.** Once A1 enumerates 60-matched borders, compute interior LP-UB per profile. Rank borders. Top borders → intensive ALNS.

**Why different.** Vol-44 was full-board. Per-border-profile interior LP-UB is new.

**Next steps.**
1. Adapt `border_lp_ub` to take fixed border.
2. Run on each enumerated border.
3. Rank by interior LP-UB.

**EV.** High. Natural complement to A1.

**Effort.** ~3 days.

### B4. Color-pair supply Hall-condition — status: `refuted` (vol-122 2026-05-17)

**Idea.** For each color pair (c1,c2), compute supply (# edges that can have this pair) vs demand. Hall-marriage: perfect-matched board exists only if supply ≥ demand.

**Why different.** Vol-44 measured per-color UB (loose). Per-side rotation choice could expose a tighter Hall constraint.

**Done (vol-122).** Built LP and MIP with binary rotation choice per piece + per-color horizontal/vertical match budget + per-side supply constraints + geometric caps (h ≤ 240, v ≤ 240). **LP optimum = 480.0. MIP optimum = 480.0.** Hall does NOT tighten vol-44's 480 — rotation freedom is fully sufficient for side balance. Per-color k the LP achieves exactly floor(N_k/2) at the optimum.

**Refutation.** Side-imbalance hypothesis (vol-44 loose because of rotation-side mismatch) is refuted.

Concept: [[../concepts/inv-b4-hall-color-pair-refuted]]. Script: `scripts/vol122_inv_b4_color_pair_hall.py`.

**Future directions still open:**
- 3-cell column Hall (intra-piece constraints across two stacked adjacencies)
- Color-triple supply (corner-adjacent contiguous segments)
- True per-cell-pair LP gives 478 (vol-44); Hall+geometry could narrow further.

---

## C. Continuous / physical-system relaxations

### C1. Edge-tension GNN message-passing — status: `unbuilt-modern` (vol-21 `wont-do-as-Hopfield`)

**Idea.** GNN where messages = edge-color compatibility scores; fixed point = candidate board.

**Next steps.**
1. Train on synthetic 6×6/8×8.
2. Adapt for canonical 16×16.

**EV.** Low.

**Effort.** ~2 weeks.

### C2. Boundary-MPS — status: `refuted` (vol-13). DO NOT REVISIT.

### C3. Quantum annealing simulation — status: `unbuilt`

**Idea.** QUBO encoding for SA / D-Wave / Qiskit.

**EV.** Low (essentially ALNS in different parameterization).

**Effort.** ~1 week PoC.

---

## D. Structural / decomposition attacks

### D1. Piece-orbit symmetry — status: `wont-do` (vol-27). DO NOT REVISIT (canonical has no symmetries).

### D2. Twin-piece exploitation — status: `unbuilt`

**Idea.** Vol-65: 5 twin pairs (10 pieces). Use as interchangeable in MIP.

**EV.** Low (4% variable reduction max).

**Effort.** 1 day.

### D3. Topological constraint: mismatch β₁ = 0 — status: `unbuilt`

**Idea.** Vol-19 found low β₁. Constrain mismatch subgraph to acyclic. Adds as cutting plane.

**EV.** Medium.

**Effort.** ~3 days.

### D4. RL self-play (PPO/REINFORCE) — status: `unbuilt` (BACKLOG since vol-30)

**Idea.** Train RL agent to pick value-order during CSP. Reward = max depth/score.

**Done.** Vol-48/49 ES refuted. PPO/Q-learning unbuilt.

**Next steps.**
1. PPO loop on 6×6/8×8.
2. Self-play 1000 games.
3. Scale to 16×16.

**EV.** Medium-high. The unrefuted theoretical handhold per vol-114.

**Effort.** Multi-week.

### D5. Iterative-OT — status: `refuted` (vol-18). DO NOT REVISIT.

### D6. Cooperative pair-swap — status: `wont-do` (vol-24). DO NOT REVISIT.

---

## E. Solver / encoder improvements

### E1. MaxSAT encoder rebuild — status: `partial` (vol-17/vol-121)

**Done.** Encoder fails at scale (kissat UNKNOWN, z3 timeout).

**Next steps.**
1. Profile encoder for halo-1/halo-3.
2. Tighter encoding (Tseitin shortcuts).
3. Alternative solvers (RC2, EvalMaxSAT, MaxHS, UWrMaxSat).
4. Try as SAT decision query "score ≥ N?" → SAT/UNSAT.

**EV.** Medium.

**Effort.** ~1 week.

### E2. HiGHS warm-starting — status: `partial` (vol-121 T2 v3)

**Done.** CBC warmStart API didn't accept solution cleanly.

**Next steps.** Verify pulp/CBC API; try Gurobi or SCIP; try HiGHS-native.

**EV.** Medium.

**Effort.** ~3 days.

### E3. Engine: incremental AC-3 (vol-25 BACKLOG) — status: `partial`

**EV.** 10-15% on joe engine; not record-class.

**Effort.** 1-2 hours.

---

## F. Math / proof-direction

### F1. σ-subset theorem (vol-118/vol-119) — status: `proven-empirically`. No next step.

### F2. Prove K≤5 neighborhood lock analytically — status: `unbuilt`

**Idea.** Formalize empirical "all K≤5 moves are score-non-improving on basins". Prove or counterexample.

**EV.** Low-medium. Math, not records.

**Effort.** ~1 week.

### F3. Validate corpus-MIP methodology on small puzzles — status: `unbuilt`

**Idea.** On 5×5/6×6 generated puzzles, enumerate all boards, verify corpus-MIP-locked is truthful.

**EV.** Low. Validation.

**Effort.** ~3 days.

---

## G. Pipeline-composition (low priority — recombines existing tools)

### G1. CP+SAT cooperative — `unbuilt` (vol-17 candidate)
### G2. Verhaard set-SA — `unbuilt`
### G3. Houdayer cluster-swap ALNS — `unbuilt`
### G4. Cold portfolio refresh — `built` (vol-17), untested at scale
### G5. Pipeline with 4/5 hint pinning (1 free) — `unbuilt`

**Idea.** Strict-canonical uses 5/5. Vol-60 459 record uses 4/5 (gives up pos 210). Systematize: which hint to unpin yields the best basin?

**Next steps.** Modify bf_bw_schedule_hinted with --unpin-hint flag. Sweep all 5 hints × seeds.

**EV.** Medium.

**Effort.** ~2 days.

---

## H. Long-horizon / multi-week (worth weeks of compute)

### H1. Massive corner-rot × seed sweep — A3 at scale

**EV.** High via breadth.

**Effort.** Driver 1 day, compute months.

### H2. Re-run cross-machine SOTA recipe properly — status: `unbuilt`

**Idea.** vanilla_path border-first × 9 threads × 30min × multiple corner perms, then ALNS basic 30min × multiple seeds. 12h overnight.

**Done.** Vol-121 T1a/T1b tried 2 offsets each.

**Next steps.** 16+ offsets × 30min × 8 threads no-pin-hints, each → ALNS × 4 seeds.

**EV.** Medium. Replicates SOTA at our compute budget.

**Effort.** Half-day script + overnight compute.

### H3. RL self-play (D4) at scale — multi-week.
### H4. B&P&C (B2) at canonical scale — multi-week.

---

## I. Three-milestones-from-veteran (vol-121 vault concept)

The veteran researcher's three intermediate targets:
1. **471/480 matched-edges** (community 469 + 2; minimal record-break)
2. **231/258 linear placement** (CSP-depth metric, untranslated)
3. **Complete internal 14×14** (interior II=364, current best McGavin=354 — 10 mismatches to fix)

#3 is the cleanest decomposition and the same target as A1+B3 above (border + interior decomposition).

**Concept**: [[../concepts/three-milestones-from-veteran]], [[../concepts/interior-14x14-parity-feasible]].

---

## J. New inventions emerging mid-research

### J1. Double-row column-DP with beam search — status: `unbuilt` (added 2026-05-17)

**Idea.** Solve puzzle as a 2-row sliding band. State = (column index, colors of the band's top + bottom boundary at this column). DP processes columns left-to-right, choosing 2 pieces per column step. Memo over (col, top_boundary_color, bottom_boundary_color) tuples. Then sweep over band positions (rows 0-1, 1-2, ..., 14-15).

**Why different.** Row-by-row CSP captures only horizontal coupling. Column-DP captures vertical coupling AS PART OF STATE. Both axes simultaneously.

**Why hard.** Naive state = 23^32 colors — intractable. But with **beam search** (keep top-K states per column), bounded to 23 × 23 × K manageable.

**Next steps.**
1. Implement single-band column-DP on a fixed band (rows 0-1).
2. Add beam pruning to keep top-K=10000 states.
3. Sweep bands; chain solutions via shared row.
4. Compare matched-edge counts vs row-major DFS.

**EV.** Medium-high. Beam search on column-DP is a textbook approach that hasn't been applied here.

**Effort.** ~3 days.

### J2. "Reverse SAT": find a board that DOESN'T exceed score N — status: `unbuilt`

**Idea.** Encode the constraint "score ≤ N" as SAT. Add "score > 469" as the hypothesis. If UNSAT, **proves 469 is the global maximum** (mathematically). If SAT, the witness is the record.

**Why different.** All our work attacks "find a board with score ≥ N". The dual — prove no such board exists — is logically equivalent but algorithmically different.

**Next steps.**
1. Adapt `cluster_maxsat_repair` encoder for full-board SAT.
2. Add "matched edges ≥ 470" as hard constraint.
3. Solve with kissat / z3 / cadical.

**EV.** Low for finding a record (the SAT instance is huge). High for the dual proof IF some clever encoding is feasible.

**Effort.** ~1 week.

### J3. Spectral piece-graph embedding — status: `unbuilt`

**Idea.** Build a "piece-compatibility graph": nodes = pieces, edges = "could be placed adjacent on the board with some rotation". Compute the graph Laplacian's eigendecomposition. The Fiedler vector gives a natural piece ordering. Use it as a CSP variable-order heuristic.

**Why different.** All current variable orders are geometric (cell position). Spectral order is algebraic (piece compatibility).

**Next steps.**
1. Build compatibility graph (~256 nodes, ~tens of thousands of edges).
2. Compute Laplacian + Fiedler vector.
3. Use as CSP variable order in vanilla_path via --path-csv.

**EV.** Low-medium. Spectral methods rarely beat hand-tuned heuristics on this scale of CSP.

**Effort.** ~2 days.

### J4. Per-Color Lagrangian Schedule (PCLS) — status: `refuted-as-discriminator` (vol-122)

**Idea.** Combine vol-22's bound-ascent (color-priority Lagrangian multipliers on piece-uniqueness constraints) with a Blackwood-style *schedule of relaxations*, but the schedule is **per-color rather than per-side**. Each step:
1. Solve the LP relaxation of the per-color matching polytope with current multipliers λ_k.
2. Read LP shadow prices; identify the color with the **largest binding shadow price** (= the color most "blocking" further improvement).
3. Relax piece-uniqueness for that color by 1 unit (allow one duplicate of one piece-color).
4. Re-solve LP; lock the most-improved piece placement integer.
5. Repeat until enough placements lock to form a CSP seed.

**Why genuinely different from existing methods.**
- **vs vol-22 bound-ascent**: vol-22 ascends a static bound; PCLS uses LP shadow prices to *adaptively choose which color to relax*. Vol-22 collapses score on full apply; PCLS locks integers incrementally.
- **vs Blackwood schedule**: Blackwood relaxes specific edge constraints in a fixed order. PCLS relaxes piece-supply constraints, chosen by LP duality (no human-curated schedule).
- **vs cluster MIP**: PCLS produces a SEED (partial board) via LP, not a final integer solution; MIP-locality is local, PCLS is global-LP-guided.

**Concrete first step (PoC, 1-2 days).**
1. Use the existing `border_lp_ub` LP infrastructure.
2. Add λ_k multipliers on per-color piece-supply constraints (start λ=0).
3. After each LP solve, identify k* = argmax shadow_price(supply_k).
4. Add a binary lock variable for the largest fractional placement in color k*, fix it to 1.
5. Re-solve. Repeat ≤ 60 iterations (≤ border-DP scale).
6. Dump the locked placements as a CSP partial; pipe to `border_to_csp_fill`.

**Why this might work where vol-22 didn't.**
Vol-22 reaches LP score 473 but collapses on integer apply because it tries to apply ALL color relaxations at once. PCLS locks ONE integer per step, so the LP stays feasible at each step. The lock prevents the rollback that broke vol-22.

**Linked.** [[../concepts/vol-22-bound-ascent]] (if exists), [[../concepts/inv3-border-dp-seed]], [[../concepts/inv-b4-hall-color-pair-refuted]].

**EV.** Medium-high. Synthesizes vol-22's reach (LP UB 473) with vol-122 A1's locking discipline. Independent of any existing 459/469 basin → respects directive 1.

**Effort.** 1-2 days PoC; 1 week full attack.

**Result (vol-122 2026-05-17).** Built PoC v3. **PCLS supply-LP gives identical UB=480 for McGavin border AND all 5 clean-slate borders** — supply isn't the binding constraint at the per-color level. Concept: [[../concepts/vol122-pcls-poc-result]]. Refutes the supply-LP version; future PCLS must use per-cell-pair LP (vol-44 / B3).

### J5. Interior-only ALNS with cyclic border freezing — status: `unbuilt` (added 2026-05-17)

**Idea.** The 176-cell plateau finding (vol-122 A1) shows that CSP-fill from a clean-slate border saturates at the same interior count across 3 distinct borders. This is a *fixed-border interior bottleneck*, not a border-search problem. Run ALNS where the destroy operator is **constrained to the interior 14×14** and the border is **frozen** for K iterations, then unfrozen for K iterations (cyclic). Lets ALNS explore interior basins independently of border configuration.

**Why different.**
- Current ALNS basic destroys anywhere; usually destroys border cells (which then need re-repair, wasting effort).
- Interior-only freezes the border ring as a stable scaffolding; ALNS only re-arranges the 196 interior pieces.
- Cyclic unfreeze (every K=100 iter) prevents getting stuck in a single border's basin.

**Concrete first step.** Add `--freeze-border` flag to `alns_only`. Run on a CSP-filled board; compare convergence vs unfrozen baseline.

**EV.** Medium. The 176-plateau finding directly motivates this.

**Effort.** 1 day to add flag + 30-min runs to measure.

### J6. Frontier-State Memoized CSP (FSMC) — status: `built-poc-positive` (vol-122)

**Idea (user-proposed).** In CSP backtracking, many partial paths diverge
then CONVERGE to equivalent states: same placed-piece set, same frontier
color signature. A memoized search can detect convergence and skip
redundant subtree exploration.

**State key.**
- bitset of placed piece IDs
- frontier signature: tuple of (position, side, color) for every
  placed-cell side facing an unplaced cell

**Why different from existing methods.**
- Standard backtrack explores each path independently.
- DLX/Algorithm-X uses linked-list cover but doesn't memoize.
- FSMC adds CACHING — different placement ORDERS reaching the same
  PARTIAL CONFIGURATION share the rest of the search.

**Done (vol-122).** Python PoC measured convergence on 3×3 through 7×7
puzzles. Strong signal: 17–94% convergence rates, 1–9× theoretical
node savings. Concept: [[../concepts/vol122-fsmc-convergence-measured]].

**Next steps.**
1. **Rust implementation**: port the Python prototype to a high-perf
   Rust binary integrated with `solver-engine`. Estimate based on PoC:
   ~1-2 days of careful coding.
2. **Storage strategy**: Bloom filter, LRU eviction, or bounded-depth
   memoization to handle astronomical state count on canonical 16×16.
3. **Benchmark**: compare nps + nodes-to-solve vs vanilla joe_depth150_par.
4. **Integrate with score-objective**: store BEST score reached from
   each state, not just existence. Enables "skip to known-better"
   pruning for MaxScore CSP.

**EV.** High. The PoC convergence rates suggest 2-5× speedup on canonical
even with aggressive cache eviction. Combined with existing 232×
blackwood-fast (vol-106), could push search throughput far enough to
brute-force-find 469+ basins from many starting points.

**Effort.** 3-5 days.
- Day 1: Rust port of PoC, validate same convergence on small puzzles.
- Day 2: Bloom-filter + LRU cache.
- Day 3-4: Integrate with solver-engine; benchmark.
- Day 5: Apply to canonical-scale; measure nps gain.

**Concept.** [[../concepts/vol122-fsmc-convergence-measured]].
**Linked**: [[dlx-e2-implementation-status]] (ZDD is a related encoding —
both exploit state equivalence; ZDD does it via shared subDAGs at the
data-structure level, FSMC does it via cache lookups).

### J7. Hint-Free Forced-Move Analysis (HFFM) — status: `analysis-done` (vol-122)

**Idea.** For each adjacency color-pair (c1, c2), count L-shape supply
(# pieces × rotations × sides that present c1-then-c2 on adjacent piece
sides). For each piece, find color-pairs it UNIQUELY provides.

**Done (vol-122).** 92/256 pieces (36%) uniquely provide at least one
color pair. All 4 corner pieces and most edge pieces are in this set.
No supply=1 (true singleton) pairs; minimum supply = 4 = 1 piece × 4 rotations.

**Concept**: [[../concepts/vol122-hffm-forced-pieces]].

**Next steps.**
1. Adjacency-pair MIP for tighter UB (vs vol-44 per-color = 480).
2. Pair-supply CSP propagator (extends K3 CFCC to pair level).

### K10. Kuramoto coupled oscillator dynamics — status: `unbuilt` (added 2026-05-17)

**Idea.** Model 256 pieces × 4 sides as Kuramoto oscillators on a 16×16 grid. Adjacent oscillators couple with strength 1 iff their face colors match. Find sync configurations via Kuramoto dynamics (continuous-time gradient descent on the Kuramoto Hamiltonian).

**Why genuinely different.** Continuous-relaxation physics — different from discrete CSP/MIP/ALNS. The DYNAMICS may visit configurations CSP can't reach.

**Concrete first step.** Python PoC on 4×4/c4 — does the system sync to a global optimum?

**EV.** Medium-low. Continuous-relaxation usually loses information for discrete combinatorial.

**Effort.** 1 day.

### K11.1. Wave-mechanics Hamiltonian — status: `unbuilt` (added 2026-05-17)

**Idea.** Each color = a frequency ω_c. Each piece = a 4-port scattering center. Adjacent edges coupled by $J \cos(ω_{c_i} - ω_{c_j})$. Eigenmodes of the Hamiltonian on a partial board reveal "soft" directions where piece swaps lower energy.

**Concrete first step.** Build the 256×256 piece-piece compatibility Hamiltonian. Eigendecompose. Inspect lowest-eigenvalue eigenvectors for piece-swap candidates.

**Why different.** Continuous-spectral analysis of a piece-piece graph is novel for E2. (Vol-122 J3 did spectral on the COUPLING graph; here we add the energy Hamiltonian of the assigned configuration.)

**Effort.** 1 day. Spec page: [[../concepts/k11-cross-domain-brainstorm]] section 1.

**EV.** Medium. The wave-packet dynamics (vol-122 K10 cousin) is the novel hook.

### K11.2. Optical transmission channel rank — status: `unbuilt` (added 2026-05-17)

**Idea.** Treat each color as a wavelength. Matched edges transmit, mismatched edges reflect. Compute the 16×16 transmission channel matrix $T_{ij}$ between border entries. Measure its RANK and CONDITION NUMBER as a board signature.

**Why different.** Existing methods sum scalar mismatches; channel rank uses GLOBAL transmission paths. Could discriminate 458 (2 big mismatch clusters) from 459 (4 small clusters).

**Concrete first step.** Implement ray-tracing through matched-edge graph for the standing 459, vol-32 458, J1 boards. Compare channel rank. ~1h Python.

**EV.** Medium-high. Channel rank is a NEW scalar feature; if it correlates strongly with score, it's a new scoring function.

**Effort.** 1h PoC + 1 day analysis.

**Concept**: [[../concepts/k11-cross-domain-brainstorm]] section 2.

### K11.4. Information-theoretic compression scoring — status: `unbuilt` (added 2026-05-17)

**Idea.** Compute the LZ77 / arithmetic-coding compression length of a board's piece-id sequence. Hypothesis: high-score boards COMPRESS BETTER because they have more local structure.

**Why different.** Information-theoretic complexity is independent of edge-matching metric. Provides an orthogonal signal.

**Concrete first step.** 30 min Python: for each candidate board, compute LZ77 compression ratio of row-major + col-major + spiral-major piece sequences.

**EV.** Medium-low. Compression may correlate with structural rigidity but might not discriminate fine score differences.

**Effort.** 30 min - 1 day.

**Concept**: [[../concepts/k11-cross-domain-brainstorm]] section 4.

## M-series — Completely Different Models (added 2026-05-17, K12 brainstorm)

Per user directive "model the puzzle as something completely different". All UNBUILT.

### M1. Foam topology — `unbuilt` (designed)

**Idea.** Matched-edge regions = 2D bubbles. Junction angles (3+-region meetings) should obey Plateau's 120° law if board is at "equilibrium". Distance from Plateau statistics = signature.

**Concrete first step.** Identify junctions in 459/458/J1 boards, measure angles. ~1h Python.

**Concept:** [[../concepts/k12-completely-different-models]] M1.

### M2. Electrical circuit / impedance — `unbuilt`

**Idea.** Pieces = 4-terminal resistors; colors = resistance values; matched edges = wires. Total impedance of border-to-border paths = scalar signature. Kirchhoff's laws on the matched-edge graph give global constraints.

**Why different.** Circuit theory gives EFFECTIVE-RESISTANCE between any two nodes — a scalar that integrates ALL paths, not just shortest.

**Concrete first step.** Compute pairwise effective resistance (graph theory) between 4 corner cells for various boards. Should correlate with board "rigidity".

**EV.** Medium. Effective resistance is a well-studied graph invariant; likely correlates with score.

**Effort.** 1 day Python.

### M3. DNA sequence alignment — `unbuilt`

**Idea.** 22 colors → 22 extended bases. Adjacent pieces "base-pair". Apply Smith-Waterman to row sequences. Sequence alignment scores might predict matchability.

**Caveat.** May collapse to J1 column-DP (already explored). Worth a 1h PoC to see if it's genuinely different.

**EV.** Low-medium.

**Effort.** 1h.

### M4. Crystallographic lattice gas — `unbuilt`

**Idea.** Pieces = molecules with 4 binding sites; colors = binding energies. Lattice gas Hamiltonian. Find ground state via Wang-Landau MCMC.

**Why different.** Wang-Landau samples the ENTIRE energy landscape uniformly — different from ALNS which biases toward greedy descent.

**Effort.** 2 days.

### M5. Cellular automaton — `wont-do`

Collapses to ALNS-like behavior.

### M6. Music chord progression — `unbuilt`

**Idea.** Pieces = chords (4 notes = 4 colors). Adjacent edges = chord transitions. Music-theoretic VOICE LEADING constraints might identify "playable" boards.

**Why different.** Music theory has well-developed notions of CONSONANCE distance metric (Tenney's harmonic distance, Euler's gradus suavitatis). These metrics might give a new scoring function.

**Concrete first step.** Define a color-pair "consonance" matrix from the canonical E2 piece-graph. Map to musical intervals via similarity. See if "consonant" boards = high-score.

**EV.** Low-medium. Stretching the analogy.

**Effort.** 1 day.

### M7. Matrix factorization / recommender system — partial-overlap with vol-122 J3

**Idea.** 256×256 piece-piece compatibility matrix → SVD. Latent factors reveal piece "preferences".

**Done partially.** Vol-122 J3 did Laplacian spectral decomposition. SVD with different normalization (collaborative filtering style) is a different angle.

**Effort.** 1 day.

### M8. Knot / braid theory — `unbuilt`

**Idea.** Each piece-side permutation under rotation = a permutation group element. Adjacent pieces' compatible-rotation set = braid generators. Find boards whose "braid invariant" is trivial.

**Why different.** Knot invariants (Jones polynomial, Alexander polynomial) are GLOBAL topological invariants — completely different from local color-matching.

**Concrete first step.** For a complete board, compute the boundary braid (= 60-edge sequence of permutations applied). Compute its Burau matrix or Jones polynomial.

**EV.** Speculative. May not connect to matched-edge score at all.

**Effort.** 2-3 days.

### M9. Protein folding (HP-model) — `unbuilt`

**Idea.** Pieces = amino acids; colors = hydrophobicity classes. Find folding (= board arrangement) minimizing exposed hydrophobic edges.

**EV.** Low (HP-model is over-simplified).

**Effort.** 1 day.

### M10. Stock market / time series — `unbuilt`

**Idea.** Each row/column = a time series of "prices" (colors). Matched = stable; mismatched = price jump. ARIMA model on row sequences.

**Concrete first step.** Treat row 0-15 of 459 record as a time series. Fit ARIMA, compute residuals. Compare to J1 boards.

**EV.** Low. ARIMA on discrete categorical sequences is odd.

**Effort.** 1h.

### M11. Chemistry / molecular bonds — `wont-do`

Too similar to M2/M4.

### M12. Linguistics / parsing — `unbuilt`

**Idea.** Piece edges as production rules. Board = parse tree. Find boards satisfying a context-free grammar.

**EV.** Low. CFG parsing on grids has been done in image recognition but doesn't seem to add to puzzle solving.

**Effort.** 2 days.

### M13. Holographic encoding / compressed sensing — `unbuilt` (per user reminder)

**Idea.** A hologram encodes 3D info via 2D interference. Apply compressed sensing / Fourier reconstruction to a partial board's mismatch map. Predict full board structure.

**Why different.** Compressed sensing recovers sparse signals from few measurements. The mismatch map is sparse (21 mismatches in 480 edges = 4.4% density). Inverse-FFT reconstruction might INTERPOLATE missing colors.

**Concrete first step.** For the 459 board, compute the 2D FFT of the mismatch indicator. Try to predict surrounding-cell mismatches from a subset.

**EV.** Medium. Compressed sensing is well-studied; if it works, it's a NEW partial-to-complete predictor.

**Effort.** 1-2 days.

### M14. Topological data analysis (persistent homology) — `unbuilt`

**Idea.** Compute persistent homology of the matched-edge graph. β_0 (connected components) and β_1 (cycles) at different "filtration thresholds" give a barcode signature.

**Why different.** Persistent homology is GLOBAL but multi-scale. May reveal hierarchical basin structure.

**Concrete first step.** Use ripser or giotto-tda on the matched-edge graphs of 459/458/J1.

**EV.** Medium. TDA is novel for E2 but technically demanding.

**Effort.** 2-3 days.

### M15. Statistical mechanics replica trick — `unbuilt`

**Idea.** Compute the partition function $Z = \sum_{\text{configs}} e^{-\beta E}$ via replica trick. Replica symmetry breaking would indicate glassy basins.

**Why different.** Replica trick has been used for analyzing spin glasses; if E2 is glassy, RS breaking would explain why search saturates.

**EV.** Medium. Theoretical heavy lift but novel.

**Effort.** 3-5 days.

### M16. Information bottleneck / variational inference — `unbuilt`

**Idea.** Train an information-bottleneck model that compresses partial boards into latent codes, then decodes to predict completions. Identify the "bottleneck dimensions" that encode score.

**EV.** Medium-high. IB is a powerful tool for finding minimal sufficient statistics.

**Effort.** 3-5 days (ML setup heavy).

### BUG-FIX: ALNS basic produces duplicate pieces — `unbuilt` (2026-05-17 evening)

**Evidence**: vol-122 evening run of `alns_only --ops basic --seed 7` on `RECORD_TIE_457_vol34_t3_t01_seed1.json` reported `matched=459/480` but `verify_board` rejected with `duplicates: [180, 248]` and `uniq=254/256`. The ALNS final scoring counts edges WITHOUT verifying piece-uniqueness, so duplicate placements yield inflated scores.

**Reproduction**: `./target/release/alns_only --cp-board output/vol-34/t3_signal/RECORD_TIE_457_vol34_t3_t01_seed1.json --alns-budget-ms 1800000 --seed 7 --ops basic`. Output board has piece 180 at both pos 197 and pos 210 (canonical hint position), piece 248 at both pos 72 and pos 221.

**Why important**: the bug INVALIDATES claims of new records produced by ALNS basic. Any "458+" board from this preset must be `verify_board`-checked before claiming. Furthermore, the bug might be silently inflating scores in many previous runs (vol-60, vol-110, etc.).

**Likely root cause**: one of the `basic` ALNS operators (random_region / worst_window / conflict_driven / mwpm_defect_pair / worst_band) places a piece during repair without marking it used in the placement bitset, leaving a stale copy at the original location.

**Concrete first step**:
1. Instrument `alns_only` to assert piece-uniqueness after every operator's commit.
2. Reproduce the bug with a small budget (~30s) and capture which operator caused the duplication.
3. Fix the operator's place-and-remove invariant.

**EV**: HIGH. Bug correctness affects the entire ALNS-basic result history. Likely several "false records" lurking.

**Effort**: 1-2 days (instrument → repro → fix → regression test).

## W-series — Web-roam 2026-05-17 (cross-domain harvest from forums + scientific literature)

Origin: vol-122 session-resume web roam after N-series dead-end. User
directive: "roam around online... see what exists in the world we could
bring in there". Concept page: [[../concepts/web-roam-2026-05-17]].

### W1. Hyperoptimized approximate tensor-network contraction — `unbuilt` (Tier S)

**Source.** Gray & Chan PRX 14, 011009 (2024); arXiv:2407.21287 for
rugged spin glasses.

**Idea.** Represent puzzle's Boltzmann distribution as a 2D PEPS-style
tensor network. Approximately contract with fixed bond-dimension χ to
recover per-site marginals. Sequentially fix highest-marginal piece-rotation
per cell. Cost: N² for 2D short-range, independent of landscape ruggedness.

**Why different.** Boundary-MPS (vol-13 refuted) was 1D *for counting*.
W1 is 2D PEPS *for per-site marginals* — different operational primitive.
Doesn't traverse landscape. The 2024 paper benchmarks on 48×48 spin glass
= comparable scale to E2's 16×16.

**Concrete first step.** Use `cotengra` + `opt_einsum`. Encode 6×6 E2 with
edges-as-variables (~24 edges) and validity tensors at each cell. χ=16
marginals → fix piece-rotation per cell. Compare against `solver-engine`
joe profile on same 6×6 puzzle. **1 week PoC**, then scale to 8×8, 12×12,
16×16.

**EV.** **Very high.** Continuous-but-rigorous; physics-validated on
rugged landscapes; untested at canonical E2 scale.

**Effort.** 1 week PoC, ~3 weeks full canonical attack.

### W2. Survey Propagation (Mézard-Zecchina) — `unbuilt` (Tier S)

**Source.** Braunstein-Mézard-Zecchina 2002/2005; Marino-Parisi-Ricci-Tersenghi
*Nature Communications* 7, 12996 (2016) backtracking-SP.

**Idea.** Generalized BP that passes *surveys over message clusters*. Designed
for k-SAT close to SAT/UNSAT threshold where BP cycles. Backtracking-SP reaches
solutions "in regions unreachable by any other algorithm" per 2016 paper.

**Why different.** Vol-11/12 BP gave 18.84% reduction (not strong alone).
SP captures *cluster structure* that BP cannot. E2 has documented cluster
structure (vols 18-22, 65, 99-115).

**Concrete first step.** Adapt our `eternity2-sat-encoder` output → feed
to Braunstein-Mézard public SP code (or `thibsej/SurveyPropagation`). 6×6
E2 first, then 8×8, then canonical.

**EV.** **High.** Physics-validated; never tried on E2.

**Effort.** ~1 week.

### W3. Kovalsky-Glasner-Basri Vandermonde-LP — `unbuilt` (Tier A)

**Source.** Kovalsky, Glasner, Basri. *SIAM J. Imaging Sci.* 2015
(arXiv:1409.5957). Vault has the citation (vol-2/3, [[publishability]])
but never built.

**Idea.** Exponential change of variables $T_i = e^{t_i}$. Color constraints
become polynomial equations. Vandermonde relaxation: replace permutation
matrix with doubly-stochastic (Birkhoff-von Neumann polytope). Iterative LP:
$P^{n+1} = \arg\max \langle P^n, P \rangle$ subject to linear constraints +
doubly-stochastic.

**Why different.** Vol-44 cell-pair LP is *generic*. Kovalsky uses *algebraic*
Vandermonde structure with polynomial closure. Paper validated on 6×6 (2 iter)
and 8×8 (6 iter); never scaled to 16×16.

**Concrete first step.** Julia or Python+scipy.linprog PoC on 4×4. Scale
if iteration count is reasonable.

**EV.** Medium-high. Different relaxation could give different partials.

**Effort.** 1 week PoC, 2 weeks full.

### W4. LKH-style adaptive-cardinality k-opt chains — `unbuilt` (Tier A)

**Source.** Helsgaun, "General k-opt submoves for LKH." Math. Prog. Comp.
(2009). State-of-the-art TSP heuristic.

**Idea.** Adaptive-K edge-chain: start a swap, evaluate gain, conditionally
extend chain or close it. Chains routinely reach K=10-20 by chaining gains.

**Why different.** Our ALNS operators are all *fixed-cardinality* destroys
(1-rot, 2-swap, k-band). Vol-20, 65, 99 show E2 basins are operator-locked
under K≤5. LKH-chains break this barrier by *gain-chaining* — never tried.

**Concrete first step.** Implement `lkh_chain_e2` operator in
`crates/localsearch/src/`. Add to ALNS basic ops bundle. Run on standing
458 strict-canonical + 459 record basins.

**EV.** Medium-high. Adaptive-cardinality moves are a *missing axis* in
our operator portfolio.

**Effort.** 2-3 days.

### W5. GFlowNet-amortized ant-colony sampling — `unbuilt` (Tier B)

**Source.** Kim et al. AISTATS 2025 (GFACS).

**Idea.** Train GFlowNet to amortize prior over solution space; iterate
with ACO-style search.

**Why different.** Generative rather than search-based. Diverse-by-construction.

**Concrete first step.** Define MDP: state = partial board, action = place
piece. Train GFlowNet via flow-matching loss on synthetic 6×6/8×8.

**EV.** Medium. Speculative.

**Effort.** 2-3 weeks (ML training).

### W6. Discrete score-based diffusion (SEDD / DeFoG) — `unbuilt` (Tier B)

**Source.** Lou et al. SEDD ICML 2024 (arXiv:2310.16834); DeFoG 2025.

**Idea.** Discrete diffusion with score-entropy loss. Generate boards via
reverse diffusion.

**Why different.** Generative paradigm; 1024-state discrete labels.

**EV.** Low-medium. Generative fidelity untested at E2 state space.

**Effort.** 3-4 weeks.

### W7. Frozen-variable / backbone fraction by basin — `unbuilt` (Tier B)

**Source.** Achlioptas-Coja-Oghlan 2007-2012 (frozen variables in random CSPs);
Molloy 2012 (freezing threshold k-coloring).

**Idea.** For each cell in a basin (e.g., 459-basin), count distinct
piece-rotation values across all basin boards. Cells with 1 value = frozen
(true backbone); 4+ values = liquid. Map freezing fraction by region.

**Why different.** Vol-17 found 17/18-cell backbone, vol-20 corrected to
5 hint cells. Have we measured *freezing structure* of the 459-class basin?
Different from operator-lock at K≤5.

**Concrete first step.** Use existing 459/458 basin board dump. Python
script: for each cell pos in [0..255], count distinct (piece_id, rotation)
across basin boards. Plot heatmap. ~1-2 days.

**EV.** Medium. New structural signature.

**Effort.** 1-2 days.

### W8. Tropical-geometry framework realisation counting — `unbuilt` (Tier C)

**Source.** arXiv:2502.10255 (Feb 2025).

**Idea.** Tropical-geometry deletion-contraction on a bigraph to count
realisations of a rigid framework. A solved board = a framework.

**Why different.** Closed-form upper bound on the *number of distinct
full-score boards*. Could give a counting result instead of just bound on
score.

**EV.** Low-medium. Speculative.

**Effort.** 1-2 weeks.

---

### Open slot for next invention

- (placeholder)

---

## Priority recommendation for the autonomous month

Budgeting at **5 days per invention** per user directive. Total ≈ 6 inventions over 30 days, with compute interleaved.

**Days 1-5 — INVENTION A1 (border-DP) full pipeline.** Goal: enumerate ≥10K piece-unique 60-matched borders, group by interior-color profile, ALNS each profile representative × 4 seeds × 30min, build B3 (per-border interior LP-UB) and rank. Outcome target: identify the top 10 borders by ALNS-final-score and by interior LP-UB.

**Days 6-10 — INVENTION A4 (DLX exact-cover).** Build minimal DLX in Rust on 4×4/6×6 (day 6), scale to 8×8/12×12 (day 7-8), adapt for MAX-matched (day 9), canonical 16×16 run (day 10). Outcome: nps comparison vs vanilla_fast 125M pp/s and node-count vs CSP backtracking.

**Days 11-15 — INVENTION A5 (bidirectional search).** Implement corners-in + center-out CSP frontiers meeting at 14-cell ring. Test on 8×8 (day 11-12), scale to 16×16 (day 13-14), measure depth reduction (day 15).

**Days 16-20 — INVENTION B-cluster (B1+B3+B4): tighter UB attacks.** Per-row LP-UB (day 16), per-border interior LP-UB on A1 outputs (day 17-18), color-pair Hall-condition (day 19), publish a vault concept "tightened UB landscape" (day 20).

**Days 21-25 — INVENTION C1 (GNN message-passing) prototype.** Train on synthetic 6×6/8×8 (day 21-23), adapt for canonical 16×16 (day 24-25). May fail; that's still data.

**Days 26-30 — INVENTION D4 (RL self-play) PPO start.** Multi-week project; days 26-30 cover only setup + first training runs.

H2 (cross-machine SOTA at scale) runs **continuously in background** through the whole month, consuming idle compute. Math/proof work (F2) interleaved as primary compute waits.

If any week's invention finds a ≥460 board: STOP scheduled plan, focus deep on that direction.

---

## Linked

- [[CURRENT-VOL]]
- [[BACKLOG]]
- [[../sessions/vol-121]] (what was tried and didn't work)
- [[../sessions/vol-122]] (current)
- [[../concepts/inv3-border-dp-seed]] (A1 detail)
- [[../concepts/vol121-all-locked]] (exhaustively proven locked)
- [[../concepts/three-milestones-from-veteran]] (veteran hints)
