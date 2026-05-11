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

### Job inheritance from day-Claude

Two background jobs are running. They write to disk and don't depend
on the Claude process. They'll continue regardless of session.

1. **E1: Frame-first deep PT on 450-seed.** Single border (seed
   3405709039), 75 min PT, on top of the 286 interior CP partial.
   - Log: `/tmp/e1_deep_450.log`
   - Checkpoint: `output/e1_deep_450.json`
   - Status when handed off: 4 min elapsed, 287 interior-CP done,
     PT started. ~71 min remaining.
   - **Question this answers**: does the 450 basin yield to longer
     PT (455+? 458+?) or is 450 the ceiling for this specific border?

2. **E1.7: EvalMaxSAT on full 16x16 WCNF.** No time limit set.
   - Log: `/tmp/evalmaxsat_e2.log`
   - WCNF input: `output/sat_e2_size_16_official_eternity_1778526730.wcnf`
     (108.8 MB, 171,112 vars, 5.8M hard clauses, 480 soft).
   - Status when handed off: 1.5 min elapsed, parsing/early CDCL.
     RSS ~2 GB. No `o <cost>` lines yet.
   - **Question this answers**: what's the maximum #matched-edges
     achievable under the official 5 hints?
   - **Stop-loss for night-Claude**: if EvalMaxSAT exceeds ~5 GB
     RSS or 4h wall time without producing any `o` line, kill it
     and document.

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

### What NOT to do tonight

- ❌ Build IsingFormer / DR-ALNS / NMWPM-style GNN (all are 1-2
  week builds).
- ❌ Run another 12-border frame-first batch with no top-6
  filter — we have that data, it confirms the ceiling is
  ~450 at 180s PT.
- ❌ Re-attempt mini-CP repair on plateau states — vol. 4 F2
  established this AC3-wipes universally.
- ❌ Try diffusion CO methods — Wu et al. 2025 says they don't
  work.

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

---

## Notes section (night-Claude fills as you go)

(Empty — first entry will be your first experiment result.)
