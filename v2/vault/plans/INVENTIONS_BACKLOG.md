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
