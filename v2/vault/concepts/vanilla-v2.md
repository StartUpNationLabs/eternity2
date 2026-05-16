---
name: vanilla-v2
description: Vol-106 T3 — vanilla DFS rewritten using blackwood-fast's optimization patterns. 92-93M pp/s single-thread on canonical 16x16 (vs vanilla_fastest's 72-73M, +27%). Per-position bucketing + sentinel-terminated lists + u64 bitset + unsafe inner loop.
metadata:
  type: project
---

# vanilla-v2 (vol-106 T3)

**Status**: `built`.
**Origin**: vol-106 (2026-05-16). User direct ask: "could we apply
the same logic to build a freaking amazing vanilla DFS too that's
even faster than our current one?" + "build a v2 of it".
**Files**: `crates/blackwood-fast/src/bin/vanilla_v2.rs`.

## What it is

A vanilla row-major DFS for canonical 16×16 E2 with NO Blackwood
schedule, NO heuristic patterns, NO break-index allowance — just
raw backtracking with the cleanest possible inner loop. It applies
the architectural patterns from [[blackwood-fast]] on top of
[[vanilla-fastest]]'s per-position bucketing scheme.

## What was changed vs vanilla_fastest

| pattern | vanilla_fastest | vanilla_v2 |
|---|---|---|
| Per-position buckets keyed by `(north_color, west_color)` | yes | yes (identical scheme) |
| Border constraints implicit in bucket build | yes | yes |
| Rare-pid-first sort within bucket | yes | yes |
| Used-pieces representation | `[bool; 256]` (1 byte/piece) | `[u64; 4]` bitset (8 bits/byte) |
| Bucket termination signal | `bucket_end_at_depth[d]` (extra load + compare per trial) | sentinel `u32::MAX` (1 load + 1 cmp) |
| Inner-loop bookkeeping | `bucket_start_at_depth` + `bucket_end_at_depth` (2 arrays, 1 load each on bucket entry) | `frame_cursor` alone; sentinel signals end |
| Entry encoding | u32 with (pid, rot, s, e) | identical u32 layout |
| Hint pinning | yes | omitted (orthogonal feature) |
| Multi-threading | yes | omitted (orthogonal feature) |

## Measurements

Canonical Selby-Riordan 16×16 with 22 interior colors. Single
thread, apple-m1, --release. Same puzzle, same border ordering.

| budget | vanilla_v2 (pp/s) | vanilla_fastest (pp/s) | speedup |
|---:|---:|---:|---:|
|  3s |       93.2 M |        73.0 M | +27.6 % |
|  5s |       93.1 M |        73.3 M | +27.0 % |
| 10s |       92.4 M |        72.1 M | +28.2 % |
| 15s |       92.6 M |        72.6 M | +27.6 % |

Max depth: vanilla_v2 = 205-212, vanilla_fastest = 207-210 (rough
parity, within ALNS-style noise).

## What drove the speedup

The hot inner loop in vanilla_fastest is:

```rust
let end = bucket_end_at_depth[depth];     // L1 load
let mut cur = frame_cursor[depth];        // L1 load
while cur < end {                         // 1 cmp + 1 br
    let entry = bucket_data[cur];         // L2 load
    let pid = entry_pid(entry);
    if !used[pid] { found = entry; break; } // 1 byte load + 1 br
    cur += 1;
}
```

vanilla_v2's hot loop:

```rust
let mut cur = frame_cursor[depth];        // L1 load
loop {
    let entry = entries[cur];             // L2 load
    if entry == SENTINEL { break; }       // 1 cmp + 1 br
    let pid = entry_pid(entry);
    let bit = 1u64 << (pid & 63);
    if (used[pid >> 6] & bit) != 0 { cur += 1; continue; }  // 1 u64 load + 1 and + 1 br
    found = entry; break;
}
```

Differences worth their existence:

1. **Sentinel terminator**: eliminates the `bucket_end_at_depth[d]`
   read at the top of every depth entry, plus removes a register
   that LLVM would otherwise pin to `end`.
2. **u64 bitset**: same byte-count as `[bool; 256]` but checked via
   a single `and` instruction. Slightly tighter codegen on apple-m1
   because the bitset fits in L1d cache lines.
3. **Single cursor**: `frame_cursor` alone tracks resume position;
   no separate start/end pair. Halves the bookkeeping per backtrack.

These are micro-optimizations individually, but compounded they
yield the +27% measured.

## What it doesn't have

- **No hint pinning.** The canonical 5 hints (4 corners + center)
  are not enforced. For score-axis work where hints must be
  respected, use vanilla_fastest (which supports `--pin-hints`).
- **No multi-threading.** A single worker. Trivial to wrap in rayon
  with per-thread bucket-seed offsets if needed.
- **No save/snapshot.** No `--save-best`, no `--snapshot-dir`. Pure
  benchmarking tool.

For real score-axis work, vol-107+ should port these features onto
vanilla_v2 (or — equivalently — port vanilla_v2's hot loop changes
back into vanilla_fastest).

## Linked

- [[blackwood-fast]] — the sibling crate where the patterns came from.
- [[../sessions/vol-106|vol-106 session]].
