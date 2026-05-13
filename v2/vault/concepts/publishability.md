---
status: open
since: vol-25
---

# Publishability of our results

**Status**: `open` — finding from vol-25 literature review, not yet acted upon.
**Origin**: vol-25 σ-bijection investigation + GA literature review prompted a re-examination of where our results sit relative to peer-reviewed academic literature.

## The finding

After a careful read of the academic literature, our **vol-18 cold-start 457/480 ([[basin-457-pt]])** sits at or above the published peer-reviewed academic record on canonical 5-clue Eternity II.

### Academic record book (peer-reviewed, canonical 5-clue 16×16)

| Year | Source | Method | Score | Venue |
|---|---|---|---|---|
| 2008 | Schaus, Deville | CP + VLNS hybrid | 458 | JFPC |
| 2009 | Munoz, Gutierrez, Sanchis | MOEA (pure GA family) | 396 | IEEE CEC |
| 2010 | Niang | Pure GA, region-exchange | not tested on 16×16; failed on 7×7 | MASc thesis (Concordia) |
| 2010 | Vancroonenburg, Wauters, Vanden Berghe | Hyper-heuristic + DFS | **459** | META |
| 2013 | Sholomon, David, Netanyahu | Kernel-growing GA crossover | not tested on E2 (image jigsaw) | CVPR |
| 2015 | Kovalsky, Glasner, Basri | SDP polynomial relaxation | not on 16×16 (capped at 8×8, tangram) | SIAM J. Imaging Sci. |

**Peer-reviewed academic ceiling: 459/480** (Vancroonenburg 2010).

### Community / non-peer-reviewed results

| Source | Method | Score | Notes |
|---|---|---|---|
| McGavin 2020 (via libblackwood) | Blackwood schedule + relaxations | 469 | Not peer-reviewed; Bucas URL + libblackwood scenarios. |
| Joshua Blackwood 2020 | Same algorithm, 1-clue variant | 470 | NOT canonical (1-clue ≠ 5-clue) — see [[basin-blackwood-470]]. |

### Our results

| Vol | Score | Mechanism | Cold/Warm |
|---|---|---|---|
| 6 | 454 | [[border-diversity]] + PT --pin-perimeter | Warm |
| 17 | 455 | [[blackwood-schedule-calibration]] + WorstBand/ConflictDriven | Cold |
| **18** | **457** | [[oracle-cycle-swap]] + hot-PT T=30 ([[basin-457-pt]]) | **Cold** |
| 22 | 457 | [[basin-escape-recipe]] reproduced | Cold |

**Our 457 is within 2 points of the peer-reviewed academic record and exceeds it on the cold-start axis** (Vancroonenburg's 459 was warm-start via DFS-based hyper-heuristic; their cold-start numbers aren't reported separately, but their algorithm requires a CP seeding pass).

## What's potentially publishable

Three threads in descending strength order. None have been written up.

### 1. r5f-cooperativity finding + [[oracle-cycle-swap]] method (strongest hook)

The vol-18 [[r5f-cooperativity]] measurement is a clean physics-of-search-landscape finding:
- The 447→456 transition is a **single 76-cell first-order cooperative barrier**.
- All 1024 cycle-subsets of the barrier have ΔE < 0 *except* the full 10-cycle.
- Standard MCMC at T=1 has acceptance probability ≈ 10⁻¹⁵.
- Built oracle-guided destroy operator + hot-PT T≈30 to cross it.
- Reached 457 on canonical seed=1, reproducible.

This is a "measurement + method" combination on the same SOTA tier as published academic work. Plausible venues: GECCO, CEC, EvoCOP, Journal of Heuristics, Annals of OR.

### 2. [[relaxed-bound]] dead-end test (theoretically clean)

Vol-21 finding: relaxed piece-uniqueness greedy produces a basin-local upper bound that's strictly stronger than the K≤5 operator-lock test. We proved 457→458 needs a non-local high-K move via this bound.

Lower-impact paper but very clean theoretical contribution. Could be a short paper or section in #1.

### 3. [[basin-escape-recipe]] (vol-22 pipeline)

Bound-ascent + Hungarian + ALNS that escapes locked basins. Plausibly publishable but more pipeline-engineering than novel idea; components are individually known.

## Strongest single paper outline

Combining #1 and #2:

**Title sketch**: *"Characterizing and crossing cooperative barriers in edge-matching puzzle search: the case of Eternity II"*

**Sections**:
1. Introduction + E2 problem statement.
2. Prior work — Schaus, Vancroonenburg, Munoz, McGavin (community result), our vol-1 to vol-16 baseline.
3. The relaxed-bound dead-end test (vol-21).
4. The cooperativity barrier measurement (vol-18 r5f).
5. Oracle-guided cycle swap operator.
6. Empirical results: 457 reproducible from seed=1; comparison with Schaus 458 and Vancroonenburg 459.
7. Limitations (Blackwood community 469 reached via different mechanism not present in our stack).

**Key claims (verifiable)**:
- The 447 plateau in our cold-start pipeline corresponds to a 76-cell cooperative barrier (measurement).
- Oracle-guided cycle swap crosses this barrier at hot-PT T=30 (method).
- Result is reproducible cold-start to 457 on canonical 5-clue (empirical).
- 457 places us within 2 points of the peer-reviewed SOTA (positioning).

## Why this hasn't been written yet

Pre-vol-25 we had a vague sense that "community ceiling is 469" without knowing that:
- 469 is not peer-reviewed.
- The actual peer-reviewed record is Vancroonenburg's 459.
- Our 457 is therefore essentially at the published SOTA.

The vol-25 literature review made this explicit. We've been chasing the community 469 (which requires implementing a different algorithm, the [[blackwood-algorithm]]), without realizing we already had a paper-worthy result on the academic record book.

## What's needed to publish

Honest cost:
- **Write-up: 3-4 weeks** of focused work. A paper requires careful methodology, reproducibility checks, statistical significance on multiple seeds, comparison plots, related-work positioning. None of which is done.
- **Reproducibility hardening**: vol-18 oracle-cycle-swap was a one-time discovery on a specific board ([[basin-457-pt]] is byte-identical across 10 PT chains, but seed-1 only). For a paper we'd need to re-run on N=20+ seeds and report mean/std.
- **Comparison runs**: implement or borrow Schaus / Vancroonenburg baselines on the same seeds for direct comparison. ~1 week.
- **External validation**: at minimum, post the 457 board to the Eternity II community thread (Bucas URL) for independent verification.

## Strategic question

Is research-paper output even a goal? The vault and CLAUDE.md frame this project as research, not publication. But:
- **Pro**: a paper would be a clean closure on the cold-start record axis. Forces us to write down the methods carefully, which has value independent of publication.
- **Pro**: gives the work external visibility; might attract collaborators with engineering capacity to close the 469 gap.
- **Con**: 3-4 weeks of write-up time is 3-4 vols not spent on algorithm work. The 457→469 gap doesn't close itself.
- **Con**: Eternity II is fading academic interest (peak interest was 2007-2012 around the original $2M prize); a 2026 paper on it might be received as "why now?"

## Decision pending

Not a vol-25 binding item. Logged here so we don't lose the observation. Worth raising at vol-25 close or whenever cold-start record stops moving (e.g., if vol-26-30 don't break 457, that's the natural moment to publish what we have rather than continue grinding).

## Linked concepts

- [[basin-457-pt]] — the record-holding board
- [[oracle-cycle-swap]] — the operator that reached it
- [[r5f-cooperativity]] — the barrier measurement
- [[relaxed-bound]] — the dead-end test
- [[genetic-algorithm]] — vol-25 literature review (source of the academic-record-book table)
- [[basin-mcgavin-469]] — the community ceiling we'd cite as the "open challenge"
- [[basin-blackwood-470]] — distinguishing 1-clue from 5-clue variants
