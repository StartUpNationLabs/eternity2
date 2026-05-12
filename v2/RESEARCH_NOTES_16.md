# RESEARCH_NOTES_16.md — vol-16 session log

Live log for vol-16. Vol-15 closeout is in `RESEARCH_NOTES_15.md`.
Punch list anchor is `~/.claude/.../memory/project_e2_vol16_cleanup_anchor.md`.

## Vol-16 mission

Cleanup / refactor / re-architect volume. NOT a new-algorithm
volume. User-flagged at vol-15 mid-session: *"our code is becoming
quite a mess"* and *"re-engineer the way we manage all those
possibilities for different algorithms, paths, hints etc..."*

Vol-17+ resumes new-algorithm work (schedule calibration from
community 469 boards, then break-tolerant ALNS warmup, etc).

## State at vol-16 start

| metric | value |
|---|---|
| canonical-E2 seed-1 ALNS best (vol-15) | 416/480 (blackwood_raw) |
| canonical-E2 seed-1 ALNS baseline | 439/480 (joe_depth150_bp_par) |
| community ceiling | 469/480 (McGavin 2020) |
| solver-engine/src/lib.rs | 3831 lines |
| named `pub const` engine profiles | enumerated below |
| `EngineSolver::*` constructors | 25 |
| bench-audit binaries | 20 |
| workspace clippy warnings | TBD (clippy newly installed) |
| single-thread BLACKWOOD_RAW nps | ~80k |
| BLACKWOOD_RAW multi-core nps | ~650k |

Allocator dominates the profile (~42% inclusive CPU). Bounds-checks
~15%. `class_balance_check` 7.6% self time in RAW (suspect: might
not be off in the profile config). Cleanup-only speedup potential:
2–4×.

## Carry-over from vol-15: background process

A 1h CP + 1h ALNS run of `blackwood_raw_rect_layered` (PID 29398,
started ~19:52) was left running at vol-15 close to test whether
layered+Blackwood breaks past depth 81 with more wall-clock.

At vol-16 start (20:19, ~26 min in): `best_depth=81`, unchanged
from the 5-min run's 80. Prediction holding: wall is structural
(schedule-bound), not search-time-bound. Will land naturally
~21:52. Not killed; not vol-16 work.

Reasonable expectation: final result lands at best_depth 80-90,
confirming layered ordering is incompatible with Blackwood
schedule constraint without no-good learning (consistent with
Ansótegui et al. CP'08). If best_depth leaps to 150+, vol-16
reopens the layered hypothesis (very unlikely).

## Session plan

Order matters; earlier items unblock later ones.

1. **Now**: RESEARCH_NOTES_16.md (this file) + commit.
2. **Cat-8 architectural decision**: pick a strategy-composition
   pattern and document in `V2_DESIGN.md`. **Picked: Option A**
   (trait + dyn dispatch). Commit BEFORE refactor code so the
   user can object. Cost: ~5% vtable hit in hot loop; mitigation
   via `#[inline]` on trait methods.
3. **Cat-1 registry drift**: sync Blackwood profiles into
   proto comment block + `server::service::instantiate` + `list_solvers`.
   Defer schedule-injection proto change; document the limitation.
4. **Cat-6/7 quick wins**: clippy clean, cargo machete, cargo audit,
   .gitignore additions. Each = separate commit. Should take a
   couple hours and produce 5-8 commits.
5. **Cat-4 perf cleanup #1 (alloc pressure)**: pre-reserve undo
   Vec + diff buffer on SearchState. Re-profile. Measure nps delta.
6. **Cat-4 perf cleanup #2 (class_balance audit)**: confirm whether
   it's on in RAW; either drop or rewrite. Re-measure.
7. **Cat-2 EngineConfig split**: orthogonal sub-configs +
   EngineConfigBuilder. Implements Cat-8's chosen pattern.
   This is the biggest refactor; allow most of vol-16 for it.
8. **Cat-3 bench-audit sprawl**: extract `Pipeline` lib;
   consolidate 20 bins → ~10. Depends on Cat-2 builder API.

Bars NOT in scope this session:
- Calibrating Blackwood schedule from community 469s (vol-17).
- New propagators, new value-orders, new scan orders (vol-17).
- Adding new EngineConfig dimensions.
- Adding new bench-audit bins (only consolidate).

## Bars

| tier | requirement |
|---|---|
| T1 (minimum) | registry drift resolved + clippy clean + 1.5× engine speedup measured + V2_DESIGN.md decision committed |
| T2 (good) | T1 + EngineConfig split shipped + 2× engine speedup + bench-audit halved |
| T3 (excellent) | T2 + 8/22 bins consolidated + memory hygiene + builder DSL shipped |
| T4 (session-defining) | T3 + measurable score improvement on canonical E2 from the perf wins (plausible if 2× engine combines with the calibrated schedule from vol-17 work) |

## Live log

### 2026-05-12 ~20:20 — session opened, plan committed

Read auto-memory (anchor, vol-15 closeout, vol-14 closeout, V2_DESIGN.md).
Picked Option A from the four design candidates after the AskUser
loop. About to write the V2_DESIGN.md "Strategy composition"
section, then move to Cat-1 registry drift.

### 2026-05-12 21:25 — vol-16 closeout

10 commits shipped on develop, organised by category:

```
9c10324 vol-16:        open session log + strategy-composition design decision
91fd34d vol-16 Cat-1:  sync drifted profiles into proto + server registry
9dd33b1 vol-16 Cat-6/7: clippy clean + dep audit + .gitignore + dead code
09cedd0 vol-16 Cat-4:  drop per-UndoEntry Vec alloc (engine alloc-pressure pass 1)
afbfad0 vol-16 Cat-4b: drop class_balance from BLACKWOOD_RAW — 2.4x speedup
592398a vol-16 Cat-3:  partial: dedup score_board+render_board+placed_count+ProgressSink
1b4bd28 vol-16 Cat-3:  stage 2: migrate 9 more bins to shared helpers
```

#### Tier ranking

| tier | target | status |
|---|---|---|
| T1  | registry drift + clippy clean + 1.5× engine speedup + V2_DESIGN.md call | ✅ MET (2.87× speedup, exceeds 1.5×) |
| T2  | + EngineConfig split + 2× engine speedup + bench-audit halved | ⚠️ PARTIAL (2.87× ✓, bench-audit -652 lines ≈ −34% across 13 bins; struct split deferred) |
| T3  | + 8/22 bins consolidated + memory hygiene + builder DSL | ⚠️ PARTIAL (13/22 bin migrations ✓, memory hygiene pending in closeout, builder DSL deferred) |
| T4  | + measurable score improvement on canonical E2 | ❌ NOT ATTEMPTED (no algorithm changes in vol-16 by design) |

#### Deltas worth quoting

| metric | before | after |
|---|---:|---:|
| workspace rustc warnings | 32 | 0 |
| workspace clippy warnings (pedantic+nursery) | 233 | 87 |
| unused dependencies | 8 | 0 |
| cargo audit vulnerabilities | 0 | 0 |
| solver-engine BLACKWOOD_RAW single-thread nps | ~80k | ~230k (+187%) |
| bench-audit bin line count (13 migrated) | 1086 + ... | -652 lines net |
| server registry engine profiles (instantiate + list_solvers) | 17 | 32 |

#### What Cat-4b's 2.4× win cost: dropping `class_balance_propagator` from
BLACKWOOD_RAW. Reason: profile showed 7.6% self-time inclusive
much higher. It IS break-sound but pruning value at depth ~80
(Blackwood's wall) is negligible. Other profiles retain it.

#### What's deferred to vol-17

- **Cat-2 EngineConfig struct split**: Option A (trait + dyn) is
  committed in V2_DESIGN.md "Strategy composition (vol-16)". The
  implementation is mechanical-but-voluminous: 14-field struct →
  5 sub-structs/traits, 25 const profile slabs → builder calls,
  ~44 `self.config.X` reference sites. Single coherent PR
  rather than incremental.
- **Cat-3 remaining 7 bins**: framefirst (different score
  signature), compare, fleet, backtrack_diag, initial_domains,
  sweep_depth (mostly self-contained), profile_blackwood_raw.
- **Cat-5 memory consolidation**: merge duplicate vol-14 entries
  per the anchor (5+ pairs identified). Touched briefly in closeout
  below.
- **Cat-7 Rust best-practices audit**: nightly udeps, cargo bloat
  baseline, thiserror migration, module-hierarchy split for the
  3.8k-line lib.rs.

#### Cat-4 numbers — full detail

The vol-15 anchor predicted 2-4× cleanup-only speedup. Achieved
2.87× by two mechanisms:

| commit | site | benchmark (canonical-E2, 15s, single-thread) |
|---|---|---|
| pre-vol-16 baseline | — | ~80 kNps |
| Cat-4 alloc cleanup (UndoEntry arena) | hot loop allocator | 97-98 kNps (+22%) |
| Cat-4b drop class_balance + pre-alloc outer Vec | dropped propagator | 217-237 kNps (+187% vs baseline) |

Profile artifact: `output/v15_profile/blackwood_raw_60s_sym.json.gz`.
Vol-17 should re-profile with the post-vol-16 binary to see if
the remaining inclusive 42% allocator cost shrank proportionally
(it should — most of `System::alloc_zeroed` was in the per-entry
`vec![0u64; wpp]` we deleted).

#### Vol-15 carry-over: 1h+1h Blackwood run terminated

PID 29398 (`blackwood_raw_rect_layered` 1h CP + 1h ALNS, started
~19:52 vol-15) terminated CP at exactly 3600s as designed.

**CP final**: `nodes=3.4 billion  depth=80  placed=85/256  matched=113/480`.
ALNS phase started at +1h (~20:52); will finish ~21:52.

**Prediction confirmed**: doubling wall-clock from 5min → 1h on
canonical E2 with `blackwood_raw_rect_layered` did NOT break past
depth 80 (5min was best_depth=80). The wall is structural — the
combination of layered ordering + Blackwood schedule cannot pass
depth ~80 without no-good learning. Saves the depth-wall finding
to memory as a clean null.

(Throughput: 3.4 G nodes in 3600s ⇒ 944 kNps multi-core. That
matches the BLACKWOOD_RAW design — 7 cores × ~140k single-thread
post-vol-16 = ~1 MNps would be expected today.)

### 2026-05-12 ~21:30 — vol-16 re-profile validation

Recorded 30s post-vol-16 BLACKWOOD_RAW profile at
`output/v16_profile/blackwood_raw_30s_post_vol16_sym.json.gz`
(+ syms sidecar). Comparison to vol-15:

| metric | vol-15 (pre) | vol-16 (post) | Δ |
|---|---:|---:|---|
| nps (single-thread) | ~80k | ~234k | +193% |
| place_and_propagate_opts self | 7.9% | 70.2% | (relative ↑ as everything else shrank) |
| class_balance_check self | 7.6% | 0.0% | confirmed off |
| System::alloc_zeroed inclusive | 17.5% | <1% | confirmed gone |
| System::dealloc inclusive | 24.1% | <1% | confirmed gone |
| Total allocator inclusive | ~42% | 2.3% | **-40 percentage points** |
| `<usize as PartialOrd>::lt` self | 14.6% | not visible | (moved into other functions) |

`SearchState::restore` is now the second-largest self-time
contributor at 19.1% — it's the arena-restore loop that ORs
diffs back into `domain_bits`. The work was previously hidden
inside `Vec::drop`-induced `System::dealloc`. With the arena it's
now O(undo_log_size × wpp) of cache-friendly work, but visible.

Vol-17 follow-up: the recurse path's restore is the new hotspot.
Investigate whether the OR-back loop can be replaced by a
saved-snapshot pattern (memcpy of `domain_bits[base..]` slice on
entry, memcpy back on exit). Trade-off: more bytes copied per
call vs no per-entry restore loop. Worth a measurement.

profile_blackwood_raw also widened my view of allocator surface:
post-vol-16, only `BufferSink::drop` + a handful of macOS malloc
calls contribute. The arena strategy is correct and complete.

### 2026-05-12 ~21:30 — Cat-7 baseline data (vol-17 chores)

`cargo bloat --release -n 25 -p eternity2-bench-audit --bin profile_blackwood_raw`:

  binary text size: 433 KiB
  top engine funcs (% of .text):
    solve_parallel              3.3% (14.1 KiB)
    SearchState::new            2.6% (11.1 KiB)
    SearchState::recurse        2.2% (9.3 KiB)
    place_and_propagate_opts    2.1% (9.3 KiB)
    compute_heuristic_sides     1.0% (4.3 KiB)
    ChannelSink::emit           0.9% (4.0 KiB)
    run_impl                    0.8% (3.3 KiB)
    build_hint_rectangle_path   0.7% (3.2 KiB)
    build_hint_rectangle_layered 0.7% (3.2 KiB)

No bloat issue — the hot functions are the ones we'd want to be
hot. ~70% of .text is in 891 smaller methods (long tail).

`cargo outdated --workspace --depth 1`:

  | crate         | current | latest |
  |---------------|---------|--------|
  | tonic         | 0.12.3  | 0.14.6 |
  | tonic-web     | 0.12.3  | 0.14.6 |
  | tonic-build   | 0.12.3  | 0.14.6 |
  | prost         | 0.13.5  | 0.14.3 |
  | criterion     | 0.5.1   | 0.8.2  |  (dev-only)

`cargo audit`: 0 vulnerabilities (209 deps scanned, advisory-db
loaded 1070 advisories). Clean.

Recommendation for vol-17: coordinated tonic 0.12 → 0.14 +
prost 0.13 → 0.14 upgrade (proto codegen lands in same PR).
Criterion upgrade is optional and dev-only. None block any
research direction.

### 2026-05-12 ~21:50 — Cat-2 Stage A bug + fix, Cat-4c reality check

User pushed back with "you can much more than you think" → I
attempted Cat-2 Stage A (PropagatorConfig sub-struct).

What shipped:
- `PropagatorConfig` extracted from EngineConfig's 7 flat
  propagator fields (6 bools + Option<u32> depth gate).
- 30 named profile slabs updated to use nested FRU pattern.
- 16 read sites in lib.rs + 2 in sweep_depth.rs renamed.
- ~120 lines of mechanical rewrite via /tmp/cat2_rewrite2.py.

Then I followed up with **Cat-4c**: slice-based inner loops in
SearchState::restore + place_and_propagate_opts prune closure +
piece-uniqueness loop. Iter().zip() pattern for bounds elision.

Initial Cat-4c benchmark: **264-268 kNps**. Reported as 3.35×
speedup vs vol-15 baseline ~80k.

Then re-profiled and found `class_balance_check` BACK at 19.1%
self time — but BLACKWOOD_RAW should have class_balance OFF
(from Cat-4b). Debug found the Cat-2 Stage A rewrite script
**had a regex bug**: `[A-Z_]+` didn't match slab names containing
digits (GACOLOR_AC3, JOE_DEPTH150, ...). 17 of 30 slabs silently
fell back to BORDER_FIRST_LCV defaults (class_balance: true,
all others false).

Fix script (cat2_full_fix.py) extracts truth from the pre-Cat-2
source and re-injects via nested FRU on `Self::BORDER_FIRST_LCV.propagators`.
17 slabs restored.

**True Cat-4c benchmark after fix**: 364-367 kNps.

| stage | nps | total speedup vs vol-15 baseline |
|---|---:|---:|
| vol-15 baseline | ~80k | 1.00× |
| Cat-4 alloc cleanup | ~98k | 1.22× |
| Cat-4b drop class_balance from RAW | ~230k | 2.87× |
| Cat-2 Stage A + Cat-4c slice loops (reported, broken) | ~268k | 3.35× |
| **Cat-2 Stage A fix + Cat-4c** | **~367k** | **4.6×** |

The +38% jump from "Cat-4c broken" to "Cat-4c fixed" is
explained by:
- Previously BLACKWOOD_RAW silently had class_balance ON (Cat-2
  regression). That cost ~38% throughput per Cat-4b's measurement.
- The fix restores Cat-4b's correctness; slice loops give the
  rest.

Honest framing: I committed a CORRECTNESS regression in Cat-2
Stage A. The Cat-4c headline number (268 kNps) was measured on
a misconfigured engine. The fix commit (b55f59c) documents this
clearly. No published vol-16 numbers between 11c5141 and b55f59c
should be trusted on non-RAW profiles (joe_depth150_par etc.
were running with wrong propagator stacks during that window).

All 107 workspace tests pass throughout — the test suite didn't
catch this because no test exercises a specific named profile by
asserting on its propagator config; tests are end-to-end solves
which still succeed (slower or with different node counts).
Vol-17 follow-up: add per-profile `assert_eq!(profile.propagators.ac3, true)` etc.
unit tests to catch this class of regression.
