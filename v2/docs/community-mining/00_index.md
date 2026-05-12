# Community-mining index — vol-10 probe #7

Per-thread analysis of the top groups.io threads on Eternity II.

## Source

`v2/community-exports/messages.jsonl` — 11,511 messages from
groups.io/g/eternity2, 2000-2026. Read using
`scripts/v10_thread_reader.py` which de-HTML's and dedups quoted
replies per thread.

## Threads digested (12 of ~30 substantive threads with ≥25 msgs)

| # | Subject | Msgs | Date | File |
|---|---------|-----:|------|------|
| 1 | SAT | 82 | 2011-2026 | [01_SAT_thread.md](./01_SAT_thread.md) |
| 4 | Design the hardest puzzle | 54 | 2007-08 | [02_Design_the_hardest_thread.md](./02_Design_the_hardest_thread.md) |
| 13 | Algorithmic Challenges related to E2 | 44 | 2010-06+ | [03_Algorithmic_Challenges_thread.md](./03_Algorithmic_Challenges_thread.md) |
| 17 | Interior Rectangles | 40 | 2008-03 | [04_Interior_Rectangles_thread.md](./04_Interior_Rectangles_thread.md) |
| 60 | A method to prune E2 search space by 17-30%+ | 26 | 2026-01 | [05_Joe_pruning_method_thread.md](./05_Joe_pruning_method_thread.md) |
| 46 | Estimated number of solutions with/without hints | 28 | 2024-01 | [06_Solution_count_estimates_thread.md](./06_Solution_count_estimates_thread.md) |
| 32 | Two-stage solution process | 32 | 2025-05 | [07_Two_stage_solution_thread.md](./07_Two_stage_solution_thread.md) |
| 20 | Highest points (of 480) with 5 hints | 38 | 2023-03 | [08_Highest_5hints_thread.md](./08_Highest_5hints_thread.md) |
| 28 | EternityII Solver (Blackwood release) | 34 | 2020-09+ | [09_Blackwood_solver_thread.md](./09_Blackwood_solver_thread.md) |
| 58 | While solving for a 14x14 - 196 solution | 26 | 2022-05+ | [11_Inner_14x14_thread.md](./11_Inner_14x14_thread.md) |
| 14 | Eternity2 information - Disclosure | 43 | 2011-02 | [12_Solution_secrecy_thread.md](./12_Solution_secrecy_thread.md) |
| miscellaneous | (7 medium threads) | — | various | [10_misc_threads.md](./10_misc_threads.md) |

## Threads NOT yet digested (worth future passes)

In rank order by size, threads ≥25 msgs not yet read:

- #2 "New file uploaded to eternity_two" (64 msgs, 2008-05) — file-upload notifications
- #3 "Datasets for the Proposed Benchmark Puzzles" (57 msgs, 2008-02)
- #5 "89794 nodes for the size 14 hints 15_2 benchmark" (52 msgs, 2007-10)
- #6 "Robby the Robot" (49 msgs, 2008-07) — read; covered in 10_misc
- #7 "Question for Christopher Monckton" (46 msgs, 2007-07)
- #8 "Is E2 the hardest design?" (46 msgs, 2008-04)
- #9 "Things running?" (46 msgs, 2013-05) — has dvholten's EMPI claim already captured
- #10 "New round of benchmarks" (45 msgs, 2007-08)
- #11 "Minimal E2 coding" (45 msgs, 2008-03)
- #12 "Brendan's puzzles" (45 msgs, 2009-02) — read; covered in 10_misc
- #14 (read above)
- #15 "UP_OR_LEFT_BORDER type" (41 msgs, 2007-08) — covered in 10_misc
- #16 "Brendan's set_1 10x10 solution" (41 msgs, 2017-09) — partially covered; key finding (Takahashi 468 on TopCoder variant) recorded
- #18 "Alternate approaches - Forum Sleeping" (40 msgs, 2011-05) — read; mostly debug chat
- #19 "Going to be hard to wait till Monday!" (38 msgs, 2008-09) — Verhaard 467 submission anticipation
- #21 "human challenges related to E2" (36 msgs, 2007-09)
- #22 "Benchmark puzzle (16x16, 24 borders)" (35 msgs, 2007-07)
- #23 "Rotation Solutions" (35 msgs, 2007-11) — partially covered in vol-10 probe #5 (C-2)
- #24 "Possible scanline optimization" (35 msgs, 2008-10)
- #25 (read above)
- #26 "New competition: solve by hand" (34 msgs, 2008-09)
- #27 "Proposed homotopy method..." (34 msgs, 2009-03) — covered: apal's 3×3 sub-puzzle enumeration
- #29 "E2 Benchmark files, Brendan's 8x8" (33 msgs, 2007-03)
- #30 "Scoop" (32 msgs, 2007-07)
- #31 "Happy new challenge for 2008..." (32 msgs, 2007-12)

## Most session-defining findings cross-thread

1. **Canonical solution count**: McGavin's complex theory gives
   ~14,702 solutions with start piece, ~4×10^-8 with 5 hints
   (= ~1 solution; canonical E2 has unique-solution boundary by
   design). See `06_Solution_count_estimates_thread.md`.

2. **Brendan's complete model** (May 2025): 10^38 borders × 10^34
   inner solutions × 10^-27 matching = 10^45 search space.
   Two-stage decomposition is intractable. See `07_Two_stage_solution_thread.md`.

3. **Blackwood's complete 469 algorithm** documented verbatim (msg #31
   of Blackwood thread, Nov 2020). Heuristic-sides + piecewise-linear
   exhaustion + 12 scheduled break indices. See `09_Blackwood_solver_thread.md`.

4. **The 17-color phase-transition formal anchor** (Mateu 2012,
   Springer-published): E2 sits at the GEMP-F SAT phase-transition
   peak. See `01_SAT_thread.md`.

5. **The 17+5 color split is mathematically derived** (Brendan +
   stertenbrink 2007): I=17, B=5 give expected ~1 solution by exact
   formula. See `02_Design_the_hardest_thread.md`.

6. **The 14×14 internal sub-problem is empirically intractable**
   (4.4×10^13 days at random search per Brendan 2008; not solved in
   19 years per onesmallstep 2025). See `04_Interior_Rectangles_thread.md`,
   `11_Inner_14x14_thread.md`.

7. **The multiset-equality propagator (vol-10 NS-1) was
   independently proposed by Al Hopfer in 2022**. The community
   already verified 14×14 sub-puzzles with parity-correct boundaries
   solve in minutes. See `11_Inner_14x14_thread.md`.

8. **Joe's prune-back-to-depth-150 policy** (Jan 2026): 17-49%
   search-space reduction. Adoptable today by vol-9.
   See `05_Joe_pruning_method_thread.md`.

9. **McGavin's 295M nodes/sec C backtracker** code is in the Joe
   pruning thread (msg #18, attached ZIP). 4× faster than typical.
   See `05_Joe_pruning_method_thread.md`.

10. **SAT scales to 10×10** — universal limit, 4 independent
    confirmations. See `01_SAT_thread.md`.

11. **Takahashi 468 (chokudai)** is on the **TopCoder unframed
    variant**, not canonical E2. McGavin 469 remains the verified
    canonical 5-clue ceiling. See `10_misc_threads.md` and the
    "Brendan's set_1 10x10" thread tail.

12. **No one alive knows the official E2 solution** — Tomy disclosed
    that the generator computer was destroyed; solution sealed in
    envelope. See `12_Solution_secrecy_thread.md`.

13. **Brendan personally confirms the disjoint-color design** as
    deliberate (May 2025): *"the arrangement of colours on the edge
    and corner pieces is different from the colour arrangement on the
    middle pieces. This wasn't accidental; it was a deliberate design
    choice to make the puzzle harder."*

14. **Optimal scanline path** for canonical E2: **bottom-left
    start, left-right rows** (McGavin 2017, validated by complex
    theory). See "Brendan's set_1 10x10" thread.

15. **E2 piece-set deliberately resists rotation-set finding**
    (Dave Clark 2007): Real E2 pieces are ~10× harder to find valid
    rotation-sets than randomized matched piece-sets — empirical
    evidence the generator engineered against this oracle. See vol-10
    probe #5 C-2.

## Methodological note

Three approaches were tried in vol-10 for community-corpus mining:

1. **vol-8 score+method-name grep**: 5 community techniques surfaced.
2. **Probe #5 intent-keyword grep**: 6 additional items.
3. **Probe #7 per-thread full reading**: 15 additional structural
   findings + 3 algorithmic anchors after 12 threads (of ~30
   substantive). Per-thread reading is **most productive** but
   highest-context-cost. Reading complete threads is much more
   efficient than grep for narrowly-themed but deeply-developed
   discussions like "SAT" (where every message builds on the prior).
