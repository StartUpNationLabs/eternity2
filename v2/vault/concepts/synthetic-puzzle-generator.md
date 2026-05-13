---
tags: [concept, infrastructure, ml]
status: built
origin-vol: 26
---

# Synthetic puzzle generator (Selby-Riordan-style, with recoverable solution)

**Status**: `built` (vol-26)
**Origin**: vol-26 (learned value-order gate)
**Files**: `crates/generator/src/lib.rs` (`generate_with_solution`), `crates/ml-export/src/bin/gen_export.rs`

## Definition

A small extension to the existing `eternity2-generator` crate that, in
addition to producing a Selby-Riordan-style E2-family puzzle, also returns
the canonical assembly that was implicitly built during generation. The
new entry point is:

```rust
pub fn generate_with_solution(
    cfg: GeneratorConfig,
) -> Result<(Puzzle, Vec<Placement>), GeneratorError>;
```

`Placement = { position, piece_id, rotation }`. The placements form a
complete assembly: at every cell the placed piece's rotated edges satisfy
adjacency with all neighbours and match the gray border where required.
A unit test in `crates/generator/src/lib.rs` checks this on 16 seeds.

## Why we re-used the Rust generator instead of writing Python

Vol-26's plan said: *"Re-implement the Selby-Riordan generator in Python.
The existing C++ generator is in solvers/ (read-only legacy); shelling out
is more fragile than re-implementing."*

But the **Rust** `eternity2-generator` already implements exactly the same
construction in 156 LOC (`crates/generator/src/lib.rs`), with deterministic
SplitMix64 seeding and a clean Result API. Re-implementing in Python
would mean:
- 2 sources of truth for the puzzle distribution; subtle divergence
  inevitable.
- ~3 hours of Python writing for code we already have in Rust.
- Python's PRNG would not match Rust's SplitMix64 byte-for-byte, so
  "seed=N in Python" and "seed=N in Rust" produce different puzzles —
  loses the ability to cross-validate.

Decision (vol-26 open): use the Rust generator as the single source of
truth. Add `generate_with_solution`. Add a small `gen-export` binary
(`crates/ml-export/src/bin/gen_export.rs`) that writes a JSONL stream of
`{seed, size, color_count, pieces, canonical_solution, expert_trajectory}`
records the Python side reads with `json.loads`.

## What this generator produces

Per `crates/generator/src/lib.rs`:

1. Assign each interior edge of the (W, H) board a random color from
   `1..=interior_colors`. Coverage pass first (each color appears ≥ once),
   then uniform random for the rest.
2. Build the 4 edges of every piece from its position's surrounding
   interior edges, with `BORDER` (0) on outer-boundary sides.
3. Apply a uniformly-random rotation to each piece.
4. Shuffle the piece order.

The output puzzle has at least one solution (the one we built in step 1)
by construction. The Selby-Riordan procedure on canonical 16×16 E2 is more
elaborate — it ALSO enforces the [[rare-color-rule]] (rare colors 1-5 on
opposite-edge-only) and several other structural constraints. **This
generator does NOT enforce those refinements.**

## What this generator does NOT produce

- ❌ Rare-color-on-opposite-edges invariant — every interior edge is
  uniformly random, so a piece can have rare color 1 on adjacent sides.
- ❌ Hint set — the synthetic puzzles are hint-less; the engine's
  `BorderFirstMRV` is the only constraint.
- ❌ Unique-solution guarantee — multiple solutions are usually possible,
  the generator just guarantees ≥ 1.
- ❌ Canonical-E2-difficulty parity — 6×6/5c at 5s budget solves 100% with
  MRV; canonical 16×16 doesn't.

Vol-26 confirmed (measured 2026-05-13) that the rare-color refinement
isn't needed for the gate measurement: a small imitation model trained on
the unrefined synthetic distribution still produces ≥ 540× node reduction
on held-out synthetic puzzles. The signal a value-order model picks up is
robust to the refinement gap.

## File: the JSONL record

`crates/ml-export/src/bin/gen_export.rs` writes one line per puzzle:

```json
{
  "seed": 1,
  "size": 6,
  "color_count": 6,
  "pieces": [{"id": 0, "edges": [0, 2, 1, 0]}, ...],
  "canonical_solution": [{"position": 0, "piece_id": 5, "rotation": 1}, ...],
  "expert_trajectory": [{"depth": 0, "position": 0, "piece_id": 5, "rotation": 1}, ...]
}
```

The `expert_trajectory` is captured by a `TrajectorySink` (impl
`EventSink`) that overwrites a depth-indexed stack on every `ValueTried`
event during the engine's solve. On `Solved`, the slots 0..cell_count hold
the winning sequence. The trajectory is what the imitation model trains
to predict at every depth `d`: given the partial board after steps
`0..d-1`, predict step `d`'s `(piece_id, rotation)`.

## Generation throughput (measured)

| Size | Colors | Median nodes/puzzle | Throughput |
|---|---|---:|---:|
| 6×6 | 3 | 655 | ~80 puz/sec |
| 6×6 | 4 | 4472 | ~50 puz/sec |
| 6×6 | 5 | 2397 | ~200 puz/sec |
| 7×7 | 5 | 392 151 | ~10 puz/sec |
| 8×8 | 5 | 1 064 127 | ~5 puz/sec |

Note the non-monotonic difficulty in colors: 6×6/4c is HARDER than 6×6/5c
because fewer colors means more piece collisions (more pieces have
identical edges → more backtracking before propagation discriminates).

## Linked concepts

- [[selby-riordan-generator]] — the analysis page describing what the
  canonical-E2 generator actually does (this concept page describes our
  Rust implementation, simpler than canonical).
- [[learned-value-order]] — the vol-26 deliverable that consumes this
  generator's output.
- [[rare-color-rule]] — refinement absent from this generator.

## Linked memory

- `project_e2_vol26_learned_value_order` — vol-26 gate result.
