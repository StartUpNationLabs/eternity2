// Post-hoc rescorer: reads a board JSON saved by any v14 bench bin
// and prints the canonical /480 score (unplaced cells contribute 0).
// Use to honest-grade CP partials.
// Vol-118 T9: migrated to canonical eternity2_export::load_board.
//
// Usage: rescore_board <board.json> [<board.json> ...]

use std::path::PathBuf;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_export::load_board;
use eternity2_localsearch::alns::score_board as ls_score_board;
use eternity2_solver_trait as _;

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: rescore_board <board.json> [...]");
        std::process::exit(2);
    }
    println!("path\tplaced/256\tmatched/480\tls_score\tpct");
    for a in &args {
        let p = PathBuf::from(a);
        match load_board(&p, &puzzle) {
            Ok(b) => {
                let placed = placed_count(&b, &puzzle);
                let (m, t) = score_board(&puzzle, &b);
                let ls = ls_score_board(&puzzle, &b);
                let pct = m as f64 * 100.0 / t as f64;
                println!(
                    "{a}\t{placed}/{}\t{m}/{t}\t{ls}\t{pct:.1}%",
                    puzzle.cell_count()
                );
            }
            Err(e) => eprintln!("{a}\tERROR: {e}"),
        }
    }
}
