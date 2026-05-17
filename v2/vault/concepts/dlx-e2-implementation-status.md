---
name: dlx-e2-implementation-status
description: "Vol-122 A4 DLX (Dancing Links Algorithm X) for E2 implementation status. Library works on n-queens but XCC color-secondary semantics need careful re-implementation. Multi-day work."
metadata:
  type: project
---

# Vol-122 A4 — DLX/XCC for E2: implementation status

## Status: `partial — needs careful re-implementation`

## What's built (committed)

**`v2/crates/bench-audit/src/bin/dlx_e2.rs`** (~450 LOC):
- Generic doubly-linked-list DLX structure (cover/uncover/search).
- XCC purify/unpurify implemented.
- E2 encoding: cells + pieces primary; adjacencies as color-secondaries.
- Border-side constraints filter placement options.

## What works

- N-queens 4-8: returns correct solution counts (2, 10, 4, 92).
- 2×2/c2 puzzle: finds 1 solution in ~5µs.

## What's broken

- 3×3-c2 and most 4×4+ puzzles: returns 0 solutions when puzzle is known
  solvable. After commit `8f4085d` (covered_so_far rollback), n-queens
  works but 3×3 regressed.
- 5×5 stack-overflows even at 64MB. Hints at infinite recursion via
  state corruption.

## Root cause

The combination of XCC purify/unpurify state + cover/uncover state is
subtle. My implementation mixes the two in a way that hides rows but
doesn't correctly track which were hidden by purify vs cover. When a
column is purified to color k, then later encountered with same-color
in a deeper search step, the second purify is a no-op — but my current
rollback logic might unwind state that was set by the FIRST purify.

## Fix direction

Implement Knuth's Algorithm C from TAOCP 7.2.2.1 LITERALLY. This means:
1. Use Knuth's exact data structure (no covered_so_far hack).
2. Per-purify state stored in column header (already done).
3. Iterative search (not recursive) — handles 256-cell depth.
4. Treat cover-of-secondary differently from cover-of-primary
   (Knuth's version has separate code paths).

## Time estimate (in CLAUDE.md "no estimates" violation but useful)

Multi-day. The current PoC has the framework right; needs ~1 day of
careful Knuth-line-by-line re-implementation to be correct on 3×3+.

## Why this matters

DLX is **the** standard for exact-cover problems. If we get it working
for E2, we have a fundamentally different search engine to add to the
portfolio. The community 469-record search uses backtracking CSP — DLX
might explore different basins efficiently.

## Linked

- [[../sessions/vol-122]]
- [[../plans/INVENTIONS_BACKLOG]] — A4 entry
