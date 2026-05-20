---
name: j1-forward-look-heuristic
description: "J1 forward-look heuristic: instead of greedy current-band-score, weight each chain state by a 'remaining color supply' compatibility score. Could prevent the band 12-14 decay."
metadata:
  type: project
status: built
---

# J1 — Forward-Look Heuristic

## Observation

Greedy J1 chain (beam=100k) produces:
- 8 PERFECT bands (0-7): score 46 each.
- Decay bands 8-14: 45, 45, 43, 42, 40, 36, 35.

**The decay is monotone** and accelerates near the end. Total final
matched = 444. Standing 459. Gap = 15.

## The greedy horizon problem

At band $r$, the algorithm commits row $r+1$'s bottom edges based ONLY
on maximizing band $r$'s score. The committed colors at row $r+1$'s
bottom must match band $r+1$'s top edges (their top, which is row $r+1$'s
top).

When the greedy chain reaches band 13, the REMAINING pieces have:
- 32 pieces left (256 - 7×16 = 32)
- Color profiles that may not match band 13's bottom = row 14's top.

## Forward-look heuristic (FLH)

At band $r$, when selecting the top-K states for the next band, weight
by **forward compatibility**:

$$
\text{state\_value}(s) = \alpha \cdot \text{score}(s) + \beta \cdot \text{forward\_compat}(s)
$$

where:

$$
\text{forward\_compat}(s) = \sum_{c=0}^{n-1} \min\!\left(\text{supply}_k(s) : k = \text{bottom\_color}(s, c)\right)
$$

Intuitively: how many remaining pieces have a color matching the BOTTOM
of cell $(r+1, c)$ on their TOP edge. If many remaining pieces can serve
row $r+2$, the chain has more flexibility.

## Math

Let $\mathcal{R}_r(s)$ = set of pieces remaining (not used by state $s$
through band $r$).

For each column $c$, the row $r+2$ at column $c$ must have a piece whose
TOP edge matches $s$'s bot[c].bottom. Let
$$
\nu_c(s) = \left|\{p \in \mathcal{R}_r(s) : p.\text{TOP} = s.\text{bot}[c].\text{B} \text{ in some rotation}\}\right|
$$

Forward compat:
$$
\text{FC}(s) = \prod_c \nu_c(s) \quad \text{or} \quad \sum_c \log(1 + \nu_c(s))
$$

The product gives the order-of-magnitude available paths; the log-sum is
additive and easier to use as beam-score.

## Beam-prune with FLH

Instead of sorting purely by score, sort by $\alpha \cdot \text{score} + \beta \cdot \text{FC}$.

Tuning $\alpha = 1$, $\beta \in [0.01, 0.1]$ keeps score dominant but breaks
ties by forward compatibility. Small but possibly significant for late-band
decay.

## Implementation cost

Computing FC per state costs $O(n \cdot |\mathcal{R}|)$ = $16 \cdot 32 = 512$
ops at band 13. Across $\text{beam} = 100k$ states: $5 \times 10^7$ ops/band.
At 100M ops/sec in Rust: 0.5s per band — affordable.

## Expected benefit

If FLH prevents bands 12-14 from losing 11+11+10 = 32 edges, and instead
losses spread to bands 8-14 at ~3 each, total = 46×8 + 43×7 = 369 +301 =
670 vs current 654. Final-matched: ~459.

That's right at standing record. Worth trying.

## Status

`design-complete` — implement next.

## Linked

- [[j1-column-dp-design]]
- [[j1-rust-beam100k-first-complete-board]]
- [[j1-band-14-failure-analysis]]
