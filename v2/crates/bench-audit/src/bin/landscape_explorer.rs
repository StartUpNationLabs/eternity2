// Vol-34 user proposal / Vol-35 T1 — fitness landscape mapping on
// small E2 puzzles.
//
// Enumerate local optima by running ALNS-from-random for many seeds.
// Save each LO's board JSON for offline clustering / barrier analysis.
//
// Usage:
//   landscape_explorer --size 6 --colors 5 --puzzle-seed 1 \
//       --n-restarts 500 --alns-budget-ms 5000 --threads 4 \
//       --out-dir output/vol-35/landscape_6x6
//
// Output:
//   <out-dir>/lo_<restart_seed>_s<score>.json — board JSON per restart
//   <out-dir>/summary.jsonl — one row per restart (seed, score, hash)

use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

use eternity2_bench_audit::QuietSink;
use eternity2_core::{Board, Position, Rotation};
use eternity2_export::score_board;
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_localsearch::{
    piece_swap_hillclimb, polish_rotations, run_alns, Acceptance, AlnsConfig, ConflictDriven,
    DestroyOp, MwpmDefectPair, RandomRegion, RepairKind, WorstBand, WorstWindow,
};
use rayon::prelude::*;
use serde_json::json;

// Fisher-Yates random permutation of 0..n using LCG.
fn random_perm(n: usize, mut state: u64) -> Vec<usize> {
    let mut v: Vec<usize> = (0..n).collect();
    for i in (1..n).rev() {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let j = ((state >> 32) as usize) % (i + 1);
        v.swap(i, j);
    }
    v
}

fn random_initial_board(puzzle: &eternity2_core::Puzzle, seed: u64) -> Board {
    let n = puzzle.cell_count() as usize;
    let pos_perm = random_perm(n, seed);
    let mut b = Board::empty(puzzle);
    // Each piece_id gets placed at a random position with random rotation.
    let mut state = seed.wrapping_add(0xDEAD_BEEF);
    for (pid, pos) in pos_perm.iter().enumerate() {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let rot_u = ((state >> 32) as u8) & 0b11;
        let rot = Rotation::from_u8(rot_u).unwrap_or(Rotation::R0);
        if pid >= n {
            break; // safety: more pieces than cells
        }
        b.place(*pos as Position, pid as u16, rot);
    }
    b
}

fn build_ops() -> Vec<Box<dyn DestroyOp>> {
    // Size-agnostic destroy ops. Avoid the ones requiring 16×16-specific
    // hint geometry.
    vec![
        Box::new(RandomRegion { k: 4 }),
        Box::new(WorstWindow { k: 3 }),
        Box::new(WorstBand { k_rows: 2 }),
        Box::new(ConflictDriven { max_size: 10 }),
        Box::new(MwpmDefectPair { max_pairs: 8 }),
    ]
}

fn main() {
    let mut size: u32 = 6;
    let mut colors: u32 = 5;
    let mut puzzle_seed: u64 = 1;
    let mut n_restarts: u32 = 500;
    let mut alns_ms: u64 = 5_000;
    let mut threads: usize = 4;
    let mut out_dir = PathBuf::from("output/vol-35/landscape");
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--size" => size = args.next().unwrap().parse().unwrap(),
            "--colors" => colors = args.next().unwrap().parse().unwrap(),
            "--puzzle-seed" => puzzle_seed = args.next().unwrap().parse().unwrap(),
            "--n-restarts" => n_restarts = args.next().unwrap().parse().unwrap(),
            "--alns-budget-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--threads" => threads = args.next().unwrap().parse().unwrap(),
            "--out-dir" => out_dir = PathBuf::from(args.next().unwrap()),
            other => panic!("unknown arg: {other}"),
        }
    }
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    let puzzle = generate(GeneratorConfig { size, interior_colors: colors, seed: puzzle_seed })
        .expect("generate");
    let max_edges = (puzzle.width - 1) * puzzle.height + puzzle.width * (puzzle.height - 1);
    eprintln!(
        "[landscape] puzzle: {}x{}, colors={}, puzzle_seed={}, max_edges={}",
        size, size, colors - 1, puzzle_seed, max_edges
    );
    eprintln!(
        "[landscape] n_restarts={}, alns_ms={}, threads={}",
        n_restarts, alns_ms, threads
    );

    let summary_path = out_dir.join("summary.jsonl");
    let _ = std::fs::write(&summary_path, "");

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .expect("rayon pool");

    let t0 = Instant::now();
    let done = AtomicU64::new(0);

    pool.install(|| {
        (0..n_restarts).into_par_iter().for_each(|restart_seed| {
            let init = random_initial_board(&puzzle, restart_seed as u64);
            let cfg = AlnsConfig {
                time_budget_ms: alns_ms,
                repair_budget_ms: 200,
                acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
                segment_iters: 20,
                seed: (restart_seed as u64).wrapping_add(1),
                verbose: false,
                repair: RepairKind::Sa,
                cp_fallback_to_sa: true,
                pinned_positions: Vec::new(), // no canonical hints on generated puzzles
                iter_budget: 0,
                lex_break_isoscore: false,
                checkpoint_path: None,
                checkpoint_every_ms: 60_000,
                repair_step_budget: 64,
                cp_repair_parallel: false,
            };
            let mut ops = build_ops();
            let (alns_board, _stats) = run_alns(&puzzle, &init, ops.as_mut_slice(), &cfg);
            // Polish to a (rotation, single-swap) local optimum so the
            // saved board is a deterministic attractor, not a transient
            // best-along-trajectory snapshot.
            let pinned: std::collections::BTreeSet<u32> = std::collections::BTreeSet::new();
            let (alns_board, _) = polish_rotations(&puzzle, &alns_board, &pinned);
            let (final_board, _) = piece_swap_hillclimb(&puzzle, &alns_board, &pinned);
            let (score, _) = score_board(&puzzle, &final_board);

            // Write per-restart JSON
            let placement: Vec<_> = (0..puzzle.cell_count())
                .map(|p| match final_board.get(p) {
                    Some((pid, rot)) => json!({
                        "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                    }),
                    None => serde_json::Value::Null,
                })
                .collect();
            let board_json = json!({ "placement": placement });
            let out_path = out_dir.join(format!("lo_{restart_seed:05}_s{score:03}.json"));
            let _ = std::fs::write(&out_path, serde_json::to_string(&board_json).unwrap());

            // Append summary row
            let row = json!({
                "restart_seed": restart_seed,
                "score": score,
                "path": out_path.to_string_lossy(),
            });
            use std::io::Write;
            let mut f = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&summary_path)
                .expect("open summary");
            let _ = writeln!(f, "{}", row.to_string());

            let d = done.fetch_add(1, Ordering::Relaxed) + 1;
            if d % 50 == 0 {
                eprintln!(
                    "[landscape] {d}/{n_restarts} done; elapsed={:.0}s",
                    t0.elapsed().as_secs_f64()
                );
            }
        });
    });

    eprintln!(
        "[landscape] DONE: {} restarts in {:.1}s",
        n_restarts,
        t0.elapsed().as_secs_f64()
    );
    let _ = QuietSink::new(); // silence unused-import warn if needed
}
