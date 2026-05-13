# Session — vol-25 (2026-05-13)

**Theme**: Pre-binding code-quality + engine perf push (user-requested, before formal vol-25 binding pick).
**Time**: ~16:00 → 17:10 CEST (~1h focused work after vol-24 close).

## Context

Vol-24 closed earlier the same day with `score-optimizing-cp` shipped (route b: branch-and-bound MaxScore CP). Vol-25 has a draft binding (tighter MaxScore upper bound) but the audit-at-open hadn't been formally executed yet.

User asked: "study the code quality, god classes, refactoring needed because of duplicate utilities (like stats, exports, bucas url, csv etc...) and furthermore bad potential organization of code for modularity which is excessively important here."

That triggered a code-quality audit. The audit surfaced both **structural debt** (god files, duplicate utilities, bin proliferation) and **perf debt** (the existing solver-engine hot path had untapped wins). The user then pivoted to perf: "Now you are in editing mode, you can do 1 and 2 right now."

The session became a **flamegraph-driven perf push**, with the structure findings deferred to BACKLOG.

## What got built (perf — 7 commits)

Single file touched: `crates/solver-engine/src/lib.rs`. All discovery via `samply record` + `atos -i` inline-frame attribution on bench-fast bins (`profile_joe`, `profile_blackwood_raw`).

| Commit | Pattern | Joe Δ | BR Δ |
|---|---|---|---|
| `cded9a0` | Fold `domain_is_empty` into bitset loop via `survived` OR-accumulator; eliminate `arena.resize(+wpp, 0)` zero-fill via stack scratch `[u64; 32]` + `extend_from_slice` (piece-uniqueness loop) | +1.5% | +27.5% |
| `108cdc9` | AC-3 timeout check 1/64 → 1/4096 (macOS `Instant::elapsed_us` was **12.4%** of joe runtime); same scratch trick for AC-3 arena | +0.6% | – |
| `114ab59` | Same fix pattern applied to edge-color `prune` closure (third application of same trick) | +1.9% | +2.4% |
| `fd5b615` | Dirty-list scoping for the AC-3 count rebuild | +3.2% | – |
| `6727fed` | Hoist read-only slice binds (`placed`, `rows`, `same_piece_rots`) out of AC-3 inner support-check loop | +3.7% | – |
| `90343ec` | Fuse AC-3 row-list build with support-check loop — replace `ac3_to_check: Vec<u32>` materialization with stack u64 snapshot walked via `trailing_zeros` | +7.0% | – |
| `6db374c` | Popcount-based AC-3 count rebuild: `count[p][s][c] = popcount(domain[p] & side_color_mask[s,c])` | +4.3% | – |
| `b392e1f` | Cleanup: removed dead `ac3_to_check` field | – | – |

**Cumulative** (single-thread, 60 s, canonical E2 seed 1, bench-fast profile):
- BLACKWOOD_RAW: **347 k → ~440 k nps (+27%)**
- joe_depth150_bp: **6 864 → ~8 400 nps (+22.4%)**

All 27 solver-engine tests pass at every step.

## How the wins were found

The first samply capture told us the hot path was tightly localized: **all of joe's top-200 self-time samples landed in 8 KB of code** (0x23000–0x25000 in TEXT), and atos initially symbolicated everything to `place_and_propagate_opts (lib.rs:2972)` — the call site of `propagate_ac3`.

The breakthrough was using **`atos -i`** to walk inline-frame chains. The compiler had inlined `propagate_ac3` into `place_and_propagate_opts`, so naive symbolication lost the line-level attribution. With `-i`, we got real per-line cost distribution inside the 240-line AC-3 function. From there each fix was direct: find the hot line, understand what's wasted, rewrite the local block.

**A specific instructive surprise**: the static-audit agent (no profiling) predicted `#[inline]` on `count_heuristic_in_row`, `domain_snapshot` reuse, and value-order dispatch lifting as the biggest wins (~5–10% combined). The flamegraph showed all three at <1%. Meanwhile the static audit completely missed:
- `Instant::elapsed_us` at 12.4% (because it's inside a "rare" 1/64 gate that turns out to dominate due to mach_absolute_time cost),
- The 25.8% on a single line (the piece-uniqueness drop computation),
- 7.57% on `domain_is_empty` (a "trivial" 16-word scan).

**Lesson**: static reading of Rust hot code is unreliable for perf prediction. The compiler reshapes everything; flamegraph attribution is the only honest signal.

## Audit-at-open NOT executed

Vol-25 has a CURRENT-VOL.md drafted at vol-24 close with binding T1 = "tighter MaxScore upper bound." This perf push is **opportunistic, not the vol-25 binding**. At the next formal session start, the audit-at-open protocol still needs to fire on items aged ≥ 3 vols (`piece-orbit-as-atom`, `multi-cell-bound-ascent`, etc.).

The code-debt findings are stored in `concepts/code-debt.md` and queued in BACKLOG so they don't get lost.

## Concepts touched

- [[code-debt]] — NEW. Full restructure proposal (5 duplicated utilities → 3 new crates; solver-engine 5-module split; bin harness consolidation).
- [[engine-perf-hot-paths]] — NEW. Per-line attribution of pre-fix joe + BLACKWOOD_RAW flamegraphs; the 7 fixes; the 4–5 fixes still in the backlog.
- [[ac3]] — implementation now reflects the popcount-rebuild + slice-binding + fused-iteration pattern.

## New BACKLOG entries

Two new sections in `plans/BACKLOG.md`:
- **Code quality / refactoring** (5 items): `extract-eternity2-time-crate`, `extract-eternity2-export-crate`, `split-solver-engine-lib-into-5-modules`, `extract-eternity2-puzzle-io-crate`, `consolidate-bin-harness`.
- **Engine perf — remaining wins** (5 items): `incremental-ac3-count-maintenance`, `restore-or-simd`, `profile-bin-use-null-sink`, `precompute-cell-nb-info`, `vault-validation-of-perf-wins`.

Total: 10 new items, all with concrete effort + EV estimates from the audit.

## Process notes

- **Tooling investment that paid off**: getting `samply record` + `atos -i` + a Python aggregation script working took ~15 minutes. After that every fix took 5–20 minutes of code + 60 s of measurement. The investment is durable — same recipe applies to any future hot-path question on this codebase.
- **The "ac3-bound" framing for joe is now confirmed**: ~96% of joe's CPU is inside `propagate_ac3` (97% pre-fix, 87% post-fix as other paths got more visible). Joe wins beyond vol-25 must come from AC-3 internals.
- **The compiler's inlining is aggressive enough that line-level attribution requires `-i`**. Future profiling work should default to this.
- **One reverted experiment**: explicit 4-side unroll of the count-decrement at line 3287 (originally part of fix-7) — neutral / -0.6% noise. The compiler was already unrolling. Worth recording: not every micro-opt helps; trust the profile.

## What we owe to vol-25-proper (the formal binding work)

The CURRENT-VOL.md binding (MaxScore tighter upper bound) is untouched and still queued. This perf session was a sidequest. Next session should run the audit-at-open per CLAUDE.md discipline and pick the actual vol-25 binding.

The perf gains *should* compound with any future algorithmic work — every solver call is now faster — but per [[../../../../.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/project_e2_vol14_bp_null|Vol-14 BP-as-value-order REVERSAL]] we know raw-nps wins don't always translate to score wins. The `vault-validation-of-perf-wins` BACKLOG item captures the open question.

## Open at close

- **Code debt audit committed but not acted on.** Five extractions queued; none shipped.
- **AC-3 count rebuild still ~18% of joe runtime** even after popcount + dirty-list. Full incremental maintenance (BACKLOG: `incremental-ac3-count-maintenance`) is the next biggest lever.
- **Vol-25 formal binding (`tighter-maxscore-upper-bound`) not started**. The audit-at-open per CLAUDE.md should run at next session.

## Linked memory

- [[../../../../.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/project_e2_vol15_blackwood_results|BLACKWOOD_RAW throughput finding]] — vol-15 measured 367 k nps single-thread; we're now at ~440 k.
- [[../../../../.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/project_e2_vol16_closeout|Vol-16 closeout]] — prior perf vol that hit `place_and_propagate`. These vol-25 fixes extend that work into AC-3.
- [[../../../../.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/project_e2_vol14_bp_null|Vol-14 BP-as-value-order REVERSAL]] — the warning that CP-partial nps wins don't always translate to score wins; motivates the `vault-validation-of-perf-wins` BACKLOG item.
