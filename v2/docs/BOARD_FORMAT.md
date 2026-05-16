# Eternity II board JSON/CSV format

This is the canonical on-disk format for E2 board partials and complete
solutions, produced by `eternity2_export::save_board` /
`save_board_csv` and read by `load_board` / `load_board_csv`.

## JSON (canonical, `placement` sparse format)

```json
{
  "placement": [
    {"pos": 0,   "piece_id": 3,   "rotation": 2},
    {"pos": 15,  "piece_id": 17,  "rotation": 0},
    ...
  ],
  "score": 459,
  "total_adjacencies": 480,
  "metadata": {
    "source": "bf_bw_schedule_hinted",
    "seed": 42,
    "elapsed_ms": 60000,
    "note": "v17a par-8"
  }
}
```

### Field semantics

| field        | type            | required | meaning |
|--------------|-----------------|----------|---------|
| `placement`  | array of object | YES      | list of placed cells (empty cells OMITTED) |
| `placement[i].pos` | u32 (0..255) | YES   | row-major position: `pos = y * width + x` |
| `placement[i].piece_id` | u32       | YES   | 0-indexed piece identifier |
| `placement[i].rotation` | 0\|1\|2\|3 | YES  | counter-clockwise 90° rotations from base |
| `score`      | u32             | optional | informational; verifier always recomputes |
| `total_adjacencies` | u32      | optional | informational |
| `metadata`   | object          | optional | producer-defined tags |

### Position convention

Position `pos` ∈ [0, W·H) using **row-major scan order**:
- `pos = y * W + x` where `(x, y)` is `(column, row)`.
- For canonical 16×16: `pos = 0` is top-left, `pos = 255` is bottom-right.

### Rotation convention

The Rust `Rotation` type uses `R0=0, R90=1, R180=2, R270=3` (each
applies 90° **clockwise** rotation per the implementation comment in
`crates/core/src/piece.rs`). The rotation applies to the piece's edges:

```
Base piece edges: (top, right, bottom, left)
After R90:        (left, top, right, bottom)
After R180:       (bottom, left, top, right)
After R270:       (right, bottom, left, top)
```

### Empty cells

Empty cells are **omitted** from the `placement` array. A board with
only 5 hints placed has a `placement` array of length 5, not 256.

## CSV format

```
pos,piece_id,rotation
0,3,2
15,17,0
34,207,1
...
```

- Header row is OPTIONAL; reader detects it via the `pos` prefix.
- One row per placed cell. Empty cells OMITTED.
- Columns are positional: `pos, piece_id, rotation`.

## Backwards-compatible read formats

`load_board` ALSO accepts (for backwards compatibility):

### Placement-indexed (deprecated, still readable)

```json
{
  "placement": [
    {"piece_id": 3, "rotation": 2},
    null,
    {"piece_id": 17, "rotation": 0},
    ...
  ]
}
```

Array INDEX = position. `null` = empty. Used by older bf_bw_* bins.

### DumpedBoard (deprecated, still readable)

```json
{
  "width": 16,
  "height": 16,
  "seed": 42,
  "score": 459,
  "total_edges": 480,
  "cells": [
    [3, 2],
    null,
    [17, 0],
    ...
  ]
}
```

Used by `eternity2-export::write_dump` (the original
diagnostic format). `cells` array INDEX = position.

### Nested `board.placement`

```json
{
  "board": {
    "placement": [...]
  }
}
```

`load_board` recurses into `.board.placement` when the top-level
`placement` is absent. Used by `run_e2_restart` summaries.

## Verifier behavior

`eternity2_export::verify(&puzzle, &hints, &board)` returns a
`VerifyReport` checking:

1. **Piece-uniqueness**: each `piece_id` appears at most once.
2. **Border-consistency**:
   - Pieces at puzzle-edge positions must have BORDER (color 0) on the
     outward-facing side(s).
   - Pieces at interior positions must NOT have BORDER on any side.
3. **Hint-compliance**: canonical hints (from puzzle CSV) are placed
   at the correct positions with correct piece+rotation.
4. **Edge-match score**: count of matching colored edges between
   adjacent placed pieces.

A board is `LEGAL_COMPLETE` if: piece-unique, no border violations,
all hints match, all 256 cells placed.
`LEGAL_PARTIAL` drops the all-placed requirement.
`ILLEGAL` if any of the above fails.

## Color encoding (puzzle CSV)

The Selby-Riordan canonical puzzle CSV at
`data/puzzles/size_16_official_eternity.csv` uses 16-bit binary
words for each color:

- `1111111111111111` (= 65535) = BORDER (sentinel)
- `0000000000000001` (= 1) = interior color 1
- `0000000000000010` (= 2) = interior color 2
- ... up to color 22 for the canonical puzzle.

The internal color representation is `u8`, with `BORDER = 0` (despite
the CSV using all-ones; the parser maps 65535 → 0).
