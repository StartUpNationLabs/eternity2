# Vol-35 — 457 basin landscape (pairwise Hamming)

**Date**: 2026-05-14.

## Setup

6 distinct cold-start record-tie 457 boards, all rescore-verified
to 457/480:

| # | source | origin |
|---:|---|---|
| 0 | blackwood_mrv 5min seed 7 | vol-32 |
| 1 | blackwood_mrv 5min seed 10 | vol-32 |
| 2 | blackwood_mrv 30min seed 4 | vol-32 |
| 3 | vol-34 t1signal seed 1 | vol-34 T3 |
| 4 | vol-34 t3 t01 seed 1 | vol-34 T3 |
| 5 | vol-35 family 255 (deep + 60s — byte-identical) | vol-35 T1b |

## Pairwise Hamming (piece + rotation must both match)

```
         [0]  [1]  [2]  [3]  [4]  [5]
[0]  s7    0   53  161  247  249  249
[1]  s10  53    0  164  246  249  248
[2]  s4  161  164    0  249  249  249
[3]  t1  247  246  249    0  250  248
[4]  t3  249  249  249  250    0  246
[5]  f255 249  248  249  248  246    0
```

Mean=223.8, min=53, max=250.

## Cluster interpretation

- **Cluster A**: s7 + s10 — H=53 (sister basins, share ~80%
  of cells)
- **Cluster B**: s4 — H≈162 from A (same-family but distant)
- **Cluster C**: t1signal — H≈247 from A,B
- **Cluster D**: t3_t01 — H≈249 from everything
- **Cluster E**: f255 — H≈248 from everything

→ **5 distinct 457 basin attractors** at cluster level.
Three of these (C, D, E) found by independent methods
(vol-34 T3 thread-id-offset scan, vol-35 T1b family lottery).

## Implication

Memory note `project_e2_vol20_operator_lock.md` says the single
vol-20 457 was operator-locked under all K≤5 moves. **Different
457 basins are NOT clones** — they are genuinely independent
attractors at piece+rotation level.

The 5 distinct attractors found cold-start in vol-32 to vol-35
suggest a moderately rich 457-class on canonical E2. The
question is whether the **PT lottery** mentioned in
`project_e2_vol20_operator_lock` (10 byte-identical PT-457
boards) found just ONE of these clusters or a different one.

## Caveat — vol-32 memory revision

The vol-32 memory says blackwood_mrv 457s are "byte-identical".
That refers to the `.pt_e2.json` PT-overlay files OR a subset I
haven't located. The cold-start `RECORD_TIE_457_blackwood_mrv_*.json`
files we have here are NOT byte-identical:
- s7 vs s10: H=53 (close but distinct)
- s7 vs s4: H=161 (basin-distant)

So at minimum the three vol-32 cold-start blackwood-mrv 457s are
**not all the same basin** — two are sister-basins, one is more
distant.

## Edge-relax bound per cluster

Ran `edge_relax --max-iters 20` on each cluster rep:

| Cluster | rep | bound | gap above 457 |
|---|---|---:|---:|
| A | blackwood_mrv s7 | 462 | +5 |
| B | blackwood_mrv s4 | **465** | **+8** |
| C | vol-34 t1signal | 464 | +7 |
| D | vol-34 t3_t01 | 464 | +7 |
| E | vol-35 f255 | 463 | +6 |

**Cluster B has the highest bound (465)** — 8 above current score.
This is the most promising target for further ALNS recovery.

The bound depends on the cluster, not the score. Two boards both
at score 457 can have very different headroom. The vol-21 measurement
methodology (bound on the partial that fed ALNS) gave family 255 →
463; running the same on the recovered 457 board itself gives a
slightly different value (462–465 across clusters) because the
relaxed greedy iterates differently from different starting points.

## Consensus-core analysis (confirms vol-20)

Across the 5 distinct cluster representatives (A,B,C,D,E), counted
how many clusters agree on (piece_id, rotation) at each position.

Full agreement (5/5): **5 cells = canonical hints**
- pos 34 (r=2,c=2) → piece 207
- pos 45 (r=2,c=13) → piece 254
- pos 135 (r=8,c=7) → piece 138
- pos 210 (r=13,c=2) → piece 180
- pos 221 (r=13,c=13) → piece 248

3/5 agreement: 4 cells (1.6%)
2/5 agreement: 95 cells (37.1%)
1/5 agreement (idiosyncratic): 152 cells (59.4%)

**This is exactly the [[../../../../Users/raphaelanjou/.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2-v2/memory/project_e2_vol20_backbone_correction.md|vol-20 backbone correction]] result on a fresh sample**: only the
5 canonical hints carry cross-cluster weight; no other cell achieves
4/5 or 5/5 agreement. Pinning anything beyond the 5 canonical hints
will over-constrain the search.

No "backbone" beyond hints discovered. Second independent confirmation
of vol-20.

## Greedy bound-ascent on cluster B (vol-22 reproduction)

Ran greedy bound-ascent (only accept bound-monotone moves) on
cluster B's 457 board (initial bound=465):
- 5000 iters, 1455 accepts in 165s
- best bound reached: **470** (+5 from start)
- best score at that bound: **78** (massive score collapse)

This reproduces [[../../../../Users/raphaelanjou/.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2-v2/memory/project_e2_vol22_basin_escape.md|vol-22's finding]]:
greedy bound-ascent CAN find higher-bound basins (up to 471 in
vol-22, 470 here in 165s), but the score collapses to <100 and
ALNS recovery in those fresh basins plateaus at ceiling-25..30.

A bound=470 board with -30 recovery would land near 440 — not
a record. The vol-22 conclusion holds: **bound-ascent without
matching ALNS-recovery upgrade is a dead end**.

The unshipped tool from vol-22 backlog: McGavin-style prune-restart
that retains more of the basin context as it walks. That would be
the real unblock to converting high-bound destinations into score.

## σ-cycle distance to 458 record

Used `oracle_cycle_swap` to compute the piece-permutation distance
between each 457 cluster and the vol-32 458 board.

| Cluster | rep | # cycles | longest cycle | applying all cycles | applying cycles+rot |
|---|---|---:|---:|---:|---:|
| A | blackwood s7 | 12 | 114 | **458 (+1)** ✓ | 458 |
| B | blackwood s4 | 6 | 191 | 454 | **458 (+1)** ✓ (1 rot fixup) |
| C | vol-34 t1signal | 11 | 56 | 447 | 447 |
| D | vol-34 t3 | 13 | 52 | 434 | 438 |
| E | vol-35 f255 | 13 | 77 | 426 | 430 |

**KEY**: clusters A and B reach the 458 board via σ-cycle
decomposition (A directly, B with 1 rotation fixup). Both are in
the **458 piece-multiset family**. Cluster C is partial (cycle
application drops below 458); D and E are different families.

So in piece-multiset space, the 458 family includes 4 known boards:
- vol-32 458 (record)
- cluster A: blackwood_mrv s7 (457)
- cluster A': blackwood_mrv s10 (457, sister of s7 at H=53)
- cluster B: blackwood_mrv s4 (457)

That's **3 distinct 457 boards + 1 458 board** in the same family,
all from blackwood_mrv runs. Clusters C, D, E are genuinely
disjoint piece-multiset families.

**Implication for ALNS escape**:
- Cluster B → 458 is a coordinated 191-piece-permutation, far
  beyond current ALNS destroy capability (max K=80 destroys
  ~80 cells; this needs 191 coordinated).
- Cluster C → 458 has 11 simultaneous cycles, all needed for
  consistency. ALNS can't apply 11 coordinated swaps in one move.

The 458 sits in a "neighborhood" of cluster B in piece-multiset
space but not in spatial-placement space (full H=249/256). The
vol-22 finding that ALNS-PT plateaus at ceiling-25..30 in fresh
basins implies that the cluster B → 458 transition CANNOT be
made via local search without oracle guidance.

The structural insight: **`polish_rotations` is already optimal
on cluster B's 457** (no rotation fixup found by local search).
The "1 rotation fixup" reachable from cluster B comes only AFTER
applying the 191-cycle σ-permutation — it's a different piece
arrangement, not the current one.

## Vol-36 follow-up

- Run K=6, K=8, K=10 operator-lock test on the 5 distinct
  457-cluster representatives. Are they all individually
  operator-locked, or do some have escape routes a larger move
  would find?
- Bound-relaxed score on each: family 255 has bound 463. What
  about the other 4 clusters' bounds? Plug each into bound-ascent
  (vol-21) for one-shot bound calculation.
- Hungarian / OT-distance between cluster representatives: are
  there piece-permutation matchings that bridge them?

## Linked

- [[../sessions/vol-32]] — original 458 record + 457 ties
- [[../sessions/vol-34]] — 4-basin discovery via T3
- [[vol-35-t1b-family-lottery]] — family-255 458 attempt
- [[../../../../Users/raphaelanjou/.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2-v2/memory/project_e2_vol20_operator_lock.md|memory:vol20-operator-lock]]
