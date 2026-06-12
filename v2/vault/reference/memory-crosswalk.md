---
tags: [reference, crosswalk]
date: 2026-05-20
covers: 128 memory entries
---

# Memory ↔ vault crosswalk

Maps every file in `~/.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/` to the vault page(s) that cite or supersede it.

The memory layer is the **persistent agent memory** (loaded in every conversation). The vault layer is the **researcher knowledge base** (Obsidian, navigable by human). They overlap; the vault carries more structure.

**Discipline**: when a memory entry is fully absorbed into a vault page, the memory entry should be either (a) trimmed to a one-line pointer or (b) left as the canonical reference. Either is fine; the vault should always be reachable from the memory file's `[[wikilink]]` tags.

> Updated 2026-05-20 (vol-188). Previous version covered vol-13 era only; this rewrite covers all 128 current memory entries.

---

## Feedback (binding directives, cross-cutting)

| Memory | Vault | Notes |
|---|---|---|
| `feedback_e2_senior_researcher_mode` | [[REMINDER_USER_DIRECTIVES]], CLAUDE.md | binding directive #1 |
| `feedback_e2_inventor_mode` | [[REMINDER_USER_DIRECTIVES]] | binding directive #2 |
| `feedback_e2_one_invention_per_volume` | CLAUDE.md, [[plans/CURRENT-VOL]] | one named algo per vol |
| `feedback_e2_no_textbook_symmetry_breaking` | [[E2_KNOWN_FACTS]] §Symmetries | canonical E2 has NO symmetries |
| `feedback_vols_61_to_70_invented_algos` | [[sessions/TIMELINE]] Era VI | each vol 62+ has named algo |
| `feedback_vols_106_115_blank_puzzle_speedup` | [[DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP]], [[SYNTHESIS_VOLS_106-115_2026-05-16]] | speedup+invention directive |
| `feedback_autonomous_dont_wait` | (cross-cutting) | never end turn listing options |
| `feedback_multi_week_projects_allowed` | (cross-cutting) | RL self-play, B&P&C, etc. in scope |
| `feedback_clean_slate_also_valued` | (cross-cutting) | balance basin-attack with clean-slate |
| `feedback_from_scratch_preference` | (cross-cutting) | prefer constructive-from-scratch |
| `feedback_invent_cross_domain` | (cross-cutting) | try waves/lights/images lenses |
| `feedback_8_cores_max` | (cross-cutting) | 8 cores allowed (was 7) |
| `feedback_depth_over_quick_pocs` | (cross-cutting) | math first → clean code → docs |
| `feedback_no_false_metrics` | [[relaxed-bound]] | relaxed_bound is NOT a UB |
| `feedback_never_overwrite_results` | (cross-cutting) | timestamps in output paths |
| `feedback_fix_broken_code` | (cross-cutting) | fix > workaround |
| `feedback_no_limiting_thoughts` | CLAUDE.md | "2-week" PoC usually overnight-doable |
| `feedback_no_self_time_estimates` | CLAUDE.md | verify with `date`/`etime` |
| `feedback_research_mindset` | (cross-cutting) | innovate, take time, reformulate |
| `feedback_use_uv_for_python` | CLAUDE.md | uv pip install / uv run |
| `feedback_use_latex_for_math` | (cross-cutting) | `$inline$` / `$$display$$` |

---

## Project state and ceiling

| Memory | Vault |
|---|---|
| `project_e2_state` | [[E2_KNOWN_FACTS]], [[INDEX]], [[SYNTHESIS_VOL_188]] |
| `project_e2_dead_ends` | [[dead-ends]] |
| `project_e2_2026_05_16_rigidity_theorem` | [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]], [[_umbrella-mcgavin-mip-proofs]] |
| `project_e2_mcgavin_blackwood_gap_analysis` | [[mcgavin-blackwood-gap-analysis]] |

---

## Standing records (chronological)

| Memory | Score | Vol | Vault basin |
|---|---:|---:|---|
| `project_e2_459_sota_cross_machine` | 459 | 60 | [[basin-459-p06]] |
| `project_e2_record_break_458_2026_05_17` | 458 strict | 122 | [[E2_KNOWN_FACTS]] §Records |
| `project_e2_strict_record_459_2026_05_18` | 459 strict | 122 DB | (DB find) |
| `project_e2_record_460_2026_05_18` | 460 | 125 | [[basin-461-cp1203-v125]] (sibling) |
| `project_e2_record_461_2026_05_18` | 461 | 125 | [[basin-461-cp1203-v125]] |
| `project_e2_new_461_off5428_2026_05_19` | 461 | 125 | [[basin-461-cp1203-v125]] (alt off) |
| `project_e2_record_463_2026_05_19` | **463** | 129 | [[basin-463-cp2301-v129]] |
| `project_e2_v175_458_new_basin_2026_05_20` | 458 (new cp) | 175 | [[basin-458-cp3012-v175]] |
| `project_e2_v181_460_new_basin_2026_05_20` | 460 (new cp) | 181 | [[basin-460-cp0312-v181]] |

---

## Structural / measurement findings

| Memory | Vault |
|---|---|
| `project_e2_ns1_deficit_invariant` | [[ns1-deficit]] |
| `project_e2_rare_opposite_rule` | [[rare-color-rule]] |
| `project_e2_rare_color_geography` | [[rare-color-rule]] (statement 3, border exclusivity) |
| `project_e2_hamilton_frame_count` | [[hamilton-frame]] |
| `project_e2_edge_bp_measurement` | [[edge-bp-marginals]] |
| `project_e2_mps_relaxation_null` | [[boundary-mps]] |
| `project_e2_blackwood_layered_depth_wall` | [[blackwood-layered-depth-wall]] |
| `project_e2_piece_set_symmetries` | [[piece-set-symmetries]], [[E2_KNOWN_FACTS]] §Symmetries |
| `project_e2_intaglio_2x2_finding` | [[intaglio-attack-lex]], [[forbidden-patch-theorem-2026-05-19]] |
| `project_e2_k11_basin_signatures` | [[k11-basin-signatures]], [[PAPER_2026-05-17_vol122_basin_diversity_and_rigidity]] |
| `project_e2_three_basin_iso_plateau_2026_05_20` | [[three-basin-iso-plateau]] |
| `project_e2_18_basin_families_2026_05_19` | [[corner-permutation-study]] |
| `project_e2_seed1_seed13_same_basin_2026_05_20` | (σ-cycle artifact; see [[sigma-cycle-universal-indecomposable]]) |
| `project_e2_v169_weakness_probe_2026_05_20` | [[prior-guided-alns]] |
| `project_e2_v172_cp1230_cp1203_overlap_2026_05_20` | [[chiasmus-basin-crossover]] |
| `project_e2_v125_t34_fpl_probe_result` | [[fpl-frozen-pair-lifting]] (refuted) |
| `project_e2_vol130_filament_result_2026_05_19` | [[filament-lk-2d]] |
| `project_e2_vol65_oracle_sigma_indecomposable` | [[sigma-cycle-universal-indecomposable]], [[piece-side-matching]] |
| `project_e2_vol65_orientation_asymmetry` | [[piece-orbit-structure]] |
| `project_e2_vol65_sister_basin_sigma_cycles` | [[basin-permutation-group]] |
| `project_e2_vol68_mcgavin_rigidity` | [[mcgavin-basin-rigidity]] |
| `project_e2_vol68_n_row_scaling` | [[mcgavin-n-row-scaling]] |
| `project_e2_vol62_mip_local_optimality` | [[mip-local-optimality-459]] |
| `project_e2_vol55_local_optimality_multi_cluster` | [[concepts/_umbrella-mcgavin-mip-proofs]], [[sessions/vol-55]] |

---

## From-scratch builder era (vols 155+)

| Memory | Vault |
|---|---|
| `project_e2_from_scratch_456_2026_05_19` | [[prior-data-augmented-beam]] |
| `project_e2_from_scratch_460_2026_05_19` | [[prior-data-augmented-beam]], [[v155-finding-prior-lift]] |
| `project_e2_v156_460_pipeline_2026_05_19` | [[sessions/vol-156]] |

---

## Volume sessions

Listed in vol order. Empty cells = no dedicated concept (memory IS the canonical record for that finding).

| Memory | Vault session | Vault concept(s) |
|---|---|---|
| `project_e2_vol12_engine_profiles` | [[vol-12]] | [[engine-profile-registry]], [[ns1-deficit]], [[bitset-domain-rep]] |
| `project_e2_vol14_*` (14 entries) | [[vol-14]] | [[hint-pinning-bug]], [[edge-bp-marginals]], [[frame-first]], [[hamilton-frame]], [[scan-order]], [[mismatch-geometry]], [[basin-443-vol14]], [[alns]], [[pt-tabu]], [[parallel-tempering]] |
| `project_e2_vol15_blackwood_results` | [[vol-15]] | [[blackwood-algorithm]], [[engine-profile-registry]] |
| `project_e2_vol16_cleanup_anchor` | [[vol-16]] | [[engine-profile-registry]] |
| `project_e2_vol16_closeout` | [[vol-16]] | [[bitset-domain-rep]], [[ac3]] |
| `project_e2_vol17_blackwood_then_csp` | [[vol-17]] | [[blackwood-then-csp]] |
| `project_e2_vol17_447_top_mismatch` | [[vol-17]] | [[basin-447-top-row]] |
| `project_e2_vol17_r4_piece_mi` | [[vol-17]] | [[rare-color-rule]] |
| `project_e2_vol17_session_summary` | [[vol-17]] | (entry point) |
| `project_e2_vol18_457_record` | [[vol-18]] | [[basin-457-pt]], [[oracle-cycle-swap]] |
| `project_e2_vol18_456_unreplicable` | [[vol-18]] | [[trajectory-families]] |
| `project_e2_vol18_r3_ot_null` | [[vol-18]] | [[ot-hungarian-repair]] |
| `project_e2_vol18_r5_homology` | [[vol-18]], [[vol-19]] | [[mismatch-homology]] |
| `project_e2_vol18_r5f_cooperativity` | [[vol-18]] | [[r5f-cooperativity]] |
| `project_e2_vol18_trajectory_families` | [[vol-18]] | [[trajectory-families]] |
| `project_e2_vol18_puzzle_reduction_null` | [[vol-18]] | (minor null, no separate page) |
| `project_e2_vol18_457_operator_locked` | [[vol-18]] | [[operator-lock]] |
| `project_e2_vol20_backbone_correction` | [[vol-20]] | [[mismatch-geometry]] |
| `project_e2_vol20_operator_lock` | [[vol-20]] | [[operator-lock]], [[basin-457-pt]] |
| `project_e2_vol21_edge_relax_bound` | [[vol-21]] | [[relaxed-bound]] |
| `project_e2_vol22_basin_escape` | [[vol-22]] | [[basin-escape-recipe]] |
| `project_e2_vol23_prune_restart` | [[vol-23]] | [[prune-restart]] |
| `project_e2_vol23_x_skeleton_null` | [[vol-23]] | (null; see session) |
| `project_e2_vol24_score_optimizing_cp` | [[vol-24]] | [[score-optimizing-cp]], [[prune-restart]] |
| `project_e2_vol25_perf_push` | [[vol-25]] | [[engine-perf-hot-paths]], [[code-debt]] |
| `project_e2_vol26_learned_value_order` | (no session) | [[learned-value-order]] |
| `project_e2_vol27_onnx_gate_pass` | (no session) | [[learned-value-order]] |
| `project_e2_vol28_transfer_refuted` | (no session) | [[learned-value-order]] |
| `project_e2_vol29_imitation_ceiling` | (no session) | [[learned-value-order]] |
| `project_e2_vol30_first_ml_canonical_lift` | (no session) | [[learned-value-order]] (refuted) |
| `project_e2_vol31_ml_score_lift` | (no session) | [[learned-value-order]] (refuted) |
| `project_e2_vol32_*` (5 entries) | [[vol-32]] | [[learned-value-order]] bug, [[unsat-clause-propagator]], InsertionOrder finding, pt-saturation |
| `project_e2_vol34_polish_swap_bug` | [[vol-34]] | (bug fix in alns_only) |
| `project_e2_vol35_landscape` | [[vol-35]] | [[fitness-landscape-mapping]] |
| `project_e2_vol35_pin_hints_bug` | [[vol-35]] | (pin_hints duplicate-piece bug) |
| `project_e2_vol36_make_canonical_operator` | [[vol-36]] | [[make-canonical-operator]] |
| `project_e2_vol36_vanilla_path` | [[vol-36]] | [[vanilla-v2]] |
| `project_e2_vol37_pos161_invariant` | [[vol-37]] | [[structural-scan-pos161]] |
| `project_e2_vol48_49_es_refuted` | [[vol-48]], [[vol-49]] | (RL ES refutation) |
| `project_e2_vol56_58_session` | [[vol-56]], [[vol-57]], [[vol-58]] | [[cdcl-no-good-e2]], [[cdcl-engine-integration]] |
| `project_e2_vol106_blackwood_fast` | [[vol-106]] | [[blackwood-fast]], [[rust-perf-at-scale]] |

---

## Engineering todo

| Memory                       | Vault                                                |
| ---------------------------- | ---------------------------------------------------- |
| `project_todo_engine_bitset` | [[bitset-domain-rep]] (DONE)                         |
| `project_e2_vol25_perf_push` | [[engine-perf-hot-paths]], [[code-debt]], [[vol-25]] |

---

## Reference

| Memory | Vault |
|---|---|
| `reference_community_e2_ceiling` | [[community-corpus]], [[basin-mcgavin-469]], [[community-e2-history]] |
| `reference_blackwood_decoded` | [[basin-blackwood-470]], [[blackwood-algorithm]] |
| `reference_verhaard_actual_method` | [[verhaard-set-sa]] |
| `reference_e2_bp_measurements` | [[bp-marginals]] |
| `reference_e2_community_corpus` | [[community-corpus]] |
| `reference_e2_corpus_480_false_positives` | [[basin-mcgavin-469]] §Confounds, [[community-corpus]] |
| `reference_external_brainstorm_2026_05_18` | [[plans/EXTERNAL_BRAINSTORM_2026-05-18]] |

---

## Discipline note

When **adding new findings** in future volumes:
1. Save the memory entry as usual.
2. Update the relevant vault concept page with the new measurement.
3. Add a row in this crosswalk.
4. If a wholly new concept emerges, create a new vault page + add to [[INDEX]].

This ensures the vault stays **complete and discoverable** while memory stays **agent-loadable**.
- `project_e2_vol217_staged_fullboard_2026_06_12.md` → [[staged-fullboard-construction]], [[crossing-oracle]], [[vol-217]]
- `feedback_e2_no_8x8_enumeration.md` → BACKLOG `8x8-exact-counting-rig` (wont-do, user directive 2026-06-12)
