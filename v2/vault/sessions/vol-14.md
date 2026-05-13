# Session — vol-14

**Theme**: EdgeBpMarginals Rust port. Hint-pinning bug discovered. McGavin-Blackwood gap analysis. Blackwood spec drafted.
**Raw**: [[../sessions/archive/raw/RESEARCH_NOTES_14|RESEARCH_NOTES_14.md]], [[../sessions/archive/raw/RESEARCH_NOTES_14_PLAN|RESEARCH_NOTES_14_PLAN.md]]

## What was attempted

- Port [[edge-bp-marginals]] from Python (vol-12) to Rust engine as `ValueOrder::EdgeBpMarginals`.
- `run_e2_restart`: outer-loop random restart (test of Joe's policy as fully-cold restart).
- Frame-first via Hamilton catalog: sample 500 frames, apply as engine hints.
- Hint-centric scan order A/B.
- Backtrack distribution instrumentation.
- Initial domain map measurement (the 764-plateau).
- Reverse-engineer Blackwood algorithm from `docs/community-mining/09_Blackwood_solver_thread.md` → [[V15_BLACKWOOD_SPEC]].

## What was measured / kept

- **CRITICAL BUG**: `alns_e2` was UNPINNING canonical hints during destroy. All vol-12/vol-14 ALNS-fill scores invalidated; fixed in commit `afb3dc9`. See [[hint-pinning-bug]].
- **[[edge-bp-marginals]] empirical reversal**: CP-only loses (−3 depth, −11 matched) but **end-to-end CP+ALNS wins** (443 vs 442; post-fix ~440-441).
- **Hint-centric scan order**: 42 depth / 62 matched vs border-first MRV 164 / 282. **Scan-order correlation is empirical not causal.** See [[scan-order]].
- **[[mismatch-geometry]] backtrack distribution**: 95% of backtracks in INTERIOR. Layer-3 shoulder is the bottleneck (124 bt/cell, 12× perimeter). Border ring NOT the lock.
- **Initial domain map (the 764-plateau)**: after hints+AC3, ~175 interior cells all have domain = 764 (max). The 764-plateau **IS** the search problem.
- **[[mcgavin-blackwood-gap-analysis]] established**: 4 orthogonal gaps to 469 (algorithm × 3, engineering × 1). Our ceiling without Blackwood is 446-454.
- **[[hamilton-frame]] CSP-validity NULL**: 47% of frames exhausted <200ms; ~100% rejected under gacolor+AC3. Frames necessary-not-sufficient.
- **Rectangle / Layered destroy operators**: ship at 60s budget +small, lose at 300s.
- **PT-from-443 (running at close)**: 446/480 mid-session — but ALNS bug invalidates the seed.
- **12x12/12 testbed established**: 8x8/8 trivial (ms), 12x12/12 hard (245-252/264 in 90s).

## What was refuted

- **Random outer-loop restart**: doesn't replicate Joe's in-place prune-back-to-T policy.
- **Hint-centric scan order**: border-first MRV is the correct CSP strategy.
- **Frame-first with vol-12 Hamilton catalogue**: needs CSP-aware re-enumeration.
- **Pure value-order axis as solver lever**: exhausted; integration into pipeline is where the wins live.

## Concepts touched

- [[edge-bp-marginals]] (Rust port)
- [[hint-pinning-bug]] (introduced)
- [[mcgavin-blackwood-gap-analysis]] (introduced)
- [[scan-order]] (hint-centric refuted)
- [[mismatch-geometry]] (backtrack-distribution + 764-plateau additions)
- [[hamilton-frame]] (CSP-validity caveat added)

## Open at close → vol-15

- Implement Blackwood algorithm per spec.
- Re-baseline post-bug-fix.

## Linked memory

- `project_e2_vol14_alns_hint_bug`
- `project_e2_vol14_bp_null`
- `project_e2_vol14_framefirst_null`
- `project_e2_vol14_hint_centric_null`
- `project_e2_vol14_backtrack_distribution`
- `project_e2_vol14_initial_domain_map`
- `project_e2_vol14_443_mismatch_geometry`
- `project_e2_vol14_mismatch_geometry_universal`
- `project_e2_vol14_rectangle_path_findings`
- `project_e2_vol14_scan_order_analysis`
- `project_e2_vol14_pt_no_tabu`
- `project_e2_vol14_session_summary`
- `project_e2_vol14_old_stack_comparison`
- `project_e2_vol14_12x12_testbed`
- `project_e2_mcgavin_blackwood_gap_analysis`
- `project_e2_state`
