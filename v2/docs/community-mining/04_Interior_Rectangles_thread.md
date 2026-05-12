# "Interior Rectangles" — topic 47710285 (40 msgs, 2008-03)

## Headline

Brendan Owen computed estimated time-to-find-one-solution for
rectangular sub-puzzles **using the 196 interior pieces of E2**.
Reveals a **phase transition** at specific length-width combinations
beyond which the sub-puzzle has many solutions vs. having only ~2.

## The intractability table

For finding ONE rectangle filling using only interior pieces (and the
196 piece pool):

| Width × Height | Time |
|---------------:|-----:|
| 13×14 | 0.62 days |
| 7×27 | 1.67 days |
| 11×17 | 27.9 days |
| 6×32 | 51.9 days |
| 9×21 | 79.7 days |
| 4×49 | 761 days |
| 10×19 | 2,646 days |
| 5×39 | 3,917 days |
| 8×24 | 8,680 days |
| 12×16 | 26.2 million days |
| 7×28 | 200M days |
| 13×15 | 6.14×10^11 days |
| **14×14** | **4.44×10^13 days** (∼10^11 core-years) |

**The internal 14×14 is genuinely intractable at the random-search level.**
This is the same sub-problem onesmallstep says "nobody has solved in
19 years." Brendan's 2008 prediction perfectly explains why.

## Phase transition: "about two solutions" vs "many solutions"

For width-N interior-piece rectangles, there is a sharp length cutoff:

| Width | "About 2 solutions" if length ≤ | "Many solutions" if length ≥ |
|:-----:|---:|---:|
| 2 | 19 | 20 (~1 sec each) |
| 3 | 21 | 22 (~12 hours each) |
| 4 | 20 | 21 (~50 years each) |
| 5 | 18 | 19 (~10 thousand years each) |
| 6 | 16 | 17 (~500 thousand years each) |
| 7 | 14 | 15 (~10 million years each) |

**This phase transition is the expected-unique-solution boundary**
applied to sub-rectangles. The cutoff length × width product is
roughly **constant ≈ 80-100 cells** (e.g., 7×14 = 98, 6×16 = 96,
5×18 = 90, 4×20 = 80, 3×21 = 63). Beyond ~80-100 cells, sub-puzzles
become unconstrained.

**Operational implication**: any spiral-in or interior-first
decomposition that crosses this ~96-cell boundary enters a regime
where the sub-puzzle has many solutions, but each one is
exponentially hard to find. **The "hard middle"** of E2 is precisely
this regime.

## Linkage to other findings

- xtal's shell ladder (probe #5 C-1): shell 4 = 192 cells; the wall
  is at exactly the regime Brendan's phase transition predicts is
  "many solutions, very slow to find any one."
- Internal 14×14 = 196 cells, well into the unconstrained-but-hard
  regime. Brendan's 4.4×10^13 days for one solution matches onesmallstep's
  19-year-no-success empirical finding.
- The 6×6-hole / 7×7-hole / 6×7-hole work by McGavin in Oct 2024:
  6×6 = 36 cells (highly constrained), 6×7 = 42 cells, 7×7 = 49 cells.
  All well within the "about 2 solutions" tractable regime — explains
  why McGavin could solve these.

## What this changes

- The "internal 14×14" sub-problem from vol-10 NS-10 is now properly
  calibrated: **~10^11 core-years to find any one by random search**.
  Only a structural insight or massively parallel + lucky search can
  succeed.
- The phase-transition cutoff at ~96 cells is a **third stall point**
  beyond Hopfer's 202-206 and the shell-3-to-4 wall: any solver that
  attempts to fill an interior rectangle ≥96 cells via backtracking
  enters the intractable regime.
- For vol-9's Verhaard SA: the natural sub-set size of "180-190
  pieces" is well past 96 cells. So Verhaard's "swap-anneal a
  180-piece subset to be tileable" is operating in the intractable
  regime *by construction*. This may explain why Verhaard's method
  capped at 467: the metric (count-of-2×2-sub-tilings) is locally
  useful but the sub-puzzle being approximated is fundamentally hard.
