---
tags: [concept, propagator, ac, summary]
status: built
origin-vol: 23
---

# AC family — comparison and E2 verdicts

**Status**: `built` (reference summary, vol-23)
**Origin**: literature digest from constraint-programming.com/people/regin/pubs and related survey papers
**Files**: —

## The family at a glance

| algo | year | granularity | time worst | space | optimal? | E2 verdict |
|---|---:|---|---|---|---|---|
| AC-1 | Mackworth '77 | naive | O(e·n·d³) | O(e) | no | skip (historical) |
| [[ac3]] | Mackworth '77 | coarse | O(e·d³) | O(e) | no | **built** (vol-1) |
| [[ac4]] | Mohr–Henderson '86 | fine | O(e·d²) | O(e·d²) | yes (time) | skip (space, backtrack) |
| AC-5 | Van Hentenryck–Deville–Teng '92 | generic | depends | depends | conditional | skip (no E2 specialization) |
| [[ac6]] | Bessière '94 | fine, lazy | O(e·d²) | O(e·d + n·d) | yes (time) | skip (use ac2001) |
| [[ac7]] | Bessière–Freuder–Régin '99 | fine + metaknowledge | O(e·d²) | O(e·d + n·d) | yes (in checks) | skip (steal bidir idea) |
| [[ac2001]] | Bessière–Régin / Zhang–Yap '01 | coarse + residue | O(e·d²) | O(e·d) | yes | **BUILD NEXT** |
| AC-3rm | Lecoutre–Hemery '07 | coarse + lazy residue | not optimal | O(e·d) | no | maybe (after ac2001 A/B) |
| AC-* | Van Dongen '05 | configurable framework | — | — | — | skip (academic) |

Global / table:

| algo | year | what | E2 verdict |
|---|---:|---|---|
| [[gac-schema]] | Bessière–Régin '97 | GAC for any table constraint, O(\|T\|) | skip (table too big), but MDD-row variant interesting long-term |
| GAC-4 / GAC-MDD '14 | Régin '14 | improved table GAC | skip (same reason) |
| [[alldiff-regin]] | Régin '94 | matching-based GAC for AllDifferent | **candidate** (vol-24 stretch) |
| GCC | Régin '96 | global cardinality, network-flow GAC | skip (not our shape) |
| [[gacolor]] | Ansótegui '08 / Régin '94 base | per-color half-edge AllDifferent | **built** (vol-1) |

## The picker — flowchart

- "Is my constraint a generic binary table?" → [[ac2001]]
- "Generic binary, but constraint has cheap closed-form next-support?" → AC-5 / AC-7
- "Constraint is AllDifferent?" → [[alldiff-regin]]
- "Constraint is GlobalCardinality?" → Régin '96 GCC
- "n-ary table?" → GAC-Schema / STR2 / Compact-Table
- "Don't know / many small constraints?" → [[ac3]] is fine; upgrade to AC-2001 once you measure AC-3 dominates the profile.

## E2 stack — what's where

Currently in production:
- [[ac3]] — pairwise edge-matching, vol-1
- [[gacolor]] — Régin '94 alldiff per color, vol-1
- [[ns1-deficit]] — multiset equality, vol-12
- parity, island — vol-12 toggles
- Forward-checking via [[bitset-domain-rep]] — piece-uniqueness only at assignment time

Gap analysis:
1. **AC-3 inner loop is hot** (vol-16 profile). [[ac2001]] is the textbook drop-in fix. Estimated 2-10× engine speedup at zero correctness cost. **Top recommendation.**
2. **Piece-uniqueness is enforced weakly.** [[alldiff-regin]] adds GAC over the residual piece set. Safe under Blackwood (unlike AC-3/gacolor). Medium effort, uncertain prune-strength gain.
3. **Bidirectionality is unexploited** in AC-3 revisions. Cheap micro-optimization (steal-from-[[ac7]]); probably noise vs AC-2001.
4. **Table-GAC / MDD compression** of row-slices is a real research direction adjacent to [[mcgavin-engine]] and [[boundary-mps]] but is months of work, not a port.

## Soundness under [[blackwood-algorithm]] break-allowance

| propagator | sound under breaks? |
|---|---|
| AC-3 / AC-2001 / AC-6 / AC-7 | **no** — enforces strict edge-matching |
| GAColor | **no** — assumes exact perfect matching per color |
| NS-1 | **no** — multiset equality is end-state-exact |
| Régin AllDifferent (piece-level) | **YES** — piece uniqueness is strict in Blackwood too |
| Forward-checking on placed pieces | yes |

→ AllDiff-Régin is the only "strong global" candidate that survives the Blackwood regime. Worth prioritizing in any future BLACKWOOD_RAW work.

## References

- Bessière 1994, "Arc-Consistency and Arc-Consistency Again", AIJ 65(1)
- Régin 1994, "A Filtering Algorithm for Constraints of Difference in CSPs", AAAI
- Bessière, Régin 1995, "Using bidirectionality to speed up arc-consistency processing"
- Bessière, Régin 1997, "Arc consistency for general constraint networks", IJCAI
- Bessière, Freuder, Régin 1999, "Using Constraint Metaknowledge to Reduce Arc Consistency Computation", AIJ
- Bessière, Régin 2001, "Refining the Basic Constraint Propagation Algorithm", IJCAI
- Zhang, Yap 2001, "Making AC-3 an optimal algorithm", IJCAI
- Bessière, Régin, Yap, Zhang 2005, "An Optimal Coarse-grained Arc Consistency Algorithm", AIJ
- Lecoutre, Hemery 2007, "A Study of Residual Supports in Arc Consistency"
- Régin 2014, "Improving GAC-4 for Table and MDD Constraints", CP

## Linked concepts

- [[ac3]] [[ac4]] [[ac6]] [[ac7]] [[ac2001]] [[gac-schema]] [[alldiff-regin]]
- [[gacolor]] [[ns1-deficit]] [[bitset-domain-rep]] [[blackwood-algorithm]]
