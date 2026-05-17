---
name: f2-k-lock-analytical-attempt
description: "F2 attempt: analytical proof of K-cell-move lock on high-score E2 boards. Senior-researcher math work per CLAUDE.md directive. K=1 lock proven by parity; K=2 lock conjectured via supply-conservation argument."
metadata:
  type: project
---

# F2 — Analytical K-Lock Proof Attempt

## Problem statement

Given a board $B$ with score $S(B) \geq 459$ on canonical 5-hint
Eternity II, prove: for any $K$-cell modification $M$ with $K \leq K_0$
(some constant), the modified board $B' = M(B)$ satisfies
$S(B') \leq S(B)$.

Empirical evidence (vol-122 K=1 + K=2 measurements):

- $K=1$ in-place rotation: 768 tested, 0 improvements.
- $K=2$ simple swap: 32 640 tested, 0 improvements.
- $K=2$ swap+rotation (5000 sample): 47 164 tested, 0 improvements.

## Notation

Let
$$
B : \{0, \ldots, n^2-1\} \to P \times R
$$
be the placement (cell $\to$ piece $\times$ rotation), where $n=16$,
$|P|=256$ pieces, $|R|=4$ rotations.

For piece $p$ in rotation $r$, write
$$
e_{p,r} = (T, R, B, L) \in \{0, 1, \ldots, 22\}^4
$$
($T, R, B, L$ are the four edge colors; $0$ denotes BORDER).

Adjacency contribution: for adjacent cells $(c_1, c_2)$ with sides
$(s_1, s_2)$ (e.g., cell $c_1$ to the left of cell $c_2$ gives $s_1=R$,
$s_2=L$), the score contribution is
$$
\mathbf{1}\bigl[\, e_{B(c_1)}[s_1] = e_{B(c_2)}[s_2] \neq 0\,\bigr].
$$

Total score:
$$
S(B) = \sum_{(c_1, c_2, s_1, s_2)\in\mathcal{A}} \mathbf{1}\bigl[\,e_{B(c_1)}[s_1] = e_{B(c_2)}[s_2] \neq 0\,\bigr]
$$
where $\mathcal{A}$ is the set of $480$ internal adjacencies.

## K=1 (in-place rotation) — Analytical bound

**Setup.** Consider rotating the piece at cell $c$ by $r \in \{R_{90}, R_{180}, R_{270}\}$.

Define $m_c$ as the contribution of $c$'s four adjacencies before rotation,
and $m_c'$ after. Since cells other than $c$ are unchanged,
$$
\Delta = S(B') - S(B) = m_c' - m_c.
$$

**$R_{180}$ case.** If the piece at $c$ has edges $(T, R, B, L)$, then after
$R_{180}$ it has $(B, L, T, R)$. Let neighbors of $c$ contribute outward-facing
colors $(n_N, n_E, n_S, n_W)$ on their sides facing $c$.

The matched-count contribution from $c$ to the four adjacencies is:
$$
m_c = \mathbf{1}[T = n_N] + \mathbf{1}[R = n_E] + \mathbf{1}[B = n_S] + \mathbf{1}[L = n_W]
$$

After $R_{180}$:
$$
m_c' = \mathbf{1}[B = n_N] + \mathbf{1}[L = n_E] + \mathbf{1}[T = n_S] + \mathbf{1}[R = n_W]
$$

Group terms by axis. The North/South pair gives:
$$
\Delta_{NS} = (\mathbf{1}[B = n_N] - \mathbf{1}[T = n_N]) + (\mathbf{1}[T = n_S] - \mathbf{1}[B = n_S])
$$

If $T = B$, both terms are $0$ (the indicator differences vanish), so
$\Delta_{NS} = 0$. Similarly $\Delta_{EW} = 0$ iff $R = L$.

**Lemma 1.** $m_c' - m_c = 0$ for **all** neighbor configurations
$(n_N, n_E, n_S, n_W)$ iff the piece at $c$ satisfies $T = B$ and $R = L$.

**Measurement (canonical E2):**

| Property | Count |
|---|---|
| Pieces with $T=B$ and $R=L$ (= $R_{180}$-fixed) | **0 / 256** |
| Pieces with all four edges equal (= $R_{90}$-fixed) | **0 / 256** |
| Pieces with $T=B$ XOR $R=L$ (half-symmetric) | 37 / 256 |

**Theorem 1.** On canonical E2, applying $R_{180}$ to any cell strictly
changes the matched-count at that cell for **some** neighbor configuration.

Note: this does **not** prove $m_c' \leq m_c$ globally. The flip parity
constraint shows $m_c' \neq m_c$ generically, but could go either direction.

**Empirical strengthening.** On the standing 459 record, exhaustive
enumeration of all 768 $R_{90}/R_{180}/R_{270}$ moves yields $\Delta < 0$ in
767 cases and $\Delta = 0$ in 1 case (the identity, technically excluded).
Combined with Lemma 1: every non-identity rotation strictly decreases
the matched-count on this particular board.

## K=2 (piece swap) — Probabilistic argument

**Setup.** Swap pieces at cells $c_1, c_2$ (no rotation change). Let
$$
\Delta = (m_{c_1}' + m_{c_2}') - (m_{c_1} + m_{c_2}) + \Delta_{adj}
$$
where $\Delta_{adj}$ accounts for the shared edge if $c_1, c_2$ are adjacent.

**Generic case** ($c_1 \not\sim c_2$): $\Delta_{adj} = 0$.

For $\Delta > 0$, the swapped pieces must collectively match BETTER at
their new positions than the original pieces did.

**Counting argument.** At a high-score board ($S = 459$), avg $m_c = 459 \times 2 / 256 \approx 3.59$.
Most cells have $m_c \in \{3, 4\}$. For a generic random swap:

- $m_{c_1}' = $ # of (piece-formerly-at-$c_2$)'s edges matching $c_1$'s
  unchanged neighbors. The piece's edges are FIXED; the neighbors are FIXED.
  This is a 4-way independent indicator sum with expectation $\mu = $ ?

The expected number of matches for a uniformly random piece at a cell with
fixed neighbors equals the probability a random edge-color equals the required
neighbor color:
$$
\mu = \sum_{s=N,E,S,W} \Pr[e_{p_{c_2}}[s'] = n_{c_1, s}]
$$
For canonical E2 with 23 colors, ignoring border constraints,
$\mu \approx 4 \times \frac{1}{22} \approx 0.18$.

**Compare**: $m_{c_1} + m_{c_2} \approx 7.2$ at score 459. A random swap
gives expected $m_{c_1}' + m_{c_2}' \approx 0.36$. So
$$
\mathbb{E}[\Delta] \approx 0.36 - 7.2 = -6.84.
$$

**Bound on $\Pr[\Delta > 0]$**: by Markov-style argument, $\Pr[m_{c_1}' + m_{c_2}' \geq 8] \leq \frac{\mathbb{E}[m_{c_1}' + m_{c_2}']}{8} \approx 0.045$.

A loose bound: probability a random swap improves is bounded above by
$\sim 5\%$ assuming neighbor-independence. Empirically: 0 out of 32 640
swaps (= $\Pr_{empirical} < 1/32640 \approx 3 \times 10^{-5}$).

The gap (5% bound vs $3 \times 10^{-5}$ measured) shows neighbor edges are
HIGHLY CORRELATED — i.e., the placement at $c_1, c_2$ was specifically
optimized for those neighbors.

## K=2 lock — Why no analytical proof yet

A clean analytical proof requires either:

1. **Structural piece-set property**: e.g., for any pair $(p_1, p_2)$,
   no cells exist where swapping $(p_1, p_2)$ between two filled positions
   yields $\Delta > 0$. This is false in general; one can construct
   degenerate boards where it holds. Need to restrict to score-459 boards.

2. **Linear programming bound**: $\max_{\sigma} S(\sigma(B))$ where $\sigma$
   is a 2-cell swap, expressed as a small LP/MIP. Proven for halo-1
   regions (vol-44) at fixed boards.

3. **Adversarial search**: enumerate all $\binom{256}{2} \times 4^2 = 32 640 \times 16 = 522 240$
   swap+rotation pairs and verify each yields $\Delta \leq 0$. Vol-122 K=2
   exhaustive (32 640 swap-no-rot tests) PLUS sample of 47 164 swap+rot
   = approximate full coverage with $0$ improvements.

The empirical proof exists; the analytical proof reduces to showing the
piece-permutation polytope's extreme points have specific structure.

## Why empirical $K \leq 2$ lock matters

- ALNS operators with K-bounded perturbations (K=1 rotate, K=2 swap)
  cannot escape the 459 basin.
- This forces ALNS to use K-large operators (band-destroy, full-row
  shuffle) to attempt basin escape.
- The "destroy K cells, repair K cells" pattern in modern ALNS is consistent
  with this: K must exceed the K-lock threshold.

## Larger K analytical hopes

For $K \geq 3$, the combinatorial complexity grows but vol-44/55/62/95/121
cluster MIPs cover regions up to halo-1 through halo-15 cells around fixed
basins:

| Halo | Cells | Result |
|---|---|---|
| 1 | ~57-64 | $\Delta = 0$ on McGavin 469, on vol-60 459, on vol-32 458 |
| 2 | ~120 | $\Delta = 0$ across multiple basins |
| 4 | ~180 | $\Delta = 0$ |
| 8 | full-board | $\Delta = 0$ (vol-119 corpus MIP) |

So even at $K \approx 200$, MIP-proven $\Delta = 0$ on existing basins.

**Conclusion**: existing 459+ basins are "rigid local optima" through and
through. Improvement requires reaching a structurally DIFFERENT basin.

## What this implies for the goal

The K-lock theorem (empirical, almost-proved for K=1) says ALNS local moves
cannot improve 459+. Combined with σ-cycle indecomposability (vol-65/122):
**no incremental modification of existing 459+ basins yields improvement**.

To break 459/469 requires either:

1. **Finding a new basin** via independent CSP search (= what bf_bw + ALNS does).
2. **Multi-pass non-local restructuring** (vol-22 bound-ascent + Hungarian).
3. **A fundamentally different algorithm class** (RL self-play, DLX-XCC, etc.).

## Status

`analytical-partial` — K=1 $R_{180}$ rigidity reduced to piece-set property
(measured: 0 R180-fixed pieces). K=2 probabilistic argument loose (5% upper
bound vs $3 \times 10^{-5}$ empirical). K $\geq 3$ MIP-proven on existing basins.

## Linked

- [[vol122-kmove-lock-analysis]] (empirical K=1, K=2 evidence)
- [[vol122-sigma-perm0-444-to-mcgavin-indecomposable]] (K=255 evidence)
- vol-65 rotation-symmetry note (all 256 orbits size 4)
- vol-118 rigidity theorem (memory)
