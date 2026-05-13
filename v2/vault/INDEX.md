---
tags: [moc, index]
---

# E2 Research Vault — Map of Content

The Obsidian landing page. Click any wikilink to navigate.

## Quick orientation

- **Goal**: solve canonical 5-clue Eternity II (16×16 Monckton piece set) — score 480/480.
- **Community ceiling**: 469/480 ([[basin-mcgavin-469|McGavin 2020]] via Blackwood algorithm).
- **Our current cold-start record**: 457/480 ([[basin-457-pt]]).
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

### Structural / measurement
- [[mismatch-geometry]] — where errors live (universal mismatches, fracture threshold)
- [[rare-color-rule]] — opposite-edge invariant + border exclusivity
- [[selby-riordan-generator]] — the generator behind canonical E2
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
