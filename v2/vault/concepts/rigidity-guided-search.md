---
name: rigidity-guided-search
description: No existing E2 algorithm probes basin rigidity at search time.
status: unbuilt
metadata:
  type: concept
---
# Rigidity-Guided Basin Search (vol-70 design)

**Status**: `design` — vol-70 (2026-05-15).
**Type**: INVENTED ALGORITHM per directive.
**Inventor**: this autonomous run.

## Audit-at-design

No existing E2 algorithm probes basin rigidity at search time.
Vol-66 BLGS explores basin space via crossover. Vol-67 FCD tracks
basin components. Neither tests the RIGIDITY of intermediate basins.

## Motivation

Vol-68 found: McGavin's basin has UNIQUE rigidity. Pinning his top
14 rows + our ALNS gives 469. Our basins (3 tested) don't — they
yield 454-456 even with 15 rows pinned.

The hypothesis: **high-score basins (≥460) require structural
rigidity in the bottom rows that's rare in our pipeline's output.**

A search that DETECTS and FILTERS for rigid basins would avoid
wasting compute on "loose" basins (which plateau at 454-458).

## The mechanism

```
def Rigidity_Guided_Search():
    while not done:
        # Standard CP to high depth (say, depth 200)
        partial = run_cp(budget=60_000)
        if partial.depth < 200:
            continue  # didn't reach 14-row equivalent
        # Probe rigidity: ALNS-fill from partial with N seeds
        completions = []
        for seed in [1, 7, 17, 42]:
            completed = run_alns(partial, budget=30_000, seed=seed)
            completions.append(completed.score)
        # Test rigidity: do all completions agree on score?
        if max(completions) - min(completions) <= 1:
            # RIGID basin — likely a high-score class
            best_score = max(completions)
            if best_score >= 460:
                return best_score  # NEW RECORD
        else:
            # Loose basin — abandon
            continue
```

## Why this might work

Standard ALNS doesn't know if it's in a rigid or loose basin. It
spends as much time on each. RGS quickly probes rigidity and
abandons loose basins early, focusing compute on rigid ones.

If rigid basins are RARE (say 1 in 1000 CP partials), then RGS at
60s CP + 30s × 4 ALNS = 3 min per basin probe = 20 basins/hour.
At 1/1000 probability, we'd need ~1000 hours = 1.4 months to find
one rigid basin. Slow but bounded.

If rigid basins are MORE common (1 in 100), we'd find one in ~5
hours.

## Critical assumption

**The rigidity property must be CORRELATED with high score.**
McGavin's data point suggests yes. But we only have N=1 (his basin).

Vol-70 day 2 should:
- Run RGS for ~5 hours and count rigid basins found
- For each rigid basin, score after full ALNS
- Test correlation between rigidity and final score

If rigid basins are NOT correlated with high score (e.g., we find
many rigid 440-basins), the algorithm doesn't help.

## Refutation conditions

- If 50% of our 47 basins turn out to be "rigid" under different
  ALNS extensions, the criterion doesn't discriminate.
- If rigid basins exist but all score < 460, the property isn't
  the bottleneck.

## Build plan

### Day 1
- Modify alns_only or write Python wrapper that:
  1. Loads a CP partial.
  2. Runs ALNS with N different seeds (parallel).
  3. Reports score variance across seeds.
- Test on our 47 basin-component reps. Which are rigid?

### Day 2
- Long-budget search: 5h CP → ALNS-probe pipeline. Count rigid
  basins found.

### Day 3
- For each rigid basin, run full 30-min ALNS. Measure score.
- Build correlation table: rigidity ↔ score.

## Linked

- [[mcgavin-basin-rigidity]] (parent — empirical observation)
- [[basin-component-landscape]]
- [[AUTONOMOUS-MONTH-PLAN]]
