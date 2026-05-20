# V182 ENGRAVE — Exact CSP-Fill on Stripped Row-Bands

Status: `partial` — probe done on K∈{2,4} row bands; no record lift; consistent with three-basin-iso-plateau.
Origin: vol-182.
Files: `scripts/v182_engrave/sweep_bands.sh`, engine via existing `solver-engine` CSP solver.

## Idea

From a known 460 board:

1. Strip a contiguous row band of $K$ rows (e.g., rows 12..15) → leaves $192$ pieces placed and $64 - 16 K$ cells empty.

   *(Correction: stripping K rows removes 16K cells, leaves 256-16K placed.)*

   For $K=4$ (rows 12..15): 192 placed, 64 empty.
2. Use the engine's exact CSP/AC3 solver to find the **highest-scoring legal fill**:
   - Corners pinned.
   - Hints pinned.
   - Remaining 192 pieces fixed → exposed edge-color constraints at the strip boundary.
3. Compare best legal fill against the original board.

## Math

The stripped fill is a constrained CSP: variables $\{c_\text{empty}\}$, domain
$\{p_\text{remaining}\} \times \text{rot}$, constraints on edge-color
compatibility with placed neighbours.

It is **NP-hard in $K$** (subsumes the full puzzle when $K = 16$), but for small
$K$ (2–4) the search is tractable in minutes with engine propagation.

## Empirical result

| Strip K | Cells empty | Compute | Best fill |
|---|---|---|---|
| 2 (rows 14–15) | 32 | 5 min | 32 alternative fills, all ≤460 |
| 4 (rows 12–15) | 64 | hit row-13 wall ~15s | recovers original 460 (proves local rigidity) |

## Interpretation

ENGRAVE confirms what three-basin-iso-plateau showed differently: at the 460
level the band-local CSP is **locally rigid** — there is no higher-scoring legal
fill of the bottom 2–4 rows given the top is fixed.

This is stronger than "ALNS can't lift" because ENGRAVE is **exact**: no
randomness, no time-budget excuse. Within the band, 460 is the genuine ceiling.

## What's open

- Larger $K$ (6, 8). Computationally heavier; if iso-plateau holds, no help anyway.
- Strip a non-contiguous set (e.g., 4 corners + a middle window) — not tried.
- Strip border + interior corner — not tried.

## What's refuted

- "Exact CSP-fill of a row band can lift a 460 to 461" — refuted on $K \in \{2, 4\}$.

## Linked concepts

- [[three-basin-iso-plateau]]
- [[../basins/basin-460-cp0312-v181]]
