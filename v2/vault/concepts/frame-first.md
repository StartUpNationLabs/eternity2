---
tags: [concept, decomposition, partial-refuted]
status: partial-refuted
origin-vol: 4
---

# Frame-first decomposition

**Status**: `partial` — vol-4 break of 449 plateau; vol-14 Hamilton frame seeding NULL
**Origin**: vol-4
**Files**: `crates/benchmark/src/bin/plateau_analyze.rs`, `crates/bench-audit/src/bin/run_e2_framefirst.rs`, `scripts/v12_hamilton_frame.py`

## Definition

Don't search interior + border jointly. Instead:
1. Generate a feasible 60-piece border ring (Hamilton cycle over border-class pieces with matching edges).
2. Pin the ring; run CP/PT/ALNS on the 196-piece interior.

The border ring is a clean sub-problem; the interior under a fixed ring is also smaller.

## Vol-4 result

Frame-first decomposition with border-seed `0xCAFEFEEF` beat canonical PT baseline 449 → **450/480**. First break of the 449 plateau.

## Vol-12 Hamilton frame enumeration

`scripts/v12_hamilton_frame.py`: DFS over the border-class adjacency graph with edge-color matching. Output: 75,173 Hamilton-cycle valid border rings, stored in `output/v12_hamilton/frames_full.json`.

**Critical caveat (corrected vol-14):** This is a **120s time-bounded DFS**, NOT exhaustive enumeration. The true count is unknown. Operational count of usable frames (those that survive [[gacolor]]+[[ac3]] under canonical hints) is much smaller still.

## Vol-14 frame-first NULL

Tested 500-frame sample as engine hints:
- **47% of frames** exhausted CP search <200ms under baseline propagation.
- **~100% of frames** rejected under gacolor+AC3 (incompatible with canonical hints).

→ Vol-12's Hamilton frames are **necessary-not-sufficient** for full E2 CSP. They satisfy pairwise edge matching on the border ring but fail joint feasibility with the 5 canonical hints + interior alldiff.

→ A frame catalogue is needed that's **CSP-aware**: run gacolor+AC3 during ring DFS, validate against the 4 interior canonical hints + start piece. Not built.

## Hint-centric vs border-first scan order (vol-14)

A/B test of "scan order starting from hint cells outward" vs standard border-first MRV at 60s:
- Hint-centric: depth 42 / 62 matched.
- Border-first MRV: depth 164 / 282 matched.

**Border-first MRV is the correct CSP strategy**; the scan-order correlation with mismatch geometry is empirical, not causal. See [[scan-order]].

## Vol-6 reframing: border diversity

Vol-6 discovered the deeper issue: most community boards share 3 unique borders (86% cell consensus). The corpus is **monocultural at the border level**. Vol-6 built Las Vegas border sampler (100k diverse borders in 6s) + `pt_e2 --pin-perimeter` flag → **454/480** from a corpus border (still our warm record).

## Where this is open

- **CSP-aware frame enumerator**: run gacolor+AC3 during ring DFS + validate vs 4 interior hints. Backlog `csp-aware-frame-enum`.
- **Frame as outer loop on Blackwood**: pick a frame, run [[blackwood-algorithm]] interior with the frame pinned. Not tried.

## Linked concepts

- [[scan-order]] — the order question this raised
- [[blackwood-algorithm]] — likely outer-loop pairing for future work
- [[border-diversity]] — vol-6 sampler that beat 449 → 454

## Linked memory

- `project_e2_hamilton_frame_count`
- `project_e2_vol14_framefirst_null`
- `project_e2_vol14_hint_centric_null`
