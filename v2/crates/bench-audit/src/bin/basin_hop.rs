// Vol-20 — basin-hopping operator probe.
//
// Take a high-score board (e.g., 457). Force-break ONE matched edge
// by rotating one of its endpoints to a different rotation. The new
// board has score ≤ original - 1 (often ≤ -3 since one rotation
// breaks 4 edges simultaneously). Run a short ALNS to recover.
//
// Question: does ALNS always converge back to the original 457, or
// does the perturbation occasionally find a DIFFERENT 457 (or even
// 458+) basin?
//
// CLI:
//   basin_hop --source-board <path> --n-trials 32 --alns-budget-ms 60000 --seed 1
//
// Each trial picks a different matched edge to break, runs ALNS,
// records final score. Output: distribution of final scores; flag
// any final score > original.
//
// IMPORTANT: skip rotations of HINT cells; we cannot violate the
// canonical hints.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Rotation};
use eternity2_localsearch::{
    polish_rotations, piece_swap_hillclimb, run_alns, Acceptance, AlnsConfig, ConflictDriven,
    DestroyOp, MwpmDefectPair, RandomRegion, RepairKind, WorstBand, WorstWindow,
};

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> eternity2_core::Board {
    eternity2_export::load_board(path, puzzle).expect("load_board")
}

fn build_ops() -> Vec<Box<dyn DestroyOp>> {
    vec![
        Box::new(RandomRegion { k: 4 }),
        Box::new(WorstWindow { k: 5 }),
        Box::new(ConflictDriven { max_size: 30 }),
        Box::new(ConflictDriven { max_size: 80 }),
        Box::new(MwpmDefectPair { max_pairs: 12 }),
        Box::new(WorstBand { k_rows: 4 }),
    ]
}

fn main() {
    let mut source_board = PathBuf::new();
    let mut n_trials: u64 = 32;
    let mut alns_budget_ms: u64 = 60_000;
    let mut seed: u64 = 1;
    let mut k_perturbations: usize = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--source-board" => source_board = PathBuf::from(args.next().unwrap()),
            "--n-trials" => n_trials = args.next().unwrap().parse().unwrap(),
            "--alns-budget-ms" => alns_budget_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--k-perturbations" => k_perturbations = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if source_board.as_os_str().is_empty() {
        eprintln!("usage: basin_hop --source-board PATH --n-trials N --alns-budget-ms MS --seed S");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let src = load_board(&source_board, &puzzle);
    let (src_m, _) = score_board(&puzzle, &src);
    let pinned: std::collections::BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();

    eprintln!(
        "basin_hop: source={}/480 placed={}/{}; hints={}; n_trials={n_trials}",
        src_m, placed_count(&src, &puzzle), puzzle.cell_count(), pinned.len()
    );

    // Identify candidate cells: non-hint cells.
    let mut candidate_cells: Vec<u32> = (0..puzzle.cell_count() as u32)
        .filter(|p| !pinned.contains(p))
        .collect();
    eprintln!("candidate (non-hint) cells: {}", candidate_cells.len());

    // Deterministic shuffle via seed.
    let mut rng_state = seed.wrapping_mul(0x9E3779B97F4A7C15);
    for i in (1..candidate_cells.len()).rev() {
        rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let j = (rng_state >> 33) as usize % (i + 1);
        candidate_cells.swap(i, j);
    }

    let mut results: Vec<(u32, u32, u32, u32, u32)> = Vec::new();
    let mut best_score = src_m;
    let mut best_board_id: i32 = -1;

    for trial in 0..n_trials {
        let mut perturbed = src.clone();
        // Perturb k cells: pick k cells offset by trial × k.
        let base = (trial as usize) * k_perturbations;
        let mut perturb_log: Vec<(u32, u8, u8)> = Vec::new();
        for kk in 0..k_perturbations {
            let idx = (base + kk) % candidate_cells.len();
            let pos = candidate_cells[idx];
            let Some((pid, cur_rot)) = perturbed.get(pos) else { continue };
            let trial_seed = (seed.wrapping_add(trial).wrapping_add(kk as u64 * 13))
                .wrapping_mul(0x9E3779B97F4A7C15);
            let new_rot_id = ((trial_seed >> 32) as u8 + 1) % 4;
            let new_rot_id = if new_rot_id == cur_rot.as_u8() { (cur_rot.as_u8() + 1) % 4 } else { new_rot_id };
            let new_rot = Rotation::from_u8(new_rot_id).unwrap();
            if new_rot == cur_rot { continue; }
            perturbed.place(pos, pid, new_rot);
            perturb_log.push((pos, cur_rot.as_u8(), new_rot.as_u8()));
        }
        let (pre_alns_m, _) = score_board(&puzzle, &perturbed);
        if perturb_log.is_empty() { continue; }
        let pos = perturb_log[0].0;  // log first one as anchor
        let cur_rot = Rotation::from_u8(perturb_log[0].1).unwrap();
        let new_rot = Rotation::from_u8(perturb_log[0].2).unwrap();

        // Run ALNS.
        let cfg = AlnsConfig {
            time_budget_ms: alns_budget_ms,
            repair_budget_ms: 1500,
            acceptance: Acceptance::SimulatedAnnealing { t: 2.0 },
            segment_iters: 50,
            seed: seed.wrapping_add(trial * 17),
            verbose: false,
            repair: RepairKind::Sa,
            cp_fallback_to_sa: true,
            pinned_positions: pinned.iter().copied().collect::<Vec<u32>>(),
            iter_budget: 0,
            lex_break_isoscore: false,
            checkpoint_path: None,
            checkpoint_every_ms: 60_000,
            repair_step_budget: 0,
            cp_repair_parallel: false,
        };
        let mut ops = build_ops();
        let t0 = Instant::now();
        let (alns_board, _stats) = run_alns(&puzzle, &perturbed, ops.as_mut_slice(), &cfg);
        let (alns_board, rg) = polish_rotations(&puzzle, &alns_board, &pinned);
        let (alns_board, sg) = piece_swap_hillclimb(&puzzle, &alns_board, &pinned);
        let elapsed = t0.elapsed();
        let (final_m, _) = score_board(&puzzle, &alns_board);
        eprintln!(
            "trial {} (k={}): pre_alns={}/480, post_alns={}/480 (Δ vs source = {:+}, polish_rot=+{}, polish_swap=+{}), elapsed {:.1}s",
            trial, perturb_log.len(), pre_alns_m, final_m, final_m as i32 - src_m as i32, rg, sg, elapsed.as_secs_f64(),
        );
        let _ = (pos, cur_rot, new_rot);  // suppress unused for now
        results.push((trial as u32, pos, new_rot.as_u8() as u32, pre_alns_m, final_m));
        if final_m > best_score {
            best_score = final_m;
            best_board_id = trial as i32;
            // Save the better board immediately.
            let out_dir = PathBuf::from("output/v20_basin_hop");
            let _ = std::fs::create_dir_all(&out_dir);
            let json = serde_json::json!({
                "trial": trial,
                "break_pos": pos,
                "new_rot": new_rot.as_u8(),
                "pre_alns": pre_alns_m,
                "post_alns": final_m,
                "source_score": src_m,
                "placement": (0..puzzle.cell_count()).map(|p| {
                    alns_board.get(p).map(|(pid, rot)| serde_json::json!({
                        "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                    }))
                }).collect::<Vec<_>>(),
            });
            let p = out_dir.join(format!("basin_hop_best_{}_{}.json", src_m, final_m));
            let _ = std::fs::write(&p, serde_json::to_string_pretty(&json).unwrap());
            eprintln!("  ** NEW BEST: {} saved to {}", final_m, p.display());
        }
    }

    eprintln!();
    eprintln!("Summary ({} trials, source={src_m}):", results.len());
    let mut scores: Vec<u32> = results.iter().map(|r| r.4).collect();
    scores.sort();
    eprintln!("  min={}, p25={}, median={}, p75={}, max={}, best_overall={}",
        scores.first().copied().unwrap_or(0),
        scores[scores.len() / 4],
        scores[scores.len() / 2],
        scores[3 * scores.len() / 4],
        scores.last().copied().unwrap_or(0),
        best_score
    );
    let n_recovered = results.iter().filter(|r| r.4 == src_m).count();
    let n_better = results.iter().filter(|r| r.4 > src_m).count();
    let n_worse = results.iter().filter(|r| r.4 < src_m).count();
    eprintln!("  recovered to {}: {}", src_m, n_recovered);
    eprintln!("  better than {}: {}", src_m, n_better);
    eprintln!("  worse than {}: {}", src_m, n_worse);
}
