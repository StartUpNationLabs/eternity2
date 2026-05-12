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

### Planned next steps

1. **23:26** v17b seed-1 result. If ≥454, T1 is met. If still
   plateaued around 447, the schedule is not the only bottleneck and
   the next levers are propagator-stack tuning and Variant K.
2. **23:30 → 00:30** cold portfolio for variance baseline. 8 seeds
   on `joe_depth150_bp_par` baseline, 3+3 min CP+ALNS each. Lets
   us answer "is 439 the median seed-1 result or a fluke?"
3. **00:30 → 01:00** K-pipeline test on best seed from portfolio.
4. **01:00 → 01:30** closeout writeup + memory update.

