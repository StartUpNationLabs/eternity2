# VOL-32 — does ML-derived seed unlock vol-22's basin-escape recipe?

**Opened**: 2026-05-13 (vol-31 close).
**Status**: drafted; awaits open.
**Gated on**: vol-31 PASS (+10 weak / +8 strong score lift from
LearnedOnTies-174 partial). Now we test whether the *better starting
basin* enables vol-22's basin-escape recipe to find a >457 basin.

## Why this volume exists

Vol-31 closed at 445/480 from LearnedOnTies-174 via 15-min strong PT —
above the 437 baseline at iso-budget, well below the 457 record. The
457 record came from vol-18's hot-PT *finding a specific lucky basin*
that vol-22's basin-escape recipe confirmed is locked under all moves
we've tried. **The +8 from vol-31 might or might not survive when we
scale the recovery pipeline to vol-22's full machinery.**

Two distinct hypotheses:
1. **Ceiling preserved**: 445 is a real plateau for the
   LearnedOnTies-174 basin. Vol-22's basin-escape recipe from this
   starting basin reaches ≤ 457 (matches or below our record).
2. **Ceiling broken**: the LearnedOnTies-174 partial seeds a
   *different* basin family than vol-18's discovery, with a higher
   ceiling. Vol-22's recipe from this basin finds > 457.

Hypothesis 2 is the record-break case. Cost: ~1 day to wire, then
overnight compute.

## Audit-at-open

Items aged ≥ 3 vols by vol-32 open:

- `multi-cell-bound-ascent` (9 vols, ALNS-axis). Deferred 5+ times.
  Mark `wont-do` per the "5 deferrals = wont-do" rule.
- `bound-floor-alns-with-per-step-check` (9 vols, ALNS-axis). Same.
- `diverse-457-search` (10 vols). Same.
- Vol-31 BACKLOG additions (`learned-on-ties-long-pt`,
  `learned-on-ties-hyperparam-sweep`).

## Binding items

ONE only — pick the highest-EV record-break attempt.

### T1 — LearnedOnTies-174 + basin-escape recipe

1. Run vol-22's basin-escape pipeline on LearnedOnTies-174:
   - Start from `output/pt_e2_1778700960_445of480.json` (the
     LearnedOnTies-174 → PT-15min result, score 445).
   - Apply bound-ascent + Hungarian repair + ALNS in the basin-escape
     loop (see `concepts/basin-escape-recipe.md`).
   - Run for 2-4 hours overnight.
2. Compare final score to:
   - Vol-22 baseline (basin-escape from cold-start = 457).
   - The 457 record (vol-18 hot-PT discovery).

**Gate condition** (set before running):
- **PASS (record break)**: final score ≥ 458.
- **MATCH**: final score = 457. Suggests LearnedOnTies seeds the SAME
  basin family as vol-18's discovery. No new lever, but cheaper path
  to the record.
- **FAIL**: final score 446-456. The basin-escape lift from
  LearnedOnTies-174 is smaller than vol-22's lift from cold-start.
  ML seeds a worse basin family.

Honest cost: ~1 day to wire the pipeline + 4 hr overnight compute.

## What this vol explicitly does NOT do

- ❌ Hyperparameter sweep (cheap BACKLOG item; ~5 min compute).
- ❌ RL self-play (different paradigm; defer to vol-33+).
- ❌ More model training. Vol-30 already showed model size / data
  don't push the depth lift past +9; basin-escape is the right lever.

## Vol-close protocol

Standard:
1. Update T1 status in BACKLOG.
2. Amend [[../concepts/learned-value-order]] with basin-escape result.
3. If T1 PASS (≥ 458): update score-history; this is the first ML
   contribution to a record. Memory entry mandatory.
4. If T1 MATCH (= 457): the LearnedOnTies path is a cheaper way to
   reach our existing record. Useful methodology note; no record bump.
5. If T1 FAIL: LearnedOnTies basins don't help vol-22's recipe.
   Closes the ML-via-basin direction; vol-33 candidates become
   hyperparam sweep, long PT, or RL self-play.

## Linked concepts

- [[../concepts/learned-value-order]] — vol-26..31 history.
- [[../concepts/basin-escape-recipe]] — vol-22 pipeline.
- [[../basins/basin-457-pt]] — current record basin.

## Linked sessions

- [[../sessions/vol-31]] — the +10/+8 score-axis result.
- [[../sessions/vol-22]] — basin-escape recipe origin.
