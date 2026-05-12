# Miscellaneous high-value findings from additional threads

Aggregated short notes from threads not warranting standalone files.

## Thread #6 — "Robby the Robot allowing mismatching" (49 msgs, 2008-07)

Already partly covered in [vol-8 catalogue C-3 / prove #5]. New
specifics from full-read:

- **Max (Jul 2008)**: took a 219-piece scanline partial, allowed
  single-edge-mismatch from depth ≥215, **found 461 almost
  instantly, several 463s in half a day**. The mismatch-allowed
  endgame was *original* to Max in this thread.
- **Max's piece-hardness-quota propagator**: for first 128 pieces of
  backtracking, backtrack not only on color-failure but **also if
  enough hard pieces have not yet been used**. Increased average
  branch depth by ~7 pieces. This is **a different propagator from
  Blackwood's heuristic-side-exhaustion** and worth implementing
  independently.
- **Al (originator, Jul 2008)**: piece hardness = number of edge-pair
  matches with all other pieces. Lookup-table indexed for quick
  placement. **452 by hand in 1 hour** (filling gaps in a 244 legal
  partial). Independent observation: *"if you flip the piece order
  the results are about the same, mixing makes it worse"* — hardness-
  order is monotone-useful.

Later messages (#11-#49) are philosophical (physical-simulation
modeling, autonomous-agent theories). No actionable algorithm.

## Thread #12 — "Brendan's puzzles" (45 msgs, 2009-02)

Tom (istarinz) ran exhaustive solver on ~30 sub-puzzles of Brendan's
two test sets. Published full **solution-count + nodes-searched
tables**:

Selected entries (Set 1):

| Puzzle | Solutions | Nodes for exhaustive search |
|--------|----------:|--------------------------:|
| 5×5 | 8 | 42,324 |
| 6×6 | 65 | 15,400,045 |
| 7×7 | 6,297 | 6.86×10^10 |
| 8×8 | 13 | 7.48×10^11 |
| 9×9 | 2 | 1.92×10^14 |
| 12×6 | 171 | 9.57×10^12 |
| 16×4 | 4,685 | 5.89×10^11 |

Set 2:

| Puzzle | Solutions | Nodes for exhaustive |
|--------|----------:|--------------------:|
| 8×8 | 24 | 1.57×10^12 |
| 9×9 | 3 | 1.45×10^14 |
| 12×6 | (not run) | — |

**Calibration**: Brendan's complex theory predicted 3 solutions for
9×9 (set 1); empirical 2-3. **Match within ±33%** — Brendan's theory
is calibrated.

**The 9×9 cap is 1.5×10^14 nodes** = ~10^14 = vol-7's MaxSAT 45-cell
scale. Confirms 9×9 ≈ 45-cell-MaxSAT difficulty.

## Thread #14 — "Eternity2 information - Disclosure of the known 'solution'" (43 msgs, 2011-02)

Largely chatter about Tomy's stalled official prize submission process.
Some claims that the "known solution" was disclosed only to the
arbiter (the "Eternity Brain" company; never made public). **Johannes
Lindé's vague "invariants" claim** appears here — but he never
disclosed specifics. Already covered in vol-10 probe #5.

## Thread #15 — "UP_OR_LEFT_BORDER type" (41 msgs, 2007-08)

Discussion of **whether scanline goes top-to-bottom or
bottom-to-top, and corner choice**. Stertenbrink and Brendan converge:
**"depending on starting corner, search-space estimate ranges 8.2×10^16
to 7.6×10^28"** for hints.20.3 — 12 orders of magnitude variance just
in corner-choice. **The corner-choice is the strongest no-cost
optimization in a backtracker.**

## Thread #19 — "Going to be hard to wait till Monday!" (38 msgs, 2008-09)

Anticipation thread for the Sept 2008 prize submission deadline. No
algorithmic content. Worth noting only: **Verhaard officially
submitted a 467 to Tomy** before this deadline. Tomy's official
position on partial-score submissions never published.

## Thread #44 — "First Scrutiny over. No winner Yet !!" (28 msgs, 2009-01)

Tomy announced "Scrutiny phase 1 closed, no winner." Verhaard's 467
was the highest submitted. **The "$10,000 to Swedish woman" headline
turned out to be a misreading — it was actually a different award
related to Eternity I.** Tomy's official position: no partial-score
prize awarded.

## Thread #45 — "Sorry if this is already answered" (28 msgs, 2009-08)

Newbie FAQ thread. Useful for what the community considered well-
established by 2009:

- 467 = Verhaard's record.
- Hint utility debated; "many think hints make it harder."
- Brendan's complex theory considered authoritative.
- 9×9 sub-puzzles are the practical SAT/exhaustive-enumeration ceiling.

## Thread #56 — "Introducing myself and some of my experiences from 2 months of failures" (26 msgs, 2008-09)

Markus Zajc's intro post. He's a newcomer reporting **"possibility
matrix"** experience (his own term for MRV variable ordering).
Already covered in probe #5.

## Thread #58 — "While solving for a 14x14 - 196 solution" (26 msgs, 2022-05)

This is **directly about the internal 14×14 sub-problem**. Worth a
separate file later — for now: confirmed no one has ever found one,
and discussion of why even partial 14×14 solutions are hard.

## Thread #59 — "Difficulty of Eternity II puzzles of the same size" (26 msgs, 2025-04)

Reinout Annaert's thread. Discussion of **why two random puzzles of
the same size differ in difficulty** — i.e., **the difficulty
distribution among edge-matching puzzles is wide, and most are easier
than E2**. Selby-Riordan picked the hardest-known.

This means: vol-9 building heuristics that work on Brendan's puzzles
may **not generalize to E2** — Brendan's are samples from the typical
distribution, E2 is engineered tail.

## Thread #75 — "Survey of e2pieces.txt files" (Vasily V., 2023-03)

**Definitive reference for piece-data formats in the wild.** Vasily
catalogued multiple `e2pieces.txt` variants used by different
solvers, in different edge-orderings (NESW, NWSE, etc.). Listed
~10 variants on GitHub and in groups.io files area. Useful when
comparing solver outputs.

## Thread #51 — "Top Results" (Juraj Pivovarov, 2014-10)

Confirms 467 is **still the record as of October 2014**. 7 years
between Verhaard (2008) and any contest. Long stagnation.
