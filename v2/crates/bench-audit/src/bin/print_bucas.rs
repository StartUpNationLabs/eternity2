// print_bucas — print the bucas URL for a board JSON.
// Useful for inspecting partial boards visually.

use std::path::{Path, PathBuf};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Rotation};
use eternity2_export::bucas_url;

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
        let pos = item.get("pos").and_then(|x| x.as_u64()).map(|x| x as u32)
            .unwrap_or(idx as u32);
        let pid = item.get("piece_id").and_then(|x| x.as_u64()).ok_or("entry missing piece_id")?;
        let rot = item.get("rotation").and_then(|x| x.as_u64()).ok_or("entry missing rotation")?;
        let piece_id = PieceId::try_from(pid as u32).map_err(|e| format!("piece_id: {e}"))?;
        let rotation = Rotation::from_u8(rot as u8).ok_or("bad rotation")?;
        board.place(pos, piece_id, rotation);
    }
    Ok(board)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: print_bucas <board.json>");
        std::process::exit(1);
    }
    let path = PathBuf::from(&args[1]);
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let board = load_board(&path, &puzzle).expect("load board");
    let url = bucas_url(&puzzle, &board, "vol118_partial");
    println!("{}", url);
}
