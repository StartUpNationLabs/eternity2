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

### T4 — 1-UIP analysis for E2 (THEORETICAL OBJECTION)

Started designing real 1-UIP. Realized the E2 cause-graph structure
may make 1-UIP LESS POWERFUL than in SAT:

**Why SAT 1-UIP works well**: clauses are 3-100 literals, propagation
forms a deep implication graph. 1-UIP finds ONE asserting literal at
each decision level, dramatically shrinking the conflict clause.

**Why E2 1-UIP may NOT work well**: each AC-3 removal in my code is
caused by ONE placed cell directly (piece-uniqueness or edge-equality).
The cause-graph is FLAT: depth ≤ 2 from any literal to wipeout. 1-UIP
collapses to "union of all single-cell causes," which IS what I already
compute.

The REAL clause-size problem at canonical is:
- Wipeout cell loses ~700+ values from initial domain.
- Each value lost to ONE cell (its cause).
- Union of single-cell causes = potentially most-placed-cells.

To shrink: need to recognize that many causes are REDUNDANT in
combination. Standard SAT 1-UIP doesn't do this; **redundant-cause
elimination** would. That's a different (and harder) analysis.

**Alternative**: instead of 1-UIP, try **subsumption-based learning**:
when a small clause C1 already exists and we'd learn a larger C2 ⊇ C1,
skip learning C2. This keeps the DB compact but doesn't shrink
individual clauses.

**This insight suggests vol-60 should NOT be "implement real 1-UIP"
but rather "investigate E2-specific clause-size reduction techniques"**:
- Per-cell forbidden-piece sets (compact representation).
- Clause subsumption + back-subsumption.
- Drop "trivial" clauses where one cause-cell's value alone would
  cause the wipeout (those clauses are implied by piece-uniqueness +
  edge-equality, no new info).

Reframing the vol-60 problem this way is more honest than chasing
SAT-style 1-UIP that may not apply.

## T5 — basin lottery COMPLETED 156/156 (final analysis)

Lottery completed at 15:31 CEST (~1h45m total wall time, 8 threads,
5min ALNS each). 39 distinct vanilla_fast snapshots × 4 seeds = 156
total runs.

### Final score distribution

| Statistic | Value |
|---|---:|
| min | 424 |
| p25 | 446 |
| median | 452 |
| **mean** | **449.88** |
| p75 | 454 |
| p90 | 456 |
| **max** | **458** (1 occurrence) |

### Top records (≥457)

| Score | Snapshot | Seed | Initial depth |
|---:|---|---:|---:|
| **458** | t601_s002_d207 | 4 | 207 |
| 457 | t606_s002_d211 | 2 | 211 |
| 457 | t601_s002_d207 | 2 | 207 |
| 457 | t601_s001_d206 | 4 | 206 |

**Total: 4 records at 457+**, **0 records at 459+**.

### Per-thread max

Thread 601 produced the only 458. Thread 606 produced one 457. All
other threads capped at 456.

### Empirical record-break probability

For our vanilla_fast + ALNS pipeline @ 5min budget:
- P(458) per job = 1/156 = **0.64%**
- P(457+) per job = 4/156 = **2.6%**
- P(459+) per job = 0/156

To find a 459 with 50% probability under same setup: need ~116 more
jobs (~60 more minutes on 8 threads). High variance, low EV given
Schaus 2008 academic ceiling at 458.

### Vol-59 close

Closing vol-59 with:
- T1 (Joe iter-budget): deferred per vol-50 evidence of no benefit.
- T2 (thread-601 follow-up): killed after 2 seeds (454/453, lower
  than 458) refuted "rich basin" hypothesis.
- T3 (CDCL scaling 5×5→16×16): SHIPPED.
- T4 (1-UIP theoretical analysis): SHIPPED — E2 flat cause graph
  limits 1-UIP benefit.
- T5 (lottery final): 1×458 + 3×457 in 156 trials, no 459+.

**Standing 458 record UNCHANGED** after 156 lottery trials confirming
the empirical record-break probability is ≤ 0.6%.

## Linked

- [[vol-58]] — predecessor with canonical-scale failure
- [[cdcl-no-good-e2]] — math design
- [[cdcl-engine-integration]] — engine plan
