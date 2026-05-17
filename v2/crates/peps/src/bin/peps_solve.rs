// peps_solve — Rust orchestrator for PEPS-Lagrangian piece-fixing.
//
// STATUS: stub. Production PEPS implementation is in
// scripts/w1_peps/peps_quimb_lagrangian.py. This Rust binary will eventually:
//   1. Load the puzzle.
//   2. Build cell tensors in parallel via Rayon.
//   3. Call out to Python (via PyO3) or use native Rust boundary-MPS.
//   4. Run Lagrangian dual loop.
//   5. Dump partial-board JSON.
//
// For now, this just verifies the eternity2-peps crate compiles + the
// PepsContext constructor works.

use eternity2_peps::PepsContext;
use eternity2_puzzle_io::load_puzzle;
use std::path::PathBuf;
use std::sync::Arc;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: peps_solve <puzzle.csv>");
        std::process::exit(2);
    }
    let path = PathBuf::from(&args[1]);
    let puzzle = load_puzzle(&path).expect("load puzzle");
    println!(
        "loaded puzzle: {}x{}, {} pieces",
        puzzle.width,
        puzzle.height,
        puzzle.pieces().len()
    );

    let ctx = PepsContext::new(Arc::new(puzzle));
    println!(
        "PEPS context built: K = {} (incl BORDER), n_signatures = {}",
        ctx.k_colors,
        ctx.signature_lookup.len()
    );

    eprintln!("\nNote: full Rust PEPS implementation is a stub. See");
    eprintln!("scripts/w1_peps/peps_quimb_lagrangian.py for the working Python");
    eprintln!("version, which validated complete solves on 4×4 and 6×6 puzzles.");
}
