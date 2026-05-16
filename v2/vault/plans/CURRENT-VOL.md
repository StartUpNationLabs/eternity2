# Current vol — vol-105 (2026-05-16)

**Standing record**: 459/480 (vol-60 cross-machine SOTA, p06 corner perm).
**Mode**: autonomous, user away ≥ 1 month. Senior-researcher.

## Binding items (≤ 3)

### T1 — Joint piece-set + cell-set MIP

Builds the σ-cycle-targeting MIP that allows SWAPS between an in-region
cluster and out-of-region pieces. The local rigidity theorem (PAPER
2026-05-16) proves every halo-r ≤ 4 MIP returns delta=+0 — but those
MIPs only PERMUTE within-cluster pieces, they don't swap pieces in/out.
The σ-cycle decomposition (vols 65/99/101) requires cell-set + piece-set
JOINT moves: pieces leave the cluster, pieces from elsewhere enter.

Minimal version: pick a 4-cell defect region in the local-459 basin;
expand the MIP variable set to include "swap variable" `s_{c,p,p'}`
for each cell c, in-region piece p, out-of-region piece p'. If feasible,
scale to 6/8/12 cells.

If at any scale up to ~16 cells we find delta > 0, that breaks the
rigidity theorem. If delta = +0 holds even with cross-region swap, that
extends the theorem's strength.

Sound regardless of outcome.

### T2 — Bottom-rows-only ALNS/MIP variant

Per-row diversity finding (memory: per_row_diversity_corpus): rows
12-15 have 3× more arrangement diversity than rows 0-11 across the
record corpus. ALNS / MIP focused on bottom 4 rows (with rows 0-11
pinned to the local-459 board) is a search budget that has not yet
been allocated.

Two flavors:
- Strict pinning + MIP: rows 0-11 frozen, MIP on 64 cells of rows 12-15.
- Relaxed bottom-half ALNS: rows 0-7 pinned, ALNS on rows 8-15.

T2.a is highly constrained (likely returns +0 like the halo MIPs but
on a larger 64-cell region). T2.b is a novel ALNS shape we haven't run.

### T3 — Row-pair UB extension to the full board

Vol-86 proved a sound UB ≤ 123 on McGavin's top-4 rows via LP+integer
arithmetic, 18.7k binary vars, 1200s. That's the first non-trivial
structural UB below 480.

Extend: compute the same row-window UB for the six overlapping 4-row
windows. If each gives a sound UB ≈ 120, summing with overlap
correction could yield a board-wide UB significantly below 480. First
step toward a rigorous board-wide UB.

If the per-window UB exhibits high variance (some windows ≪ 123),
that pinpoints which rows are the "harder" rows — algorithmic signal.

## Audit-at-open compliance

Audit completed in `sessions/vol-105.md` (this vol's journal). Key
finding: user-stated "community 470" is on the 1-clue Blackwood
variant, not canonical 5-clue. Vault data verified: canonical
ceiling = 469 (McGavin 2020). No mass edits — accurate documentation
preserved.

Aged unbuilt items from BACKLOG.md not yet picked up at open; will
revisit during T1/T2/T3 execution.

## Working order

1. T2.a (Strict bottom-rows MIP) first — reuses existing MIP
   infrastructure (vol-44 + vol-55 + vol-83 stack), shortest path to
   data.
2. T3 — also reuses LP/MIP infra. Run in parallel where possible.
3. T1 — requires new MIP variables / new bin. Hardest, but most
   directly attacks the σ-cycle rigidity.

## Linked

- [[../INDEX|INDEX]]
- [[../PAPER_2026-05-16_canonical_E2_rigidity_theorem|PAPER]]
- [[../IDEAS_FROM_BLANK_2026-05-16|IDEAS]]
- [[../sessions/vol-105|vol-105 journal]]
