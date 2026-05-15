// Vol-60 T9 — relaxed_bound on the MERGED CP-partials (corners + canonical + CP-filled cells).
// This measures basin-quality at the depth our CP search actually reaches.

use std::path::PathBuf;
use eternity2_bench_audit::relaxed_bound;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Rotation};

fn load_partial(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Board {
    let raw = std::fs::read_to_string(path).expect("read");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let mut b = Board::empty(puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for (idx, p) in arr.iter().enumerate() {
            if p.is_null() { continue; }
            let pos = match p.get("pos").and_then(|x| x.as_u64()) {
                Some(v) => v as u32,
                None => idx as u32,
            };
            let pid_u = p["piece_id"].as_u64().unwrap() as u16;
            let pid = PieceId::from(pid_u);
            let rot_u = p["rotation"].as_u64().unwrap() as u8;
            let rot = Rotation::from_u8(rot_u).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn placed_count(b: &Board, puzzle: &eternity2_core::Puzzle) -> u32 {
    (0..puzzle.cell_count()).filter(|&p| b.get(p).is_some()).count() as u32
}

fn main() {
    let dir = std::env::args().nth(1).expect("usage: perm_merged_bounds <dir>");
    let dir = PathBuf::from(dir);
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let mut entries: Vec<_> = std::fs::read_dir(&dir)
        .expect("read dir")
        .filter_map(Result::ok)
        .filter(|e| e.path().extension().map_or(false, |x| x == "json"))
        .collect();
    entries.sort_by_key(|e| e.path());

    println!("perm   placed  relaxed_bound  note");
    let known: std::collections::HashMap<&str, &str> = [
        ("p04", "FA"), ("p02", "FB"), ("p05", "vol-35"), ("p12", "lottery 458"), ("p22", "McGavin"),
    ].iter().copied().collect();
    for entry in entries {
        let path = entry.path();
        let name = path.file_stem().unwrap().to_string_lossy().to_string();
        let pid: String = name.split('_').next().unwrap_or("?").to_string();
        let b = load_partial(&path, &puzzle);
        let placed = placed_count(&b, &puzzle);
        let bound = relaxed_bound(&puzzle, &b);
        let note = known.get(pid.as_str()).copied().unwrap_or("");
        println!("{pid:<5}  {placed:>5}   {bound:>4}/480     {note}");
    }
}
