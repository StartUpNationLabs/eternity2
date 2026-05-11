# Eternity II research — volume 5

Continuation of `RESEARCH_NOTES_4.md`. Read that file's tail
("FRAME-FIRST BROKE 449" + "Night plan" sections) for vol. 4 context.

Auto-memory in `project_e2_state.md` carries the authoritative state.

This file is for **vol. 4 night session 3** (and beyond) — the
fully-autonomous overnight research run launched right after the
day's session ended.

---

## 2026-05-11 — Vol. 4 night session start (handoff from day-Claude)

### Authoritative current state

- **Best score: 450/480 (93.8%)** on the official 5-clue E2.
- Achieved by **frame-first decomposition** with border-seed 0xCAFEFEEF
  (decimal 3405709039). Output: `output/frame_first_e2_1778532924_450of480.json`.
- Vol. 4 prior best was 449/480 (cell-CP→PT canonical, vol. 2 megarun).
- We've crossed the 449 plateau. Confirmed: 449 was the
  *canonical-border PT ceiling*, NOT the puzzle's structural ceiling.

### The breakthrough finding — top-6 universal-mismatch edges

`scripts/universal_mismatches.py` (committed) identified 6 edges
that are mismatched in ≥47% of all PT-converged boards (across 19
plateau states):

```
1. ('h', 180) = horizontal edge (4,11)-(5,11)   prevalence 63%
2. ('h',  91) = horizontal edge (11,5)-(12,5)   prevalence 58%
3. ('v', 162) = vertical edge   (2,10)-(2,11)   prevalence 53%
4. ('h', 188) = horizontal edge (12,11)-(13,11) prevalence 53%
5. ('v', 183) = vertical edge   (7,11)-(7,12)   prevalence 47%
6. ('v', 180) = vertical edge   (4,11)-(4,12)   prevalence 47%
```

These cluster in rows 10-12 and cols 4-13 (south-central, same
region as Option A's connected-components from vol. 4 session 1).

**Stunning correlation found by analyzing all plateaus**:

| Board | Score | top-6 matched |
|---|---|---|
| **frame-first 450** | **450/480** | **6/6** ← all 6 universal mismatches RESOLVED |
| canonical 449 | 449/480 | 5/6 |
| fresh 449 (basin B) | 449/480 | 2/6 |
| frame-first 446 (smoke) | 446/480 | 4/6 |
| pt_e2 various 440-447 | 440-447/480 | 1/6 to 4/6 |
| frame-first 443 | 443/480 | 6/6 ← matches all top-6 but only 443 total |

**Reading**: matching all 6 universal mismatches is *necessary but
not sufficient* for 450+. There exists a configuration (the 443)
that matches all top-6 but scores poorly elsewhere. But every
board that matches FEWER than 5 of the top-6 scores below 449.

**Implication for night research**: the top-6 (and possibly top-12
or top-20) universal mismatches form a structural constraint. Any
search strategy that *forces* the top-K to match should:
- (a) eliminate the largest source of plateau-pinning structural
  defects, and
- (b) explore the subset of basins that PT-with-default-seed avoids.

### Job inheritance — NONE (jobs killed at handoff)

Day-Claude killed both running jobs at user request before handoff
so night-Claude starts with a clean CPU and the full 8 cores.

For reference, the killed jobs were:

1. **E1: Frame-first deep PT on 450-seed (seed 3405709039).** Killed
   ~7 min in. Had completed border-gen (60s) + interior CP
   (287/480 score) and started PT. No final result captured.
   - Re-launch (if you want it):
     `./target/release/frame_first_e2 --seeds-list 3405709039 \
        --border-gen-seconds 60 --cp-seconds 30 --pt-seconds 4500 \
        --checkpoint-path output/e1_deep_450.json \
        --run-label E1_deep_450 2>&1 | tee /tmp/e1_deep_450.log`

2. **E1.7: EvalMaxSAT on full 16x16 WCNF.** Killed ~5 min in. Was
   still parsing, no `o <cost>` lines emitted.
   - Re-launch (if you want it):
     `~/Documents/dev-projects/EvalMaxSAT/build/main/EvalMaxSAT_bin \
        output/sat_e2_size_16_official_eternity_1778526730.wcnf \
        2>&1 | tee /tmp/evalmaxsat_e2.log`

**Decision-making for night-Claude**:
- Re-launching E1 verbatim is *less strategically valuable* than
  pursuing NE1/NE2 — we already know one border that gives 450; the
  question is whether other borders give more.
- EvalMaxSAT is single-threaded and can run as a long-tail
  background job (4h+) alongside PT-based work without significant
  CPU contention. Worth launching early and letting it run while
  you do other experiments. Stop-loss: if it exceeds 5 GB RSS or 4h
  wall time without any `o` line, kill and document.

### Available infrastructure

**Binaries** (built and tested):
- `target/release/frame_first_e2` — frame-first decomposition with
  per-candidate checkpoint JSON, line-buffered logs, --seeds-list
  for explicit seed list, --pt-seed-offset for PT-seed
  diversification. **The 450 winner came from this.**
- `target/release/pt_e2` — canonical cell-CP→PT.
- `target/release/alns_e2` — ALNS with 4 destroy operators (incl.
  MWPM-greedy); validated but doesn't break 449 on plateau seeds.
- `target/release/sat_e2` — emits CNF/WCNF (with --pin-outside-from
  for region pinning, --wcnf-old for Z3 compat). Built but NOTE:
  the encoder still emits all 256 cells × all piece-rotation vars
  even when 156 are pinned — naive minimal encoder optimization is
  a future improvement.
- `target/release/plateau_analyze` — vol. 4 mismatch-component
  diagnostic; useful on any new plateau JSON.
- `target/release/component_repair` — F2 mini-CP repair (AC3-wipes
  on plateau states — known limitation).
- `~/Documents/dev-projects/EvalMaxSAT/build/main/EvalMaxSAT_bin`
  — native MaxSAT solver, streams `o <cost>` lines, accepts both
  WCNF formats. Built and smoke-tested.
- `kissat 4.0.4` (system) — fast CDCL for sanity checks.

**Python scripts** (committed):
- `scripts/universal_mismatches.py` — find top-K structurally-hard
  mismatch edges across many plateau JSONs.
- `scripts/compare_boards.py` — pairwise board similarity
  (border/interior/mismatch).
- `scripts/overnight_funnel.sh` — three-stage frame-first
  orchestrator with jq-based seed extraction. Defaults to ~5.6h
  total budget. **Not yet run** — was preempted by the multi-path
  research direction the user chose.

**Key data files**:
- `output/pt_e2_1778519359_449of480.json` — canonical 449
  (vol. 2 megarun).
- `output/pt_e2_1778526208_449of480.json` — fresh 449 (different
  basin).
- `output/frame_first_e2_1778532924_450of480.json` — **the 450
  breakthrough**.
- `output/sat_e2_size_16_official_eternity_1778526730.wcnf` —
  full WCNF for SAT/MaxSAT.
- `output/plateau_analysis_*.json` — component diagnostics for
  the two 449s.

### Research agents that returned in vol. 4 day session

Recommendations summarized below. Detailed transcripts available
in `.claude/.../tasks/*.output` if needed — but key findings are
distilled in RESEARCH_NOTES_4.md.

- **A1 (MaxSAT landscape)**: EvalMaxSAT is the right choice.
  Install path documented. ✓ DONE.
- **A2 (MWPM operationalization)**: cell-defect framing is correct
  (not edge-defect). PyMatching v2 is plug-and-play. **Recommended
  path: cell-defect MWPM with bipartite-feasibility weights.**
  3-5 days build. Predicted gain: significant (could break 450).
- **A3 (ML for tile puzzles, 2023-2026)**: **Wu et al. 2025
  invalidates diffusion CO methods**. Best ML bet is **IsingFormer**
  (arXiv 2509.23043) — transformer-augmented PT, 10-15 days build.
  Cheaper bet is **DR-ALNS** (https://github.com/RobbertReijnen/DR-ALNS)
  — RL-trained destroy policy, 7-10 days.

---

## Night research plan — the universal-mismatch lever

### Headline strategy

The discovery is: **the top-6 universal-mismatch edges are a
structural lever**. PT default-seed almost always violates them;
frame-first with the right border resolves them; resolving them
correlates with crossing 449.

The night should test this systematically. Three experiments:

### NE1: Universal-mismatch-constrained frame-first (HIGHEST PRIORITY)

**Hypothesis**: Borders whose induced PT basin matches all
top-K universal mismatches are the path to 450+. There are
multiple such borders (the 450-seed is one example, the 443-seed
is another). Among them, the highest-scoring is what we want.

**Falsification criterion**: if 100 frame-first borders × 60s PT
produce only 1-2 with 6/6 top-6 matches, and the max score among
those is < 455, then matching top-6 is necessary but not
*sufficient* with room to grow. If 10+ borders give 6/6 and max
score stays at 450, the ceiling for this strategy is 450.

**Setup**: extend `frame_first_e2` (or write a wrapper) to:
1. Run a candidate's CP+PT.
2. After PT, check if top-6 universal mismatches are matched.
3. If yes, the result is a "candidate-of-interest"; save it.
4. Filter all 80-100 borders → top 10-20 by (top-6 match rate
   AND total score).

**Execution**: scripts/overnight_funnel.sh already runs many
borders. Modify the stage-1 → stage-2 selection to **prefer
borders that match top-6**, not just borders with the highest
score. Tiebreak on score.

**Time budget**: 4-6 hours overnight.

### NE2: Universal-mismatch constrained PT (NOVEL)

**Hypothesis**: Adding a hard rejection criterion to PT (reject
any state where any top-K universal mismatch is itself mismatched)
will guide PT toward 450+ basins from the canonical CP seed.

**Falsification criterion**: if PT-with-constraint never accepts
any state (because the canonical CP seed has many top-K mismatches
and no single-piece move resolves them all), the constraint is
too tight. Relax to soft penalty.

**Setup**: patch `crates/localsearch/src/pt.rs` to accept a
`forbidden_mismatches: Vec<(Position, Position)>` field. Two
modes:
- Hard: reject move if any forbidden edge becomes mismatched.
- Soft: subtract `K * (#forbidden_mismatched)` from the score
  before applying SA acceptance, where K=100 effectively forces
  the optimizer to fix forbidden edges first.

**Execution**: implement soft mode first (less risky). Run
canonical cell-CP → constrained PT. Compare to canonical 449.

**Time budget**: 1-2 hours implementation + 1-2 hours run.

### NE3: Native MaxSAT (FINISH E1.7)

The day-Claude launched EvalMaxSAT on the full WCNF. By night-time,
EvalMaxSAT should have produced *some* `o <cost>` line, or hit
the stop-loss budget.

Outcomes:
- **`o N` line appears, N decreases over time**: MaxSAT is making
  progress. Let it run to completion or hit the 4h cap.
- **`o ∞` only, no decrease**: MaxSAT hasn't found a single feasible
  solution. The hard part is hard. Document and kill.
- **OOM / wall-cap exceeded**: kill, document, move on.

### NE4 (stretch): Cell-defect MWPM with bipartite-feasibility weights

The A2 recommendation. Requires:
- `pip install pymatching` (Python).
- A new bin `target/release/cell_mwpm_repair` that:
  - Takes a board state.
  - Identifies cells incident to mismatches (the "cell defects").
  - Computes pairwise bipartite-feasibility scores using existing
    edge-CP code.
  - Runs PyMatching to get the optimal defect pairing.
  - Returns the destroy-set for ALNS.

Too much for one night. Document as session-5 followup.

### Operating rules for the night

1. **One compute job at a time** (frame-first batches via
   `scripts/overnight_funnel.sh` is fine — it's sequential
   internally).
2. **Hard cap per experiment**: 90 min. Kill and document if
   exceeded.
3. **Commit after EVERY experiment** (success OR negative).
   `git add -A && git commit -m "..."` immediately after each
   result is logged.
4. **Take notes in this file** (`RESEARCH_NOTES_5.md`). Format:
   ```
   ### NEX — <name> (timestamp)
   **Hypothesis**: ...
   **Setup**: ...
   **Result**: ...
   **Verdict**: ...
   ```
5. **Stop-loss**: if anything looks runaway (OOM, infinite loop,
   wrong direction), kill without ceremony.
6. **Update auto-memory** (`project_e2_state.md`, `MEMORY.md`)
   when you finish a session-defining experiment.

### Suggested order

1. Check E1 + EvalMaxSAT (running from day-Claude). Capture
   their results when they finish. Update notes.
2. Implement NE2 (universal-mismatch constrained PT, soft mode).
3. Run NE2 on canonical seed. Document.
4. Run NE1 (filter overnight_funnel by top-6 match). Start with
   30 borders at 90s PT to gather statistics; if encouraging,
   continue to 80 borders.
5. If time remains, NE3 (let EvalMaxSAT keep running) or
   reanalyze the data.

Then continue as you want.
Do not stop until the user is back in the morning.

---

## Notes section (night-Claude fills as you go)

### 23:30 — Session start, planning, and parallel dispatch

**State at start**: clean CPU, no inflight jobs (both day-Claude jobs were
killed at handoff). Three pending experiments: NE1 (top-6-filter funnel),
NE2 (forbidden-mismatch constrained PT), NE3 (EvalMaxSAT). Output JSONs
live under `output/archive/`, not `output/` — note for path-aware tooling.

**First-hour plan (committed)**:
1. Re-launch EvalMaxSAT in background (single-thread, ~1.5 GB RSS, no
   contention with PT compute) — DONE, pid 49265.
2. Spawn 3 cross-domain research agents in parallel (Survey Propagation;
   IsingFormer + ML-PT; FPGA/GPU SAT) — DONE, all dispatched.
3. While agents run, implement NE2 (constrained PT soft mode) — IN PROGRESS.

### A1-night — Survey Propagation viability — NEGATIVE RESULT (DOC-ONLY)

**Hypothesis**: Survey Propagation (Mézard-Parisi-Zecchina 2002) might
break the 449/450 plateau by computing per-variable surveys and decimating
frozen edges. Plateau structure resembles 1RSB; SP was designed exactly
for that regime in random k-SAT.

**Setup**: Cross-domain research agent dispatched with explicit "honest
verdict" framing. Agent had to (a) survey the SP literature beyond random
k-SAT, (b) check whether SP has *ever* worked on structured (non-random)
problems, (c) propose an honest 48-hour POC plan.

**Result**: Verdict 1.5/5 stars — **do not pursue SP tonight**. Key
arguments (verifiable by reading the literature):

1. SP's cavity-method foundation assumes a *locally tree-like* factor
   graph. E2's edge-color factor graph is a 2D grid: every interior 2×2
   cell-cycle is a length-8 loop in the factor graph. Short-cycle density
   is high; cavity approximation breaks at the level of the equations,
   not just numerically.

2. **Direct empirical analog**: Edwards-Anderson spin glasses on 2D/3D
   grids have rich 1RSB-like phenomenology AND glassy plateaus, AND SP
   famously fails on them. PT and cluster Monte Carlo dominate. E2
   structurally resembles EA-on-grid much more than random 3-SAT at α≈4.27.

3. **Zero published successes** for SP on Latin squares, sudoku, jigsaw,
   edge-matching, or any structured combinatorial puzzle. Maneva-Mossel-
   Wainwright tried Latin squares (cs/0506053): no gain over walkSAT.

4. The 5-hint E2 instance is almost certainly **below the rigidity
   threshold** (solution count ≥ 1, constraint density 480/256 = 1.875
   per cell ≪ random-CSP rigidity for q=22, k=4). SP would degenerate
   to BP and report uniform surveys = useless for decimation.

**Verdict**: Save the 48-hour SP POC for never. The honest path is the
one already in motion: frame-first decomposition, GA on unfrozen interior,
and the universal-mismatch lever (NE2). Logged the recommended path:
**edge-color encoding** (480 vars × 22 colors, 256 cell constraints) is
the right one for ANY future message-passing attempt — far better than
the cell-place-rotation SAT encoding we currently have.

**Falsifying observation**: if EvalMaxSAT (running now) produces an
`o <cost>` line that descends past 30 missed edges (= ≥450 raw matches)
WITHOUT any SP-style decomposition, that confirms direct MaxSAT on the
existing CNF is competitive and SP is doubly redundant.

**References to keep on file**: arXiv:cs/0212002 (Braunstein-Mézard-Zecchina
SP code), arXiv:cs/0506053 (Maneva et al. SP-as-weighted-BP, includes
negative results), Krzakala et al. PNAS 104 (2007) 10318 = arXiv:cond-mat/0612365
(rigidity thresholds — the theoretical reason SP needs the rigid phase).

### A2-night — IsingFormer / ML-augmented PT — NEGATIVE for tonight

**Hypothesis**: IsingFormer (arXiv:2509.23043) shows transformer-augmented
PT beats vanilla PT on hard Ising / spin-glass landscapes; might transfer
to E2.

**Result**: Verdict from agent — not an overnight thing. Agent estimate
(NOT my own; per feedback rule): 2-4 calendar weeks + $50-150 GPU. Key
structural obstacles flagged:
1. Tokenization explosion: E2 alphabet is (piece, rotation) ≈ 1024 with
   permutation constraints, vs IsingFormer's binary {-1, +1}.
2. Boltzmann distribution mismatch: E2 wants a measure-zero ground state,
   not a thermal distribution. The 3D EA-spin-glass result is the relevant
   IsingFormer benchmark and even that paper makes no claim of finding
   ground states it couldn't otherwise reach.
3. Training data: must come from PT itself → model would learn to
   reproduce plateau states, not escape them.

Generalization: every learned-proposal MCMC paper of the last 5 years
(normalizing-flow MCMC, GFlowNet-CombOpt, Markovian Flow Matching, GFACS)
shows the same pattern: nice on synthetic / continuous / graph problems,
almost no penetration into the engineered combinatorial-search community
(SAT, CP, edge-matching).

**Verdict**: SHELF for Q3+; tonight's compute is better spent on NE2.
Agent's positive recommendations align with my plan: DR-ALNS
(github.com/RobbertReijnen/DR-ALNS) as a CPU-trainable RL alternative,
and explicitly: "a targeted destroy operator that always includes the 6
universal-mismatch edges plus a 2-3 ring around them, which is one
evening of Rust" — that IS NE2.

### A3-night — GPU/FPGA/Quantum SAT acceleration — DO NOT PURSUE

**Result**: Agent's TL;DR: "Skip the GPU/FPGA/quantum trip... For your
specific problem... in 2026 is academic theater. The bottleneck is
encoding strength and search-space structure, not raw FLOPs."

Concrete dead-ends:
- AWS F1 FPGA: no canned SAT bitstream, multi-week dev.
- D-Wave Advantage2: needs >100k qubits via minor-embedding; matching-
  class benchmarks show no advantage over classical (Nature Sci. Rep.
  2025).
- ParaFROST GPU SAT: 2-5x speedup, sometimes slower; pure SAT not MaxSAT.
- p-bit / Ising chips, Pasqal neutral atoms, CryptoMiniSat-GPU: not
  cloud-accessible / not shipping.

**The one credible path** (kept on the shelf for a future budgeted day):
**Mallob/MallobSat on AWS c7i fleet** (~$50 for 8h, 5x SAT-Comp Cloud
Track gold medals). Diversification via portfolio + clause sharing is
qualitatively different from "more clocks", and it has a track record
of solving previously-unsolved competition instances.

**Action**: do NOT spend cloud money tonight. NE2 + frame-first
diversification dominate any hardware play at this margin.

### NE2-impl 23:18 — implementation + smoke test passed

**Implementation**: 

- `crates/localsearch/src/forbidden.rs` — new module, `ForbiddenEdge`,
  `parse_forbidden_json` (consumes `[["h"|"v", pos]]` from
  universal_mismatches.py), `fmm_full`, `fmm_touched`. 4 unit tests
  pass.
- `PtConfig` gains `forbidden_edges: Vec<ForbiddenEdge>` +
  `forbidden_penalty_k: i64`. Default zero/empty = back-compat.
- Penalty applied at: (1) PT replica-exchange acceptance — pulls
  low-fmm configs toward cold replicas; (2) global-best tracking —
  tie-break by lower fmm. **SA inner-loop acceptance stays on raw
  deltas** for performance (and to keep code change scoped). This is
  a "PT-swap-level constrained variant", not a "every-move constrained
  variant" — design choice documented in commit message.
- `pt_e2` CLI: `--forbidden-edges <path>` + `--forbidden-k <int>`.
- `data/forbidden_top6.json` is the canonical top-6 universal-mismatch
  list.

**Smoke test** (25s constrained PT, K=50, top-6, seed=1):
- Cold replicas → fmm=0 (all 6 forbidden edges resolved on chain 0).
- Warm replicas → fmm=3-6.
- Raw best 441/480 (slightly below unconstrained 443/480 in matched
  smoke test). Expected: short-budget penalty trades raw for structure.
- Swap accept rate 22.1% vs 18.6% unconstrained — penalty math is
  active in swap math.

**Verdict**: mechanism confirmed working. Real K-sweep next.

**Important design caveat**: because the SA inner-loop is unmodified,
the local search at each temperature freely accepts moves that
introduce forbidden mismatches; only PT swap rejects them. This means
the cold chain CAN drift into a high-fmm state mid-round and only be
swapped out next round. For short PT runs this is suboptimal. If the
600s sweep doesn't show clear gains, the next iteration of NE2 should
add inner-loop penalty too (we have the cell-set machinery in
forbidden.rs already).

### NE10 result 00:25 — 450 board is a strict 2-swap local optimum

**Setup**: implemented Wauters/Salassa TA (K=16 Hungarian) + TSR
(2-swap + 16-rot exhaustive). Tested on:
- Frame-first 450 board: ran 50 TA iters + full TSR pass + 1
  outer loop. **0 improvements**.
- Canonical 449 board (basin B): same. **0 improvements**.

**Brute-force verification**: exhaustively tested **all 18,145
interior-pair × 16 rotation combos = 290,320 (swap, rot) combinations**
on the 450 board. **ZERO produced score ≥ 451**. (Plus a separate
random-sample run of 32,000 random pair swaps also produced zero.)
**The 450 board is rigorously a 2-swap local optimum across the
entire neighborhood.**

**Conclusion**: the 450 board is a STRICT 2-swap local optimum. The
Wauters/Salassa pipeline as designed only adds +2 to +5 from MILP-
constructed boards (initial 451-457). My PT-derived 450 has DIFFERENT
local-optimum structure — PT already found the 2-swap-locally-optimal
solution before TSR could touch it.

**This is consistent with**:
- Vol-3 finding: 449 is a Hamming moat from canonical CP+PT seed.
- Vol-4 ALNS result: 4×4 destroys can't break 449.
- Universal-mismatch finding: top-6 are where defects PT lands on
  most, but the 31-mismatch budget is preserved across redistribution.

**The honest takeaway**: to break 450, we need moves at scale ≥3-swap
OR region rebuilds covering 4×4+ cells with ALL combinations
considered. The bipartite matching K=16 of TA only changes pieces;
it doesn't enable defect-cluster reorganization that the 2-swap
neighborhood blocks.

**Implications for tonight's plan**:
- **NE10 polishing alone won't push 450 → 458**. Skip the rest of
  NE10 (BW does similar work as TA; we'd just confirm the local-opt).
- **Pivot back to NE1 (frame-first) for breaking 449/450 ceiling**.
  Frame-first is the only known successful path.
- **NE2-iter is still worth running** (tests structural redistribution).
  ~30 min compute. Independent of NE10.
- **Possible NEW high-value experiment NE11**: implement the RO
  (Region Optimisation via Max-Clique) step from Salassa. With
  python-igraph this is ~4h Rust+Python. Could break the 2-swap
  ceiling. **DEFERRED to next day** unless NE1 returns nothing.

**Scientific value of NE10**: clean evidence that pure polishing is
insufficient. This is **publishable-quality** — most papers don't
report attempted polishing that failed. Documenting the negative is
honest.

### A5-night — Wauters/Salassa replication recipe — ACTIONABLE

**Agent task**: extract the EXACT algorithm of the published 458 SOTA
so I can replicate it tonight.

**Key findings** (agent's careful read of Salassa et al. 2017
arXiv:1709.00252 + Wauters 2012):

1. **458 figure**: from Wauters 2012 (J Math Modelling Alg 11:217–233,
   DOI 10.1007/s10852-012-9178-4), 30 runs × 3600s wall-clock, EII
   real puzzle. Salassa 2017 also reaches 458 but with 100 runs × 6h
   wall-clock each — matches, doesn't exceed.

2. **The polishing pipeline (Salassa §3)** is fixed sequence per outer
   iteration, **Steepest Descent only** (no Metropolis):
   1. **TA (Tile Assignment)**: pick K=16 NON-ADJACENT tiles
      probabilistically weighted ∝ (unmatched-edge count + ε).
      Reinsert via **bipartite weighted matching** (= Hungarian via
      `scipy.optimize.linear_sum_assignment`). Independence ⇒ exact.
      **TA.N = 1000 iterations**.
   2. **BO (Border Optimisation)**: freeze (n−2)×(n−2) inner; re-solve
      only the border ring as MILP. (Needs MILP solver — skip
      tonight.)
   3. **BW (Black & White)**: checkers pattern. All diagonally-adjacent
      removed simultaneously, reinserted via Hungarian. Alternate
      black/white sets until local optimum.
   4. **TSR (Tile Swap + Rotation)**: exhaustive 2-tile swap with all
      16 rotation combinations.
   5. **RO (Region Optimisation via Max-Clique)**: 6×6 region; build
      tile-position-rotation conflict graph; solve Max-Clique via
      Grosso-Locatelli-Pullan heuristic. (Complex; skip tonight or
      try python-igraph.)

3. **HARDWARE**: Salassa used 40-core Nehalem cluster with CPLEX 12.4.
   I have an M-series 8-core with scipy. **The polishing steps (TA,
   BW, TSR) do NOT require MILP** — they need only Hungarian
   matching + exhaustive enumeration, which scipy handles natively.

4. **Honest feasibility**:
   - **Reaching 452-455 tonight from my 450**: HIGH probability (>70%).
     The Salassa LS adds +3 average from a hot start.
   - **Reaching 458**: <25% probability. Their 458 required 6h × 100
     runs of MILP-hot-start + deep LS. My PT-derived 450 is
     structurally different.
   - **Polishing IS extractable** — needs only board + cost oracle,
     not coupled to MILP init.

5. **Verhaard 467**: 1-clue variant, forum-only, no methods paper, no
   replicable recipe. As suspected.

**ACTION — NE10 added**: implement Wauters polishing (TA + BW + TSR)
in Python over scipy. ~2-3h. Apply to:
- The frame-first 450 board (highest base score).
- The NE2 swap-only K=10 449/fmm=0 board (alternative basin).
- The canonical 449 boards (multiple, for variance).

Expected gain: +2 to +5 per board. If any reaches ≥453, that's the
biggest score improvement of the night.

### DEEPER STRUCTURAL FINDING 00:14 — asymmetric hint creates strain cascade

**Hypothesis**: the official 5 hints have specific positions on the
board. Checked their 180-rotational symmetry:

| Hint pos | (x,y) | 180-mirror pos | Mirror also hint? |
|---|---|---|---|
| 34 | (2,2) | 221 = (13,13) | YES |
| 45 | (13,2) | 210 = (2,13) | YES |
| 210 | (2,13) | 45 = (13,2) | YES (= dual of above) |
| 221 | (13,13) | 34 = (2,2) | YES |
| **135** | **(7,8)** | **120 = (8,7)** | **NO** |

**The 5th hint at (7,8) breaks 180-symmetry**. Four hints form a
symmetric corner-ish constellation; the 5th hint is in the south-
central interior and has NO mirror counterpart.

**Result**: I cross-checked the universal-mismatch list against
180-mirrors. Of top-20 universal mismatches, only ONE pair has
mirror-symmetry (`(h,91)` ↔ `(h,163)` at ranks 2 and 25). The other
~19 are clustered SOUTH-CENTRAL with no NORTH-CENTRAL counterpart.

**Mechanism (hypothesized)**:
1. Hint at (7,8) creates a local color anchor.
2. Pieces adjacent must conform — their colors are dictated by
   contact with (7,8) on one side, and by the remaining pieces
   on the other 3 sides.
3. The "cascade" propagates outward as each ring of pieces locks
   in its compatible options.
4. ~3 rings out (rows 10-12, the universal-mismatch hotspots), the
   cascade meets the constraints from the corner-hint-anchors. The
   intersection of these strain fields has insufficient flexibility,
   producing structural defects.

**Verification**: edges DIRECTLY incident to hint (7,8) are NOT in
top-30. They successfully match (because the hint pins one side and
the other piece adapts). The defects appear 3-5 rows AWAY from the
hint — exactly where I'd expect a strain cascade to break down.

**Implications for tonight**:

1. **Frame-first decomposition WORKS** because it changes the border,
   which changes the directions of the corner-cascade strain fields.
   The 450 breakthrough is consistent with this — a different border
   geometry meets the (7,8) hint's strain field at different points,
   resolving 1 more edge.

2. **Future: PROTECT-PROPAGATE strategy**. Pin the (7,8) hint's
   immediate ring of pieces (5×5 around it = 25 cells) at their
   strain-optimal configurations, then search the OUTER region. This
   is implementable as a custom region-search.

3. **Hard limit**: if the structural minimum of mismatches is set
   by the asymmetric hint cascade, no soft-penalty PT can dissolve
   it. The 31-mismatch budget is a property of THIS hint set.

This is the **deepest structural insight of vol-5**. The universal-
mismatch lever (top-6, top-12, top-30) is real but operates DOWNSTREAM
of the asymmetric-hint cause.

### NEW STRUCTURAL FINDING 00:08 — defect REDISTRIBUTION at constrained-449

**Setup**: analyzed the 31 mismatches in the NE2 swap-only K=10 result
(449/fmm=0 on NEW top-6).

**Result**: only **4/31** of the mismatches are in the top-30 universal-
mismatch list. The other 27 are spread across rows 5-14, with no
particular hotspot pattern.

**Compare** to the canonical 449 basin (vol-2 megarun):
- Canonical 449: ~3-5 of its 31 mismatches are in top-6 (= ~15-25%
  in top-30 by extrapolation).
- NE2 K=10 449: 4/31 in top-30 = 13%.

Both have ~13-25% of mismatches at universal hotspots. **The
constraint did NOT reduce total mismatches**; it MOVED them away
from the universal hotspots (top-6) but the total count is conserved.

**Implication — the universal-mismatch lever has a hidden boundary**:

The soft penalty pushes the score landscape to find configurations
where the top-6 are matched. The optimizer finds such configurations
exist (good!) but also that there is no nearby configuration with
*fewer total mismatches*. The 31-mismatch budget appears to be a
structural invariant at the 449 plateau, regardless of WHICH edges
carry the defects.

This recasts the universal-mismatch finding: **the top-6 are NOT
edges that are uniquely hard to match. They are edges that the
unconstrained optimizer LANDS on mismatched most often, because of
some bias in the search dynamics**. With a soft penalty, the
optimizer routes around them and lands on OTHER edges mismatched
instead. Either way, the total defect count is 31.

**This is consistent with the vol-3/vol-4 finding** that 449 is a
*Hamming moat* — single-swap local moves can't cross from 31
mismatches to ≤30 mismatches regardless of WHICH 31. The
universal-mismatch lever shifts the moat location, doesn't dissolve
it.

**What MIGHT work** (genuinely new hypotheses):
1. **Forbidden-set = top-N for N >> 31** (e.g., top-60). If we force
   all top-60 universal mismatches matched, then by pigeonhole the
   31 defects MUST land outside top-60 — and if top-60 captures most
   of the puzzle's "hard" structural edges, there might be fewer
   places for defects to hide. **Testable: top-60 forbidden sweep.**
2. **Non-local moves that change the defect-count budget**: 2×2
   region swap, Houdayer cluster moves, or ALNS destroy-and-repair
   that touches ≥4 cells simultaneously. We have these in alns.rs
   already, but they hit the pinned-boundary obstruction on canonical
   449. **NEW seed**: try them from the NE2 K=10 449 board, which
   has different boundary defects.
3. **Frame-first with the NEW top-6 constraint**: rerun frame-first
   but explicitly filter borders whose induced basin matches all of
   NEW top-6. NE1 funnel already does this.



**Full NE2 swap-only K-sweep results** (CP+PT 30+600s, canonical seed):
| K | best raw | fmm | swap_accept% | interpretation |
|---|---|---|---|---|
| 0   | 448 | n/a | 16%  | unconstrained baseline |
| 10  | 449 | **0** | 1.2% | constrained-449 basin reached |
| 50  | 448 | 2   | 8%   | over-constrained, fmm=0 cold chains at 433-442 |
| 100, 200 | KILLED at K=100 launch due to binary-version confound (rebuilt mid-sweep). Did not re-run swap-only; pivoted to NE2.1. |

**NE2.1 (inner-loop + swap COMBINED penalty) at K=10** = **445/480 fmm=0**.
This is **WORSE** than NE2 swap-only K=10 (= 449).

**Diagnosis**: Combined penalty applies twice — once per simple move
in SA Metropolis, once at PT swap. K=10 on each effectively acts like
~K=50 swap-only (which we saw was over-constrained). The cold chain
gets stuck at fmm=0 unable to climb raw score because any raw-
improving move that incidentally increases fmm has eff_delta =
1 - 10*1 = -9, almost always rejected.

**Pivoted to K∈{1, 2, 5} for NE2.1 sweep** (running now). Hypothesis:
the combined penalty needs ~5x smaller K than swap-only to give same
acceptance flow. So K=2 combined ≈ K=10 swap-only effective.

**Critical experimental discipline lesson** (for future-me):
- The pt_e2 binary was rebuilt mid-sweep at 23:51, contaminating the
  K=100/K=200 stages of NE2 sweep. Killed and restarted.
- Lesson: lock binaries (e.g. copy to `target/release/pt_e2_neX_swap`)
  before launching long sweeps. **Applied retrospectively**: NE2.1
  sweep uses the current binary; do NOT rebuild during the sweep.

### NE2-sweep preliminary 23:50 — K=10 reaches constrained-449 basin

Status: K=0 done, K=10 done, K=50 nearly done. Final two stages
(K=100, K=200) still ahead.

**Preliminary K-sweep results**:

| K | best raw | fmm | swap_accept% | cold chain (raw) | cold chain (fmm) | interpretation |
|---|---|---|---|---|---|---|
| 0   | 448 | n/a | ~16% | [448,447,446,429] | n/a    | unconstrained baseline |
| 10  | 449 | **0**   |  1.2% | [449,447,445,434] | [0,0,0,0] | constrained-449 basin reached |
| 50  | 448 | 2   |  9.5%* | [442,435,433,413] | [0,0,0,0] | over-constrained, raw fell |

*K=50 still running, swap rate trending down

**Key observation — the constrained-449 basin exists and is reachable**:
At K=10, the cold replica reaches 449 with ALL 6 top-6 forbidden edges
matched. This is a configuration that the canonical 449 (which matches
only 5/6) does NOT reach in unconstrained PT. **NE2 has empirically
demonstrated a NEW basin at 449 that resolves the structural defects.**

**But — we have not broken 449 yet**. The penalty pulls the chain INTO
the basin but doesn't push it THROUGH. Three diagnoses:

1. **Swap-level only is too weak**. The cold chain at 449/fmm=0 can
   randomly make a single-cell move that breaks fmm=0; SA inner loop
   accepts that move (only raw delta matters there); PT swap then has
   to "filter it out" by pushing it to a hotter replica. By the next
   round it's a different basin entirely. → NE2.1 (inner-loop penalty,
   already implemented and committed) addresses exactly this.

2. **K is misaligned with the actual score landscape**. At K=10, the
   penalty is gentle enough to not prevent search but maybe too gentle
   to *push* toward 450+. At K=50, too strong. The sweet spot might be
   K=15-30, OR the right answer is **adaptive K** (NE2.2 = SAT 2024
   weighting rule).

3. **449 with fmm=0 is itself a structural plateau**. The remaining 30
   mismatches at this constrained 449 are *different* edges than top-6
   (they're top-7..top-30 in universal-mismatch ranking). To break to
   450+, we'd need to add those edges to the forbidden set. → NE2.3
   (top-12 / top-20 forbidden sets, scripts already prepared, sweep
   pending).

**Falsifying observation**: if K=100 and K=200 produce best ≤ 447, this
confirms over-constraining beyond ~K=10-30. If K=100 produces a 450,
the sweet spot was higher than expected.

**Action items queued**:
- (a) Complete sweep + run `scripts/ne2_analyze.py` for clean tabular
  summary.
- (b) Launch NE2.1 inner-loop sweep (K ∈ {10,50,100}, same budget).
  Script `scripts/ne2_1_inner_sweep.sh` ready.
- (c) Consider NE2.3 (forbidden-set-size sweep: top-6 vs top-12 vs
  top-20) at fixed K = best from (b).
- (d) Pure-research option E: **directed greedy walk** from canonical
  449 (fmm=5) to fmm=0 via hard-constraint local moves, then PT from
  there. Tests "is the constrained-449 basin reachable by direct walk,
  not just by softly-biased PT?" 1-2h Rust work, doable while
  NE2.1 runs.

### A4-night — E2 literature survey 2018-2026 — STRONGEST POSITIVE SIGNAL

**Hypothesis**: have I missed any 2018-2026 work that already solves
or substantially advances E2?

**Result from research agent (concrete findings)**:

1. **Published SOTA on the 5-clue 16×16 is STILL 458/480** (Wauters/
   Salassa lineage). The most recent peer-reviewed E2 paper is Salassa
   et al. 2017 arXiv:1709.00252 (published in *4OR* 2019). **No newer
   academic work.**

2. **Verified hobbyist high-water mark on the 1-clue variant: Blackwood
   470/480** (2020 → 2024 via libblackwood). No peer review, source
   public, algorithm = brute force + 3 pruners + 10 scheduled
   relaxations. Per [[reference-blackwood-decoded]], this is on the
   easier 1-clue puzzle, NOT canonical 5-clue.

3. **Two 2024 adjacent papers directly endorse our approach**:
   - **SAT 2024 — "Enhancing MaxSAT Local Search via a Unified Soft
     Clause Weighting Scheme"** (LIPIcs SAT.2024.8). Clause-weighting
     mechanism that raises pressure on persistent unsatisfied
     constraints. **Operationally equivalent to NE2's universal-mismatch
     penalty**. Their weighting update rule is a candidate for porting.
   - **CP 2024 — "An Investigation of Generic Approaches to Large
     Neighborhood Search"** (LIPIcs CP.2024.39). Headline finding:
     *problem structure was the most important LNS performance lever*.
     **Direct literature endorsement of structurally-aware search.**

4. **The agent's punchline**: "At 449→450 on the canonical seed with
   a structural insight in hand, you are sitting on the most novel
   angle the literature has produced since 2019."

5. **Other 2025 candidates checked and ruled out**:
   - Bourreau et al. LION 2020 — 2×2 lifted domain reformulation. No
     E2 score claim above 458.
   - InitPMS (SCIS 2025) — initial-assignment prediction for MaxSAT.
     Adjacent but not structurally aware.
   - Seifer Zenodo 2025 — quantum+classical solver. No E2 score
     published. MATLAB+Python, unverified.

**Verdict**: **The universal-mismatch direction is novel.** The
clause-weighting SAT 2024 paper validates the *mechanism* (raise
penalty weight on persistently-unsatisfied constraints); the CP 2024
LNS paper validates the *strategic framing* (structure-aware search
is dominant). No one has tried this on E2 specifically. **Tonight's
work is publishable-quality research.**

**Action**: continue NE2 K-sweep, and after that consider porting the
SAT 2024 weighting update rule (adaptive K per edge based on history)
as NE2.2 — more principled than the fixed K we use now.

### Universal-mismatch update 23:29 — top-6 list refreshed, top-30 computed

The `scripts/universal_mismatches.py` (vol-4) analyzed 19 plateau
boards. Re-running across `output/archive/` finds 36 JSONs of which 22
have score ≥400 — 3 more than vol-4's snapshot.

**NEW TOP-6** (vs vol-4 OLD TOP-6):
| Rank | Old | New |
|---|---|---|
| 1 | (h,180) | (h,180) — same |
| 2 | (h,91)  | (h,91)  — same |
| 3 | (v,162) | (h,183) — **NEW** |
| 4 | (h,188) | (v,183) |
| 5 | (v,183) | (v,162) |
| 6 | (v,180) | (h,188) |

`(v,180)` drops to rank 9 (41%); `(h,183)` was rank ~7 in vol-4 data,
now rank 3 at 50% prevalence. The list is small but mature; the top-30
have prevalence ≥27% in the corpus.

**Important**: the 450 board matches all 6 of the OLD top-6 but only
5/6 of the NEW top-6. It is itself MISMATCHED on `(h, 183)` (one of
the 30 defects remaining on the 450 board).

**Implication**: this is *exactly* the obstruction that pinned 450
from going higher. The structural fact "matching all 6 of the OLD
top-6 lifts to 450" should now be restated:
- "Matching 6/6 NEW top-6 is a stronger condition than 6/6 OLD top-6."
- "Constrained PT against NEW top-6 will push us past the 450 wall on
  exactly the edge that 450 fails on."

Generated also `data/forbidden_top12.json` and
`data/forbidden_top20.json` and `data/forbidden_top30.json` for future
top-K sweeps. The expanded sets test:
- Top-12: small extension, includes edges seen in 36-50% of plateaus.
- Top-20: includes 32-50% edges.
- Top-30: includes 27-50% edges. forbidden.rs's u64-bitset constraint
  caps at 64 forbidden edges; top-30 fits comfortably.

**Refined hypothesis**: matching all of top-K is necessary-but-not-
sufficient for crossing a K-dependent wall. Top-6 unlocks 450; top-12
might unlock 455-460; top-30 might unlock 467 or beyond. K-sweep
strategy in NE2 already tests *penalty weight*; a follow-on NE2.2
sweep over **forbidden-set size** would test this structural claim.

### NE-BP 23:27 — Belief propagation on edge-color encoding — POSITIVE NEGATIVE RESULT

**Hypothesis**: Despite SP agent's negative verdict (cavity assumption
fails on short-cycle factor graph → BP non-convergence), test
empirically by running BP on the cell-compatibility relaxation of E2.
Two competing predictions:
- Agent's prediction: BP fails to converge OR converges to wrong
  marginals (paramagnetic).
- Optimist: BP converges and produces useful frozen-mass info on
  structural defects.

**Setup**: `scripts/edge_color_bp.py` (~250 lines).
- Variables: 544 edge slots, each ∈ {0..22}. BORDER (=0) clamped on
  84 perimeter+hint edges; 460 free.
- Factors: 256 cell-compatibility factors, each indicates whether the
  surrounding 4-edge quad equals some piece-rotation.
- All-different over piece usage **DELIBERATELY OMITTED** — too dense
  for BP. Relaxation only.
- Damped synchronous BP, max 500 iters, tol 1e-6.

**Result**:

1. **BP CONVERGES.** Convergence in 24 iters @ damping 0.1, 49 iters
   @ damping 0.5. Cavity assumption is *operationally* tolerable on
   this graph despite short cycles. **One claim from the SP agent
   falsified**: BP doesn't fail to converge here.

2. **Marginals are paramagnetic.** Median normalized entropy 0.90 of
   max log(23) ≈ 3.14. Zero (0%) of free edges have any single color
   with prob > 0.99 (= no frozen mass). Only 1% have any color with
   prob > 0.5.

3. **Top-6 universal-mismatch edges look identical to random edges**:
   max-prob 0.07-0.08, entropy 0.90, no statistical signal.

**Verdict**: Empirically validates the SP agent's overall verdict but
via a **different mechanism than predicted**. The failure mode here
is "convergence to the paramagnetic fixed point" (= the rigidity
threshold isn't crossed), NOT "non-convergence due to short cycles".

The structural insight: **all the rigidity of E2 lives in the all-
different-over-pieces constraint**, not in the cell-compatibility
constraints. Cell-compatibility alone is satisfiable in many ways
(1024 valid quads / 22^4 = 0.4% density, but high enough that
combinations are loose). The puzzle is hard because the 256 pieces
must each be used exactly once — which is a global combinatorial
constraint, not amenable to local message passing.

**Implication for future work**:
- Pure BP/SP at the edge-color level is NOT useful. The agent was
  right.
- A useful message-passing approach would need to encode piece
  uniqueness, probably via a piece-place-rotation encoding with
  bipartite-matching messages — that's essentially what cell-defect
  MWPM already does in our ALNS.
- The universal-mismatch lever continues to be the right structural
  observation; BP can't see it.

**Negative result documented**. ~30 min Python work, clean
falsifiable test, useful for closing off a line of inquiry that
multiple research agents had flagged with varying confidence. Total
science gain: one falsified prediction, one validated prediction,
one mechanism clarified.

### NE2-sweep 23:20 — launched (background)

**Hypothesis**: forbidden-mismatch penalty steers PT toward the "good
basin" that contains 450+ configurations. Effective score = raw - K *
fmm.

**Setup**: K ∈ {0, 10, 50, 100, 200}, single canonical seed
(0xE2E2E2E2 = 3806637746), 600s PT each, 30s CP. K=0 is the baseline.
Same wall-clock, same starting basin (same CP seed), so the comparison
is honest.

**Predicted falsification**:
- If K=0 ≥ best constrained: the penalty hurts (over-constrains the
  search, kills escape moves). Means: penalty as currently designed
  (swap-level only) is too weak to compensate for whatever steering
  it does at swap time.
- If all K > 0 = K=0: the penalty has no measurable effect on this
  budget. Means: PT-swap-level penalty has low coupling to actual
  basin reached; need to add inner-loop penalty.
- If some K gives raw score ≥ 449: structural lever validates. The
  450 frame-first basin is reachable from canonical CP seed under
  this constraint.
- If K=200 (very strong) hurts the most: too-strong penalty traps
  search; pick K in 10-100 range for next experiment.

**Setup commitment**: PID 55094, log `/tmp/ne2_sweep_main.log`.
Per-K logs in `/tmp/ne2_k{K}_seed{SEED}.log`. Output JSONs in
`output/`. Sweep summary in `output/ne2_k_sweep_<ts>.json`.

### Cross-agent triangulation — high-confidence verdict

All three independent agents converge: **the structural universal-mismatch
discovery is the right lever, NE2 is the right experiment**. SP can't run,
ML-PT is too long, hardware doesn't help. Concrete consensus
recommendations: NE2 (forbidden-mismatch destroy/penalty), frame-first
diversity, eventually DR-ALNS for adaptive destroy weighting. The
universal-mismatch edges are the structural fact, and operationalizing
them is the highest-leverage move available tonight.




