// Column-generated lifted LP UB on a canonical-E2 board's border.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::{strip_interior_except_hints, LpOptions};
use eternity2_bench_audit::border_ub_lifted::{column_generated_lifted_lp_ub, ColumnGenOpts};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use serde_json::Value;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut path_arg: Option<String> = None;
    let mut threshold: f64 = 0.05;
    let mut time_limit_secs: f64 = 1800.0;
    let mut iter = args.iter();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--threshold" => threshold = iter.next().unwrap().parse().unwrap(),
            "--time-limit-secs" => time_limit_secs = iter.next().unwrap().parse().unwrap(),
            other => {
                if !other.starts_with("--") { path_arg = Some(other.to_string()); }
            }
        }
    }
    let path_arg = path_arg.expect("usage: border_lp_ub_lifted_cg <board.json>");

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let hint_positions: Vec<Position> = hints.hints.iter().map(|h| h.position).collect();

    let board = load_board(&PathBuf::from(&path_arg), &puzzle).expect("load board");
    let border_board = strip_interior_except_hints(&puzzle, &board, &hint_positions);
    let placed = (0..puzzle.cell_count()).filter(|&p| border_board.get(p).is_some()).count();
    eprintln!("[{path_arg}] border+hint cells placed: {placed}");

    let mut base_opts = LpOptions::default();
    base_opts.verbose = true;
    base_opts.time_limit_secs = time_limit_secs;

    let opts = ColumnGenOpts {
        base_lp_opts: base_opts,
        x_active_threshold: threshold,
        max_iters: 1, // single-iteration for now
    };

    match column_generated_lifted_lp_ub(&puzzle, &border_board, opts) {
        Ok(r) => {
            println!("{path_arg}\tcol_gen_total_ub={:.4}\tbb={}\tbi_ub={:.4}\tinterior_ub={:.4}\tn_x={}\tn_z={}\tavg_z_per_edge={:.1}\ttotal_time={:.1}s",
                r.total_ub, r.bb_matches, r.bi_ub, r.interior_ub,
                r.n_x, r.n_z, r.n_z_per_edge_avg, r.solve_secs);
        }
        Err(e) => {
            eprintln!("{path_arg}\tERROR: {e}");
        }
    }
}
