// LP-relaxation upper-bound on canonical-E2 interior score given a fixed
// border placement.
//
// Usage:
//   border_lp_ub <board.json>   # extracts the border + hints, runs LP UB

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::{lp_ub_with, strip_interior_except_hints, LpOptions};
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
        eprintln!("usage: border_lp_ub <board.json>");
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
            verbose: false,
            threads: 8,
            time_limit_secs: 600.0,
            use_ipm: true,
            presolve: true,
            integer: false,
            force_bi_match: Vec::new(),
        };
        match lp_ub_with(&puzzle, &border_board, opts) {
            Ok(r) => {
                println!("{arg}\tplaced={placed}\tbb={}\tbi_ub={:.4}\tlp_interior={:.4}\ttotal_ub={:.4}\tn_x={}\tn_y={}\tn_constraints={}\ttime={:.2}s",
                    r.bb_matches, r.bi_ub, r.interior_ub, r.total_ub, r.n_x, r.n_y, r.n_constraints, r.solve_secs);
                if let Some(pc) = &r.per_color_ii_ub {
                    println!("# per-color I-I LP UB:");
                    for k in 1..pc.len() {
                        println!("#   color {k:>2}: {:.4}", pc[k]);
                    }
                }
            }
            Err(e) => {
                eprintln!("{arg}\tERROR: {e}");
            }
        }
    }
}
