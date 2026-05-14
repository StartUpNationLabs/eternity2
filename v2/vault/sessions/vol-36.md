# Vol-36 — vanilla_path + canonical-respecting CP

**Theme**: User-proposed: raw-DFS with custom paths (vs vanilla_fast's
hardcoded row-major). A/B tested 7 path modes; best is **border-first**
at +12 score edges over row-major. All centre-first variants confirm
the vol-14 hint-centric refutation in propagator-free settings.

**Raw**: `vault/sessions/vol-36-vanilla-path-ab.md` (the A/B detail).

## What was attempted

- T1a — `vanilla_path` bin (Rust), 6 path modes + `--path-csv`,
  per-step pre-bucketing on constraint mask, 60-100M pp/s.
- T1b — 30s × 1-thread A/B across 7 path modes.
- T1c — 5min × 8-thread CP × ALNS 5min × 4 seeds on border-first partial.
- T1d — vanilla_fast row-major --pin-hints (canonical-respecting) baseline.
- T2 — McGavin prune-restart with MaxScore on make-canonical vol-32 458 partial
  (in flight at vol close).

## What was measured / kept

| Path mode | Depth (30s/1t) | Score |
|---|---:|---:|
| row-major | 210 | 433 |
| **border-first** | **215** | **445** ← best cold CP |
| outer-spiral | 99 | 204 |
| hint-link | 48 | 51 |
| hint-then-outspiral | 48 | 51 |
| hint-then-borderin | 99 | 162 |
| centre-sandwich | 42 | 57 |
| border-then-hints | 87 | 166 |

- **vanilla_path bin** with per-step pre-bucketing on constraint mask
  works at 60-100M pp/s.
- **Border-first wins cold CP** at +12 edges over row-major (445 vs 433).
- **All centre-first variants fail** at depth ~50 wall.
- **Border-first 5min × 8 thread cp5min.json → ALNS-5min × 4 seeds**:
  scores 442, 451, 452, 457. Seed 2 = 457 verified piece-unique, BUT
  0/5 canonical hints honored. NOT a canonical record.
- **vanilla_fast row-major --pin-hints @60s × 8 threads**: depth 208,
  score 429. Per-thread variance high; 2/8 stuck at depth 34.
- **vanilla_fast row-major --pin-hints @5min × 8 threads**: in flight.

## What was refuted

- **Centre-first paths (4 variants tested)**: depth caps at 42-99,
  scores 51-162, all below row-major's 433. The vol-14 "hint-centric
  scan order NULL" finding is reproduced in raw-DFS (propagator-free)
  settings. Starting at interior cells creates over-constrained
  boundary that grows faster than search depth.
- **Two-phase enumerate-then-fill (B-variant)** is structurally
  infeasible: count of valid centre completions at depth 50 ≈ 5⁴⁵
  ≈ 10³¹, enumeration would take 10¹⁵ years at 100M pp/s.
- **Border-then-hints variant** (canonical-respecting border-first):
  depth 87, score 166. Phase boundary disrupts row-major locality.

## Concepts touched

- [[scan-order]] — path order has dramatic effects even without
  propagators: cold CP score variance 51-445 across 8 path modes.
- (refuted again) hint-centric-null — now confirmed at both engine
  level (vol-14) and raw-DFS level (vol-36).
- [[canonical-hint-compliance]] — new framing: paths that reach deep
  often disagree with canonical hints. vol-32 458 has 3/5 honored;
  border-first 5min+ALNS has 0/5; pin-hints depth caps at ~210.
  Tension between "reach deep" and "respect canonical".

## Open at close

1. **vanilla_fast --pin-hints 5min × 8 threads + ALNS lottery** — in
   flight. If yields ≥459 canonical-respecting, vol-36 successful.
2. **prune_restart from make-canonical vol-32 458 partial with MaxScore** —
   in flight. If CP fills the 4 dropped cells to ≥460, record candidate.
3. The vol-36 T2 (McGavin prune-restart bound-trigger) is now in flight
   via the make-canonical approach (different from vol-23's CP-depth
   trigger). Composition vol-23 prune-restart × vol-24 MaxScore × hints-aware
   has not been tested before.

## Records ledger (post vol-36 work)

| score | source | canonical | verified |
|---:|---|:---:|:---:|
| 458 | vol-32 vanilla_fast → ALNS | 3/5 | ✓ |
| 457 | vol-32 blackwood_mrv seed 7,10,4 | (unknown — assumed ≥3/5) | ✓ |
| 457 | vol-35 deep458 full/diverse seed 5 | 3/5 | ✓ |
| 457 | vol-36 border-first → ALNS seed 2 | 0/5 (NOT canonical) | ✓-piece-unique only |

The new vol-36 457 is interesting but NOT a record-class find because
it violates canonical-hint constraint.

## Linked memory

- Pending: write `project_e2_vol36_vanilla_path.md` capturing the
  border-first lift + centre-first refutation.
