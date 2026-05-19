// V140-T1 — Count forbidden 2x2 patches on a board (Rust).

use std::path::PathBuf;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Rotation};
use eternity2_localsearch::intaglio::count_forbidden_2x2;

fn load_cp_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Board {
    let raw = std::fs::read_to_string(path).expect("read board");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let mut b = Board::empty(puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for (idx, p) in arr.iter().enumerate() {
            if p.is_null() { continue; }
            let pos = match p.get("pos").and_then(|x| x.as_u64()) {
                Some(v) => v as u32, None => idx as u32,
            };
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot_u = p["rotation"].as_u64().unwrap() as u8;
            let rot = Rotation::from_u8(rot_u).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let board_path = args.get(1).expect("usage: v140_intaglio_count <board.json>");
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let board = load_cp_board(std::path::Path::new(board_path), &puzzle);
    let forbidden = count_forbidden_2x2(&puzzle, &board);
    let total = (puzzle.width - 1) * (puzzle.height - 1);
    println!("forbidden_2x2: {}/{}", forbidden, total);
}
