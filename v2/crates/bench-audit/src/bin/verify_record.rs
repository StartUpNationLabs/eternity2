// Vol-60 — verify_record: one-shot record verification.
// Per CLAUDE.md scientific-rigor rules, every claimed record must
// pass these checks before being filed in vault.
//
// Usage: verify_record <board.json> [board.json ...]
//
// Output (per board):
//   path  matched/480  placed/256  unique_pieces  hints_obeyed/5  STATUS
//
// STATUS = OK / FAIL_DUP_PIECES / FAIL_MISSING_PIECES / FAIL_HINT_<pos>

use std::path::{Path, PathBuf};

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Rotation};
use eternity2_solver_trait as _;

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
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, canonical_hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: verify_record <board.json> [...]");
        eprintln!("");
        eprintln!("Per CLAUDE.md rule #5: every record claim must pass these checks.");
        eprintln!("Verifies: matched-edges score, piece uniqueness, canonical hint compliance.");
        std::process::exit(2);
    }

    println!("path                                              matched  placed  unique  hints  status");
    let mut all_ok = true;
    for a in &args {
        let p = PathBuf::from(a);
        match load_board(&p, &puzzle) {
            Ok(b) => {
                let placed = placed_count(&b, &puzzle);
                let (matched, _total) = score_board(&puzzle, &b);

                // Piece uniqueness check
                let n_pieces = puzzle.pieces().len();
                let mut piece_used = vec![false; n_pieces];
                let mut dup_count = 0;
                let mut missing_count = 0;
                for pos in 0..puzzle.cell_count() {
                    if let Some((pid, _)) = b.get(pos) {
                        let idx = u32::from(pid) as usize;
                        if idx < piece_used.len() {
                            if piece_used[idx] { dup_count += 1; }
                            piece_used[idx] = true;
                        }
                    }
                }
                for &u in &piece_used { if !u { missing_count += 1; } }

                // Hint compliance check
                let mut hints_obeyed = 0;
                let mut first_failed_hint: Option<u32> = None;
                for hint in &canonical_hints.hints {
                    match b.get(hint.position) {
                        Some((pid, rot)) if pid == hint.piece_id && rot == hint.rotation => {
                            hints_obeyed += 1;
                        }
                        _ => {
                            if first_failed_hint.is_none() { first_failed_hint = Some(hint.position); }
                        }
                    }
                }

                let n_hints = canonical_hints.hints.len() as u32;
                let unique_label = if dup_count == 0 && missing_count == 0 {
                    format!("256/256")
                } else {
                    format!("DUP={} MISSING={}", dup_count, missing_count)
                };

                let status = if dup_count > 0 {
                    format!("FAIL_DUP_PIECES")
                } else if missing_count > 0 && placed == puzzle.cell_count() {
                    format!("FAIL_MISSING_PIECES")
                } else if hints_obeyed == n_hints {
                    format!("OK")
                } else {
                    format!("OK_HINTS_{}of{}", hints_obeyed, n_hints)
                };

                let path_disp = if a.len() > 50 { format!("...{}", &a[a.len()-47..]) } else { a.to_string() };
                println!("{:50}  {}/480  {}/{}  {}  {}/{}  {}",
                    path_disp, matched, placed, puzzle.cell_count(), unique_label,
                    hints_obeyed, n_hints, status);

                if dup_count > 0 || missing_count > 0 { all_ok = false; }
            }
            Err(e) => {
                eprintln!("{a}\tERROR: {e}");
                all_ok = false;
            }
        }
    }
    if !all_ok { std::process::exit(1); }
}
