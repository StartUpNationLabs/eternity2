# Prior-Guided ALNS (V169 / "OPHIDIA")

Status: `partial` (math written 2026-05-20, implementation in progress)
Origin: vol-169 (this volume)
Files: `crates/localsearch/src/alns.rs::PriorDestroy`, `crates/bench-audit/src/bin/alns_only.rs` (flag `--prior-destroy`).
Naming: **OPHIDIA** — the destroy operator slithers along weakly-supported cells.

## Motivation

V155 (PRIOR data-augmented beam) reaches 460/480 from-scratch in 4–238s. After
that, conventional ALNS (basic_lkh) lifts a 456 V155 build to 460 in ~30min, but
**plateaus at 460**. Vol-156 → Vol-163 sweeps confirm:

- 156: 2/7 ALNS seeds reach 460 from V155-456. None reach 461.
- 160: K=64–256 builds × 4 seeds ALNS — best 460.
- 162: 16 seeds, K=4096 high459 → **all 16 identical board** (1 unique hash). Seed-tiebreak is a null axis.
- 163: 480 builds × 80 seeds — only `high459+row` reached 460, all 80 same hash.

**Diagnosis**: ALNS destroy operators (`RandomRegion`, `WorstWindow`, `ConflictDriven`,
`MwpmDefectPair`, `WorstBand`, `LkhChainDestroy`) are *spatially heuristic* but
*history-blind*. They do not know which cells V155 was confident about
(piece-position pair frequently observed in high-score corpus) vs which cells V155
guessed (piece-position pair never observed; placed by tiebreak).

**Hypothesis**: cells with low corpus support are the weak link. Targeting them
preferentially for destroy should break the 460 ceiling.

## Math

### Definitions

Let `P : [0, N_pieces) × [0, N_positions) → ℕ` be the empirical count matrix
from a corpus of $B$ high-score boards above some threshold $\tau$ (canonically
$\tau = 459$, $B = 49$):

$$
P(p, c) = \big|\{\,b \in \mathcal{B}_\tau \,:\, b[c] = p\,\}\big|
$$

For a board $b$ with placement function $b[\cdot]$, the **cell prior support** is

$$
s_b(c) := P(b[c],\ c) \in [0, B].
$$

A cell with $s_b(c) = 0$ is **unsupported**: the piece at $c$ was never observed at $c$ in
any $\tau$-corpus board. A cell with $s_b(c) = B$ is **maximally supported**: the
piece appears at this exact position in every corpus board.

### Destroy distribution

Define **cell weakness**:

$$
w_b(c) := \exp\!\big(-\beta \cdot s_b(c)\big), \qquad \beta > 0.
$$

This is a Boltzmann-style weakness: small $\beta$ → near-uniform; large $\beta$ → spike on $s = 0$ cells.

The **prior-guided destroy seed distribution** is

$$
\Pr(\text{seed}=c) \;=\; \frac{w_b(c)}{\sum_{c'} w_b(c')}.
$$

Choosing $\beta$:
- $\beta = 0$: uniform random seed (= `RandomRegion`'s seed).
- $\beta = 1/B$: gentle preference, weakness ratio across $s \in [0,B]$ is $e \approx 2.72$.
- $\beta = 4/B$: strong preference, ratio $e^4 \approx 55$.
- $\beta = \log B$: $s = 0$ outweighs $s = B$ by factor $B$.

### Grow-region

Once seed $c_0$ is chosen, grow a BFS region by visiting orthogonal neighbors and
adding them in **weakness-priority order** (max-heap by $w_b(\cdot)$) until $k$ cells
are collected. Equivalent to: "starting at the weakest cell, propagate through the
weakest neighbors until the region has $k$ cells".

This concentrates destroy on a *contiguous patch of weakly-supported cells*,
maximizing the chance that the region admits a *higher-scoring repair* than the
current weakly-supported placement.

### Why the existing ops don't suffice

| Op | Targets | Prior-aware? |
|---|---|---|
| `RandomRegion(k)` | uniform k×k window | no |
| `WorstWindow(k)` | low-density k×k window (by matched-edges) | **partial** (density ≈ inverse weakness for matched edges, but the prior tracks corpus support, which is a different signal) |
| `ConflictDriven` | mismatched-edge seed + BFS | only via edge mismatches |
| `MwpmDefectPair` | min-weight matching on defects | only via defects |
| `WorstBand(k)` | k-row band with worst density | row-density only |
| `LkhChainDestroy` | gain-tracking chain | gain signal |
| **`PriorDestroy` (V169)** | low-corpus-support region | **yes** |

The new signal is orthogonal to all existing ops. The corpus prior captures
positional preferences (e.g., which pieces tend to live at center vs edge) that
the matched-edge / defect / band signals don't see.

### Critical edge case: 0/256 cells unsupported

If a board's placement has $s_b(c) = 0$ for ALL 256 cells (e.g., the board is in a
genuinely novel basin not represented in the corpus), $w_b$ becomes uniform and
PriorDestroy degenerates to `RandomRegion`. This is fine — it means PriorDestroy
self-disables on basins it cannot inform.

### Critical edge case: pinned positions

Canonical hint positions (135, 210, 34, 221, 45) MUST NOT be destroyed. ALNS
already filters them via `cfg.pinned_positions`. PriorDestroy will set
$w_b(c) = 0$ on pinned positions to be safe.

## What we'll measure

For each base board (V155→ALNS 460 outputs):
1. **Score lift**: max score reached over 30min × 8 seeds, vs `basic_lkh` baseline.
2. **Best-history**: when in the 30min did the lift occur? (Pure-time efficiency.)
3. **Op contribution**: ALNS adaptive weights — does `PriorDestroy` earn high reward?
4. **Variance**: min/median/max across 8 seeds. Single-seed point estimates are not science (see CLAUDE.md §4).

## What's still open

- Is the 460-basin's unsupported-cell count predictive of break-out potential? Boards with more $s = 0$ cells should be EASIER to break (the prior thinks they're guesses).
- Could PriorDestroy operate on **pairs** ($P(p, c)$ + $P(q, c')$ for adjacent pairs)?
- Does combining `PriorDestroy` with V155-rerun-on-residual close a loop?

## Linked concepts

- [[prior-data-augmented-beam]] (V155 — where the prior was first used)
- [[v155-finding-prior-lift]]
- [[../sessions/vol-155]], [[../sessions/vol-156]]
- [[basin-460-v156-newcps]]

## Linked memory

- `project_e2_v156_460_pipeline_2026_05_19`
- `project_e2_from_scratch_460_2026_05_19`
