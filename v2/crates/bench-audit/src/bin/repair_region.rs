// Repair one user-specified region of the board via MIP.
// Usage:
//   repair_region <board.json> --cells "x1,y1;x2,y2;..." [--time-limit-secs N]
//
// Or special: --all-mismatch-clusters loads the 10 known clusters of
// the vol-32 458 board and unions them.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::cluster_repair::{repair_cluster, ClusterOptions};
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

const VOL32_458_CLUSTERS: &[(u32,u32)] = &[
    (6,12),(7,12),(8,12),(7,13),(8,13),       // C0
    (3,10),(3,11),(3,12),(4,12),(5,12),       // C1
    (1,13),(2,13),(3,13),                     // C2
    (9,13),(10,13),(11,13),                   // C3
    (5,14),(6,14),                            // C4
    (13,13),(14,13),                          // C5
    (4,13),(4,14),                            // C6
    (11,14),(12,14),                          // C7
    (9,14),(10,14),                           // C8
    (2,11),(2,12),                            // C9
];

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut board_path = "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json".to_string();
    let mut cells_arg: Option<String> = None;
    let mut all_mismatch_clusters = false;
    let mut time_limit_secs: f64 = 600.0;
    let mut threads: u32 = 8;
    let mut iter = args.iter().peekable();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--cells" => cells_arg = Some(iter.next().unwrap().clone()),
            "--all-mismatch-clusters" => all_mismatch_clusters = true,
            "--time-limit-secs" => time_limit_secs = iter.next().unwrap().parse().unwrap(),
            "--threads" => threads = iter.next().unwrap().parse().unwrap(),
            other => {
                if !other.starts_with("--") { board_path = other.to_string(); }
                else { eprintln!("(unrecognized: {other})"); }
            }
        }
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let mut board = load_board(&PathBuf::from(&board_path), &puzzle).expect("load board");
    let (matched_0, total_0) = score_board(&puzzle, &board);
    eprintln!("Initial score: {matched_0}/{total_0}");

    let region: Vec<Position> = if all_mismatch_clusters {
        VOL32_458_CLUSTERS.iter().map(|&(x,y)| y * puzzle.width + x).collect()
    } else {
        let s = cells_arg.expect("--cells x1,y1;x2,y2;...");
        s.split(';').map(|tok| {
            let mut p = tok.split(',');
            let x: u32 = p.next().unwrap().parse().unwrap();
            let y: u32 = p.next().unwrap().parse().unwrap();
            y * puzzle.width + x
        }).collect()
    };
    eprintln!("Region size: {}", region.len());

    let opts = ClusterOptions { time_limit_secs, threads, verbose: true };
    match repair_cluster(&puzzle, &board, &region, opts) {
        Ok(r) => {
            println!("\nobj_new={:.1}  delta={:+}  time={:.2}s", r.obj_value, r.delta, r.solve_secs);
            if r.delta > 0 {
                for &(c, pid, rot) in &r.assignments { board.place(c, pid, rot); }
                let (m, t) = score_board(&puzzle, &board);
                println!("APPLIED. New score: {m}/{t}");
                let out_path = "output/vol-44_cluster_repair/board_after_region_repair.json";
                std::fs::create_dir_all("output/vol-44_cluster_repair").ok();
                let placement: Vec<_> = (0..puzzle.cell_count()).filter_map(|p| {
                    board.get(p).map(|(pid, rot)| {
                        serde_json::json!({ "pos": p, "piece_id": pid, "rotation": rot.as_u8() })
                    })
                }).collect();
                let out = serde_json::json!({ "matched": m, "total": t, "placement": placement });
                std::fs::write(out_path, serde_json::to_string_pretty(&out).unwrap()).expect("write");
                println!("Saved to {out_path}");
            } else {
                println!("No improvement.");
            }
        }
        Err(e) => println!("ERROR: {e}"),
    }
}
