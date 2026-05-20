# Session — vol-12

**Theme**: Bitset engine rewrite. NS-1 propagator. Edge-color BP. Hamilton frame enumeration.
**Raw**: [[archive/raw/RESEARCH_NOTES_12|RESEARCH_NOTES_12.md]]

## What was attempted

- 7-step bitset domain rep rewrite ([[bitset-domain-rep]]).
- NS-1 multiset-equality as Rust propagator.
- Edge-color BP (544 edges × 23 colors).
- Hamilton frame enumeration over border-class adjacency graph.
- Depth-threshold gating for expensive propagators (`joe_depth150` family).

## What was measured / kept

- **[[bitset-domain-rep]]**: +48–101% nps depending on profile. `t=150+NS-1`: nps 959 → 1932 (+101%).
- **[[ns1-deficit]] propagator**: 10–28% node pruning; +28.6% at depth-threshold 150.
- **[[edge-bp-marginals]]**: **18.84% interior reduction** (2.24× vol-11 cell encoding). First BP variant to BEAT random in Python A/B.
- **[[hamilton-frame]] enumeration**: 75,173 frames in 120s DFS. (Critical caveat noted in vol-14: this is a lower bound, NOT exhaustive.)
- **Fleet nps**: 98–156k on baseline 8×5 generated puzzles.
- **Cold-start**: 303 cells matched / depth 174 at 5min (`joe_depth150_par`); 443/480 with ALNS-fill at 15s post-CP.

## What was kept that turned out wrong (corrected vol-14)

- The 443/480 ALNS-fill score was on the broken-ALNS-hint-pinning binary; post-fix true score is ~440. See [[hint-pinning-bug]].
- The 75k Hamilton frames are necessary-not-sufficient (vol-14 frame-first null).

## What was refuted

- **Depth-shallow propagator firing**: cost > benefit. Depth-gate at 150 is the right threshold.

## Concepts touched

- [[bitset-domain-rep]] (introduced)
- [[ns1-deficit]] (port from vol-11 measurement)
- [[edge-bp-marginals]] (introduced)
- [[hamilton-frame]] (catalogue, caveat in vol-14)
- [[engine-profile-registry]] (`joe_depth150` family added)

## Linked memory

- `project_todo_engine_bitset`
- `project_e2_vol12_engine_profiles`
- `project_e2_edge_bp_measurement`
- `project_e2_ns1_deficit_invariant`
- `project_e2_hamilton_frame_count`
