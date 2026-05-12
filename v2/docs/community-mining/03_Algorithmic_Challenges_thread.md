# "Algorithmic Challenges related to E2" — topic 47713411 (44 msgs, 2010-06)

## Headline
The thread that **defined the per-cell domain-reduction methodology**
the community now uses: ARC consistency + 3×3 SimpleSolverReduction.

## Concrete usable artifacts

- **doc_s_smith Java Eternity II Toolbox**: open-source, multiple
  versions referenced (V0.6, V0.7, V0.9alpha). Available in groups.io
  files area under doc_smith folder. Implements ARC consistency,
  node-count estimator, search-strategy finder.
- **Geoff Harris "A CSP View of Eternity 2.doc"**: in groups.io files
  area under Beginner Benchmark Puzzles. Formal CSP framing with
  Delphi code excerpt in message 5241.
- **capiman26061973 (Martin) recursive ARC**: applies ARC consistency
  repeatedly until fixed point (~4 iterations). Stores result as
  `PossibleCardsFile[piece][position][rotation] = 0` flag table.
- **istarinz (Tom) 3×3 SimpleSolverReduction**: for each hint, run a
  small 3×3 solver around it and remove from each cell's domain any
  piece-rotation not appearing in some 3×3 solution.
- **Carles Mateu PhD thesis** (formal CSP treatment, GEMP framing):
  `http://www.tesisenxarxa.net/TDX-0311109-172201/`.

## Empirical node-count benchmarks

**14×14 with 20 hints (hints.20.3)** — *complete enumeration*:
- doc_s_smith's solver: **29,481,602,025,785 nodes = 2.95×10^13** in
  **1,346,200 sec = ~15.5 days** on 1 core of an Intel Q9550 @ 3.4GHz.
- Result: **exactly 1 solution found** (= the original solution from
  which the puzzle was generated).
- doc_smith's pre-prediction was 1.7×10^13; actual 2.95×10^13. **The
  estimator is accurate within 2× on this 14×14 case.**

**14×14 with 12 hints (hints.12.1)**:
- 821M nodes / 38s scan + 326s strategy finding = 364s overall.

**14×14 with 12 hints (hints.12.2)**:
- 1.24B nodes / 52s scan + 258s strategy = 310s overall.
- Rowscan from optimal corner: 2.03B nodes / 81s — faster than
  strategy-found algo here.

## Two competing node-count estimators

- **Brendan Owen's "Complex Theory"**: predicts ~10^45 nodes for
  full E2 (uniformity-of-edge-distribution argument).
- **doc_s_smith's estimator** (Java toolbox): predicts ~10^50 nodes
  for full E2. **5 orders of magnitude higher**.

doc_s_smith hypothesizes the gap is **parity-related** but never
formalized it. **Unresolved question in the corpus**: which estimator
is right? This matters: if Brendan's is right, full enumeration is
"only" ~10^45 nodes; if doc_smith's is right, it's 10^50.

## ARC-consistency progression on hints.20.3

Three independent implementations (doc_smith, Tom, Martin) reach
nearly identical domain-reduced tables. Snapshot of cell-by-cell
remaining-piece counts (out of 728 = 196 interior × 4 rotations):

| Cell | Before ARC | After ARC | After 3×3-SimpleSolver |
|------|-----------:|----------:|----------------------:|
| (interior, hint-adjacent) | 728 | ~30-100 | ~10-50 |
| (interior, far from hint) | 728 | ~500-720 | ~480-680 |
| (corner) | 51 | 1-15 | 1-15 |
| (edge) | 51 | 10-50 | 10-50 |

**At one specific cell (14,6), all three implementations independently
proved exactly 1 candidate.** That cell is fully determined by static
constraint propagation alone — no search needed there.

## "Find positions where ARC removes the most" heuristic

Martin (msg #15) builds a database mapping (field_a, field_b) pairs to
the number of impossible 2-piece combinations. Snippet:

```
F  2/F 17:    11081     2740    13821      801 -> R0R1
F 17/F 32:    11077     2744    13821      801 -> R1R0
F 29/F 31:     1155      245     1400      825 -> R1R0
F 29/F 61:    90389    10863   101252      892 -> R1R2
F 29/F 44:   108914    10237   119151      914 -> R1R2
```

Interpretation: ratio `Impossible / (Impossible+Unknown) * 1000`.
Higher = more pruning power. **Cells 29, 44, 61, 31 are the
highest-leverage starting points** for ARC under Martin's metric.
Worth verifying on our piece set.

## Linkage to vol-7/9/10

- Vol-9's Eulerian propagator: produced 0 pruning. The ARC consistency
  here produces ~80,000 removed (piece, position, rotation) triples on
  a 14×14 with 20 hints. **ARC is universally the strongest static
  propagator** — vol-9 should verify its ARC implementation is at
  least as strong as Martin's.
- Vol-7's MaxSAT 45-cell result: doc_smith's full-enumeration 14×14
  with 20 hints in 15.5 days on 1 core is in the same general
  difficulty class. Our MaxSAT optimum is rigorous; their result is
  brute-force-exhaustive. Comparable strength.
- Vol-10 probe #4 (pieces 17, 38, 62 forcing): these come *for free*
  from a complete ARC pass; they should already be in Martin's
  reduction tables. Vol-9 propagators inheriting from ARC should
  surface them automatically.

## Open question for vol-11

Can we reproduce Martin's recursive-ARC `PossibleCardsFile` table on
the canonical E2 piece set (no hints, no auxiliary constraints)?
This is the **clean static AC-3 baseline** every solver should agree
on. If our solver-engine ARC differs from his, we have a bug or a
gap.
