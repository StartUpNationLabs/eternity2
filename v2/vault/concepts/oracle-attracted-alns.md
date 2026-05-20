---
name: oracle-attracted-alns
description: Codebase: no existing op uses an oracle board as an attractor.
status: unbuilt
metadata:
  type: concept
---
# Oracle-Attracted ALNS (vol-69 design)

**Status**: `design` — vol-69 (2026-05-15).
**Type**: INVENTED ALGORITHM per directive.
**Inventor**: this autonomous run.

## Audit-at-design

Codebase: no existing op uses an oracle board as an attractor.
Vol-18 OracleCycleSwap applies σ-cycle from oracle but doesn't bias
the search toward the oracle as continuous objective.

## Motivation

Vol-65 found McGavin's 469-basin is topologically isolated at
Hamming 247 from any non-McGavin record. Standard ALNS with matched-
edge objective is GREEDY w.r.t. score; it never accepts moves that
go AWAY from current high-score basin even if they go TOWARD McGavin.

The maximally-adversarial thesis says: incremental score-improving
moves cannot escape 459. But maybe **moves that SACRIFICE score for
proximity to McGavin's piece-placement** could bridge the gap.

## The objective

Standard ALNS: maximize `f(B) = score(B)`.

Oracle-Attracted ALNS: maximize
`f_oracle(B, McG) = score(B) - λ · hamming(B, McG)`

Where λ is a tuning parameter and McG is McGavin's 469 board.

When λ = 0: standard ALNS (likely converges to 458-459).
When λ → ∞: all moves toward McGavin accepted regardless of score.
Intermediate λ: balance between score and proximity.

## The mechanism

```
def Oracle_Attracted_ALNS(B, oracle, lambda_schedule):
    for t in iterations:
        # Standard destroy-repair
        B' = destroy_and_repair(B)
        # Accept based on combined objective
        lam = lambda_schedule(t)
        f_old = score(B) - lam * hamming(B, oracle)
        f_new = score(B') - lam * hamming(B', oracle)
        if SA_accept(f_new - f_old, T(t)):
            B = B'
        # If we land in oracle's σ-orbit (hamming < 100), drop λ to 0
        # and let standard ALNS take over to refine.
        if hamming(B, oracle) < 100:
            lambda_schedule = lambda_zero
```

## Lambda schedule

- Cold start: λ = 0.1 (mild oracle attraction)
- Linear ramp: λ → 1.0 over first 5000 iterations
- Acceptance check at iteration 5000+: if no progress toward oracle
  (hamming hasn't decreased), spike λ to 5.0 (force-attract)
- Once hamming < 100: λ → 0 (let standard ALNS refine)

## Why this might work

The σ-cycle indecomposability blocks **score-strictly-improving**
moves toward McGavin. But Oracle-Attracted ALNS allows
**score-worsening but oracle-approaching** moves to be accepted at
high λ. This is the FIRST mechanism that decouples score from
basin-exploration.

If McGavin's basin truly is isolated by score-only metric, but
CLOSE in hamming-distance from SOME accessible basin, OA-ALNS
can bridge.

## Limits / refutation conditions

- If even oracle-attracted ALNS cannot reduce hamming below 100,
  the McGavin basin is structurally inaccessible.
- If λ collapses ALNS to nonsense (random moves toward oracle),
  no high-score recovery is possible.
- If the σ-cycle indecomposability ALSO applies to hamming-monotone
  moves (every hamming-reducing move strongly score-reducing),
  OA-ALNS gains nothing.

## Build plan

### Day 1
- Implement OA-ALNS in Python (no Rust port needed for prototype).
- Score = matched-edges (from cached grid).
- Hamming = piece-position diff to McGavin.

### Day 2
- Run from each of our 47 basin-component reps, with multiple λ schedules.
- Measure: minimum hamming reached, score profile, basin-component
  transitions.

### Day 3
- If hamming < 100 ever reached: ALNS-only mutation on result + report.
- If not: refute as another structural axis.

## Linked

- [[basin-permutation-group]]
- [[basin-component-landscape]]
- [[e2-maximally-adversarial-thesis]]
- [[vol-69]]
