# "EternityII Solver" — topic 76623077 (34 msgs, 2020-09 → 2021-02)

The canonical **Joshua Blackwood solver release thread**. This is where
the 470-record solver was first made public and explained.

## Blackwood's algorithm in full (msg #31, 2020-11-22)

### Core idea

A backtracker that **deliberately exhausts a chosen subset of edge
colors early** ("heuristic sides"), then permits a fixed schedule of
mismatches ("breaks") at chosen depth indices.

The mismatches are what turn this from a true backtracker into a
high-score-partial finder.

### Parameters for 469

```
heuristic_sides       = [17, 2, 18]
break_indexes_allowed = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256]
                        (11 + 1 = 12 break opportunities → 469/480)
heuristic_array       = piecewise-linear color-exhaustion target
                        by index   0 → exhaust   0 of 122
                        by index  16 → exhaust   0
                        by index  26 → exhaust  28
                        by index  56 → exhaust  71
                        by index  76 → exhaust  89
                        by index 102 → exhaust 106
                        by index 160 → exhaust 119 of 122
max_heuristic_index   = 160
```

The 122 = 24 + 50 + 48 (counts of colors 17, 2, 18 across all piece
edges in the 256 pieces). The 94 = number of pieces containing at
least one heuristic color (some pieces have 2 or 3).

### Proposed parameters for 470 (Blackwood, Nov 2020 — never confirmed)

```
heuristic_sides       = [13, 16, 10]
break_indexes_allowed = [197, 203, 210, 216, 221, 225, 229, 233, 236, 238]
                        (10 break opportunities → 470/480)
heuristic_array       = same shape, different counts
```

Choice rationale (Blackwood's own words):
- These sides have "lots of overlap" — easy to burn early.
- "Aren't used in any of the 4 corners" — preserves corner options.
- "Aren't used in the start piece" — preserves start-piece flexibility.

### Verification process

Counter `solve_index_counts` tracks how many times each board index is
reached. **Key tuning loop**: vary heuristics, check if **board index
249+ is reached at least as often as a previous baseline**. Don't get
"stuck anywhere" — analyze cumulative time per index.

### Stopping criterion

Original 469 code used `50,000,000,000` as iteration cap before restart.
**Blackwood (msg #22): "arbitrary - I tried a few big numbers (over 1B)
and they didn't make too much of a difference."** A 470 attempt would
likely need this much higher.

## Jef Bucas's optimizations (msgs #21, #32)

Bucas rewrote the C# code in **C with Python-generated unrolled code**
(`libblackwood`, github.com/jfbucas/libblackwood). **~2× speedup** vs
Blackwood's Mono C#:

Mono C#: 4110 L1-dcache loads/sec, 1274 branches/sec, 2.31 instr/cycle,
136.7 sec wall.

Rewritten C: 3325 L1-dcache loads/sec (more cache-friendly), 1083
branches/sec, 1.30 instr/cycle, **59.4 sec wall** = **2.3× faster**.

L1 cache miss rate went from 0.33% to 0.09% (Bucas's redesign improved
memory locality 3.6×).

## Six 469s found (Nov 2020)

After releasing the solver, the community found **six 469s within 3
weeks**:
- JBlackwood+Jef_469_a, _b, _c, _d, _e, _f, _g (7 found Nov 16-19)
- JBlackwood+PMcGavin_469 (McGavin running Blackwood)
- JBlackwood+PMcGavin_469_a (Carlos Fernandez's swap-improvement of
  McGavin's)

So **the 469-attractor is reachable in days from a clean Blackwood
run** (468-tuned parameters, no extensive optimization).

The **470** (Mar 2021) came from Blackwood himself with retuned
parameters during a "Thanksgiving holiday" tune (mentioned msg #31).
He never explicitly published the 470's exact parameters in this
thread — they're in his code on GitHub.

## What Blackwood tried that DIDN'T work

From msg #18:
1. **Eliminating 4 sides early** instead of 3: similar results.
2. **Saving sides for the end**: worse.
3. **Different heuristics**: ~2× improvement (marginal).
4. **SAT solvers** (kissat, cryptominisat, OR-tools): "didn't get
   great results."
5. **GPU**: tried but no improvement.
6. **Caching all pre-solved 2×2s**: tried, didn't help.

**The 470 ceiling is real even with Blackwood's algorithm family.**

## What this changes for vol-9

- **Blackwood's exact 469-parameter set is on record above**. Vol-9
  can adopt the schedule wholesale — no parameter search needed for
  the 469 baseline.
- **Bucas's C-generated unrolled code (libblackwood) is ~2× faster
  than Blackwood's C#**. If vol-9's Rust solver isn't already at the
  300M nodes/sec McGavin level, **studying libblackwood's per-cell
  goto unrolling is the right inspiration**.
- **The 470 attempt parameters are known** (msg #31 proposal) but
  Blackwood himself reported "didn't get great results" with similar
  variations. The 470 success came from extensive parameter tuning,
  not architectural changes. Suggests vol-9 should **build a
  parameter-sweep harness around the Blackwood schedule** rather
  than reinvent the algorithm.

## Carlos Fernandez's "exchange piece" post-processor (msg #29)

Carlos's program takes a 469 and **tries one-piece swaps** to find
another 469 with one piece different. He uses this to *enlarge the
known-469 archive*. The thread shows **multiple 469s differ by a
single piece swap** — i.e., they share the same essential structure.

This is **structural evidence the 469-attractor has a narrow basin**:
many local-optimum 469s exist within hamming-distance 1 of each other.
**Vol-7 MAP-Elites should capture this and confirm 469s form a
single cluster, not a dispersed set.**
