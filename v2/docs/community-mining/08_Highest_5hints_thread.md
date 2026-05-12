# "Highest points (of 480) with using all 5 (!) hints?" — topic 97336163 (38 msgs, 2023-03)

## Headline

A 2023 leaderboard thread specifically for **5-hint canonical scenario**.
Highest score reached: **460/480** by Bruno Gauthier using "Eternity II
Editor" (`sourceforge.net/projects/eternityii/`).

Other scores posted in the thread (all 5-hint canonical):
- 412 — capiman26061973 (seed)
- 447 — Carlos Fernandez (intermediate)
- 452 — Carlos Fernandez
- 453 — David Barr
- 454 — Carlos Fernandez (after swap improvement)
- 455 — Carlos Fernandez and David Barr (independent)
- 456 — David Barr
- 457 — Carlos Fernandez
- 458 — David Barr
- **460 — Bruno Gauthier** (March 9, 2023)

All boards shared as decoded bucas URLs (already in our community_corpus).

## Methods used

**Carlos Fernandez's two-program approach**:
1. First program is a variation of Joshua Blackwood's solver. Two cycles:
   - Cycle 1: starting from bottom-left, solve 4 rows, save result.
   - Cycle 2: read that file, rotate pieces 180°, place at top, solve
     remaining space. Rotate back.
2. Second program takes the output and **exchanges pieces to improve**
   the score. Found 454 in 2 minutes, then 455.

**Bruno's tool**: Eternity II Editor (Java, on SourceForge). Manual
+ algorithmic. Copy/paste scanrow grids.

**David Barr's Python solver**: source at `pastebin.com/7SD89c6T`.
Iterates split-strategies for last 4 rows in various-sized chunks.

## New solver references

- **Eternity II Editor**: `sourceforge.net/projects/eternityii/` —
  Java-based, manual placement + heuristics. Worth fetching to
  understand Bruno's workflow.
- **David Barr's Python solver**: `pastebin.com/7SD89c6T` (may have
  expired).
- **Carlos Fernandez's "Joshua Blackwood variation"**: not published
  on GitHub. Mentioned only verbally in this thread.

## Observation worth recording

**The 5-hint canonical scenario peaks at 460 across this 2023 thread,
not 467 or 469**. Verhaard's 467 (2008) and McGavin's 469 (2020) used
different methods. The 2023 cohort is **less effective** than Verhaard
or McGavin per pure solver throughput. This suggests the **community
SOTA has not propagated cleanly** — different teams reinvent and cap
at different scores. Vol-9 building from Verhaard's actual method
documented in vol-8 has a chance to clear this cohort.

## What this changes

- **Bruno Gauthier's 460 is verifiable**: should already be in our
  community_corpus. If not, fetch it.
- **Carlos's "two-cycle 180° rotation" trick** is a concrete macro-move
  worth understanding. It says: complete the bottom strip, then rotate
  the whole solver state 180° and "place from the top" — effectively
  searching both endpoints inward. Could be useful in vol-9's SA.
