---
tags: [synthesis, capstone, moc]
date: 2026-05-20
covers: vols 1–188
status: master synthesis
---

# Eternity II — Master Synthesis (vol-188)

The capstone document for 188 volumes of research. Where we are, what we've proven, what we've refuted, what's still open.

For granular vol-by-vol detail: see [[sessions/TIMELINE]].
For binding directives: see [[REMINDER_USER_DIRECTIVES]].
For numerical facts at a glance: see [[E2_KNOWN_FACTS]].

---

## 1. State of the project

### 1.1 Records

| Convention | Score | Vol | Mechanism |
|---|---:|---:|---|
| **Matched edges** (our standing record) | **463** | 129 | PALIMPSEST consensus-trap attack on (2,3,0,1)@462 |
| **Strict canonical** (5/5 hints obeyed) | **459** | 122 + DB | DB-find; algorithm-produced 458 at vol-122 |
| **Community canonical 5-clue ceiling** | 469 | — | McGavin 2020, Joshua Blackwood's solver |
| **Theoretical perfect** | 480 | — | unsolved by anyone publicly since 2007 |

### 1.2 Known basins ≥ 458 across distinct corner-perms

The corner-perm (the 4 corner piece-IDs at positions 0/15/240/255) is a coarse basin signature.
Of the 24 possible cps, **18 carry ≥ 458 boards** in our 1278-board DB (vol-129 PALIMPSEST analysis).
Only **5** have reached ≥ 460:

| cp | Score | Discovery |
|---|---:|---|
| (3,2,0,1) | 469 | McGavin 2020 |
| (1,2,0,3) | 461 | V125 (vol-125) |
| (0,3,1,2) | 460 | V181 KEYRING (vol-181) |
| (2,3,0,1) | **463** | V129 PALIMPSEST (vol-129) |
| (1,0,2,3) | 459 | vol-60 (p06) |

13 corner-perms have ≥ 458 boards but no ≥ 460 board yet. **vol-189 CORTEZ targets these directly.**

### 1.3 The three-basin iso-plateau (vol-185–188)

Three independently-discovered ≥ 458 basins were tested under every local operator in the inventory:

- V175 458 (cp=(3,0,1,2)) [[basins/basin-458-cp3012-v175]]
- vol-60 459 (cp=(1,0,2,3)) [[basins/basin-459-p06]]
- V181 460 (cp=(0,3,1,2)) [[basins/basin-460-cp0312-v181]]

**All three are iso-locked** under 30-min and 1-hour ALNS basic_lkh + V179 LARGE-K + V180 INTAGLIO. V181 460 specifically is:

- 1-row, 2-row, 3-row joint-swap locally rigid (vol-186 [[concepts/row-level-rigidity]])
- 4 distinct 30+ cell regions MIP-proven rigid by HiGHS (vol-187 [[concepts/v187-intaglio-mip]])
- σ-cycle indecomposable to McGavin 469 across all 15 cycles (vol-188 [[concepts/v188-translation-sigma-indecomposability]])

This is the strongest structural rigidity result in the vault, and confirms the **Local Rigidity Theorem** (vols 83-101, [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]]) on a 4th independent basin.

---

## 2. What we've proven (durable findings)

### 2.1 Local Rigidity Theorem (vols 65–101, strengthened through vol-188)

**Statement (empirical, supported by ≥ 17 MIP proofs across 4 basins).**
For every tested record with score ≥ 458 on canonical 5-clue E2:

1. **Halo-2 local MIP-rigidity**: no piece-permutation + rotation within any halo-r ≤ 2 region around defect cells improves score.
2. **Larger-region rigidity**: for McGavin 469, no improvement within any halo-r ≤ 4 region. For V181 460, no improvement within any 30+ cell rectangular region (vol-187).
3. **Cross-basin σ-cycle indecomposability**: every σ-cycle subset from a local basin to McGavin's 469 reduces score. Confirmed on 3 independent basin pairs (vol-65, vol-99, vol-188).
4. **Geometric dispersion**: 80–255 cell σ-cycles are board-spanning, touching nearly all 14×14 interior cells.
5. **Row-level rigidity** (vol-186 new): no valid alternative 16-piece chain for any single row, nor any 2-row or 3-row joint swap, can lift V181 460.

**Corollary.** To lift any local basin to ≥ McGavin 469 requires a single simultaneous re-arrangement of 80+ dispersed cells. **No known local algorithm operates at this scale.**

See: [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]], [[PAPER_2026-05-17_vol122_basin_diversity_and_rigidity]], [[concepts/three-basin-iso-plateau]].

### 2.2 First sound UB below 480 (vol-86, corrected vol-105)

**McGavin top-4 rows** (64 cells): MIP dual bound = 123, gap 6%. Caveat (vol-105): this is a **subset bound** under the assumption that the rest of the board is fixed to McGavin's configuration. It is not an unconditional UB on 480. Still: the first non-trivial structural UB below 480 on canonical E2.

See: [[concepts/board-wide-ub-derivation]].

### 2.3 σ-cycle indecomposability is universal (vol-65, vol-99, vol-110, vol-111, vol-188)

Across **4 measured basin pairs** (local-459↔McGavin, sister-458↔sister-458, BF-pipeline-459↔BF-pipeline-459, V181-460↔McGavin), every proper subset of cycles in the piece-permutation π strictly reduces score. The decomposition is at the "single big cycle" granularity (one cycle of size 80, 154, or 255 cells dominates each π).

This is the deepest structural obstruction we've found. Lifting a local basin to ≥469 requires **the entire σ-cycle applied at once**, not a partial walk.

See: [[concepts/sigma-cycle-universal-indecomposable]], [[MATH_NOTES_2026-05-16_SIGMA_SUBSET_THEOREM]].

### 2.4 The 458/459 level sets have multiple distant basins (vol-110, vol-119, vol-175)

The 459-level set is a **union of ≥ 2 structurally distant clusters**, each halo-1 MIP-rigid ([[concepts/459-level-set-two-cluster-confirmed]]). The 458-level set has ≥ 3 distant basins (vol-32 458, sweep_p18 458, V175 458) — corpus-distance ≥ 240 cells between them.

Empirically, the σ-subset bound Δ ≈ −B(S) is **tight across a 30-board corpus** (vol-119, [[concepts/sigma-subset-bound-empirically-tight]]).

### 2.5 INTAGLIO 2×2 finding (vol-180)

**99.72% of random 2×2 patches are forbidden** in canonical 5-clue E2 (i.e., admit no valid edge-color completion).
- HIGH-score boards (≥ 458): typically ~29 forbidden 2×2 sub-patches.
- A hypothetical 480-board: 0 forbidden 2×2 patches.

This gives an inexpensive structural penalty for ranking partials: count forbidden 2×2 patches and minimize. See [[concepts/intaglio-attack-lex]], [[concepts/forbidden-patch-theorem-2026-05-19]].

### 2.6 NS-1 Δ-invariant correlates with score (Hopfer 2022; our work vols 50, 119)

The NS-1 "deficit" invariant Δ ∈ {0, 1, 2, 4} for canonical E2 partials in the 448-480 range:
- Δ = 0 needed for 480
- Δ = 1 at 469 (McGavin)
- Δ = 2 at 459
- Δ = 3-4 at 458

A search that minimizes Δ biases toward high-score basins. (Not yet used as a search objective.)

See: [[concepts/ns1-deficit]].

### 2.7 K11 basin signatures (vol-122)

Spectral λ_2 of the cluster-graph + match-zone (mz) jointly distinguish basins. A hint-rigidity trade-off was discovered: λ_2 picks separate basins, but the strict-canonical hints constrain which λ_2 region admits 5/5 compliance.

See: [[concepts/k11-basin-signatures]].

### 2.8 Engine + tooling state

| Component | Throughput / metric |
|---|---|
| blackwood-fast | **85 M nps single-thread** (232× over vol-15 solver-engine BLACKWOOD_RAW; ~28% of Bucas's C) |
| vanilla-v2 | **97 M pp/s** (+33% over vanilla_fastest) |
| ALNS | proven ceiling per basin ≈ +1 score on 30-min budget; 1-hour gives 0 lift on iso-plateau |
| MIP rigidity | HiGHS-MIP proves rigidity to ~30-cell rectangular regions in tractable time; larger inconclusive at 30min |
| LP-UB on basins | 3-row band UB ≈ 95, integer ≈ 83; 4-row LP ≈ 135, integer ≤ 112 (vol-187) |

---

## 3. What we've refuted (don't repeat these)

The full registry is in [[concepts/dead-ends]] and the bottom of [[sessions/TIMELINE]]. Cross-vol selection:

| Idea | Refuted at | Why |
|---|:---:|---|
| Survey propagation | vol-13 | cavity method invalid on this structure |
| Boundary MPS tensor network | vol-13 | 10¹⁰¹ overcounting |
| Eulerian border (anr_56 2007) | — | vacuous on canonical E2 |
| Homotopy-ALNS (β₁-cycle destroy) | vol-65 | β₁ = 0 on all ≥ 458 records |
| Component-quotient destroy halo ≤ 1 | vol-65 | MIP-bounded |
| σ-cycle subset import from oracle | vol-65, 110, 188 | universally indecomposable |
| McGavin bottom-N pinning | vol-82 | sharp threshold at top-N=14 (bottom gives 443-462) |
| CAS (Concentric Annular Solving) | vol-79 | 433 greedy ceiling |
| CAS-hybrid + ALNS | vol-79 | 418 (worse than CAS alone) |
| Per-piece column-gen alone | vol-52→54 | doesn't close cell-fractional gap |
| RL via Evolutionary Strategies | vol-48–49 | degrades below imitation baseline |
| basin-mix MIP at 4 basins | vol-112 | MIP-proved optimum = 459 |
| SigmaCycleDestroy ALNS op | vol-108 | bounded |
| Beam search analytically | vol-109 | refuted |
| Oracle-aware repair (graft) | vol-109 | loses 170 pts |
| High-T MCMC + σ-Metropolis | vol-114 | chains randomize, never exceed 459 |
| CHIASMUS basin crossover | vol-172 | refuted as record-mover |
| SEMAPHORE row-Hungarian | vol-183 | row-10 piece-starvation wall |
| LIGHTHOUSE bidirectional MERGE | vol-184 | 0 valid pairs at K ≤ 300 |
| V182 ENGRAVE K∈{2,4} band-fill | vol-182 | refutes local 460 lift |
| Naive CDCL at canonical 16×16 | vol-58–59 | avg clause 96 lits, 0 unit-props |
| Kissat on full puzzle SAT | vol-124 | 8 × 30min ALL UNKNOWN |
| Single & double near-twin swaps on McGavin | vol-68 | max 469 |
| FPL probe (per-piece pinning) | vol-125-T34 | INFEASIBLE |
| FILAMENT short-chain repair | vol-130 | no short positive-gain chains |
| Corner-rotation symmetry breaking | binding | canonical E2 has NO symmetries |
| Standard MIP cluster-repair halo ≤ 2 | vol-44, 95 | LOCALLY OPTIMAL on every basin tested |
| Naïve row/col-bidirectional build | vol-184 | interface row constraint as tight as full bipartite matching |

---

## 4. The 13 pivot moments

1. **Vol-15 Blackwood port**: first cross-domain transfer attempt. Established that the community algorithm is *transferable*, even if not directly stronger initially.
2. **Vol-22 basin-escape recipe**: discovers that 469-ceiling basins are *reachable* by our pipeline — the bottleneck is filling, not finding.
3. **Vol-32 458 break**: 7 vols of LVO investment; the actual lift came from vanilla_fast + ALNS. Lesson: throughput matters more than cleverness when seeds are cheap.
4. **Vol-43 reframing**: meta-recognition of "comfort lottery" anti-pattern. Documented in [[concepts/dead-ends]].
5. **Vol-44 MIP**: introduced sound bounds via cluster MIP. 458 confirmed firm.
6. **Vol-60 cross-machine 459**: community-class compute (30min ALNS basic seed=42) breaks the 458 wall. Lesson: compute distribution matters; long single seeds dominate short multi-seed lotteries.
7. **Vol-65 σ-cycle indecomposability**: theoretical breakthrough — quantifies why basin transitions are hard, even given the right pieces.
8. **Vol-105 corpus-470 retraction**: discovered that "470 boards" in community corpus are 1-clue Blackwood variant, not canonical 5-clue. Major correctness fix.
9. **Vol-118 bf-bucket bug fix + canonical I/O**: explains 200 fake records; 39 bins migrated to canonical export crate; -427 lines duplication.
10. **Vol-122 directive "STOP mixing 459/469"**: forces inventor-only mode for a month. Best meta-decision in the project.
11. **Vol-125 A1 closure**: border-DP + bf_bw + ALNS finally bridges to from-scratch ≥ 460. Lifts the standing record 459 → 461 → soon → 463.
12. **Vol-129 PALIMPSEST 463**: consensus mining of 1278-board DB identifies "consensus traps" (high-persistence pairs forbidden in 462+). Targeted destroy on those → +1 lift to **463 standing record**.
13. **Vol-155 PRIOR**: corpus prior matrix as a beam-search value-ranking signal. Opens the from-scratch ≥460 era; later combined with patch prior, pheromone (V181 KEYRING).

---

## 5. The big anti-pattern: comfort lottery

Documented vol-43, applied through vol-188. The pattern:

> Uncertain what to do next → run more seeds / more parallel / more budget / more variations on the same operator class.

This is almost always the wrong move. The right move is one of:
- Do math (LP/MIP/group theory/polytope analysis) directly on the obstruction.
- Invent a structurally different operator class.
- Build a measurement that distinguishes between competing hypotheses.

Bigger compute *can* break a record (vol-60's 30-min seed=42 vs vol-32's 5-min lottery), but only as *one specific lift* — not as a general strategy. The Local Rigidity Theorem now formalizes *why*: every local basin is structurally locked under the operators we've measured.

See: [[concepts/dead-ends]], [[vol-43-reframing]].

---

## 6. What's still open

### 6.1 High-EV, this-week-doable

1. **CORTEZ (vol-189 binding)**: build V181 KEYRING + corner-pinning over the 15 unexplored corner-perms. Any ≥ 460 in a new cp is a new record; any ≥ 461 is a breakthrough.
2. **V129 463 ↔ McGavin 469 σ-transport**: 6-point gap, different cps. Possibly shorter cycles than V181↔McGavin's 49-52-cell indecomposables.
3. **V125 461 ↔ V129 463 σ-transport**: 2-point gap. Smallest gap we have; if anything decomposes, it's here.
4. **INTAGLIO-MIP on V129 463 and V125 461**: characterize their rigidity profile (analogous to vol-187 on V181 460).
5. **Non-rectangular MIP regions on V181 460**: L-shapes, diagonals, scattered. The 4-row rectangular MIP didn't converge at 30min; non-rectangular cuts may close faster.
6. **4-row MIP with stronger LP cuts** (clique cuts, Chvátal-Gomory).

### 6.2 Multi-week / requires investment

7. **Branch-and-Price-and-Cut full implementation** (vol-52 sketch). Estimated 3-4 weeks; gives sound bounds and may rule out 480 unconditionally.
8. **SDP relaxation** for tighter than-LP bounds (Idea A from IDEAS_FROM_BLANK).
9. **Multi-week RL self-play** with reward = max-score-found (deferred since vol-30+; A1 closure was higher EV).
10. **Cross-machine BOLT** for additional engine speedup (compile to Linux ELF).

### 6.3 Structural / theoretical

11. **Group-theoretic σ-cycle enumeration**: can σ-cycle candidates be enumerated using Burnside/Cayley tools without an oracle?
12. **Is the σ-cycle 470 → 480 (if 480 exists) similarly indecomposable**, or does the increased solution density allow decomposable bridges?
13. **Does the maximal-adversarial pattern arise from Selby-Riordan's specific generator**, or from canonical color balance more broadly? (If generator-specific, perturbing the generator might reveal an easier puzzle.)

### 6.4 Recently re-opened by vol-188 close

14. **CORTEZ may find a ≥460 in a new cp** — that's the high-leverage near-term experiment. If even one new cp reaches ≥ 460, we have a 6th cp with a ≥ 460 board, and the basin-count argument for "the 460+ region is sparse" weakens.

For the live short-list: [[plans/CURRENT-VOL]] and [[plans/INVENTIONS_BACKLOG]].

---

## 7. A note on canonical convention

Conventions matter — see CLAUDE.md anti-pattern §5. Our records:

- **Matched edges 463** (vol-129): does not require 5/5 hints obeyed; is the "Bucas leaderboard convention" the community uses.
- **Strict canonical 459** (vol-122 DB-find): 5/5 hint cells filled with the canonical hint pieces in correct rotation.
- **Vol-32 458** (cold): matched-edges with **3/5 hints obeyed** (relaxed). When people compare to "vol-32 458" without qualification, they often mean this; remember it's not the strict-canonical convention.

The vol-122 algorithm-produced **458 strict** is the corresponding strict-canonical-class record produced by our pipeline; the **459 strict** at vol-122 was a DB find (a board that happened to satisfy strict canonical on independent rescore).

---

## 8. Standing message

> **463 matched, 459 strict, structurally locked across all 5 basins ≥ 458 that we've tested.**
> **The next break requires either an unexplored corner-perm to harbour a ≥ 460 board, OR a fundamentally non-local operator that operates at the σ-cycle scale.**

The path forward is concrete: vol-189 CORTEZ targets the corner-perm angle. Cross-basin σ-transport on smaller gaps is the math angle. Branch-and-Price-and-Cut is the bounds angle. The vault is consolidated; the obstructions are characterized; the work continues.

---

## See also

- [[INDEX]] — vault navigation
- [[README]] — vault discipline
- [[REMINDER_USER_DIRECTIVES]] — binding rules
- [[E2_KNOWN_FACTS]] — facts at a glance
- [[sessions/TIMELINE]] — vol-1..188 timeline
- [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]] — local rigidity theorem
- [[PAPER_2026-05-16_459_indecomposability_synthesis]] — 459 indecomposability
- [[PAPER_2026-05-17_vol122_basin_diversity_and_rigidity]] — basin diversity & rigidity
- [[SYNTHESIS_VOLS_106-115_2026-05-16]] — vols 106-115 synthesis (blank-puzzle speedup era)
- [[concepts/three-basin-iso-plateau]] — current rigidity finding
- [[concepts/dead-ends]] — refuted approaches registry
