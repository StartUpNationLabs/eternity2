---
name: vol34-dup-piece-bug-cleanup-incomplete
description: "Vol-35 supposedly cleaned the vol-34 duplicate-piece bug, but ~189 invalid DB records remained. The DB's '459 strict' record had pieces 180+248 duplicated. True strict-canonical record is 458, not 459."
status: built
metadata:
  type: postmortem
---

# Vol-34 duplicate-piece bug: cleanup was incomplete

## Discovery (2026-05-21, user observation)

While inspecting V199's "458 strict in new basin cp=(0,3,2,1)" via Bucas,
user noticed pieces with id 181 and 249 displayed in two positions
(piece IDs 180 and 248 internally; bucas uses 1-indexed display).

## Audit results

Ran `scripts/db_audit/find_invalid_db_boards.py` over all 1278 DB records:
- VALID: 1089 (85%)
- INVALID: 189 (15%)
- All INVALID share the same fingerprint: pieces 180 and 248 duplicated,
  pieces 197 and 230 missing.

Notable invalid high-score records:

| File | Claimed score | Status |
|---|---|---|
| `459_basic_sa_t1_s7_904478000_p13705` | 459 strict | **INVALID** (was our standing strict record) |
| `457_REAL_RECORD_TIE_457_vol34_t1signal_seed1` | 457 strict | INVALID |
| `457_RECORD_TIE_457_vol34_t3_t01_seed1` | 457 strict | INVALID |
| `457_winning5_sa_t1_s1_d12e28e2` | 457 strict | INVALID |

## Implications

1. **The "standing 459 strict-canonical record" was bogus.** It had 180+248
   duplicated. The TRUE strict-canonical record is **458**
   (`458_basic_sa_t1_s42_357042000_p7627_60658d38`, vol-122 finding,
   verified 256 unique pieces).

2. **V199 "459 reproductions" inherit the bug**: 5 jobs produced
   boards byte-identical to the bogus DB 459 — all 5 invalid.

3. **V199 "new 458 strict in cp=(0,3,2,1)" was based on
   invalid 457 base** — that result is also invalid.

## What IS valid from V199

- The 458 strict at cp=(0,2,1,3) (output/vol-199/RECORD_458_STRICT_NEW_BASIN_cp0213.json) — 256 unique pieces, 5/5 hints, independent rescore 458/480.

This is a genuinely new 458-strict basin, distinct from vol-122's DB 458.

## Cleanup applied

189 invalid records renamed `*.INVALID_DUPS.json.QUARANTINED` so they
no longer match `*.json` globs in sweeps. Standard `database-400-480/*.json`
now picks up only the 1089 valid records.

## Lesson

The vol-35 cleanup memo said "vol-34 records retracted; bug fixed in 3 save paths" — implying full cleanup. In fact ~189 boards predating the fix were saved with the bug still active and remained in DB. The vol-122 strict-canonical 458 finding still stands as the true peak; the 459 record was a phantom.

## Linked

- vol-35 (original cleanup)
- vol-122 (legitimate 458 strict)
- v199 (this vol's pipeline, partially-contaminated by invalid bases)
