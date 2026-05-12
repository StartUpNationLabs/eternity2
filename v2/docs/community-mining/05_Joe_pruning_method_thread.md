# "A method to prune E2 search space by 17-30%+" — topic 117069769 (26 msgs, 2026-01)

Very recent and very concrete. Joe + Peter McGavin + Mike Pringle.

## Joe's pruning policy (vol-9-implementable today)

**Setup**: standard scan-row backtracker on E2 (or E2-like). Profile shows:
- 99% of backtrack time is at depth >132
- 70% of backtrack time is at depth >150

**Policy**: if the backtracker spends N iterations at depth > T without
finding the next placement, **prune back to depth T** and restart.
N and T are tuneable.

**Empirical sweep** (Joe's table on his 16x16 E2-like puzzle, no canonical
E2 hints — uses correct-tile hints from a known solution):

| Border hints | Inner hints | Total hints | Prune-after-N | Prune-to-depth | Iterations | Reduction |
|--------------|-------------|-------------|---------------|----------------|-----------|-----------|
| 60           | 56          | 116         | (none)        | -              | 370M      | baseline |
| 60           | 56          | 116         | 2000          | 150            | 258M      | **30%**   |
| 60           | 56          | 116         | 1600          | 150            | 189M      | **49%**   |
| 60           | 48          | 108         | (none)        | -              | 899M      | baseline |
| 60           | 48          | 108         | 1600          | 150            | 723M      | 20%       |
| 60           | 48          | 108         | 132           | -              | 548M      | 39%       |
| 60           | 44          | 104         | (none)        | -              | 8.4B      | baseline |
| 60           | 44          | 104         | 1600          | 150            | 6.5B      | 23%       |
| 60           | 40          | 100         | (none)        | -              | 47B       | baseline |
| 60           | 40          | 100         | 1600          | 150            | 39B       | **17%**   |

**Net finding**: even at 100 hints (only 56 fewer than the solution), the
pruning yields 17%. Effectiveness peaks at the "fully-determined start"
regime (116 hints) at ~49%.

## Hint-count vs information content

Joe's permutation table:

| Hints | Permutations |
|------:|-------------:|
| 0     | 1.3×10^179 |
| 16    | 6×10^24 |
| 32    | 10^51 |
| 64    | 2.4×10^85 |
| 72    | 9.9×10^145 |
| 88    | (solved by crypto-RNG run) |
| 128   | 6×10^24 ?(table inconsistent) |

The takeaway: **each correctly-placed hint reduces the search space by a
geometric factor**. The 5 official E2 hints reduce by ~10^9 — significant
but small compared to 100+ hint hints from a known solution.

## Peter McGavin's optimized C backtracker

McGavin shared his C code as a ZIP attachment in this thread (msg #18).
**This is the single most-optimized public E2 backtracker.**

Performance benchmarks:
- **295M tile placements / second single-core** on Joe's E2-like puzzle.
- For comparison: community typical 70-90M/sec; David Barr 40M/sec C code;
  Joe's C# 27-37M/sec.

Techniques used (per McGavin msg #20):
- `gcc -O6 -mcpu=native -mtune=native -march=native`
- Try clang, icc, icx; profile-guided optimization
- (Surprising:) for some workloads, compile 32-bit with `gcc -m32`
- Auto-generated unrolled per-cell goto-style code:
  ```c
  case70:
    if (70 > best) { print_puzz2(70); best = 70; }
    if (!Q[70].active) {
      Q[70].pieces = fit_table[(((Q[11].pieces->piece->edges[2])*24+23)*24+23)*24+Q[69].pieces->piece->edges[1]];
      Q[70].active = TRUE;
    }
    if (Q[70].pieces->piece) {
      placed[Q[70].pieces->piece->piecenum] -= 1;
      Q[70].pieces = Q[70].pieces->next;
    if (!Q[70].pieces) { Q[70].active = FALSE; goto case69; }
    p = Q[70].pieces->piece;
    if (placed[p->piecenum]) {
      placed[Q[70].pieces->piece->piecenum]++;
      goto case70;
    }
    nodes += 1;
    placed[Q[70].pieces->piece->piecenum] = 1;
  ```
- Lookup table `fit_table` indexed by **(north-edge, east-edge, south-edge,
  west-edge)** of three adjacent cells, plus per-cell sentinel padding.

Vol-7's `solver-engine` is in Rust; if we can match this speed (~300M/sec)
on E2 specifically, we have a strong throughput edge. The McGavin code is
the reference target.

## McGavin's "15-hints solve" on Joe's E2-like

Solved Joe's 16x16x5x17_71.txt (different piece set — 17 interior colors)
with only **15 strategically-placed hints** in ~5.5 hours on a Ryzen 5
5600H. Search tree had 41.16B nodes. **Hint positions matter**: Joe's
"first 116 sequential row-hints" achieves 1.5K iters; McGavin's "18
strategically dispersed hints" achieves ~3B iters but with a much
sparser hint set.

Mike Pringle separately reports: **74 hints in a spiral-out path solve
the same puzzle in 7M placements** (per his solver). Add the 4 outlying
hints corresponding to E2's original hints, reduces to 101 hints.
**The placement of hints relative to the search path matters more than
the count.**

## What this changes for vol-9 / vol-11

**Immediate vol-9 actionable**:

1. **Adopt Joe's prune-back-to-depth-150 policy** in the vol-9 SA
   inner backtracker. Trivial to add. Predicted 17-49% speedup.
2. **Adopt McGavin's lookup table layout** (4-axis edge-color index)
   if vol-9's solver-engine isn't already using this. Matches the
   295M/s target.
3. **Read Mike's 2007 post #3098** for the original optimization
   techniques.

**Vol-11 candidates**:

4. Joe's per-hint-count permutation table is a clean information-theoretic
   model of the problem. Could be used to predict whether a partial
   solution at a given depth has enough constraint to be completable.
5. **The 49%-reduction parameter (1600 iters + depth 150) on the
   16x16 E2-like generalizes only partially** — Joe found "Brendan's
   16x16 ranges 2500-30k iters" instead of 1500, suggesting the
   optimal pruning depth is puzzle-dependent. Worth calibrating on
   canonical E2.

## Direct quotes worth preserving

- McGavin (Feb 2025): *"It doesn't stop when it finds a solution. It
  keeps searching for more solutions until the entire search tree is
  searched."* — important context for benchmarking.
- Joe (Jan 2026): *"It seems we do not need to search the full search
  space, and can calculate the target search space based on the first
  116 to 150 tiles and pruning periodically. The trick is finding the
  sweet spot for the pruning parameters that reveals the solution
  without skipping past it."*
- McGavin (Jan 2026): *"For the fewest number of hints to practically
  solve the 16x16, I would expect those few hints to be dotted around
  the lower half (say) of the board, perhaps at knight spacing, or in
  the corner of every 3x3, or something like that, rather than all
  concentrated together..."* — **hint-placement geometry matters**.
- Mike Pringle (Jan 2026): *"spiral-out hint placement was most
  efficient... 74 hints, 7M placements without heuristics."*
