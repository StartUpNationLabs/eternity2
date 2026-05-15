// LP UB on canonical-E2 5-clue with NO border placed.
// Only the 5 canonical hints are fixed. The 60 perimeter cells are
// free in the LP (over all 60 border pieces × valid rotations).
//
// This is the global LP UB over all possible canonical 5-clue boards.
// If it's > 478, there exist basins with higher UB than we've sampled.
// If it's exactly 478, the 478 cap IS the canonical-5-clue LP ceiling.

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_bench_audit::border_ub::{lp_ub_with, LpOptions};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Position};

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");

    // Create a board with ONLY the canonical hints placed.
    let mut board = Board::empty(&puzzle);
    for h in &hints.hints {
        board.place(h.position, h.piece_id, h.rotation);
    }
    let placed = (0..puzzle.cell_count()).filter(|&p| board.get(p).is_some()).count();
    eprintln!("Board: only canonical hints placed ({placed} cells)");
    eprintln!("Hints: {:?}", hints.hints.iter().map(|h| h.position).collect::<Vec<_>>());

    let opts = LpOptions {
        verbose: true,
        threads: 8,
        time_limit_secs: 1800.0,
        use_ipm: true,
        presolve: true,
        integer: false,
        force_bi_match: Vec::new(),
    };
    eprintln!("Running LP UB on canonical-5-clue with no border fixed...");
    let t0 = std::time::Instant::now();
    match lp_ub_with(&puzzle, &board, opts) {
        Ok(r) => {
            println!("\n==== RESULT ====");
            println!("bb_matches  = {}", r.bb_matches);
            println!("bi_ub       = {:.4}", r.bi_ub);
            println!("interior_ub = {:.4}", r.interior_ub);
            println!("total_ub    = {:.4}", r.total_ub);
            println!("n_x = {}, n_y = {}, n_constraints = {}", r.n_x, r.n_y, r.n_constraints);
            println!("solve_secs  = {:.2}", r.solve_secs);
            println!("total       = {:.2}s", t0.elapsed().as_secs_f64());
        }
        Err(e) => {
            eprintln!("LP error: {e}");
            std::process::exit(1);
        }
    }
    let _ = (placed,);
}
