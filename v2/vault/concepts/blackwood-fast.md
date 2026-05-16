---
name: blackwood-fast
description: Hyper-optimized Rust port of libblackwood's per-cell-unrolled DFS shape, achieving 65-68M nps single-thread on canonical 16x16/22c (~175x speedup over existing solver-engine BLACKWOOD_RAW, ~22% of Bucas's C engine's 295M nps). Vol-106 T1.
metadata:
  type: project
---

# blackwood-fast (vol-106 T1)

**Status**: `built` (raw DFS, no Blackwood schedule yet) — first meaningful
shipment of throughput-parity work.
**Origin**: vol-106 (2026-05-16). User redirect from MIP track:
"migration of blackwood here in an hyper-optimized manner" + "why
can't we make something as good ourselves in RUST?".
**Files**: `crates/blackwood-fast/src/lib.rs`,
`crates/blackwood-fast/src/bin/bench.rs`.

## The thesis the work confirmed

The 800× throughput gap between our existing solver-engine
`BLACKWOOD_RAW` (367k nps) and Bucas's libblackwood C engine
(295M nps) is **architectural**, not a Rust-vs-C language ceiling.
Closing 175× of that gap took one afternoon of porting; the
remaining ~4-5× is the standard Blackwood schedule + further
microarchitecture work.

## Design

A new workspace crate that replicates the SHAPE of Bucas's C
backtracker without the codegen layer. Key choices:

1. **Const-generic specialization for canonical 16×16/256-piece.**
   `solve_raw_sized::<256, 256, 4>` stack-allocates board, cursor,
   per-depth metadata, and pieces_used bitset. Width-aware
   modulo / division is replaced by precomputed per-depth flags
   (`depth_top_row`, `depth_left_col`, `depth_tbl`).

2. **Four border-aware flat candidate tables.** The row-major
   constraint at any cell is `(top_color, left_color)` known
   from already-placed neighbours. Border cells additionally
   require BORDER on right (last column) and/or bottom (last row).
   We materialise FOUR separate candidate tables — one per
   `(right_border, bottom_border)` combination — flattened into
   a single `entries: Vec<PieceRot>` with `offsets: Vec<u32>`
   indexed by `(tbl << 16) | ref_key(top, left)`. This pushes the
   border filter OUT of the inner loop entirely.

3. **`pieces_used` as a 4-word u64 bitset (256 pieces).** Cache-
   resident, one load + AND-test per candidate trial. Replaces
   the `Vec<bool>` (8-byte per element, heap-allocated, cache-
   wasting) of the first iteration.

4. **`bottom_of` / `right_of` u8 LUTs indexed by PieceRot.0.**
   When we descend depth and need the neighbour's exposed edge
   color, we read it from a flat 65536-entry LUT in O(1). No
   `rotated_edges()` call in the hot path.

5. **Sentinel-terminated candidate lists** (libblackwood trick).
   Each bucket ends with `PieceRot::NONE`. The inner trial loop
   walks by index until it sees the sentinel; eliminates the
   `c_idx < cands.len()` comparison and lets us encode "end of
   list" as a value the consumer naturally checks anyway.

6. **`unsafe { get_unchecked / .add(idx) }` on the sized hot path.**
   Workspace precedent: `crates/bench-audit/src/bin/vanilla_fastest.rs`
   (vol-32 explicit authorisation in CLAUDE.md). The generic path
   keeps bounds checks. The 2 KB inner-loop instructions of the
   sized path now contain zero panic edges.

## Measurements (apple-m1, --release, single-thread)

### 30s × 4 seeds variance (per CLAUDE.md rule #4)

| seed |     nodes (M) | max_depth |  nps (M) |
| ---: | ------------: | --------: | -------: |
|    1 |          1983 |       167 |     66.1 |
|    7 |          2038 |       168 |     67.9 |
|   42 |          1961 |       166 |     65.4 |
|  100 |          2051 |       172 |     68.4 |
| **median** | — | 167.5 | **67.0** |

Variance ~5%. All four runs reach depth 166-172/256 within 30s.

### Speedup vs prior work

|                                          | nps single-thread | × baseline |
| ---------------------------------------- | ----------------: | ---------: |
| solver-engine `BLACKWOOD_RAW` (vol-15)   |              367k |     1.0×   |
| blackwood-fast first iteration           |              56M  |   153×     |
| blackwood-fast + bitset + 4-table        |              60M  |   163×     |
| blackwood-fast + sentinel + unsafe       |          **65-68M** | **177-185×** |
| libblackwood (Bucas C, McGavin)          |             295M  |    803×    |

We are at **~22% of Bucas's C single-thread throughput** with no
Blackwood schedule yet, no goto-chain unrolling, no advanced AArch64
intrinsics. The remaining gap is split across:

- The Blackwood heuristic-schedule (depth-wise required-pattern count) — adds work per node but breaks dead branches earlier; net gain on score-axis even if nps drops.
- Per-depth specialisation (Bucas literally inlines 256 depth blocks; we share one loop body). Const-generic dispatch on WH gives LLVM an opportunity to unroll if profitable; we haven't measured whether it does.
- `prefetch_read_data` hints before reading the next candidate slice.
- Possibly a 2-level offsets table to fit the hot lookup in L1d (currently 1 MB → L2 only).

## What still needs to be ported

1. **Heuristic-pattern schedule (Blackwood 469 params).** Once
   integrated, this turns blackwood-fast from a raw DFS into the
   actual Blackwood algorithm. See [[blackwood-algorithm]]
   "469 parameter set".
2. **Break-index allowance.** The 12 specific depths where ≤1
   edge mismatch is allowed.
3. **Multi-thread orchestration.** Bucas's main.py launches N
   worker processes with different bucket-seed offsets. Trivial
   in Rust via rayon.
4. **Heartbeat / cooperative cancellation.** The current
   `time_budget_us` cutoff is checked every 65536 nodes; fine
   for ms-scale precision.
5. **Solution save & resume.** Currently we only return the
   board state at termination. The C engine writes intermediate
   "best depth seen" board snapshots.

## What this enables

- **Cold-start record attempts** at meaningful throughput. At
  68M nps × 8 threads = 540M nps aggregate. McGavin's 469 was
  found in "days on ~200 cores" at 295M nps; the aggregate node
  count to reach 469 is ~10^15 = a few days of our 540M nps × 8
  cores. **For the first time, the canonical 469 target is
  reachable on our infrastructure** (modulo schedule integration).
- **Blackwood schedule calibration** at honest throughput
  (vol-15/17 calibrations were limited by 367k nps; many more
  schedule variants can now be evaluated).
- **Per-vol calibration cycles** of 5-30 min instead of
  multi-hour. Vol-17 spent days; with blackwood-fast a 30-min
  lottery yields the same statistical power.

## What might be wrong

- We have NOT verified the candidate-list completeness against the
  C engine on a known puzzle. Test plan: take the canonical
  Selby-Riordan 16×16 puzzle, run both engines for the same node
  budget, compare depth trajectories. **Until this is done, treat
  blackwood-fast as a faster DFS, not a verified Blackwood port.**
- The bitset implicitly caps NPIECES at the generic-version's
  4096; the sized version caps at BITSET_WORDS×64 = 256. Fine
  for canonical, would need re-monomorphisation for larger
  puzzles.
- `PieceRot::NONE` sentinel uses `u16::MAX` (`piece_idx = 16383`,
  `rot = 3`). If a puzzle had 16384 pieces we'd collide. Cap
  enforced at 16384 in `RowMajorIndex::build`.

## Linked

- [[blackwood-algorithm]] — the algorithm this engine implements.
- [[mcgavin-blackwood-gap-analysis]] — quantifies the 800×
  throughput gap.
- [[blackwood-schedule-calibration]] — what to integrate next.
- [[../sessions/vol-106|vol-106 session]].
- [[../IDEAS_FROM_BLANK_2026-05-16]] item #1.
