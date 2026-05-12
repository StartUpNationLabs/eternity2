# SAT thread — groups.io topic 47714407 (82 messages, 2011-02 → 2026-03)

Read end-to-end in vol-10 probe #7.

## Cast of characters

- **Marie / capiman26061973**: built the canonical CNF generator. 130,180
  variables, ~250M binary clauses, 4.5 GB CNF for full E2. Uses old
  Cryptominisat. Cannot solve full E2 but routinely solves Brendan's 6x6
  / 8x8 / 10x10.
- **andreas gammel**: friends with a top SAT expert who got his entire
  university department (20 people) E2 puzzles — they capped at 10×10.
- **Dieter von Holten (dvh)**: long-term SAT/SMT experimenter. Submitted
  E2 encodings to SAT Competition 2019/2020 (pp. 53 and 72 of the proceedings).
  Strongly recommends SMT (Z3, MiniZinc) over pure SAT for alldifferent.
- **Carles Mateu**: published academic paper with SAT/CSP encodings
  ([Springer 2012](https://link.springer.com/article/10.1007/s10601-012-9128-9)).
  Key finding: E2 is a GEMP-F (framed Generalized Edge-Matching Puzzle);
  the SAT phase-transition (hardest instances) for GEMP-F is at **17 colors
  for the inner core** — exactly E2's interior color count.
- **Marijn Heule (referenced)**: CMU professor. Authored the 2008 paper
  `http://www.cs.cmu.edu/~mheule/publications/eternity.pdf` — canonical SAT-
  encoding-for-edge-matching reference.
- **jgallicc (Jan 2023)**: working with Marijn to improve 2008 results, new
  constraints + search heuristics for large boards. No outcome reported.
- **Vlastislav W. (Vlasta)**: CNF instances for 12×16, 13×13framed, 16×16-
  minus-6×6 attached to the thread. Uses kissat, cryptominisat, or-tools,
  mallob (parallel). Custom commander-3/4 AMO encoding. Latest (Dec 2025):
  combining SAT + ILP (highs, scip, cplex, gurobi) for last 3 rows after SAT
  finds 16×13.
- **Akos Fekete**: explained SAT variable counting; fixing corners only
  reduces variables by 0.02–0.05%.
- **mulisak**: quantum-computing angle. Today's hardware has 156 qubits
  heavy-hex / 120 superconducting; even simple "puzzles" need >400 qubits;
  E2 set-cover formulation would need >3000 qubits. Far from feasible.
- **Peter McGavin**: doesn't use SAT, uses heavily-optimized backtrackers
  with scan-row paths and Brendan Owen's "complex theory" for path selection.
  Often the practical "answer" to whatever SAT can't reach.

## Concrete findings

### Scaling

- Full E2 CNF: **130,180 vars, ~250M binary clauses, 4.5 GB**.
- Modern SAT solvers (kissat, cadical 3, cryptominisat, or-tools, mallob)
  cap at roughly **10x10**.
- An entire SAT-expert university department (20 people) couldn't get past
  10x10 (gammel, 2011).
- Vlasta's best result (Mar 2026): inner 9×9 from interior pieces (extendable
  to 11x11 framed) found after **2,347,484 seconds CPU (~27 days)** and 943M
  conflicts on kissat. Confirms "10x10 is the practical SAT ceiling."
- 15×15framed has been attempted with SAT — never succeeded after 1 month.
- McGavin (no SAT, only backtrackers): solved Brendan's pieces_set_1 10×10
  in 2 years across hundreds of CPU cores. pieces_set_2 10×10 is still
  unsolved as of Mar 2026.

### Theoretical anchor (Mateu 2012)

> "For the E2 case things are even worse, as E2 is a GEMP-F (it has a
> frame), and for GEMP-F the phase transition (the hardest problems from a
> SAT perspective) is at 17 colors for the inner core, exactly those of E2."

This is a **published academic explanation** for why E2 is at peak SAT-hardness:
the Selby-Riordan generator engineered the inner-color count to sit exactly at
the SAT phase-transition peak. Independent confirmation of vol-7's M1 finding
"generator-engineered to defeat solvers."

### Why SAT doesn't beat backtracking on E2

dvh (Jan 2023 + Oct 2024): *"SAT can in principle solve edge-matching, but
current solvers and encodings are not competitive."* Edge matching is
**inherently combinatorial — SAT cannot bypass trial-and-error backtracking.**
A SAT solver is a "high-end, top notch, state-of-the-art search, but still
brute force search." Mixed Boolean-Integer (SMT, Z3, MiniZinc) is more
appropriate; "still not competitive."

### Brendan Owen's "complex theory" (McGavin verbatim)

Probably the **single most useful unimported algorithm** in the SAT thread.
PDF link: `https://groups.io/g/eternity2/files/Peter%20McGavin/complex_theory.pdf`

Inputs: (i) current state (partial board), (ii) distribution of edges on
remaining pieces, (iii) placement path.

Outputs:
- estimated # solutions reachable from current branch
- estimated # nodes in current branch (only this depends on placement path)

**Heuristic**: at each node, choose the piece maximizing
**(estimated solutions / estimated nodes)** — equivalently, the piece that
most-narrows-the-tree-relative-to-solution-density. This subsumes MRV
(most-restricted-variable) as a special case and adds a lookahead variant
(maximize the ratio after N pieces).

McGavin (Feb 2025) used complex theory to **pre-choose horizontal vs vertical
scan path for the 12×16 puzzle**: estimated tree size for horizontal scan was
slightly smaller. Empirical validation: solved 12×16 with 4 clues in 12 hours
on 22 backtrackers using the chosen path.

### Concrete progress on E2 sub-puzzles (Oct 2024 – Feb 2025)

McGavin solved (using backtrackers + complex theory + heuristics):

- **16×16 minus 6x7 hole, with all hints**, 8 backtrackers, 2-3 hours.
- **16×16 minus 6×6 hole, no hints (start piece only)**, 14 backtrackers
  across several PCs, 20 hours. Each backtracker 60–140M pieces/sec.
- **16×16 minus 6×6 hole, with 4 clues**, hundreds of cores for weeks
  (= "many times harder than without clues").
- **12×16 with 4 clues**, 20 backtrackers overnight (~12 hours).
- Several 12×16 with 4 clues solutions found, including some with 6 extra
  pieces placed beyond the 12×16 target.

McGavin estimates: "16×16 minus 6×6 in the middle with the 4 clue pieces has
~10^32 possible solutions, only one extending to a full 480/480 E2 solution."

Vlasta tested McGavin's solution as a starting point for full E2: best
extension was 458/480. So the 16×16-minus-6×6 attractor is not a stepping
stone to the 470+ regime.

### Vlasta's CNF instances (publicly attached to the thread)

12×16, 13×13framed, 16×16-minus-6×6. Uses commander-3/4 AMO encoding
(no recursion). ~71,000 variables for 12×16 with hints (~33% of full E2's
130,180). 16×16-minus-6×6 with all 60 border-piece clues reduces to ~80,000
variables (~39%) — still not solvable.

### Active 2026 SAT effort

Vlasta (Dec 2025): testing or-tools, mallob (massively parallel up to 128+
cores, distributed-across-computers), kissat with custom learnt-clause
export-to-file (`ccadical_set_learn(s, nullptr, 2, learn_cb)`) for **shared
hints between runs**. This is BOINC-style distributed SAT. No published
result yet.

dvh's 2026 conclusion (Mar 31): even successful SAT runs returned UNSAT for
most instances, and "the border ring is a trap — its the opposite of a
constraint." Recommends avoiding border-first encoding. Estimates minimum
49,500 vars for tighter encodings.

McGavin Mar 2026 closing thoughts (most current):

> "It seems to be extremely hard to find a 14×14 unframed solution using
> exactly the 196 interior pieces supplied with E2. But given the estimated
> vast number of solutions, I think it's within the bounds of possibility
> that someone could find such a solution using a combination of clever
> heuristics and powerful computers."

## What this changes for vol-9 / vol-11

1. **Vol-7's MaxSAT 45-cell result is the strongest SAT-style result in the
   entire community corpus** — McGavin solved a 6×6 hole = 36 cells with
   backtracker. Our 45-cell MaxSAT optimum is in fact **larger than anything
   the SAT crowd publicly solved**.
2. **Brendan Owen's "complex theory" should be imported** as a piece-selection
   heuristic and a path-selection meta-heuristic. Specifically the
   solutions/nodes ratio at each placement. The PDF is at
   `groups.io/g/eternity2/files/Peter%20McGavin/complex_theory.pdf`.
3. **The 17-color phase-transition fact is now formally attributed**
   (Mateu 2012). Citation for our notes; not a new build.
4. **Mateu's Springer paper should be in our reference set.**
5. **Avoid border-first encoding** in any new SAT/CSP work (dvh consensus).
6. **SMT (Z3) is the natural next-step beyond MaxSAT**, but the community
   confirms it's not competitive either. Lower priority than non-SAT
   approaches.

## Quotes worth keeping

- (Mateu 2012): "GEMP-F phase transition is at 17 colors — exactly E2's."
- (dvh 2024): "The border ring is a trap — it's the opposite of a constraint."
- (McGavin 2026): "Solutions to Brendan's 10×10 set_1 — likely dozens or
  hundreds more undiscovered solutions waiting to be found."
- (McGavin 2024): "Complex theory estimates the inner 14×14 with all 196
  middle E2 pieces and unconstrained borders has ~6×10^30 solutions without
  clues, ~2×10^19 with clue constraints. Yet finding any one is extremely hard."
