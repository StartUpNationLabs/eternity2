---
name: literature-2026-06-bounds-wang
description: "vol-208 literature mining — (1) the published E2 MILP/Clique formulations (arXiv:1709.00252) are intractable beyond 7-8x8 and report NO sub-480 LP bound for 16x16; our PARQUET+strip-cut work is AT/BEYOND the published bound frontier. (2) Canfora-Cedeño 2026 (arXiv:2601.18968) Wang-tiling entropy classifier (good/bad alphabets via S_Γ(n)=log W_Γ(n)) — a hardness DIAGNOSTIC, but assumes no-rotation + infinite supply, so not directly E2; adaptable as a diagnostic only."
status: built
metadata:
  type: concept
---

# Literature mining (vol-208, 2026-06-10) — bounds + Wang-tiling stat-mech

## 1. Published E2 MILP/Clique bounds — we are at/beyond the frontier
**"MILP and Max-Clique based heuristics for the Eternity II puzzle"**, arXiv:1709.00252.
- MILP = **exactly our base formulation**: binary `x[t,r,c,α]` (tile t at (r,c) rot α),
  binary unmatched-edge `h_{r,c}` (right) / `v_{r,c}` (bottom), **minimize Σ unmatched**.
  Border forced to gray (color 0). Identical to PARQUET's per-edge model.
- Also a Max-Clique formulation (nodes = tile-placements, edges = no-conflict;
  find clique of size n²).
- **Intractable beyond 7×7–8×8** with CPLEX 12.6 / SOTA clique solver (1 day limit).
  10×10 clique graph file > 1 GB. **"The true EII instance is still far beyond the
  grasp of these models."**
- **They report NO LP-relaxation bound for 16×16** — they solve integer instances
  directly (≤8×8) and never discuss LP tightness at scale.

**Implication.** There is no published sub-480 LP/MILP bound on canonical E2. Our
[[parquet-overlapping-patch]] (base LP = 480.000) + [[MATH_NOTES_2026-06-10_strip_cut_bound]]
(window-integer cuts) are at or beyond the published bound frontier. A *sound* LP < 480
would be genuinely new — but no published soundness argument to crib; we're on our own
for cut validity. Confirms the bound direction is open AND hard (nobody has it).

## 2. Wang-tiling stat-mech entropy classifier (2026) — a diagnostic, not a bound
**Canfora & Cedeño, "Detecting the finer structure of P vs NP with statistical
mechanics: the Wang tiling problem"**, arXiv:2601.18968v1 (Jan 2026).
- Idea: a tile-alphabet Γ is **"good"** (poly-time tiling exists, "normal
  thermodynamics") vs **"bad"** ("chaotic", hard), decided by the entropy
  $S_\Gamma(n)=\log W_\Gamma(n)$ where $W_\Gamma(n)$ = # tilings of an n×n square.
  Good ⟺ $\partial S/\partial n>0$ (positive temperature → tiles arbitrarily large).
  Protocol II: the discrete map $S_\Gamma(n+1)=f_\Gamma(S_\Gamma(n))$ is regular for
  good alphabets, chaotic for bad ones (edge-of-chaos = the hard boundary).
- A finer-structure view of P vs NP: tractability depends on the *alphabet*, not
  just the problem — which maps onto E2 (the Selby-Riordan piece set is a specific,
  maximally-adversarial alphabet).

**MISMATCH with E2 (do not naively apply):**
- Their tiles **cannot rotate** (rule 1); E2 pieces are rotation-orbit-4.
- **Infinite supply** (tile the plane); E2 has **256 distinct pieces, no repeats**.
- Fixed 16×16 with all-distinct pieces ≠ "does Γ tile arbitrarily large n".
So $W_\Gamma(n)$ as defined is NOT E2's count. Adaptable only by redefining
$W^{E2}(n)$ = # valid all-matched n×n sub-tilings from E2's set WITH rotation and
WITHOUT repeat — computable for small n, but their good/bad *theory* assumes
no-rotation/infinite-supply, so the boundary may not transfer.

**Verdict.** A **diagnostic** lead (classify E2's hardness in a 2026 framework;
possible publishable cross-validation that E2 is "bad/chaotic"), NOT a record or
bound path. Logged to backlog as a diagnostic; the bound stays primary.

## Linked
- [[parquet-overlapping-patch]] — our base LP (the same MILP, =480)
- [[MATH_NOTES_2026-06-10_strip_cut_bound]] — the open bound attack
- [[academic-references]] — add both arXiv IDs
- [[dead-ends]] — neither method is a dead end, both are open/diagnostic
