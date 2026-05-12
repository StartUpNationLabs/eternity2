# "Two-stage solution process" — topic 112789366 (32 msgs, 2025-05)

## Marcus Garvie's binary LP approach

Marcus Garvie (university professor of applied math) is solving E2 via
**binary linear programming feasibility** (no objective function), using
**IBM CPLEX or Gurobi**, controlled from MATLAB. Wants to factor into
two stages: solve border, then interior. This is the **most recent
non-backtracker approach in the corpus**.

David Barr's response (msg #2): **"there are very many boundary
configurations (with all pieces matching) which will not be able to
contain a valid arrangement of interior pieces"** — confirming that
two-stage decomposition doesn't help.

## Brendan Owen returns (msg #12, 2025-05-16)

After ~14 years of inactivity, Brendan himself responds. Confirms:

- "I believe we have developed a robust mathematical model capable of
  answering questions about the expected search space size and the
  number of solutions for all the approaches discussed in this thread."
- "The mathematical model has consistently demonstrated a strong match
  between predicted search space size and empirical results."

And lays out the **definitive numerical model** for E2 (msg #14, 2025-05-18):

| Quantity | Value |
|----------|-------|
| **Number of distinct outer frame configurations** | 10^38 |
| **Number of inner 14×14 solutions (196 pieces, ignoring frame)** | 10^34 |
| **Nodes searched to find one inner 14×14 solution** | 10^59 |
| **Average inner-130-piece partial-solutions per 196-piece solution** | 10^25 |
| **Conditional P[outer frame fits given inner solution]** | 10^-27 |
| **Conditional P[inner solution fits given outer frame]** | 10^-27 |

**The product 10^38 × 10^34 × 10^-27 ≈ 10^45**, which is the search-space
order vol-7 was estimating. **This is the complete factorial decomposition**.

## Why two-stage doesn't help

- **Border-first**: 10^38 borders × 10^-27 chance-of-fitting-an-interior =
  10^11 expected viable borders. Even iterating through 10^11 viable
  borders to find one is intractable.
- **Interior-first**: 10^34 inner-solutions × 10^-27 chance-of-fitting-a-
  border = 10^7 expected viable inner-solutions. But finding one inner
  solution alone takes 10^59 nodes, so we never even reach the matching
  step.

**The asymmetric factorization confirms vol-7's "pinned-perimeter
plateau" empirical finding**: with a random border pinned, only one in
~10^27 borders can be extended to a full solution. Vol-7's saturation
at 449-454 with a pinned border is consistent — most random borders
are simply unextendable.

## Brendan's view on hints (msg #12, 2025)

> "Frankly, I have never paid much attention to the hints provided after
> completing the modelling, as I did not expect anyone to find a
> solution. My personal view is that the hints primarily serve to give
> people false hope and provide the sales team with a mechanism to sell
> more smaller puzzles."

This **independently confirms vol-10 probe #6 finding** that Blackwood,
onesmallstep, and reinout_ all observed: the 5 official hints may be a
hindrance more than a help. Brendan, the puzzle-design analyst, views
them as primarily commercial.

## Lisa Drapeau's "designed-fair-E2" project

Lisa is building **a deliberately fair variant** to study what an
"optimal" puzzle looks like:
- 14×14 internal, 16×16 overall
- 10 internal colors (vs E2's 17), equal counts
- All pieces unique 4-tuples
- No symmetric / duplicate / mirrored / rotated-permutation pieces
- Distinct color set for border interface

**This is a synthetic benchmark** that mirrors Brendan's "designed
hardness" with knobs explicit. Worth fetching if available.

## What this changes for vol-9 / vol-11

- **The asymmetric 10^38/10^34 split between outer and inner** explains
  why no two-stage decomposition works. **Stop building two-stage
  algorithms**.
- **Brendan's complete model is in the corpus** and gives precise
  predictions for every search-order variant. **Vol-11 candidate**:
  port Brendan's `complex_theory.c` (referenced in 06) to Rust as a
  pre-search predictor for vol-9's SA, calibrating expected difficulty
  per piece-set candidate.
- **Marcus's LP approach is worth following** even though it's slow now.
  If CPLEX/Gurobi scales differently from SAT (which caps at 10×10),
  it could be the next research direction. Worth checking back in a
  few months for Marcus's results.

## Direct quote worth preserving

Brendan (msg #12): *"I have studied search spaces for other polyform
puzzles, I found this simple square-based edge-matching puzzle
significantly easier and more accurate to model."*

This is **Brendan saying E2 is *easy to analyze* but hard to solve** —
the structural model is well-understood; only the constants are
astronomical.
