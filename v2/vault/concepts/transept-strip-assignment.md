---
name: transept-strip-assignment
description: "TRANSEPT (vol-208) — from-scratch constructor: solve a GLOBAL piece→horizontal-stratum assignment, then each stratum to MaxScore optimum vs its assigned pool + shared seam, then optimize seams. Synthesizes N2 (strip-MaxSAT) + N1 (assignment-pricing). GATE findings: a near-perfect stratification EXISTS (McGavin's bottom 10 rows are 100% perfect strata) but is board-specific (0/256 pieces row-pinned across corpus; 192/256 float) — so the assignment must be solved fresh, no corpus prior."
status: partial
metadata:
  type: concept
---

# TRANSEPT — global piece→stratum assignment + exact strata (vol-208)

**Origin**: vol-208 (2026-06-10). Frontier #1 (from-scratch into a higher novel
basin) done rigorously. Synthesizes backlog N2 (strip-MaxSAT constructive) + N1
(scarcity-priced global assignment). Successor to WATERSHED → MOSAIC line.
**Files**: `scripts/v208_confluence/` (probes, gates), TRANSEPT engine TBD.

## The idea
Every prior from-scratch constructor (greedy ~385, BP-decimation 435, MOSAIC 448,
Anjou scaffolds ~429) plateaus far below SOTA because of ONE shared failure mode:
the **last-filled region inherits incompatible pieces** (piece-theft / pool
depletion). They all commit pieces in *scan order* (left-right, block-by-block)
without globally deciding which pieces go where.

TRANSEPT fixes exactly that:
1. **Global assignment pre-pass**: solve a piece→stratum transportation problem
   (which of the 256 pieces is allocated to each horizontal stratum), priced by
   (N,W)-scarcity so scarce servers land in the stratum that needs them.
2. **Exact strata**: solve each stratum to MaxScore OPTIMUM (RC2/seqAMO window-
   MaxSAT) against ONLY its assigned pool + its shared seam with the stratum above.
3. **Seam optimization**: the inter-stratum seams are the residual defect; optimize
   them (re-assign boundary pieces / local seam MaxSAT).

The novelty vs MOSAIC (4×4 soft blocks, greedy order) and Anjou scaffolds
(independent strips, POST-HOC reconcile): the contention is resolved by a GLOBAL
assignment BEFORE any stratum is solved — the missing ingredient both lacked.

## ★ VERDICT (vol-208) — TRANSEPT construction side REFUTED; pivoted to the bound
After the four gates below, the construction side of TRANSEPT is a rigorous
negative. The clean separable design (assign-then-fill) is dead, and every
non-degenerate variant reduces to a method already exhausted:
- **Separable assign-then-fill**: dead. No assignment objective is selective —
  corpus prior vacuous (Q2, pieces float), color-balance vacuous (Q4, every
  partition balances). With no guiding objective the assignment degenerates to
  greedy.
- **Greedy strip-fill** (Q3): reproduces refuted J1 exactly — rows 0–9 fill
  PERFECTLY (pool 256→96), then collapse (rows 10–11: 3 defects; rows 12–13: ~5;
  pool→32). Plateau ~370–385 (greedy-constructor class). The depth-150 wall.
- **Residual-aware steering** (the one novel idea): needs a top stratum to have
  MANY optimal fills with different leftover pools. Measured (`gate_swap_freedom`):
  stratum-0 optimum has **0 single-piece substitutions** — locally rigid. Even if
  multi-piece optimal alternatives exist, *choosing* among them to help the bottom
  is a cross-seam coordinate descent = ALNS across the strip boundary = exhausted.

**Conclusion**: strip-decomposition has no separable structure to exploit; it is
either refuted-J1 (greedy) or exhausted-ALNS (steered). The Q1 existence result
(near-perfect stratifications exist) stands, but they're reachable only by
co-optimizing assignment+fill = the intractable global 16×16 solve. The volume's
energy pivoted to the **bound** side: [[MATH_NOTES_2026-06-10_strip_cut_bound]]
(window-integer cuts vs the 480 LP saturation — a shot at proving 480 impossible).

## GATE measurements (vol-208 binding item 1)

### Q1 — A near-perfect stratification EXISTS (POSITIVE)
`gate_contention.py` on McGavin 469, per-stratum internal+seam matched:
- H=1: rows 0–5 carry ALL 11 defects; **rows 6–15 are 100% perfect** (15/15
  internal, 16/16 seam) at every cell.
- H=2: rows 0–5 carry the defects; **rows 6–15 perfect** (46/46 internal, 16/16 seam).
- H=4: bottom two 4-row strata 108/108 + 16/16 seam — perfect.

→ Strip-decomposition is NOT fundamentally doomed: a real near-optimal board
decomposes into near-perfect strata. The bottom 10 rows are *perfectly fillable*
as strata. (McGavin's defects cluster at the TOP, unlike greedy constructors whose
defects cluster at the bottom — an inversion worth noting.)

### Q2 — But the assignment is board-specific, no corpus prior (NEGATIVE for fixed-assignment)
Across 79 corpus boards ≥458, per-piece ROW distribution:
- **0 of 256 pieces are row-pinned** (row-stdev < 2.0).
- **192 of 256 float** (row-stdev > 3.5; uniform-over-16 stdev ≈ 4.61); median 3.97.

→ The same piece appears in wildly different rows across different high boards.
There is NO canonical piece→stratum assignment to mine from the corpus. Each high
basin has its OWN consistent assignment, and they all differ. TRANSEPT must solve
the assignment FRESH as a global optimization — good for novelty (fresh basin
reachable), but means the assignment is genuinely hard (no warm prior).

### Q3 — Greedy sequential strip-fill (the baseline TRANSEPT must beat)
`gate_strip_fill.py` H=2, RC2-exact per stratum, full pool→deplete:
- strata 0,1 (rows 0–3): PERFECT (46/46 internal, 16/16 seam) — pool rich (224→192).
- [later strata measured below — depletion expected near the bottom]

### Q4 — per-stratum COLOR-BALANCE is VACUOUS as an assignment objective (NEGATIVE)
`gate_color_balance.py`: for each stratum pool, the vol-65 per-color matching cap
(Σ_c ⌊count_c/2⌋) vs internal edges needed:
- McGavin partition (H=2): caps [49,59,56,58,57,57,57,50], all ≥ 46 (needed).
- **Random partitions (same sizes, 200 trials): 100% have ALL strata cap ≥ needed.**
  Min-cap mean 51.9 (min 49) — random pools are *as balanced* as McGavin's.

→ The per-stratum color-supply balance is **not selective** — almost any partition
satisfies it. This is the PARQUET pattern again (the per-color budget is globally
tight at exactly 480, vol-65 [[E2_KNOWN_FACTS]], so it's locally satisfiable
everywhere). **A color-count assignment objective is vacuous.** McGavin's partition
is NOT special in color-balance terms; what makes it fillable is the *exact
adjacency pattern*, not the color multiset.

## What this implies for the design — the assignment objective is the hard part
- **Corpus prior**: vacuous (Q2 — pieces float across rows).
- **Color-count balance**: vacuous (Q4 — every partition balances).
So the only thing distinguishing a fillable partition from an unfillable one is
the **exact adjacency feasibility** — i.e. solving (near-)exactly whether the
assigned pool tiles the stratum, which is the stratum MaxSAT itself. The
assignment and the fill are **not separable** by any cheap proxy measured so far.

This is the same wall J1 hit (band-12/14, refuted — could not break 459): a
band/stratum builder where the per-band assignment has no tractable guiding
objective degenerates to greedy, and greedy depletes. **TRANSEPT's separable
two-phase design (assign-then-fill) is therefore NOT viable as originally framed**
— there is no cheap assignment objective. See "Pivot" below.

The Q1 existence result still stands (near-perfect stratifications exist), but they
are findable only by *co-optimizing* assignment + fill, not by a pre-pass. That
co-optimization at 16×16 scale is the intractable global solve the whole project
has hit. Honest status: the clean separable TRANSEPT is refuted by Q4; a
co-optimizing variant is the open question (see Pivot).

## Linked
- [[scarcity-skeleton-shared-core]] — vol-208 scarce-demand measurement
- [[watershed-frontier-flow]] — the (N,W) scarcity / piece-theft diagnosis it targets
- [[mosaic-window-maxsat]] — prior constructor (soft blocks, greedy order) it improves on
- [[parquet-overlapping-patch]] — bound side (capped); TRANSEPT is the search side
- `reference_anjou_experiments_2026_06_09` (memory) — window-MaxSAT tractability + scaffold failure mode
