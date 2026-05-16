// bf_similarity — vol-106 T10 measurement bin.
//
// Runs N parallel workers, each with a different bucket shuffle, on the
// canonical puzzle. At termination, computes pairwise board similarity
// (number of cells where two workers placed the same piece + rotation).
//
// Purpose: empirically test the hypothesis that cooperative frontier
// hashing would pay off. If workers' deepest boards agree on a high
// fraction of placed cells, the dedupe table would catch many hits.
// If agreement is near-random, the invention isn't worth building.

use eternity2_blackwood_fast::{
    blackwood_schedule_calibrated_v17a, pairwise_similarity, solve_blackwood_par_all,
};
use eternity2_puzzle_io::load_puzzle_with_hints;
use std::path::PathBuf;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut puzzle_path = PathBuf::from(
        "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv",
    );
    let mut budget_ms: u64 = 30000;
    let mut threads: usize = 8;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&args[i + 1]); i += 2; }
            "--budget-ms" => { budget_ms = args[i + 1].parse().expect("budget"); i += 2; }
            "--threads" => { threads = args[i + 1].parse().expect("threads"); i += 2; }
            _ => { eprintln!("unknown arg: {}", args[i]); std::process::exit(1); }
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let schedule = blackwood_schedule_calibrated_v17a(&puzzle, &hints).expect("schedule");

    eprintln!("[bf_similarity] threads={} budget_ms={}", threads, budget_ms);

    let t0 = std::time::Instant::now();
    let results = solve_blackwood_par_all(&puzzle, &schedule, threads, budget_ms * 1000);
    let elapsed = t0.elapsed();

    eprintln!("[bf_similarity] elapsed={:?}", elapsed);
    eprintln!("[bf_similarity] per-thread max_depth:");
    for (tid, (stats, _)) in results.iter().enumerate() {
        eprintln!(
            "    t{tid}: max_depth={} nodes={}",
            stats.max_depth, stats.nodes
        );
    }

    let boards: Vec<_> = results.iter().map(|(_, b)| b.clone()).collect();
    let sim = pairwise_similarity(&boards);

    println!("# pairwise board similarity matrix (cells in agreement)");
    print!("    ");
    for j in 0..threads {
        print!("    t{j:<3}");
    }
    println!();
    for i in 0..threads {
        print!("t{i:<3}");
        for j in 0..threads {
            print!("    {:<4}", sim[i][j]);
        }
        println!();
    }

    // Summary: average off-diagonal similarity, max off-diagonal.
    let mut total = 0u64;
    let mut count = 0u64;
    let mut max_off = 0u32;
    for i in 0..threads {
        for j in 0..threads {
            if i != j {
                total += sim[i][j] as u64;
                count += 1;
                if sim[i][j] > max_off {
                    max_off = sim[i][j];
                }
            }
        }
    }
    let mean_off = if count > 0 { total as f64 / count as f64 } else { 0.0 };
    let mean_diag = (0..threads).map(|i| sim[i][i] as u64).sum::<u64>() as f64 / threads as f64;
    println!();
    println!("# summary");
    println!("    mean diagonal (placed cells per thread): {:.1}", mean_diag);
    println!("    mean off-diagonal (agreement between threads): {:.1}", mean_off);
    println!("    max off-diagonal: {}", max_off);
    println!("    agreement fraction (off-diag mean / diag mean): {:.1}%",
        100.0 * mean_off / mean_diag);
}
