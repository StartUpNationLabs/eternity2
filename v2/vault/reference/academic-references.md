---
tags: [reference, academic, bibliography]
date: 2026-05-20
---

# Academic References — Eternity II and Related Techniques

A curated bibliography of academic papers relevant to our work. Grouped by topic. For community (non-academic) work, see [[community-e2-history]].

> Last refresh: 2026-05-20 (vol-188 web-enrichment pass).

---

## Complexity theory

### Demaine & Demaine 2007 — NP-completeness of edge-matching

**Citation**: Demaine, E.D., Demaine, M.L. (2007). "Jigsaw Puzzles, Edge Matching, and Polyomino Packing: Connections and Complexity." *Graphs and Combinatorics* 23, 195–208.

**Key result**: Signed and unsigned **edge-matching square-tile puzzles are NP-complete**, equivalent to jigsaw and polyomino packing. The seminal result establishing E2's worst-case hardness.

**Why we cite**: foundational. Justifies why no polynomial-time algorithm exists for E2 unless P = NP. Implies any sub-exponential approach must exploit structure, not generality.

- arXiv: [erikdemaine.org/papers/Jigsaw_GC/](https://erikdemaine.org/papers/Jigsaw_GC/)
- Springer: [link.springer.com/article/10.1007/s00373-007-0713-4](https://link.springer.com/article/10.1007/s00373-007-0713-4)

### Demaine et al. 2019 — Edge matching with inequalities

**Citation**: "Edge Matching with Inequalities, Triangles, Unknown Shape, and Two Players." JCDCG³G 2019.

**Key result**: Variants of edge-matching:
- **Inequalities** between adjacent tiles: NP-complete for strict, polynomial for nonstrict.
- **Triangular edge matching**: 3 types; one polynomial, two NP-complete.
- **Allowing rotations** in one-row puzzles: NP-hard.

**Why we cite**: refines the complexity landscape. Useful when considering relaxations or variants in our own work.

- arXiv: [arxiv.org/abs/2002.03887](https://arxiv.org/abs/2002.03887)

### "Edge-matching Problems with Rotations" 2017

**Citation**: arXiv 1703.09421.

**Key result**: Edge-matching with rotations is NP-hard even in restricted settings.

- arXiv: [arxiv.org/abs/1703.09421](https://arxiv.org/abs/1703.09421)

---

## E2-specific solver work

### Salassa, Vancroonenburg, Wauters, Della Croce, Vanden Berghe 2017 — MILP + Max-Clique

**Citation**: "MILP and Max-Clique based heuristics for the Eternity II puzzle." arXiv 1709.00252.

**Key contributions**:
- Original **MILP formulation** for E2.
- Novel **Max-Clique formulation** as alternative.
- Two MILP-based constructive heuristics for initial solutions.
- Multi-neighbourhood local search "competitive with state-of-the-art procedures."
- Published new hard-to-solve benchmark instances as byproduct.

**Why we cite**: closest peer to our [[corpus-restricted-region-mip-locked]] and [[lifted-lp-column-gen-per-piece]] work. Their MILP and our MIP rigidity analysis target related questions from different angles. Their max-clique formulation is an idea we have NOT explored.

- arXiv: [arxiv.org/abs/1709.00252](https://arxiv.org/abs/1709.00252)

### Heule 2008 — SAT encoding for edge-matching

**Citation**: "Solving edge-matching problems with satisfiability solvers." (Marijn Heule, CMU.)

**Key result**: Canonical SAT-encoding reference for edge-matching puzzles. Variables: piece-position-rotation; clauses: edge-compatibility, piece-uniqueness, position-uniqueness.

**Status today**: SAT solvers cap at **10×10 sub-puzzles** in practice — empirically confirmed across kissat, cryptominisat, cadical 3, or-tools, mallob (parallel) over 15+ years of community SAT effort. See [[community-e2-history]] §SAT.

**Why we cite**: ground truth for SAT-encoding scaling. Establishes that pure SAT is not the path to 480.

- Author page: [cs.cmu.edu/~mheule/](https://www.cs.cmu.edu/~mheule/)
- Semantic Scholar: [Solving edge-matching problems with satisfiability solvers](https://www.semanticscholar.org/paper/Solving-edge-matching-problems-with-satisfiability-Heule/5959a7f20f3f06fad2e1a8dc0ef00924892d865f)

### Mateu, Hamadi 2012 — GEMP-F phase transition

**Citation**: Mateu, Hamadi. "Edge matching puzzles as hard SAT/CSP benchmarks." *Constraints* journal, Springer 2012.

**Key result**: E2 is a **GEMP-F** (framed Generalized Edge-Matching Puzzle). The SAT/CSP **phase transition** for GEMP-F is at **17 interior colors** — exactly E2's design. Formal anchor for why the puzzle is calibrated to peak difficulty.

**Why we cite**: independently confirms Brendan Owen + stertenbrink's 2007 community derivation that I=17, B=5 are chosen for ~1 expected solution. The phase-transition view explains why E2 is hard not just because of NP-completeness but because of *parameterized hardness peak*.

- Springer: [link.springer.com/article/10.1007/s10601-012-9128-9](https://link.springer.com/article/10.1007/s10601-012-9128-9)
- Extended version: [repositori.udl.cat/.../Edge Matching Puzzles as Hard SAT/CSP Benchmarks](https://repositori.udl.cat/server/api/core/bitstreams/31b80903-c28c-4d6f-88a9-606e5cb08095/content)

### "How Hard is a Commercial Puzzle: the Eternity II Challenge"

**Citation**: Ansótegui, Béjar, Fernández, Mateu (UdL).

**Key result**: One of the earliest academic analyses of E2 specifically as a hard CSP benchmark. Various encodings tested.

- Repositori UdL: [How Hard is a Commercial Puzzle](https://repositori.udl.cat/server/api/core/bitstreams/0b6533fe-54e5-4070-85fe-80f7d35837d8/content)

### Other E2 academic work (chronological)

- **Niang 2011** (Concordia MASc): "Solving the Eternity II Puzzle using Evolutionary Computing Techniques." [PDF](https://spectrum.library.concordia.ca/id/eprint/7487/1/Niang_MASc_S2011.pdf).
- **2012 Springer chapter**: "Evolutionary Genetic Algorithms in a Constraint Satisfaction Problem: Puzzle Eternity II."
- **"Fast Global Filtering for Eternity II"** — variable-ordering work.
- **"A general variable neighborhood search approach for the resolution of the Eternity II puzzle"** — VNS metaheuristic.
- **"A Guide-and-Observe Hyper-Heuristic Approach to the Eternity II Puzzle"** — hyperheuristic.
- **"Automatically Generating and Solving Eternity II Style Puzzles"** (2018, Springer).

**Aggregate**: the academic record on E2 specifically is ~10 papers across 2008-2018. The community work (groups.io, McGavin, Blackwood) outperforms the academic best — McGavin's 469 is unmatched by any academic-published solver. The phase-transition formal anchor (Mateu) and the NP-completeness baseline (Demaine) are the most influential academic results; the rest are individual solver attempts that don't beat Blackwood's algorithm.

---

## Selby+Riordan (original Eternity I and design influence on E2)

### Selby's solver description (Eternity I, 2000)

**Source**: Alex Selby's website — `archduke.org/eternity/method/desc.html` (HTTP 403 from web fetch; historical content).

**Brief**: Alex Selby and Oliver Riordan used **probability theory + clever combinatorial reductions** to solve the original Eternity I puzzle in 7 months (claimed the £1M prize). The key insight: identify *combinatorial weaknesses in the puzzle design* and exploit them to dramatically reduce the search space.

**Why we cite**: the Eternity I→II transition was specifically engineered (by Selby+Riordan themselves, hired by TOMY) to remove their original weaknesses. The 17/5 color split derived in 2007 is the result of that engineering — they made E2 *deliberately resistant* to the kind of weakness-exploit that won them Eternity I.

- Plus Maths article: [plus.maths.org/content/forever-rich](https://plus.maths.org/content/forever-rich)
- Oliver Riordan's homepage: [people.maths.ox.ac.uk/~riordan/](http://people.maths.ox.ac.uk/~riordan/)
- Wikipedia: [en.wikipedia.org/wiki/Eternity_II_puzzle](https://en.wikipedia.org/wiki/Eternity_II_puzzle)

---

## Constraint programming techniques we use

### Régin 1994 — GAC for alldifferent

**Citation**: Régin, J.-C. "A filtering algorithm for constraints of difference in CSPs." AAAI 1994.

**Key result**: Generalized Arc Consistency for the AllDifferent global constraint via maximum bipartite matching + Berge's theorem on alternating paths. Build value graph, find max matching, mark edges as "vital" / "removable", prune.

**Why we cite**: this is [[gacolor]] (per-color alldiff) — our most powerful global propagator. The structure of E2 (each color appears in bounded supply) makes alldiff per color a natural fit.

- Survey: [The alldifferent Constraint: A Survey](https://www.andrew.cmu.edu/user/vanhoeve/papers/alldiff.pdf) (van Hoeve)

### Demeulenaere, Hartert, Lecoutre, Perez, Perron, Régin, Schaus 2016 — Compact-Table

**Citation**: "Compact-Table: Efficiently Filtering Table Constraints with Reversible Sparse Bit-Sets." CP 2016, Toulouse.

**Key result**: Bitwise algorithm to enforce GAC on table constraints. Uses reversible sparse bit-sets; tuples invalidated incrementally on value removals via bit-set operations. State of the art for table propagation.

**Why we cite**: relevant for any extensional encoding of E2 (e.g., precomputed 2×2 patch tables). Our [[ac3]] and [[gacolor]] are not table-based; if we ever moved to a table encoding, this is the algorithm to use.

- arXiv: [arxiv.org/abs/1604.06641](https://arxiv.org/abs/1604.06641)

### Gent, Miguel — GAC for AllDifferent empirical survey

**Citation**: "Generalised arc consistency for the AllDifferent constraint: An empirical survey." Artificial Intelligence Journal.

**Why we cite**: empirical comparison of AllDifferent propagation methods. Validates that Régin-style GAC is the right choice for our use case (small-supply per-color alldiff).

- Semantic Scholar: [Generalised arc consistency for AllDifferent: An empirical survey](https://www.semanticscholar.org/paper/Generalised-arc-consistency-for-the-AllDifferent-An-Gent-Miguel/cea6e58cd5457c7fa35af194d62d020876cd5fc8)

### Recent (2023) — Bitwise GAC for AllDifferent

**Citation**: "A bitwise GAC algorithm for alldifferent constraints." IJCAI 2023.

**Why we cite**: recent improvement on AllDifferent GAC via bitwise representation; potentially useful if we ever re-instrument [[gacolor]].

- ACM: [dl.acm.org/doi/abs/10.24963/ijcai.2023/221](https://dl.acm.org/doi/abs/10.24963/ijcai.2023/221)

---

## LP/SDP for puzzle assembly

### Kovalsky, Basri, Glasner 2014 — LP for jigsaw assembly

**Citation**: Kovalsky, S., Basri, R., Glasner, D. "Solving Jigsaw Puzzles with Linear Programming."

**Key result**: A "global approach" — LP/SDP formulation where the entire puzzle assembly is one optimization, not sequential placement. Demonstrated on synthetic and image puzzles.

**Caveat**: did NOT apply to Eternity II. Image-puzzle compatibility is real-valued (gradient continuity); E2 edge colors are discrete. The continuous-LP formulation doesn't translate directly. But the *idea* of global optimization rather than sequential placement is relevant.

**Why we cite**: a different paradigm — supports our [[lifted-lp-column-gen-per-piece]] thinking. Could inspire an SDP relaxation for E2 (an open item in our SYNTHESIS_VOL_188 §6.2).

- PDF: [shaharkov.github.io/projects/GlobalPuzzles.pdf](https://shaharkov.github.io/projects/GlobalPuzzles.pdf)

---

## Topics we should look into more (gaps)

These are areas where academic work exists but we haven't pulled the references into the vault yet:

- **B&P&C (branch-and-price-and-cut) for combinatorial puzzles** — vol-52 designed a per-piece column-gen formulation; full B&P&C literature could refine it.
- **SDP relaxations for QAP / NP-hard assembly** — relevant for our open §6.2 SDP-relaxation idea.
- **Recent (2023+) SAT preprocessing for hard structured instances** — Vlasta's kissat work + Mallob parallel runs are at the community frontier.
- **Reinforcement learning for value-ordering on combinatorial CSP** — our [[learned-value-order]] work hit a transfer ceiling at vol-28; modern RL for CSP (e.g., neural-guided value ordering) is an open area.
- **Lattice-based / group-theoretic formulations of edge-matching** — our σ-cycle indecomposability ([[sigma-cycle-universal-indecomposable]]) is a group-theoretic finding without a published precedent we've located.

---

## Linked

- [[community-e2-history]] — community (non-academic) history
- [[community-corpus]] — our corpus of decoded community boards
- [[ac3]], [[gacolor]] — our CP propagators
- [[learned-value-order]] — our RL/ML work
- [[lifted-lp-column-gen-per-piece]] — our LP/column-gen work
- [[sigma-cycle-universal-indecomposable]] — our group-theoretic finding
- [[corpus-restricted-region-mip-locked]] — our MIP rigidity probe
