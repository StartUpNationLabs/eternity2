---
name: hint-compliance-clarification
description: "Vol-112 — clarification on hint-compliance conventions across our records. Strict-canonical 5-clue (5/5 hints obeyed): ceiling 457 (blackwood_mrv). Matched-edges 4/5: 459 (vol-60). Matched-edges 0/5 (our pipeline): 459-460. Different puzzle variants; not directly comparable."
metadata:
  type: project
---

# Hint compliance conventions (vol-112 clarification)

**Status**: `built` 2026-05-16 ~14:55. Methodology clarification.

## The conventions

Per CLAUDE.md rule #5: "Define your record convention before
claiming records." There are MULTIPLE scoring conventions in play
across this project's records:

| convention                       | hint compliance | best record we have |
|----------------------------------|----------------:|-------------------:|
| **Strict-canonical 5-clue**      |             5/5 | 457 (blackwood_mrv) |
| **Matched-edges 4/5**            |             4/5 | 459 (vol-60 RECORD_TIE) |
| **Matched-edges 0/5 (= 1-clue)** |             0/5 | 460 (pipeline bseed9) |

The "standing record 459" in our project memory is the
**matched-edges 4/5** variant. The **strict-canonical 5-clue**
record is **457**.

## Why this matters

The bf-pipeline (vol-110/111/112) operates on the 0/5-hint variant
(blackwood-fast doesn't enforce canonical hints). The 459-460
boards it produces are valid 1-clue solutions but NOT canonical
5-clue solutions.

The `cluster_repair` CP solver enforces canonical hints; running it
on a 0/5-hint board causes **"hint at position X causes immediate
wipeout"** because the pinned hint conflicts with the placed piece.

Concrete evidence (vol-112 testing):
- `cluster_repair --board pipeline-orig-459`: error at position 221.
- `cluster_repair --board vol-60-RECORD_TIE_459`: error at position 210.

Both records violate at least one canonical hint.

## Implications for vols 106-115

The directive is "blank-puzzle speedup + invention." Score-axis is
out of scope. The vol-110/111/112 work on 459+ has been measuring
on the 0/5-hint variant, which is fine for the matched-edges
metric but **doesn't advance canonical 5-clue solving**.

For canonical 5-clue progress:
- Need a hint-preserving version of the bound-ascent + Hungarian
  pipeline. The `random_swap` function in `edge_bound_ascent.rs`
  DOES pin canonical hints via `pinned: BTreeSet<u32>`, but the
  bound-ascent INPUT (a bf_bw partial) already lacks hints.
- Alternative: run the pipeline on a hint-respecting record (e.g.,
  vol-32 458 with 3/5 hints) instead of a bf_bw 0/5-hint partial.

These are vol-113+ work; vol-112 closes with the methodology
clarification.

## Linked

- [[new-459-from-bf-pipeline]] — has the retraction note.
- [[basin-mix-mip-refuted]] — MIP refutation across 4 basins
  (all 0/5 hints).
- [[../sessions/vol-112]].
