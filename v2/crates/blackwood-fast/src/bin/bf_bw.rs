// bf_bw — benchmark solve_blackwood (raw DFS + Blackwood schedule pruning).
//
// Usage: bf_bw [--puzzle path] [--budget-ms ms]
// Defaults: canonical Selby-Riordan 16x16, 5000 ms.

use eternity2_blackwood_fast::{
    blackwood_schedule_469, blackwood_schedule_calibrated_v17a, score_board, solve_blackwood,
    solve_blackwood_par,
};
use eternity2_puzzle_io::load_puzzle_with_hints;
use std::path::PathBuf;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut puzzle_path = PathBuf::from(
        "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv",
    );
    let mut budget_ms: u64 = 5000;
    let mut schedule_name = String::from("v17a");
    let mut break_first: Option<u32> = None;
    let mut break_count: Option<u32> = None;
    let mut threads: usize = 1;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&args[i + 1]); i += 2; }
            "--budget-ms" => { budget_ms = args[i + 1].parse().expect("budget"); i += 2; }
            "--schedule" => { schedule_name = args[i + 1].clone(); i += 2; }
            "--break-first" => { break_first = Some(args[i + 1].parse().expect("break-first")); i += 2; }
            "--break-count" => { break_count = Some(args[i + 1].parse().expect("break-count")); i += 2; }
            "--threads" => { threads = args[i + 1].parse().expect("threads"); i += 2; }
            _ => { eprintln!("unknown arg: {}", args[i]); std::process::exit(1); }
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let mut schedule = match schedule_name.as_str() {
        "v15" | "469" => blackwood_schedule_469(&puzzle, &hints).expect("schedule built"),
        "v17a" => blackwood_schedule_calibrated_v17a(&puzzle, &hints).expect("schedule built"),
        other => panic!("unknown schedule: {other}"),
    };
    // Optional break-index override for exploration.
    if let (Some(first), Some(n)) = (break_first, break_count) {
        let wh = (puzzle.width * puzzle.height) as u32;
        let mut new_breaks: Vec<u32> = (0..n).map(|i| (first + i).min(wh - 1)).collect();
        new_breaks.dedup();
        eprintln!("[bf_bw] override breaks: {:?}", new_breaks);
        schedule.break_indexes_allowed = new_breaks;
    }
    eprintln!("[bf_bw] schedule={}", schedule_name);
    eprintln!("[bf_bw] break_indexes_allowed={:?}", schedule.break_indexes_allowed);
    eprintln!(
        "[bf_bw] puzzle: {}x{}, colors={}, schedule heuristic_sides={:?} max_idx={} pool_size~ many",
        puzzle.width, puzzle.height, puzzle.color_count,
        schedule.heuristic_sides, schedule.max_heuristic_index
    );
    eprintln!("[bf_bw] exhaustion_targets={:?}", schedule.exhaustion_targets);

    eprintln!("[bf_bw] threads={}", threads);
    let t0 = std::time::Instant::now();
    let (stats, board) = if threads > 1 {
        solve_blackwood_par(&puzzle, &schedule, threads, budget_ms * 1000)
    } else {
        solve_blackwood(&puzzle, &schedule, budget_ms * 1000)
    };
    let elapsed = t0.elapsed();
    let nps = (stats.nodes as f64) / elapsed.as_secs_f64();
    let score = score_board(&puzzle, &board);
    println!(
        "{{\"profile\":\"blackwood_fast\",\"threads\":{},\"budget_ms\":{},\"elapsed_ms\":{},\"nodes\":{},\"max_depth\":{},\"solved\":{},\"best_score\":{},\"nps\":{:.0}}}",
        threads, budget_ms, elapsed.as_millis(), stats.nodes, stats.max_depth, stats.solved, score, nps
    );
}
