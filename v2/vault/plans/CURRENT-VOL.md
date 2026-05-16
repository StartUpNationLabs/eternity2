# Current vol — vol-109 CLOSED 2026-05-16 ~12:55 CEST

## Vol-109 close summary

**0 positive shipments. 1 empirical refutation, 2 analytical
refutations, 1 partial (infrastructure blocker).** The empirical
T1.a refutation is the senior-researcher win of the day: a
10-minute test saved a multi-day infrastructure investment.

- T1.a ✓ Built `scripts/vol109_oracle_graft.py`; empirically
  refuted the oracle-aware-repair hypothesis. Grafting oracle
  pieces drops partial score by 170-200 points.
- T1 ✗ Oracle-aware ALNS repair NOT BUILT (analytical concern
  confirmed empirically).
- T2 ✗ Beam-search ANALYTICALLY REFUTED.
- T3 partial — cross-compile blocked by no Linux linker on macOS host.

See [[../sessions/vol-109]] for the full table.

## Engine state (unchanged)

- bf_bw 84-85M nps; pipeline → ALNS 450-451 stable in 7 min.
- Standing record 459/480.

## Vol-110 binding items (≤ 3)

### T1 — Multi-objective ALNS (invention candidate)

Objective = matched-edges + γ × (rigid-cluster-count or
sigma-cycle-distance-to-McGavin). Bias ALNS toward
McGavin-shaped basins (1 large component vs the current 4 small
ones in 459 basin).

Effort: multi-day. Variance testing mandatory (≥ 8 seeds per
γ value).

Prior: medium. The rigidity theorem (vols 83-101) showed McGavin
has a single large rigid component; basins with this property
might be ALNS-liftable to 469. Untested.

### T2 — Pipeline composition test (cheap experiment)

Run bound-ascent (vol-22) → Hungarian → bf_bw 5min → ALNS on a
non-record basin. Tests if bf_bw's higher throughput recovers
basins vol-22's old solver-engine couldn't reach.

Effort: 1-2 hours. Plumbing not invention.

Prior: low to medium. The vol-22 work reached 469-ceiling basins;
bf_bw might fail to find them or might find new ones.

### T3 — Cross-toolchain install (infrastructure)

Install x86_64-linux-gnu cross-toolchain (x-tools or
homebrew-formula equivalent) so bf_bw can link to Linux targets.
Then cross-compile + scp to a Linux box for BOLT.

Effort: 2-4 hours assuming clean install.

Prior: medium for cross-machine validation; BOLT win is unclear
without seeing apple-m1 vs x86-64 numbers first.

## Linked

- [[../INDEX]]
- [[../DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP]]
- [[../sessions/vol-109|vol-109 close]]
- [[../LAB_NOTES_2026-05-16]]
