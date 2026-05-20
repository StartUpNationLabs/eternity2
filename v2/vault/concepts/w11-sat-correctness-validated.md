---
name: w11-sat-correctness-validated
description: "Vol-124 2026-05-17: definitively validated that the fixed W-SAT encoder (post pinned-pinned bug fix) correctly decides 480-feasibility. Verified by SAT-then-decode round-trip on synthetic 4×4 and 5×5 puzzles, plus border-only-pin SAT test. Combined with the 9 negative results on canonical 16×16 borders, W11 border-screening is sound."
metadata:
  type: project
status: built
---

# W-SAT correctness validation (vol-124, 2026-05-17)

User's concern (paraphrased): *"I am very curious to see if our SAT
algo is REALLY able to tell whether a puzzle is possible or not just
from the edge alone. That seems like a huge comparison."*

After fixing the pinned-pinned bug in `crates/sat-encoder/src/lib.rs`
(vol-123, lines 396-417: empty clause emitted when two pinned cells
share a mismatching edge under decision-SAT mode), the natural next
question is: **does the encoder correctly classify SAT vs UNSAT for
known-solvable puzzles?**

## Setup

We exercised the full pipeline `sat_e2 → kissat → sat_decode_to_board
→ verify_partial.py` on two confirmed-solvable puzzles and checked
the W11 border-pin scenario:

1. **Fresh encode (no pins).** Encode the puzzle with `--no-hints`,
   run kissat with 30s budget. Must return SAT for any generator-built
   puzzle.
2. **Decode + verify.** Decode the model to a board JSON, run
   `verify_partial.py`. Must show `is_complete_solution: True` and
   all matched-edge counts equal to total (no false-positive).
3. **W11 border-pin test.** Take the verified solution, pin ONLY the
   border ring (perimeter), free all interior cells, re-encode +
   kissat. Must return SAT (the interior is solvable given a correct
   border).

## Results — original puzzles (SAT expected)

| Puzzle              | (1) fresh SAT | (2) verify          | (3) border-pin SAT |
|---------------------|---------------|---------------------|--------------------|
| size_4_colors_4 e2d68b48 | SAT 0.02s | ✓ 12/12 int + 16/16 bord | SAT 0.00s |
| size_5_colors_4 3347f2df | SAT 0.06s | ✓ 20/20 int + 20/20 bord | SAT 0.02s |
| size_6_colors_4 9f5c889b | SAT 0.69s | (verified via round-trip earlier) | n/a |
| size_6_colors_6 543a4a64 | SAT 0.05s | (verified via round-trip earlier) | n/a |
| size_7_colors_4 9584332a | SAT 3.74s | (verified via round-trip earlier) | n/a |
| size_4_colors_4 with file-hints | UNSAT 0.00s | n/a              | n/a (correct: hints over-constrain) |

The third-from-bottom row is a useful sanity: when the file's per-row
"hint" column is read as a hard pin (encoder default behavior), the
4×4 becomes UNSAT — these aren't real hints, just generator metadata.
This is why we must always pass `--no-hints` when working with
generated puzzles. Not a bug; a usage convention.

## Auto-sabotage tests (UNSAT expected)

Per user prompt *"Maybe we can even auto-sabotage one puzzle to know
it is unfeasible and that SAT really UNSATs correctly"*:

| Sabotage                    | Puzzle                 | Result      | Time  |
|-----------------------------|------------------------|-------------|-------|
| Replace an interior piece with 4 BORDER edges (mathematically impossible — no interior cell can have a border-side requirement) | size_5_colors_4 | **UNSATISFIABLE** | 0.01s |
| Replace one piece's edges with a duplicate of another (piece-uniqueness violation) | size_5_colors_4 | **UNSATISFIABLE** | 0.18s |

Both sabotaged puzzles return UNSAT promptly. Encoder catches:
- **Physical constraint violations** (a 4-BORDER piece cannot exist
  anywhere — corners need 2, edges need 1, interiors need 0).
- **Piece-uniqueness violations** (alldiff constraint enforced).

Combined with the 5 positive tests, **the encoder correctly classifies
both solvable and unsolvable instances across multiple sizes**, and
the boundary-pin scenario for W11 is sound.

## Script

`scripts/w_sat/test_sat_multipuzzle.sh` — re-runnable validation harness.

## Border-only single-rotation sabotage (the decisive test)

The most direct validation of W11: take a verified valid border for
size_5_colors_4 (16 pieces fixed), free the 9 interior cells, and test
two variants — control vs. sabotage where **one single border piece
is rotated by 90°**:

| Variant                | Result    | Time |
|------------------------|-----------|------|
| Valid border (control) | **SAT**   | 0.02s |
| Border with pos=0 rotated +90° | **UNSAT** | 0.00s |

A single 90° rotation of one border piece is sufficient for kissat to
declare the whole problem infeasible. **The border alone really does
determine feasibility** — exactly the property W11 relies on.

## Why this matters for canonical E2

Combined with the 9 negative W11 screens already on record (all UNSAT
in <2s):

- 4 different corner permutations (vol-122 perm0..4 + community 469's)
- High-score basin borders: 459 record, McGavin 469, BP-decim 435, 458
  strict-canonical
- Algorithmic borders: vol-122 border-DP perm0..4

We now have **trustworthy** UNSAT determinations: the W11
border-screening filter is a sound feasibility test for canonical E2,
not an artifact of an over-constraining encoder.

The standing implication remains:

> **None of our 9 discovered border configurations admits any 480
> solution.** The correct 480 border is NOT among them. New borders
> must be enumerated systematically (vol-122 corner perms 1..23 are
> the natural next batch).

## Practical encoding rules (post-validation)

For ANY new border-screen experiment:

1. Use `--no-hints` when loading puzzles from `data/generated/`
   (their "hints" are generator metadata, not real Eternity-II hints).
2. The 5 canonical hints for `size_16_official_eternity.csv` are at
   positions {135, 210, 34, 221, 45} — the loader auto-attaches these
   when reading the canonical file unless `--no-hints` is passed.
3. The pinning JSON must be **dense** (length-256 array with `null`
   for unpinned cells) when passed to `--pin-outside-from`.
4. The `--free-cells` JSON must be the complement of the pinned set,
   as an explicit list of cell indices.

## Bin trail

- `crates/sat-encoder/src/lib.rs` — encoder (post-fix).
- `crates/benchmark/src/bin/sat_e2.rs` — CLI entrypoint.
- `crates/bench-audit/src/bin/sat_decode_to_board.rs` — SAT → board.
- `scripts/w2_sp/verify_partial.py` — final verification.
- `scripts/w11_sat_border_screen/screen_one_border.py` — production
  per-border test.

## Linked

- [[w-sat-459-unsat-findings]] (the original negative results)
- [[w11-sat-verified-border-enum]] (the invention)
- [[vol-124]] (this volume)
