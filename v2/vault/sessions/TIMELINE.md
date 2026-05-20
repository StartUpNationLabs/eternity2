---
tags: [moc, timeline]
date: 2026-05-20
covers: vols 1–188
---

# Vol-1..188 Timeline

The spine of the research. Each vol gets one line. Group by era. Records track the **matched-edges** convention unless tagged `[strict]`.

For details, follow the wikilink → `sessions/vol-NN.md` (where present) or the linked concept/paper.

---

## Era I — Build the baseline (vols 1–12)

Establish a working solver, score above floor.

| Vol | Record | One-liner |
|---:|:---:|---|
| 1 | 449 (cold) | Cell-CP baseline. [[gacolor]] + [[ac3]]. |
| 2 | 449 | engine/event-stream contract. |
| 3 | 449 | refactor + smoke tests. |
| 4 | 450 | [[frame-first]] decomposition: border, then interior. **First break.** |
| 5 | 453 (warm) | [[genetic-algorithm]] GA-LARGE 4×4/6×6 crossover cascade. |
| 6 | **454 warm** | [[border-diversity]] + [[parallel-tempering]] + `--pin-perimeter`. Historic warm record. |
| 7 | 454 | [[z22-vertex-charge]] gauge fingerprint. No new break. |
| 8 | — | step-8 propagators wired (class balance, parity, island). |
| 9-10 | — | shared infrastructure: events, throttling, registry. |
| 11 | — | parallel/portfolio runner. |
| 12 | (439 true) | [[bitset-domain-rep]] engine rewrite; corrects vol-7 scoring. Edge-BP measurement 18.84% interior reduction. |

## Era II — Blackwood + records, the 457 plateau (vols 13–18)

Port the community algorithm; reach community-class records.

| Vol | Record | One-liner |
|---:|:---:|---|
| 13 | — | [[boundary-mps]] tensor network proposed; later REFUTED (10¹⁰¹ overcounting). |
| 14 | (~440) | [[edge-bp-marginals]]; [[hint-pinning-bug]] discovered. |
| 15 | 416 | [[blackwood-algorithm]] raw port (cliff-fix). |
| 16 | — | BLACKWOOD_RAW closeout, AC-3 LUT precompute. |
| 17 | **455** | [[blackwood-schedule-calibration]] + WorstBand+ConflictDriven{80}. |
| 18 | **457** | [[oracle-cycle-swap]] + hot-PT T=30. → [[basin-457-pt]] discovered. |

## Era III — Investigations + ML detour (vols 19–32)

Characterize the 457 basin; chase value-order learning; finally break 458.

| Vol | Record | One-liner |
|---:|:---:|---|
| 19 | 457 | [[mismatch-homology]] β₁ — small signal. |
| 20 | 457 | [[operator-lock]] K ≤ 5 lock confirmed. |
| 21 | 457 | [[relaxed-bound]] basin-local ceiling (later: NOT a true bound; cheap heuristic). |
| 22 | 457 | [[basin-escape-recipe]] finds [[basin-440-469]] (469-ceiling basin reachable). |
| 23 | 457 | [[prune-restart]] shipped; cold-route lifts CP-depth but ALNS-fill 424 < vanilla 451. |
| 24 | 457 | [[score-optimizing-cp]] shipped. |
| 25 | 457 | Perf audit: 7 fixes (+22% joe, +27% blackwood). |
| 26-27 | 457 | [[learned-value-order]] gate at 6×6/5c — 540× node reduction, 5.5× wall-clock with ONNX in-process. |
| 28-29 | 457 | Cross-domain LVO transfer REFUTED; distribution-matched imitation hits teacher ceiling. |
| 30-31 | 457 | LVO "+9 depth" / "+10 score" — **both REFUTED at vol-32** (LOT bug fell through to InsertionOrder). |
| 32 | **458** | NEW RECORD via vanilla_fast + ALNS-5min. 2/5 hints displaced (relaxed canonical). |

## Era IV — Tooling consolidation & landscape (vols 33–42)

Crate split; fitness-landscape mapping; honest nulls.

| Vol | Record | One-liner |
|---:|:---:|---|
| 33 | 458 | Big refactor: solver-engine 5355 → 3705 lines; 5 deferred items shipped. |
| 34 | 458 | T2 propagator refuted; vol-34 records RETRACTED at vol-35 (pin_hints bug). |
| 35 | 458 | **pin_hints duplicate-piece bug found + fixed** (3 save paths). 19 distinct basin families found. |
| 36 | 458 | vanilla_path bin: border-first +12 edges vs row-major. Canonical-compliance tension noted. |
| 37 | 458 | structural_scan + pos-161 invariant (interior cross-basin cell). |
| 38 | 458 | drop-k MaxScore on canonical 454: best 431 (-23). Mismatch region too tight to refill. |
| 39 | 458 | ALNS-diverse on canonical 454 → 455 (×2). +1 lift, 5/5 hints. |
| 40 | 458 | ALNS-diverse × 24 runs on canonical 457: ALL stayed at 457. Confirms vol-22 lock. |
| 41 | 458 | ValueOrder::RecordsPrior shipped. +5-9 matched edges at iso-depth. First positive engine-level signal. |
| 42 | 458 | McGavin 469 from corpus decoded; canonical make-canonical drops it to 443. |

## Era V — Reframing, LP/MIP rigor (vols 43–59)

Pivot to bounds, MIP, CDCL. Establish 458 firm.

| Vol | Record | One-liner |
|---:|:---:|---|
| 43 | 458 | **Reframing only**. 7 cross-domain reframings; anti-pattern noted (comfort lottery). |
| 44 | 458 | **MIP cluster-repair**: vol-32 458 basin halo ≤ 2 LOCALLY OPTIMAL. LP UB 478. |
| 45-46 | 458 | LP-UB CP search; per-class diagnostics. No lever. |
| 47 | 458 | Lifted-LP McCormick — column-gen v1/v2 both INVALID. |
| 48-49 | 458 | RL via Evolutionary Strategies — both ES variants finish BELOW imitation baseline. |
| 50 | 458 | `node_budget` axis shipped; ALNS-5min × 4 from 412 → 428 (+4). LP-integer anatomy: 33% LP / 67% piece-uniqueness. |
| 51 | 458 | Bound-trigger prune-restart: triggers correctly but recovery is bottleneck. |
| 52 | 458 | Design-doc for per-piece column-gen. Estimated 7-10 days. |
| 53 | 458 | Toy worked example: LP=integer for piece-uniqueness alone. 20-pt gap is cell-fractional × scale. |
| 54 | 458 | Per-color integer bin: 5.96 fractional + 12 rounding = 17.96 gap; minimal worked example proves [[y-linearisation-cell-fractional-gap]]. |
| 55 | 458 | **B&P-and-cut MVP**: 6 real canonical clusters, LP-MIP gap is real, 458 LOCALLY OPTIMAL on every cluster (multi-cluster). |
| 56 | 458 | CDCL no-good design + 6×6 proto (96% have ready-to-fire clauses; GREEN for vol-57). |
| 57 | 458 | `crates/cdcl-proto` standalone; algorithm validated, 2WL deferred. |
| 58 | 458 | **22 cluster MIPs across 3 basin families** all locally optimal. CDCL canonical-16×16 FAILS (avg clause 96 lits). |
| 59 | 458 | Basin lottery 156 jobs → P(458) = 0.64%. CDCL hit rate crashes ≥ 12×12. E2 cause-graph is FLAT. |

## Era VI — Cross-machine 459 + invention era (vols 60–105)

The 459 break; then 41 vols of structural analysis culminating in the rigidity theorem.

| Vol | Record | One-liner |
|---:|:---:|---|
| **60** | **459** | **NEW LOCAL RECORD**: cross-machine replay → p06 corner perm + vanilla_fast + ALNS basic seed=42 30min. |
| 61 | 459 | SOTA replay calibration on vol-60 basin. No 460. |
| 62 | 459 | [[basin-level-genetic-search]] designed. |
| 63 | 459 | [[temporal-rewind-search]] designed. |
| 64 | 459 | invention scaffolding. |
| 65 | 459 | **σ-cycle indecomposability** (459→McGavin 11 cycles, 255 cells, every subset reduces). [[piece-side-matching]] LP (canonical=307, rotation-aware=480). Spectral λ_1/λ_2=2.95, Fiedler = frame/interior. |
| 66 | 459 | [[component-quotient-destroy]] shipped & refuted. |
| 67 | 459 | [[forced-component-departure]] designed; 47 basin-components found. |
| 68 | 459 | **McGavin top-N pinning sharp threshold N=14**; NEW 469 board (pieces 234↔235 swap at pos 73↔75). [[mcgavin-basin-rigidity]]. |
| 69 | 459 | [[oracle-attracted-alns]] designed. |
| 70 | 459 | [[rigidity-guided-search]] refined, refuted. |
| 71-78 | 459 | [[component-rep-database]], piece-pair frequency, basin-component analysis. 47 distinct basin-components. |
| 79 | 459 | [[cas-frame-final]] CAS = 433; CAS-hybrid + ALNS = 418 (worse). [[hamilton-frame]] 75k frame LOWER BOUND. |
| 80 | 459 | [[blackwood-triple-sweep]]: top-overlap triples scored WORST (refuted at single seed). |
| 81-82 | 459 | [[mcgavin-basin-top-bottom-symmetry]] top-N=14 → 469, bottom-N → 443-462. Mismatches in rows 0-4. |
| 83-101 | 459 | **LOCAL RIGIDITY THEOREM**. 13+ MIP-proven local-optimal regions across 3 basins. σ-cycle universality. McGavin near-twin orbit = exactly 2. **PAPER**: [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]]. |
| 102-104 | 459 | (work folded into vols 83-101 + paper.) |
| 105 | 459 | Closed early (user redirect). Rows-12-15 LP-UB on local-459 = 121.14. **CRITICAL**: corpus 470 boards are 1-clue Blackwood variant, not canonical. PAPER UB claim corrected (subset-bound). |

## Era VII — Blank-puzzle speedup + 459 level set (vols 106–115)

User directive: pivot from score to algorithm inventions + speedup.

| Vol | Record | One-liner |
|---:|:---:|---|
| 106 | 459 | [[blackwood-fast]] crate: solver-engine 367k nps → 56M nps (153×). |
| 107 | 459 | bitset+4tbl+sentinel: 65M nps (177×). |
| 108 | 459 | +PGO: 72M nps (196×). [[sigma-cycle-destroy]], [[fanout-sort-value-order]] both refuted. |
| 109 | 459 | T12 per-depth unroll proc-macro: 76M nps. [[beam-search-on-e2]] analytically refuted; [[oracle-aware-alns-repair]] empirically refuted. |
| 110 | 459 | NEW 459 basin via bf_bw pipeline (0/5 canonical hints, structurally distant). |
| 111 | 459 | σ-cycle indecomposability EXTENDS to 459↔459 (not just 459→469). |
| 112 | 459 | **basin-mix MIP at 4 basins** MIP-PROVED optimum = 459. [[corpus-restricted-mip-doesnt-scale]] beyond N=5. |
| 113 | 459 | Hint-preserving raw DFS shipped. |
| 114 | 459 | T1 const + PGO: **85M nps (232×)**. MCMC single-piece-swap + σ-cycle Metropolis: bounded in 459 level set. |
| 115 | 459 | (folded into [[SYNTHESIS_VOLS_106-115_2026-05-16]].) |

## Era VIII — Pipeline saturation & directive shift (vols 116–124)

Strict-canonical pipeline; the corpus-restricted MIP invention; the "stop mixing 459/469" directive.

| Vol | Record | One-liner |
|---:|:---:|---|
| 116 | 459 + [strict] 435 | Hint-preserving Hungarian shipped; full pipeline 5/5 canonical compliant. |
| 117 | 459 | hint-preserving schedule path; 3 σ-cycle math findings (schedule×hint destructive). |
| 118 | 459 | Two-cluster 459-level set CONFIRMED via rigidity matrix. **bf-bucket bug FIXED**. 39 bins migrated to canonical I/O (-427 lines). |
| 119 | 459 | **INVENTION**: [[corpus-restricted-region-mip-locked]] (locks 459 at halo-8 with 191 free cells in <1min). NEW 458 basin sweep_p18_s2 (3/5 hints, structurally distinct). 30-board basin corpus assembled. |
| 120 | 459 | **THEOREM**: strict-canonical 457 + matched 459 BOTH corpus-MIP-LOCKED across full interior with 25-30 board corpus. |
| 121 | 459 | Exhaustive anchor-on-McGavin halo/joint MIPs + ALNS: ALL Δ=0. → driver for the user redirect. |
| **122** | 459 + **[strict] 458** | **NEW STRICT-CANONICAL RECORD**. User issues binding [[REMINDER_USER_DIRECTIVES|directive]]: STOP mixing 459/469; inventor mode for 1 month. λ_2 signature pick + ALNS basic 30min seed=42. 19 sub-experiments (T1/A1/A4/J3-7/K1-4). |
| 123 | 459 | Continuation of vol-122 inventions; close. |
| 124 | 459 | 8 kissat × 30min on canonical SAT → ALL UNKNOWN. CDCL on monolithic encoding exhausted. SAT-rigid up to halo-10. |

## Era IX — A1 closure & the 461/463 break (vols 125–129)

User: "you have 1 month". A1 border-DP closure; then PALIMPSEST.

| Vol | Record | One-liner |
|---:|:---:|---|
| 125 | 459 → **460** → **461** | A1 closure: CSP-fill wrapper + 1000-border corpus + bf_bw + ALNS. off=125 → 460; off=110 → **461**. Depth-40 phase transition identified. |
| 126 | 461 | [[concord-difference-map]] partial. |
| 127 | 461 | [[concretion-rigid-molecules]] refuted. |
| 128 | 461 | [[atlas-pattern-database]] refuted. Pure static analysis saturates. |
| **129** | **463** | **PALIMPSEST**: 1278-board DB consensus mining → 15-basin attack on (2,3,0,1)@462 base. **463/480 (current matched record)**. 18 corner-perm families ≥458 identified. |

## Era X — Long compute spree (vols 130–154)

Sparse session journals — many vols rolled into concepts/memory directly.

(Coverage: 131, 134, 146-153 are the only journaled vols. 130, 132-145, 154 work captured in concepts.)

| Vol(s) | Record | One-liner |
|---:|:---:|---|
| 130 | 463 | FILAMENT result — SA-repair beats FILAMENT-repair (no short positive-gain chains). |
| 131 | 463 | session journal present. |
| 132-145 | 463 | gap; work in concepts. |
| 146-153 | 463 | close-out + continuing inventions. |

## Era XI — From-scratch 460s (vols 155–170)

V155 PRIOR opens the era of constructive-from-scratch ≥ 460.

| Vol | Record | One-liner |
|---:|:---:|---|
| **155** | 463 + **from-scratch 456** | [[prior-data-augmented-beam]] (V155): corpus prior matrix on K=4096 + path-dedup-4 → from-scratch 456. **First constructive builder informed by corpus distribution.** |
| 156 | 463 + **460** | V155 → ALNS basic_lkh pipeline → 460/480. |
| 157-168 | 463 | gap; work in concepts (multiple invention vols). |
| **169** | 463 + 460 | **OPHIDIA**: [[prior-guided-alns]] — V155→ALNS with PriorDestroy. V155→ALNS 460 boards 73-75% corpus-orthogonal. |
| 170 | 463 | gap. |

## Era XII — Multi-basin sampling & invention sprint (vols 171–181)

Build new ranking signals; stochastic beam; new basin discovery.

| Vol | Record | One-liner |
|---:|:---:|---|
| 171 | 463 | **MURMURATION**: stochastic Gumbel-beam on V155 to sample 1000s of 460 basins. |
| 172 | 463 | **CHIASMUS**: cross-basin row-interleave — refuted as record-mover. |
| 173 | 463 | (filler / scratch) |
| 174 | 463 | (filler / scratch) |
| 175 | 463 + 458 (new cp) | **GAUNTLET** zigzag → 458 in cp=(3,0,1,2); first ≥458 in this cp. [[basin-458-cp3012-v175]]. |
| 177 | 463 | (scratch) |
| 178 | 463 | **STIGMA**: [[stigma-pheromone-adjacency]] — pheromone adjacency ranker. |
| 179 | 463 | **LARGE-K**: [[v179-large-k-destroy]] — destroy variants k∈{32,48}. |
| 180 | 463 | **INTAGLIO**: [[intaglio-attack-lex]] — lex-ordered acceptance on forbidden-2x2 patches. 99.72% random patches forbidden. |
| **181** | 463 + **460** | **KEYRING**: patch + pheromone + position prior → 460 in cp=(0,3,1,2) (first ≥460 in this cp). [[basin-460-cp0312-v181]]. 5/8 lifts ≥458. |

## Era XIII — Rigidity confirmation (vols 182–188)

Prove the three-basin iso-plateau is structural, not budgetary.

| Vol | Record | One-liner |
|---:|:---:|---|
| 182 | 463 | **ENGRAVE**: [[v182-engrave-csp-fill]] band-fill K∈{2,4} — refutes local 460 lift. |
| 183 | 463 | **SEMAPHORE**: [[semaphore-row-hungarian]] — row-10 piece-starvation wall. |
| 184 | 463 | **LIGHTHOUSE**: [[lighthouse-bidirectional-row]] — MERGE interface infeasible (0 valid pairs at K≤300). |
| 185 | 463 | **Cleanup**: vault catchup, BACKLOG audit, MEMORY trim. [[three-basin-iso-plateau]] documents universal local rigidity. |
| 186 | 463 | **LIGHTHOUSE-SOFT + row-swap**: V181 460 PROVEN row-locally rigid (1-row, 2-row, 3-row swap). McGavin same property. [[row-level-rigidity]]. |
| 187 | 463 | **INTAGLIO-MIP**: 4 distinct regions (32, 32, 32, 30 cells) **HiGHS-MIP-proven** rigid on V181 460. 1h ALNS confirms basin lock. [[v187-intaglio-mip]]. |
| **188** | 463 | **TRANSLATION**: σ-cycle indecomposability confirmed on 3rd basin pair (V181-460 ↔ McGavin-469). [[v188-translation-sigma-indecomposability]]. |

---

## Records progression (records-only)

| Vol | Score | Convention | Mechanism |
|---:|:---:|---|---|
| 6 | 454 | warm | border-diversity + PT |
| 17 | 455 | cold | Blackwood schedule |
| 18 | 457 | cold | oracle-cycle-swap + hot-PT |
| 32 | 458 | matched (3/5 hints) | vanilla_fast + ALNS-5min |
| 60 | **459** | matched | p06 + vanilla_fast + ALNS basic seed=42 30min |
| 122 | 458 | **strict 5/5** | λ_2 signature + ALNS |
| 125 | **460, 461** | matched | bf_bw off=125 / off=110 + ALNS |
| 129 | **463** | matched | PALIMPSEST 15-basin attack on (2,3,0,1)@462 |
| 155 | 456 | from-scratch | V155 PRIOR (K=4096+dedup) |
| 156 | 460 | matched | V155 → ALNS basic_lkh |
| 175 | 458 | matched (new cp) | V175 GAUNTLET zigzag, cp=(3,0,1,2) |
| 181 | 460 | matched (new cp) | V181 KEYRING, cp=(0,3,1,2) |

DB-find (not algorithm-produced): **459 strict-canonical** (5/5 hints) at vol-122 close.

---

## Era boundaries — why they matter

- **I → II**: paradigm shift from CSP-only to portable community algorithms (Blackwood).
- **II → III**: 457 plateau triggers tooling investment (ML LVO).
- **III → IV**: 458 break + bug discovery cycle.
- **IV → V**: pivot to LP/MIP rigor (the "is 458 even a real ceiling?" question).
- **V → VI**: cross-machine replay confirms 459 is reachable; era of structural analysis begins.
- **VI → VII**: user directive forces invention focus + speedup; the engine matures.
- **VII → VIII**: pipeline saturation visible; MIP-locking confirms structural ceilings.
- **VIII → IX**: directive to STOP mixing 459/469 + inventor month; A1 closure breaks the wall (460→461→463).
- **IX → X**: long compute spree (vols 130-154 sparse in journals).
- **X → XI**: V155 opens from-scratch ≥ 460 era; corpus prior is the key.
- **XI → XII**: invention sprint with new ranking signals; new basins (cp 0312, cp 3012).
- **XII → XIII**: rigidity confirmation — V181 460 is structurally locked under MIP + row-swap + σ-cycle.

---

## Pivot moments (the "what changed direction")

1. **Vol-15 Blackwood port**: cross-domain transfer attempt; first borrow from community.
2. **Vol-22 basin-escape recipe**: discovery that 469-ceiling basins exist locally.
3. **Vol-32 458 break**: 7 vols of LVO investment; the actual lift came from vanilla_fast + ALNS.
4. **Vol-43 reframing**: meta-recognition of comfort-lottery anti-pattern.
5. **Vol-44 MIP**: introduces sound bounds; 458 firm.
6. **Vol-60 cross-machine 459**: community-class compute matters; SOTA replay.
7. **Vol-65 σ-cycle indecomposability**: theoretical breakthrough on basin structure.
8. **Vol-105 corpus-470 retraction**: canonical-vs-Blackwood-variant clarified.
9. **Vol-118 bf-bucket bug fix**: 200 false records explained; canonical I/O consolidated.
10. **Vol-122 directive**: STOP mixing 459/469. Forces inventor-only operating mode.
11. **Vol-125 A1 closure**: the border-DP pipeline finally bridges to ALNS; opens the 461 / 463 break.
12. **Vol-155 PRIOR**: corpus prior as a value-ranking signal; opens from-scratch ≥460 era.
13. **Vol-185-188 rigidity**: structural confirmation that ≥461 needs non-local operators.

---

## Dead-end registry (cross-vol)

These are tracked because the no-quiet-deletes rule wants the audit trail.

- **Survey propagation** (vol-13): theoretical block, cavity method invalid.
- **Boundary MPS** (vol-13): 10¹⁰¹ overcounting gap.
- **Eulerian border** (vol-?): vacuous on canonical E2.
- **Homotopy-ALNS** (vol-65): β₁=0 on all 458+ records.
- **Component-quotient-destroy at halo ≤ 1** (vol-65): MIP-bounded.
- **CAS-hybrid + ALNS** (vol-79): 418 (worse than CAS alone 433).
- **σ-cycle subset import** (vol-65/110): every subset reduces score.
- **Per-piece column-gen alone** (vol-52→54): doesn't close cell-fractional gap.
- **RL ES (vol-48-49)**: degrades below imitation baseline.
- **basin-mix MIP at 4 basins** (vol-112): MIP-PROVED optimum = 459.
- **σ-cycle predicts ALNS-lift** (vol-107): partial signal weakens at N=6.
- **SigmaCycleDestroy ALNS op** (vol-108): refuted.
- **Beam search analytically** (vol-109): refuted.
- **Oracle-aware repair** (vol-109): graft loses 170 pts.
- **High-T MCMC + σ-Metropolis** (vol-114): chains randomize, never exceed 459.
- **CHIASMUS basin crossover** (vol-172): refuted as record-mover.
- **SEMAPHORE row-Hungarian** (vol-183): row-10 piece-starvation wall.
- **LIGHTHOUSE bidirectional MERGE** (vol-184): 0 valid pairs at K≤300.
- **V182 ENGRAVE K∈{2,4} band-fill**: refutes local 460 lift.
- **Bottom-N pinning of McGavin** (vol-82): 443-462 only.
- **Naive CDCL at canonical 16×16** (vol-58-59): avg clause 96 lits, 0 unit-props.
- **Kissat on full puzzle SAT** (vol-124): 8×30min ALL UNKNOWN.
- **Single & double near-twin swaps on McGavin** (vol-68): max 469.

See also: [[dead-ends]].

---

## Open as of vol-188

1. **Find ≥461 in any of 15 unexplored corner-perms** (vol-189 CORTEZ binding).
2. **Cross-basin σ-transport between closer basins** (e.g., V129 463 ↔ V181 460 — 6-point gap, possibly shorter cycles).
3. **Non-rectangular MIP regions** on V181 460 (diagonal, L-shape, scattered).
4. **4-row + MIP** with longer budget / stronger cuts.
5. **SDP relaxation** for tighter than-LP score bounds.
6. **Multi-week RL self-play** with reward = max-score-found.

For the active short-list, see [[CURRENT-VOL]] and [[INVENTIONS_BACKLOG]].
