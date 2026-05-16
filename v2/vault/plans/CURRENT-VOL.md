# Current vol — vol-121 OPENED 2026-05-16

## Audit-at-open compliance

- Vols 119+120 closed with corpus-MIP-locked theorem on 459/457.
- Open at close: the 459→478 LP-UB gap is the basin-discovery
  deficit. Vol-121 directly attacks this by enlarging the corpus
  via the cross-machine SOTA recipe (30min × 8-thread vanilla_path).

## Vol-121 binding items (≤ 3)

### T1 — Long vanilla_path basin hunt (RUNNING)

Replicate cross-machine SOTA recipe: 30min × 8-thread vanilla_path
at multiple offsets → ~403-cell partial → 30min ALNS basic at
multiple seeds. Expected wall: 60min vanilla phase + 30min ALNS
phase ≈ 90min.

Goal: produce partials structurally distinct from vol-119 corpus.
If ALNS reaches ≥458 from new partials, those basins go into the
T2 corpus-MIP.

### T2 — Apply corpus-restricted region MIP to T1 outputs

When T1 produces new 458+ basins, add to corpus and re-run
`vol119_region_basin_mix_mip.py` at halo-15. Tests whether enlarged
corpus moves the MIP optimum.

### T3 — Variance reporting

Every ALNS output must report score with full provenance (corner
perm/offset, seed, ops, wall, partial). Per CLAUDE.md rule #4
(variance is mandatory). Sweep variance across ≥4 seeds.

## Linked

- [[../INDEX]]
- [[../sessions/vol-120|vol-120 close]]
- [[../concepts/corpus-restricted-region-mip-locked]]
