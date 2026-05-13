# Session — vol-09

**Theme**: First community technique ports. Eulerian-border (refuted) + Verhaard SA (small signal).
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_9|RESEARCH_NOTES_9.md]]

## What was attempted

- Port anr_56's Eulerian-cycle border propagator.
- Port a subset of Verhaard's swap-annealing as `crates/solver-verhaard/`.
- Add `ValueOrder::PreferredFirst`, `SolveOpts.preferred_pieces`, `SolveOpts.excluded_pieces`.
- Falsifiable A/B vs canonical E2.

## What was measured / kept

- **[[eulerian-border]] propagator**: zero pruning power on canonical E2 (1M trials at 5 depths). Necessary-but-vacuous constraint.
- **[[verhaard-set-sa]] small signal**: +6.5-edge signal vs random on 30s SA + preferred ordering (seed 42 reaches depth 181 / 308 edges; mean 297.5 across 4 seeds).
- Brendan 2008 community result confirms Verhaard's 180-piece subset is intractably hard by construction.

## What was refuted

- **Eulerian-border** as production propagator (vacuous on canonical E2).
- **Verhaard-180-piece-SA** small variant as 469-path (architecture confirmed but not expressive at our scale).

## Concepts touched

- [[eulerian-border]] (introduced + refuted)
- [[verhaard-set-sa]] (small-signal port)
- [[engine-profile-registry]] (PreferredFirst + preferred/excluded pieces hooks)

## Methodology lesson

This was the first systematic A/B port. The lesson — **measure with falsifiable A/B before believing community lore** — paid off here (Eulerian null) and shaped vol-12 (NS-1 with measurement) and vol-15 (Blackwood with measurement).

## Open at close

Verhaard's full method (set-composition swap-annealing meta-loop + loser-group + 80-piece scaffold) still unported. Backlog: `verhaard-full-port` 2-3 days.

## Linked memory

- `reference_verhaard_actual_method`
- `project_e2_state` (vol-9 row)
