// bf_bw — benchmark solve_blackwood (raw DFS + Blackwood schedule pruning).
//
// Usage: bf_bw [--puzzle path] [--budget-ms ms]
// Defaults: canonical Selby-Riordan 16x16, 5000 ms.

use eternity2_blackwood_fast::{blackwood_schedule_469, solve_blackwood};
use eternity2_puzzle_io::load_puzzle_with_hints;
use std::path::PathBuf;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut puzzle_path = PathBuf::from(
        "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv",
    );
    let mut budget_ms: u64 = 5000;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&args[i + 1]); i += 2; }
            "--budget-ms" => { budget_ms = args[i + 1].parse().expect("budget"); i += 2; }
            _ => { eprintln!("unknown arg: {}", args[i]); std::process::exit(1); }
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let schedule = blackwood_schedule_469(&puzzle, &hints).expect("schedule built");
    eprintln!(
        "[bf_bw] puzzle: {}x{}, colors={}, schedule heuristic_sides={:?} max_idx={} pool_size~ many",
        puzzle.width, puzzle.height, puzzle.color_count,
        schedule.heuristic_sides, schedule.max_heuristic_index
    );
    eprintln!("[bf_bw] exhaustion_targets={:?}", schedule.exhaustion_targets);

    let t0 = std::time::Instant::now();
    let (stats, _board) = solve_blackwood(&puzzle, &schedule, budget_ms * 1000);
    let elapsed = t0.elapsed();
    let nps = (stats.nodes as f64) / elapsed.as_secs_f64();
    println!(
        "{{\"profile\":\"blackwood_fast\",\"budget_ms\":{},\"elapsed_ms\":{},\"nodes\":{},\"max_depth\":{},\"solved\":{},\"nps\":{:.0}}}",
        budget_ms, elapsed.as_millis(), stats.nodes, stats.max_depth, stats.solved, nps
    );
}
