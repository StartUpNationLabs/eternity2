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




