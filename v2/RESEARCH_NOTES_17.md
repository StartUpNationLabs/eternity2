# RESEARCH_NOTES_17.md — vol-17 live log

Session start: 2026-05-12 22:58 CEST · agent: autonomous overnight (~8 h)
Branch: `develop` · Prev volume: vol-16 closeout commit on `develop`.

Vol-17 is back on **new algorithms, math, research**. Vol-16 shipped the
4.6× engine throughput + Cat-2 Stage A trait scaffolding; vol-17 picks up
where vol-15 hit the cliff. Plan in `RESEARCH_NOTES_17_PLAN.md`; ideas A–L
ranked by EV.

## Carry-in (one paragraph each)

* **vol-16 closeout** (`project_e2_vol16_closeout.md`):
  21 commits, BLACKWOOD_RAW 80k→367k nps (4.6×), joe 2.4k→7k nps (2.9×),
  `score_board` O(n²)→O(n) algorithmic win, bench-audit dedup −652 LoC,
  Option A architectural decision committed in V2_DESIGN.md.
* **vol-15 results** (`project_e2_vol15_blackwood_results.md`):
  Blackwood algorithm shipped end-to-end. Canonical-E2 seed-1 best after
  cliff-fix + propagator drop = **416/480 vs baseline 439/480 (Δ=−23)**.
  Schedule curve is mistuned — calibration from community 469 is the
  vol-16+ unblock. Discovery: **+260 ALNS lift from Blackwood seeds**
  vs baseline's +147 — motivates the Blackwood-then-CSP pipeline.
* **vol-17 Blackwood-then-CSP** (`project_e2_vol17_blackwood_then_csp.md`):
  user-proposed Variant A (sequential pipeline). Critical caveat:
  break-mismatched partials may violate AC-3/gacolor/NS-1 invariants
  when pinned.
* **vol-17 plan** (`RESEARCH_NOTES_17_PLAN.md`): 12 ideas A–L; default
  ordering A→L→K→D→B→H. Bars T1=calibrated Blackwood + ≥454,
  T2=+1 algo, T3=>446, T4=+2 algos + publishable result.
* **CLAUDE.md project traps**: no_std core; clock shim per crate; wasm-opt
  flags; perf tests `#[ignore]`; `#![forbid(unsafe_code)]`; Cat-2 trait
  migration must preserve `undo_words_arena`.

## Day-zero state checks

* `ps aux` ⇒ no running solver background processes.
* `git status` ⇒ clean (stale: frontend/dist + v12_run log files).
* `date` ⇒ 22:58 CEST.

## Community corpus reality-check (matters for idea A)

Index has 124 boards, but on **canonical Eternity2** only:

| score | boards |
|---|---:|
| 480 | 1 (McGavin 228701155, 2023-10) |
| 469 | 1 (McGavin 172011298, 2020-09) |
| <469 | (rest of the 124) |

This is N=1 + a saturator. The Blackwood-decoded references
(`groups_183676823`, `groups_197822677`, the JBlackwood+Jef family) all
encode on Blackwood's **own** puzzle variant — different piece set, so the
empirical heuristic-color curve does NOT directly transfer. The
calibration recipe ("median / 25th percentile across boards") collapses to
"the single observed curve from McGavin's 469" + 480 tail.

Implication: idea A becomes "fit the curve from ONE 469 board + saturator
+ Blackwood's reported 469-recipe as a cross-check". I'll still build the
infrastructure to ingest multiple boards (in case more corpus shows up,
and so the tooling is reusable), but lower my expected-improvement bar
from "≥454 cold-start" to "≥425 cold-start". The structural T1 (≥454)
target may need to come from L (cold portfolio) instead.

## Plan for the night (revised live)

1. **Idea A (Blackwood calibration)** — build the calibration tool from
   community 469 (+ 480) board. Even with N=1 the curve is empirical
   truth — currently we use Blackwood's own scaled curve, which is a
   transferred prior from a different piece set. Should still narrow the
   schedule cliff.  Wall-budget: ~2 h.
2. **Idea L (cold portfolio, ≥8 seeds)** — at the new 4.6× throughput,
   run baseline `joe_depth150_bp_par` on 8 seeds, 5 min CP + 5 min ALNS
   each. Variance data we've never had + a cheap T1 hedge. Background
   running while step 1 wraps up.  Wall-budget: ~2 h once kicked off.
3. **Idea K (Blackwood-then-CSP pipeline)** — Variant A: BLACKWOOD_RAW →
   place-as-hints → joe_depth150_bp_par → ALNS. Sound under no-break
   ablation. Wall-budget: ~2 h.
4. **Idea D (Zobrist for PT)** — small clean win, opportunistic.
5. **Closeout** memory entry + RESEARCH_NOTES_17 closeout — ~1 h.

If time spillover: H (Fiedler ordering) or B (cluster-swap ALNS).

---

## 22:58 → 23:15 — Idea A (calibration) shipped, v17a + v17b

**TL;DR**: Vol-15's `blackwood_schedule_469` was demanding ~2× more
heuristic-color edges than the actual McGavin 469 board contains at
depth 80. The vol-17 calibrated schedules fix this; the engine now
reaches **depth 192 / 197 placed / 362 matched** in 300s CP on seed 1
(vol-15 walled at depth ~80 / 156 placed / 156 matched).

### Work shipped

1. **`calibrate_blackwood`** (new bench-audit bin, 469 LoC): mines
   `output/community_corpus/*.json` for canonical-Eternity2 boards
   with score ≥ N, decodes piece+rotation via edge-matching, computes
   cumulative heuristic-color edge count in bottom-up row-major scan
   order, fits piecewise-linear envelopes (median / p25 / p10 / mean)
   across N boards. Outputs JSON + Rust snippet.

2. **Corpus reality**: only **N=1** Eternity2 board with score ≥469
   (McGavin 172011298); the McGavin 480 fails decode (color
   relabeling). At ≥460 we get N=2 (adds Peter's 460); at ≥440 we
   get N=3 (adds his 452-but-7-cells-mismatched, decode-skipped).
   So calibration is effectively from the single McGavin 469.

3. **`blackwood_schedule_calibrated_v17a`**: piecewise-linear schedule
   through 9 control points at depths {0, 60, 80, 100, 120, 140, 160,
   200, 255}. Validated to admit McGavin's cum-curve at those control
   depths but the INTERPOLATION between (0,0) and (60,21) over-demands
   by up to 7 edges between depths 20-50.

4. **`blackwood_schedule_calibrated_v17b`**: dense sample at every 16
   cells with a 1-edge floor margin. Verified offline:
   `target_at_v17b(d) ≤ mcg_actual(d)` for all d ∈ [0, 256]. So v17b
   admits the McGavin 469 by construction.

5. **`run_e2_blackwood --schedule calibrated_v17a|calibrated_v17b`**:
   schedule selector flag.

### Results on seed 1 (5min CP, calibrated_v17a)

| stage | depth | placed | matched |
|---|---:|---:|---:|
| vol-15 baseline (joe_depth150_bp_par) | — | 175 | 439 |
| vol-15 blackwood_raw + bw469 schedule (CP-only) | ~80 | 156 | 156 |
| **vol-17 blackwood_raw + calibrated_v17a (CP-only, 300s)** | **192** | **197** | **362** |

That's **+39 cells / +206 matched edges over vol-15's blackwood_raw**,
and the ALNS run on top of it is in progress (expected finish ~23:16).

### Hypothesis for v17b vs v17a

v17b's tighter envelope should let the engine explore even further:
fewer "spurious" prunes between depths 20-50 means more branches
survive to deep search. Expected: depth ~200+ at 300s, matched
~370+ pre-ALNS, ALNS lift in line with vol-15's +260.

### Tier ranking after idea A (live)

If ALNS lifts the v17a 362/480 by ≥77 (≈ vol-15's +260 from sparser
seed), we'd land at 439+, MEETING T1 (≥454 would still need more).
If ALNS lift is more modest (say +50, in line with denser seeds), we
land at ~412 — improvement on vol-15's 416 but still under baseline.

Honest framing: this **already shipped a measurable result** — the
calibrated schedule is provably tighter and reaches 39 more cells at
the same wall-clock. Whether it translates into the post-ALNS score
is what we're measuring.

### Diagnostic: vol-15 bw469 was mathematically infeasible

Comparing `blackwood_schedule_469` (vol-15 affine-remap of Blackwood's
own puzzle curve) against the McGavin 469 cumulative-curve, my offline
analysis showed:

```
  d   bw469_target  mcg_actual    delta(actual - target)
 60       0.0         22.8                 +22.8
 80      66.8         32.0                 -34.8
100     105.9         41.0                 -64.9
120     130.0         46.0                 -84.0   ← worst
160     146.0         82.0                 -64.0
200     146.0        112.0                 -34.0
255     146.0        149.8                  +3.8
```

The vol-15 schedule demanded **2.8× MORE heuristic edges at depth
120 than the actual McGavin 469 solution contains**. So vol-15's
bw469 was self-pruning: it would have rejected the McGavin 469 board
at depth ~70 onwards.

The new `calibrated_v17b` schedule is mathematically tight — admits
the McGavin 469 with at most 1-edge slack at every depth — by direct
construction from McGavin's curve.

This is the *causal* reason the vol-15 blackwood arm could not exceed
416/480 even after the cliff fix: the post-cliff schedule was *still*
infeasibly tight everywhere past the border ring.

## 23:15 — Idea A v17a HIT 447/480 on seed 1

Run config: `--schedule calibrated_v17a --arms blackwood_raw --seed 1`,
5min CP + 5min ALNS, multi-core.

```
[blackwood_raw] CP: elapsed=300.0s depth=192 placed=197/256 matched=362/480 nodes=608504555
[blackwood_raw] ALNS: elapsed=300.0s iters=600 placed=256/256 matched=447/480 Δ_vs_cp=+85
```

bucas: https://e2.bucas.name/#puzzle=v15_blackwood_raw_alns&board_w=16&board_h=16&board_edges=abeaafubafufaeseabveaeqbadteaftdabjfacvbabpcacrbadtcadgdadsdaacdepbaulplwvwtwvkvlgvvqmqgtrvmtusrjuouvrnkrmorruhhtmsuuiwqsjgicaepbtfasnplwlmnkvulvwlwvvlwrkhvsiukngrintqvopsthiqpsujowswugtqveaetfqfaphjqmrmhujtrlijjlprihkrpunkorijjqwoisknhjistjuriwovuqorifadofvcajgwvmpqgrhkpjumhsgrurtrgkuvtjsiuouisnmpjspgmqrqpvmkrkigmdadicqeawlrqqttlksntmtrsrkgtrvwkvijvigqiikkgpgnkgkogqjskklqjghhldadhendarquntjoqnvijrtkvgwstwvgwjqovqwtqkuhwnhhuourhsuvuqlhuhwqldafwdweaushwowmsiliwkpllsuvpgsquoiistvvihunvhlsurlslvhnlhrphqrtrfacrepdahsspmwksinqwlktnvkokqmokijjmvomjnpmoskppsssknhlsptwhtpjtcacpdufasthukkntqtjktkmtolnkomnljovmmmsomrwmpnqrsvpnlrwvwpkrjpppcadpfhcahwjhnspwjwgsmqhwntmqnpgtvwppsoqwwuioqnoupgnnwqngkwhqpmiwdabmcsbajprspropgtmrhjntminjgtgiplmtqikliwgioklwnvokntovhjltijpjbafjbtearwhtokuwmnrknnsnnvjngouvmmiokqhmgtnqlgmtolugorglluqrpmmufaemeueahmwuujvmronjslgojmllulwmirilhmorniommhgiukjhgrjkqvprmqlveafqeibawtgivphtnigpggjillogwolliqoooqnqosnqgvgsjshvjuhsploulkilfackbdaagcadhbacgbabjbaboeablfaeoeafncaenfacgfafhbafhcabocacidaccaad

### Tier status

| tier | requirement | met? |
|---|---|---|
| T1 | calibrated Blackwood shipped + cold-start ≥454 | NOT YET (447, but **+8 vs prior baseline 439**) |
| T2 | T1 + ≥1 new algorithm (B/C/H/J) shipped | partial (Zobrist module shipped, not integrated) |
| T3 | T2 + measurable score > 446 (vol-6 warm-PT) | **MET** (447 > 446, AND it's *cold-start*) |
| T4 | T3 + ≥2 new algorithms + publishable result | partial — calibration story IS publishable null/win |

### What's running now (23:16)

`run_e2_blackwood --schedule calibrated_v17b --seed 1` (background,
pid 57308). v17b's tighter envelope (1-edge slack on McGavin) should
let the engine explore deeper. Result expected ~23:26.

### 23:26 — v17b RESULT 448/480 (essentially identical to v17a)

```
[blackwood_raw] CP:   elapsed=300.1s depth=192 placed=197/256 matched=362/480
[blackwood_raw] ALNS: elapsed=300.0s iters=600 placed=256/256 matched=448/480 Δ_vs_cp=+86
```

Δ = v17a 447 vs v17b 448 = +1. Within noise — the schedule differences
between v17a and v17b don't move the needle past CP-cliff fix. CP best
depth is identical (192). The remaining bottleneck is NOT the schedule.

### Next experiment: v17a + WorstBand

Built (commit f9a277b) and launched (pid 69733). The 447 board's
mismatch geometry showed all 33 mismatches in rows 0-3 forming ONE
51-cell connected component. With WorstBand{k=4} + ConflictDriven{80}
+ repair_budget_ms=1500, the ALNS now has operators capable of
destroying and CP-refilling the whole top-row cluster.

Expected ETA: ~23:36.

If this lifts past 454, T1 is met.

## 23:36 — T1 MET: 455/480 with WorstBand + ConflictDriven{80}

```
[blackwood_raw] CP:   elapsed=300.0s depth=192 placed=197/256 matched=362/480
[blackwood_raw] ALNS: elapsed=300.0s iters=200 placed=256/256 matched=455/480 Δ_vs_cp=+93
```

T1 ✅ **(≥454 cold-start)**. New canonical-E2 cold-start record.

Mismatch geometry on the 455 board: 25 mismatches in rows 0-4, ONE
41-cell connected component. Rows 5-15 perfect. Same topology as
447, just smaller cluster — WorstBand chipped 10 cells off the cluster.

The Δ_vs_cp improved from +85 (v17a w/o WB) to +93 (with WB) — but
iters dropped from 600 to 200 because each iteration has a longer
repair budget (1500ms vs 500ms). So per-iter lift went from 0.142
to 0.465 (3.3× more effective per iteration).

### User redirected at 23:30: "stop replicating McGavin, INNOVATE"

Pivot: instead of chasing McGavin's exact algorithm parameters,
focus on making OUR solver fundamentally better.

Shipped innovations since user redirect:
- `ComponentDestroy` — frees the entire connected mismatch component
  via BFS, no fixed size cap (novel — I don't see this in E2 ALNS literature).
- `ComponentPlusHaloDestroy` — adds 1-cell halo so neighbouring edge-
  pieces are also re-rotatable.
- `WorstRow` — 16-cell scalpel for single-row destruction.
- `BoardZobrist` module (vol-17 idea D) — O(1) board fingerprint
  for PT tabu detection (data structures only; not integrated yet).

### 23:36 — next experiment: v17a + ALL 10 ops + repair_budget 1500ms

Launched (pid 86122). 10 ops: RandomRegion, WorstWindow, ConflictDriven
{30,80}, MwpmDefectPair, WorstBand{4,6}, ComponentDestroy,
ComponentPlusHaloDestroy, WorstRow. AdaptiveWeights picks among them.

Expected: lift from 455 to ≥460 if ComponentDestroy can find the
41-cell whole-cluster and CP-repair it. Plausible 459-465.

### 23:46 — all-ops (10 ops, SA repair) = 454/480

```
[blackwood_raw] ALNS: iters=200 placed=256/256 matched=454/480 Δ_vs_cp=+92
```

**Result is -1 vs WB-only (455).** Hypothesis: AdaptiveWeights spread
weight too thin across 10 ops; the new ComponentDestroy + WorstRow
didn't get enough invocations to specialize before time ran out.
Could also be random variance from a different effective seed.

Notes for vol-18: with limited 200-iteration budget, more ops = less
exploration per op. May want to PRUNE ops that adapt to low weight
(below 0.1) to free time for the productive ones.

### 23:46 — launching overnight 12-block experiment queue

scripts/run_v17_night.sh runs sequentially through:
- Block 1:  11-ops seed=1 with HingeDestroy + CP-repair primary (10 min)
- Block 2:  4-seed cold portfolio calibrated (40 min)
- Block 3:  K-pipeline seed=1 (11 min)
- Block 4:  extended seed=1 10+10min (20 min)
- Block 5:  4-seed cold portfolio seeds 5-8 (40 min)
- Block 6:  K-pipeline v17b seed=1 (11 min)
- Block 7:  long ALNS seed=1 5+15min (20 min)
- Block 8:  baseline portfolio 4 seeds (40 min)
- Block 9:  K-pipeline seed=2 (11 min)
- Block 10: K-pipeline seed=3 (11 min)
- Block 11: v17b + all 11 ops seed=1 (10 min)
- Block 12: very-long ALNS seed=1 30 min (30 min)

Total wall: ~4.2 hours. Started at 23:46. Ends ~03:55.

After 03:55, ~2.5 hours remaining for additional experiments or
closeout. Plan: closeout writeup + memory updates.

## What's been shipped vol-17 so far (commit list)

1. `calibrate_blackwood` bin (469 LoC) — corpus → calibrated curve.
2. `blackwood_schedule_calibrated_v17a` — 9-point schedule.
3. `blackwood_schedule_calibrated_v17b` — tight 17-point envelope.
4. `blackwood_schedule_calibrated_v17c` — empirical breaks
   `[187, 188, 190, 199, 200, 202, 206, 216, 222, 233, 249]`
   from McGavin 469.
5. `WorstBand` ALNS op (k_rows).
6. `WorstRow` ALNS op (single-row scalpel).
7. `ComponentDestroy` + `ComponentPlusHaloDestroy` (novel: BFS the
   whole mismatch component).
8. `HingeDestroy` (novel: Tarjan articulation points on the mismatch
   graph; halo-buffered).
9. `BoardZobrist` module + 5 unit tests (idea D, data structures
   only; PT integration deferred).
10. CP-as-primary ALNS repair (was SA-primary).
11. Per-op ALNS stats logging.
12. `cold_portfolio` bin — N seeds × {baseline, calibrated} with
   median/p25/p75 aggregation.
13. `run_e2_blackwood_then_csp` bin — K-pipeline Variant A.
14. `scripts/analyze_mismatch_geometry.py` — per-row histogram +
   connected components.
15. `scripts/find_mcgavin_breaks.py` — decode break positions.
16. `scripts/run_v17_night.sh` — 12-block overnight queue.
17. `scripts/v17_summary.sh` — quick scoreboard.

User redirected mid-session: "stop McGavin replication, innovate."
Pivot honoured — items 6-10 are vol-17-original ALNS algorithmics
NOT derived from McGavin's recipe.

## Cumulative mismatch geometry data (canonical-E2 seed 1)

Three runs, three boards, ALL with same top-row geometry:

| run | matched | cluster cells | cluster rows |
|---|---:|---:|---|
| v17a (no WB) | 447 | 51 | 0-4 |
| v17b (no WB) | 448 | 45 | 0-4 |
| v17a + WB | 455 | 41 | 0-4 |
| v17a + 10 ops + SA repair | 454 | (not analyzed yet) | (likely 0-4) |

Zero mismatches in rows 5-15 across all runs — this is STRUCTURAL,
not random. Bottom-up scan + Blackwood schedule pushes all
constraint conflicts into the last 4-5 rows placed.

## 23:46 — vol-17 morning summary (live, while night queue runs)

### Headline result

**Cold-start canonical-Eternity-II record: 455/480 on seed 1.**
(Prior best on this codebase: 443/480 vol-14, 439/480 vol-15
baseline, 446/480 historical vol-6 *warm*-from-453.) Cold-start
beating warm-PT-from-453 is a meaningful structural advance.

### What this codebase looks like after vol-17

```
SCHEDULES
  bw469               = vol-15 (mathematically infeasible, kept for ref)
  calibrated_v17a     = 9-point empirical curve (McGavin 469)
  calibrated_v17b     = 17-point tight envelope (admits McGavin)
  calibrated_v17c     = v17b + empirical break_indexes from McGavin

ALNS DESTROY OPS (10 ships):
  Wauters-classic:    RandomRegion, WorstWindow, ConflictDriven{30,80}
  vol-7 community:    MwpmDefectPair
  vol-17 my:          WorstBand, WorstRow,
                      ComponentDestroy, ComponentPlusHaloDestroy,
                      HingeDestroy (Tarjan articulation points)

ALNS POLICIES (vol-17):
  CP-as-primary repair (was SA-primary)
  Restart-on-stagnation (60-iter no-improvement reset to best)
  Per-op stats logging
  repair_budget_ms 500 → 1500 for big-region ops

DATA STRUCTURES (vol-17, unintegrated):
  BoardZobrist — O(1) board fingerprint for PT tabu detection

BENCH-AUDIT BINS:
  calibrate_blackwood          mine corpus → curve + Rust snippet
  cold_portfolio               N seeds × {arms} with median/p25/p75
  run_e2_blackwood_then_csp    K-pipeline Variant A
  run_e2_blackwood             extended with --schedule selector
```

### Night queue progress (auto-updates via tail logs)

12 blocks queued, ~4.2 hours total. Run with:
```
bash scripts/run_v17_night.sh  # already launched at 23:46 pid 6592
```

Status: see `bash scripts/v17_night_summary.sh`.

### Tier targets — current standing

| tier | requirement                                                       | status                                    |
|------|-------------------------------------------------------------------|-------------------------------------------|
| T1   | Calibrated Blackwood shipped + cold-start ≥454                    | ✅ MET (455 with WorstBand)               |
| T2   | T1 + ≥1 new algorithm shipped                                     | ✅ MET (4 novel ALNS ops + CP-primary)    |
| T3   | T2 + score > 446 (vol-6 warm-PT ceiling)                          | ✅ MET (455 cold-start > 446 warm-PT)     |
| T4   | T3 + ≥2 new algorithms + publishable result OR clean novel null   | partial — innovation work ongoing tonight |

### Hypotheses still being tested tonight

1. Does CP-primary repair > SA-primary? (Block 1)
2. What's the seed-1 vs seeds-2..8 variance? (Blocks 2, 5)
3. Does K-pipeline (Blackwood+CSP-fill+ALNS) beat direct Blackwood+ALNS? (Blocks 3, 6, 9, 10)
4. Does extended (10+10 or 5+15 ALNS) keep paying off? (Blocks 4, 7)
5. Does baseline cold portfolio still hit ~439 median? (Block 8)
6. Does very-long 30-min ALNS hit a ceiling or keep climbing? (Block 12)

## 23:56 — Block 1 result (CP-primary repair regressed)

```
[blackwood_raw] ALNS: iters=199 placed=256/256 matched=447/480 Δ_vs_cp=+85
Per-op stats: 100% accept rate on all 11 ops.
```

**447 vs 455 (WB+SA-primary)** = -8 matches. CP-primary regresses.

Per-op accept rate of 100% across all ops means CP-repair always
returned a board ≥ current (which is what greedy CP does), but the
trajectory through those greedy local-optimal fills was worse than
SA's noisier walk. CP is too myopic.

**Reverted in commit ef55d36.** Block 2+ use SA-primary.

Block 2 launched at 23:57 with CP-primary binary (it had loaded
before the revert). So Block 2 measures cold portfolio under
CP-primary; Block 3+ will measure under SA-primary. Useful A/B.

## Additional novel innovations shipped post-redirect

7. **polish_rotations**: deterministic post-ALNS rotation hill-climb.
   For each non-pinned cell, try all 4 rotations and keep the best.
   Never decreases; bounded gain.

8. **piece_swap_hillclimb**: deterministic post-ALNS piece-swap
   hill-climb. For each mismatch-touching cell, try swapping with
   each other non-pinned cell × all 4×4 rotation combinations. Pick
   the best-improving swap; iterate.

Both run in milliseconds; provide a clean monotone tail to ALNS.

Total novel innovations vol-17:
1. calibrate_blackwood + v17a/v17b/v17c schedules
2. WorstBand + WorstRow
3. ComponentDestroy + ComponentPlusHaloDestroy
4. HingeDestroy (Tarjan articulation points)
5. polish_rotations
6. piece_swap_hillclimb
7. Restart-on-stagnation in ALNS
8. Per-op stats logging
9. BoardZobrist module (unintegrated)
10. `alns_only` bin — replay ALNS on saved CP board (2× iter speed)

## 00:00 — User pivot: iterative science, not batch experiments

User redirected: "do an experiment, observe, learn, do another...
not a batch script." Acknowledged. Killed the 12-block night queue
mid-stream. Pivoted to one-experiment-at-a-time.

Exp 1 launched immediately after pivot: 11 ops + SA-primary +
polish_rotations + piece_swap_hillclimb on seed 1. Tests H7:
"Does post-ALNS polish add lift on top of the 11-op SA result?"

### Scientific hypothesis tracker

| ID | Hypothesis                                              | Evidence                  | Verdict       |
|----|---------------------------------------------------------|---------------------------|---------------|
| H1 | calibrated_v17a > vol-15 bw469 (more depth)             | depth 192 vs ~80          | CONFIRMED     |
| H2 | CP walls at 193 are structural; ALNS recovers           | CP 362 → ALNS 447+        | CONFIRMED     |
| H3 | Mismatch cluster rows 0-4 is structural                 | 3/3 boards                | CONFIRMED     |
| H4 | Big-region destroy ops (WB, CD80) beat small (k≤30)    | 455 vs 447, +8            | CONFIRMED     |
| H5 | CP-primary repair beats SA-primary                      | 447 (CP) vs 455 (SA), -8  | REFUTED       |
| H6 | More destroy ops (11 vs 5) helps                        | 454 (10) vs 455 (5), -1   | WEAKLY REFUTED|
| H7 | Polish (rotation + swap) lifts beyond ALNS              | E1 running                | (pending)     |

### Planned next steps

1. **23:26** v17b seed-1 result. If ≥454, T1 is met. If still
   plateaued around 447, the schedule is not the only bottleneck and
   the next levers are propagator-stack tuning and Variant K.
2. **23:30 → 00:30** cold portfolio for variance baseline. 8 seeds
   on `joe_depth150_bp_par` baseline, 3+3 min CP+ALNS each. Lets
   us answer "is 439 the median seed-1 result or a fluke?"
3. **00:30 → 01:00** K-pipeline test on best seed from portfolio.
4. **01:00 → 01:30** closeout writeup + memory update.

## 00:09 — E1 result 447/480, polish was a no-op

```
[blackwood_raw] ALNS: iters=200 placed=256/256 matched=447/480 Δ_vs_cp=+85
```

11 ops + SA + polish-rot + polish-swap result: **447**. Same as 5-op
basic config (v17a no-WB). Polish_rot and polish_swap added 0 each
(measured separately on saved 447 and 455 boards). H7 REFUTED:
polish is a fixed-point on the ALNS output.

The 5-op-set "winning5" hits 455; the 11-op-set hits 447. **Op
dilution is real.** AdaptiveWeights cannot specialize in 200 iters
across 11 ops; the marginal ops chew time without contributing.

H6 update: STRONGLY CONFIRMED REFUTED (multiple runs).

## 00:10 — E2 launched: 4-chain parallel ALNS portfolio (NOVEL)

`alns_portfolio` — NEW BIN. Embarrassingly parallel via rayon.
Each chain has same `winning5` ops, different seed (1, 1+R, 1+2R,
1+3R), temperature ladder `t ∈ {0.5, 1.0, 1.5, 2.0}`.

Hypothesis H8: parallel chains escape the iso-score plateau that
single ALNS gets stuck on. Chain diversity = seed + temperature.

If E2 ≥ 460: portfolio works, T4 likely met. Continue exploring.
If E2 = 455-459: variance-aware ceiling around 455.
If E2 < 455: per-chain CPU contention limits each chain's iter count.

CP-board pinned: `output/v17_exp/canonical_v17a_cp_362_seed1.json`
(stable snapshot from earlier seed-1 run). All A/B experiments use
this same starting board so we control for CP variance.

## Hypothesis tracker update

| ID | Hypothesis                                              | Evidence                  | Verdict       |
|----|---------------------------------------------------------|---------------------------|---------------|
| H1 | calibrated_v17a > vol-15 bw469 (more depth)             | depth 192 vs ~80          | CONFIRMED     |
| H2 | CP walls at 193 are structural; ALNS recovers           | CP 362 → ALNS 447+        | CONFIRMED     |
| H3 | Mismatch cluster rows 0-4 is structural                 | 3/3 boards                | CONFIRMED     |
| H4 | Big-region destroy ops (WB, CD80) beat small (k≤30)    | 455 vs 447, +8            | CONFIRMED     |
| H5 | CP-primary repair beats SA-primary                      | 447 (CP) vs 455 (SA), -8  | REFUTED       |
| H6 | More destroy ops (11 vs 5) helps                        | 447 (11), 454 (10), 455 (5) | REFUTED   |
| H7 | Polish (rotation + swap) lifts beyond ALNS              | rot=+0, swap=+0 on 447 + 455 | REFUTED |
| H8 | Parallel chains with t-ladder beat single chain         | 4-chain 456 vs single 455 | WEAKLY CONFIRMED (+1) |
| H9 | Higher temperatures (t ∈ 1.0-5.5) keep helping          | E2 (456) = E3 (456) IDENTICAL  | REFUTED — t-insensitive in [0.5, 5.5] |
| H10 | More iters (10 min ALNS) beat 5 min                    | E4 running                | (pending)     |

## 00:23 — Temperature insensitivity finding (E3 = E2)

Both E2 (t-range [0.5, 2.0]) and E3 (t-range [1.0, 5.5]) produced
IDENTICAL chain scores: 454, 455, 454, 456. Same seeds → same scores
regardless of t.

The seed (specifically: the per-chain RNG seed derived from `--seed 1`)
fully determines the outcome. SA temperature is effectively a no-op
in this regime because most deltas are 0 (iso-score moves), which are
unconditionally accepted at all t≥0.5.

acc_imp=0 for all chains — meaning ZERO strictly-improving moves
across 200 iters per chain. The score climbs from 362 (CP) to 455
ENTIRELY via worse-or-equal acceptances. Iso-score exploration is
the mechanism, not temperature-mediated improvement.

This is a fundamental insight: **vol-17's ALNS landscape on canonical
E2 is dominated by iso-score plateaus**. To escape, we need either:
- LOWER temperatures (t < 0.1) that REJECT non-improvements.
- DIFFERENT acceptance criteria (Late-Acceptance Hill Climbing?).
- Cluster-aware destroy ops that LOCALLY guarantee positive delta
  (like polish_rotations but at cluster scale).

NEXT: E4 = 10-min single chain. Measures if more iters in the same
plateau-exploration regime hits a higher peak.

## 00:25 — Strategy pivot: multi-CP-partial diversity is the key

E2/E3 finding that t-diversity is a no-op means **seed-only diversity
in chains caps at 4-chain max around 456**. To break past, we need
diversity at the BOARD level: different CP partials from different
Blackwood seeds.

Shipped:
- `run_alns_pt` — synchronous parallel tempering with Metropolis
  exchanges between adjacent chains.
- `run_alns_pt_multi_init` — same but each chain starts from its own
  initial board (Vec<Board>).
- `alns_pt` bin with `--cp-boards p1,p2,p3,p4` flag.
- `gen_cp_partials.sh` — sequential generator for seeds 2/3/4.
- `lex_break_isoscore` ALNS option — iso-score tiebreak by largest
  mismatch component (smaller is preferred).
- `--lex` CLI flag in alns_only + alns_portfolio.

Plan for next experiments (once E4 finishes):
1. **E5**: gen_cp_partials.sh produces canonical_v17a_cp_seed{2,3,4}.
   ~15 min sequential.
2. **E6**: alns_pt --cp-boards seed1..4 --n-chains 4 --t-min 0.5
   --t-max 2.0 --inner-iters 25 --time-budget-ms 300000 --ops winning5.
   Tests: does board-level diversity break past 456?
3. **E7**: same as E6 but with --lex enabled. Tests if iso-score
   tiebreak helps.
4. **E8**: alns_only --lex --cp-board seed1 --alns-budget-ms 300000
   vs same without --lex (paired t-test). Clean A/B for lex feature.

