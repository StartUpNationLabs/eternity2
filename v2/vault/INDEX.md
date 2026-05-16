---
tags: [moc, index]
---

# E2 Research Vault — Map of Content

The Obsidian landing page. Click any wikilink to navigate.

## Quick orientation

- **Goal**: solve canonical 5-clue Eternity II (16×16 Monckton piece set) — score 480/480.
- **Community ceiling**: 469/480 ([[basin-mcgavin-469|McGavin 2020]] via Blackwood algorithm).
- **Our current record (vol-60)**: **459/480** (vanilla_fast + ALNS, p06 corner perm).
- **Cold-start record (vol-32)**: 458/480.
- **Warm-start record (vol-6)**: 454/480.
- **Gap to community**: 10 points; the 459 ↔ 469 gap is **rigorously characterised** as a board-spanning σ-cycle problem (vols 65-101 PAPER).
- **Spec contract**: `v2/V2_DESIGN.md`.
- **Project guide**: `v2/CLAUDE.md`.
- **2026-05-16 PAPER**: [[../PAPER_2026-05-16_canonical_E2_rigidity_theorem|Local Rigidity Theorem]] (13+ MIP-proven local-optimal regions, sound UB ≤ 123 on McGavin top-4, universal σ-cycle indecomposability).

## Plans + discipline

- [[plans/BACKLOG|BACKLOG]] — canonical T-list across volumes
- [[plans/CURRENT-VOL|CURRENT-VOL]] — active volume's binding items (other-agent territory)
- [[README]] — vault discipline (audit-at-open, concept-first, no quiet deletes)

## Score history

| Vol |            Cold |    Warm | Mechanism                                                         |                               |
| --: | --------------: | ------: | ----------------------------------------------------------------- | ----------------------------- |
|   1 |             449 |       — | Cell-CP baseline ([[gacolor]] + [[ac3]])                          |                               |
|   4 |             450 |       — | [[frame-first]] decomposition                                     |                               |
|   5 |               — |     453 | [[genetic-algorithm                                               | GA-LARGE]] cascade            |
|   6 |               — | **454** | [[border-diversity]] + [[parallel-tempering]] --pin-perimeter     |                               |
|   7 |               — |     454 | (no break, structural characterization)                           |                               |
|  12 |      (439 true) |       — | [[bitset-domain-rep]] engine rewrite                              |                               |
|  14 | (~440 post-fix) |       — | [[edge-bp-marginals]] + [[hint-pinning-bug                        | hint pinning bug]] discovered |
|  15 |             416 |       — | [[blackwood-algorithm]] raw (cliff-fix)                           |                               |
|  17 |         **455** |       — | [[blackwood-schedule-calibration]] + WorstBand+ConflictDriven{80} |                               |
|  18 |         **457** |       — | [[oracle-cycle-swap]] + hot-PT T=30 ([[basin-457-pt]])            |                               |
|  22 |             457 |       — | [[basin-escape-recipe]] finds [[basin-440-469                     | 469-ceiling basin]]           |
|  23 |             457 |       — | [[prune-restart]] shipped; cold-start route +266 CP-depth lift but ALNS-fill only 424 (< 451 vanilla) |                               |
|  24 |             457 |       — | [[score-optimizing-cp]] shipped — MaxScore CP-fill 412→419 vs vol-23 round-2 partial; cold-chain 413 at 40% budget |                               |
|  26 |             457 |       — | [[learned-value-order]] gate at 6×6/5c — 540× engine-node reduction vs MRV+LCV; stdio bridge eats wall-clock win |                               |
|  27 |             457 |       — | [[learned-value-order]] gate PASS — ONNX in-process, 5.5× wall-clock win, 16/16 recovery of MRV-failures at 100ms budget |                               |
|  28 |             457 |       — | [[learned-value-order]] cross-domain transfer REFUTED — 6×6-trained v2 model gives Δ=−108 depth regression under `joe_depth150_bp` at canonical 16×16 |                               |
|  29 |             457 |       — | [[learned-value-order]] distribution-matched imitation hits the teacher ceiling — Δ=−1 with −35% nodes, −37% backtracks at iso-depth (gate PASS at match condition) |                               |
|  30 |             457 |       — | ~~[[learned-value-order]] +9 depth lift from LearnedOnTies~~ **REFUTED vol-32** — bug at lib.rs:2550 caused LOT to silently fall through to InsertionOrder; model never called |                               |
|  31 |             457 |       — | ~~[[learned-value-order]] +10/+8 score lift~~ **MIS-ATTRIBUTED vol-32** — the "depth-174 ML partial" was actually an InsertionOrder partial; real numbers but wrong attribution |                               |
|  32 |         **458** |       — | **NEW RECORD** via vanilla_fast (125M pp/s, community-class) + ALNS-5min: matched=458/480 (caveat: 2 of 5 canonical hints displaced). Also: vol-30/31 BUG DISCOVERED, [[unsat-clause-propagator]] prototype, blackwood_raw+MRV cold-start tied 457 in 10min |                               |
|  33 |               — |       — | code refactor: 5 deferred items shipped (eternity2-time, -export, -puzzle-io crates; solver-engine modules split; bin-harness scaffold). solver-engine lib.rs: 5355→3705 lines |  |
|  34 |             — |       — | T1 vanilla_fast snapshot infra; T2 unsat-clause-propagator hard-pruner refuted (encoding reconciled); T3 lottery: 2 boards CLAIMED 457 but later **RETRACTED** (vol-35 found pin_hints duplicate-piece bug). 2 alns_only bugs fixed (polish_swap, filename collision). User-proposed [[fitness-landscape-mapping]] vol-35 T1. |  |
|  35 |             — |       — | **Vol-35 closed**: pin_hints duplicate-piece bug found + fixed (3 save paths); vol-34 records + vol-35 "7th basin" claim retracted. Multi-scale landscape mapped (4×4 → 16×16); 10×10/8c smallest showing clustering. Thread-id sweep finds 19 distinct basin families (vs 5 default). Deep_458_basin lottery on vol-32's clean partial: 1×458 byte-identical + 2 new 457 satellites. **458 record stands; no 459 break.** [[vol-35]] |  |
|  36 |             — |       — | **Vol-36 closed**: vanilla_path bin shipped (raw-DFS, custom paths, 60-100M pp/s, 7 path modes). border-first wins cold CP at +12 edges vs row-major; all centre-first variants refuted (re-confirm vol-14 hint-centric null in raw-DFS). **Canonical-compliance tension** found: vol-32 458 has only 3/5 hints honored; vol-36 border-first ALNS produces 0/5; pin-hints depth caps at ~208. Make-canonical operator built: 458 → canonical 446 (5/5 hints) via prune_restart MaxScore in 0.1s. Vol-37 lottery from 7 canonical partials in flight. [[vol-36]] |  |
|  37 |             — |       — | **Vol-37 closed (no record break)**: structural_scan.py + gh_e2.py + canonical 454 production. Found pos 161 (interior, x=1 y=10) = pid 234 rot 0 invariant across all 7 verified records (genuine cross-basin structural cell, NOT hint-adjacent). gh_e2 relaxation algorithm works but relaxation-gap dominates. Pos 161 synthetic-hint on vf 5min × 8t: +2 depth, +4 score (modest). Two mid-vol re-evaluations cancelled saturated lotteries. Canonical records unchanged: 457 (×3 blackwood_mrv), 456 (×2 blackwood_raw), 454 (new pathway). [[vol-37]] |  |
|  38 |             — |       — | **Vol-38 closed (honest null)**: prune-restart MaxScore on canonical 454 with drop-k ∈ {0, 20, 40}: best completion 431 (-23 vs 454 start). Canonical 454 mismatch region (38 cells) is structurally CP-uncompletable — no 256-completion of the dropped region beats 454. To break 454, need larger drop (>50% of board) OR change the SURROUNDING 218 cells (not just the mismatch cluster). [[vol-38]] |  |
|  39 |             — |       — | **Vol-39 closed (modest lift)**: ALNS-diverse (winning5 + BottomBandDestroy) 8 seeds × 5min from canonical 454 → 2 seeds reached **455** (NEW canonical record-class, +1 lift). Both 5/5 hints, piece-unique, distinct boards (54 cells differ). drop-100 prune-restart 60s: 138-cell refill too big for CP budget. [[vol-39]] |  |
|  40 |             — |       — | **Vol-40 closed (honest null)**: ALNS-diverse 24 runs (3 canonical 457 sources × 8 seeds × 5min) ALL stayed at 457. Confirms vol-22 "457 is ALNS-locked" finding even with BottomBandDestroy added. ALNS ceiling per basin ≈ +1 score; 454→458 requires ~4 chained lifts at decreasing probability. To break 458 need community-class compute or new algorithm. [[vol-40]] |  |
|  41 |             — |       — | **Vol-41 closed (positive signal, no record-break)**: ValueOrder::RecordsPrior SHIPPED. New engine variant ranks candidates by record-frequency from vol-37 structural_scan. A/B canonical E2 5min: +5-9 matched edges at iso-depth (171). Downstream ALNS-5min × 4 seeds: +8 mean, +16 best (3 of 4 seeds win). Best ALNS-completion 439/480 (below records). First positive engine-level signal in vol-37-41 series. Gate (≥5% depth lift) not met but consistent positive effect. [[vol-41]] |  |
|  42 |             — |       — | **Vol-42 closed (honest null + session close)**: McGavin 469 from community corpus decoded, applied make-canonical (drops to 443 = -26 score, since McGavin is 1-clue variant), ALNS-diverse × 4 seeds → all 4 reach 444 (deterministic +1 lift). Community 469 layout is structurally incompatible with our canonical 5-clue. **Autonomous session closes after 7 volumes (vol-36-42)**. Real outputs: 6 tools (vanilla_path, make_canonical, structural_scan, gh_e2, --extra-hint, RecordsPrior), 5 new canonical records (454, 455 ×2, 444), verify_records.sh 10/10 pass, honest nulls documented. Records UNCHANGED: 458 absolute, 457 canonical. [[vol-42]] |  |
|  43 |             — |       — | **Vol-43 reframing only**: 7 cross-domain reframings explored, no shipped record-mover. [[vol-43-reframing]] |  |
|  44 |             — |       — | **Vol-44 closed (rich research, no break)**: LP UB tool ships; 3 border-classes A/B/C UB 478/477/476; vol-32 458 basin PROVEN locally optimal under MIP cluster-repair (halo ≤ 2) and whole-interior MIP (196 cells, 1h). 458 border is LP-UB locally maximal under k≤3 perturbations. **Conclusion: 458 is firm in this basin; record break needs UB ≥ 479 basin.** [[vol-44]] |  |
|  45 |             — |       — | **Vol-45 closed**: CP search with LP UB-based pruning. Built but no record-class breakthrough. [[vol-45]] |  |
|  46 |             — |       — | **Vol-46 closed**: Per-class LP UB diagnostic. No record lever. [[vol-46]] |  |
|  47 |             — |       — | **Vol-47 closed (negative)**: Lifted LP McCormick formulation. Standard LP intractable at canonical scale; column-gen v1/v2 variants under/over-count match credit, both INVALID. Correct path = Lagrangian relaxation with cutting planes (multi-week). [[vol-47]] |  |
|  48 |             — |       — | **Vol-48 closed (negative)**: RL via vanilla Evolutionary Strategies (sigma=0.2). 4 rounds: collapsed to std=0.00 by R3 at 277/480 (−5 vs vol-29 imitation 282). ES fails on E2 value-order because engine argmax is structurally invariant to small policy perturbations. Infra (`crates/rl-search`) reusable. [[vol-48]] |  |
|  49 |             — |       — | **Vol-49 closed (negative)**: Adaptive-sigma ES (bumps to 2× when std<0.5). 6 rounds peak 280 at R3 then collapsed; bumps to 0.4 and 0.8 did not exceed 280 and destabilized. **Both ES variants finish BELOW imitation baseline** — ES degrades the model. Q-learning is the natural pivot (gradient on Q-values, not argmax). [[vol-49]] |  |
|  50 |             — |       — | **Vol-50 closed (net negative + infrastructure + math)**: 3 pivots — Q-learning design, then REINFORCE+Plackett-Luce via ONNX Gumbel (probe refuted via deterministic RandomUniformLike), then search-side. Shipped `SolveOpts.node_budget` engine axis + prune_restart `--node-budget` flag. A/B time-budget vs node-budget: same final partial (412 vs 410), 3× more wall for node-budget. ALNS-5min × 4 from 412 partial: best=428 (+4 vs vol-23 baseline 424). blackwood_raw + MRV 1h × 4 parallel **FAILED** (CPU oversubscription crushed each seed to depth 85-90 vs vol-32's 5min @ depth 190+). Math: LP-integer gap anatomy — 33% in fractional LP, 67% in piece-uniqueness joint-infeasibility. [[vol-50]] |  |
|  51 |             — |       — | **Vol-51 closed (modest infrastructure, no record)**: B1 bound-trigger prune-restart built and shipped — extracted `relaxed_bound` to bench-audit lib, added `--bound-trigger` and `--drop-k-bound-stall` flags to prune_restart, per-round bound logged. Empirical: trigger CORRECTLY fires when board is full + score stagnant; **recovery is the bottleneck** — drop k=60 + halo = 164 cells dropped, CP-MaxScore refills only 140 in 30s, score collapses to 188 from 412. Pivot to B3 engine profiling found vol-25 already did this comprehensively (7 fixes shipped, joe +22%, BLACKWOOD_RAW +27%); no further research-grade profiling work remains. Apples-to-apples: our vanilla_fast 125M nps single-thread vs McGavin 295M — only ~2.4× gap, not the "4000×" suggested by mismatched comparison. Standing 458 record unchanged. [[vol-51]] |  |
|  52 |             — |       — | **Vol-52 closed (design doc only)**: 400-line concept page on lifted-LP via per-piece column-generation. Structural alternative to vol-47's failed McCormick: keeps same LP variables, decomposes via Lagrangian per piece. Each subproblem ≤ 800 placements; master is LP. Expected to close 12 of 20 LP-integer-gap points (piece-uniqueness joint-infeasibility). Wouldn't directly break 458 (which vol-44 proved integer-optimal under MIP) but provides optimality certificates per basin + tighter CSP-search bound. Engineering: 7-10 days; flagged as candidate for vol-53+. No code shipped this vol; design-only per CLAUDE.md senior-researcher mode. [[vol-52]] |  |
|  53 |             — |       — | **Vol-53 closed (PARTIAL REFUTATION of vol-52)**: Python+highspy worked example on toy 2-3 cell LP instances. All toy cases LP=Integer (zero gap). Reveals the canonical-E2 20-point LP-integer gap doesn't come from piece-uniqueness fractionality alone — it comes from y-linearisation interacting with piece-uniqueness at scale. Per-piece column-gen alone won't close the gap; needs full branch-and-price-and-cut (revised estimate: 3-4 weeks, not 7-10 days). Standing 458 may be near-globally-optimal under search algorithms we have. [[vol-53]] |  |
|  54 |             — |       — | **Vol-54 closed (math resolution of vol-50 vs vol-53)**: built `per_color_integer` bin, filled the INTEGER column of vol-50's anatomy table. Confirms 5.96 fractional + 12 rounding = 17.96 II gap numerically. **BUT**: color 8 has INT=21 > floor(LP_UB)=20, proving `floor(LP_UB[k])` is NOT a per-color integer bound; vol-50's "12 from piece-uniqueness joint-infeasibility" interpretation refuted. Minimal 2-cell, 2-piece worked example (HiGHS verified) gives LP=1.0, INT=0, gap=1.0 — the actual mechanism is **cell-fractional x**, not rotation-fractional or piece-uniqueness slack. Vol-52 design now `refuted`: per-piece column-gen tightens rotations but doesn't restrict cell-level fractionality. Vol-44 MIP (1h) remains the cheapest tight bound. [[vol-54]] [[y-linearisation-cell-fractional-gap]] |  |
|  55 |             — |       — | **Vol-55 closed (MVP success: B&P-and-cut on canonical-E2)**: 3-hr build (per user "limiting thoughts" challenge), shipped `dump_cluster_for_lp` Rust bin + Python+highspy LP/MIP solver. Measured LP UB vs MIP optimum vs current-458 on 6 real canonical-E2 clusters. **LP-MIP gap is real**: 5×4 cluster has gap=3.31, 6×3 has gap=3.41 (confirms vol-54 mechanism on canonical data). **458 record is LOCALLY OPTIMAL on every cluster tested** (MIP=current for all 6, including the gap-3 clusters). The cell-fractional gap is LP looseness, NOT 458-suboptimality. Sharpens vol-44's single-cluster local-optimality to multi-cluster local-optimality. Standing 458 confidence substantially raised; remaining question is whether a higher-MIP basin exists. MIP runtime scales ~2× per added cell — full canonical-scale needs Rust + column-gen (vol-44 already did this in different form). [[vol-55]] |  |
|  56 |             — |       — | **Vol-56 closed (rich research, 8 deliverables)**: dual-track autonomous vol on CDCL no-good learning + structural discovery. (T2) `cdcl-no-good-e2.md` math design: hard/soft no-goods, soundness lemmas, soft-minimization non-monotone subtlety. (T3) Engine wipeout-distribution + repetition measurement: 46k wipeouts/60s, 67% position-set hashes unique, FULL hashes 100% unique. (T4) Python 6×6/5c proto: clauses median 6 literals, 96% of states have ready-to-fire clauses, avg 6.57 per node — **GREEN LIGHT for vol-57 CDCL Rust build**. (T6) `cdcl-engine-integration.md` solver-engine refactor design (Option A separate path). (T7) Row-10-12 bimodal family analysis: row 11 splits 6 records into 2 families perfectly. (T8) Row-11-swap experiment: -41 score, energy barrier exists. **T7 CORRECTION**: Family A = relaxed-canonical (3/5 hints, allows +1 score); Family B = strict-canonical (5/5 hints). The vol-32 458 record is on the 3-hint puzzle; strict-canonical record is 457. Lottery (T1) running 156 ALNS jobs in background. [[vol-56]] |  |
|  57 |             — |       — | **Vol-57 closed (CDCL Rust prototype)**: `crates/cdcl-proto` standalone crate. AC-3 with cause tracking + 1-UIP-equivalent + watch-filtered unit-prop. Algorithm validated; clauses median 8-9 lits on 6×6/5c. Wall-clock 2WL deferred to vol-58+. [[vol-57]] |  |
|  58 |             — |       — | **Vol-58 closed (extensive validation + canonical-scale failure)**: family-B 457 basin MIP-verified on 11 clusters, McGavin 469 basin verified on 9 clusters. Total **22 cluster MIPs across 3 basin families** all locally optimal. CDCL scaling 5×5→16×16: 7×7 PASS (3.4× wall-clock + finds where vanilla can't), canonical 16×16 FAIL (avg clause 96 lits, 0 unit-props). Our 458 matches Schaus & Deville 2008 academic SOTA. [[vol-58]] |  |
|  59 |             — |       — | **Vol-59 closed (lottery + CDCL scaling + theoretical 1-UIP analysis)**: basin lottery 156/156 jobs: 1×458 + 3×457, **no 459+ found, P(458)=0.64%**. CDCL scaling test confirms unit-prop hit rate crashes at 12×12+ due to clause-size growth. **THEORETICAL FINDING**: E2's cause-graph is FLAT (depth ≤ 2), so SAT-style 1-UIP collapses to what my naive code already does. Real fix isn't 1-UIP but redundant-cause elimination — a different (and possibly harder) analysis. Path to >458 narrowed: McGavin/Blackwood-class algorithm or fundamentally different paradigm. [[vol-59]] |  |
|  60 |         **459** |       — | **NEW LOCAL RECORD**: cross-machine SOTA replay produced 459/480 from p06 corner-perm + vanilla_fast + ALNS basic seed=42 30min. p06 partial = corner perm (1,0,2,3). All vol-32 458 + vol-44 458 + 2 sister basins now MIP-locally optimal (halo-1). |  |
|  61 |             459 |       — | Vol-61 SOTA replay calibration on vol-60 459 basin. ALNS lottery rich diagnostics; no 460. |  |
|  62-79 |       459 |       — | Vols 62-79: 8+ invented algorithms (Homotopy-ALNS, ComponentClusterDestroy, BLGS, FCD, OA-ALNS, RGS, CAS) all bounded ≤ 459. McGavin 469 fully decoded. New 469 board found (near-twin swap). σ-cycle indecomposability 459→469 (vol-65). Basin asymmetry (vol-68 top-row pinning). |  |
|  80 |             459 |       — | **Blackwood "lots of overlap" rationale REFUTED at single-seed**: 7-triple sweep, top-overlap triples scored worst (436-437), bottom-overlap best (446). 1-seed result; needs variance check. [[blackwood-triple-sweep]] |  |
|  82 |             459 |       — | **McGavin basin TOP-DETERMINING**: bottom-N pinning gives 443-462 vs top-N=14 → 469. Mismatch geometry: McGavin 11 mismatches concentrate in rows 0-4 (top 5). [[mcgavin-basin-top-bottom-symmetry]] [[mcgavin-469-mismatch-geometry]] |  |
|  83-101 |       459 |       — | **Local Rigidity Theorem proven**: 13+ MIP-PROVEN local-optimal regions across 3 basins. McGavin halo-1 (vol-83, 37 cells, 895s) → halo-2 per-comp (vol-92) → halo-3 per-comp (vol-94) → halo-4 comp 0 (vol-96, 57 cells = LARGEST). Local 459 halo-1 joint (vol-90, 59 cells, 1800s) + halo-2 per-comp (vol-93) + halo-4 per-comp (vol-100, comp 0 = 56 cells PROVEN). Vol-32 458 halo-2 per-comp (vol-95). First sound UB below 480 (vol-86: top-4 ≤ 123). σ-cycle indecomposability UNIVERSAL across 3 basin-pairs (vols 65/99/101). σ-cycles board-spanning (rows 1-14 × cols 1-14). McGavin near-twin orbit = exactly 2 boards (6555 perturbations tested, 0 give 470). Corner perm (3,2,0,1) UNIQUE 469 host across 1156-board corpus. PAPER: [[../PAPER_2026-05-16_canonical_E2_rigidity_theorem]]. Standing 459 unchanged after 10h autonomous. |  |


## Concepts — by category

### Engine / propagators
- [[gacolor]] — Régin alldiff per color (most powerful global)
- [[ac3]] — pairwise arc-consistency
- [[ns1-deficit]] — multiset-equality invariant (necessary, loose)
- [[bitset-domain-rep]] — vol-12 engine rewrite
- [[engine-profile-registry]] — registry of profiles (2 solver_ids × 7 heuristics)
- [[engine-perf-hot-paths]] — vol-25 flamegraph audit + 7 fixes (+22% joe, +27% BR)
- [[scan-order]] — variable-order axis (BorderFirstMRV, RowMajorBottomUp, …)
- [[mcgavin-engine]] — community throughput target (295M nps)

### Search algorithms
- [[blackwood-algorithm]] — heuristic-schedule + break-index backtracker (community 469)
- [[blackwood-schedule-calibration]] — empirical schedules from corpus
- [[blackwood-then-csp]] — pipeline composition (Variant K)
- [[prune-restart]] — Joe's in-place restart (vol-23 shipped)
- [[score-optimizing-cp]] — MaxScore B&B objective (vol-24 shipped)
- [[frame-first]] — vol-4 decomposition (border + interior)
- [[border-diversity]] — Las Vegas sampler + pin-perimeter

### Local search / metaheuristics
- [[alns]] — destroy-repair, 10-op portfolio
- [[parallel-tempering]] — PT chains; warm-record producer
- [[genetic-algorithm]] — vol-5 4×4 / 6×6 crossover
- [[oracle-cycle-swap]] — vol-18 cold-record producer (with hot-PT)
- [[basin-escape-recipe]] — vol-22 bound+Hungarian+ALNS pipeline
- [[ot-hungarian-repair]] — used inside basin-escape recipe

### Value-orders / message-passing
- [[bp-marginals]] — cell-encoding (refuted as standalone)
- [[edge-bp-marginals]] — vol-12 edge-color (partial-positive in pipeline)
- [[survey-propagation]] — refuted (cavity-method block)
- [[boundary-mps]] — vol-13 tensor network (refuted, 10¹⁰¹ overcounting)
- [[learned-value-order]] — vol-26 imitation-learning gate (540× engine-node reduction at 6×6/5c; bridge eats wall-clock)

### Structural / measurement
- [[mismatch-geometry]] — where errors live (universal mismatches, fracture threshold)
- [[rare-color-rule]] — opposite-edge invariant + border exclusivity
- [[selby-riordan-generator]] — the generator behind canonical E2
- [[synthetic-puzzle-generator]] — vol-26 Rust impl + JSONL exporter for synthetic E2-family puzzles
- [[mismatch-homology]] — vol-19 β_1 (small signal)
- [[z22-vertex-charge]] — vol-7 gauge fingerprint
- [[r5f-cooperativity]] — vol-18 76-cell barrier (KEY PHYSICS)
- [[trajectory-families]] — score-distance ≠ configuration-distance
- [[strain-cascade]] — vol-4 hypothesis (partly confounded with scan-order)
- [[hamilton-frame]] — 75k frames (partial, necessary-not-sufficient)

### Bounds / dead-end tests
- [[relaxed-bound]] — vol-21 basin-local ceiling (strictly stronger than K=5)
- [[bound-ascent]] — climb the bound landscape
- [[operator-lock]] — K ≤ 5 lock test (vol-20)
- [[inner-k-optimality]] — EvalMaxSAT proof for sub-regions
- [[exact-joint-bound]] — MaxSAT for joint optimum (z3 failed, kissat-RC2 unbuilt)
- [[lp-integer-gap-anatomy]] — vol-50 anatomy; vol-54 filled INT column + sharpened interpretation
- [[y-linearisation-cell-fractional-gap]] — **vol-54** precise gap mechanism (cell-fractional x, NOT rotation-fractional)
- [[lifted-lp-column-gen-per-piece]] — vol-52 design, **refuted at vol-54** (column-gen alone doesn't close cell-fractional gap)

### Pipelines / infrastructure
- [[basin-escape-recipe]] — vol-22 composite
- [[cold-portfolio]] — vol-17 parallel-chunk runner
- [[blackwood-then-csp]] — vol-17 Variant K

### Code quality
- [[code-debt]] — vol-25 restructure proposal (5 dup utils, solver-engine 5-module split, bin harness)

### Community / external
- [[community-corpus]] — 12k messages decoded, 123 boards
- [[mcgavin-engine]] — 295M nps target
- [[blackwood-algorithm]] — the algorithm behind 469
- [[verhaard-set-sa]] — 2008 set-composition swap-annealing
- [[eulerian-border]] — anr_56 2007 (refuted on canonical E2)
- [[mcgavin-blackwood-gap-analysis]] — 4 orthogonal gaps to 469

### Bugs / postmortems
- [[hint-pinning-bug]] — vol-14 ALNS unpinning canonical hints (fixed `afb3dc9`)

### Refuted / do-not-revisit
- [[dead-ends]] — SP, IsingFormer, GPU/FPGA SAT (cross-domain agent verdicts)
- [[survey-propagation]] — theoretical block
- [[boundary-mps]] — 10¹⁰¹ overcounting gap
- [[eulerian-border]] — vacuous on canonical E2
- [[blackwood-layered-depth-wall]] — schedule wall structural

## Basins — notable boards

| Basin | Score | Status |
|---|---:|---|
| [[basin-449-plateau]] | 449 | historic floor (cell-CP) |
| [[basin-450-vol4]] | 450 | first break (frame-first) |
| [[basin-453-vol5]] | 453 | GA-LARGE record |
| [[basin-454-vol6]] | 454 | **historic warm record** |
| [[basin-443-vol14]] | ~440 | vol-14 (post-fix invalidated) |
| [[basin-447-top-row]] | 447 | vol-17 calibrated_v17a |
| [[basin-457-pt]] | **457** | **current cold record** (vol-18 hot-PT) |
| [[basin-440-469]] | 440 | vol-22 fresh, ceiling 469 |
| [[basin-blackwood-470]] | 470 | community, 1-clue variant (NOT canonical) |
| [[basin-mcgavin-469]] | 469 | **community canonical 5-clue ceiling** |

## Sessions

- [[sessions/vol-01]] through [[sessions/vol-54]] — per-volume journals
- [[sessions/night-05]], [[sessions/night-07]] — preprint + closeout distillations
- `sessions/archive/raw/` — original RESEARCH_NOTES_*.md, NIGHT*.md, V15_BLACKWOOD_SPEC.md

## Memory crosswalk

- [[reference/memory-crosswalk]] — map of `~/.claude/.../memory/*.md` → vault pages

## Discipline

- Audit-at-open every new volume.
- Concepts carry durable knowledge; sessions are journals.
- No quiet deletes — `status: refuted` with evidence link.
- Discoveries mid-vol → BACKLOG, not pivots.
