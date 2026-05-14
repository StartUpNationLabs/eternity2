// Compare two boards: count matching (pos, piece_id, rotation) cells
// and classify the differences.

#![forbid(unsafe_code)]

use std::collections::HashSet;
use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::is_perimeter_pos;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use serde_json::Value;

fn load_board(path: &Path, puzzle: &Puzzle) -> Result<Board, String> {
    let bytes = std::fs::read(path).map_err(|e| format!("read {path:?}: {e}"))?;
    let v: Value = serde_json::from_slice(&bytes).map_err(|e| format!("parse: {e}"))?;
    let arr = v.get("placement").and_then(|x| x.as_array())
        .or_else(|| v.get("board").and_then(|b| b.get("placement")).and_then(|x| x.as_array()))
        .ok_or("missing placement[]")?;
    let mut board = Board::empty(puzzle);
    for item in arr {
        if item.is_null() { continue; }
        let pos = item.get("pos").and_then(|x| x.as_u64()).ok_or("pos")?;
        let pid = item.get("piece_id").and_then(|x| x.as_u64()).ok_or("pid")?;
        let rot = item.get("rotation").and_then(|x| x.as_u64()).ok_or("rot")?;
        let piece_id = PieceId::try_from(pid as u32).map_err(|e| format!("{e}"))?;
        let rotation = Rotation::from_u8(rot as u8).ok_or("bad rot")?;
        board.place(pos as u32, piece_id, rotation);
    }
    Ok(board)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() < 2 { eprintln!("usage: board_diff <a.json> <b.json>"); std::process::exit(2); }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let a = load_board(&PathBuf::from(&args[0]), &puzzle).expect("load a");
    let b = load_board(&PathBuf::from(&args[1]), &puzzle).expect("load b");

    let mut same_pos_same_piece_rot = 0;
    let mut same_pos_same_piece_diff_rot = 0;
    let mut same_pos_diff_piece = 0;
    let mut perimeter_same = 0;
    let mut perimeter_diff = 0;
    let mut interior_same = 0;
    let mut interior_diff = 0;

    // Build piece-to-position maps for set comparison.
    let mut a_pieces_by_region: std::collections::HashMap<&str, HashSet<PieceId>> = Default::default();
    let mut b_pieces_by_region: std::collections::HashMap<&str, HashSet<PieceId>> = Default::default();

    for pos in 0..puzzle.cell_count() {
        let av = a.get(pos);
        let bv = b.get(pos);
        match (av, bv) {
            (Some((apid, arot)), Some((bpid, brot))) => {
                let same_pos = apid == bpid && arot == brot;
                let perim = is_perimeter_pos(&puzzle, pos);
                if same_pos {
                    same_pos_same_piece_rot += 1;
                    if perim { perimeter_same += 1; } else { interior_same += 1; }
                } else if apid == bpid {
                    same_pos_same_piece_diff_rot += 1;
                    if perim { perimeter_diff += 1; } else { interior_diff += 1; }
                } else {
                    same_pos_diff_piece += 1;
                    if perim { perimeter_diff += 1; } else { interior_diff += 1; }
                }

                // Region binning by row.
                let (_, y) = puzzle.xy(pos);
                let region = match y {
                    0 | 15 => "perim_h",
                    _ if pos % puzzle.width == 0 || pos % puzzle.width == 15 => "perim_v",
                    1..=4 => "top",
                    5..=9 => "mid",
                    10..=14 => "bot",
                    _ => "other",
                };
                a_pieces_by_region.entry(region).or_default().insert(apid);
                b_pieces_by_region.entry(region).or_default().insert(bpid);
            }
            _ => {}
        }
    }

    println!("Board diff: {} vs {}", args[0], args[1]);
    println!("Per-cell:");
    println!("  same (piece+rot): {same_pos_same_piece_rot}");
    println!("  same piece diff rot: {same_pos_same_piece_diff_rot}");
    println!("  diff piece: {same_pos_diff_piece}");
    println!("Perimeter:");
    println!("  same: {perimeter_same} / 60");
    println!("  diff: {perimeter_diff} / 60");
    println!("Interior:");
    println!("  same: {interior_same} / 196");
    println!("  diff: {interior_diff} / 196");

    println!("\nPiece-set overlap by region:");
    let regions: Vec<&str> = vec!["perim_h", "perim_v", "top", "mid", "bot"];
    for r in regions {
        let ap = a_pieces_by_region.get(r).cloned().unwrap_or_default();
        let bp = b_pieces_by_region.get(r).cloned().unwrap_or_default();
        let common = ap.intersection(&bp).count();
        let a_only = ap.difference(&bp).count();
        let b_only = bp.difference(&ap).count();
        println!("  {r}: |A|={} |B|={} common={common} A_only={a_only} B_only={b_only}", ap.len(), bp.len());
    }
}
