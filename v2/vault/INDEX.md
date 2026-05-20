---
tags: [moc, index]
date: 2026-05-20
vol: 188
---

# E2 Research Vault — Map of Content

The Obsidian landing page. Open any wikilink to navigate.

> Last rewrite: 2026-05-20 (vol-188 close). The old per-vol score-history table moved to [[sessions/TIMELINE]].

---

## Where to start

| Reading order | Document | Why |
|---|---|---|
| 1 | [[REMINDER_USER_DIRECTIVES]] | binding rules from the user (2026-05-17). |
| 2 | [[SYNTHESIS_VOL_188]] | master synthesis — state of the project at vol-188. |
| 3 | [[E2_KNOWN_FACTS]] | numerical facts at a glance. |
| 4 | [[plans/CURRENT-VOL]] | what the active volume is doing. |
| 5 | [[sessions/TIMELINE]] | vol-1..188 timeline, era-grouped. |
| 6 | [[plans/INVENTIONS_BACKLOG]] | the systematic list of unexplored attacks. |

---

## Standing state (vol-188)

- **Matched-edges record**: **463/480** (vol-129 PALIMPSEST, cp=(2,3,0,1)).
- **Strict-canonical record (5/5 hints)**: **459/480** (vol-122 DB-find).
- **Community ceiling**: **469/480** (McGavin 2020, canonical 5-clue).
- **Three-basin iso-plateau** at 458–460 (V175, vol-60, V181) — structurally locked under all known local ops. See [[concepts/three-basin-iso-plateau]].
- **18 corner-perms** carry ≥ 458; **5** reach ≥ 460. 13 cps unexplored at ≥ 460. → [[plans/CURRENT-VOL]] (vol-189 CORTEZ).

---

## Vault structure

```
vault/
├── INDEX.md, README.md, REMINDER_USER_DIRECTIVES.md  ← entry
├── E2_KNOWN_FACTS.md, SYNTHESIS_VOL_188.md           ← capstones
├── PAPER_*.md, MATH_NOTES_*.md                       ← papers/notes
├── concepts/   ← 344 durable algorithm/finding pages (umbrellas start with `_`)
├── basins/     ← 17 notable boards
├── sessions/   ← per-volume journals, TIMELINE.md spine, archive/raw/
├── plans/      ← BACKLOG, CURRENT-VOL, INVENTIONS_BACKLOG, etc.
└── reference/  ← memory-crosswalk and mirrors of authoritative refs
```

---

## Papers & math notes (root)

- [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]] — local rigidity theorem (vols 83-101).
- [[PAPER_2026-05-16_459_indecomposability_synthesis]] — 3-layer 459-ceiling characterization.
- [[PAPER_2026-05-17_vol122_basin_diversity_and_rigidity]] — basin diversity + rigidity.
- [[MATH_NOTES_2026-05-16_459_LEVEL_SET]] — 459-level set framework.
- [[MATH_NOTES_2026-05-16_SIGMA_SUBSET_THEOREM]] — σ-subset theorem.
- [[SYNTHESIS_VOLS_106-115_2026-05-16]] — vols 106-115 synthesis (blank-puzzle speedup).
- [[LAB_NOTES_2026-05-16]], [[IDEAS_FROM_BLANK_2026-05-16]], [[DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP]] — vol-106-era materials.
- [[AUDIT_2026-05-20]] / [[CONCEPT_TRIAGE_2026-05-20]] — this synthesis pass's working docs.

---

## Concepts — by category

### Umbrellas (start here for clusters)

- [[concepts/_umbrella-vol122-experiments]] — 19 vol-122 sub-experiments.
- [[concepts/_umbrella-j1-builder-attempts]] — 18 J1 builder variants.
- [[concepts/_umbrella-mcgavin-mip-proofs]] — 18 McGavin rigidity cuts.
- [[concepts/_umbrella-cas]] — CAS cluster (refuted as greedy).

### Engine / propagators

- [[concepts/gacolor]] — Régin alldiff per color (most powerful global).
- [[concepts/ac3]] — pairwise arc-consistency.
- [[concepts/ns1-deficit]] — multiset-equality invariant (necessary, loose).
- [[concepts/bitset-domain-rep]] — vol-12 engine rewrite.
- [[concepts/engine-profile-registry]] — 2 solver_ids × 7 heuristics.
- [[concepts/scan-order]] — variable-order axis.
- [[concepts/mcgavin-engine]] — community throughput target (295M nps).
- [[concepts/blackwood-fast]] — our 85M nps single-thread engine.
- [[concepts/rust-perf-at-scale]] — perf notes.

### Search algorithms

- [[concepts/blackwood-algorithm]] — schedule + break-index backtracker (community 469).
- [[concepts/blackwood-schedule-calibration]]
- [[concepts/blackwood-then-csp]] — pipeline composition.
- [[concepts/prune-restart]] — Joe's in-place restart.
- [[concepts/score-optimizing-cp]] — MaxScore B&B objective.
- [[concepts/frame-first]] — border + interior decomposition.
- [[concepts/border-diversity]] — Las Vegas sampler.

### Local search / metaheuristics

- [[concepts/alns]] — destroy-repair, 10-op portfolio.
- [[concepts/parallel-tempering]] — PT chains.
- [[concepts/genetic-algorithm]] — 4×4 / 6×6 crossover.
- [[concepts/oracle-cycle-swap]] — vol-18 cold-record producer.
- [[concepts/basin-escape-recipe]] — vol-22 composite.
- [[concepts/ot-hungarian-repair]]
- [[concepts/prior-guided-alns]] — V169 OPHIDIA.
- [[concepts/v179-large-k-destroy]] — V179 LARGE-K.
- [[concepts/intaglio-attack-lex]] — V180 lex-ordered acceptance.
- [[concepts/chiasmus-basin-crossover]] — refuted.

### Builders (constructive, vol-150+)

- [[concepts/prior-data-augmented-beam]] — V155 PRIOR.
- [[concepts/stigma-pheromone-adjacency]] — V178 STIGMA.
- [[concepts/keyring-patch-prior]] — V181 KEYRING (production).
- [[concepts/murmuration-basin-sampling]] — V171 Gumbel-beam.
- [[concepts/spectral-border-signature]] — V178 border-spectral.
- [[concepts/neuronic-ranker]] — exploratory ML ranker.
- [[concepts/bidirectional-meet-in-middle]] — refuted at V184.

### Value-orders / message-passing

- [[concepts/bp-marginals]] — refuted as standalone.
- [[concepts/edge-bp-marginals]] — partial-positive in pipeline.
- [[concepts/survey-propagation]] — refuted.
- [[concepts/boundary-mps]] — refuted (overcounting).
- [[concepts/learned-value-order]] — ML imitation gate.

### Structural / measurement

- [[concepts/piece-side-matching]] — PSM polytope.
- [[concepts/piece-orbit-structure]]
- [[concepts/piece-set-symmetries]] — 0 rotation-symmetric, 5 multiset twins.
- [[concepts/piece-spectral-fiedler]] — Fiedler = frame/interior.
- [[concepts/mismatch-geometry]]
- [[concepts/rare-color-rule]] — Selby-Riordan invariant.
- [[concepts/selby-riordan-generator]]
- [[concepts/r5f-cooperativity]] — vol-18 76-cell barrier.
- [[concepts/hamilton-frame]] — 75k frames lower bound.
- [[concepts/z22-vertex-charge]] — vol-7 gauge fingerprint.
- [[concepts/three-basin-iso-plateau]] — current standing rigidity finding.
- [[concepts/row-level-rigidity]] — vol-186 1/2/3-row rigidity.
- [[concepts/sigma-cycle-universal-indecomposable]] — universal cross-basin obstruction.
- [[concepts/corner-permutation-study]] — 18-cp basin taxonomy.
- [[concepts/v187-intaglio-mip]] — MIP rigidity probes on V181 460.
- [[concepts/v188-translation-sigma-indecomposability]] — V181↔McGavin σ-transport refutation.
- [[concepts/k11-basin-signatures]] — λ_2 + mz basin discriminator.

### Bounds / dead-end tests

- [[concepts/relaxed-bound]] — basin-local ceiling (NOT a true UB).
- [[concepts/bound-ascent]] — climb the bound landscape.
- [[concepts/inner-k-optimality]] — EvalMaxSAT proof for sub-regions.
- [[concepts/exact-joint-bound]] — joint MIP optimum.
- [[concepts/lp-integer-gap-anatomy]] — vol-50 anatomy.
- [[concepts/y-linearisation-cell-fractional-gap]] — vol-54 precise gap mechanism.
- [[concepts/lifted-lp-column-gen-per-piece]] — vol-52 design, refuted at vol-54.
- [[concepts/board-wide-ub-derivation]] — subset-bound caveat.
- [[concepts/corpus-restricted-region-mip-locked]] — vol-119 invention.
- [[concepts/sigma-subset-bound-empirically-tight]]
- [[concepts/forbidden-patch-theorem-2026-05-19]] — INTAGLIO theory.

### Bugs / postmortems

- [[concepts/hint-pinning-bug]] — vol-14 ALNS unpinning canonical hints.
- [[concepts/bf-candidate-bucket-bug]] — vol-118 edge pieces at interior cells.
- [[concepts/dead-ends]] — central refuted-approaches registry.

---

## Basins — notable boards

| Basin | Score | cp | Status |
|---|---:|---|---|
| [[basins/basin-449-plateau]] | 449 | — | historic floor (cell-CP) |
| [[basins/basin-450-vol4]] | 450 | — | first break (frame-first) |
| [[basins/basin-453-vol5]] | 453 | — | GA-LARGE record |
| [[basins/basin-454-vol6]] | 454 | — | historic warm record |
| [[basins/basin-443-vol14]] | ~440 | — | vol-14 (post-fix invalidated) |
| [[basins/basin-447-top-row]] | 447 | — | vol-17 calibrated_v17a |
| [[basins/basin-457-pt]] | 457 | — | vol-18 hot-PT cold record |
| [[basins/basin-440-469]] | 440 | — | vol-22 basin, ceiling 469 (oracle path) |
| [[basins/basin-459-p06]] | 459 | (1,0,2,3) | vol-60 local cold record |
| [[basins/basin-459-pt]] | 459 | — | PT-found 459 sister |
| [[basins/basin-458-cp3012-v175]] | 458 | (3,0,1,2) | vol-175 new basin (V175 GAUNTLET) |
| [[basins/basin-458-sweep-p18]] | 458 | — | vol-119 sweep_p18_s2 (structurally distant) |
| [[basins/basin-460-cp0312-v181]] | 460 | (0,3,1,2) | vol-181 new basin (V181 KEYRING) |
| [[basins/basin-461-cp1203-v125]] | 461 | (1,2,0,3) | vol-125 (A1 closure) |
| [[basins/basin-463-cp2301-v129]] | **463** | (2,3,0,1) | **vol-129 current matched record** |
| [[basins/basin-blackwood-470]] | 470 | — | community, 1-clue variant (NOT canonical) |
| [[basins/basin-mcgavin-469]] | 469 | (3,2,0,1) | community canonical ceiling |

---

## Plans + discipline

### Active (3 canonical)

- [[BACKLOG]] — canonical T-list across volumes.
- [[INVENTIONS_BACKLOG]] — systematic list of unexplored attacks.
- [[CURRENT-VOL]] — active vol's binding items.

### Archive

- `plans/archive/` — per-vol plans (VOL-26..VOL-60) + date-stamped scratch from vol-122-146 era. See [[plans/archive/README]].

### Discipline

- [[README]] — vault discipline (audit-at-open, concept-first, no quiet deletes).

---

## Sessions

- [[sessions/TIMELINE]] — the spine: vol-1..188 era-grouped one-liners.
- [[sessions/vol-188]], [[sessions/vol-187]], [[sessions/vol-186]], … — per-vol journals.
- `sessions/archive/raw/` — RESEARCH_NOTES_*.md, NIGHT*.md, V15_BLACKWOOD_SPEC.md.

---

## Reference

- [[reference/memory-crosswalk]] — `~/.claude/.../memory/*.md` ↔ vault pages.
- [[reference/reference-blackwood-decoded]]
- [[reference/reference-community-e2-ceiling]]
- [[reference/reference-verhaard-actual-method]]

---

## Discipline (per README)

- **Audit-at-open** every new volume — see [[plans/BACKLOG]].
- **Concepts** carry durable knowledge; **sessions** are journals.
- **No quiet deletes** — `status: refuted` with evidence link.
- **Discoveries mid-vol** → BACKLOG entries, not pivots.
- **Take notes AS YOU GO** — every non-trivial finding → session or concept page at the moment it occurs.
