# Vol-56 — dual-track: basin lottery (bg) + CDCL no-good math (fg)

**Open**: 2026-05-15
**Theme**: First autonomous-vol-after-explicit-don't-wait directive.
**Status**: in-progress.

## T1 — basin lottery (background)

Launched `vanilla_fast --budget-ms 3600000 --threads 8
--thread-id-offset 600 --snapshot-dir output/vol-56/snapshots
--snapshot-min-depth 200` at 13:26 CEST. 1h budget, 8 threads,
snapshot every 30s when a NEW maximum depth ≥ 200 is reached.

After ~70s: 27 snapshots collected. Throughput is good. Will harvest
~hundreds of distinct deep partials over the hour, then run vol-22
basin-jump recipe on each.

Plan to assess at end-of-hour: count distinct partials by basin
(Hamming distance threshold), pick top-N for ALNS-PT lottery,
run for 6-12h overnight.

## T2 — CDCL no-good math (foreground)

Shipped `concepts/cdcl-no-good-e2.md` — full design document.

**Key contributions**:

1. **Precise definition** of no-good for E2 MaxCSP: a pair $(N, B)$
   where $N$ is a partial assignment and $B$ is a score bound on its
   completions.

2. **Soundness lemmas** for hard ($B=0$, AC-3 wipeout source) and
   soft ($B>0$, from incumbent + admissible UB) no-goods.

3. **Subtlety surfaced**: soft no-good minimisation is NOT monotone.
   Dropping a literal from $N$ may push the bound on completions of
   $N' \subsetneq N$ above $B$. 1-UIP analysis from SAT doesn't
   directly carry over for soft case. **Practical recommendation:
   MVP learns hard no-goods only**, defers soft case until hard works.

4. **Engine integration sketch**: AC-3 cause-tracking + 1-UIP +
   2-watched-literals + forget heuristic. Estimated 3-4 weeks for
   full build; ~1-2 days for Python-prototype MVP.

5. **Why this is genuinely novel**: untouched in 55 vols. ML/RL
   refuted, basin-escape saturated, LP-tightening confirmed
   irrelevant (vol-55). No-good learning is the classic CSP/SAT
   technique left.

## T3 — wipeout-distribution measurement (foreground)

Built `crates/bench-audit/src/bin/measure_wipeouts.rs`. Runs a 60s
canonical-E2 search with `joe_depth150_bp`, dumps:

- 267k nodes visited
- 46k backtracks
- 46k domain wipeouts
- **wipeouts / backtracks = 1.00** (every backtrack involves a wipeout)
- Wipeout depth range: [51, 165]
- Peak at depth 130-135 (~2.2k per depth)
- 2% of wipeouts at depth ≥ 150
- 0 wipeouts at depth < 51 (current AC-3 + profile prevents shallow failures)

### Interpretation

Positive signal for no-good learning:
- High wipeout count (~767/s) — many failures to learn from.
- Failures distributed across many depths — not all clustered at one
  point.

Concerning signal:
- Wipeouts at **depth ~130** mean naive no-goods are ~130-literal
  clauses. That's huge.
- The minimization step (1-UIP) is CRITICAL — without it, no-goods
  are too big to be useful.

### T3b — wipeout REPETITION measurement (built tonight, not deferred)

Built `bin/measure_wipeout_repetition.rs`: rebuilds the current
placement from `ValueTried`/`Backtrack` event stream, hashes the
position-set AND the full (pos, pid, rot) tuple-set at each wipeout.

**60s canonical-E2 run results**:

| Metric | Value |
|--------|------:|
| Wipeouts in 60s | 46,105 |
| Distinct position-set hashes | 30,840 |
| Distinct FULL (pos, pid, rot) hashes | 46,105 |
| Avg wipeouts per position-set | 1.49 |
| Avg wipeouts per FULL hash | **1.00** (100% unique) |
| Top position-set repeat count | 55 |
| Median stack size at wipeout | 134 |
| Stack range at wipeout | [52, 166] |

### Empirical verdict on no-good learning

**Mixed signal that tilts negative**:

1. **Naive full no-good learning has 0% hit rate.** Every wipeout
   has a different (pos, pid, rot) sequence. Storing full clauses
   gives nothing.

2. **Position-set repetition exists** (~33% of wipeouts hit a
   previously-failed position-set). With 1-UIP-style minimization
   identifying which sub-position-set triggers the failure, a cache
   COULD hit on these.

3. **But median clause size is ~134 cells**. Even minimised clauses
   would average maybe 5-15 literals (typical SAT/CSP minimisation
   ratios). Storage and lookup overhead scales with the index.

4. **The 1-UIP minimisation is the entire game**. Without it,
   no-good learning gives no benefit on E2. With it, the EV depends
   on minimisation effectiveness — historically in CSP this is
   highly problem-dependent.

### Implication for vol-57 build

The vol-56 T2 design doc said "MVP = hard no-goods only". The
repetition data now sharpens: **the MVP must include 1-UIP
minimization from the start** because naive storage hits never. This
makes the MVP 2-3 days, not 1-2 days as originally estimated.

The 3-4 week full build is still appropriate, but the priority
ordering shifts:
- Week 1: AC-3 cause-tracking + 1-UIP minimization (the must-have).
- Week 2: 2WL watch index + clause storage.
- Week 3: forget policy + tuning.

If 1-UIP minimization on canonical E2 produces clauses of average
size ≤ 20 with hit-rate >10%, no-good learning beats the LP arc.
If clauses average size ≥ 50 or hit rate < 5%, this direction is also
closed.

**The MVP measurement that decides**: a Python prototype that
performs AC-3 + 1-UIP on a small puzzle, measures clause
sizes/hit-rates. ~1-2 days. Top priority for vol-57.

### T1 update — basin lottery at ~9 min in

PID 5478 still running. 37 snapshots collected in 9 minutes. On track
for ~200+ snapshots in the hour budget. Sufficient diversity for the
overnight basin-lottery to follow.

## Subtotal: vol-56 deliverables so far

- `vault/concepts/cdcl-no-good-e2.md` (math design, ~250 lines)
- `crates/bench-audit/src/bin/measure_wipeouts.rs` (instrumentation bin)
- 30+ deep partial snapshots in `output/vol-56/snapshots/`
- Memory: `feedback_autonomous_dont_wait.md`

## Linked

- [[../concepts/cdcl-no-good-e2.md]]
- [[../sessions/vol-55]] — predecessor
- memory: `feedback_autonomous_dont_wait.md`
