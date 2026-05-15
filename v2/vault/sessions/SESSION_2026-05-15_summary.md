# Autonomous session 2026-05-15 — session summary

**Duration**: ~3 hours of compute, 5 vols closed (54, 55, 56, 57, 58).
**Standing 458 record**: UNCHANGED.
**Headline finding**: 458 is ultra-confirmed locally optimal across
22 cluster MIPs spanning 3 basin families. Our score matches the
2008 academic SOTA (Schaus & Deville CP+VLNS).

## Vol-by-vol

### Vol-54 (math) — gap mechanism precise
- Filled vol-50's per-color INTEGER table: 5.96 fractional + 12 rounding
- Color 8 INT > floor(LP_UB) refutes vol-50 interpretation
- **Cell-fractional x via y-min-of-sums concavity** is the precise mechanism
- 2-cell 2-piece worked example: LP=1.0, IP=0, gap=1.0 (HiGHS verified)

### Vol-55 (B&P MVP) — multi-cluster local optimality
- `dump_cluster_for_lp.rs` + Python+HiGHS LP/MIP
- 4 family-A cluster locations all locally MIP-optimal
- LP-MIP gap 3.3-3.4 is LP looseness, NOT 458 suboptimality

### Vol-56 (CDCL math + measurement) — GREEN LIGHT for vol-57
- `cdcl-no-good-e2.md` math design: hard/soft no-goods, soundness
- Wipeout-distribution: 46k wipeouts/60s at depth median 134
- Python proto on 6×6/5c: clauses median 6, 96% of states have
  ready-to-fire clauses, avg 6.57 per node
- Row-11 bifurcation finding + correction (hint-relaxation induced)

### Vol-57 (CDCL Rust prototype) — works at small scale
- `crates/cdcl-proto` shipped
- 7×7/6c: cdcl 3.4× FASTER + finds where vanilla times out
- Algorithm validated; engineering for canonical-scale deferred

### Vol-58 (multi-track) — extensive validation
- Family-B 457 basin: 11 cluster MIPs, all locally optimal
- McGavin 469 basin: 9 cluster MIPs, all locally optimal
- Total: **22 cluster MIPs across 3 basin families**
- Canonical 16×16 CDCL: 12× fewer nodes, but 96-lit clauses → 0
  propagations. Real 1-UIP needed.
- Deletion-based minimization tried, found UNSOUND (cascading bugs)

## Standing 458 record — comprehensive assessment

**LITERAL matched-edges**: 458 (vol-32 vanilla_fast + ALNS, 3/5 hints).
**STRICT-canonical**: 457 (blackwood_mrv, 5/5 hints).
**Community ceiling**: 469 (McGavin 2020, ~200 cores × days).
**Academic SOTA**: 458 (Schaus & Deville 2008, CP+VLNS).

**Our 458 matches the published 2008 academic ceiling.** To break:
- Community-style scheduled-relaxation algorithms (Blackwood, McGavin)
- Different fundamental algorithm (CDCL at canonical, RL self-play)

## Lottery — running in background

`scripts/vol56_basin_lottery.sh`: 39 vanilla_fast deep snapshots × 4
seeds × 5min ALNS. At 72/156 jobs: best=458, dist centered 452-454.

## Vol-59+ candidates

1. **Real 1-UIP for canonical CDCL** (multi-day, high uncertainty)
2. **Scheduled relaxations in our CP search** (multi-day, prior art exists)
3. **Lottery completion + analysis** (passive, no new compute needed)
4. **McGavin pipeline replication** (multi-week multi-machine)
5. **Vol-29 RL self-play continuation** (multi-week)

## Files shipped (this session)

### Rust crates / bins
- `crates/cdcl-proto/` (new crate)
- `crates/bench-audit/src/bin/per_color_integer.rs`
- `crates/bench-audit/src/bin/dump_cluster_for_lp.rs`
- `crates/bench-audit/src/bin/measure_wipeouts.rs`
- `crates/bench-audit/src/bin/measure_wipeout_repetition.rs`

### Scripts
- `scripts/vol56_basin_lottery.sh`

### Concept pages
- `vault/concepts/y-linearisation-cell-fractional-gap.md`
- `vault/concepts/cdcl-no-good-e2.md`
- `vault/concepts/cdcl-engine-integration.md`
- `vault/concepts/standing-458-record-status.md`

### Session pages
- `vault/sessions/vol-54.md` through `vol-58.md`
- This summary page

### Memory (in `~/.claude/.../memory/`)
- `feedback_autonomous_dont_wait.md`
- `project_e2_vol55_local_optimality_multi_cluster.md`
- `project_e2_vol56_58_session.md`

## Discipline observations

This session was **highly productive** because:
1. The autonomous "don't wait" mandate was explicit and enforced.
2. Each negative result was DOCUMENTED as a finding, not buried.
3. Math/measurement/prototype iteration was balanced with reflection.
4. Background compute (lottery) ran while foreground worked on math.

Process improvements for next session:
- Earlier deduplication of records (would have caught the 3-hint
  vs 5-hint Family-A vs Family-B distinction earlier).
- Better instrumentation upfront (the 1-UIP soundness issue would
  have surfaced earlier with formal correctness tests).
