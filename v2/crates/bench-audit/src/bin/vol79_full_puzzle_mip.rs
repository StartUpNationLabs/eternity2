//! Vol-79 — Try full-board MIP relaxation via cluster_repair on ALL cells.
//!
//! Uses cluster_repair's MIP infrastructure. Cluster = all 256 cells.
//! Pieces = all 256 pieces (permute freely).
//! This is the full QAP — likely won't solve to optimum, but LP-relaxation
//! gives a sound bound.

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_bench_audit::cluster_repair::{repair_cluster, ClusterOptions};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Rotation};

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    // Build an INITIAL board by placing pieces 0..256 at positions 0..256 with rotation 0.
    // This is a dummy starting placement; repair_cluster will permute.
    let mut board = Board::empty(&puzzle);
    for p in 0..256 {
        board.place(p, PieceId::try_from(p).unwrap(), Rotation::R0);
    }

    let cluster: Vec<Position> = (0..256).collect();
    println!("Full-board MIP: 256 cells, 256 pieces, ALL free");
    println!("Cluster size: {}", cluster.len());

    let opts = ClusterOptions {
        time_limit_secs: 600.0,
        threads: 4,
        verbose: true,
    };

    match repair_cluster(&puzzle, &board, &cluster, opts) {
        Ok(r) => {
            println!("\n=== MIP RESULT ===");
            println!("Objective (matched edges): {}", r.obj_value);
            println!("Delta over starting: {}", r.delta);
            println!("Solve time: {:.2}s", r.solve_secs);
        }
        Err(e) => {
            println!("MIP failed: {}", e);
        }
    }
}
