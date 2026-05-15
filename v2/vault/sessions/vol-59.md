# Vol-59 — Joe iter-budget + thread-601 followup + CDCL scaling

**Open**: 2026-05-15 (continuation of autonomous session)
**Status**: in-progress.

## T2 — thread-601 follow-up (running)

Launched: 16 seeds × 15min ALNS on `t601_s002_d207`, parallel=2
sharing CPU with lottery's 8. ETA 2h. Monitor armed for 458+ events.

## T3 — CDCL scaling across puzzle sizes (built tonight)

Tested cdcl-proto on 5×5 through 16×16 puzzles. Key result:

| Size | Vanilla nodes | CDCL nodes | Ratio | Avg clause | Unit-props |
|------|---:|---:|---:|---:|---:|
| 5×5/4c | 254 | 83 | 0.33 | 4.4 | 4 |
| 7×7/6c | 1,063,352 | 31,160 | 0.029 | 8.3 | 7,891 |
| 8×8/7c | 728,289 | 48,335 | 0.066 | 11.0 | 6,562 |
| 10×10/9c | 354,033 | 43,603 | 0.123 | 21.8 | 8,020 |
| 12×12/12c | 184,226 | 19,846 | 0.108 | 23.8 | **2** |
| 16×16/22c | 113,309 | 9,149 | 0.081 | 96.1 | **0** |

### Findings

1. **Node ratio stays ~10% across sizes**. CDCL algorithm consistently
   explores far fewer nodes than vanilla.

2. **Average clause size grows roughly linearly with puzzle size**:
   4.4 → 8.3 → 11 → 22 → 24 → 96 literals for sizes 5 → 7 → 8 → 10 → 12 → 16.

3. **Unit-propagation HIT-RATE CRASHES at 12×12**. From 8000+ props
   at 7-10× sizes down to 2 at 12×12 and 0 at 16×16. The clauses are
   too big to fire as units (≈24 literals requires 23 of them to be
   simultaneously assigned + the 24th to be a candidate value).

4. **The 7×7 wall-clock win does NOT scale**. Naive cause-tracking
   produces clauses whose size grows with puzzle size, and large
   clauses fire less often. Real 1-UIP implication-graph minimization
   is essential to maintain small clauses at scale.

### Implication

The vol-57+vol-58 conclusion is now precisely quantified:
- **At ≤10×10, our naive CDCL works.** It's a real algorithmic win.
- **At 12×12+, clauses outgrow their usefulness as unit-prop sources.**
- **Real 1-UIP via cause-graph walking is the critical missing piece**
  to scale CDCL to canonical 16×16.

### Vol-60+ engineering scope

To make CDCL competitive at canonical 16×16:

1. **Replace `analyze_conflict` with real 1-UIP**: walk the cause
   graph from the wipeout cell BACKWARD through chained removals,
   stop at the first node where exactly one literal is at the highest
   decision level in the conflict cut. The asserting clause is the
   negation of literals at LOWER levels + that one UIP literal.

2. **Quantitative target**: avg clause size ≤ 15 at canonical scale,
   unit-props per node ≥ 1.0.

3. **Build cost**: 3-5 days careful Rust work. The cause-tracking
   already exists (vol-57); the graph-walking + level-tracking is
   new.

This is the next concrete vol-60+ work, with measurable success
criterion.

## Linked

- [[../sessions/vol-58]] — predecessor with canonical-scale failure
- [[../concepts/cdcl-no-good-e2]] — math design
- [[../concepts/cdcl-engine-integration]] — engine plan
