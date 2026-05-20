---
name: m17-qw-greedy-builder-issue
description: "QW Greedy Builder result CORRECTED via verify_board: 251/256 placed, 5/5 hints, but only 75/466 matched. Python parser bug propagated. The QW heuristic does NOT produce competitive boards from clean slate."
metadata:
  type: project
status: built
---

# M17 — QW Greedy Builder corrected result

## What I thought I had

The Python QW Greedy Builder reported "434/480 matched" using its own
edge-counting logic.

## What verify_board (canonical Rust loader) actually shows

- 251/256 placed
- **5/5 hints obeyed** ✓
- **75/466 matched** (terrible — about 16% match rate)
- status LEGAL_PARTIAL

The Python parser misreads the binary-one-hot color encoding in the
CSV. When I rotated and computed matches in Python, I got "raw" colors
that aren't the canonical Rust colors. The 434 was nonsense.

## Lesson

**Always use the Rust loader (canonical) for E2 edge computations.**
Python parsers can quickly drift from the canonical encoding.

## What the QW heuristic DOES do correctly

- Places pieces respecting hint constraints (5/5 hints).
- Places 251 of 256 pieces (97.7% — covers most of the board).
- Avoids border violations.

## What it FAILS at

- Edge MATCHING. The algorithm picks "high-affinity pieces" by quantum
  walk, but its "best_placement_for_piece" function uses the same Python
  rotation logic — so it doesn't actually optimize for matches in
  canonical colors.

## Refutation status

The CONCEPT (quantum-walk-guided piece-priority for clean-slate
construction) is not refuted. The IMPLEMENTATION had a Python parser
bug that produced fake match counts.

A proper Rust implementation might still work. But the algorithmic
gain is uncertain.

## Status

`implementation-bug` → `refuted-as-implemented`. Concept could be re-built
in Rust using canonical encoding.

## Linked

- [[m17-quantum-clean-slate-finding]] (the clean-slate analysis is OK)
