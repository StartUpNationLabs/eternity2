// Vol-118 T5b — heur_count distribution by piece-class.
//
// Output: for each piece class (corner/edge/interior) and rotation, the
// distribution of heur_count (0-4). Helps understand whether the v17a
// schedule's targets are FEASIBLE under hint pinning.

use eternity2_blackwood_fast::{
    blackwood_schedule_calibrated_v17a, PieceRot, RowMajorIndex,
};
use eternity2_puzzle_io::load_puzzle_with_hints;
use std::path::PathBuf;

fn main() {
    let puzzle_path = PathBuf::from(
        "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv",
    );
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let schedule = blackwood_schedule_calibrated_v17a(&puzzle, &hints).expect("v17a");
    let mut index = RowMajorIndex::build(&puzzle);
    index.set_heuristic_sides(&schedule.heuristic_sides);

    // Walk pieces, classify, accumulate heur_count distribution.
    let mut hist = std::collections::HashMap::<&'static str, [u32; 5]>::new();
    hist.insert("corner_max", [0; 5]);
    hist.insert("edge_max", [0; 5]);
    hist.insert("interior_max", [0; 5]);

    for piece in puzzle.pieces() {
        let edges = piece.edges.as_array();
        let n_border = edges.iter().filter(|&&c| c == 0).count();
        let class = match n_border {
            2 => "corner_max",
            1 => "edge_max",
            _ => "interior_max",
        };
        // Compute max heur_count across all 4 rotations.
        let piece_idx = (0..index.n_pieces)
            .find(|&i| index.piece_ids[i as usize] == piece.id)
            .expect("piece") as u16;
        let mut max_hc = 0u8;
        for rot in 0..4u8 {
            let pr = PieceRot::new(piece_idx, rot);
            let hc = index.heur_count_of[pr.0 as usize];
            if hc > max_hc { max_hc = hc; }
        }
        hist.get_mut(class).unwrap()[max_hc as usize] += 1;
    }

    println!("# Distribution of max heur_count over 4 rotations, by piece-class");
    println!("# heur_count: 0   1   2   3   4");
    for &cls in &["corner_max", "edge_max", "interior_max"] {
        let h = hist[cls];
        let total: u32 = h.iter().sum();
        println!("  {:>15}  {:3} {:3} {:3} {:3} {:3}  (total {})",
            cls, h[0], h[1], h[2], h[3], h[4], total);
    }

    // Average max heur_count by class (over best rotation).
    println!();
    println!("# Average max heur_count per piece, by class:");
    for &cls in &["corner_max", "edge_max", "interior_max"] {
        let h = hist[cls];
        let total: u32 = h.iter().sum();
        let weighted: u32 = h.iter().enumerate().map(|(i, &n)| i as u32 * n).sum();
        let avg = weighted as f64 / total as f64;
        println!("  {:>15}  {:.3}", cls, avg);
    }

    // How many pieces have max_heur >= 2?
    println!();
    println!("# Pieces with max_heur >= 2 (heur-rich candidates):");
    let mut count_rich = 0u32;
    for &cls in &["corner_max", "edge_max", "interior_max"] {
        let h = hist[cls];
        let rich = h[2] + h[3] + h[4];
        let total: u32 = h.iter().sum();
        println!("  {:>15}  {:>3}/{}  ({:.1}%)", cls, rich, total, 100.0 * rich as f64 / total as f64);
        count_rich += rich;
    }
    let total_pieces = puzzle.pieces().len() as u32;
    println!("  TOTAL          {}/{}  ({:.1}%)", count_rich, total_pieces, 100.0 * count_rich as f64 / total_pieces as f64);
}
