# Vol-129 Close — 2026-05-19 ~09:49 CEST

## Theme

PALIMPSEST — historical-consensus invariant mining. Bucket records
by corner perm, identify trap pairs (high count in low scores, never
in 462+) vs escape pairs.

## What shipped

1. **Consensus mining (V129-T1)**: 1278 records → 5573 consensus
   traps + 490 likely-correct pairs. All 256 positions are in some
   trap.
2. **Trap-density heatmap (V129-T2)**: traps concentrated in rows
   0-5 (8-12 per cell); rows 10-15 are largely consensus-correct.
   Our 461 basin family is locked at the top half.
3. **Per-position trap+escape pieces (V129-T5)**: for every cell,
   identified which pieces are "trap" and which are "escape" (in
   any 462+ board).
4. **Interior trap analysis (V129-T8)**: 139 of 144 interior cells
   have trap≠escape; highest concentration in rows 2-5.
5. **Full-overlay attack (V129-T6)**: pinning 251 escape pieces
   produces a board with corner perm (3,2,0,1) at 451/480 — 5/256
   cells from McGavin's 469. CONSENSUS-RECONSTRUCTION of McGavin.
6. **K-sweep escape pinning (V129-T7)**: K=16/32/64 hard-pinning all
   ≤439, well below 461 base. **Hard-pinning attack REFUTED**.
7. **Basin clustering (V129-T11)**: pairwise diff between 18 corner-
   perm basin representatives — only 2 pairs are closely related
   (McGavin family + our 461 family). **15 genuinely distinct
   isolated basins** identified.
8. **🎯 15-basin attack (V129-T12)**: 18 × 30min ALNS basic seed=42:
   - (2,3,0,1)@462 → **463** (NEW RECORD, never seen in DB)
   - (1,3,0,2)@458 → 459 (+1)
   - (0,2,3,1)@458 → 459 (+1)
   - 15 others: flat.

## The 463 record

**File**: `output/vol-129/RECORD_463_corner2301_seed42.json`
**Properties**:
- Matched-edges: 463/480 (verified)
- Corner perm: (2,3,0,1), McGavin family
- Hint compliance: 1/5 (matched-edges convention)
- Diff vs McGavin 469: 28 cells
- Diff vs base (462_vol82_bottom14_462): only 3 cells (ALNS swap)
- Reached at iter=4 of 1200, then plateau

**Lineage**: Within McGavin's basin family. Not a new basin — a +1
push inside an already-known basin via ALNS finding 3 cells to swap.

## What's open at close

- Strict-canonical record still 459 (no change here, since 463 is
  1/5 hints).
- Standing matched-edges max remains McGavin's 469.
- 14 non-McGavin isolated basins all stuck at ≤461. The
  Selby-Riordan piece set genuinely admits ≥462 only in McGavin's
  family.

## What's REFUTED

- Pin-escape-pieces as a search operator (K=16/32/64 all <461).
- Cross-basin transport via pair pinning (V125-T34 already showed).
- 15 non-McGavin basin families can be pushed to 462+ via 30min ALNS
  basic seed=42.

## What's BUILT/USEFUL

- PALIMPSEST as a DATA-ANALYSIS tool (5573 traps, basin clustering,
  per-position signatures) is durably useful.
- The 18-basin attack found 1 new record (463) and confirmed 14 are
  stuck at ≤461.

## Linked

- [[concepts/palimpsest-historical-consensus]]
- [[concepts/fpl-frozen-pair-lifting]] (refuted)
- [[concepts/concord-difference-map]] (partial)
- [[concepts/concretion-rigid-molecules]] (refuted)
- [[concepts/atlas-pattern-database]] (refuted)
- [[concepts/filament-lk-2d]] (partial)
- [[basin-440-469]]
- [[project_e2_record_463_2026_05_19]] (memory)
- [[project_e2_18_basin_families_2026_05_19]] (memory)
