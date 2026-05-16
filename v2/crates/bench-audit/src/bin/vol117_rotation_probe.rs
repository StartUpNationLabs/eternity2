// Vol-117 T2 — rotation-only local moves on a 459 board.
//
// Math: for each placed piece, test all 4 rotations in place. Check
// if a different rotation is legal (BORDER colors on correct sides
// for border/corner positions). If legal, compute new score. Log all
// improvements.
//
// Theoretical question: is the 459 level set rotation-locally optimal?
// If yes (every piece in every basin already at the best rotation),
// then rotation is "frozen" — the basin is rigid even under
// rotation-only moves. If no, there's a free Δ to gain by simply
// rotating one piece.

use std::path::{Path, PathBuf};

use eternity2_bench_audit::score_board_dense as score_board;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Rotation};

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: vol117_rotation_probe <board.json>");
        std::process::exit(1);
    }
    let board_path = PathBuf::from(&args[1]);
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let mut board = load_board(&board_path, &puzzle).expect("load board");

    let (matched_base, _) = score_board(&puzzle, &board);
    eprintln!("base score: {}/480", matched_base);

    let n = puzzle.cell_count() as u32;
    let mut improvements: Vec<(u32, u32, u8, u8, i32)> = Vec::new();
    let mut total_legal_alternatives = 0usize;
    let mut tested_positions = 0usize;

    for pos in 0..n {
        let Some((piece_id, original_rot)) = board.get(pos) else { continue };
        tested_positions += 1;
        for r_new_u8 in 0..4u8 {
            if r_new_u8 == original_rot.as_u8() { continue; }
            let Some(r_new) = Rotation::from_u8(r_new_u8) else { continue };
            // Test by placing and rescoring. The Board::place will replace.
            board.place(pos, piece_id, r_new);
            // Validate: the score might be valid even with a "wrong" rotation
            // (BORDER colors mis-facing become 0 mismatches but cap matches).
            let (new_matched, _) = score_board(&puzzle, &board);
            let delta = new_matched as i32 - matched_base as i32;
            // Restore.
            board.place(pos, piece_id, original_rot);
            total_legal_alternatives += 1;
            if delta > 0 {
                improvements.push((pos, u32::from(piece_id), original_rot.as_u8(), r_new_u8, delta));
            }
        }
    }

    println!(
        "tested {} positions, {} alt-rotation tests, {} improvements found",
        tested_positions, total_legal_alternatives, improvements.len()
    );
    improvements.sort_by_key(|x| -x.4);
    for (pos, pid, r_old, r_new, delta) in improvements.iter().take(20) {
        println!(
            "  pos={} piece={} rot {}->{} delta={}",
            pos, pid, r_old, r_new, delta
        );
    }
}
