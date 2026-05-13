# Engine perf — hot paths and remaining wins

**Status**: `partial` — 7 fixes shipped vol-25 (2026-05-13), 4 more identified.
**Origin**: vol-25 perf push (2026-05-13), user-requested code-quality review that pivoted to perf via samply flamegraph.
**Files**: `crates/solver-engine/src/lib.rs` — specifically `place_and_propagate_opts` (lines ~2860–3050) and `propagate_ac3` (lines ~3060–3320).

## Definition

The per-node hot path of the CSP engine. Joe-class profiles (gacolor + AC-3 + multiset_equality + depth-gate, the canonical 5-clue baseline) spend ~96% of CPU inside `propagate_ac3`. Light-prop profiles (BLACKWOOD_RAW: edge-color + piece-uniqueness only) spend ~70% in the piece-uniqueness bitset loop.

## What we measured (vol-25, single-thread, 60s budget, canonical E2 seed 1)

### Baseline (pre-fix)

| Profile | nps | Time distribution |
|---|---|---|
| BLACKWOOD_RAW | 347 k | 25.83% on `dom[w] & pmask[w]` (line 2940); 7.57% on redundant `domain_is_empty(p)` scan (line 2950); 4.97% on `arena.resize(+wpp, 0)` bzero (line 2929) |
| joe_depth150_bp | 6 864 | 95.86% on `lib.rs:2972` (the `match propagate_ac3(...)` call site — atos symbolicates AC-3 inline body to this single line) |

### After 7 fixes shipped vol-25

| Profile | nps | Δ vs baseline |
|---|---|---|
| BLACKWOOD_RAW | ~440 k | **+27%** |
| joe_depth150_bp | ~8 400 | **+22.4%** |

## The 7 fixes shipped (commits, vol-25 2026-05-13)

| # | Commit | Pattern | Joe Δ | BR Δ |
|---|---|---|---|---|
| 1 | `cded9a0` | Fold `domain_is_empty` into bitset loop via `survived |= new`; eliminate `resize(+wpp, 0)` zero-fill via stack scratch `[u64; 32]` + `extend_from_slice` (piece-uniqueness loop) | +1.5% | +27.5% |
| 2 | `108cdc9` | AC-3 timeout check rate 1/64 → 1/4096 (macOS `Instant::elapsed_us` was 12.4% of joe runtime); same scratch trick for AC-3 arena | +0.6% | – |
| 3 | `114ab59` | Same fix pattern applied to edge-color `prune` closure (third application) | +1.9% | +2.4% |
| 4 | `fd5b615` | Dirty-list scoping for the AC-3 count rebuild — only re-walks positions whose domain mutated since last AC-3 entry | +3.2% | – |
| 5 | `6727fed` | Hoist read-only slice binds (`placed`, `rows`, `same_piece_rots`) out of the AC-3 inner support-check loop | +3.7% | – |
| 6 | `90343ec` | Fuse AC-3 row-list build with support-check loop — replace `ac3_to_check: Vec<u32>` materialization with stack u64 snapshot of `domain_bits[a]` walked via `trailing_zeros` | +7.0% | – |
| 7 | `6db374c` | Popcount-based AC-3 count rebuild — `count[p][s][c] = popcount(domain[p] & side_color_mask[s,c])`, replacing per-set-bit increment loop | +4.3% | – |

Followed by cleanup commit `b392e1f` removing the now-dead `ac3_to_check` field.

All 27 solver-engine tests pass at every step.

## What was refuted / didn't help

- **`#[inline]` on `count_heuristic_in_row`** — static-audit agent predicted 1–3%; flamegraph showed not in top-200 samples. Compiler already inlines under LTO.
- **`domain_snapshot` reuse via SearchState scratch field** — predicted 3–5%; `recurse` doesn't appear in self-time at all in the propagator-heavy profile.
- **Value-order dispatch lifting** — predicted 2–5%; not visible in flamegraph.
- **SearchState field reordering for cache** — predicted <1%; correctly skipped.
- **Manual unroll of the 4-side count decrement** (commit reverted) — neutral / -0.6% noise. Compiler already unrolls.

## What's left on the table — backlog

### Fix 8 — full incremental AC-3 count maintenance

**EV**: ~10–15% on joe.
**Effort**: 1–2h with real bug risk.

The fix-4 dirty-list approach captures only ~3% of the headline 22% rebuild cost because piece-uniqueness drops mark nearly every unplaced cell dirty. The fully incremental version decrements `count` at every drop site (piece-uniqueness, prune closure, AC-3 inner) and increments at every restore site, eliminating the rebuild entirely.

Mutation sites that need instrumentation:
- `place_and_propagate_opts` piece-uniqueness loop drop (iterate scratch set-bits, dec 4 count cells per row)
- `prune` closure edge-color drop (same)
- `restore()` (iterate OR-back set-bits, inc 4 count cells per row)
- `pin_to()` (less hot, runs at search init; could mark dirty as fallback)
- `recurse` Blackwood break-index domain-zero (2 sites)

Risk: a missed mutation site → stale count → wrong support checks → wrong pruning. The 27 unit tests catch this if propagator-comparison tests exercise the path; verify before shipping. The infrastructure (`ac3_dirty_list`, `ac3_dirty_flag`, `mark_ac3_dirty` helper) is already in place from fix 4 — leave it as a safety net for any path we miss.

### Fix 9 — SIMD via `chunks_exact(2)` over u64x2 on restore's OR-back loop

**EV**: 2–4%.
**Effort**: 30 min.

`restore` (lib.rs:3408–3422) ORs `wpp = 16` u64s back into a domain. `chunks_exact(2)` over u64 pairs might trigger autovectorization to NEON (apple-m1 has dedicated u64x2 ALUs).

### Fix 10 — Profile harness fix: use NullSink, not BufferSink

**EV**: profile-only; doesn't affect production. `drop_in_place<BufferSink>` was 2.98% of pre-fix BLACKWOOD_RAW samples — the bench-fast profile bins (`profile_blackwood_raw.rs`, `profile_joe.rs`) collect every event for 60s into a Vec that gets dropped at exit. Swap to `eternity2_events::NullSink` for cleaner attribution.

**Effort**: 5 min, but only useful for future profiling work.

### Fix 11 — AC-3 inner support-check loop: precompute `nb_info` per cell

**EV**: 1–2% (speculative).
**Effort**: 1 h.

The `nb_info: [(Option<Position>, usize, usize); 4]` is reconstructed at every queue-pop inside `propagate_ac3` (lib.rs:3205–3210). Position-only deps; could be precomputed at SearchState::new into `cell_nb_info: Vec<[(Option<Position>, usize, usize); 4]>` and just sliced per pop.

The reconstruction itself isn't a hotspot (the profile shows time INSIDE the inner loop reading nb_info, not constructing it), so this might not move the needle. Worth trying if other levers are exhausted.

## How to profile

`samply` is the right tool on macOS (apple-m1 doesn't support `perf`). Key recipe:

```bash
# Build with debuginfo
cargo build --profile bench-fast -p eternity2-bench-audit \
    --bin profile_joe --bin profile_blackwood_raw

# Capture (60 s each, sequential to avoid CPU contention)
E2_PROFILE_MS=60000 samply record --save-only \
    -o /tmp/joe.json.gz ./target/bench-fast/profile_joe

# Resolve with inline frames — critical because propagate_ac3 inlines
# into place_and_propagate_opts and atos must unwind inline chains
atos -i -o ./target/bench-fast/profile_joe -arch arm64 -l 0x100000000 \
    < addresses_offset_by_0x100000000.txt
```

Then aggregate by `(function, lib.rs:N)` for line-level attribution.

The samply JSON format (gzipped Firefox Profiler) is parseable: top-level → `threads[0]` → `samples.stack` indexes into `stackTable.frame` → `frameTable.address`. Inline info is in `frameTable.inlineDepth` but on macOS samply leaves it at 0 — use `atos -i` post-hoc.

**Trap**: samply addresses are TEXT offsets. Apple TEXT loads at `0x100000000`. Add this offset before calling atos with `-l 0x100000000`.

## Why the joe profile is "AC-3-bound"

joe runs gacolor + AC-3 + multiset_equality + depth_threshold=150. The depth gate fires for most early nodes (search is mostly below depth 150), so gacolor/multiset are gated off. AC-3 runs on every placement. The per-call cost of AC-3 is the count-rebuild + support-check fixpoint loop, both dominated by domain-bitset iteration. There's no algorithmic simplification available — the work IS the work; we just need to do it faster.

## Linked concepts

- [[ac3]] — the algorithm
- [[bitset-domain-rep]] — domain bits as packed u64
- [[code-debt]] — the broader restructure proposal that triggered this work
- [[engine-profile-registry]] — the profiles whose nps we measured (BLACKWOOD_RAW, joe_depth150_bp)

## Linked memory

- [[../../../../.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/project_e2_vol15_blackwood_results|BLACKWOOD_RAW throughput finding]] — vol-15 measured 367k nps; we're now at ~440k single-thread (+20%).
- [[../../../../.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/project_e2_vol16_closeout|Vol-16 closeout]] — prior perf vol that hit `place_and_propagate` (vol-16 Cat-4* commits). These vol-25 fixes extend that work into AC-3.
