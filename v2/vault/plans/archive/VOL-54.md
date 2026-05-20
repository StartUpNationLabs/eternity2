# VOL-54 — where does the LP-integer gap actually live? (math investigation)

**Open**: 2026-05-15
**Predecessor close**: vol-53 partially refuted vol-52 per-piece column-gen.

## Why this vol

Vol-50 and vol-53 made **contradictory** claims about where the
~20-point LP-integer gap comes from on canonical-E2 boards:

| Source | Claim |
|---|---|
| Vol-50 [[lp-integer-gap-anatomy]] | 33% fractional-y, 67% integer-rounding loss from piece-uniqueness joint-infeasibility |
| Vol-53 [[per-piece-column-gen-6x6-worked]] | gap comes from y-linearisation interacting with piece-uniqueness at scale; toy LPs had zero gap; "even when each piece's Σ_{c,r} x = 1, y can take fractional values that integer x cannot achieve" |

These cannot both be right. Vol-50's '67% piece-uniqueness'
table is from per-color LP UBs with **?'s** for integer columns.
Vol-53's refutation came from toy LPs with **no edge structure** (2-3
cells, 3-4 pieces — nothing like the real y-min-of-sums geometry).

The 458 record is "near-globally-optimal for current search algorithms"
only IF we know what the gap actually is. We don't.

**A bad answer to this question wastes 3-4 weeks of B&P engineering on
the wrong relaxation. A good answer tells us which direction to attack.**

## Binding item — math investigation in 2 parts

### T1 — Fill the per-color INTEGER matches table for vol-32 458 board

Vol-50 has a per-color LP-UB column from
`output/vol-44_border_lp_ub/per_color_458.log`. The integer column
is `?` everywhere. Fill it by directly counting integer matches per
color on the verified board.

Outcomes:
- If `Σ floor(LP_UB_k) - Σ integer_k ≈ 12`, vol-50's "12 points
  piece-uniqueness" claim survives — each color hits its LP-attainable
  floor but they can't be jointly realised.
- If `Σ floor(LP_UB_k) - Σ integer_k ≈ 0`, vol-50's claim is wrong —
  the integer board is per-color tight. Then vol-53's "y-linearisation
  loose at scale" inherits the burden of explanation.

### T2 — Small y-LP-with-x-integer test (sharpens vol-53)

Take a 6×6 verified integer board. Fix x to that integer assignment
(every `x[p, c, r] ∈ {0, 1}`). Write the y-LP:
- `y[c, c', k] ∈ [0, 1]` for each I-I edge and color.
- `y[c, c', k] ≤ a[c, side, k]` and `y[c, c', k] ≤ b[c', side, k]`.
- `Σ_k y[c, c', k] ≤ 1`.
- Objective: max `Σ y`.

Predict: with x integer, a and b are integer (0 or 1 per edge-side-color).
`min(a, b)` is then 0 or 1, and the LP collapses to the integer matching.
LP = integer.

If LP = integer at integer x ⇒ the gap on canonical-E2 is **entirely
from fractional x**. Vol-53's "y-fractionality even at integer-piece
allocation" intuition is wrong. The gap mechanism is what vol-50 said,
just possibly miscounted.

If LP > integer at integer x ⇒ y-linearisation IS loose in itself,
vol-53 right, and per-piece column-gen can't close it.

### Connecting T1 + T2

| T1 outcome | T2 outcome | Verdict on vol-50 vs vol-53 |
|---|---|---|
| floor-tight per color | LP = integer | vol-50 right but mis-narrated; gap is joint-x-fractional → tight relaxation possible by handling x-joint structure |
| floor-tight per color | LP > integer | vol-53 right; y-cuts needed (not just x decomposition) |
| floor-LOOSE per color | LP = integer | gap *is* piece-uniqueness; vol-50 right; per-piece column-gen could work |
| floor-LOOSE per color | LP > integer | both contribute; need both tightenings |

This is the cheap math that should have been done before vol-52's
3-4 week estimate.

## Audit-at-open compliance

Aged `unbuilt` items in BACKLOG, decisions:

- `mcgavin-prune-restart-bound-trigger` (since vol-36): **built at vol-51** with bound-trigger; recovery bottleneck. Status amended at vol-51 close. Aged-resolved.
- `unsat-soft-value-order-vol37` (since vol-34): **DEFER** — vol-34 measured signal at d<100 but is unrelated to current LP-axis investigation; cheap (4-6h) but orthogonal. Keep `unbuilt`.
- `rl-self-play-value-order` (since vol-30): **DEFER** — multi-week; vol-29 closed imitation ceiling, RL is the only structural path, but contained-EV within single autonomous session is poor. Keep `unbuilt`.
- `code-refactor-vol25-batch` (since vol-25): **DEFER** — engineering. Pure dedup. Vol-54 is math; not a refactor vol.
- `extract-eternity2-time-crate` / `-export-crate` / `split-solver-engine-lib` / `consolidate-bin-harness` (since vol-25): **DEFER as a group with code-refactor batch**.
- `incremental-ac3-count-maintenance` (since vol-25): **DEFER** — perf engineering. EV +10-15% on joe. Not record-track.
- `restore-or-simd`, `profile-bin-use-null-sink`, `precompute-cell-nb-info`, `vault-validation-of-perf-wins` (since vol-25): **DEFER** — same engineering bucket.
- `diverse-457-search` (since vol-21): **DEFER** — overnight compute, never blocking.
- `multi-cell-bound-ascent` (since vol-22, double entry): **WONT-DO** — vol-22 measurements showed bound-ascent reaches 473 then ALNS collapses every step. Multi-cell variant inherits the recovery problem. Mark wont-do; add to next backlog edit.
- `bound-floor-alns-with-per-step-check` (since vol-22): **WONT-DO** — invasive 1-2d for diagnostic value; same recovery bottleneck.
- `tight-joint-bound-survey` (since vol-22): **WONT-DO** — blocked on `kissat-rc2-maxsat` which is wont-do; diagnostic, not lever.
- `joe-iteration-budgeted-prune` (since vol-32): **DEFER** — half-day, score-axis lever, but orthogonal to current math investigation.
- `learned-on-ties-long-pt` (since vol-31): **DEFER** — compute-only overnight job.
- `insertion-order-under-joe-depth150-bp` (since vol-32): **DEFER** — characterisation work for vol-33+.
- `unsat-clause-propagator-prototype` (since vol-32): **DEFER** — Python prototype shipped; Rust integration is a separate vol.

Net: 3 wont-do moves (`multi-cell-bound-ascent`, `bound-floor-alns-with-per-step-check`, `tight-joint-bound-survey`). All others defer with stated reasons.

## Why 1 binding item, not 3

Per CLAUDE.md "3 binding items max, often 1". The T1+T2 split here
IS one investigation — the per-color table + the y-with-integer-x
test are TWO measurements answering ONE question. Splitting them
gives a 2x2 outcome matrix that decides direction unambiguously.

## Linked

- [[vol-50]], [[vol-53]] — the conflicting claims
- [[lp-integer-gap-anatomy]] — vol-50 table to fill
- [[per-piece-column-gen-6x6-worked]] — vol-53 refutation
- [[lifted-lp-column-gen-per-piece]] — what's at stake
