# BRAID — Joint Warp-Weft Color-Thread Construction

**Status**: `wont-do` 2026-05-19 (Vol-153, same day). The warp-weft
framing is conceptually appealing but the proposed search algorithms
reduce to row-major DFS with row-shaped beam units — essentially
V151 with bigger atomic search units. **Not fundamentally new**.

**Lesson**: framing matters less than the search primitive. BRAID's
"warp threads" and V151's "row prefix in beam" describe the same
search structure with different vocabulary.

**Pivot**: V154 = DLX (Knuth Algorithm X / dancing links) is a
genuinely different SEARCH PRIMITIVE — not DFS with constraints, but
exact-cover with column-deletion. Untried for E2.

## Conceptual move

V147+V149+V152 lessons: "decompose then solve" doesn't work on
canonical E2 (decompositions are vacuous OR inseparable). BRAID
*encodes the coupling* by treating the 2D matching constraints as
two orthogonal 1D thread families that share a piece-knot at every
intersection.

## Key advantage

Each warp thread has only 22 colors. So warp $y$ has at most $22^{16}$
distinct realizations, but constrained by continuity $(e_{y,x} = w_{y,x+1})$
this drops to a structure exploitable by DP.

Specifically: a single warp thread = a walk of length 15 in the
"warp-color-pair" multi-set graph. With color counts (24,24,24,24,24,
48×5, 50×12), the # of walks is bounded but the actual constraint
(piece availability) reduces this much further.

## Implementation outline

```python
def find_warp_threads(pieces, size):
    """Enumerate possible warp threads = sequences of (W, E) color
    pairs along a single row, where E[x] = W[x+1], W[0] = E[15] = 0
    (border), AND the (N, S) freedom is preserved (don't pin yet)."""
    # For each starting (W=0, E=c1) corner, walk via color compatibility.
    # Use beam search to keep top-K walks at each depth.
    pass

def join_warps_with_wefts(warps, pieces):
    """Given a list of warp threads, find a compatible assignment of
    weft threads + pieces such that:
      - Every cell's 4 sides come from compatible warp+weft.
      - Every piece used exactly once."""
    # Backtracking over (warp_y, weft_x) constraints.
    pass
```

## Why this might break the 455 ceiling

- V151 beam search hit 455 because the cell-first greedy is shortsighted
  about row-end / col-end constraints.
- BRAID directly enforces row-continuity AND column-continuity from
  the START of construction; no last-mile constraints come as a surprise.

## Falsifiable

The math is straightforward. The empirical question is whether the
joint warp+weft+piece-assignment CSP is searchable in practice. We'll
know in 1-2 days.

## Linked

- [[../sessions/vol-153]]
- [[../plans/INVENTION_NAMES_2026-05-19]]
- [[weaving-beam]] (V151 parent; 455 ceiling)
- [[harmonics-matching]] (V152 refuted; informed BRAID design)
