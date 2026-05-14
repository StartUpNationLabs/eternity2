// Cluster boards by their border-placement (60 perimeter cells). Outputs
// a TSV: each board's border-class id + total score + path.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::is_perimeter_pos;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use eternity2_export::score_board;
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

fn border_fingerprint(puzzle: &Puzzle, board: &Board) -> Vec<(Position, PieceId, u8)> {
    let mut out = Vec::new();
    for pos in 0..puzzle.cell_count() {
        if is_perimeter_pos(puzzle, pos) {
            if let Some((pid, rot)) = board.get(pos) {
                out.push((pos, pid, rot.as_u8()));
            }
        }
    }
    out.sort();
    out
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let mut class_map: HashMap<Vec<(Position, PieceId, u8)>, (usize, Vec<(String, u32)>)> = HashMap::new();
    let mut next_id = 0usize;

    for path in &args {
        match load_board(&PathBuf::from(path), &puzzle) {
            Ok(b) => {
                let fp = border_fingerprint(&puzzle, &b);
                let (m, _) = score_board(&puzzle, &b);
                let entry = class_map.entry(fp).or_insert_with(|| { let id = next_id; next_id += 1; (id, Vec::new()) });
                entry.1.push((path.clone(), m));
            }
            Err(e) => eprintln!("{path}\tERROR: {e}"),
        }
    }

    let mut classes: Vec<_> = class_map.into_iter().collect();
    classes.sort_by_key(|c| std::cmp::Reverse(c.1.1.len()));
    println!("class_id\tn_boards\tmax_score\tmin_score\trepresentative_path");
    for (_fp, (id, members)) in classes {
        let scores: Vec<u32> = members.iter().map(|(_, s)| *s).collect();
        let max_s = *scores.iter().max().unwrap();
        let min_s = *scores.iter().min().unwrap();
        let rep = members.iter().max_by_key(|(_, s)| *s).map(|(p, _)| p.clone()).unwrap_or_default();
        println!("{id}\t{}\t{max_s}\t{min_s}\t{rep}", members.len());
    }
}
