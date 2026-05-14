// Sequential cluster-repair on the vol-32 457 (class B) board.
// Class B has all I-I mismatches in rows 1-4 (top band), unlike class A
// (bottom band). Test if class B is also MIP-locally-optimal.

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

fn add_halo(puzzle: &Puzzle, cells: &[Position], radius: u32) -> Vec<Position> {
    let mut set: std::collections::BTreeSet<Position> = cells.iter().copied().collect();
    for _ in 0..radius {
        let snapshot: Vec<Position> = set.iter().copied().collect();
        for c in snapshot {
            let (x, y) = puzzle.xy(c);
            let nbrs: [(i64, i64); 4] = [
                (x as i64, y as i64 - 1),
                (x as i64 + 1, y as i64),
                (x as i64, y as i64 + 1),
                (x as i64 - 1, y as i64),
            ];
            for (nx, ny) in nbrs {
                if nx < 1 || ny < 1 || nx >= (puzzle.width as i64 - 1) || ny >= (puzzle.height as i64 - 1) {
                    continue;
                }
                set.insert((ny as u32) * puzzle.width + (nx as u32));
            }
        }
    }
    set.into_iter().collect()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut halo_radius: u32 = 0;
    let mut time_limit_secs: f64 = 60.0;
    let mut iter = args.iter();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--halo" => halo_radius = iter.next().unwrap().parse().unwrap(),
            "--time-limit-secs" => time_limit_secs = iter.next().unwrap().parse().unwrap(),
            other => eprintln!("(unrecognized: {other})"),
        }
    }
    let board_path = "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json";
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let mut board = load_board(&PathBuf::from(board_path), &puzzle).expect("load board");
    let (matched_0, total_0) = score_board(&puzzle, &board);
    println!("Initial score: {matched_0}/{total_0}  halo_radius={halo_radius}");

    // Class B clusters from mismatch_map output on vol-32 457 s7:
    let clusters: Vec<Vec<(u32, u32)>> = vec![
        vec![(6,1), (7,1), (8,1), (7,2), (8,2)],            // C0 size=5
        vec![(3,2), (4,2), (5,2), (3,3), (3,4)],            // C1 size=5
        vec![(9,1), (9,2), (10,2), (11,2)],                 // C2 size=4
        vec![(8,3), (7,4), (8,4)],                          // C3 size=3
        vec![(10,4), (11,4)],                               // C4 size=2
        vec![(12,1), (13,1)],                               // C5 size=2
    ];

    let opts = ClusterOptions { time_limit_secs, threads: 4, verbose: false };
    let mut total_delta: i32 = 0;

    for (idx, c_coords) in clusters.iter().enumerate() {
        let cluster_core: Vec<Position> = c_coords.iter().map(|&(x,y)| y * puzzle.width + x).collect();
        let cluster: Vec<Position> = if halo_radius > 0 { add_halo(&puzzle, &cluster_core, halo_radius) } else { cluster_core.clone() };
        println!("\n=== Cluster C{idx} core_size={} region_size={} ===", c_coords.len(), cluster.len());
        match repair_cluster(&puzzle, &board, &cluster, opts.clone()) {
            Ok(r) => {
                println!("  obj_new={:.1}  delta={:+}  time={:.2}s", r.obj_value, r.delta, r.solve_secs);
                if r.delta > 0 {
                    for &(c, pid, rot) in &r.assignments { board.place(c, pid, rot); }
                    total_delta += r.delta;
                    let (m, t) = score_board(&puzzle, &board);
                    println!("  APPLIED. New score: {m}/{t}");
                } else {
                    println!("  no improvement (delta={}), skipping", r.delta);
                }
            }
            Err(e) => println!("  ERROR: {e}"),
        }
    }

    let (matched_f, total_f) = score_board(&puzzle, &board);
    println!("\n========================================");
    println!("Final score: {matched_f}/{total_f}  (delta_total={total_delta})");
}
