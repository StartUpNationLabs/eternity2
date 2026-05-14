# Vol-32 wake-up summary (2026-05-14 ~03:25)

Read this first.

## 🎯 HEADLINE: 457/480 RECORD TIE via blackwood_raw+MRV pipeline

**Achievement**: tied vol-18's all-time cold-start record of **457/480**
in just **10 minutes of compute** (5min CP + 5min ALNS, single seed),
using the **blackwood_raw + MRV** value-order discovered as a vol-32
bonus from the bug-investigation cross-profile sweep.

**Pipeline**:
```
canonical-eval --profile blackwood_raw --mode mrv --budget-ms 300000 --dump-partial <out>
   ↓ depth 191, 196/256 placed, 359/480 edges
alns_only --cp-board <partial> --alns-budget-ms 300000 --seed 7 --ops winning5 --repair-kind sa
   ↓ matched=457/480 (95.2%), 256/256 placed
```

**Saved board**: `output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json`
(md5: 969a282d...). **3rd distinct 457 in project history**
(vol-18 byte-identical x11, vol-21 bound-ascent 457 at basin-bound 461,
this vol-32 457). 247/256 cells differ from vol-21's 457.

**Lottery context (N=24 seeds × 5min ALNS from the 5min CP partial)**:
- 2/24 (8%) reached **457** (seeds 7 & 10, distinct boards)
- 5/24 reached 456
- 4/24 reached 455
- mean=450.2, median=454, max=457, min=434, stdev=6.86

**Bound-ascent on the 457 boards**:
- 5min seed 7's 457: bound = 462 (+5)
- 5min seed 10's 457: bound = 457 (saturated)
- 30min seed 4's 457: bound = 465 (+8, HIGHEST)

5000-10000-iter SA bound-ascent from each: best stays at original bound.
**The basin family is structurally capped at 457 under ALL our operators.**

**Final cumulative experiment (vol-32 close, 05:50)**:
57 ALNS lottery runs + 4 PT configs + 10000-iter bound-ascent + 8 ops
presets — across 3 distinct 457 boards with bounds varying 457-465.
**0 runs broke 457.** All converge to 457 (or below for non-457 seeds).

Also confirmed at vol-32 close that **joe_depth150_bp at 30min CP
hits the SAME depth-174 partial as at 60s** — engine is wall-locked
at depth 174 for that profile regardless of time. blackwood_raw is
the unique config in our codebase that pushes past 174 to 190+.

See `vault/sessions/vol-32-457-record-tie.md` for full experiment list.

**Saved boards**:
- `output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json` (bound 462)
- `output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json` (bound 457, saturated)

---

## 🚨 MORNING UPDATE (07:30-08:10) — 458/480 NEW RECORD

Morning push achieved:
1. **vanilla_fast bin shipped** — 125M pp/s single-thread (community
   speed range, Yendor 97M / Razvan 140M). 8-thread mode: 577M
   aggregate pp/s. See `vault/sessions/vol-32-458-NEW-RECORD.md`.
2. **vanilla_fast → ALNS gave 458/480** (seed 5 of 8-seed lottery) —
   **+1 over all-time record**.
3. **Caveat**: 2 of 5 canonical hints displaced (cells 210, 221).
   User accepts: matched-edges on canonical piece set is the
   achievement.
4. **Fix shipped**: vanilla_fast --pin-hints now always includes
   all 5 hints in saved partial regardless of max_depth.
5. **vanilla_fastest** (unsafe variant): same throughput as safe
   (LLVM already at optimization ceiling).

**Morning lottery attempts** (post-458):
- 8 ALNS seeds × 5min from 458 board (winning5): all 458 (basin lock)
- 4 ALNS ops variants (mega, full, hingeonly, componentonly): all 458
- Bound-ascent from 458: found b463-464 configs (higher bounds)
- ALNS recovery from b463/b464: 452, 456, 456 (recipe doesn't bridge)

**Verdict**: 458 stands. 459+ needs algorithmic propagation
(unsat-propagator) or fundamentally different operators.

**Bucas URL**: see `output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.url.txt`.

---

## NEXT VOLUMES (split per user)

- **VOL-33**: code quality refactor (vol-25 items, 8 vols deferred).
  Pure refactor — extract-eternity2-time/export/puzzle-io crates,
  split solver-engine lib, consolidate bin harness.
- **VOL-34**: throughput exploitation + record chase.
  Hour-long vanilla_fast probes, unsat-clause-propagator Rust
  integration, mass ALNS lottery from 100 partials.

---

## What happened tonight

### 1. The original ML plan was invalidated (early on)

Vol-30/31's "+9 depth lift from LearnedOnTies" was a **one-line engine
bug** (lib.rs:2550 cell_side_edge initializer didn't include the
LearnedOnTies arm). The model was never being called. LOT_TRACE
instrumentation found 0 fires under buggy LOT.

**Fix shipped at commit `95978a5`.** Real post-fix ML lift = +3 matched
edges (depth Δ=0), not +9 depth as claimed.

### 2. The real engine win that was hiding under the bug

The "+9" was actually **InsertionOrder beating EdgeBpMarginals by +9
under joe_depth150_bp** — an engine-axis observation, not ML.

Cross-profile A/B confirms inversion: under light propagators
(border_first_lcv) EdgeBp is +22 vs MRV; under heavy propagators
(joe_depth150_bp, gacolor_ac3) InsertionOrder wins.

### 3. ALL-NIGHT BONUS DISCOVERY: blackwood_raw + MRV = 453/480 ALNS-5min

Cross-profile A/B at 30s budget surfaced this:

| Profile + value-order | Depth | Notes |
|---|---:|---|
| blackwood_raw + MRV | **190** | vol-15 thought wall=80 (Blackwood schedule artifact) |
| blackwood_raw + EdgeBp | 190 | |
| blackwood_raw + insertion | 20 | collapse |

**The depth-190 partial → alns_only 5min, seed=1 = 453/480** matched
edges (256/256 placed, all 5 canonical hints in correct positions+
rotations). Verified by `target/release/rescore_board`.

| Pipeline | ALNS-5min |
|---|---:|
| vol-31 baseline | 426 |
| vol-31 "ML" (= InsertionOrder, mis-attributed) | 436 |
| vol-32 strong PT 15min from vol-31 partial | 445 |
| **vol-32 NEW: blackwood_raw_190 → ALNS** | **453** (+8 vs strong PT) |
| vol-18 all-time record (lucky basin) | 457 |

**Only −4 from the all-time record, at iso-budget. Single seed.**

PT-5min from the same partial gave **451** — ALNS beats PT here.

**8-seed ALNS lottery from blackwood_raw_190 partial DONE** (5min/seed):

| seed | score |
|---:|---:|
| 2 | **456** |
| 4 | **456** |
| 1 | 454 |
| 8 | 454 |
| 5 | 452 |
| 7 | 451 |
| 3 | 450 |
| 6 | 442 |

**N=8 mean=451.9, median=453, max=456, min=442.**
**Two distinct 456 boards** (different md5s — not byte-identical
reproduction). **−1 from all-time record.**

**Both 456 basins are basin-locked under winning5 ALNS:**

- **7-seed re-lottery from seed 2's 456 board (seeds 101-107, 5min each)**: 7/7 → 456 (basin-locked).
- **4-seed test from seed 4's 456 board (seeds 201-204, 5min each)**: 4/4 → 456 (basin-locked).
- **15min extension** from seed 2's 456 board (seed 100, 900s): 600 iters, 0 improvements past 456.

Two distinct 456 basins (58/256 cells differ between them), both
are stable local optima.

**ALNS operator portfolio is structurally insufficient to break 456:**
Tested 8 different ALNS ops presets (basic, full, mega, mega_mix,
cdonly, componentonly, hingeonly, wbonly) on seed 2's 456 board ×
5min each. **ALL 8 → 456 exactly, 0 lifts past starting score.**
That covers every operator subset our codebase exposes, including
the strong ones (k=80 ConflictDriven, full HingeDestroy + ComponentDestroy
+ WorstRow, MegaBand, etc.).

PT high-T (T_max=4.0, 8-rep, Houdayer-every-5, kick-every-10, 5min):
**also 456**. Hot replicas only reached 411 — couldn't even climb
back to the 416 plateau the cold replica found, let alone past 456.

**Comprehensive basin-lock verification (vol-32 close)**:
- 8 ALNS seeds × 5min from MRV partial → 442-456, max=456 (2 seeds)
- 7 ALNS seeds × 5min from seed 2's 456 board → 7/7 = 456
- 4 ALNS seeds × 5min from seed 4's 456 board → 4/4 = 456
- 8 distinct ALNS ops presets × 5min × same seed → 8/8 = 456
- 15min ALNS extension (600 iters) → 456 (0 lifts)
- PT 5min strong (vol-31 config) → 451 (worse than ALNS)
- PT 5min hot (T_max=4) → 456 (matches but doesn't escape)
- 8 ALNS seeds × 5min from edge_bp partial (different CP partial,
  same depth 190) → 438-456, max=456 (1 seed)

**The 456 ceiling appears across two distinct depth-190 partials
(MRV-derived and edge_bp-derived) of blackwood_raw cold-start.**
Total 27 ALNS runs across all setups, 6 reached 456, none beat 456.

## WHY the basin is locked: bound = 458-460

Ran `edge_bound_ascent` from the 456 boards (1000-2000 iter SA):

| Board | Initial bound | Final bound (after SA) | Gap (ceil - score) |
|---|---:|---:|---:|
| Seed 2's 456 | 458 | 458 (1000 iter) | +2 |
| Seed 4's 456 | 460 | 460 (2000 iter) | +4 |

**The blackwood_raw basins have bounds 458-460** — only 2-4 theoretical
points above 456. Bound-ascent SA can't move to higher-bound configs.

**This is the structural answer**: vol-22's 469-ceiling basins exist
in a DIFFERENT basin family that bound-ascent CAN reach (vol-22 shipped
the recipe). The blackwood_raw basins are locked at bound 458-460,
which caps the basin family at 456 (gap=2-4).

To reach 457+, vol-33 needs to either:
- Run vol-22's basin-escape recipe FROM these 456 boards (find higher-
  bound configs via the bound landscape).
- Find a different starting partial that's in a high-bound basin
  family from the start.

Breaking 456→457 requires vol-22's basin-escape recipe (bound-ascent
+ Hungarian + multi-hour ALNS), a fundamentally different starting
partial, or new operator engineering. Vol-33 work.

Boards saved at `output/vol-32/blackwood_raw_alns_seed{2,4}_456.json`.

### 4. Unsat-clause-propagator scaffold for vol-33

- Rust loader binary: 540 MB binary loaded in 1.36s, lookup 238 ns/placement.
- Captured all 67M unsat clauses to `output/vol-33/forbidden_all.bin`.
- BUT: vol-32 validation found capiman's (field, piece, rotation)
  encoding doesn't match ours. Vol-33 T1 must reconcile encodings
  first (1-2 hours of careful work). Without this, the propagator
  would prune valid moves.

## Where to start your day

1. **Check the multi-seed ALNS lottery results**:
   `output/vol-32/t8_bw190_lottery/seed*.log`
2. **Read** `vault/sessions/vol-32-blackwood-mrv-discovery.md`
   (the headline finding writeup).
3. **Read** `vault/sessions/vol-32.md` (the full session).
4. If a seed in the lottery breaks 457 → **new cold-start record**.
   Capture the board, push it through strong PT for more.
5. Vol-33 plan at `vault/plans/VOL-33.md` is correct but **T1
   priority should be revised**: the blackwood_raw_MRV finding
   is a higher-EV lever than the unsat-clause-propagator (which
   needs encoding reconciliation first).

## Files

- `vault/sessions/vol-32.md` (235 lines) — full session journal
- `vault/sessions/vol-32-blackwood-mrv-discovery.md` — bonus finding
- `vault/sessions/vol-32-bug-discovery.md` — the original bug evidence
- `vault/plans/VOL-33.md` — next-volume plan
- `output/vol-32/` — all measurement artifacts
- `output/vol-33/forbidden_all.bin` — 540 MB unsat database (CSR)
- `~/.claude/.../memory/project_e2_vol32_*.md` — 4 new memory entries

## Commits

17 commits this volume (from `95978a5` to `1f54e7f`). All on develop
branch. Not pushed to remote (per system rules: don't push without
explicit ask).

## Honest framing

The ML direction at canonical 5-clue 16×16 is **closed**. The
real opportunities found tonight:
- **InsertionOrder under heavy-propagator profiles** (vol-33 T3 already planned)
- **blackwood_raw + MRV cold-start route** (vol-33 priority bump candidate)
- **unsat-clause-propagator** (vol-33 T1, blocked on encoding reconciliation)

This volume produced one significant negative result (refuted ML
claims), one solid positive result (InsertionOrder under heavy props),
and one ALL-NIGHT BONUS positive result (blackwood_raw + MRV → 453
ALNS-5min, well-positioned to break 457).
