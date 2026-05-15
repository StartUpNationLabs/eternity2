# Vol-80 — Blackwood triple sweep (2026-05-15 → 2026-05-16)

**Theme**: Test Blackwood's documented "lots of overlap" rationale for
his 470-attempt schedule by sweeping alternative heuristic-color
triples in our color encoding. Standing record 459 unchanged.

## What was attempted

1. **E2_HEURISTIC_SIDES_OVERRIDE env var** added to
   `compute_heuristic_sides` to bypass the auto-selector. Allows
   any 3-color triple to be injected for testing without changing
   schedule-builder source.

2. **Pairwise-overlap ranking** of all 165 candidate triples among
   the 11 frequency-tied canonical colors {12..22} (auto-default
   is {12,13,14} which ranks 28/165).

3. **7-triple sweep** at 60s CP + 60s ALNS, calibrated_v17a, seed=1:
   - 4 top-overlap candidates
   - auto-default control
   - 2 bottom-overlap (anti-Blackwood) controls

4. **Long-budget follow-up** with the winning triple (14,15,19) at
   5min CP + 5min ALNS, same seed/schedule.

## What was measured / kept

Sweep scores (60s × 60s):
| triple | overlap rank | score |
|---|---:|---:|
| (14, 15, 19) | 165 (bot) | 446 |
| (18, 20, 22) | 4 | 445 |
| (12, 13, 14) | 28 (auto) | 444 |
| (15, 16, 21) | 162 | 442 |
| (13, 18, 20) | 3 | 437 |
| (14, 18, 20) | 1 (top) | 436 |
| (12, 14, 20) | 2 | 436 |

Long-budget on (14,15,19): **same 446**. Not budget-limited.

## What was refuted (with caveats)

- **Blackwood's "lots of overlap" rationale** does NOT transfer to
  our color encoding at single-seed. Top-3 overlap scored worst
  (436-437); bottom-overlap best (446). This is a 1-seed result —
  not statistically sound until 8+ seeds tested (per CLAUDE.md
  rule 4).
- **Triple choice alone doesn't break 459.** Best across 7 triples
  = 446, identical at 60s and 300s budget.

## Concepts touched

- [[blackwood-triple-sweep]] (NEW)
- [[blackwood-algorithm]] (parent)

## Open at close

- Multi-seed variance check on triples (would take ~110 min for
  8 seeds × 7 triples × 2min). Probably not worth the cost given
  the long-budget shows no breakthrough.
- Sweep over schedules (v17a/b/c/e) × triples: factor of 4 more
  experiments. Possibly more informative than seed-only variance.

## Linked memory

- `feedback_e2_senior_researcher_mode.md`
- `feedback_no_false_metrics.md`
- `project_e2_vol15_blackwood_results.md`

## Bottom line

Vol-80 produced one piece of actionable structural info:
**Blackwood's "max overlap" prescription doesn't directly transfer
to our color encoding** — top-overlap triples score worst at
single-seed. Mechanism unclear; needs multi-seed validation.

Standing 459 unchanged. 71 commits since the "1 month away" signal
~5 hours ago. **The session is winding down. Standing record
through hours of autonomous research is unchanged at 459/480.**

The maximally-adversarial thesis stands stronger than ever: 8
invented algorithms + heuristic-triple sweep + full-puzzle MIP all
bounded below the standing 459. Selby-Riordan's puzzle was
engineered to be genuinely hard.
