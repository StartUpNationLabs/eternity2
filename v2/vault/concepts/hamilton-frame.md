---
tags: [concept, structural, partial]
status: partial-misleading
origin-vol: 12
---

# Hamilton frame catalogue

**Status**: `partial` — 75 k frames enumerated; CSP-validity unconfirmed
**Origin**: vol-12 (enumeration), vol-14 (CSP-invalidity finding)
**Files**: `scripts/v12_hamilton_frame.py`, `output/v12_hamilton/frames_full.json`

## What was enumerated

DFS over the border-class adjacency graph with edge-color matching, **120s time-bounded**. Output: **75,173 Hamilton-cycle valid border rings** stored as the 60-piece sequences.

## Critical caveat (corrected vol-14)

This is a **lower bound from a time-budgeted DFS**, NOT exhaustive enumeration. The true count is unknown.

Operational count of **usable** frames (those that survive [[gacolor]]+[[ac3]] under canonical hints) is much smaller still:
- **47%** of a 500-frame sample exhausted CP search <200ms under baseline propagation.
- **~100%** rejected under gacolor+AC3 (incompatible with 5 canonical hints + interior alldiff).

Hamilton frames are **necessary-not-sufficient** for full E2 CSP. They satisfy pairwise edge matching on the border ring but fail joint feasibility.

## What's needed

A **CSP-aware frame enumerator** that runs gacolor+AC3 during ring DFS + validates against the 4 interior canonical hints + start piece. Surviving frame count would be the true operational catalogue size.

Backlog: `csp-aware-frame-enum`, unbuilt.

## Why it still might be useful

- As a structural baseline for [[border-diversity]] / [[frame-first]] strategies.
- As an upper bound on the number of distinct border families to triage.

## Linked concepts

- [[frame-first]] — uses these (with caveat)
- [[border-diversity]] — vol-6 sampler that bypassed this catalogue
- [[gacolor]], [[ac3]] — the propagators that reject most frames

## Linked memory

- `project_e2_hamilton_frame_count`
- `project_e2_vol14_framefirst_null`
