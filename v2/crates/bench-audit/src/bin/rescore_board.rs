// Post-hoc rescorer: reads a board JSON saved by any v14 bench bin
// and prints the canonical /480 score (unplaced cells contribute 0).
// Use to honest-grade CP partials.
//
// Usage: rescore_board <board.json> [<board.json> ...]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Rotation};
use eternity2_solver_trait as _;



fn load_board(path: &Path, puzzle: &eternity2_core::Puzzle) -> Result<Board, String> {
    let bytes = std::fs::read(path).map_err(|e| format!("read {path:?}: {e}"))?;
    let v: serde_json::Value = serde_json::from_slice(&bytes).map_err(|e| format!("parse: {e}"))?;
    // Accept both layouts: {"placement": [...]} (run_e2_5min_bp_ab) and
    // {"board": {"placement": [...]}, ...} (run_e2_restart summary).
    let arr = v.get("placement")
        .and_then(|x| x.as_array())
        .or_else(|| v.get("board").and_then(|b| b.get("placement")).and_then(|x| x.as_array()))
        .ok_or("missing placement[]")?;
    let mut board = Board::empty(puzzle);
    for item in arr {
        if item.is_null() { continue; }
        let pos = item.get("pos").and_then(|x| x.as_u64()).ok_or("entry missing pos")?;
        let pid = item.get("piece_id").and_then(|x| x.as_u64()).ok_or("entry missing piece_id")?;
        let rot = item.get("rotation").and_then(|x| x.as_u64()).ok_or("entry missing rotation")?;
        let piece_id = PieceId::try_from(pid as u32).map_err(|e| format!("piece_id: {e}"))?;
        let rotation = Rotation::from_u8(rot as u8).ok_or("bad rotation")?;
        board.place(pos as u32, piece_id, rotation);
    }
    Ok(board)
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: rescore_board <board.json> [...]");
        std::process::exit(2);
    }
    println!("path\tplaced/256\tmatched/480\tpct");
    for a in &args {
        let p = PathBuf::from(a);
        match load_board(&p, &puzzle) {
            Ok(b) => {
                let placed = placed_count(&b, &puzzle);
                let (m, t) = score_board(&puzzle, &b);
                let pct = m as f64 * 100.0 / t as f64;
                println!("{a}\t{placed}/{}\t{m}/{t}\t{pct:.1}%", puzzle.cell_count());
            }
            Err(e) => eprintln!("{a}\tERROR: {e}"),
        }
    }
}
