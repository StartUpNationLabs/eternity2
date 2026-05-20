# Session — vol-19

**Theme**: Structural measurement — homology and MI. Fracture threshold characterization.
**Raw**: [[archive/raw/RESEARCH_NOTES_19|RESEARCH_NOTES_19.md]] (short, append-only)

## What was attempted

- `measure_betti.py`: homology β_1 of mismatch graph.
- `measure_components.py`: connected-component analysis.
- `measure_mi.py`: piece-side mutual information (North-South, East-West) per [[r4-piece-side-mi]] reformulation R4.

## What was measured / kept

- **Mismatch homology β_1 = 0** on all boards examined. Mismatch edges form a forest. Rules out CycleDestroy operator class.
- **Fracture threshold**: 454 boards have 5-7 small mismatch islands; 441 boards have a single massive 70-cell component. **The structural transition between "stuck" and "near-solution" is component fragmentation.**
- **Piece-side MI**: ~1 bit on opposite edges, ~0.7 bits adjacent. Confirms [[rare-color-rule]] generator structure on full board. (Vol-17 R4 follow-up: interior-only adjacent MI = 0.27 bits / 6.6% — generator successfully decorrelated interior.)

## What was refuted

- **CycleDestroy** ALNS operator: β_1 = 0 means no cycles to destroy.
- Initial R4 "1+ bit" claim was full-board signal dominated by frame structure; corrected vol-17.

## Concepts touched

- [[mismatch-homology]] (introduced, small signal)
- [[mismatch-geometry]] (fracture threshold added)
- [[rare-color-rule]] (MI structural confirmation)

## Linked memory

- `project_e2_vol18_r5_homology` (closely related vol-18 measurement)
- `project_e2_vol17_r4_piece_mi`
