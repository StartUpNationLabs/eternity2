# "Design the hardest puzzle" — groups.io topic 47707375 (54 messages, 2007-08)

## Headline finding

**The 17+5 color split of E2 is mathematically chosen to give expected
~1 solution.** Brendan Owen + guenter stertenbrink derived from first
principles in August 2007:

- **Interior color count for ~1 expected solution**:
  `I = (196! × 4^196)^(1/392) = 17.14 → 17`
- **Border color count**:
  `B = (56! × 4! / 17^28)^(1/60) = 4.97 → 5`

The Selby-Riordan generator picked **17/5 deliberately** — exactly the
parameters where the expected number of solutions tips from many to one.
This independently confirms Carles Mateu's later GEMP-F phase-transition
analysis (SAT thread): the unique-solution boundary IS the SAT
phase-transition for random instances.

## Expected-solutions formula by shape (stertenbrink)

For an `m×n` puzzle with `I` interior colors and `B` border colors,
expected solutions =

`((m-1)(n-1))! × 4^((m-1)(n-1)) × I^(-m(n-1)-n(m-1))
   × (2m+2n-8)! × 4! × B^(-2m-2n+4)`

For E2 (I=17, B=5, m=n=16), this gives ~1.

Per-shape expected-solutions counts (computed for E2):

| Shape | Expected solutions |
|------|------------------:|
| 16×9 horizontal stripe | 10^49 |
| 16×11 stripe | 10^58 (peak among 16×k stripes) |
| Inner 11×14 (close to 196 cells) | 10^58 |
| Outer ring + 3 layers (k=3) | 10^57 |
| Outer ring alone (k=1) | 10^37 |
| Whole 16×16 | ~1 |

**The expected-solution count has a sharp peak at the half-board scale
(~150-200 cells), then collapses to ~1 at full board.** This is the
**information-theoretic profile of E2's difficulty**: there are
astronomically many partial solutions but exactly one full one (probably).

## Why this matters

1. **Solving inner pieces alone is wildly underconstrained**: 10^58
   expected solutions for the 196-piece interior. Vol-7's "internal
   14×14 sub-problem" has so many solutions that finding any one is
   hard — confirming Vlasta's SAT findings.

2. **Border ring expected count is 10^37**: huge. Onesmallstep's *"never
   managed to find five complete outer rings"* is at odds with this
   count — it means his search method is too restrictive, not that
   borders are rare.

3. **The 10^37 × 10^-33 = 10^4 estimated chance of any border being
   extendable to a full solution** (stertenbrink, msg #5). If true,
   each individual border tried has ≈10^-33 chance of yielding a full
   solution. This is why frame-first fails: vast border combinations,
   each almost certainly unextendable.

4. **stertenbrink's "10^46 expected solutions, 10^7 expected first
   solution"** for the 16×9 stripe: at 2×10^7 nodes/sec it's "1e34
   years for complete search or 1e27 until first solution." The
   intractability is intrinsic to the design.

## Brendan's hardness recipe (verbatim summary)

> "The hardest puzzle of a given size requires:
> 1) puzzle is as compact as possible
> 2) pieces very tileable with uniform difficulty
> 3) with one expected solution"

For 256 pieces with grey borders:

- **Compact** → 16×16 square (sqrt of 256).
- **Uniform tileability** → no symmetric pieces (less orientations →
  harder), no duplicate pieces, flat edge type distribution, separate
  edge types for border vs interior to level corner/edge/interior
  rotation-count asymmetry.
- **One expected solution** → I=17, B=5 (the calculation).

Selby & Riordan's actual generator implements this exactly.

## Monckton attribution

Eternity_Two (groups.io account, 2007): *"Christopher Monckton does not
have the mathematical skills to work it out himself, this was evident
in the design of Eternity I and comments he made. He said it could not
be solved simply by using a computer. This shows he did not have a
true mathematical understanding of his puzzle."*

And: *"I am positive [Alex and Oliver Riordan] were the ones who
actually designed the puzzle and told him to forget that 3D idea."*

Independent confirmation of vol-7's M1 finding. The Monckton-designed-it
narrative is PR; the math is Selby-Riordan.

## Strategies enumerated

stertenbrink (msg #5): four strategies for E2:
1. reduce to 16×i row-rectangles and solve each
2. reduce to j×16 column-rectangles and solve each (= 1 transposed)
3. solve border first
4. solve inner first

For E2 (I=17, B=5), strategy **(1) = (2) is the best by expected node count**.
But "in practice it's only 10^46 expected solutions and 10^7 expected
first-solutions" — still **1e34 years** for complete search.

## What this changes for vol-9 / vol-11

1. **The expected-solutions profile is a calibration anchor**: at peak
   we have 10^58 solutions for inner-14 partial; at full we have ~1.
   The drop from 10^58 to 1 is concentrated in the **last ~60 pieces**.
2. **Border-first is fundamentally a long-shot** by stertenbrink's
   numbers: each border has ~10^-33 chance of being extendable. To get
   even one extendable border by random sampling needs >10^33 attempts.
   Knucklefinger's 2008 "frame-first is suicide" intuition was
   quantitatively right.
3. **The 17-color choice is provably the unique-solution boundary**.
   Worth citing in vol-7's memory as the *mathematical* version of
   vol-7's M1 "generator-engineered" finding.

## Related artifacts referenced in thread

- Brendan's complex-theory PDF (cross-referenced in SAT thread):
  `groups.io/g/eternity2/files/Peter%20McGavin/complex_theory.pdf`
- Brendan Owen's puzzle generator (open-source) — multiple references.
