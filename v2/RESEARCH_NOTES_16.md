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
