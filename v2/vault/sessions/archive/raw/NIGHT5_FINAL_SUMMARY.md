# Night 5 final summary — score 449 → 453, two breakthroughs

**For**: morning user. **Time**: ~06:25 CEST (Tue 2026-05-12).
**Status**: cascade-453 still running (~30 min remaining).

## Score trajectory

| Time | Score | Method |
|---|---|---|
| start | 449/480 | canonical CP→PT (vol-2 baseline) |
| ~01:35 | 450/480 | NE1 frame-first reproduced vol-4 best |
| 03:04 | **452/480** | GA-light cross #4 (4×4 region top-right) |
| 05:47 | **453/480** | GA-LARGE cross #37 (4×4 region top-left, different parents) |

Total improvement: **+4 over the night**.

## Boards produced

- **24 boards at 451+** (1 × 453 in basin A + 1 × 453 in basin B + ~10 × 452 + ~12 × 451).
- **At least 4 distinct 451+ basins** identified by pairwise overlap.
- **2 distinct 453 boards** with 76% mutual overlap — different basins.

## Key files

- **`output/HISTORIC_first_453_1778557672.json`**: the night's record (453/480, 27 mismatches, 0 piece duplicates, 256/256 cells, validated).
- **`output/HISTORIC_first_452_1778547973.json`**: first 452 (28 mismatches).
- **`output/HISTORIC_453_cascade453_*.json`**: the second 453 from cascade.
- All others in `output/HISTORIC_*.json`.

## What worked

| Method | Outcome | Rate |
|---|---|---|
| GA crossover, K=4×4, mixed-class parents | Produces 451+ reliably | 8-20% per attempt |
| GA crossover with 453 in parent pool | Produces 452-class neighbors | 25-57% |
| Frame-first + top-6-match selection | Reproduced 450 baseline | n/a |

## What didn't work (with rigorous evidence)

- **Soft penalty (NE2) on top-6**: redistributes defects, conserves 30-budget.
- **Inner-loop penalty (NE2.1)**: monotonically over-constrains.
- **Wauters TA Hungarian + TSR (Salassa polish)**: 0 imp on PT-derived 450 (tested 290k 2-swaps + 2M 3-cycles + 460k 4-cycles + 1.35M 5-cycles → all 0).
- **Salassa max-clique RO**: perfect-fill maxima smaller than current placement on PT boards.
- **NE-BP on edge-color encoding**: paramagnetic fixed point, no signal.
- **EvalMaxSAT on full WCNF**: 1h22m, no `o` lines.
- **Iterative-deepening forbidden set**: 3 rounds, no improvement.
- **Random-fill PT (no CP)**: plateaus at 439 (10 below CP-seeded).

## Top 10 publishable structural findings

1. **Asymmetric hint at (7,8) creates the south-central strain cascade** — quantified across 29-board corpus, defect density peaks at L1 distance 6-8.
2. **All 22 colors have even count**: puzzle theoretically fully matchable (480/480).
3. **Rare-vs-abundant inversion**: rare colors 1-5 are 100% matched on every plateau board (29/29); ALL plateau mismatches are between abundant colors (6-22).
4. **Defect redistribution under soft penalty**: NE2 K-sweep moves defects but conserves total count. NE2-iter 3 rounds: same.
5. **30-mismatch budget is NOT a hard floor** — broken to 28 (452) and 27 (453) by GA crossover.
6. **Empirical Hamming-moat depth ≥ 5 at 449 plateau**: 290k 2-swap + 2M 3-cycle + 460k 4-cycle + 1.35M 5-cycle exhaustive trials produced 0 improvements.
7. **GA crossover (16-piece simultaneous swap) breaks the plateau** — predicted by moat-depth, empirically confirmed twice.
8. **Salassa pipeline is structurally orthogonal to PT-derived boards** — perfect-fill maxima are smaller than current PT placements.
9. **At least 4 distinct 451+ basins exist** — multiple basin discoveries (76% overlap between distinct 453s).
10. **Plateau pattern repeats at every score level**: 1800s PT cannot push 452 → 453, repeating the 449 → 450 pattern. Each new score becomes its own moat.

## Algorithmic infrastructure built tonight (Rust + Python)

- `crates/localsearch/src/forbidden.rs` — soft-penalty constrained PT module.
- `crates/localsearch/src/pt.rs` — penalty integration in PT replica-exchange.
- `crates/benchmark/src/bin/pt_e2.rs` — `--start-from`, `--forbidden-edges`, `--forbidden-k` flags.
- `crates/benchmark/src/bin/frame_first_e2.rs` — `bucas_url` per checkpoint candidate.
- `scripts/edge_color_bp.py` — BP on cell-compatibility relaxation.
- `scripts/wauters_polish.py` — TA Hungarian + TSR exhaustive.
- `scripts/cell_defect_mwpm.py` — PyMatching v2 cell-defect MWPM (built, not yet wired).
- `scripts/region_max_clique.py` — Salassa §3.5 max-clique RO via igraph.
- `scripts/three_cycle_bruteforce.py`, `scripts/four_cycle_sample.py` — exhaustive k-cycle search.
- `scripts/ga_crossover.py` — block crossover with piece-duplicate repair (the breakthrough kernel).
- `scripts/ga_light_run.sh`, `scripts/ga_large_run.sh`, `scripts/ga_cascade_453.sh`, `scripts/ga_wide_run.sh` — GA orchestrators.
- `scripts/select_seeds_by_top6.py`, `scripts/ne1_top6_funnel.sh` — frame-first top-K filter.
- `scripts/ne2_iterative_deepen.sh` — iterative forbidden-set deepening.
- `scripts/puzzle_structural_analysis.py`, `scripts/mismatch_color_analysis.py`, `scripts/board_defect_heatmap.py` — structural diagnostics.
- `data/forbidden_top{6,12,20,30}.json` — universal-mismatch lists.

## Tomorrow's priorities (in order)

1. **GA-WIDE** (script ready in `scripts/ga_wide_run.sh`, NOT run tonight) — K=6,7,8 regions, 30 cross × 180s. May find 454 in a different basin.
2. **Continued cascade from the 453 boards** — both basins.
3. **Real memetic GA**: population manager, generations, fitness pressure. Tonight's runs are essentially random crossover + polish.
4. **NE7 cell-defect MWPM as ALNS destroy** (3h Rust integration).
5. **NE2.2 SAT 2024 adaptive clause-weighting port** (4h port).

## Documents to read

- This file (1 page).
- `NIGHT5_MORNING_BRIEF.md` (3 pages, status + structure).
- `NIGHT5_SYNTHESIS.md` (10 pages, full mechanism story).
- `NIGHT5_NEXT_DAY.md` (4 pages, prioritized experiments).
- `NIGHT5_ABSTRACT.md` (1 page, arXiv-style).
- `RESEARCH_NOTES_5.md` (chronological log, ~1800 lines).
