// bf_bw_hinted — vol-113 T1 — run solve_raw_with_hints (canonical 5-clue).
//
// Loads canonical Selby-Riordan + canonical hints, runs the hint-
// preserving raw DFS, dumps the partial in placement-array JSON.
//
// Goal: produce partials that pass `verify_records.sh` with
// hint-compliance 5/5, NOT the 0/5 we've been getting from bf_bw.

use eternity2_blackwood_fast::{score_board, solve_raw_with_hints};
use eternity2_puzzle_io::load_puzzle_with_hints;
use std::path::PathBuf;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut puzzle_path = PathBuf::from(
        "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv",
    );
    let mut budget_ms: u64 = 10_000;
    let mut dump_partial: Option<PathBuf> = None;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&args[i + 1]); i += 2; }
            "--budget-ms" => { budget_ms = args[i + 1].parse().expect("budget"); i += 2; }
            "--dump-partial" => { dump_partial = Some(PathBuf::from(&args[i + 1])); i += 2; }
            _ => { eprintln!("unknown arg: {}", args[i]); std::process::exit(1); }
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eprintln!(
        "bf_bw_hinted: puzzle={}x{} hints={} budget_ms={}",
        puzzle.width, puzzle.height, hints.hints.len(), budget_ms
    );

    let t0 = std::time::Instant::now();
    let (stats, board) = solve_raw_with_hints(&puzzle, &hints, budget_ms * 1000);
    let elapsed = t0.elapsed();
    let nps = (stats.nodes as f64) / elapsed.as_secs_f64();
    let score = score_board(&puzzle, &board);

    if let Some(out_path) = &dump_partial {
        let mut placements: Vec<serde_json::Value> = Vec::new();
        for (pos, &(pid, rot)) in board.iter().enumerate() {
            if pid == u16::MAX { continue; }
            placements.push(serde_json::json!({
                "pos": pos as u32,
                "piece_id": pid,
                "rotation": rot.as_u8(),
            }));
        }
        let out = serde_json::json!({
            "placement": placements,
            "source": "blackwood_fast_hinted",
            "max_depth": stats.max_depth,
            "score": score,
            "budget_ms": budget_ms,
        });
        std::fs::create_dir_all(out_path.parent().unwrap_or(std::path::Path::new("."))).ok();
        std::fs::write(out_path, serde_json::to_string_pretty(&out).unwrap())
            .expect("write partial");
        eprintln!("[bf_bw_hinted] wrote partial to {}", out_path.display());
    }

    println!(
        "{{\"profile\":\"bf_hinted\",\"budget_ms\":{},\"elapsed_ms\":{},\"nodes\":{},\"max_depth\":{},\"solved\":{},\"score\":{},\"nps\":{:.0}}}",
        budget_ms, elapsed.as_millis(), stats.nodes, stats.max_depth, stats.solved, score, nps
    );
}
