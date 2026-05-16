// Sequential cluster-repair on vol-35 lo_00001 (family A*, score 457, LP UB 478).
// Mirror of cluster_repair_458 but for a different basin in the same UB class.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::cluster_repair::{repair_cluster, ClusterOptions};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use eternity2_export::score_board;
use serde_json::Value;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
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
    let mut time_limit_secs: f64 = 120.0;
    let mut iter = args.iter();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--halo" => halo_radius = iter.next().unwrap().parse().unwrap(),
            "--time-limit-secs" => time_limit_secs = iter.next().unwrap().parse().unwrap(),
            other => eprintln!("(unrecognized: {other})"),
        }
    }
    let board_path = "output/vol-35/landscape_t3/lo_00001_t00_s002_d207_s457.json";
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let mut board = load_board(&PathBuf::from(board_path), &puzzle).expect("load board");
    let (matched_0, total_0) = score_board(&puzzle, &board);
    println!("Initial score: {matched_0}/{total_0}  halo_radius={halo_radius}");

    let clusters: Vec<Vec<(u32, u32)>> = vec![
        vec![(11,12),(12,12),(10,13),(11,13),(12,13)],     // C0 size=5
        vec![(14,13),(12,14),(13,14),(14,14)],             // C1 size=4
        vec![(7,12),(7,13),(8,13),(8,14)],                 // C2 size=4
        vec![(1,12),(2,12),(2,13)],                        // C3 size=3
        vec![(4,12),(4,13)],                               // C4 size=2
        vec![(9,12),(10,12)],                              // C5 size=2
        vec![(3,13),(3,14)],                               // C6 size=2
        vec![(1,13),(1,14)],                               // C7 size=2
        vec![(13,12),(14,12)],                             // C8 size=2
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

    if total_delta > 0 {
        std::fs::create_dir_all("output/vol-44_cluster_repair").ok();
        let placement: Vec<_> = (0..puzzle.cell_count()).filter_map(|p| {
            board.get(p).map(|(pid, rot)| {
                serde_json::json!({ "pos": p, "piece_id": pid, "rotation": rot.as_u8() })
            })
        }).collect();
        let out = serde_json::json!({ "matched": matched_f, "total": total_f, "placement": placement });
        let out_path = format!("output/vol-44_cluster_repair/lo00001_after_repair_h{halo_radius}.json");
        std::fs::write(&out_path, serde_json::to_string_pretty(&out).unwrap()).expect("write");
        println!("Saved to {out_path}");
    }
}
