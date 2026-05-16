// verify_board — canonical board verifier (vol-118 T7 consolidation).
//
// Replaces rescore_board + verify_record. Uses eternity2_export::verify
// which has comprehensive checks:
//   - piece-uniqueness
//   - border-consistency (catches vol-118 bf-bucket bug type)
//   - hint-compliance
//   - edge-match score
//
// Usage: verify_board <board.json> [board.json ...]
// Returns exit-code 0 if all boards legal, 1 if any has violations.

use std::path::{Path, PathBuf};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Rotation};
use eternity2_export::verify;

fn load_board(path: &Path, puzzle: &eternity2_core::Puzzle) -> Result<Board, String> {
    let bytes = std::fs::read(path).map_err(|e| format!("read {path:?}: {e}"))?;
    let v: serde_json::Value = serde_json::from_slice(&bytes).map_err(|e| format!("parse: {e}"))?;
    let arr = v.get("placement")
        .and_then(|x| x.as_array())
        .or_else(|| v.get("board").and_then(|b| b.get("placement")).and_then(|x| x.as_array()))
        .ok_or("missing placement[]")?;
    let mut board = Board::empty(puzzle);
    for (idx, item) in arr.iter().enumerate() {
        if item.is_null() { continue; }
        let pos = item.get("pos").and_then(|x| x.as_u64())
            .unwrap_or(idx as u64) as u32;
        let pid = item.get("piece_id").and_then(|x| x.as_u64()).ok_or("entry missing piece_id")?;
        let rot = item.get("rotation").and_then(|x| x.as_u64()).ok_or("entry missing rotation")?;
        let piece_id = PieceId::try_from(pid as u32).map_err(|e| format!("piece_id: {e}"))?;
        let rotation = Rotation::from_u8(rot as u8).ok_or("bad rotation")?;
        board.place(pos, piece_id, rotation);
    }
    Ok(board)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: verify_board <board.json> [board.json ...]");
        std::process::exit(2);
    }

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, canonical_hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    println!("path                                              placed   matched/total   uniq    hints    borders   status");
    let mut all_ok = true;
    for a in &args {
        let p = PathBuf::from(a);
        match load_board(&p, &puzzle) {
            Ok(board) => {
                let r = verify(&puzzle, &canonical_hints, &board);
                let status = if r.is_legal_complete() {
                    "LEGAL_COMPLETE"
                } else if r.is_legal() {
                    "LEGAL_PARTIAL"
                } else {
                    all_ok = false;
                    "ILLEGAL"
                };
                println!(
                    "{:<50} {:3}/{:<3}   {:3}/{:<3}       {:3}   {}/{}      {:2}        {}",
                    short_path(a),
                    r.placed_count, r.total_cells,
                    r.matched, r.total_adjacencies,
                    r.unique_pieces,
                    r.hint_compliance.matched, r.hint_compliance.total,
                    r.border_violations.len(),
                    status,
                );
                // Detailed breakdown when illegal.
                if !r.is_legal() {
                    if !r.duplicate_pieces.is_empty() {
                        eprintln!("  duplicates: {:?}", r.duplicate_pieces);
                    }
                    if !r.border_violations.is_empty() {
                        eprintln!("  border violations ({}):", r.border_violations.len());
                        for bv in r.border_violations.iter().take(10) {
                            eprintln!("    pos={} side={:?} edge={} expected={:?}",
                                bv.position, bv.side, bv.piece_edge_color, bv.expected);
                        }
                        if r.border_violations.len() > 10 {
                            eprintln!("    ... ({} more)", r.border_violations.len() - 10);
                        }
                    }
                    if !r.hint_compliance.mismatches.is_empty() {
                        eprintln!("  hint mismatches:");
                        for hm in &r.hint_compliance.mismatches {
                            eprintln!("    pos={} expected piece={} rot={:?} actual={:?}",
                                hm.hint_position, u32::from(hm.expected_piece_id), hm.expected_rotation, hm.actual);
                        }
                    }
                }
            }
            Err(e) => {
                println!("{:<50}  ERROR: {}", short_path(a), e);
                all_ok = false;
            }
        }
    }

    std::process::exit(if all_ok { 0 } else { 1 });
}

fn short_path(s: &str) -> String {
    let bn = std::path::Path::new(s)
        .file_name()
        .map(|x| x.to_string_lossy().into_owned())
        .unwrap_or_else(|| s.to_string());
    if bn.len() > 48 {
        format!("...{}", &bn[bn.len() - 45..])
    } else {
        bn
    }
}
