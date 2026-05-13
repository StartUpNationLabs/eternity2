# Session — vol-04

**Theme**: Frame-first decomposition; first break of the 449 plateau (+1 → 450).
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_4|RESEARCH_NOTES_4.md]]

## What was attempted

- `plateau_analyze` infrastructure: connected-component analysis of mismatch graph; universal-mismatch table across 29 corpus boards.
- Spectral diagnostic (Option A): is there a localized eigenmode in the deficit?
- Frame-first decomposition: generate border ring separately, greedy-fill interior.

## What was measured / kept

- **Mismatch hotspot identified**: south-central region, **rows 10-13, cols 4-13**. Top-6 universal-mismatch edges occur in **47-63%** of boards.
- **[[strain-cascade]] hypothesis** proposed: asymmetric (7,8) hint warps search backwards toward this region. Falsifiable via hint-removal test (queued).
- **First break of 449 plateau**: frame-first decomposition with border-seed `0xCAFEFEEF` → **450/480**.
- Fresh basin B discovered (~19% overlap with baseline) — basins are distinct.

## What was refuted

- **Spectral-diagnostic (Option A)** as a localized-failure detector: deficiencies are global, not eigenmode-localizable.

## Concepts touched

- [[frame-first]] (introduced as 450-breaker)
- [[mismatch-geometry]] (universal-mismatch table)
- [[strain-cascade]] (hypothesis, never directly tested)

## Implication

The plateau IS breakable — just not by within-prefix local moves. Diversification at the **border level** unlocks +1. Vol-5 will push this further with GA-crossover.

## Linked memory

- `project_e2_state` (vol-4 row)
