// Count non-BORDER color sides across all canonical-E2 pieces.
// Compute the combinatorial color-matching upper bound:
// UB = sum_k floor(N_k / 2) where N_k is the total non-BORDER side
// count of color k across all 256 pieces.

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::BORDER;

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let max_color = puzzle.color_count.saturating_sub(1) as u8;
    let mut counts = vec![0u32; (max_color as usize) + 1];

    for piece in puzzle.pieces() {
        for &side in &piece.edges.as_array() {
            if side != BORDER {
                counts[side as usize] += 1;
            }
        }
    }

    println!("color\tcount\tfloor(N/2)\twasted");
    let mut total_ub = 0u32;
    let mut total_wasted = 0u32;
    for k in 1..=max_color as usize {
        let n = counts[k];
        let ub = n / 2;
        let wasted = n % 2;
        total_ub += ub;
        total_wasted += wasted;
        println!("{k}\t{n}\t{ub}\t{wasted}");
    }

    println!("---");
    println!("Total non-BORDER sides: {}", counts[1..].iter().sum::<u32>());
    println!("Combinatorial UB on matched edges: {total_ub}");
    println!("Wasted sides (odd-count colors): {total_wasted}");
    println!("This is an UPPER BOUND ignoring spatial constraints.");
}
