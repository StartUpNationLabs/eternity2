---
name: w1-peps-design-derivation
description: "W1 design derivation. Hyperoptimized 2D PEPS contraction for E2. Confronts the vol-13 piece-uniqueness obstruction: local-message-passing cannot capture global permutation. Designs a *factor-augmented* PEPS where piece-pool sites enforce supply constraints. Three candidate encodings analyzed. Picks encoding C (piece-pool augmented PEPS with Lagrangian relaxation)."
metadata:
  type: project
status: partial
---

# W1 — PEPS contraction design for E2 (math derivation)

The 2024 Gray-Chan hyperoptimized PEPS contraction on rugged spin glasses
is *structurally inapplicable* to E2 as-given, for the same reason vol-13
boundary-MPS was refuted: **local-message-passing cannot enforce global
piece-uniqueness**. The vol-13 measurement: $Z^* \approx 7 \times 10^{93}$
boundary-consistent colorings vs. $\approx 10^{-8}$ expected solutions —
$10^{101}$ overcounting gap, all from the missing permutation constraint.

This page derives the encoding required to make PEPS work on E2.

## What spin glass PEPS does (and why it works there)

For an Ising spin glass on a 2D lattice $\Lambda$ with couplings $J_{ij}$:
$$
E(\mathbf{s}) = -\sum_{\langle i,j \rangle} J_{ij} s_i s_j, \quad s_i \in \{-1, +1\}
$$
the Boltzmann distribution is
$$
P(\mathbf{s}) = \frac{1}{Z(\beta)} e^{-\beta E(\mathbf{s})}, \quad
Z(\beta) = \sum_{\mathbf{s}} e^{-\beta E(\mathbf{s})}.
$$
Each site $i$ has its own 2-dim Hilbert space $\mathcal{H}_i = \mathbb{C}^2$.
The variables are **independent at each site** — every site has a "free"
local DOF that can take either value, and the interactions are
**pairwise local** between neighbors.

PEPS represents $P$ as a tensor at each site with bond indices to
each neighbor:
$$
P(\mathbf{s}) = \mathrm{Tr} \prod_{i} A^{(i)}_{s_i, \alpha_{i,N}, \alpha_{i,E}, \alpha_{i,S}, \alpha_{i,W}}
$$
where $\alpha_{i,d}$ is the bond connecting site $i$ to its neighbor in
direction $d$.

The per-site marginal at site $i$ is recovered by contracting the network
with $s_i$ fixed:
$$
P_i(s_i) = \frac{1}{Z} \sum_{\mathbf{s}_{-i}} P(\mathbf{s})
$$
which is a single PEPS contraction with one open leg.

**The algorithm** (Gray-Chan 2024):
1. For $\beta$ chosen in a schedule, compute $P_i(s_i)$ for all $i$.
2. Pick the site with most-peaked marginal; fix $s_i = \arg\max_{s_i} P_i(s_i)$.
3. Re-contract the (one-site-smaller) network; repeat.

Cost: $O(N^2)$ for fixed bond dim $\chi$ on short-range 2D lattices.

## The E2 obstruction

For E2, the site DOF is **not free**. Define $x_i \in [256] \times [4]$ =
the (piece, rotation) at cell $i$. The constraints are:
1. **Edge match** (local): if $i, j$ are neighbors with shared edge $e_{ij}$,
   then $\mathrm{edge}(x_i, \mathrm{dir}_{ij}) = \mathrm{edge}(x_j, \mathrm{dir}_{ji})$.
2. **Permutation** (global): $\sum_i \mathbb{1}[\pi(x_i) = p] = 1$ for each
   piece $p \in [256]$, where $\pi$ extracts the piece-id from $x$.

Constraint (1) is pairwise local — fits PEPS naturally.

Constraint (2) is **not local**: piece $p$ being used at cell $i$ excludes
$p$ from EVERY other cell. There is no bounded-neighborhood factor that
encodes this.

If we drop constraint (2), the model is exactly what vol-13 did:
edge-color matching with NO piece-uniqueness. Vol-13 found $Z^* \sim 10^{93}$
vs. true $\sim 1$, a $10^{93}$ overcount per missing global constraint.

So a faithful PEPS for E2 *must* somehow encode piece-uniqueness.

## Encoding candidates

### Encoding A — naive (piece-as-state, no global constraint)

State at cell $i$: $x_i \in [1024]$ (piece × rotation).
Edge tensor: $W_{ij}[x_i, x_j] = 1$ iff colors match, else 0.

Cell tensor: $A^{(i)}[x_i, \alpha_N, \alpha_E, \alpha_S, \alpha_W] = \mathbb{1}[\text{edges match bonds}]$.

**Problem**: Same as vol-13 — overcounts by $\sim 10^{93}$. Marginals
$P_i(x_i)$ will be near-uniform because piece-uniqueness isn't enforced,
so most cells will give wrong commitment.

### Encoding B — Lagrangian piece-uniqueness penalty

Add a Lagrangian to the energy:
$$
E_\lambda(\mathbf{x}) = E_{\text{color}}(\mathbf{x}) + \lambda \sum_{p=1}^{256} \left( \sum_i \mathbb{1}[\pi(x_i) = p] - 1 \right)^2
$$

For large $\lambda$, configurations with duplicated pieces are heavily
penalized.

**Problem**: The quadratic term is **non-local in PEPS** — it requires
all-to-all coupling among cells via the piece index. Pure PEPS topology
(2D nearest-neighbor) cannot represent it.

**Workaround**: Use **non-2D tensor network with extra "piece-pool" sites**
— see encoding C.

### Encoding C — augmented piece-pool PEPS (proposed)

**Idea**: Extend the network by adding 256 **piece-pool** sites $p_1, \ldots, p_{256}$.
Each piece-pool site $p_k$ has bonds to **every cell** $i$ via a "is this
piece $p_k$ at cell $i$?" indicator.

Topology:
- 256 cell sites arranged in 16×16 lattice (2D PEPS layer).
- 256 piece-pool sites in an additional "layer".
- Each cell site has 4 lattice bonds (N/E/S/W) + 256 piece-bonds, one per piece.
- Each piece-pool site has 256 cell-bonds.

Piece-pool tensor at site $p_k$:
$$
B^{(p_k)}[q_1, q_2, \ldots, q_{256}] = \mathbb{1}\left[\sum_i q_i = 1\right]
$$
where $q_i \in \{0, 1\}$. This is a **delta-of-sum tensor** — its
bond-dimension is $O(N)$ (not $O(2^N)$, because the sum is bounded).

Cell tensor at site $i$:
$$
A^{(i)}[x_i, \alpha_N, \alpha_E, \alpha_S, \alpha_W, q^{(i)}_{p_1}, \ldots, q^{(i)}_{p_{256}}] =
\delta(\text{color match}) \cdot \mathbb{1}[q^{(i)}_{p_k} = \mathbb{1}[\pi(x_i) = p_k] \forall k]
$$

Piece-bond dimension: 2 (the indicator $q$).

**Cost analysis**:
- Cell has 4 local bonds (each of dim 23, for colors) plus 256 piece-bonds
  (each of dim 2).
- Per-cell tensor size: $1024 \times 23^4 \times 2^{256}$ — DENSE,
  intractable.
- But SPARSE: tensor is non-zero only on configurations where exactly
  one $q^{(i)}_{p_k} = 1$ (the one matching $\pi(x_i)$). So effective
  per-cell representation is $1024 \times 23^4 \times 256$ = ~$10^9$.

Even with sparsity, the network has 256-dimensional piece-bonds and the
piece-pool tensor is delta-of-sum across 256 indices. Direct contraction
is intractable.

**The right approach**: Approximate the piece-pool factor by **mean-field
shadow prices** $\mu_p \in \mathbb{R}$ — a Lagrangian. The pool factor
$\mathbb{1}[\sum_i q_i = 1]$ is replaced by $e^{-\mu_p (\sum_i q_i - 1)}$.
Now the pool factor decouples into a product over cells:
$$
B^{(p_k)} \approx \prod_i e^{-\mu_{p_k} q^{(i)}_{p_k}} \cdot e^{\mu_{p_k}}.
$$

Then the cell tensor absorbs $e^{-\mu_p q^{(i)}_p}$ for each piece $p$ in
its piece-bond indices, eliminating the piece-pool sites entirely:
$$
\tilde A^{(i)}[x_i, \alpha_N, \alpha_E, \alpha_S, \alpha_W] = \delta(\text{color match}) \cdot e^{-\mu_{\pi(x_i)}}.
$$

Now the network is a **2D PEPS with per-cell Boltzmann weight $e^{-\mu_{\pi(x_i)}}$**.

**The $\mu$'s are learned iteratively**: at each iteration,
1. Solve PEPS with current $\mu$'s; compute per-piece expected usage $\langle q_p \rangle = \sum_i P_i(\pi(x_i) = p)$.
2. Update $\mu_p \leftarrow \mu_p + \eta (\langle q_p \rangle - 1)$ (gradient
   descent on the Lagrangian dual).
3. Repeat until $|\langle q_p \rangle - 1| < \epsilon$ for all $p$.

This is exactly **dual decomposition** on the Lagrangian, with PEPS as
the inner solver.

### Comparison to existing methods

- **vol-22 bound-ascent**: Lagrangian dual on per-color piece-supply, NOT
  per-piece. Different relaxation (looser).
- **vol-44 cell-pair LP**: full LP relaxation, gives 478 UB. PEPS-Lagrangian
  is the *non-linear / tensor-network* generalization — handles
  multi-edge correlations LP misses.
- **PCLS (J4, refuted)**: per-color LP. Per-piece Lagrangian (encoding C) is
  finer-grained than per-color.

## What encoding C gets us that vol-13 didn't

Vol-13 boundary-MPS: no piece-uniqueness, gives $Z^* / Z_{\text{true}} \sim 10^{93}$.

Encoding C with Lagrangian: at the optimum of the dual, $\langle q_p \rangle = 1$
for all pieces. The PEPS marginals are **piece-balanced** — no piece
over-used, none under-used. This recovers the missing $10^{93}$ factor.

## Practical cost

- 2D PEPS contraction on 16×16 with per-site Hilbert dim 1024 at bond
  dim $\chi$: $O(N^2 \chi^4 d^4)$ where $d = 1024$. For $\chi = 16$,
  $d=1024$: $16^4 \times 1024^4 \approx 6.5 \times 10^{16}$ per
  contraction. Intractable.

- **Reduction 1**: Don't enumerate all 1024 states per site. The cell
  tensor is sparse — most $(x_i, \alpha)$ tuples are zero. Use COO-like
  representation; effective $d_\text{eff} \approx 256$ or less.

- **Reduction 2**: Use the **edges-as-variables** formulation. Each interior
  edge $e_{ij}$ has a color $c_{ij} \in [23]$. Cell-validity tensor: given
  4 incident edges, is there a piece + rotation matching? Bond dim 23.
  Cost: $16^4 \times 23^4 \approx 2 \times 10^{10}$ per contraction —
  tractable.

- **Reduction 3**: The Lagrangian dual is solved via $\sim 50-100$ outer
  iterations of PEPS contraction. Total: $10^{12}$ FLOPs per Lagrangian
  iteration × 100 iter = $10^{14}$ FLOPs. On a modern GPU ($10^{12}$
  FLOPs/s = 1 TFLOPS), this is $10^2$ seconds per E2 attempt. Feasible.

## Plan

1. **Phase 1 — formulation verification** (1 week).
   - Build the edges-as-variables PEPS with Lagrangian.
   - Test on 6×6 generated puzzle: verify Lagrangian dual converges to
     $\langle q_p \rangle = 1 \forall p$. Verify per-cell marginals
     concentrate on the true assignment.
   - Pure Python + `cotengra` + `opt_einsum`.

2. **Phase 2 — sequential piece-fixing** (1 week).
   - On 6×6 and 8×8: at convergence of Lagrangian dual, pick most-peaked
     cell, fix that piece, re-solve. Iterate.
   - Compare against `solver-engine joe` profile.

3. **Phase 3 — canonical scale** (2 weeks).
   - Port hot loops to Julia or Rust; use distributed contraction.
   - Tune $\chi$ schedule, Lagrangian step size $\eta$, $\beta$ schedule.
   - Run on canonical E2. Target: score ≥ 460.

4. **Phase 4 — record attack** (1-2 weeks).
   - If phase 3 produces a 459+ partial: pipe to ALNS basic 30min × N seeds.
   - If a 460+ partial: stop, verify, claim.

## Cost vs vol-13

| Aspect | vol-13 boundary-MPS | W1 PEPS-Lagrangian |
|---|---|---|
| Variables | Edge colors only | Cells with piece-id + rotation |
| Topology | 1D (boundary sweep) | 2D PEPS + Lagrangian per piece |
| Piece-uniqueness | NONE | Lagrangian dual |
| Overcount | $10^{93}$ | 0 (at dual optimum) |
| Per-site marginal | Yes (vol-13 measured) | Yes (vol-13 method) |
| Sequential fix | NO (used as value-order only) | YES (Gray-Chan 2024) |

## Open questions / risks

1. **Lagrangian dual convergence**. Does the gradient descent converge to
   $\langle q_p \rangle = 1$? Vol-22 found bound-ascent on per-color
   collapses to wrong score. **W1 differs** because (a) per-piece not
   per-color, (b) it's marginal-driven not score-driven.

2. **PEPS error at $\chi$**. The 2024 paper reports 1-2% error at 48×48
   for spin glass. For E2 the variable space is bigger (256 piece-states
   vs 2 spin-states). May need larger $\chi$. If $\chi=64$ needed at
   $d=23$, cost is $64^4 \times 23^4 \times N^2 \approx 5 \times 10^{12}$
   FLOPs per contraction = manageable.

3. **Tied marginals**. If multiple cells tie at $\max P_i$, which to fix
   first? Heuristic: lowest entropy.

4. **Coupling to solver-engine**. After PEPS fixes $k$ cells, the
   remaining $256-k$ cells can be filled by CSP. Pipeline integration is
   straightforward via the partial-board JSON format.

## Linked

- [[boundary-mps]] (vol-13 refuted; the key obstruction)
- [[bp-marginals]] (vol-11/12 BP measurements; baseline)
- [[edge-bp-measurement]] (vol-12 18.84% reduction)
- [[k11-cross-domain-brainstorm]]
- [[web-roam-2026-05-17]] (W1 entry)
- [[bound-ascent]] (vol-22; Lagrangian per-color predecessor)
- [[vol122-pcls-poc-result]] (J4 refutation of per-color supply)

## Citations

- Gray, Chan. "Hyperoptimized Approximate Contraction of Tensor Networks
  with Arbitrary Geometry." *PRX* 14, 011009 (2024).
- Liang et al. "Hyperoptimized approximate contraction of tensor networks
  for rugged-energy-landscape spin glasses on periodic square and cubic
  lattices." *Phys. Rev. E* 110, 065306 (2024).
- Vol-13 boundary-MPS refutation.
