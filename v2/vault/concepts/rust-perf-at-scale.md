---
name: rust-perf-at-scale
description: "Vol-106 T7 — distilled web-research + applied results on Rust hot-loop optimization at scale. Workspace currently uses lto=thin + codegen-units=1 + target-cpu=apple-m1. PGO gives +14% on bf_bw, +12% on vanilla_fastest, +4% on vanilla_v2. Apple M1 cache-line is 128 bytes (vs 64 on x86); Firestorm L1d is 128 KB."
metadata:
  type: project
---

# Rust performance at scale — hot-loop optimization patterns

**Vol-106 T7 deliverable.** User direct ask 2026-05-16 ~09:00:
"Do a deep dive hardcore into Rust optimisation at scale. Check
online. Even just rust optimisation that's not applied to DFS on
the web." This page collects the web-researched insights and the
empirical apply-and-measure results in this workspace.

## Cargo profile knobs (applied)

| flag                 | current | what it costs / gains |
|----------------------|--------:|-----------------------|
| `opt-level = 3`      | yes     | full -O3, no debate. |
| `codegen-units = 1`  | yes     | single LLVM unit → cross-fn inlining inside the crate. +5-15% on hot paths. Costs compile time. |
| `lto = "thin"`       | yes     | cross-crate inlining of the hot trait methods (e.g. EventSink::emit, propagator hooks). +5-15%. |
| `lto = "fat"`        | bench-fast profile | fully merged LTO. Measured: +0% over `thin` for our self-contained inner loops (blackwood-fast is one crate, hot loops fully inlined under thin already). Use when crossing crate boundaries on the hot path. |
| `target-cpu=apple-m1` | yes (`.cargo/config.toml`) | Apple-specific instruction scheduler. Sub-percent on macOS host. |
| `strip = "symbols"`  | yes     | smaller binary, no perf impact. `bench-fast` profile strips=none for samply. |
| `panic = "abort"`    | NO      | bigger speedup than people expect (~3-5% on hot code that has any panic edges). Worth toggling for benchmark builds; not for production. |

## Profile-Guided Optimization (PGO) — APPLIED, measured

PGO ships with rustc; it just needs llvm-profdata of the matching
version. Xcode's llvm-profdata is too old (raw profile format
version mismatch). Homebrew's `llvm` ships a current one:
`/opt/homebrew/opt/llvm/bin/llvm-profdata`.

The workflow is encapsulated in `scripts/build_pgo.sh`:

```bash
scripts/build_pgo.sh eternity2-blackwood-fast bf_bw \
    --schedule v17a --threads 1 --budget-ms 8000
```

### Vol-106 results

Same workload (canonical Selby-Riordan 16×16/22c, single-thread,
apple-m1, --release):

| binary           | pre-PGO     | post-PGO    | Δ       |
|------------------|------------:|------------:|--------:|
| bf_bw            |  63 M nps   |  72 M nps   | **+14%** |
| vanilla_v2       |  93 M pps   |  97 M pps   |  +4%    |
| vanilla_fastest  |  73 M pps   |  82 M pps   | **+12%** |

Variance across the three: ~4-14%, consistent with what
[Reintech 2026](https://reintech.io/blog/rust-performance-optimization-complete-guide-2026)
reports for PGO on simple hot loops. The gain correlates with
how many branch-prediction wins were available to LLVM — vanilla_v2's
inner loop was already tighter (fewer branches with non-obvious
patterns), so PGO had less to lever.

### Critical PGO gotcha

The training run's profile MUST be representative of production.
If the training was on an 8s seed=42 canonical solve, the PGO build
will be optimized FOR that branch pattern. Out-of-distribution
runs may be SLOWER than the pre-PGO build. Train on a mixed bag
of workloads if you'll see multiple usage profiles.

## Apple M1 micro-architecture (Firestorm core)

Numbers from [7-cpu.com](https://www.7-cpu.com/cpu/Apple_M1.html)
and [Hacker News](https://news.ycombinator.com/item?id=25659615):

- **L1d cache size: 128 KB** per Firestorm core (vs 32 KB typical x86).
- **L1i cache size: 192 KB**.
- **L2 cache: 12 MB shared** (between 4 Firestorm + 4 Icestorm).
- **L1d latency: 3 cycles** simple, 4 cycles with complex addressing.
- **Cache line size: 128 bytes** (vs 64 on x86). One cache line holds 32 u32, 64 u16, 16 u64.
- **Hardware prefetcher**: detects sequential / strided patterns. Random access defeats it.

### What this implies for our hot loops

- Our `pieces_used: [u64; 4]` (32 bytes) is **a single cache line**. L1d hit @ 3 cycles per check.
- Our `offsets` table is ~1 MB → L2-resident (12 MB L2). Per-cell lookup costs ~14 cycles (L2 latency). NOT in L1d.
- Our `entries` table is several MB → L2 / L3. But we walk it sequentially within a bucket — prefetcher takes care of it.
- The **per-depth lookups** (`offsets[flat]`, `depth_tbl[d]`, `depth_top_row[d]`) are the random-access ones. Each new depth pays a small L2 penalty.

### Optimization implications

- **Compact hot state into single cache lines.** Our bitset+cursor+depth fit; good.
- **Sequential bucket walks** are friendly to prefetcher; no change needed.
- **Two-level offsets table** could fit hot-key lookups in L1d (saves ~10 cycles per depth-entry). Untried yet.
- **NEON SIMD** isn't a fit for our DFS (single-element decisions); fits for the bucket-sort phase but that's init, not hot.

## AArch64 branchless tricks ([Microsoft Old New Thing](https://devblogs.microsoft.com/oldnewthing/20220815-00/?p=106975))

- `TBZ` / `TBNZ`: test-bit-and-branch in one instruction, ±32 KB range. LLVM emits these for `if (x & bit) { ... }` patterns when the offset fits.
- `CSEL` / `CSET` / `CSINC`: conditional-select / conditional-set. Replaces simple if-else assignments with a single branchless instruction.
- LLVM emits these when patterns are simple. The Rust source can sometimes block this (e.g. closures over mutable state, complex control flow). Inspect with `cargo asm` or `cargo show-asm`.

In our hot loop, the bitset test `(pieces_used[word] & bit) != 0`
compiles to `LDR + AND + TBNZ` — already optimal. The
`cur < end` comparison vs `entry != SENTINEL` was a wash on apple-m1.

## LLVM loop-unroll threshold

Per [CodeArchPedia 2026](https://openillumi.com/en/en-rust-loop-performance-llvm-threshold/):
LLVM fully unrolls loops with ≤ 239 iterations. Our trial loop walks
buckets that are typically 1-12 candidates (well under), but the
outer "depth descent" loop is 256 iterations (just over). LLVM won't
literally unroll it; we'd have to const-generic our way to per-depth
specialised functions to get the libblackwood-style fully-unrolled
result.

## What we did NOT yet do

1. **BOLT post-link reordering** ([cargo-pgo blog](https://kobzol.github.io/rust/cargo/2023/07/28/rust-cargo-pgo.html)) — typical 5-10% over PGO. Apple-m1 BOLT support is less mature than x86; would need to verify it produces a working Mach-O.
2. **`#[inline(always)]` on the hot-loop helpers** (entry_pid, entry_e, entry_s). Already done in our crates but worth verifying via `cargo asm`.
3. **Per-depth specialised functions** to get true 256-block unrolling. Const-generic + recursion + LLVM tail-call. Multi-day work.
4. **2-level offsets table** to fit per-depth lookup in L1d. Concrete next step; expected +5% based on cache-miss math.
5. **NEON-SIMD bucket sort at init** — init is sub-second, irrelevant.
6. **Speculative loads via `core::hint::spin_loop`** — micro-fence, not a lever for our pattern.

## Resources cited / consulted

- [The Rust Performance Book — Build Configuration](https://nnethercote.github.io/perf-book/build-configuration.html) (Nethercote, canonical reference)
- [Rust Performance Optimization Complete Guide 2026](https://reintech.io/blog/rust-performance-optimization-complete-guide-2026)
- [rustc Profile-guided Optimization docs](https://doc.rust-lang.org/beta/rustc/profile-guided-optimization.html)
- [Kobzol — Optimizing Rust programs with PGO and BOLT using cargo-pgo (2023)](https://kobzol.github.io/rust/cargo/2023/07/28/rust-cargo-pgo.html)
- [Apple M1 — 7-cpu.com](https://www.7-cpu.com/cpu/Apple_M1.html) (most reliable single page of M1 cache numbers)
- [insn_bench_aarch64 / optimization_notes_apple_m1](https://github.com/ocxtal/insn_bench_aarch64/blob/master/optimization_notes_apple_m1.md)
- [Hacker News thread on M1 memory access](https://news.ycombinator.com/item?id=25659615)

## Linked

- [[blackwood-fast]] — the crate the PGO measurements were on.
- [[vanilla-v2]] — the new vanilla DFS that vanilla_fastest+12%-w/-PGO.
- [[../sessions/vol-106|vol-106]].
