// Lifted LP UB on a canonical-E2 board's border. McCormick on bilinear
// edge-match products. See vault/concepts/lifted-lp-formulation.md.
//
// Usage:
//   border_lp_ub_lifted <board.json>

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::{strip_interior_except_hints, LpOptions};
use eternity2_bench_audit::border_ub_lifted::lifted_lp_ub_with;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use serde_json::Value;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: border_lp_ub_lifted <board.json>");
        std::process::exit(2);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let hint_positions: Vec<Position> = hints.hints.iter().map(|h| h.position).collect();
    eprintln!("loaded puzzle: {}x{}, color_count={}, hints={:?}",
              puzzle.width, puzzle.height, puzzle.color_count, hint_positions);

    for arg in &args {
        let path = PathBuf::from(arg);
        let board = match load_board(&path, &puzzle) {
            Ok(b) => b,
            Err(e) => { eprintln!("{arg}\tERROR: {e}"); continue; }
        };
        let border_board = strip_interior_except_hints(&puzzle, &board, &hint_positions);
        let placed = (0..puzzle.cell_count()).filter(|&p| border_board.get(p).is_some()).count();
        eprintln!("[{arg}] border+hint cells placed: {placed}");
        let opts = LpOptions {
            verbose: true,
            threads: 8,
            time_limit_secs: 3600.0,
            use_ipm: true,
            presolve: true,
            integer: false,
            force_bi_match: Vec::new(),
        };
        match lifted_lp_ub_with(&puzzle, &border_board, opts) {
            Ok(r) => {
                println!("{arg}\tlifted_total_ub={:.4}\tbb={}\tbi_ub={:.4}\tinterior_ub={:.4}\tn_x={}\tn_z={}\tavg_z_per_edge={:.1}\ttime={:.1}s",
                    r.total_ub, r.bb_matches, r.bi_ub, r.interior_ub,
                    r.n_x, r.n_z, r.n_z_per_edge_avg, r.solve_secs);
            }
            Err(e) => {
                eprintln!("{arg}\tERROR: {e}");
            }
        }
    }
}
