---
name: j1-column-dp-design
description: "J1 Double-Row Column-DP with Beam Search — design + math. Solve E2 as a column-by-column sliding band, with state = (column index, top/bottom boundary colors). Per CLAUDE.md senior-researcher directive."
metadata:
  type: project
status: partial
---

# J1 — Double-Row Column-DP with Beam Search

## Idea

Solve the puzzle as a **2-row sliding band**, processing columns left-to-right:

- **State** at column $j$: $(j, \text{top-row-piece}, \text{bottom-row-piece})$
- **Transition** $(j, p_t, p_b) \to (j+1, p_t', p_b')$ iff:
  - $p_t'.L = p_t.R$ (top horizontal match)
  - $p_b'.L = p_b.R$ (bottom horizontal match)
  - $p_t'.B = p_b'.T$ (vertical match within new column)
  - $p_t', p_b'$ are unused pieces (= piece-uniqueness)

- **Objective**: maximize sum of matched edges (3 per column-step: 2 horizontal + 1 vertical).

The DP is **forward-pass exponential** in the piece-set state. To make it
tractable, use **beam search**: at each column $j$, keep only the top-$K$
states by accumulated score.

## State space

Naive: $(p_t, p_b) \in P \times P$ pairs = $256 \times 256 \approx 65$k states
per column (modulo piece-set used).

With piece-uniqueness, the SET of pieces used so far matters. Including it
explicitly gives state-space $\binom{256}{2j} \approx \text{huge}$.

**Beam-search relaxation**: track only $(p_t, p_b, \text{score-so-far})$ and the
SET of used pieces implicitly. Compress: hash the used-set, dedupe states
that have same hash + same boundary edge profile.

## Mathematical formulation

Let $\mathcal{S}_j$ denote the set of valid 2-cell column-end states at
column $j$. A state $s_j = (p_t, p_b, \mathcal{U}_j, \text{score}_j)$ where:

- $p_t, p_b \in P$: pieces in the top/bottom row at column $j$.
- $\mathcal{U}_j \subseteq P$: pieces used so far ($|\mathcal{U}_j| = 2(j+1)$).
- $\text{score}_j \in \mathbb{N}$: accumulated matched edges.

Transition relation:
$$
s_j \xrightarrow{(p_t', p_b')} s_{j+1}
$$
iff:

1. $p_t' \notin \mathcal{U}_j$ and $p_b' \notin \mathcal{U}_j$ and $p_t' \neq p_b'$.
2. $p_t.R = p_t'.L$ (top horizontal match) — counts +1 to score.
3. $p_b.R = p_b'.L$ (bottom horizontal match) — counts +1 to score.
4. $p_t'.B = p_b'.T$ (vertical match in new column) — counts +1.

(Plus the initial column: only constraint is vertical match $p_t.B = p_b.T$.)

Score increment per step: at most 3 (all three edges match).

## Beam search algorithm

Initialize $\mathcal{S}_0$: all pairs $(p_t, p_b)$ with $p_t \neq p_b$ and $p_t.B = p_b.T$.
Score contribution: +1 if vertical match holds.

At each column $j = 1, \ldots, n-1$:

1. Enumerate transitions from each state in $\mathcal{S}_{j-1}$.
2. Compute new state with updated score.
3. **Beam prune**: sort $\mathcal{S}_j$ by score, keep top $K$ states.

Output: max-score state in $\mathcal{S}_{n-1}$ traces back to a 2-row band
solution.

## Sweep over band positions

A 2-row band covers $2 \times n$ cells out of $n^2$. To cover the full
puzzle, sweep:

- Band $r$: rows $r, r+1$ for $r = 0, 1, \ldots, n-2$.

For each band, solve independently. Chain solutions: band $r$'s bottom row
becomes band $r+1$'s top row (fixed).

**This is a sequential decomposition**: solve band 0 (top 2 rows), then
band 1 (rows 1-2, top row fixed = band 0's bottom row), etc.

## Border constraints

For the canonical 16×16 puzzle:
- Row $0$ (top border): each piece must have $T = 0$ (BORDER).
- Row $n-1$ (bottom border): each piece must have $B = 0$.
- Column $0$: pieces in column 0 must have $L = 0$.
- Column $n-1$: pieces in column $n-1$ must have $R = 0$.

These reduce the state space at boundary columns/rows.

## Tractability analysis

**State count per column** (beam=K): $K$ states.
**Transitions per state**: at most $|P|^2$, but border/uniqueness reduce.
**Total work**: $O(n \cdot K \cdot |P|^2)$ per band, $\cdot n$ bands.

For $n=16$, $K=10^4$, $|P|=256$: $16 \cdot 10^4 \cdot 256^2 \approx 10^{10}$
ops per band. At $10^7$ ops/sec (Python), that's $1000$ s = 17 min/band.
$16$ bands $\to$ ~5 hours total. Too slow in Python.

**In Rust** at $10^9$ ops/sec (with good cache layout): $10$ s per band,
$160$ s total. Tractable.

## Why this is novel

- All existing solvers explore cell-by-cell. This explores **column-by-column
  with 2 pieces per state** — exploits the inherent 2D structure.
- Beam search trades completeness for tractability.
- Multi-band chaining handles full-board.

Different from:
- **Vol-4 iterative widening** (concentric rings): center-out.
- **vanilla DFS** (row-major or border-first): single-cell at a time.
- **Blackwood algorithm** (vol-15): heuristic-side schedule, breaks adjacency
  constraints temporarily.

## Risks / open questions

1. **Beam pruning loses solutions**: a state pruned at column $j$ might
   have led to the global optimum. Mitigation: large $K$, multi-restart with
   different beam sizes.

2. **Multi-band chaining inconsistencies**: band $r$'s bottom row is
   committed before band $r+1$ starts. If the "globally optimal" puzzle
   needs band-0 to commit a specific row that band-1 can't extend, we lose.
   Mitigation: backtrack across bands, or join bands via larger DP.

3. **State-equivalence under piece-permutation**: hashing $\mathcal{U}_j$
   exactly is expensive; lossy hash (e.g., color-multiset only) might
   over-merge.

## Expected performance

Optimistic: $\geq 459$ on canonical, with multi-restart beam diversity.

Pessimistic: same plateau as ALNS (~444-452) because beam doesn't escape
basin in the same fundamental way.

Realistic: **NEW algorithm class** with different convergence properties.
Worth building to discover.

## Status

`design-complete` — ready to PoC on small puzzles (4×4, 6×6, 8×8).

## Linked

- [[INVENTIONS_BACKLOG]] J1 entry
- vol-4 iterative widening (related but different)
- vol-15 Blackwood (related schedule-based)
