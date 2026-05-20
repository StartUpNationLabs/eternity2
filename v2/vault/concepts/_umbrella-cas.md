---
tags: [umbrella, meta-concept, refuted]
status: refuted-as-greedy
covers: CAS (Concentric Annular Solving) cluster
origin: vol-74-79
---

# Umbrella — CAS (Concentric Annular Solving) — 9 sub-pages

CAS = greedy annular-shell solving (place corners + outer ring → next ring → ... → inner ring).
A full audit (vols 74-79) reaches at best 433/480 score; hybrid + ALNS makes it WORSE not better.

## Verdict

**Refuted as a greedy approach.** The piece-availability bottleneck for inner shells (after greedy locks
outer shells) is the structural cause; not a tuning issue.

## Sub-pages

| Page | Result |
|---|---|
| [[cas-frame-final]] | full audit on 20 frames, distribution 430-436 |
| [[cas-frame-variance]] | preliminary (subsumed by `cas-frame-final`) |
| [[cas-hybrid-refutation]] | CAS-hybrid + ALNS → 418 (worse than CAS alone) |
| [[cas-then-alns-refine]] | CAS + ALNS refine → 437-439 (+4-6 only; below records) |
| [[cas-backtrack]] | CAS with backtrack |
| [[cas-backtrack-results]] | results from cas-backtrack |
| [[cas-beats-alns-from-frame]] | partial-positive on starting from CAS frame |
| [[concentric-annular-solving]] | the algorithm description |
| (cas in alns context) | scattered refs |

## Why CAS fails

Greedy annular fills outer rings first, locking pieces by their best fit on outer-ring edges. When the
inner ring needs specific pieces (with specific edge color profiles), they're already consumed by
outer placements that didn't anticipate the inner constraint.

Audit confirms all 480 edges are in the CAS objective; the bound is **piece availability**, not edge
coverage.

## Stronger alternatives

- **V155 PRIOR + V181 KEYRING** opens from-scratch ≥460 (CAS reaches 433).
- **A1 border-DP + bf_bw + ALNS** reaches 461 (vol-125).

## Linked

- [[dead-ends]]
- [[E2_KNOWN_FACTS]]
