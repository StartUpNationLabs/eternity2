---
name: completability-decision-threshold
description: "vol-208 — measured perfect-completion decision speed vs pinned-prefix size on canonical E2. Along McGavin's prefix, edge-strict DFS decides perfect-completability in <11ms down to 144 pieces placed (9 rows pinned / 7 free / 112 free cells), then EXPLODES at 128 placed (8 rows / 128 free, >1.4M nodes >3s). The threshold is PREFIX-SPECIFIC (measured near a real solution), not a universal guarantee; for adversarial/non-completable partials the UNSAT proof can be far slower."
status: built
metadata:
  type: concept
---

# Completability decision threshold (vol-208)

**Origin**: vol-208 (2026-06-10), user question "minimum #placed pieces to decide
completability in milliseconds". `scripts/v208_confluence/completability_speed.py`.

## What was measured
Perfect-completion decision = "can the free cells be filled so EVERY remaining
edge matches (→ a 480 board)?", decided by **edge-strict row-major DFS** (place a
piece only if it matches all already-placed neighbors; piece-uniqueness enforced),
returning SAT/UNSAT, timed. Pinned the top T rows of **McGavin 469**; swept T.

| T rows pinned | pieces placed | free cells | decision | nodes | time |
|---:|---:|---:|---:|---:|---:|
| 15 | 240 | 16 | SAT | 16 | 0.1 ms |
| 14 | 224 | 32 | SAT | 34 | 0.1 ms |
| 13 | 208 | 48 | SAT | 202 | 0.4 ms |
| 12 | 192 | 64 | SAT | 271 | 0.5 ms |
| 11 | 176 | 80 | SAT | 1.8k | 3.6 ms |
| 10 | 160 | 96 | SAT | 3.0k | 5.9 ms |
| **9** | **144** | **112** | SAT | 5.2k | **10.5 ms** |
| 8 | 128 | 128 | TIMEOUT | >1.4M | >3 s (explodes) |

## The finding
- **Millisecond decision holds down to ~144 pieces placed (9 rows pinned, 7 rows /
  112 cells free).** One row deeper (128 placed, 8 rows / 128 cells free) the
  edge-strict search **explodes** (>1.4M nodes, no decision in 3s). This is the
  **depth-128/144 wall** — the same depth-150 phase transition the vault sees from
  the construction side ([[depth-40-phase-transition]], WATERSHED rows 8-11).
- The narrowness near a real solution is why small free regions decide instantly:
  edge-strict branching is ~2-3 survivors/cell, and within ~7 rows of a genuine
  completion the tree barely branches.

## CRITICAL caveat — this is PREFIX-SPECIFIC, not a universal guarantee
- Measured along **McGavin's own completable prefix** (its rows 6-15 are perfect,
  [[scarcity-skeleton-shared-core]] Q1), so the DFS finds McGavin's real
  completion fast (SAT). It does NOT bound the time to decide an *arbitrary*
  partial board.
- For a partial that is NOT perfectly-completable, the DFS must EXHAUST the free
  region to prove UNSAT. Near the transition that exhaustion is the 1.4M-node
  explosion. So "144 placed → fast" is an existence statement about *favorable*
  prefixes, not a worst-case guarantee.
- Deciding perfect-completability of an arbitrary E2 partial is the core NP-hard
  question; there is **no known fast (poly) universal test** at any placed-count
  below full. The millisecond regime is exactly "the free region is small enough
  to exhaust" — which for edge-strict E2 means **≤ ~7 free rows / ~112 cells** in
  the favorable case, fewer if the partial branches more.

## Necessary-condition (always-fast) checks — the other half of the answer
A truly millisecond check at ANY placed-count must be a *necessary condition* that
can only return "definitely not completable" or "maybe":
- edge-strict frontier consistency (a free cell with 0 fitting pieces ⟹ UNSAT),
- per-color residual budget / Hall-lite on remaining pieces vs remaining edges.
These are O(cells), microseconds, but vol-204 WATERSHED showed global Hall fires
**0 levels early** on canonical deaths (deaths are local piece-theft, invisible to
global supply) — so the cheap necessary checks rarely fire before the DFS does.
They give a fast NO on *grossly* infeasible partials, never a fast YES.

## Bottom line (the honest answer)
- **Fast YES** (this partial perfectly completes): achievable in ms only when the
  free region is ≤ ~7 rows / ~112 cells AND the partial is genuinely near a
  solution. ~144 placed pieces is the measured favorable threshold; it is **not**
  guaranteed for an arbitrary 144-piece partial.
- **Fast NO**: only for partials a cheap necessary condition rejects (a starved
  cell / color deficit); the hard "looks fine but is actually uncompletable"
  partials need full exhaustion and have no ms decision.
- **No universal ms oracle** exists below full placement — that would solve E2.

## Linked
- [[mcgavin-n-row-scaling]] — vol-68: N=14 rows pin McGavin's 469 *under ALNS*
  (a determinacy threshold; this page is the *decision-speed* threshold, related)
- [[depth-40-phase-transition]] — the same wall from BB&B
- [[watershed-frontier-flow]] — why cheap global checks don't fire early
- [[scarcity-skeleton-shared-core]] — McGavin's perfect rows 6-15 (why SAT is fast here)
