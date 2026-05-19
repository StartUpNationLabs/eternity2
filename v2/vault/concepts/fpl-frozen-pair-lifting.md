# Frozen-Pair Lifting (FPL)

**Status**: `refuted` (Vol-125 — cross-basin probe completed
2026-05-19; max recovery 374/480 from 254/480 start, well below 461)
**Origin**: Vol-125 V125-T34, 2026-05-19
**Files**:
- `scripts/v125_fpl_analysis.py` — basic log-odds analysis
- `scripts/v125_fpl_basin_split.py` — basin-separated analysis
- `scripts/v125_fpl_cross_basin_probe.py` — cross-basin probe ALNS

## Definition

For each adjacent piece-pair $(i, j)$ in a $16 \times 16$ board and
each realised assignment $(\text{pid}_i, \text{rot}_i, \text{pid}_j,
\text{rot}_j)$, compute the score-conditioned occurrence frequency
across the record database. A pair-tuple that occurs *only* in
high-score boards (score $\ge T$) is a **candidate invariant** —
some hypothesis space of 480-feasible boards contains it, while many
sub-optimal basins do not.

The Laplace-smoothed log-odds:

$$
\text{log-odds} = \log \frac{(h + \alpha) / (N_H + 2\alpha)}{(l + \alpha) / (N_L + 2\alpha)}
$$

where $h, l$ are the pair-tuple's occurrences in HIGH and LOW buckets
and $N_H, N_L$ are the bucket sizes. Pairs with $\text{log-odds} \gg 0$
are HIGH-enriched.

## Refinement: Basin separation

Naive log-odds confounds multiple basins. The DB has 49 boards with
score $\ge 459$, but these fall into:

- **Our 461 basin family**: corner perms $\{(0,1,2,3), (1,2,3,0),
  (1,2,0,3)\}$
- **McGavin 469 basin**: corner perms $\{(3,2,0,1), (2,3,0,1)\}$ —
  matched-edges 469
- Plus several intermediate 459 basins

Splitting by corner permutation isolates the McGavin signature:
**13,637 pair-tuples appear only in McGavin-class basins** (max score
$\ge 462$). The top of this list is densely concentrated in **rows
12-15** (positions 207-254), confirming McGavin's bottom-up rigidity.

## Cross-basin probe (V125-T34c)

**Hypothesis**: pinning the top-K McGavin-only pairs onto our 461
basin's starting board forces ALNS into a different region of the
search landscape. Three possible outcomes:

1. ALNS converges to 469 → basin transport succeeds; we have an
   automatic pipeline from our records to McGavin's basin.
2. ALNS converges to a *hybrid* score $> 461$ in a new corner-perm →
   genuine new basin (the WIN).
3. ALNS regresses ($\le 461$) → basin transport infeasible; McGavin's
   bottom incompatible with our top → fundamental rigidity proved.

**Setup**: 61 McGavin pinned positions (mostly rows 12-15) applied to
`RECORD_461_off110_seed42`. Initial scored 254/480 (52.9% — overlay
destroys most matches), then ALNS basic 30min × 6 seeds with
`--extra-hint` on every pinned position.

**Results** (jobs completed 2026-05-19 07:41 CEST):

| seed | best matched |
|------|--------------|
| 1    | 363          |
| 42   | 365          |
| 7    | 364          |
| 99   | 367          |
| 142  | 374          |
| 5257 | 374          |

**Max: 374/480 — far below 461. Outcome 3 (basin transport
infeasible).**

Pinning 61 McGavin-only pair pieces onto our 461 base destroyed the
board to 254/480, and 30min ALNS could only recover to ~374. The two
basins are NOT bridgeable by per-piece pinning. This is consistent
with σ-cycle indecomposability (vol-65, vol-99): the permutation
between local-459 and McGavin-469 has 11 cycles of lengths up to 154;
applying any proper subset REDUCES score.

## What this rules in / out

- **In**: a principled way to use the existing 1278-board DB as a
  prior on hypothetical 462+ boards.
- **In**: cross-basin "transport" via pair-pinning becomes a concrete
  search operator.
- **Out** (if outcome 3): basins are rigidly incompatible, and getting
  to 462+ requires a *different* attack than pair-pinning across
  basins.

## What's still open

- Symmetric analysis: pin our 461-basin pair-signature onto a
  McGavin starting board. Does ALNS regress, or hybridize? Either way,
  it characterises the basin boundary.
- Soft pinning: penalty-based rather than hard-pinned; allows ALNS to
  selectively break the overlay if needed.
- $K$ sweep: K = 10, 20, 50, 100, 200 to find the rigidity threshold.
- Pair-conflict cycle decomposition: rather than greedy swap-chain, a
  proper cycle-aware swap that minimises lost matches.

## Linked

- [[basin-457-pt]]
- [[basin-440-469]]
- [[new-459-from-bf-pipeline]]
- [[sessions/vol-125]]
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]] (PALIMPSEST is a parent
  category — historical-consensus invariant mining)
