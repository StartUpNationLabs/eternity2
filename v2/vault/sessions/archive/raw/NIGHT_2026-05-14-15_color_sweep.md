# Night session 2026-05-14 → 2026-05-15 — Vanilla DFS color-complexity sweep + ALNS

**Source**: parallel agent session (Raphaël + Claude, night).
**Archived for future work**: 2026-05-15 by main RL agent (vol-48 in flight).

This is the **raw report** from the parallel agent. Stored here for future
reference; the main agent's ongoing work (vol-44..vol-48: LP UB analysis,
basin landscape, lifted-LP attempt, RL self-play) was not interrupted.

---

# Night session — vanilla DFS, ALNS, and color-complexity sweep

**Date**: 2026-05-14 evening → 2026-05-15 morning
**Author**: agent session (Raphaël + Claude)
**Status**: in progress (multi-seed sweep pending)

## Session context — what happened during the night

This report covers a single overnight session on the official Eternity II
puzzle (`size_16_official_eternity`, 16×16, 22 colors). The session went
through three distinct phases: (1) baseline vanilla DFS measurement,
(2) ALNS post-fill experiments, (3) color-complexity sweep on synthesized
puzzles. The color sweep (the headline experiment) is the focus of this
report; phases 1–2 are summarized first for context.

### Phase 1 — Vanilla DFS baseline

**Goal**: establish honest single-thread and multi-core throughput, and a
canonical score baseline for vanilla DFS (no propagation, no value-order
heuristics).

| Run | Setup | Result |
|-----|-------|--------|
| Single-core, 60s, row-major | `vanilla_fastest --threads 1` | 121 M pp/s · canonical **392/480** |
| 10-core, 60s, row-major | `vanilla_fastest --threads 10` | 686 M pp/s (5.66× scaling) · 392/480 |
| Single-core 10h continuous, row-major | `vanilla_fastest --threads 1 --budget-ms 36000000` | Reached depth **216** before user killed it; never beat 392/480 |
| 9-core × 30 min restarts, **border-first** | `vanilla_path --path-mode border-first --threads 9` | Run 1: canonical 387 · Run 2: **403/480** · Run 3: 397 |
| 9-core × 5 min restarts, **border-first** | same | Run 1: 387/480 (rest killed before finishing) |

**Key findings**:

- **Path order matters more than restart count.** Border-first (boundary
  placed first, interior last) beat row-major by ~+11 canonical edges in the
  same wall-clock budget. Multiple restarts on row-major never broke 392.
- **Continuous-tree DFS plateaus around depth 216 / score ~392.** The
  10-hour single-thread grind never improved past that.
- **Border-first 30-min run 2 hit canonical 403/480** — the best vanilla
  result of the night.

### Phase 2 — ALNS post-fill experiments

**Goal**: take the best vanilla partials and apply ALNS local search to
polish toward the vol-32 record of 458/480.

#### 2a — Score-counter bug discovered

Mid-session we hit a critical issue. `vanilla_path` and `vanilla_fastest`
were reporting an **inflated score** `matched_total = matched_internal +
matched_border` against a `/480` denominator, where `matched_border` counts
border-of-board self-edges (max 64) that **are not part of the canonical E2
score**. Examples:

- Border-first run 2 reported `467/480` but canonical is `403/480`.
- The implied "+9 over vol-32 record of 458" was an artifact, not real.

**Fix shipped**: both binaries now report `score=N/480 (canonical;
internal pair-matches)` plus a separate `border_self=N/64` diagnostic. The
legacy inflated number is preserved as `inflated_legacy=` for backward
compatibility. Filed as BACKLOG item `unified-edge-score-counter`.

After the fix, the honest scoreboard from this night:

| Source | Canonical / 480 |
|---|---|
| Row-major vanilla, multi-restart × 29 runs | 392 (every run identical) |
| Border-first vanilla, run 1 (5 min) | 387 |
| Border-first vanilla, run 2 (30 min) | **403** |
| Border-first vanilla, run 3 (30 min) | 397 |

#### 2b — Initial ALNS test (mega ops)

403/480 input + `alns_only --ops mega --seed 1 --alns-budget-ms 300000`:
ALNS climbed 403 → **435/480**, rebuilt 89 of 226 placed cells (39%).
Operators: `mega_band`, `worst_column_band`, `random_scatter` — aggressive
destroy that scorches whole stripes.

#### 2c — Minimal-ALNS test

Same 403 input, 5 min, `--ops minimal` (small destroy footprints).
Result: 403 → **452/480** in 5 minutes. +17 over `mega`.
Trajectory: 403 → 412 → 426 → 444 → 449 → 450 → 452. All operators
100% accepted (SA still hot).

#### 2d — Trim-and-restart DFS attempts (failed)

User proposed: pin 226 good cells from 403 as forced hints, re-DFS the
residual. Built `--start-from board.json --trim-rows N`. Result:
ALL trim values died at depth ~205 within milliseconds.

**Diagnosis**: 403 partial is **structurally infeasible** to complete.
Pinning 160-192 cells leaves no valid assignment for the rest — Joe
McGavin's prune-restart pattern.

#### 2e — ALNS sweep (8 inputs × 8 seeds × 15 min)

20 jobs across vanilla partials (387/392×5/397/403) × seeds 1..8:

| Score | Count | Inputs |
|------|-------|--------|
| **454** | 3 | seed=4 on three 392 inputs |
| 453 | 4 | seeds 2/7 on same three |
| 452 | 6 | seeds 5/6/8 |
| 451 | 6 | seeds 1/3 |
| 450 | 1 | seed=6 |

**Seed dominates input**: seed=4 wins on 3 different inputs. **No seed
broke 454.** Session high: 454/480 (4 short of vol-32 458).

#### 2f — Focused 6-core ALNS variations (pending)

`winning5`/`basic`/`full` ops, seeds 4/42, 30 min — results pending when
phase 3 started.

### Phase 3 — Color-complexity sweep on synthesized puzzles

#### Method

Generated 16×16 puzzles at C ∈ {6, 7, 8, 9, 10, 11, 12} via
`eternity2-generator`. Each puzzle has a guaranteed 480 solution.
Ran `vanilla_fastest --threads 1 --budget-ms 60000 --solve`.

#### Seed-1 results

| Colors | Best Depth | Best Score / 480 | Solved? |
|:------:|:----------:|:----------------:|:-------:|
|   6    |     248    |      464         |   no    |
|   7    |     248    |      464         |   no    |
|   8    |     241    |      450         |   no    |
|   9    |     238    |      445         |   no    |
|  10    |     236    |      441         |   no    |
|  11    |     235    |      439         |   no    |
|  12    |     234    |      437         |   no    |
| **22 (E2)** |  216  |    ~392          |   no    |

**Throughput at C=7**: 95.4% of placements at depth 220-239. The DFS
reaches depth 239 trivially but chews at d=240-255 trying to close
the last 16 cells.

#### Multi-seed (3 seeds × 7 color counts)

| Colors | Seed 1 | Seed 2 | Seed 3 | Mean | Spread |
|:------:|:------:|:------:|:------:|:----:|:------:|
|   6    |  464   |  387   |  460   | 437.0 |  **77**  |
|   7    |  464   |  456   |  462   | 460.7 |    8     |
|   8    |  452   |  449   |  261   | 387.3 |  **191** |
|   9    |  445   |  447   |  447   | 446.3 |    2     |
|  10    |  441   |  441   |  441   | 441.0 |    **0** |
|  11    |  439   |  437   |  435   | 437.0 |    4     |
|  12    |  437   |  431   |  431   | 433.0 |    6     |

#### Key findings (revised)

**R1. C=6 is NOT uniformly easy.** Seed 2 at C=6 scored 387/480 —
*harder* than official E2. The specific tiling matters more than C at C≤7.

**R2. C=7 is consistently easier than E2.** 460.7 ± 8 across seeds.
Genuinely the easier-than-E2 regime.

**R3. C=8 has a pathological seed.** C=8 seed=3 scored 261/480, depth 143.
Worst spread (191 edges). C=8 is the **danger zone**: enough color
variety to be hard but not seed-stable.

**R4. C=9..12 is the stable regime.** Spread ≤ 6. Curve ~3-4 edges per
added color.

**R5. The easy→hard inflection is C=7→C=8.** Coupling between distant
cells becomes meaningful around C=8.

#### Interpretations

**I1. Difficulty ≠ color count at the easy end**: below C=8, the specific
puzzle instance matters more than C. A "C=6 puzzle" is a distribution that
can include extremely easy AND surprisingly hard instances.

**I2. Official E2 may be a BENIGN C=22 instance**: if C=6 ranges 387–464
and C=22 lands at 392, the official E2 is likely a relatively-easy
C=22 instance. Worst-case C=22 could be much harder.

**I3. "Even C=7 doesn't solve in 60s"**: C=7 partially solves (reaches
~461/480 reliably) but does not CLOSE. The wall is at the *end* of the
tree (last 15-25 cells), same failure mode as E2.

**I4. C=8 seed=3 is a useful adversarial test instance** for engine
robustness.

## Open questions left by the night session

- **Q1**: Does C=6 solve in 5 minutes (vs 60s)? Cheap to test.
- **Q2**: Does the **propagator-based engine** trivially solve C=6/7
  at 60s? If yes, clean validation of propagator value. If no, deeper
  engine issue.
- **Q3**: How does C=8 seed=3's adversarial puzzle behave under the
  full engine?
- **Q4**: Finer sweep around C=7→C=8 to localize the difficulty cliff.

## Files

- Generated puzzles: `data/puzzles/synth/size_16_c{6..12}_seed{1,2,3}.csv`
- Seed-1 logs: `runs/color_sweep/c{6..12}.log`
- Multi-seed logs: `runs/color_sweep_multiseed/c{C}_seed{S}.log`

---

## What the main agent (vol-48 in flight) can learn from this

1. **Score-counter bug** — the parallel session found a real bug in
   `vanilla_path` and `vanilla_fastest` reporting `matched_internal +
   matched_border` as `/480`. **The fix was shipped during the night.**
   Verify the fix in the next git pull; ensure verify_records.sh validates
   against the corrected counter.

2. **Border-first beats row-major** in vanilla DFS by ~11 edges — consistent
   with vol-14's "scan-order matters" finding. Worth retesting other scan
   orders against the new corrected counter.

3. **ALNS-`minimal` operators beat `mega` operators** on a 403 input by +17
   edges. The mega-ops "scorch and rebuild" loses cells we want to keep.
   This is consistent with vol-44's basin-locking finding: small surgical
   moves preserve more good structure than aggressive destroy.

4. **Trim-and-restart DFS dies at depth 205**: pinning a 403 partial as
   hints leaves no valid completion. The 403 is a deep local optimum,
   not a near-solution. This confirms the "basin lock" pattern at the
   vanilla DFS level too.

5. **Color complexity has non-monotone effects below C=8**: instance
   variance dominates color count. This is novel structural information
   we hadn't measured before in this volume series.

6. **ALNS sweep ceiling at 454/480** under `minimal` ops across 20 jobs
   confirms vol-44's "458 is firm without different approach" finding,
   from a different starting point.

7. **Future-work hook**: the parallel agent's open Q2 (engine trivially
   solves C=6/7?) is a clean cheap experiment we should run when this
   vol-48 RL track concludes.

## Recommended vol-N+? items (for backlog)

- **F1**: Re-run the multi-seed color sweep with `joe_depth150_bp_par`
  profile (propagator-based engine) on the same C=6..12 puzzles. Compare
  to vanilla. Test the propagator's value at low-C.
- **F2**: Run the engine on the **C=8 seed=3 adversarial puzzle**.
  Whatever score it gets, that's a useful data point for engine
  robustness.
- **F3**: Finer sweep at C=7.0..7.5 (biased generators) to pinpoint the
  difficulty cliff.
- **F4**: Test if border-first scan order outperforms row-major in the
  full propagator engine (not just vanilla DFS).
