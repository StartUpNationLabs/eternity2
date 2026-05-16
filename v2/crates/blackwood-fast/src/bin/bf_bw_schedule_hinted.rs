// bf_bw_schedule_hinted — vol-117 T1 — run solve_blackwood_with_hints
// (canonical 5-clue + v17a schedule + break-index).
//
// Combines vol-113 T1 hint-pinning with the schedule + break-index path.
// Goal: produce partials that pass `verify_records.sh` with 5/5 hints
// AND get the strong scores the schedule path generates.

use eternity2_blackwood_fast::{
    blackwood_schedule_469, blackwood_schedule_calibrated_v17a,
    blackwood_schedule_calibrated_v17a_hint_aware, score_board, solve_blackwood_par_with_hints,
    solve_blackwood_with_hints,
};
use eternity2_puzzle_io::load_puzzle_with_hints;
use std::path::PathBuf;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut puzzle_path = PathBuf::from(
        "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv",
    );
    let mut budget_ms: u64 = 10_000;
    let mut dump_partial: Option<PathBuf> = None;
    let mut schedule_name = "v17a".to_string();
    let mut threads: usize = 1;
    let mut seed_offset: u64 = 0;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&args[i + 1]); i += 2; }
            "--budget-ms" => { budget_ms = args[i + 1].parse().expect("budget"); i += 2; }
            "--dump-partial" => { dump_partial = Some(PathBuf::from(&args[i + 1])); i += 2; }
            "--schedule" => { schedule_name = args[i + 1].clone(); i += 2; }
            "--threads" => { threads = args[i + 1].parse().expect("threads"); i += 2; }
            "--seed-offset" => { seed_offset = args[i + 1].parse().expect("seed-offset"); i += 2; }
            _ => { eprintln!("unknown arg: {}", args[i]); std::process::exit(1); }
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eprintln!(
        "bf_bw_schedule_hinted: puzzle={}x{} hints={} budget_ms={}",
        puzzle.width, puzzle.height, hints.hints.len(), budget_ms
    );

    let schedule = match schedule_name.as_str() {
        "v17a" => blackwood_schedule_calibrated_v17a(&puzzle, &hints)
            .expect("v17a schedule must build on canonical puzzle"),
        "v17a_hint" => blackwood_schedule_calibrated_v17a_hint_aware(&puzzle, &hints)
            .expect("v17a_hint schedule must build on canonical puzzle"),
        "bw469" => blackwood_schedule_469(&puzzle, &hints)
            .expect("bw469 schedule must build on canonical puzzle"),
        other => panic!("unknown schedule: {}", other),
    };
    eprintln!("schedule targets: {:?}", schedule.exhaustion_targets);
    eprintln!("schedule: {}", schedule_name);
    eprintln!(
        "schedule: max_heur_idx={} break_indexes={}",
        schedule.max_heuristic_index, schedule.break_indexes_allowed.len()
    );

    eprintln!("threads={} seed_offset={}", threads, seed_offset);
    let t0 = std::time::Instant::now();
    let (stats, board) = if threads > 1 {
        solve_blackwood_par_with_hints(&puzzle, &hints, &schedule, threads, seed_offset, budget_ms * 1000)
    } else {
        solve_blackwood_with_hints(&puzzle, &hints, &schedule, budget_ms * 1000)
    };
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
            "source": "blackwood_fast_schedule_hinted_v17a",
            "max_depth": stats.max_depth,
            "score": score,
            "budget_ms": budget_ms,
        });
        std::fs::create_dir_all(out_path.parent().unwrap_or(std::path::Path::new("."))).ok();
        std::fs::write(out_path, serde_json::to_string_pretty(&out).unwrap())
            .expect("write partial");
        eprintln!("[bf_bw_schedule_hinted] wrote partial to {}", out_path.display());
    }

    println!(
        "{{\"profile\":\"bf_schedule_hinted_v17a\",\"budget_ms\":{},\"elapsed_ms\":{},\"nodes\":{},\"max_depth\":{},\"solved\":{},\"score\":{},\"nps\":{:.0}}}",
        budget_ms, elapsed.as_millis(), stats.nodes, stats.max_depth, stats.solved, score, nps
    );
}
