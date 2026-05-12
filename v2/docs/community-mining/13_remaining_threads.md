# Remaining threads — final batch

Brief notes on the rest of the ≥25-msg threads not warranting standalone
files. Read at lower fidelity (scanning headers + key messages); detailed
algorithmic content is mostly absent or already covered in earlier files.

## Threads with concrete additional findings

### Thread #2 "New file uploaded to eternity_two" (64 msgs, 2008-05)
Benchmark verification chatter for a 12×12 with 40 hints. Max + Brendan +
Geoff debug each other's complex-theory estimates. **Nothing new.**

### Thread #5 "89794 nodes for the size 14 hints 15_2 benchmark" (52 msgs, 2007-10)
**doc_s_smith vs. Txibilis benchmark race** on 14×14 sub-puzzles with
many hints. doc_smith's **automatic strategy-finder beat Txibilis's
hand-tuned strategies** on hints14_15_2: 89,794 vs 141,628 nodes;
hints14_20_2: 10,667 vs 15,909. **Confirms doc_smith's strategy-finding
algorithm works.** Already partly captured in 03_Algorithmic_Challenges.

### Thread #7 "Question for Christopher Monckton" (46 msgs, 2007-07)
Brendan was interviewed on Australian TV in 2007. Predictions of solve
probability ranged 10-50%. **No technical content.**

### Thread #8 "Is E2 the hardest design?" (46 msgs, 2008-04)
**Brendan's design-parameter sweep** comparing alternative (B, M) tuples:

| B | M | Nodes (1-hint) | Solutions |
|---|---|--------------:|----------:|
| 4 | 16 | 2.9×10^57 | 1.4×10^20 |
| 4 | 17 | **4.3×10^51** | 1.1×10^11 |
| 4 | 18 | 4.2×10^44 | 1.3 |
| **5** | **17** | **1.8×10^50** | **1.7×10^9** ← E2's choice |
| 5 | 18 | 7.6×10^43 | 1.0 (= unique solution boundary) |
| 6 | 16 | 1.7×10^54 | 1.2×10^15 |
| 6 | 17 | 1.4×10^47 | 1.5×10^4 — **33× harder than E2!** |

**E2's (5,17) is NOT the globally hardest design at 1-hint** — (6,17)
is 33× harder. But (5,17) was chosen, possibly for marketing
(5 hint slots = 4 clue puzzles + 1 starter, retail product structure).

**(5,18) achieves expected-unique-solution at the cost of being slightly
easier than (5,17) by ~10^7 nodes**. The designers chose the
solvable-but-still-very-hard (5,17) point.

### Thread #9 "Things running?" (46 msgs, 2013-05)
**dvholten's EMPI invariants formally named** (already captured in
probe #5 C-3). Otherwise chatter about copyright and 14×14-frame partial
solutions (which turn out to be 14-cell-wide framed sub-rectangles, not
the genuine inner 14×14 unframed sub-problem).

### Thread #10 "New round of benchmarks" (45 msgs, 2007-08)
**Backtracker speed circa 2007**: 25-28.5M nodes/sec single-thread on
Core2Duo. Compares to McGavin's 2024 295M/sec (~10× hardware/code
improvement in 17 years). Mentions `e2a.c` simple-backtracker
reference implementation. **No algorithmic news.**

### Thread #11 "Minimal E2 coding" (45 msgs, 2008-03)
**Information-theoretic minimum encoding** of one E2 solution:
~1096-1562 bits, i.e. 137-195 bytes uncompressed. **The solution-space
entropy is ~10^330 leaves at worst.** Confirms search-space scale.

### Thread #16 "Brendan's set_1 10x10 solution" (41 msgs, 2017-09)
**McGavin's first novel 10×10 solution.** 92,907 backtracker tests,
~2×10^17 nodes, **180 core-years** across 130+ cores. **Confirms
Takahashi 468 was on TopCoder UNFRAMED variant**, not canonical E2
(via TopCoder forum link). Already captured in 10_misc_threads.

### Thread #21 "human challenges related to E2" (36 msgs, 2007-09)
**doc_s_smith's 2007 classification** of E2-related problems:
- (a) solving by hand
- (a2) maximizing partial score
- (a3) optimal strategy for many-hint puzzles
- (b1) backtracker speed optimization (top 2007: 28.5M/sec)
- (b2) high-partial-search algorithms
- (b3) automatic strategy-finding

**Already articulated in 2007 what dimkadimon's 2025 ML-eval beam
search is trying to do.** 18-year gap; same problem.

### Thread #22 "Benchmark puzzle (16x16, 24 borders)" (35 msgs, 2007-07)
Early benchmark proposal. Now superseded by E2's actual 17+5.
**Historical.**

### Thread #24 "Possible scanline optimization" (35 msgs, 2008-10)
**Max's "irrelevant-edge equivalence class" pruning**: when starting
a new row, multiple border pieces share the same interior-facing
color; the unmatched border color is irrelevant if the row doesn't
complete. **Reject equivalent pieces after one fails.** Predicted 1/3
search-space reduction. **Worth implementing in vol-9 scanline path.**

### Thread #26 "New competition: solve by hand" (34 msgs, 2008-09)
Speculation. No solver content.

### Thread #29 "E2 Benchmark files, Brendan's 8x8" (33 msgs, 2007-03)
Early benchmark files. Historical.

### Thread #30 "Scoop" (32 msgs, 2007-07)
News/announcement chatter.

### Thread #33 "Search speed" (31 msgs, 2007-08)
**Exact-cover encoding for E2**: 5,614 columns × 157,264 rows.
Per-cell 256-tile-uniqueness column + (colors × 480)-edge-color
columns. **Each color requires one-of-N + complement columns.**
DLX feasible. (Vol-7's solver-naive already uses DLX.)

### Thread #34 "Brute force does not work" (31 msgs, 2007-10)
**Definitive 2×2 partial counts** for E2:
- 5,248 corner 2×2s
- 292,012 edge 2×2s
- **4,059,952 internal 2×2s**

Hint constraints exclude 238,454. **Sanity-check baseline for vol-9
propagators.**

### Thread #35 "This one is for the speed freaks" (30 msgs, 2008-04)
**10×10 with 5 hints exhaustive solve: 3:28 hr single-thread, ~5
billion nodes, exactly 1 solution.** Multiple independent solvers
confirm. Match to all other estimates.

### Thread #37 "Disqualified" (29 msgs, 2007-08)
About someone being banned for sharing pieces. **No content.**

### Thread #38 "Beginner puzzle solutions" (29 msgs, 2008-03)
**Brendan's simple-theory predictions** for 8×8/9×9/10×10 confirmed
empirically. **10×10 with 5 hints takes 100 years at 0.2M nodes/sec
single-core**; 1 year per solution on a 20M/sec solver.

### Thread #39 "Non-recursive backtrackers" (29 msgs, 2008-03)
Architectural debate (stack vs. recursive). **No fundamentals.**

### Thread #40 "Code benchmarking — Kron's Walker" (29 msgs, 2008-04)
**Geoff's three-tier backtracker speed comparison** on B8x8With2Hints:
- Dumb backtracker: **250M nodes / 67s**
- Smart backtracker (constraint prop): **5.3M nodes / 38s — 47×
  fewer nodes**
- + probabilistic trimming: **2.78M nodes / 19s — additional 2×**

**Vol-9 should reach 47× node reduction vs naive backtracker** as a
sanity check.

### Thread #43 "Using precalculated 2x2 piece combinations" (28 msgs, 2007-12)
Discussed using 2×2 lookup tables. **Negative: too many 2×2s (4M+),
indexing overhead exceeds gain.** Confirms 2×2 meta-tiling isn't
worth it.

### Thread #44 "First Scrutiny over" (28 msgs, 2009-01)
Tomy "no winner" announcement. Verhaard's 467 was the highest
submitted. No prize awarded. **Historical.**

### Thread #45 "Sorry if this is already answered" (28 msgs, 2009-08)
**Information-theoretic argument**: ratio (A/B) of
ways-to-arrange-a-puzzle to puzzle-piece-sets ≈ 16.4 for E2. Confirms
**E2 sits at the unique-solution boundary by construction**.

### Thread #47 "An idea but no coding skill to back it up" (27 msgs, 2007-11)
Newbie suggestion + Brendan's response. **No new technique.**

### Thread #48 "Argentina presente!" (27 msgs, 2008-01)
Social. No technical content.

### Thread #49 "Language Solution" (27 msgs, 2010-03)
**Speculation: is E2 encoded Hebrew Bible text?** Multiple speakers
explore the idea. **No, mathematical analysis rules it out** —
patterns are too uniformly distributed for natural language.

### Thread #50 "Top Results" (27 msgs, 2014-10)
**2014-10 status: 467/480 is still the canonical 5-hint record**
(unchanged from 2008). Brendan's Set 2 10×10 still unsolved.
**Confirms 6-year stagnation between Verhaard 2008 and 2014.**

### Thread #51 "Problem with the solver stack?" (26 msgs, 2007-08)
Solver-bug debugging. **No content.**

### Thread #52 "The old Hints_11_2 benchmark" (26 msgs, 2007-10)
Benchmark verification. **No new finding.**

### Thread #53 "E2 has 15 millions of solutions" (26 msgs, 2007-12)
Speculation thread. The "15 million solutions" claim is mathematically
wrong (Brendan's complex theory gives ~14,702 — six orders of
magnitude lower). **Historical confusion that the community resolved.**

### Thread #54 "Do me a favour? :)" (26 msgs, 2008-01)
Help request. **No content.**

### Thread #55 "Combined effort" (26 msgs, 2008-09)
**Markus Zajc's recursive ARC propagation** description (already
captured in probe #5 / thread 13). **Estimate: "reduce to <25 tiles
and the rest follow at once"** — overly optimistic.

### Thread #56 (covered)
### Thread #57 (covered)

### Thread #58 (covered in thread file 11)

### Thread #59 (covered in vol-10 probe #6)

### Thread #60 (covered in thread file 05)

### Thread #61 "E2 mappings to known problem types" (25 msgs, 2007-07)
Discussion of mapping E2 to: exact cover, k-SAT, max clique, graph
coloring. **All confirmed mappable but intractable at E2 scale.**

### Thread #62 "Brendan's interior piece challenge" (25 msgs, 2008-04)
**Brendan posed: complete the 14×14 interior using all 196 inner
pieces.** Same as Al Hopfer's 14×14 challenge later (thread 58).
**Still unsolved 17 years later.**

### Thread #63 "Metatiles are a speedup but no domain reduction" (25 msgs, 2008-09)
**Definitive negative result**: 2×2 meta-tiling gives ~4× BK-step
reduction but generates 1M+ tiles. 4×4 meta-tiling generates
3×10^10–10^13 tiles, infeasible to enumerate. **Net: meta-tiling
not worth implementing in vol-9** for canonical E2 size.

### Thread #64 "New E2 solver available" (25 msgs, 2008-09)
Yet another solver release. **No fundamentally new technique.**

### Thread #65 (covered above)

## What's left unread

A handful of threads with ≥25 msgs are still untouched (some of the
covered IDs above span the rest of the top 30+). The remaining ones
are likely either:
- Social / news / debug threads
- Variants of already-covered topics
- Newbie introductions

I'm choosing to stop here as **the marginal information yield is
clearly diminishing** — the last 5 threads I checked produced 0-1
substantive new items each, vs. 3-5 items per thread for the top 12.
The community-mining task has been exhausted as much as is useful
without deep-dive on specific newer (2024-2026) threads.

## Final cross-thread summary

The community's collective understanding of E2:

1. **Designed at the unique-solution boundary** (B=5, M=17) but not
   the globally hardest configuration — (B=6, M=17) would be 33×
   harder. (Brendan 2008, thread 8.)
2. **Canonical 5-hint puzzle has expected ≈1 solution** (complex
   theory 4×10^-8). Tomy says the solution exists; sealed envelope.
3. **No method generalizes**: every approach (SAT, GPU, meta-tiling,
   parity, beam search, exhaustive enumeration) has been tried and
   capped at 10×10 in some form.
4. **Optimal piece-placement: scan-row from bottom-left** (validated
   by complex theory + Verhaard's eii experience + McGavin 2024 C
   code achieving 295M/sec).
5. **The best community-found canonical 5-hint score is 469**
   (McGavin 2020). Verhaard's 467 (2008) stood for 12 years.
6. **The hint utility is debated**: Blackwood/onesmallstep/reinout
   say hints make partial-solving harder; Brendan (designer) says
   "the hints primarily serve to give people false hope."
7. **The internal 14×14 sub-problem is intractable at random search**
   (~10^11 core-years per Brendan 2008 theory). Still unsolved.
8. **The multiset-equality propagator (vol-10 NS-1) is real and
   independently discovered by the community** (Al Hopfer 2022).
   Implementable, finite gain, not a silver bullet.
