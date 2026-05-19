# Current Volume — Vol-153

**Theme**: BRAID — Joint Warp-Weft Color-Thread Construction.
Eighth named invention, building on V147+V149+V152 lessons:
*layout/matching/propagation are coupled — encode the coupling.*

## Genesis (the 3 lessons)

1. **V147 INTAGLIO-DFS**: pre-placement pruners on strict DFS are
   vacuous (placed cells already feasible by construction).
2. **V149 STRATUM-Budget**: invariants over placed cells likewise
   vacuous.
3. **V152 HARMONICS**: match-first construction cannot decouple
   matching from layout — the right vertex 2-coloring IS the layout.

**Combined lesson**: canonical E2 resists separation of concerns.
Inventions must encode the COUPLING.

## The invention

A solved 16×16 board has two natural 1D structures running
orthogonally:

- **16 warp threads** (horizontal): for each row $y$, the sequence of
  (E-color, W-color) pairs along the row. Specifically: row $y$
  passes through cells $(y, 0), (y, 1), ..., (y, 15)$. The W-color of
  cell $(y, x+1)$ must equal the E-color of cell $(y, x)$ (matched
  edge) for the warp to be "tight". Mismatched edges are warp breaks.
- **16 weft threads** (vertical): symmetric, for each column $x$,
  sequence of (N-color, S-color) pairs.

Each piece at position $(y, x)$ is a 4-color "knot": $(n, e, s, w)$,
which simultaneously:
- contributes $(w, e)$ to warp thread $y$ at index $x$;
- contributes $(n, s)$ to weft thread $x$ at index $y$.

**Score = (number of matched warp links) + (number of matched weft links) = 480 max**.

A 480 board ⇔ every warp link matches AND every weft link matches.

## Why BRAID is different from V150/V151

V150/V151 builds CELL-FIRST: for each cell, pick a piece. This implicitly
constrains both warp and weft simultaneously per cell but doesn't
EXPLOIT the thread structure.

BRAID encodes the threads as first-class objects:
- Each warp thread is a sequence of 16 (W, E) pairs.
- Each weft thread is a sequence of 16 (N, S) pairs.
- A piece $(n, e, s, w)$ assigned to cell $(y, x)$ projects to:
  - warp $y$ slot $x$: (W=w, E=e)
  - weft $x$ slot $y$: (N=n, S=s)

The construction: pick the 16 warp threads and 16 weft threads
COHERENTLY such that for every cell $(y, x)$, there exists a piece
with the prescribed (n, e, s, w) AND that piece is used exactly once.

## Math

Let warp $W_y$ = sequence of $16$ pairs $\{(w_{y,0}, e_{y,0}), (w_{y,1}, e_{y,1}), ..., (w_{y,15}, e_{y,15})\}$ with continuity $e_{y,x} = w_{y,x+1}$ for $x = 0, ..., 14$ (the matched-warp condition).

Similarly weft $V_x$ = sequence of pairs $\{(n_{x,y}, s_{x,y})\}_{y=0}^{15}$ with $s_{x,y} = n_{x,y+1}$.

The piece at $(y, x)$ has sides:
$$n = n_{x,y}, \quad e = e_{y,x}, \quad s = s_{x,y}, \quad w = w_{y,x}$$

Boundary: $w_{y,0} = $ BORDER, $e_{y,15} = $ BORDER, $n_{x,0} = $ BORDER, $s_{x,15} = $ BORDER.

**Constraint**: there must exist a bijection $\phi: \{(y, x)\} \to \text{pieces}$ such that piece $\phi(y, x)$ has the prescribed sides.

This is a **product-space search**: warp space × weft space × piece-assignment.

## Search strategy

Encode as a CSP:
- Variables: 16 warp threads + 16 weft threads + piece-assignment.
- Domains:
  - Each warp thread = a tuple of 17 colors $(w_{y,0}, e_{y,0}, e_{y,1}, ..., e_{y,15})$ with $w_{y,0} = 0$ (border) and $e_{y,15} = 0$. Internal colors free.
  - Each weft analogous.
- Constraints:
  - For each cell $(y, x)$: the 4-tuple $(n_{x,y}, e_{y,x}, s_{x,y}, w_{y,x})$ must match the (sides of some) piece, after rotation.
  - Each piece used exactly once across all 256 cells.

Solve as: enumerate warp configurations (16 × ~22^15 = huge), for each, check if a consistent weft + piece-assignment exists.

Better: **CONSTRAINT PROPAGATION on warp+weft jointly**. Fix one warp thread, propagate constraints on adjacent warps and on weft slots. This is like 2D AC-3 but on the THREAD level, not the cell level.

## Concrete Day 1 plan

PoC at SMALL SCALE: 8×8 puzzle (generated, not canonical). Solve via
backtracking on warp threads with weft consistency check after each
thread placement.

If it works on 8×8, scale up. If it doesn't, refute the BRAID search
strategy (but the math stands).

## Falsifiable claims

| Claim | Test |
|-------|------|
| BRAID on 8×8/c4 finds a complete 480-equivalent in < 10 sec | Run PoC |
| BRAID on 12×12/c12 finds ≥95% complete in < 60 sec | Scale up |
| BRAID on canonical 16×16/c22 finds ≥420 in < 5 min | Scale to canonical |
| BRAID on canonical reaches > V151's 455 ceiling | Genuine win |

## Kill-criteria

- 8×8 PoC fails to find a complete board in 5 min → refute warp-first
  search strategy.
- Canonical scoring < V150's 408 (random sweep baseline) → refute
  entire BRAID encoding.

## Days budget

3 days. Day 1: 8×8 PoC + math validation. Day 2: scale to 12×12, 16×16
canonical. Day 3: measure + refute or commit.

## Linked

- [[../sessions/vol-153]] (to create)
- [[../concepts/braid-warp-weft]] (to create)
- [[INVENTION_NAMES_2026-05-19]]
- [[../sessions/vol-152]] (parent: HARMONICS refuted)
