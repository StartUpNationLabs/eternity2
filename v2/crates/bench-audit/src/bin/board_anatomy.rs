// Anatomy of a canonical-E2 board: split the 480 internal adjacencies
// into B-B, B-I, I-I classes and count matched/total in each.
//
// Usage: board_anatomy <board.json> [<board.json> ...]
//
// Output (TSV):
//   path  score  bb_match/60  bi_match/56  ii_match/364

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::{is_perimeter_pos};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Puzzle, Rotation};
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

fn anatomy(puzzle: &Puzzle, board: &Board) -> (u32, u32, u32, u32, u32, u32) {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut bb_match = 0u32;
    let mut bb_total = 0u32;
    let mut bi_match = 0u32;
    let mut bi_total = 0u32;
    let mut ii_match = 0u32;
    let mut ii_total = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let pos_per = is_perimeter_pos(puzzle, pos);
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let Some(p) = puzzle.piece(pid) else { continue; };
            let e = p.edges.rotated(rot).as_array();
            // right neighbor
            if x + 1 < w {
                let n = y * w + (x + 1);
                let n_per = is_perimeter_pos(puzzle, n);
                if let Some((npid, nrot)) = board.get(n) {
                    if let Some(np) = puzzle.piece(npid) {
                        let ne = np.edges.rotated(nrot).as_array();
                        let m = if e[1] == ne[3] { 1 } else { 0 };
                        match (pos_per, n_per) {
                            (true, true)   => { bb_total += 1; bb_match += m; }
                            (true, false) | (false, true) => { bi_total += 1; bi_match += m; }
                            (false, false) => { ii_total += 1; ii_match += m; }
                        }
                    }
                }
            }
            // bottom neighbor
            if y + 1 < h {
                let n = (y + 1) * w + x;
                let n_per = is_perimeter_pos(puzzle, n);
                if let Some((npid, nrot)) = board.get(n) {
                    if let Some(np) = puzzle.piece(npid) {
                        let ne = np.edges.rotated(nrot).as_array();
                        let m = if e[2] == ne[0] { 1 } else { 0 };
                        match (pos_per, n_per) {
                            (true, true)   => { bb_total += 1; bb_match += m; }
                            (true, false) | (false, true) => { bi_total += 1; bi_match += m; }
                            (false, false) => { ii_total += 1; ii_match += m; }
                        }
                    }
                }
            }
        }
    }
    (bb_match, bb_total, bi_match, bi_total, ii_match, ii_total)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: board_anatomy <board.json> [...]");
        std::process::exit(2);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    println!("path\tbb\tbi\tii\ttotal");
    for arg in &args {
        match load_board(&PathBuf::from(arg), &puzzle) {
            Ok(b) => {
                let (bbm, bbt, bim, bit, iim, iit) = anatomy(&puzzle, &b);
                let total_m = bbm + bim + iim;
                let total_t = bbt + bit + iit;
                println!("{arg}\t{bbm}/{bbt}\t{bim}/{bit}\t{iim}/{iit}\t{total_m}/{total_t}");
            }
            Err(e) => eprintln!("{arg}\tERROR: {e}"),
        }
    }
}
