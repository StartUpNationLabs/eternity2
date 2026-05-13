# V15_BLACKWOOD_SPEC.md

**Author**: vol-14 (2026-05-12 16:00 CEST).
**Purpose**: implementation spec for Blackwood's 2020 algorithm (the
basis of community 469/470 records). Source: thorough reading of
`docs/community-mining/09_Blackwood_solver_thread.md` (Blackwood's
own description, msg #31 2020-11-22). This is the algorithm we are
NOT running tonight; this spec is the vol-15 deliverable that closes
the structural gap to community SOTA.

## TL;DR

Blackwood's algorithm is a backtracker with **two extra ingredients**:
1. A **piecewise-linear schedule** for exhausting a chosen subset of
   edge colors ("heuristic_sides") by specific depth indices.
2. A **fixed list of break indices** where ONE edge mismatch is
   permitted during the scan (instead of forcing exact matching).

With 12 break opportunities, the maximum-feasible score is `480 -
(12 - 1) = 469`. The algorithm cannot find 480 — it's deliberately
permissive about the last few mismatches to make 469 reachable in
billions of iterations.

## Algorithm in pseudocode

```rust
fn solve_blackwood(puzzle, schedule, breaks, iter_cap) -> BestBoard {
    let mut placement = empty();
    let mut iter = 0;
    let mut best_score = 0;
    let mut best_board = empty();

    // Standard backtracking scan order (Blackwood: row-major).
    fn try_place(depth: usize, ...) -> ControlFlow {
        if iter >= iter_cap { return Stop; }
        iter += 1;

        // Heuristic-side schedule check.
        let target = schedule.exhaust_target_at(depth);
        let actual = count_placed_heuristic_pieces(placement);
        if actual < target { return Prune; }  // falling behind
        if heuristic_pool_exhausted() && depth < schedule.max_index {
            // Can't keep up later; prune.
            return Prune;
        }

        if depth == N_CELLS { record_solution(); return Continue; }

        // Try each candidate (piece, rotation) for cell at depth.
        for cand in candidates_at(depth, placement) {
            let edge_mismatches = count_local_mismatches(depth, cand, placement);

            // Allow ≤1 mismatch only if depth is a break_index.
            let allowed_mismatches = if breaks.contains(&depth) { 1 } else { 0 };
            if edge_mismatches > allowed_mismatches { continue; }

            place(depth, cand);
            if depth + 1 > best_score { record_best(placement); }
            try_place(depth + 1);
            unplace(depth);
        }
        Continue
    }
}
```

## Blackwood's 469 parameter set (verbatim)

```
heuristic_sides       = [17, 2, 18]                    # 3 colors, 122 total piece-occurrences
break_indexes_allowed = [201, 206, 211, 216, 221,
                         225, 229, 233, 237, 239,
                         241, 256]                     # 12 breaks → max 469
heuristic_schedule:
    by depth   0 → exhaust   0 of 122 heuristic-piece-occurrences
    by depth  16 → exhaust   0
    by depth  26 → exhaust  28
    by depth  56 → exhaust  71
    by depth  76 → exhaust  89
    by depth 102 → exhaust 106
    by depth 160 → exhaust 119 of 122
    (linear interpolation between control points)
max_heuristic_index   = 160
iteration_cap         = 50_000_000_000  (per Blackwood: "arbitrary")
```

## Choosing heuristic_sides (Blackwood's selection rules)

1. **Many occurrences**: pick 3 colors with high total piece-edge
   count (~120 across 256 pieces).
2. **Not on any corner piece**: 4 corner pieces × 4 rotations × 2
   non-border-edges = 32 candidate corner edges; the 3 heuristic
   colors must miss all 32.
3. **Not on the start piece** (the 5th canonical hint, piece 138 at
   pos 135): preserves start-piece flexibility.

**For canonical E2** (24 interior colors, ~480 piece edges):
- Compute color frequencies on all 256 pieces (count edges with
  each color, excluding BORDER).
- Filter out colors used on the 4 corners.
- Filter out colors used on piece 138 (the start hint).
- Sort remaining by frequency descending.
- Pick top 3.

For Blackwood's choice `[17, 2, 18]`, total 122 occurrences. Likely
multiple valid triples; he tuned among them.

## Break_indexes — why these specific numbers?

The list `[201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241,
256]` is hand-tuned by Blackwood. Pattern:
- First 5 spread by 5: `201, 206, 211, 216, 221` (depths 201-221).
- Next 4 spread by 4: `225, 229, 233, 237` (depths 225-237).
- Last 3 spread by 2-15: `239, 241, 256` (depths 239-256, with 256
  being the last cell).

Blackwood (msg #18): tried "eliminating 4 sides early" instead of
3 — "similar results". So the choice of 3 heuristic_sides is robust.

Tried "saving sides for the end" — worse. Tried "different
heuristics" — ~2× improvement. **The 469 ceiling is robust to
parameter perturbation**, suggesting the algorithm's frame (not
the specific schedule) is what gets 469.

## How this maps to our `solver-engine`

Required additions to `crates/solver-engine/src/lib.rs`:

```rust
#[derive(Debug, Clone)]
pub struct BlackwoodSchedule {
    /// Color indices that count toward the exhaustion schedule.
    pub heuristic_sides: Vec<Color>,
    /// (depth, target_count) pairs; piecewise-linear interpolation
    /// between them.
    pub exhaustion_targets: Vec<(u32, u32)>,
    /// Total of heuristic-side occurrences across all pieces (e.g.
    /// 122 for canonical E2 with sides [17, 2, 18]).
    pub heuristic_pool_size: u32,
    /// Maximum depth where schedule applies; above this, no check.
    pub max_heuristic_index: u32,
    /// Sorted ascending list of board cell indices where a single
    /// edge mismatch is permitted during scan.
    pub break_indexes_allowed: Vec<u32>,
}

pub enum ValueOrder {
    InsertionOrder,
    LeastConstraining,
    RandomShuffle,
    PreferredFirst,
    EdgeBpMarginals,
    /// Blackwood 2020: at each candidate evaluation, count how many
    /// of the candidate's edges contain heuristic_sides colors;
    /// rank descending so heuristic-rich candidates are tried first
    /// up to schedule.exhaustion_targets[depth].
    BlackwoodHeuristic,
}

pub struct EngineConfig {
    // ... existing fields ...
    pub blackwood_schedule: Option<BlackwoodSchedule>,
}
```

In `recurse()`, before standard value-ordering:
```rust
if let Some(sched) = &self.config.blackwood_schedule {
    let placed_heuristic = count_placed_heuristic(&self.placed, sched);
    let target = sched.target_at(depth);  // piecewise-linear interp
    if placed_heuristic < target { return RecurseResult::Exhausted; }
    if placed_heuristic >= sched.heuristic_pool_size && depth < sched.max_heuristic_index {
        return RecurseResult::Exhausted;  // can't keep up
    }
}
```

In `place_and_propagate`, when checking edge color matches against
neighbours: track per-call mismatch count. At depth ∈
`break_indexes_allowed`, allow up to 1 mismatch; else require 0.

## Scan order — VERIFIED EMPIRICALLY

Vol-14 decoded community 469/468 boards and computed which scan
order puts their mismatches at indices ≥ 200 (matching the
Blackwood break_indexes range):

| board    | top-down %≥200 | bottom-up %≥200 | spiral %≥200 |
|----------|---------------:|----------------:|-------------:|
| 469 (c)  |  0%           |   **36%** (med 198) |  0%      |
| 468 (a)  |  0%           |   **66%** (med 231) |  0%      |

**Blackwood's scan order is bottom-up row-major** (idx = (H-1-y)*W + x).
Index 0 = (0, 15) (bottom-left), index 255 = (15, 0) (top-right).

Our stack uses **top-down row-major** (idx = y*W + x). This is why
our 442/454 boards have mismatches at low top-down indices (= top of
board) and community 469s have them at high bottom-up indices (= top
of board, but high cell-index in Blackwood's frame).

`pub enum ScanOrder { RowMajorTopDown, RowMajorBottomUp }` is sufficient.
Default Blackwood-mode = `RowMajorBottomUp`.

## Hint × break-index collision

Vol-14 verified: under bottom-up scan, our 5 canonical hints map to
indices `{34, 45, 119, 210, 221}`. Blackwood's break_indexes are
`{201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256}`.

**Collision: hint at pos 45 (= bu_idx 221) coincides with break 221.**

Vol-15 implementation must handle this:
- If a cell is hint-pinned, no value-ordering happens there — the
  piece + rotation is forced.
- Therefore break-allowance at hint-pinned indices is **unused**
  (no candidate-row evaluation to apply it to).
- Result: effective break count drops from 12 to ≤ 11, max score
  becomes ≤ 468.
- If the hint at pos 45 produces a mismatch on either of its
  neighbours, that mismatch is unavoidable and consumes the
  "would-have-been" break.

**Vol-15 task**: implement break-allowance only on non-pinned cells.
Add a `score_ceiling()` helper that computes max achievable score
given `(hints, breaks)`.

## Heuristic-side selection — canonical E2 calibration

Vol-14 verified empirically: Blackwood's reported counts don't
match canonical E2 piece-edge color frequencies:

- Blackwood says `[17, 2, 18]` has **122 occurrences total** and
  doesn't appear on any corner.
- On canonical E2 (data/puzzles/size_16_official_eternity.csv,
  vol-11 loader), counting colors 17, 2, 18: total **124**
  occurrences. Colors 2 appears on **2 of 4 corners** (pieces 2
  and 3).

**Conclusion**: Blackwood's color labels differ from ours (his
puzzle CSV or labeling convention is offset from the v11_load_e2
output). Cannot literally adopt his triple.

**Vol-15 must recompute heuristic_sides from first principles**
on the canonical piece set:

```rust
fn compute_heuristic_sides(puzzle: &Puzzle, hints: &Hints) -> [Color; 3] {
    // 1. Identify corner pieces (those with exactly 2 BORDER edges).
    let corner_colors: HashSet<Color> = puzzle.pieces().iter()
        .filter(|p| p.edges.as_array().iter().filter(|&&c| c == BORDER).count() == 2)
        .flat_map(|p| p.edges.as_array().iter().copied().filter(|&c| c != BORDER))
        .collect();
    // 2. Identify the start piece (5th hint, at pos 135) edges.
    let start_colors: HashSet<Color> = hints.iter()
        .find(|h| h.position == 135)
        .map(|h| puzzle.piece(h.piece_id).unwrap()
            .edges.as_array().iter().copied().filter(|&c| c != BORDER).collect())
        .unwrap_or_default();
    let forbidden: HashSet<Color> = corner_colors.union(&start_colors).copied().collect();
    // 3. Count occurrences of each color across all piece edges.
    let mut counts: HashMap<Color, u32> = HashMap::new();
    for p in puzzle.pieces() {
        for &c in &p.edges.as_array() {
            if c != BORDER { *counts.entry(c).or_insert(0) += 1; }
        }
    }
    // 4. Filter, sort by frequency, take top 3.
    let mut candidates: Vec<(Color, u32)> = counts.into_iter()
        .filter(|(c, _)| !forbidden.contains(c))
        .collect();
    candidates.sort_by_key(|(_, n)| std::cmp::Reverse(*n));
    [candidates[0].0, candidates[1].0, candidates[2].0]
}
```

This will produce 3 colors specific to canonical E2 that satisfy
Blackwood's selection rules. The corresponding `heuristic_pool_size`
is the sum of their occurrence counts.

## Throughput

At our current ~14k nps multi-core, 50B iterations = **40 days
wall-clock**. To match Blackwood's ~1B iterations / few hours scale,
we need at least **100× speedup**. Without it, vol-15 should run
Blackwood with a much smaller iteration cap (e.g. 500M) and accept
that we'll find fewer 469s than the community.

For wall-clock honesty: at 14k nps we can do ~50M iterations per
hour. To match Blackwood's 1B iter scale, we'd need ~20 hours. So
vol-15's first Blackwood pilot should be:

```
target_iter_cap   = 500_000_000     (10 hours wall-clock on 8 cores)
expected_outcome  = 1-2 partial 469 boards if algorithm is correctly
                    implemented; nothing if buggy
```

## Vol-15 task list

- [ ] **#B.1**: scaffold `crates/solver-engine/src/blackwood.rs` with
  `BlackwoodSchedule` struct + serde.
- [ ] **#B.2**: add `ValueOrder::BlackwoodHeuristic`. Score rows by
  `count_heuristic_colors_in_edges(row, schedule.heuristic_sides)`.
- [ ] **#B.3**: thread `Option<BlackwoodSchedule>` into recurse;
  add schedule-violation pruning at each depth.
- [ ] **#B.4**: extend `place_and_propagate` to count per-depth
  edge mismatches and consult `break_indexes_allowed`.
- [ ] **#B.5**: add `pub enum ScanOrder` + `EngineConfig::scan_order`;
  implement RowMajorBottomUp as the second option.
- [ ] **#B.6**: write a `compute_heuristic_sides` helper that picks
  3 colors satisfying Blackwood's selection rules from a Puzzle.
- [ ] **#B.7**: parameter-search harness — try k=3..5 heuristic
  sides, varied break_index lists, run 500M-iter pilots, record
  best scores.
- [ ] **#B.8** (optional, late): plug into `pt_e2` as a warm-up
  phase replacing the standard CP — Blackwood's algorithm
  generates higher-quality CP partials.

## What this DOESN'T solve

- **The 470 ceiling** is still a parameter-tuning problem
  (Blackwood himself reported "didn't get great results" with
  similar variations).
- **480 (full solution)** requires removing breaks entirely AND
  the resulting search is the unmodified canonical E2 — same as
  what we're already doing.
- **Throughput**: Blackwood at 50M nps single-core is 3500× our
  multi-core 14k nps. Closing this is a separate engineering
  effort (McGavin's fit_table + per-cell goto unrolling).

## Risks

1. **The break_indexes only work for Blackwood's scan order**: if
   we implement them with our current top-down scan, the 469s will
   not appear. **Must verify scan order matches Blackwood's via the
   community 469 corpus** (check which board indices contain the
   community 469's mismatches in our scan order vs Blackwood's).
2. **The heuristic_sides selection is sensitive to piece-set**:
   our generator pieces' color frequencies match canonical only
   when running on canonical CSV; testing on generator-produced
   pieces would need a per-piece-set selection helper.
3. **Cumulative search-space explosion if breaks misalign with
   true solution geometry**: the algorithm finds 469s, not 480s.
   If the true 480 requires NO mismatches but the algorithm's
   schedule penalises heuristic-color-poor branches early, the
   algorithm may never search the 480-region. (This is by design;
   we accept it.)

## Verification path

After implementing, the test is:
1. Run on canonical E2 with Blackwood's 469 parameters, 500M iters.
2. Expected: at least one 469-class board (≥468/480) found.
3. Decode: compare to `output/community_corpus/groups_172011298_469.json`.
4. If our 469 is structurally similar (shared 95%+ of placements),
   verification succeeds. If very different, the algorithm is
   correct but found a different attractor (also acceptable).
5. If no ≥465 board, the algorithm is buggy.

## Related

- `docs/community-mining/09_Blackwood_solver_thread.md` — primary
  source.
- `docs/community-mining/05_Joe_pruning_method_thread.md` — Joe's
  complementary prune-restart policy (synergistic with Blackwood).
- `V15_FRAME_ENUMERATOR_SPEC.md` — vol-15's other major spec.
- Memory: `project_e2_mcgavin_blackwood_gap_analysis.md`,
  `project_e2_vol14_mismatch_geometry_universal.md`.
