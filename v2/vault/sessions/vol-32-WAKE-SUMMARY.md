# Vol-32 wake-up summary (2026-05-14 ~01:30)

Read this first.

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
are stable local optima under winning5 ALNS. Breaking 456→457
requires: different ALNS ops (k=80 ConflictDriven, HingeDestroy,
Houdayer-on-ALNS), PT with higher temperatures, or vol-22's
basin-escape recipe (bound-ascent + Hungarian + ALNS over hours).

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
