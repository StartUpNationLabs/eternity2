---
name: sigma-break-runbook
description: "Vol-125 runbook for SIGMA-BREAK (bidirectional meet-in-the-middle) experiments on canonical Eternity II. Designed for a 32 GB / 10-core machine; describes the experiments to run, expected memory/compute, and the success criteria."
metadata:
  type: project
---

# SIGMA-BREAK runbook — what to run on the 32 GB / 10-core machine

## Background

The W14 super-block alphabet decomposes 16×16 canonical Eternity II into an
8×8 super-grid where each super-cell is a 2×2 piece block. Hint super-cells
are pre-filtered for hint compliance.

## Memory reality check (2026-05-18)

On the 16 GB machine, the original `sigma_break_row0` (which stores a
HashMap<south_profile, count>) **OOM'd at 8.9 GB after 3+ minutes**.
That's ~280M distinct south-edge profiles before crash.

This means even on 32 GB:
- The "store all row-0 states" approach: **likely fits if row-0 state count
  is ≤ 10^9** (each state needs ~56 bytes), but barely.
- Full R_MID=4 (rows 0-3 stored): **DOES NOT FIT in 32 GB** if state count
  is ≥ 10^10 (which is plausible for the W14 alphabet).

**Pragmatic conclusion**: pure exhaustive bidirectional won't work; we will
NEED beam search OR a different decomposition (e.g., column-pair, quadrant)
with smaller meeting plane.

The 32 GB machine helps because:
1. Row-0 store fits (sigma_break_row0 binary as-is)
2. Beam search with K=10^7 states fits (10^7 × 56 bytes = 560 MB)
3. Multi-thread join phase has 10× more cores
4. We can run multiple decompositions in parallel (row/column/quadrant)

BB&B (forward DFS with HK alldiff propagation) reaches depth 40 of 64
super-cells before stalling. The bidirectional meet-in-the-middle approach
(SIGMA-BREAK) splits the problem: enumerate top half (rows 0-3) and bottom
half (rows 4-7) independently, then join on the row-3/row-4 boundary where
super-edges and pieces must match.

## Prerequisites on the bigger machine

1. **Rust toolchain** (any recent stable).
2. **Code**: clone `develop` branch of the eternity2 repo at the same path
   structure (`v2/...`).
3. **W14 alphabet on disk**: `v2/output/vol-125/w14/alphabet/sc_XX_YY.bin`
   (64 files, ~5 GB total). If not present, generate via:
   ```bash
   cd v2
   cargo build --profile bench-fast -p eternity2-bench-audit --bin super_block_enum
   ./target/bench-fast/super_block_enum --out-dir output/vol-125/w14/alphabet
   ```
   Takes ~3 minutes.

4. **Build SIGMA-BREAK binaries**:
   ```bash
   cargo build --profile bench-fast -p eternity2-bench-audit --bin sigma_break_row0_count
   cargo build --profile bench-fast -p eternity2-bench-audit --bin sigma_break_meet
   cargo build --profile bench-fast -p eternity2-bench-audit --bin sigma_break_row0
   ```

## Experiments to run

### Experiment 1: sigma_break_row0_count (cheap diagnostic)

**Goal**: count internally-valid row-0 super-block sequences. This tells us
the FORWARD state count after one row, which is the inner loop of SIGMA-BREAK.

**Resources**: < 1 GB RAM, single-thread, expected runtime: 5-60 minutes
(might be hours if count is huge; cap at 10^12 to avoid running forever).

**Command**:
```bash
./target/bench-fast/sigma_break_row0_count > /tmp/sigma_break_row0_count.log
```

**Expected output**: `Row-0 internally-valid count: <number>`.
- If count < 10^6: forward enumeration of rows 0-3 is FEASIBLE (each row
  multiplies by similar factor; row 0-3 might be 10^24 — too much). Bandwidth
  limit needed.
- If count > 10^9: forward enumeration is INFEASIBLE without aggressive
  pruning; pivot to a different decomposition.

**Decision rule**:
- count < 10^7 → proceed to experiment 2 (full meet-in-the-middle row 0-1)
- 10^7 ≤ count < 10^9 → use beam-search variant (sigma_break_beam, to be built)
- count ≥ 10^9 → pivot: row-based decomposition is too wide; try
  column-based or quadrant-based decomposition instead

### Experiment 2: sigma_break_meet (forward = row 0, R_MID=1)

**Goal**: hash forward row-0 states by south-edge profile + piece-bitset.
This tells us the DISTINCT south-edge profile space size at row 0, which is
the meeting plane for any meet-in-the-middle.

**Resources**: 8-32 GB RAM (the HashMap grows with distinct profiles),
single-thread, runtime: similar to experiment 1.

**Command**:
```bash
./target/bench-fast/sigma_break_meet > /tmp/sigma_break_meet.log
```

**Expected output**:
- `forward states: <N>`
- `distinct south-edge profiles: <K>`

**Decision rule**:
- K < 10^4: the meeting plane is small enough for fast lookups; proceed to
  experiment 3 (forward = rows 0-1, backward = rows 6-7, R_MID=2)
- K > 10^6: the meeting plane is too wide; the join step becomes the
  bottleneck. Consider hashing on a coarser key (e.g., just the south-edge
  COLORS, not pairs).

### Experiment 3: full bidirectional with R_MID=4 (the real algorithm)

**Goal**: enumerate forward rows 0-3 and backward rows 4-7, meet at the
row-3/row-4 boundary. If they meet on at least one (south=north, pieces
disjoint) pair, we have a 480-piece solution.

**Resources**: 16-32 GB RAM, multi-threaded (use 10 cores), runtime:
hours to days.

**Implementation NOTE**: the current `sigma_break_meet` binary only does
forward at R_MID=1. The R_MID=4 version needs:
1. Forward enum of rows 0-3: hash by (south-edge profile at row 3,
   piece-bitset after 4 rows). Expected state count: depends on row-0
   experiment; could be 10^12+.
2. Backward enum of rows 4-7: hash by (north-edge profile at row 4,
   piece-bitset after 4 rows from bottom). Similar count.
3. Join: for each backward state, look up forward states by north-edge =
   backward's south, check piece-disjoint, emit join.

**To build R_MID=4**:
- Extend `sigma_break_meet.rs` to take r_mid as a CLI arg.
- Add the backward enumeration symmetric to forward.
- Add the join phase.

**Decision rule**:
- If a 480 solution is found: stop, save board, claim record.
- If no join exists: 480 doesn't exist with this W14 alphabet decomposition
  AND the puzzle has no 480 solution (assuming bidirectional is exact, which
  it is if we keep ALL states).
- If memory blows up before completing: switch to beam-search variant.

### Experiment 4: beam-search SIGMA-BREAK

If experiment 3 OOMs, switch to beam search:
- Keep only the top K states per south-edge profile (where K is e.g. 10^6).
- The top-K heuristic could be: max free piece count, max edge-color rarity,
  or random.

This is INCOMPLETE (may miss solutions) but tractable. With K = 10^7 and
32 GB RAM, we cover much more state space than the depth-40 forward DFS
which exhausts after ~5000 nodes.

## What success looks like

The algorithm finds a 256-tuple of (piece_id, rotation) assignments to all
256 cells of the 16×16 board such that:
- All adjacent edges match in color.
- All 5 canonical hints are at the correct positions with correct rotations
  (this is automatically enforced by the W14 alphabet pre-filtering).
- All 256 pieces are used exactly once.

The output is dumped to `output/vol-125/SOLUTION_480_sigma_break.json` in
the same format as other E2 solutions:
```json
{
  "placement": [
    {"pos": 0, "piece_id": 1, "rotation": 3},
    ...
  ],
  "source": "sigma_break",
  "matched": 480
}
```

Then `rescore_board` should be run to verify independently.

## Threat model: what could go wrong

1. **State count explodes**: forward states ≥ 10^15 → not enumerable. Mitigation:
   beam search, or use a sparser decomposition.
2. **480 doesn't exist**: bidirectional meets nowhere. This is itself a major
   research finding (would refute the long-held assumption that canonical
   Eternity II has a solution).
3. **Memory pressure**: the HashMap of forward states grows with state count.
   Mitigation: switch to (a) on-disk hashing via memmap, (b) Bloom filter
   pre-screen.

## What to bring back from the bigger machine

- The full SOLUTION_480_sigma_break.json (if found)
- Or: the empty-result log showing the bidirectional meet refuted 480
  existence on this decomposition
- Or: state counts at each row depth, so we know the actual size of the
  state space
- Update this brouillon with results

## Linked

- [[sb-ble-invention]] — earlier sketch of bandwidth-limited row enumeration
- [[strict-hint-slot-rotation-fix]] — why W14 alphabet is correct
- [[v125-bbb-progression]] — why BB&B plateaus at depth 40
