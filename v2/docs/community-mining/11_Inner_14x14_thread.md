# "While solving for a 14x14 - 196 solution" — topic 91318862 (26 msgs, 2022-05 → 2022-08)

## Headline: Al Hopfer's 2022 parity-correctness conjecture

**Al Hopfer (msg #1, 2022-05-24)** wrote:

> "I am pretty sure that to solve a 14×14 - 196 solution that the
> border edges of the 14×14 must be in parity correctness with the
> internal images on all 56 border pieces."

This is **exactly the multiset-equality propagator I proposed as NS-1
in vol-10**. Al independently arrived at it 4 years earlier from
empirical observation. He notes:

> "Example: of the 56 pieces, 6 like-image appear 6 pieces (two groups
> of 6) ... there are two border pieces that have only a single image,
> pieces 17 and 38 as examples."

This **also independently references pieces 17 and 38** (onesmallstep's
2026 Discord finding), showing this analysis was in the community
since at least 2022.

## Empirical confirmation: 14×14 sub-solutions exist quickly

**Vlastislav (Aug 2022)** solved a 13×13 internal corner + 4 columns of
border (96 cells) in **2 hours without hints, 160 hours with 4 clues**.
Note the *increase* in difficulty with hints — confirms vol-10 probe #6
finding that hints make partial-solving harder.

**Carlos Fernandez (Aug 2022)**: same 13×13+border in **4 minutes without
hints, 33 minutes with 4 clues**. Found 3 different solutions in <1 hour.
**Confirms: many 14×14-ish sub-puzzles exist with parity-correct boundary.**
The bottleneck is not finding them, it is finding the *right* one that
extends to full E2.

The 4-min vs 160-hr difference between Carlos and Vlastislav is solver-
implementation gap, not difficulty.

## What this changes for NS-1

**Strong evidence the multiset-equality propagator works**. Specifically:

- The 14×14 internal sub-problem is solvable in minutes with parity
  correctness on the inward-facing boundary.
- Carlos and Vlastislav both implemented something equivalent without
  formal naming.
- **Implementing NS-1 correctly should NOT cause vol-9's SA to slow
  down** — these threads confirm partial-solutions remain abundant
  once parity is enforced.

The challenge then becomes the **second-level constraint**: given a
parity-correct 14×14 inner solution, find the one whose inward-color
sequence matches some actual border-piece arrangement. This is a
**second multiset equality**, applied at the 1st-to-2nd-ring boundary.

The full **ring-boundary multiset chain** I proposed in NS-4 (vol-10)
is exactly the right level of decomposition. Al's 2022 thread
provides the empirical confirmation that the first level works.

## Quote worth preserving

Al Hopfer (msg #4): *"the border of the 14×14 must have the same
mixture (parity) of the internal images on all the 56 border pieces."*

This is the **community's natural language for the multiset-equality
invariant**.
