// Benchmark exact contraction on a puzzle.

use eternity2_peps::{PepsContext, PieceRot};
use eternity2_peps::mps::log_z_lagrangian;
use eternity2_puzzle_io::load_puzzle;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: peps_bench <puzzle.csv> [n_iter=10]");
        std::process::exit(1);
    }
    let path = PathBuf::from(&args[1]);
    let n_iter: usize = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(10);

    let puzzle = load_puzzle(&path).expect("load");
    let ctx = PepsContext::new(Arc::new(puzzle));
    println!("Puzzle: size={} K={} n_pieces={}", ctx.size, ctx.k_colors, ctx.n_pieces);

    let mu = vec![0.0; ctx.n_pieces];
    let pinned: Vec<Option<PieceRot>> = vec![None; ctx.size * ctx.size];

    // Warmup
    let log_z_warm = log_z_lagrangian(&ctx, &mu, &pinned, 0);
    println!("Warmup log_z = {}", log_z_warm);

    // Bench
    let t0 = Instant::now();
    let mut last = 0.0;
    for _ in 0..n_iter {
        last = log_z_lagrangian(&ctx, &mu, &pinned, 0);
    }
    let dt = t0.elapsed();
    let per = dt.as_secs_f64() / (n_iter as f64);
    println!("{} iter: {:.3}s total, {:.3}s per iter (log_z={})", n_iter, dt.as_secs_f64(), per, last);
}
