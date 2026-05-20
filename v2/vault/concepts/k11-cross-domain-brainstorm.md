---
name: k11-cross-domain-brainstorm
description: "Brainstorming cross-domain framings for E2: wave mechanics, optics, information theory. Each candidate evaluated for what NEW operational structure it introduces beyond CSP/MIP/ALNS."
metadata:
  type: project
status: built
---

# K11 — Cross-domain brainstorm: waves, optics, information theory

Per user directive (2026-05-17 ~15:55 CEST): "could we try brainstorming
result 1, 2 and/or 4? Or all of them you know what".

## 1. Wave-mechanics framing

### Concept

Each color is a wave with a specific **frequency** $\omega_c$ (one of
22 distinct values). Each piece is a "scattering site" that emits/absorbs
waves at its 4 edges (top, right, bottom, left).

**Matching** = constructive interference between adjacent pieces.
**Mismatch** = destructive interference (out-of-phase / different
frequency, depending on encoding).

### Mathematical model

Let $\Psi(\mathbf{r}, t) = \sum_c A_c(\mathbf{r}, t) e^{i \omega_c t}$ be a
multi-component wavefunction over the 16×16 grid. At each cell, $\Psi$
decomposes into 4 "edge modes" — one per side.

The "Hamiltonian" of the puzzle:
$$
H = -\sum_{\langle i, j \rangle} J_{ij}^{(c_i, c_j)} \cos(\omega_{c_i} - \omega_{c_j})
$$

where $J_{ij}$ is the coupling between adjacent cells $i, j$ on their
shared edge with respective face colors $c_i, c_j$.

**Ground state** = arrangement minimizing $H$. Matched edges contribute
$-J$ (lowest energy); mismatched contribute $0$ or positive.

### What operational structure does this give?

- **Spectral analysis of the Hamiltonian**: eigenmodes of $H$ on a
  partial board reveal "soft" directions where small changes (piece
  swaps) significantly reduce energy. Maps onto SPECTRAL OPTIMIZATION,
  which is well-studied for similar systems.
- **Wave propagation**: a "defect" at cell $i$ (mismatch) generates
  outgoing wave $\propto e^{i k \cdot (r - r_i)}$. The defect's INFLUENCE
  has finite spatial extent set by the coupling strength. Identifies
  the "blast radius" of a mismatch: how far does it perturb the
  surrounding lattice?

### Connection to existing tools

- The Hamiltonian framing IS the Potts-like spin glass formulation
  already tried (vol-13 boundary-MPS, refuted). The wave-mechanics
  language is a SUPERFICIAL relabel of the same energy landscape.
- Spectral analysis of the COUPLING MATRIX (piece-piece compatibility)
  was tried (vol-122 J3, refuted — interior has flat spectrum).

### What's NEW

**Wave-packet dynamics**: simulate time-evolution of an initially
LOCALIZED wave packet centered on the standing 459 board. Does the
wavefunction "tunnel" to a higher-score basin via classical-forbidden
configurations?

This is genuinely novel — never tried in this project. PoC ~1 day.

### Cost

- 22 colors × 16×16 grid × time-evolution = $10^4$ DOF.
- Schrodinger evolution in Crank-Nicolson: $O(N^2)$ per step = $10^8$ ops.
- 1000 time steps = $10^{11}$ ops. Borderline tractable in Rust with
  scipy in Python.

## 2. Light / optics framing

### Concept

Each color is a wavelength $\lambda_c$ in a virtual "color spectrum"
ranging from $\lambda_{\min}$ to $\lambda_{\max}$ for 22 colors.

The piece edges act as TRANSMITTERS and RECEIVERS of light. A matched
edge = "transparent" (light passes). A mismatched edge = "reflective"
(light bounces).

The board is "illuminated" from outside; we measure the TRANSMITTED
LIGHT — equivalent to following "ray paths" through the matched-edge
network.

### Mathematical model

Define $T(\mathbf{r}, \lambda)$ = transmissivity of cell-edge at $\mathbf{r}$
for wavelength $\lambda$.
$T = 1$ if the edge is matched at color = $c(\lambda)$, $0$ otherwise.

Light enters at the border (16 entries per side) at various wavelengths
and traverses the board until it exits or is absorbed.

**Quality metric**: $\sum_\lambda \text{Transmitted}(\lambda)$ =
total light that exits.

### What operational structure does this give?

- **Ray-tracing as path-finding**: traversing the matched-edge graph
  finds CONNECTED REGIONS of matched edges. A high-score board has
  more transmissive paths.
- **Reflection symmetry**: a ray that enters at border position $i$
  and exits at border position $j$ defines a "transmission channel".
  The channel matrix $T_{ij}$ has properties (rank, eigenvalues) that
  may correlate with score.

### Connection to existing tools

The "ray-traversal" of matched edges is essentially CONNECTED-COMPONENT
analysis on the matched-edge SUB-graph. K9 / vol-44 / vol-118 already
analyzed matched-edge clusters.

But: ANALYZING THE TRANSMISSION CHANNEL MATRIX directly is **new**. The
matrix's rank, condition number, and eigenstructure may reveal
properties of the matched-edge network that scalar mismatch-count
doesn't.

### What's NEW

**Transmission channel rank**: how many INDEPENDENT light paths cross
the board? For a complete matched board, rank ≈ 16 (full transmission).
For a 459 board with 4 small mismatch clusters, rank ≈ 12-13 (mismatched
clusters block some paths). For a 458 with 2 large clusters, rank ≈ ?.

If channel rank correlates strongly with score, it's a new scoring
function. Cost: $O(16^3) = 4096$ per board to compute SVD.

PoC ~1h. Worth doing.

## 4. Information theory framing

### Concept

The puzzle as a NOISY CHANNEL: each placed piece "transmits" a 4-bit
color signature to its neighbors. Adjacent pieces "receive" expecting
the matching color. A matched edge = correct symbol; mismatch = error.

**Shannon channel capacity** of the puzzle = max information rate
achievable.

### Mathematical model

Source: 256 piece-rotation tuples (each a 4-color symbol). 
Channel: rotation noise + position noise (which piece goes where).
Receiver: edge-matching agent that compares left and right colors at
each edge.

**Information rate**: $I = $ matched-edges / 480 × $\log_2(22)$ bits/edge.

For matched = 459: $I = 0.956 \times 4.46 = 4.26$ bits per available edge,
or 1957 bits total board.

For random: $I \approx 1/22$ per edge.

### What operational structure does this give?

- **Mutual information between pairs of cells**: if cells $i, j$ are
  "near" in the search space, $I(p_i; p_j)$ should be high.
- **Compressibility**: a good board has low complexity / high
  predictability of the next piece given the prefix.

### What's NEW

**Compression-based scoring**: compute the Lempel-Ziv complexity (or
arithmetic coding length) of the board's row-major or column-major
piece-id sequence. **Hypothesis**: high-score boards COMPRESS BETTER
because they have more structure.

PoC: implement LZ77 / arithmetic coding for piece-id sequences,
measure compression ratio across 459/458/457/444 boards.

This is genuinely new. Cost: 30 min Python.

## Recommended priorities

If picking ONE: **Idea 2's transmission channel rank** because:
- Concrete PoC (~1h).
- Sums over all 16×16 paths — uses GLOBAL information, not just local
  adjacency.
- Could be a new BASIN SIGNATURE that discriminates 458 from 459.

If picking TWO: 2 + 4. The compression-based scoring (4) is independent
of channel rank (2) and may catch DIFFERENT structure.

If picking THREE: 2 + 4 + the wave-packet dynamics from 1. Wave packet
dynamics is genuinely new but more speculative.

## Status

`brainstorm-complete`. Implementation pending (PoC for #2 next).

## Linked

- [[feedback-invent-cross-domain]] (directive)
- [[k8-fft-signature-refuted]] (early attempt)
- [[k9-mismatch-topology-finding]] (rediscovered vol-118)
