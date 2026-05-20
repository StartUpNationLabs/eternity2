---
name: infrastructure-consolidation-plan
description: "Vol-118 user-requested cleanup. The project has accumulated 7 scoring functions, 3 board-JSON formats, 14+ load_board implementations across bins, and 5+ render/export helpers. Each is a potential source of subtle bugs (vol-118 bf-bucket bug, vol-35 piece-uniqueness, vol-14 hint-pin bug, etc.). Plan: consolidate to ONE canonical scorer, ONE board I/O module, ONE verifier, ONE export format — with a documented JSON+CSV schema."
metadata:
  type: project
status: unbuilt
---

# Infrastructure consolidation plan (vol-118 cleanup)

**Status**: `unbuilt` — design 2026-05-16.
**Origin**: user feedback after vol-118 bf-bucket bug discovery.
**Goal**: ONE canonical implementation of each I/O concern, used by
ALL bins and crates.

## Current chaos inventory

### Scoring functions (7 implementations)

| location                                       | signature                                | notes |
|------------------------------------------------|------------------------------------------|-------|
| `eternity2_export::score_board`                | `(Puzzle, Board) -> (u32, u32)`         | THE canonical one |
| `eternity2_bench_audit::score_board_dense`     | `(Puzzle, Board) -> (u32, u32)`         | thin wrapper |
| `eternity2_bench_audit::score_packed`          | `(Puzzle, edges_grid) -> u32`           | for dense edge arrays |
| `eternity2_bench_audit::score_board_baseline_wrapper` | `(Puzzle, Board) -> u32`         | legacy wrapper |
| `eternity2_localsearch::alns::score_board`     | `(Puzzle, Board) -> u32`                | inlined hot path |
| `eternity2_blackwood_fast::score_board`        | `(Puzzle, &[(PieceId, Rotation)]) -> u32` | for bf's internal repr |
| `eternity2_solver_engine::bridge::score_v2`    | various                                  | solver-specific |

### Board JSON formats (3 in active use)

| format                  | structure                                           | source |
|-------------------------|-----------------------------------------------------|--------|
| `DumpedBoard`           | `{cells: [[pid, rot] \| null]}` indexed             | eternity2-export |
| `placement` indexed     | `{placement: [{piece_id, rotation}]}` indexed       | bf_bw_* bins |
| `placement` sparse      | `{placement: [{pos, piece_id, rotation}]}` sparse   | alns_only, edge_target_match |

Some files even have BOTH indexed and `pos` fields, which trips up parsers
that check for `pos` first vs. index.

### Board loaders (14+ implementations)

In `crates/bench-audit/src/bin/` alone: 14 separate `fn load_board` definitions.
Each has slight variations:
- Some accept null entries; some don't.
- Some check `pos`; some use array index; some try both.
- Some try sparse-fallback; some don't.

### Verifiers

`scripts/verify_records.sh` shells out to `rescore_board` + `verify_record` bins.
Adequate but the two bins each have their own `load_board`.

## Bugs traceable to this chaos

| vol | bug                                                       | root cause |
|-----|-----------------------------------------------------------|------------|
| 14  | `alns_e2` unpinning canonical hints                       | inconsistent hint handling across loaders |
| 35  | piece-uniqueness bug in `pin_hints` save paths            | 3 different save paths, only some checked |
| 118 | bf-bucket bug allowing illegal placements                 | per-bin verifier silent; only viz caught it |

## Target architecture

### 1. ONE scorer

**Canonical home**: `crates/export/src/score.rs::score_board(Puzzle, Board) -> (matched, total)`.

All other scorers DELETED or made inline `#[inline(always)]` wrappers
that call the canonical. The hot-path inline in `alns` stays IF
benchmarked to lose nothing on inlining — verify before removing.

### 2. ONE board I/O module

**Canonical home**: `crates/export/src/board_io.rs`.

Public API:
```rust
pub fn load_board(path: &Path, puzzle: &Puzzle) -> Result<Board, LoadError>;
pub fn save_board(path: &Path, puzzle: &Puzzle, board: &Board, metadata: &Metadata) -> Result<()>;

pub struct Metadata {
    pub source: String,
    pub seed: Option<u64>,
    pub elapsed_ms: Option<u64>,
    pub note: Option<String>,
}
```

Reads BOTH formats (DumpedBoard + placement-array) transparently.
Writes ONE format: `placement` sparse with explicit `pos` (the
most-universal, no-ambiguity option).

### 3. ONE board verifier

**Canonical home**: `crates/export/src/verify.rs` (NEW).

Public API:
```rust
pub struct VerifyReport {
    pub placed_count: u32,
    pub matched: u32,
    pub total: u32,
    pub unique_pieces: u32,
    pub duplicate_pieces: Vec<PieceId>,
    pub border_violations: Vec<BorderViolation>,
    pub hint_compliance: HintCompliance,
}

pub fn verify(puzzle: &Puzzle, hints: &Hints, board: &Board) -> VerifyReport;
```

A SINGLE bin `verify_board` replaces both `rescore_board` and `verify_record`.

The `verify` function checks:
- Piece-uniqueness.
- Border-consistency (NEW: catches vol-118 bf-bucket bug).
- Hint-compliance.
- Edge matching.

### 4. Documented formats

Add `docs/BOARD_FORMAT.md` with:

```
JSON format (board.json):
{
  "placement": [
    {"pos": N, "piece_id": P, "rotation": R},
    ...
  ],
  "metadata": {
    "source": "string identifying which bin produced this",
    "seed": optional u64,
    "elapsed_ms": optional u64,
    "note": optional string
  },
  "score": optional u32  // informational only; verifier re-computes
}

CSV format (board.csv):
pos,piece_id,rotation
0,3,2
1,17,0
...

Field semantics:
- pos: 0-indexed cell position, row-major (pos = y * width + x).
- piece_id: 0-indexed piece identifier in puzzle's piece array.
- rotation: 0|1|2|3 (counter-clockwise 90° rotations from base).
- Empty cells: omitted from placement array.
```

### 5. Migration plan

1. Centralize scoring + loading in `eternity2-export` (already started).
2. Add `verify` module in `eternity2-export`.
3. Add `eternity2-export::load_board` / `save_board` accepting both
   legacy formats, writing canonical.
4. Update ALL bins in `bench-audit` and `benchmark` to use canonical I/O.
5. Delete per-bin `load_board` functions.
6. Update `verify_records.sh` to use new single bin.
7. Run tests to verify no regressions.

## Estimated effort

- Step 1-3 (new modules): ~2-3 hours coding.
- Step 4 (migrate ~30 bins): ~2-3 hours mechanical edits.
- Step 5-7 (cleanup + verify): ~1 hour.

**Total: 1 long session of pure cleanup.** Should ship without
breaking existing functionality. Best done before further algorithm
work to prevent accumulating more bugs.

## Linked

- [[bf-candidate-bucket-bug]] — example of bug enabled by missing verifier.
- [[code-debt]] — earlier code-debt audit (vol-25).
- [[vol-118]].
