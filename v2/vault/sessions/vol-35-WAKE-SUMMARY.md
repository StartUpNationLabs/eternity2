# Vol-35 wake-up summary (2026-05-14 ~14:30)

Read this when starting the next session.

## 🚨 CRITICAL: pin_hints duplicate-piece bug discovered + fixed

**Mid-volume finding**: `vanilla_fast --pin-hints` (vol-32+) wrote
snapshots/saves that filled canonical hint positions WITHOUT checking
if the hint piece was already placed elsewhere. Result: duplicate
pieces (typically 180×2 and/or 248×2) in saved boards.

**Impact**:
- Vol-34's claimed "457 record-ties" (×2 boards) — INVALID. Retracted.
- Vol-35's early claimed "family-255 457 basin" (×3 boards) — INVALID. Retracted.
- 221/225 vol-35 sweep snapshots had duplicates.
- All vol-32 multi-thread `vf_8t_5min.tN.json` partials had duplicates.

**Lucky escape**: vol-32's `vanilla_fast_5min_best.json` (single-thread
save) happened to be clean. So vol-32's 458 RECORD_BREAK and the
blackwood_mrv 457s stand cleanly.

**Fix shipped** (commit `1f5ebef`): 3 pin_hints save paths in
`vanilla_fast.rs` now check `already_placed: HashSet<u16>` before
filling. New saves are clean.

## Current verified record state

| Score | Board | Source |
|---:|---|---|
| 458 | vol-32 RECORD_BREAK_458 | vol-32 vanilla_fast → ALNS |
| 458 | vol-35 deep458 reproduce | vol-35 same partial, different seed |
| 457 | vol-32 blackwood_mrv seed7 | vol-32 |
| 457 | vol-32 blackwood_mrv seed10 | vol-32 |
| 457 | vol-32 blackwood_mrv seed4-30m | vol-32 |
| 457 | vol-35 deep458 full seed5 (3 hints) | vol-35 |
| 457 | vol-35 deep458 diverse seed5 (3 hints) | vol-35 |

**458 record holds.** 7 valid record boards total (2×458 + 5×457).

## Vol-35 work summary

1. **vanilla_fast generalised** to runtime puzzle size — kept fast
   path as `vanilla_fast` (hardcoded N=16, ~71M pp/s) AND added
   runtime-N variant `vanilla_fast_n` (~54M pp/s at 16×16).
2. **landscape_explorer** bin (vol-34 work) for cross-size landscape
   mapping. Probed 4×4/4c, 6×6/5c (×1000), 8×8/5c, 10×10/8c, 12×12/8c,
   16×16/22c. **10×10/8c is the smallest puzzle showing clear basin
   clustering** under naive ALNS-from-random (FDC r=-0.105, 6 pairs
   at H≤25).
3. **Thread-id-offset sweep**: vanilla_fast at offsets {0..450} ×
   5min. Found 46 productive thread_ids → 46 basin families (vs 5
   from offset 0). BUT all snapshots were buggy → re-running with
   fixed binary (in flight).
4. **deep_458_basin_lottery**: 48 ALNS runs from vol-32's clean
   `vanilla_fast_5min_best.json` partial. Results:
   - 1 × 458 (byte-identical to vol-32 458, hit rate 2.1%)
   - 2 × 457 (NEW valid, 3/5 hints, same broader 458 basin)
   - 2 × 456, 8 × 455, 6 × 454, ...
5. **escape_457_lottery**: 5 record reps × 4 seeds × 3min ALNS. ALL
   20 runs stayed at 457 — confirms 457 attractor is ALNS-locked.

## Currently in flight

`sweep_v3` (started 14:31): re-running the 10-offset sweep with the
bug-fixed binary. ETA ~15:21. Then plan re-lottery on the new clean
snapshots.

## Key takeaways for vol-36

1. **ALWAYS run `ml/verify_records.sh`** which now checks piece-uniqueness.
2. The 458 record is reproducible (1/48 hit rate from the right partial).
3. The 458 basin family also contains 457 LOs (4/48 = 4.2% hit rate).
4. To break 459: need a fundamentally different basin family with
   score-recoverable ≥ 459. The 46-family sweep didn't find one
   (under post-fix conditions); the original 5-family vol-34 set
   (when re-tested cleanly) might still — to be checked after
   sweep_v3 completes.
5. The pin_hints bug affected EVERY vanilla_fast bin downstream;
   `ml/family255_multi_snap.sh` etc. need re-running on clean snapshots.

## Files of interest

- `vault/sessions/vol-35-pin-hints-bug-retraction.md` — full bug
  story
- `vault/sessions/vol-35-deep458-lottery.md` — vol-32 458 reproduce
- `ml/verify_records.sh` — canonical record-board sanity check
- `output/vol-35/sweep_v3/` — re-probe (in flight) clean snapshots
- `output/vol-35/records/` — verified record boards (post-fix)

## Open items

- Sweep_v3 in flight: 10 offsets × 5min = ~50 min. Re-lottery pending.
- vol-35 still hasn't BROKEN 458 — every attempt either reproduces
  vol-32 458 or stays below.
- The "fitness landscape" question (user-proposed mid-vol-34) is
  still open. 10×10/8c shows clustering; 6×6 doesn't. Canonical
  16×16 shows trimodal Hamming from CP-partial LOs (vol-34
  finding, still valid since that came from `family_lottery` summary
  data, not buggy snapshots — the LOs themselves were ALNS-recovered
  from buggy partials but their relative geometry to each other
  reflects the basin family structure that the SEARCH found,
  modulo the duplicate-pieces — needs re-verification).
