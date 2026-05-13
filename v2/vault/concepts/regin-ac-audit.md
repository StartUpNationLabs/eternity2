---
tags: [concept, audit, ac, propagator]
status: research
origin-vol: 23
---

# Régin AC family — first-hand paper audit

**Status**: research note, corrects and supplements the agent-generated [[ac2001]], [[ac4]], [[ac6]], [[ac7]], [[alldiff-regin]], [[gac-schema]], [[ac-family-comparison]] pages.
**Source PDFs read first-hand (2026-05-13)**:
- Régin, "A filtering algorithm for constraints of difference in CSPs", AAAI'94 (alldiff.pdf) — full read
- Bessière, Régin, Yap, Zhang, "An Optimal Coarse-grained Arc Consistency Algorithm", AIJ 2005 (aij05-ac2001.pdf) — full read
- Régin, "Maintaining arc consistency algorithms during the search with an optimal time and space complexity", CP'05 (optmac.pdf) — partial read (sections 1-5)
- Lhomme & Régin, "A Fast Arc Consistency Algorithm for n-ary Constraints", AAAI'05 (fastGAC.pdf) — full read
- Demeulenaere et al., "Compact-Table: Efficiently Filtering Table Constraints with Reversible Sparse Bit-Sets", CP'16 (CompactTable.pdf) — full read

## Corrections to the agent's notes

### 1. The "70% of single-thread time in AC-3" number in [[ac2001]] is unsourced
I cannot find this figure in vol-16 closeout memory or any session journal. The subagent likely fabricated it from generic "AC-3 is the hot path" intuition. Before committing 2 days to an AC-2001 port, **measure**: vol-17 should profile a `joe_depth150_par` run with `cargo flamegraph` or similar and confirm AC-3 is actually the dominant single-thread cost.

### 2. AC-2001's actual experimental advantage from the paper

AIJ'05 Table 1 (preprocessing) and Table 2 (MAC search), randomly-generated + RLFAP benchmarks:
- **vs AC-3** (constraint checks): 4-25× fewer on phase-transition / over-constrained problems, ~1× on under-constrained (where AC-3 was already optimal because no propagation).
- **vs AC-3** (CPU): 1.5-9× faster on MAC benchmarks; identical on trivially-AC-consistent problems.
- **vs AC-6** (CPU): comparable, slightly faster on most instances (one exception: SCEN#11 RLFAP where AC-6 wins).
- **DOMINO pathological problem** (designed for AC-3 worst case): AC-3 takes 381s, AC-2001 takes 15.4s, AC-6 takes 12.2s.

So: AC-2001 strictly dominates AC-3 in *both* checks and CPU on problems where AC propagates a lot; **does nothing** when AC is trivial. This matches our profile (we propagate heavily inside the search), so the win is real, but **expect 2-5×, not 3-10×**. The subagent's "2-10×" was within range.

### 3. The CRITICAL trick the agent missed: AC-2001's advantage over AC-6 grows with domain size

AIJ'05 §6 Property 2 + Figure 9: when a value `v_3 ∈ D_i` has `Δ(x_j) = {v_3}` and `v_3` is supported by 101 values, **AC-6 must update 101 S-list entries (`d_A = 101`)**, while AC-2001 only checks `Last[(x_i, a), x_j] ∈ D_j` for the 3 elements of `D_i` (`d_B = 3`). The bigger the *domain on the other side of the arc*, the more AC-2001 wins over AC-6.

**E2 implication**: domains are 764 on each side. AC-2001 strictly preferred over AC-6 by this analysis. Confirms the agent's recommendation, with a real reason.

### 4. MAC restoration cost is real (Régin CP'05)

AC-6 and AC-7 maintain S-lists that mutate on backtrack. The MAC version needs either (a) save-on-write trail multiplying space by `d` (so space goes O(ed) → O(ed²), bad), or (b) Régin's CP'05 trick of accepting "equivalent state" restoration (don't restore exactly, just maintain invariants). **AC-2001 sidesteps this entirely**: `Last` only needs to be undone if you bumped it on the path down, which is naturally small. This is a structural simplicity advantage that the agent flagged but understated.

### 5. AC-6 vs AC-2001 same #checks under same ordering

AIJ'05 §6 Property 1: AC-2001 and AC-6 perform **the same number of constraint checks** when both follow the same value ordering. So the win isn't on checks, it's on the *bookkeeping overhead per propagation*. AC-2001 = bitset membership; AC-6 = S-list traversal + maintenance. For our E2 bitset domains, AC-2001's data-structure overhead is essentially free.

### 6. The agent's AllDifferent page is correct on algorithm, partial on caveats

Verified against AAAI'94: O(d|X_C|·√|X_C|) initial matching, O(m²) per propagation worst case. Régin's experimental section is *thin* — only the Zebra problem (25 variables) is shown. No published benchmark on `n ≈ 256` AllDifferent. **Risk**: matching cost on n=256 + d=764 projected piece-domain has not been measured in the literature for problems shaped like E2. The agent's "~3 days" estimate is plausible but the *value* is empirically unproven.

### 7. The agent missed Compact-Table entirely

See [[compact-table]] — separate page. This is the actual modern champion (CP'16), used as the default in or-tools. For a problem where the binary constraint is naturally a table (E2's color-matching), CT is plausibly a better fit than either AC-2001 or AC-3 + same_piece_rots LUT.

### 8. fastGAC (Lhomme-Régin 2005) is a sub-step toward CT

AAAI'05 "Fast Arc Consistency for n-ary": improves GAC-Scheme using **lower bounds on the next valid support** via lex-ordered tuples. Skip-tuples-exponential-in-arity. Won 1-3 orders of magnitude on structured tables. **Mostly subsumed by [[compact-table]]** which uses bitset operations to achieve similar skipping without explicit lower-bound machinery. Worth knowing this exists; not worth porting separately.

## Revised recommendation for E2

Original agent recommendation: implement AC-2001 next (~2 days, 2-10× win).

**My revised recommendation after first-hand reading**:

**Step 0 (vol-17, ~half day):** flamegraph confirms AC-3 is the actual bottleneck. If not, redirect effort elsewhere.

**Step 1 (vol-17, ~half day):** measure per-edge compatible-tuple counts for canonical E2 with current hints. This decides AC-2001 vs CT.
- If average ≤ ~50k tuples per edge: [[compact-table]] is the principled port. Bitsets you already trust, dynamic incremental/reset, modern champion.
- If average ≥ ~500k tuples per edge: [[ac2001]] (coarse-grained loop, no big static support arrays) is the safer bet.
- In between: prototype both on a single propagator profile, A/B for 1 day.

**Step 2 (vol-17 or vol-18, ~2-4 days):** ship the chosen algorithm with `#[ignore]` perf-comparison tests vs AC-3 baseline.

**Step 3 (orthogonal, vol-18+):** Régin AllDifferent for piece-uniqueness. Confirmed by paper reading as the only "strong global" propagator sound under Blackwood. The implementation is well-understood (Hopcroft-Karp + Tarjan SCC, both textbook), but the **empirical value on n=256 isn't in the literature** — this is a research bet, not a guaranteed win.

## What I would no longer claim

- "AC-3 is 70% of single-thread time" — unsourced, must measure.
- "AC-2001 gives 2-30× on table constraints" — paper says 2-9× CPU, occasionally 25× on constraint checks.
- "Régin AllDiff is GAC on E2 piece-uniqueness" — true *for the projected piece-only domain*, but the rotation marginalization step is not free and not analyzed in Régin's paper. We'd be doing original work on the projection cost.

## Linked concepts

- [[ac3]] [[ac2001]] [[ac4]] [[ac6]] [[ac7]] [[alldiff-regin]] [[gac-schema]] [[ac-family-comparison]] — pages this audit corrects
- [[compact-table]] — new page, the actual modern recommendation
- [[bitset-domain-rep]] — common substrate

## Linked memory

- `project_e2_vol16_closeout` — needs flamegraph to verify AC-3 hotspot claim
- `project_e2_vol15_blackwood_results` — Blackwood-soundness gap that AllDiff could partially close
