// Vol-60 T8 — relaxed_bound per corner-perm to measure basin-quality
// independent of search-pipeline performance.
//
// User's question: "they might yield worse scores, but how would we
// know if they are in fact closer to a real solution?"
//
// Answer: measure `relaxed_bound` on the 9-cell partial (corners +
// canonical hints), which is an UPPER BOUND on edge matches achievable
// FROM that geometry, ignoring piece-uniqueness. A basin with higher
// relaxed_bound IS closer to a real solution structurally, even if
// our ALNS produces lower final scores.
//
// Usage: perm_relaxed_bounds (no args; reads corner_partials/)

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

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load");

    let partials_dir = PathBuf::from("output/vol-60/corner_partials");
    let mut entries: Vec<_> = std::fs::read_dir(&partials_dir)
        .expect("read dir")
        .filter_map(Result::ok)
        .filter(|e| e.path().extension().map_or(false, |ext| ext == "json"))
        .collect();
    entries.sort_by_key(|e| e.path());

    println!("perm    TL TR BL BR  relaxed_bound  best_known");
    let known_records: std::collections::HashMap<(u32, u32, u32, u32), &str> = [
        ((0u32, 3u32, 1u32, 2u32), "FA vol-32 458"),
        ((0, 2, 1, 3), "FB blackwood 457"),
        ((0, 3, 2, 1), "vol-35 457"),
        ((2, 0, 1, 3), "lottery 458"),
        ((3, 2, 0, 1), "McGavin 469"),
    ].iter().copied().collect();

    for entry in entries {
        let path = entry.path();
        let name = path.file_stem().unwrap().to_string_lossy().to_string();
        // Parse perm ID from filename "p04_TL0_TR3_BL1_BR2"
        let parts: Vec<&str> = name.split('_').collect();
        if parts.len() < 5 { continue; }
        let pid = parts[0].to_string();
        let tl: u32 = parts[1].strip_prefix("TL").unwrap_or("0").parse().unwrap_or(0);
        let tr: u32 = parts[2].strip_prefix("TR").unwrap_or("0").parse().unwrap_or(0);
        let bl: u32 = parts[3].strip_prefix("BL").unwrap_or("0").parse().unwrap_or(0);
        let br: u32 = parts[4].strip_prefix("BR").unwrap_or("0").parse().unwrap_or(0);

        let board = load_partial(&path, &puzzle);
        let bound = relaxed_bound(&puzzle, &board);

        let note = known_records.get(&(tl, tr, bl, br)).copied().unwrap_or("");
        println!("{pid:<5}    {tl} {tr} {bl} {br}      {bound:>4}/480   {note}");
    }
}
