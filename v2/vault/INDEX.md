---
tags: [moc, index]
---

# E2 Research Vault — Map of Content

The Obsidian landing page. Click any wikilink to navigate.

## Quick orientation

- **Goal**: solve canonical 5-clue Eternity II (16×16 Monckton piece set) — score 480/480.
- **Community ceiling**: 469/480 ([[basin-mcgavin-469|McGavin 2020]] via Blackwood algorithm).
- **Our current cold-start record**: 458/480 (vol-32 vanilla_fast + ALNS).
- **Our current warm-start record**: 454/480 ([[basin-454-vol6]], historic vol-6).
- **Gap to community**: 12 points; characterised in [[mcgavin-blackwood-gap-analysis]].
- **Spec contract**: `v2/V2_DESIGN.md`.
- **Project guide**: `v2/CLAUDE.md`.

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

- [[sessions/vol-01]] through [[sessions/vol-25]] — per-volume journals
- [[sessions/night-05]], [[sessions/night-07]] — preprint + closeout distillations
- `sessions/archive/raw/` — original RESEARCH_NOTES_*.md, NIGHT*.md, V15_BLACKWOOD_SPEC.md

## Memory crosswalk

- [[reference/memory-crosswalk]] — map of `~/.claude/.../memory/*.md` → vault pages

## Discipline

- Audit-at-open every new volume.
- Concepts carry durable knowledge; sessions are journals.
- No quiet deletes — `status: refuted` with evidence link.
- Discoveries mid-vol → BACKLOG, not pivots.
