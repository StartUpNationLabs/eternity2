// Vol-118 T5 — measure heur_count of each canonical hint piece.
//
// Output: list of (hint_position, hint_piece_id, hint_rotation, heur_count_at_rot).
// Useful for recalibrating v17a schedule to subtract hint contributions.

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
    eprintln!("v17a heuristic_sides: {:?}", schedule.heuristic_sides);

    let mut index = RowMajorIndex::build(&puzzle);
    index.set_heuristic_sides(&schedule.heuristic_sides);

    // For each hint, find its piece_idx and report heur_count_of at the pinned rotation.
    let mut sorted: Vec<_> = hints.hints.iter().collect();
    sorted.sort_by_key(|h| h.position);

    let mut cum = 0u32;
    println!("# hint_pos | depth | piece_id | rotation | heur_count_at_this_rot | cum_after");
    for hint in sorted {
        let piece_idx = (0..index.n_pieces)
            .find(|&i| index.piece_ids[i as usize] == hint.piece_id)
            .expect("hint piece") as u16;
        let pr = PieceRot::new(piece_idx, hint.rotation.as_u8());
        let hc = index.heur_count_of[pr.0 as usize];
        cum += hc as u32;
        println!(
            "  pos={:3}  depth={:3}  piece={:3}  rot={}  heur={}  cum={}",
            hint.position, hint.position, hint.piece_id, hint.rotation.as_u8(), hc, cum
        );
    }

    println!();
    println!("# v17a targets (raw):");
    for &(d, t) in &schedule.exhaustion_targets {
        println!("  d={:3}  target={}", d, t);
    }
}
