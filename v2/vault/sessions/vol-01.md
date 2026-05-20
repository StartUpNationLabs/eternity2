# Session — vol-01

**Theme**: Engine foundations and literature baseline.
**Raw**: [[archive/raw/RESEARCH_NOTES_1|RESEARCH_NOTES_1.md]]

## What was attempted

- Port Ansótegui et al. CP'08 propagators ([[gacolor]], [[ac3]]) to a clean Rust workspace.
- Sweep variable-order heuristics: LCV, [[scan-order|CHESS static order]], MRV.
- Establish a generated-puzzle benchmark grid (sizes 4-8, colors 4-7).

## What was measured / kept

- **[[gacolor]] is the strongest single propagator.** Ansótegui's "most powerful global constraint" claim validated empirically.
- AC-3 + GAColor cell-CP reaches **449/480** on canonical E2 in ~43-44s single-threaded; **2.5s with RootSplit parallel** (8 cores).
- Size-8-colors-7 first-ever solved (DNF in legacy stack).
- New profile shipped: `gacolor_ac3_par` (the vol-1 default through vol-12).

## What was refuted

- **CHESS static order** without full Régin alldiff: 600× node explosion. Requires bounded-width CSP which E2 lacks.
- **Symmetry-breaking** as standalone propagator: no-op on first-solution mode; implicit ordering already sufficient.
- **Single-arc-consistency only** as production strategy.

## Concepts touched

- [[gacolor]] (introduced as canonical port)
- [[ac3]] (introduced as canonical port)
- [[scan-order]] (CHESS variant refuted; border-first MRV established)
- [[engine-profile-registry]] (first profile entry)

## Open at close

Establish ALNS / local-search infrastructure on top (deferred to vol-2 + vol-5).

## Linked memory

- (none yet, memory system started later)
