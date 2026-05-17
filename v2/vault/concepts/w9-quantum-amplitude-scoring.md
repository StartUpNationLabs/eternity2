---
name: w9-quantum-amplitude-scoring
description: "W9 INVENTION: encode color matching via complex amplitudes. Each interior edge contributes e^(i*θ_c) for color c. Board score = |sum of amplitudes|². Mismatched edges contribute partial interference; matched edges fully constructive. Enables continuous optimization + new objective function."
metadata:
  type: project
---

# W9 — Quantum-amplitude scoring (NEW INVENTION, vol-123 close)

## The idea

Standard E2 score = count of matched interior edges (binary: matched/unmatched).
This is a discrete, all-or-nothing measure.

**W9 INVENTION**: replace the discrete count by a **continuous amplitude sum**.

For each interior edge $e$ between cells $a$ and $b$:
- Let $c_a$ = color emitted by cell $a$ on side facing $b$.
- Let $c_b$ = color emitted by cell $b$ on side facing $a$.
- Edge amplitude: $A_e = e^{i \theta_{c_a}} + e^{i \theta_{c_b}}$
  where $\theta_c \in [0, 2\pi)$ is a per-color phase parameter.

Total board amplitude: $A_{\text{total}} = \sum_e A_e$.

Board score: $|A_{\text{total}}|^2$.

## Why this is interesting

1. **Continuous gradient**: small changes in piece placement give continuous
   changes in $|A_{\text{total}}|^2$. Enables gradient-based optimization
   (vs discrete count which is 0/1 per edge).

2. **Color geometry**: the phases $\theta_c$ encode a **geometry on color space**.
   E.g., if $\theta_c = 2\pi c / 22$ for $c = 1..22$, then colors are evenly
   spaced on the unit circle. Mismatched edges between colors $c_1, c_2$
   contribute $|e^{i\theta_{c_1}} - e^{i\theta_{c_2}}|^2 = 2 - 2\cos(\theta_{c_1} - \theta_{c_2})$.
   "Close" colors (small phase difference) contribute small penalty;
   "far" colors contribute up to 4.

3. **Encoding rare-color geography (vol-13)**: assign phases so rare colors
   {1-5} get a separate phase class from common colors. This builds vol-13's
   structural insight into the objective.

4. **Reformulated as a Hermitian matrix**: with $N = 480$ edges, define
   the $K \times K$ "match-strength" matrix $M$ where $M_{ij} = $ count of
   edges between color $i$ and color $j$. Then
   $|A|^2 = \sum_{i,j} M_{ij} \cdot 2 + 2 M_{ij} \cos(\theta_i - \theta_j)$.
   For matched edges $i = j$: contribution is $4 M_{ii}$.
   For mismatched: less. Maximizing $|A|^2$ over $\theta$ AND piece placements
   becomes a JOINT optimization problem.

5. **Compatible with W1 PEPS**: each cell tensor can be augmented with a
   Boltzmann weight $e^{-\beta \cdot \text{(edge amplitude}^2)}$. The
   tensor network now has *complex-valued* tensors. PEPS contraction works
   the same way.

## Concrete first step

**Day 1: Validate on 4×4.**
- Choose phases $\theta_c = 2\pi c / K$ for $c = 1..K-1$ (uniform).
- Compute $|A_{\text{total}}|^2$ for the known 4×4 solution. Should equal
  $4 \cdot $ (matched edges) for the perfect solution (all phases align).
- For non-solutions, compute the "amplitude defect".

**Day 2: Optimize phases.**
- For the canonical E2, run gradient descent on $\theta_c$ with the 5 hints
  fixed. Find phases that MAXIMIZE the "geometry distance" between far
  colors and minimize between similar pieces.

**Day 3-4: Joint optimization.**
- Continuous optimization of phases + ALNS-style discrete optimization of
  piece placements. Alternating updates.

**Day 5: Test on canonical E2.**
- See if the new scoring function helps ALNS escape the 459/448 plateaus.

## Why this is a real W9 invention (not a tweak)

- Vol-13 measured color geography but used DISCRETE matching.
- Vol-44 used per-color LP but on the BINARY match count.
- Vol-122 explored cross-domain (foam, music, etc.) but not amplitude-based.
- **No prior vol used complex amplitudes** in the scoring function.

The complex amplitude formulation is GENUINELY NEW for E2.

## Risks / why it might not work

1. The maximum of $|A|^2$ might not correspond to maximum matched edges.
   If two different colors have very close phases, the amplitude is still
   high even though the edge is "mismatched".
   
   **Mitigation**: choose phases to be MAXIMALLY SPREAD (e.g., uniform).

2. The continuous landscape might have many local maxima.

3. Computational cost of $|A|^2$ is O(n_edges) per evaluation — same as
   discrete count. No speedup, just different optimization geometry.

## What this could SOLVE

If the continuous gradient gives access to optimization paths that the
discrete count doesn't, we might break out of operator-locked plateaus
(459 record, 458 strict-canonical).

It's also a candidate for a **new scoring metric** that complements existing
ones, enabling new ALNS heuristics.

## Linked

- [[rare-color-rule]] (vol-13 phase-of-color analog)
- [[w1-peps-design-derivation]] (PEPS extension natural)
- [[../plans/INVENTIONS_BACKLOG]] (will be added as W9)
- [[../plans/SOLVING-E2-VISION]] (alternative path)
