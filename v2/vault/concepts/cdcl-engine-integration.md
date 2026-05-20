---
name: cdcl-engine-integration
description: addresses the concrete Rust solver-engine refactor for the vol-57 build.
status: unbuilt
metadata:
  type: concept
---
# CDCL no-good learning — solver-engine integration design

**Status**: `design` — vol-56 T6 (2026-05-15).
**Origin**: companion to [[cdcl-no-good-e2]] (math design); this page
addresses the concrete Rust solver-engine refactor for the vol-57 build.

## Refactor goals

Add CDCL no-good learning to solver-engine without:
- Breaking the existing engine profiles (gacolor, AC-3, NS-1 etc.).
- Regressing performance on non-no-good profiles (must be opt-in).
- Compromising the bitset-based AC-3 hot path.

## Where AC-3 lives now

`crates/solver-engine/src/lib.rs`:
- `propagate_ac3()` at line 1503 — main AC-3 fixpoint loop.
- Uses bitset-style domains (`domain_bits`, `ac3_present`).
- Maintains `ac3_count[pos][side][color]` incrementally via
  `ac3_dirty_list`.
- Wipeout sites at lines 1392, 1450, 1736 — increments
  `stats.domain_wipeouts` and emits `DomainWipeout` event.

The hot path is highly optimized. Vol-25 spent significant effort on
this (3-week perf push). **A cause-tracking refactor must NOT
degrade the AC-3 hot path** for profiles that don't use no-good
learning.

## Architectural choice

Two options:

### Option A — separate cause-tracking AC-3 path

Maintain TWO AC-3 implementations:
1. `propagate_ac3_fast` (current, no cause tracking).
2. `propagate_ac3_with_causes` (new, slower, tracks per-row removal causes).

Engine config flag `enable_no_good_learning: bool` selects path.

Pros: hot path untouched for non-learning profiles.
Cons: code duplication; the two implementations must agree on which
constraints fire which removals.

### Option B — sparse cause-tracking on the existing path

Keep `propagate_ac3` as-is. When learning is enabled, the engine
additionally maintains a sparse mapping from (cell, row) → cause-set
(set of currently-assigned literals whose constraints forced the
removal).

Pros: no duplicated AC-3 code.
Cons: per-row cause computation adds work on every removal, possibly
visible in the hot path.

**Recommendation**: Option A. Vol-25's perf wins on the hot path are
hard-fought and shouldn't be compromised for a research feature.
Option A keeps everything cleanly separate.

## Cause-tracking AC-3 (Option A) — algorithm

The existing `propagate_ac3` works via bitset operations on full u64
words. For cause-tracking, we need PER-ROW resolution. Algorithm
sketch:

```rust
// New struct in SearchState:
struct CauseTracker {
    // For each cell, the partial cause-set for each REMOVED row.
    // Keyed by row-id (within the cell's full domain).
    // Encoded as a Vec<u8> per cell, or a single arena-allocated buffer.
    // For each removal, cause-set is small (1-4 currently-assigned cells).
    per_cell_row_cause: Vec<Vec<SmallVec<[Position; 4]>>>,
}

fn propagate_ac3_with_causes(state, ...) -> Outcome {
    // ... same dirty-list rebuild as the fast path ...
    while let Some(p) = queue.pop() {
        // For each removed row r in domain[p] this iteration:
        for removed_row in newly_removed_rows {
            // What caused this row to be removed?
            // Look at which neighbour(s) of p have constraints that
            // would have allowed r, and now don't.
            let causes = identify_causes(state, p, removed_row);
            state.cause_tracker.per_cell_row_cause[p][removed_row.id] = causes;
        }
    }
}
```

### Identifying causes during AC-3

When AC-3 removes row `r` from `domain[p]`, the cause is the set of
currently-placed cells `c'` whose edge-color constraint with `p` no
longer admits `r`. We identify these by walking the 4 neighbours of
`p`:

```rust
fn identify_causes(state, p, removed_row_id) -> SmallVec<[Position; 4]> {
    let mut causes = SmallVec::new();
    let r_edges = state.rows[removed_row_id].edges;
    for (np, my_side, their_side) in neighbours_of(p) {
        if let Some((np_pid, np_rot)) = state.placed[np] {
            let np_edges = state.puzzle.piece(np_pid).edges.rotated(np_rot);
            if r_edges[my_side] != np_edges[their_side] {
                // Edge constraint from np forbids r at p.
                causes.push(np);
            }
        }
        // Else: np is not placed; its UNplaced rows determine constraints
        // (AC-3 support check). Need to check if there's ANY row in
        // domain[np] that would match r's side; if no, that's an
        // arc-consistency cause.
        // For now, simplify: only consider PLACED neighbours.
        // This may miss some causes but gives a SOUND (over-approx) clause.
    }
    causes
}
```

**Soundness**: each removal's cause-set is sufficient (forcing those
literals removes the row). Subset may be even sufficient (minimal
cause), but our over-approximation is sound.

**Storage cost**: per cell up to (max domain size) × O(4) Position
entries. For 16×16, max domain ~768; for interior cells reached during
search, current domain shrinks to ~10-100. Memory per cell at
mid-search ~100 × 4 × 4 bytes = 1.6KB. For 256 cells, ~410KB.
Tractable.

## Conflict analysis (1-UIP)

When AC-3 wipes out cell `c_w` (domain empty), the conflict is the
union of causes for ALL rows that were in `c_w`'s initial domain at
this AC-3 call. The union is the "decision-level conflict cause set".

For 1-UIP minimisation:
1. Build conflict graph from cause_tracker: each removed row points
   to its causes.
2. Walk back from the wipeout cell's removed rows, traversing causes.
3. At each step, identify the "first UIP": the first node from which
   ALL paths to the wipeout pass.
4. The 1-UIP cut is the asserting clause.

For E2's specific structure (cause is always *placed* cells, not
deeper implications), the cause tree is *flat*: each removed row's
cause is a set of placed cells, no further indirection. **1-UIP
analysis is therefore equivalent to: minimal union of cause-sets
across all rows that were in the wipeout cell**.

Algorithm:
```rust
fn analyze_conflict(state, wipeout_cell) -> NoGood {
    let mut union_causes = HashSet::new();
    for row_id in state.initial_domain_at_this_call[wipeout_cell] {
        let causes = state.cause_tracker.per_cell_row_cause[wipeout_cell][row_id];
        union_causes.extend(causes);
    }
    // Minimize: try removing one literal at a time, check if AC-3
    // applied to (union_causes \ {l}) still wipes out wipeout_cell.
    // Quadratic in clause size; for clauses ≤ 20 literals this is OK.
    minimize_clause(union_causes, state, wipeout_cell)
}
```

Where `minimize_clause` tries each subset of one-fewer-literal and
re-runs AC-3. Quadratic in clause size.

## Storage: 2-watched-literals (2WL)

```rust
struct NoGood {
    literals: Vec<(Position, PieceId, Rotation)>,  // sorted
    watch_a: usize, watch_b: usize,                // indices into literals
}

struct NoGoodDB {
    clauses: Vec<NoGood>,
    // For each literal (p, pid, rot), list of clause IDs watching it.
    watches: HashMap<(Position, PieceId, Rotation), Vec<usize>>,
}
```

When a literal `(p, pid, rot)` becomes "assigned" during search:
- Walk `watches[(p, pid, rot)]`.
- For each clause, check if the watch_a/watch_b is now satisfied
  (matching current assignment). If yes, advance the watch to another
  unassigned literal in the clause.
- If all literals except one are satisfied, **unit-propagate**: remove
  the value of the last unassigned literal from its cell's domain.
- If all are satisfied, **conflict** — backtrack.

The cost of a watch update is O(clause size) in the worst case; with
2WL, only ~2 clauses per literal need touching on average.

## Engine plumbing — call sites

Sites to modify:
1. **AC-3 path selection**: in `recurse` / `solve_inner`, dispatch to
   either `propagate_ac3_fast` or `propagate_ac3_with_causes` based on
   profile flag.

2. **Wipeout handler**: at the wipeout site (lines 1392, 1450, 1736),
   call `analyze_conflict` and add the learned clause to `NoGoodDB`.

3. **Pre-recurse check**: before each new value try, walk `NoGoodDB`'s
   watch list for the new literal and check for unit-propagation.

4. **Backtrack**: when the search undoes a placed cell, no clause-list
   action is needed (the no-good only fires when ALL its literals are
   assigned; backtracking removes literals from assigned and the watch
   moves naturally).

5. **Forget heuristic**: periodically, prune clauses with low recent
   activity. Standard heuristics: LBD (Literal-Block Distance) or
   activity-weighted.

## Engine profile

Add `EngineSolver::joe_depth150_bp_nogood()` or a new profile.
EngineConfig field:
```rust
pub no_good_learning: NoGoodConfig,

pub struct NoGoodConfig {
    pub enabled: bool,
    pub max_clauses: usize,        // default 100_000
    pub forget_threshold_lbd: u32, // forget clauses with LBD > this
    pub max_clause_size: usize,    // skip storing huge clauses
}
```

Default `NoGoodConfig::disabled()` for all existing profiles to keep
backward compat.

## Engineering timeline

Week 1: cause-tracking AC-3 implementation + tests.
- Day 1-2: clone propagate_ac3 → propagate_ac3_with_causes scaffolding.
- Day 3-4: cause identification (placed-neighbour subset).
- Day 5: unit tests on tiny puzzles (4×4 hand-designed wipeouts).

Week 2: conflict analysis + NoGoodDB.
- Day 1-2: analyze_conflict + clause minimisation.
- Day 3-4: 2WL data structure + watch updates.
- Day 5: integration with `recurse` (check + add).

Week 3: tuning + measurement.
- Day 1-2: forget policy implementation.
- Day 3-4: canonical-E2 measurement, compare to baseline.
- Day 5: documentation + vault write-up.

This is the FULL build, not the MVP. MVP could ship in 1.5 weeks by
skipping the forget policy + sticking with 1-UIP-equivalent
minimisation.

## Risk register

1. **Cause-tracking AC-3 may be ~5-10× slower** than the fast path.
   Acceptable if it produces enough clauses to compound benefit.

2. **1-UIP minimisation may be expensive**. Quadratic in clause size.
   Mitigate: cap minimisation iterations; skip clauses larger than
   threshold.

3. **2WL maintenance under heavy backtracking**. SAT solvers have
   well-known patterns here; need to ensure invariants hold across
   E2's domain-removal/restore mechanism.

4. **Clause overhead in non-record-track profiles**. If no-good
   learning produces no measurable speedup on canonical-E2 within
   the 60s budget that vol-32 used, this is a research dead-end.
   Decide: do we want CDCL even if it doesn't break record? Yes —
   it's the only structurally novel algorithm path remaining.

5. **Memory pressure**. 100k clauses × avg 10 literals × 8 bytes =
   8MB per worker. With 8 workers (parallel mode), 64MB additional
   memory. Acceptable.

## Open questions for vol-57

1. **Does parallel mode share the NoGoodDB across workers?** Adds
   sync overhead but each worker contributes clauses. Probably worth
   trying both modes.

2. **What backbone literals are universal?** Vol-37 found pos 161
   = pid 234 rot 0 is invariant across all known 457+ boards. We
   could SEED the NoGoodDB with structural clauses derived from such
   invariants. This is an unusual optimization — most SAT solvers
   start with empty DB.

3. **Restart strategy**. The vol-50 node_budget axis is a natural
   restart trigger. Luby sequence? Custom?

## Linked

- [[cdcl-no-good-e2]] — math design (this is engine companion)
- [[vol-56]] — measurement + decision-to-build
- [[vol-25]] — perf push that constrains the hot path
