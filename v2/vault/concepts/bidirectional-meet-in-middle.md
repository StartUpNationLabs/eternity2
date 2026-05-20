# Bidirectional Meet-in-Middle (V175 GAUNTLET)

Status: `unbuilt` (design 2026-05-20)
Origin: vol-175 (planned)
Naming: **GAUNTLET** — two armies converging on a single combat zone.

## Idea

Current CSP-based and beam-search approaches all proceed in one direction: either top-down (start at row 0, fill toward row 15) or border-first (place ring, then interior).

GAUNTLET runs **two beams simultaneously**:
- **Forward beam** $\mathcal{F}$: places pieces top-down starting from row 0.
- **Backward beam** $\mathcal{B}$: places pieces bottom-up starting from row 15.

After $d$ depth each, both beams have placed roughly half the board. The interface is at row 7-8 (or some chosen meeting row $m$).

**Meet condition**: at depth $d = m \cdot 16$, beams have populated rows $\{0, \ldots, m-1\}$ from above and $\{m+1, \ldots, 15\}$ from below. The remaining row $m$ is jointly searched.

## Math — depth and beam sizing

For canonical 16×16 E2 with 256 cells:
- Forward beam fills $m \cdot 16$ cells.
- Backward beam fills $(15 - m) \cdot 16$ cells.
- Joint row has 16 cells.
- $m \cdot 16 + (15 - m) \cdot 16 + 16 = 256$. ✓

For balanced halves: $m = 8$. Forward fills rows 0-7 (128 cells); backward fills rows 9-15 (112 cells); row 8 jointly resolved (16 cells).

## Why genuinely different

- **Cross-beam compatibility check.** Existing approaches don't filter by reachability of the goal from a partial state. GAUNTLET prunes any forward partial $f$ that is incompatible with ANY backward partial $b$ (i.e., $f$'s southern edge colors at row $m-1$ don't match any feasible $b$'s northern edge colors at row $m+1$). This is a *bidirectional reachability* prune, much stronger than per-side CSP propagation.

- **Bidirectional info.** Hints at positions 135 and 210 are in the lower half — backward beam benefits from them early. Hints 34, 221, 45 are in the upper half — forward beam benefits. Each beam uses its 2-3 hints from the start; no need to wait until depth 100+ to feel hint effect.

- **Halving the search space.** If each beam keeps $K$ partials, the joint cardinality is $K^2$ but the reachability filter cuts this to $\approx K \cdot \text{compatible-prefix-rate}$. For E2's color constraint graph, the compatible rate at the meeting interface is empirically estimable.

## Algorithm sketch

```
Initialize F = { empty_board }, B = { empty_board }
For depth d in 0..(meeting_depth):
    F = expand_forward(F, scan_forward[d]); top-K-prune
    B = expand_backward(B, scan_backward[d]); top-K-prune
    if d % CROSS_CHECK_INTERVAL == 0:
        # Build compatibility hash on the dividing-row edges
        H_north_of_meeting = { hash(b.northern_edge_colors_at_meeting) : b }
        Filter F: keep only f where f.southern_edge_colors_at_meeting matches some b ∈ B
        Symmetric: filter B by F
Resolve_meeting_row(F, B): for each (f, b) pair, search-fill row m using remaining pieces.
```

## Implementation plan

Stage 1 (1 day): build `gauntlet_beam` bin as a fork of `v155_weaving_prior`. Run forward and backward beams sequentially (single thread), check meeting compatibility.

Stage 2 (1 day): parallelize forward and backward beams across 2 threads (rayon).

Stage 3 (2 days): the cross-check prune. Build a Bloom filter / hash table on the meeting-edge fingerprints. Implement compatibility queries.

Stage 4: ALNS-fill the joint row + any unfilled cells.

## What we expect

H1: bidirectional beams find higher-score boards in less wallclock than unidirectional, because cross-check eliminates dead-ends earlier.

H2: GAUNTLET's distribution of basins differs from V155's. New corner-perm × meeting-fingerprint configurations.

H3: at K = 256 per beam, joint K² = 65k — manageable. Cross-check prune may reduce to K-effective ≈ 1000-10000.

## What's still open

- Choice of meeting row $m$. Symmetry ($m = 8$) is balanced, but $m = 12$ (only 4 rows backward) might be faster.
- Should the backward beam use the same prior as forward, or a *backward prior* (corpus matrix reflected)? The prior was built directionless, but the placement order matters.
- Three-way split: forward + backward + center-out, meeting at two interfaces.

## Linked

- [[../sessions/vol-175]] (planned)
- [[prior-data-augmented-beam]] (V155 forward beam, the base)
- [[murmuration-basin-sampling]] (V171, complementary basin discovery)
- [[../plans/INVENTIONS_BACKLOG]] (A5)
