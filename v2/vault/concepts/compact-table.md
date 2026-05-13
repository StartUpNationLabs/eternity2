---
tags: [concept, propagator, gac, table, candidate]
status: unbuilt
origin-vol: 23
priority: HIGH
---

# Compact-Table (Demeulenaere, Hartert, Lecoutre, Perez, Régin, Schaus — CP'16)

**Status**: `unbuilt`, **strong candidate — possibly better fit than [[ac2001]] for E2's actual constraint shape**
**Origin**: Demeulenaere et al., "Compact-Table: Efficiently Filtering Table Constraints with Reversible Sparse Bit-Sets", CP'16. The default propagator for table constraints in or-tools (Google) and OscaR.
**Files**: — (target: `crates/propagators/src/compact_table.rs`)

## Why I missed this on the first pass

The subagent's vault notes treated `gac-schema` as the Régin family's table-GAC endpoint and recommended skipping it. That was 1997-era thinking. The line continued: AC5-TC (Mairy 2012), STR (Ullmann 2007), STR2 (Lecoutre 2011), STR3 (Lecoutre 2015), MDD4R (Perez-Régin 2014), and finally **Compact-Table (CP'16)** which dominates all of them on a 1621-instance XCSP benchmark (avg 3.77× speedup vs the *virtual best of the second-best for each instance*, 9.11× vs STR2, 5.07× vs STR3). Lecoutre — co-author of STR2/STR3 — co-authored CT.

CT is *also* the propagator that won the MiniZinc Challenges via or-tools. This is not an obscure algorithm.

## Definition

CT maintains, per table constraint, a **reversible sparse bit-set** `currTable` over the rows of the table: bit `i` is 1 iff tuple `τ_i` is still a valid support given current domains.

Two precomputed static bit-sets per (variable, value) pair:
- `supports[x, a]` — bit `i` is 1 iff `τ_i[x] = a`.

Two operations per propagation round:
1. **updateTable()**: AND `currTable` with the union of `supports[x, a]` for surviving values of changed variables (or NOT-union of removed values, whichever is cheaper — *dynamic incremental-vs-reset choice*). Single word-level AND across `p = ⌈|T|/64⌉` words.
2. **filterDomains()**: for each `(x, a)` still in some domain, check `currTable ∩ supports[x, a] ≠ ∅` via `intersectIndex` (linear bit-AND walking only non-zero words). If empty → remove `a`. Residue: cache last non-zero word index; next call probes that word first.

The "reversible sparse bit-set" data structure is the cleverness: `index[]` permutation tracks which words are non-zero so iteration skips empty words; `limit` is the only `rint` that needs trailing on backtrack. State restoration is O(1) per word that became non-zero on the way down — no per-tuple bookkeeping.

## Complexity

- Time per propagation: O((p + r·d) · 64) bitwise ops where `p = ⌈|T|/64⌉` words. Tight in practice — single ANDs, no constraint checks once initialized.
- Space: `O(r·d·p)` for the `supports[x,a]` arrays + `O(p)` for `currTable`. **For E2:** if we encode the per-edge color-matching constraint as a table, the table is small (color set is tiny), but we have one per edge — 480 edges × tiny tables. The interesting case is encoding **bigger blocks** (piece-rotation × adjacent piece-rotation = up to 764×764 = 583k tuples per cell-pair edge, but only the valid color-matching ones, which is sparse).
- Backtrack: O(1) per modified word via the reversible `limit` + word swap.

## Why this might fit E2 better than [[ac2001]]

Our domain rep is **already** a bitset of (piece-rotation) tuples per cell ([[bitset-domain-rep]]). The constraint between adjacent cells is a table: pairs of (piece-rot, piece-rot) whose shared-edge colors match. Two options:

1. **Table-per-edge.** 480 edges, each a table of compatible (piece-rot, piece-rot) pairs. Table size bounded by 764 × (matching-color subset). Probably 10k-50k tuples per edge — small.
2. **AC-2001 + same_piece_rots LUT (what we have).** Coarse-grained loop with per-value `Last` residues.

The decision hinges on a measurement we don't yet have: how big is the average table per edge in tuples, and how does word-aligned AND-and-intersect compare to bitset-membership + LUT lookup? CT's word-level AND is *extremely* cache-friendly; on a sparse table it gets the bit-set sparse optimization for free.

## Caveats and limitations (from the paper itself)

- §7 "Contradiction with Previous Results": Demeulenaere et al. note that prior comparison papers (Mairy 2012, Perez-Régin 2014 MDD4R) had **slow STR2 implementations** that over-penalized STR. So CT's lead over STR/MDD lines is **smaller than earlier papers claimed** — they re-implemented everyone in OscaR for fairness. Honest scientific behavior, but the takeaway is: don't trust pre-2016 head-to-head numbers.
- 10 person-months of OscaR engineering went into the comparison. A naive port can lose to a tuned STR2/STR3.
- Hard requirement: positive table constraint (set of allowed tuples). Negative tables need a different formulation.
- The dynamic incremental-vs-reset switch (line 10 of CT alg) materially helps — the static incremental variant CTI is 9% slower on average, the static reset CTR is 46% slower. Implement the dynamic choice or take the hit.

## E2 applicability

**Strong candidate — re-rank above AC-2001 pending a sizing measurement.** Reasoning:

1. E2's color-matching constraint **is** a table constraint. The reason we use AC-3 is historical (1977 Mackworth), not because tables are wrong for this problem.
2. Reversible sparse bit-set maps cleanly onto our existing [[bitset-domain-rep]] worldview. We already trust bitset ANDs.
3. Vol-16 cleanup already isolated `same_piece_rots` precomputation as the AC-3 hot path — that LUT *is* a degraded version of `supports[x, a]`. CT is the principled version with proper sparse-set bookkeeping.
4. **Soundness under Blackwood**: same caveat as AC-2001 / AC-3 / gacolor — CT enforces exact edge matching, unsound under break allowance. Keep gated.

**Open question (vol-17 measurement, ~half day):** instrument the engine to count, per edge, the size of the compatible (piece-rot, piece-rot) tuple table. If ≤ 100k tuples per edge (i.e., ≤ ~1600 64-bit words for `currTable`), CT is clearly the right port. If ≥ 1M tuples per edge, table representation is too fat and AC-2001's coarse-grained iteration is more memory-economical.

**Integration sketch (vol-18, ~4 days)**:
1. Precompute per-edge table: enumerate compatible (piece-rot, piece-rot) tuples by shared-edge color.
2. Implement `RSparseBitSet`: `words: Vec<u64>`, `index: Vec<u16>`, `limit: TrailedInt`, `mask: Vec<u64>`.
3. Build `supports[cell, piece_rot]` static bit-sets.
4. Replace AC-3 inner revision with CT's `updateTable()` + `filterDomains()`.
5. Trail the `limit` field + word changes via existing engine trail.
6. A/B vs `joe_depth150_par` baseline.

## Linked concepts

- [[ac2001]] — coarse-grained alternative, possibly simpler to ship
- [[ac3]] — what we'd replace
- [[gac-schema]] — Régin's 1997 ancestor that CT supersedes
- [[bitset-domain-rep]] — our existing infra meshes naturally
- [[blackwood-algorithm]] — when to disable

## Linked memory

- `project_e2_vol16_closeout` — `same_piece_rots` LUT is the embryonic version of `supports[x, a]`
- `project_e2_vol12_engine_profiles`
