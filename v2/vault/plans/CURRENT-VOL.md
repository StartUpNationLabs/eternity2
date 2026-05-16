# Current vol — vol-119 OPENED 2026-05-16

## Audit-at-open compliance

- vol-118 closed with 14 tasks shipped (consolidation + bf-bucket bug fix).
- Aged unbuilt items reviewed in BACKLOG: most are 3+ vols old; the
  "engine perf remaining wins" list is durable and not blocking; the
  RL self-play item is a multi-week project (out of scope this vol).
- Picked up vol-118 T10 thread: "skip bound-ascent" + corpus enlargement.

## Vol-119 binding items (3 max)

### T1 — Clean-slate basin corpus enlargement (INVENTION via diversity)

**Mechanism.** Run pipeline (bf_bw → bound-ascent → Hungarian → ALNS
basic) over **corner-perm × seed-offset × ALNS-seed** grid. Most
volumes used 4-8 corner perms × 8 seeds; we'll sweep ≥50 corner
perms × ≥10 seed-offsets × 4 ALNS seeds. Filter by bound-ascent
UB ≥ 460 (vol-118 T6 pattern). Save EVERY produced 459+ basin to a
deduplicated corpus (Hamming-distance ≥ 30 = new basin).

**Why this is invention-class.** Vol-112 said explicitly: "as more
459 basins are discovered, the cell-choice space [for basin-mix MIP]
grows, and the MIP optimum could move." No prior vol has enlarged
the basin corpus past ~7 distinct 459s. The cluster characterization
(A vs B) in vol-118 T1 was on 7 basins.

**Why this is also clean-slate.** No 459-anchor; the pipeline starts
from raw puzzle + fresh bf_bw partials.

**Expected output**: a corpus of 10-30 distinct 459 basins +
diversity statistics.

### T2 — Basin-mix MIP on enlarged corpus (INVENTION attack)

**Mechanism.** Re-run vol-112's basin-mix MIP, but with the T1
corpus (≥10 basins). The MIP picks one basin's (piece,rot) per cell,
subject to piece-uniqueness, maximizing matched edges. If MIP > 459,
**this is a record** — a board constructed by mixing existing 459
basins, validated by MIP.

**Why this might break.** Vol-112's MIP at N=4 found a NEW 459 board
(mix of 3 of the 4 basins). The cell-choice combinatorics scales as
N^256; even at N=10, the search space is 10^256, orders of magnitude
larger. Some cell might have a piece at a non-mismatch position in
a previously-unobserved basin that resolves a mismatch in another.

**Variance**: rerun MIP with N ∈ {4, 8, 16, 32} as the corpus grows
to characterize the marginal value of each new basin.

### T3 — σ-thin-pair search (MATH probe, parallel to T1/T2)

**Mechanism.** Vol-118 MATH_NOTES left explicitly open: "are there
σ-cycle PAIRS where one cycle is nearly contiguous (e.g., a row
swap of pieces)?" Compute σ-decompositions across all pairs in the
enlarged corpus and report the MINIMUM B(S)/|S| across all (pair,
cycle, subset) triples. If any subset has B(S)/|S| < 1.1, the
σ-subset attack reactivates (current min ~1.5×).

**Why this is novel.** No prior vol has scanned σ-pair structure for
isoperimetric outliers. The 7-board × 7-board matrix from vol-118
gave aggregate clustering but not per-cycle isoperimetric stats.

## Linked

- [[../INDEX]]
- [[../sessions/vol-118|vol-118 close]]
- [[../concepts/basin-mix-mip-refuted]] (the lead this vol exploits)
- [[../MATH_NOTES_2026-05-16_SIGMA_SUBSET_THEOREM]] (the math T3 attacks)
