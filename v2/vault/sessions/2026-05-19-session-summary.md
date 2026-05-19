# 2026-05-19 Session Summary — Vols 125-130 in 1 hour

User directive (running):
- "Innovate" + "multi-hour work is possible" + "user is away 1 month"
- "Each invention in a different volume"
- External brainstorm reservoir archived in
  `vault/plans/EXTERNAL_BRAINSTORM_2026-05-18.md`

## Vols covered

| Vol | Theme | Status | Key Result |
|-----|-------|--------|-----------|
| 125 | T34 FPL Frozen-Pair Lifting | refuted | Cross-basin probe: max 374/480 from 254 start (basin transport infeasible) |
| 126 | CONCORD Difference Map | partial | 3 PoC iterations, math sound but tuning hard |
| 127 | CONCRETION Rigid Molecules | refuted | No forced pair/triple/quad pairings (out-degree 9-12) |
| 128 | ATLAS Pattern Database | refuted | E2 objective is additive per-edge; per-patch UB = 480 trivially |
| 129 | PALIMPSEST Historical Consensus | partial | 5573 consensus traps, full-overlay → 5/256 from McGavin 469 |
| 130 | FILAMENT LK-on-2D | partial | Standalone +36 on 254; ALNS+filament +77 in 60s |

## Quantitative new findings

1. **18 corner-perm basin families** with score ≥458 (vol-129 discovery).
   16 are NON-McGavin and have max 458-461; each potentially hides a
   462+ basin.
2. **Consensus traps**: 5573 pair-tuples appear in 200+ low-score
   boards but never in 462+. All 256 positions are in some trap.
3. **Trap-density heatmap**: traps concentrated in rows 0-3 (8-12
   per cell); rows 10-15 are largely consensus-correct.
4. **5 cells from McGavin**: full PALIMPSEST escape overlay produces
   a 451/480 board that diffs by exactly 5 cells from McGavin's 469.
5. **σ-cycle indecomposability re-confirmed**: pinning 61 McGavin
   pair-tuples onto our 461 destroys score to 254; 30min ALNS can
   only recover to 374. Full 255-cell σ is required for cross-basin
   move.

## Code artifacts (commits)

15+ commits across the 6 vols. Notable:

- `crates/localsearch/src/filament.rs` — new Rust module, LK chain
- `crates/bench-audit/src/bin/v130_filament_apply.rs` — standalone bin
- `crates/bench-audit/src/bin/gen_small_csv.rs` — tiny puzzle generator
- `scripts/v125_fpl_*.py` — 3 FPL analysis scripts
- `scripts/v126_concord_{poc,v2,v3}.py` — 3 CONCORD PoC iterations
- `scripts/v127_concretion_*.py` — 4 CONCRETION analysis scripts
- `scripts/v128_atlas_critique.py` — ATLAS refutation
- `scripts/v129_*.py` — 6 PALIMPSEST analysis + attack scripts
- `vault/plans/EXTERNAL_BRAINSTORM_2026-05-18.md` — durable invention archive

## Open items (in flight)

- V129-T7 K-sweep escape pinning (K=16/32/64, 2 seeds each, 30min ALNS):
  expected completion ~08:13 CEST.
- V129-T9 (1,0,3,2) basin attack (seed=42, 30min ALNS): expected
  ~08:18 CEST.

## Next vols (if user binding stays)

- **Vol-131 GRAIN** (polycrystalline annealing): multiple growing
  seeds with grain-boundary destroy.
- **Vol-132 PRISM** (chromatic dual decomposition): 17 color layers
  + Lagrangian decomp.
- **Vol-133 TUNNEL** (path-integral QA): replace SA with quantum
  annealing.

## Remaining wildcards from brainstorm

- **MURMUR** (neural CA) — speculative, ML-heavy
- **INTAGLIO** (carve forbidden patterns) — twin of CONCRETION;
  given CONCRETION refuted, INTAGLIO likely also limited
- **PROVENANCE** (designer cryptanalysis) — moonshot
- **VANISH** (Nullstellensatz infeasibility oracle) — moonshot
- **SHADOW** (cut-and-project from higher-dim) — moonshot

## Memory updates this session

- Added `reference_external_brainstorm_2026_05_18.md`
- Added `feedback_e2_one_invention_per_volume.md` (binding)
- Added `project_e2_v125_t34_fpl_probe_result.md`
- Added `project_e2_18_basin_families_2026_05_19.md`

## Linked

- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
- [[concepts/fpl-frozen-pair-lifting]]
- [[concepts/concord-difference-map]]
- [[concepts/concretion-rigid-molecules]]
- [[concepts/atlas-pattern-database]]
- [[concepts/palimpsest-historical-consensus]]
- [[concepts/filament-lk-2d]]
