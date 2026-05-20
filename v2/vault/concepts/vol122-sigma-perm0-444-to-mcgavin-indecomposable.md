---
name: vol122-sigma-perm0-444-to-mcgavin-indecomposable
description: "Vol-122 K5 — σ-cycle decomposition between vol-122 perm0_444 basin (NEW clean-slate) and McGavin 469 is INDECOMPOSABLE. Extends vol-65 rigidity to a new basin."
metadata:
  type: project
status: built
---

# Vol-122 K5 — σ-transfer perm0_444 → McGavin_469

## Setup

NEW INVENTION: previously σ-cycle analysis was vol-60 459 ↔ McGavin 469
(memory `project_e2_vol65_oracle_sigma_indecomposable`). This extends to
a vol-122 GENERATED basin.

- Source: perm0 clean-slate basin, 444 matched (PID 43464, ALNS basic 30min seed 1).
- Target: McGavin 469-host board (community 469 1-clue equivalent).

Compute σ as position-permutation: for each position pos, σ(pos) = source-position
of the piece that McGavin needs at pos.

## Result

- **Diff cells: 255/256** (only 1 cell matches between perm0_444 and McGavin_469).
- **13 cycles**, lengths: 128, 46, 31, 10, 10, 6, 6, 6, 4, 2, 2, 2, 2.
- **Sum of cycle lengths: 255** (covers all diff cells).

### Per-cycle Δ when applied individually:

| Cycle length | Δ |
|---|---|
| 2 | -4 (3 instances) or -8 (1 instance) |
| 4 | -14 |
| 6 | -13 to -18 |
| 10 | -21 to -36 |
| 31 | -51 |
| 46 | -131 |
| 128 | -160 |

**Every single cycle yields Δ < 0.** Only the FULL 255-cell apply
recovers 469.

## Implication

The **rigidity theorem extends to vol-122 perm0_444 basin** — σ between
this and McGavin is indecomposable just like vol-60 459 ↔ McGavin.

This is a NEW data point for the rigidity theorem, on a CLEAN-SLATE
basin generated entirely from vol-122 A1 pipeline (no anchoring on
prior records).

## Generalization

Conjecturally: σ between ANY 440-460 basin and McGavin 469 is
indecomposable. Empirical evidence:
- vol-60 459 ↔ McGavin 469 (vol-65): indecomposable.
- vol-122 perm0_444 ↔ McGavin 469 (THIS): indecomposable.

Both have similar cycle-length distributions (long-tail with one ~150
cycle, several medium, many tiny).

## What this rules out

Single-cycle σ-application as a basin-escape operator. Same as vol-65.

## What it implies

Beating 459 (let alone 469) requires either:
1. **Coordinated multi-cycle moves** — but tested halo MIPs up to halo-15 (per memory
   `project_e2_2026_05_16_rigidity_theorem`) don't escape.
2. **Cross-basin paths through intermediate basins** — speculative.
3. **Completely different starting points** that yield basins NOT in
   the McGavin-similar family. (= what vol-122 A1 attempts.)

## Status

`finding-confirmatory` — extends rigidity to vol-122 basins.

## Linked

- [[vol-122]]
- [[vol122-a1-pipeline-result]]
- vol-65 σ-indecomposable note (memory)
- vol-105 sigma cycles (also vol-60 459 → McGavin)
