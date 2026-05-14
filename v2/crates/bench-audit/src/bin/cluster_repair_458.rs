// Sequentially repair each I-I mismatch cluster on the vol-32 458 board.
// For each cluster, solve a small MIP that permutes the cluster's pieces
// (rotations included) to maximise internal+boundary edge matches.
// Apply the new placement if delta > 0. Repeat for all 10 clusters.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::is_perimeter_pos;
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

fn xy(puzzle: &Puzzle, p: Position) -> (u32, u32) { puzzle.xy(p) }

fn add_halo(puzzle: &Puzzle, cells: &[Position], radius: u32) -> Vec<Position> {
    let mut set: std::collections::BTreeSet<Position> = cells.iter().copied().collect();
    for _ in 0..radius {
        let snapshot: Vec<Position> = set.iter().copied().collect();
        for c in snapshot {
            let (x, y) = puzzle.xy(c);
            // 4-neighbours (interior only)
            let nbrs: [(i64, i64); 4] = [
                (x as i64, y as i64 - 1),
                (x as i64 + 1, y as i64),
                (x as i64, y as i64 + 1),
                (x as i64 - 1, y as i64),
            ];
            for (nx, ny) in nbrs {
                if nx < 1 || ny < 1 || nx >= (puzzle.width as i64 - 1) || ny >= (puzzle.height as i64 - 1) {
                    continue; // skip perimeter cells
                }
                set.insert((ny as u32) * puzzle.width + (nx as u32));
            }
        }
    }
    set.into_iter().collect()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut board_path = "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json".to_string();
    let mut halo_radius: u32 = 0;
    let mut time_limit_secs: f64 = 60.0;
    let mut iter = args.iter().peekable();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--halo" => halo_radius = iter.next().unwrap().parse().unwrap(),
            "--time-limit-secs" => time_limit_secs = iter.next().unwrap().parse().unwrap(),
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
    println!("Initial score: {matched_0}/{total_0}  halo_radius={halo_radius}");

    // Define clusters for the 458 board (vol-44 mismatch_map output).
    let clusters: Vec<Vec<(u32, u32)>> = vec![
        vec![(6,12), (7,12), (8,12), (7,13), (8,13)],          // C0 size=5
        vec![(3,10), (3,11), (3,12), (4,12), (5,12)],          // C1 size=5
        vec![(1,13), (2,13), (3,13)],                           // C2 size=3
        vec![(9,13), (10,13), (11,13)],                         // C3 size=3
        vec![(5,14), (6,14)],                                   // C4 size=2
        vec![(13,13), (14,13)],                                 // C5 size=2
        vec![(4,13), (4,14)],                                   // C6 size=2
        vec![(11,14), (12,14)],                                 // C7 size=2
        vec![(9,14), (10,14)],                                  // C8 size=2
        vec![(2,11), (2,12)],                                   // C9 size=2
    ];

    let opts = ClusterOptions { time_limit_secs, threads: 4, verbose: false };
    let mut total_delta: i32 = 0;

    for (idx, c_coords) in clusters.iter().enumerate() {
        let cluster_core: Vec<Position> = c_coords.iter().map(|&(x,y)| y * puzzle.width + x).collect();
        let cluster: Vec<Position> = if halo_radius > 0 {
            add_halo(&puzzle, &cluster_core, halo_radius)
        } else {
            cluster_core.clone()
        };
        println!("\n=== Cluster C{idx} core_size={} region_size={} ===", c_coords.len(), cluster.len());
        match repair_cluster(&puzzle, &board, &cluster, opts.clone()) {
            Ok(r) => {
                println!("  obj_new={:.1}  delta={:+}  time={:.2}s", r.obj_value, r.delta, r.solve_secs);
                println!("  assignments:");
                for &(c, pid, rot) in &r.assignments {
                    let (x, y) = xy(&puzzle, c);
                    let old = board.get(c).map(|(p, r)| (p, r.as_u8())).unwrap_or((0, 0));
                    println!("    pos={c} ({x},{y}): {} r{} -> {} r{}", old.0, old.1, pid, rot.as_u8());
                }
                if r.delta > 0 {
                    // Apply.
                    for &(c, pid, rot) in &r.assignments {
                        board.place(c, pid, rot);
                    }
                    total_delta += r.delta;
                    let (m, t) = score_board(&puzzle, &board);
                    println!("  APPLIED. New score: {m}/{t}");
                } else {
                    println!("  no improvement (delta={}), skipping", r.delta);
                }
            }
            Err(e) => {
                println!("  ERROR: {e}");
            }
        }
    }

    let (matched_f, total_f) = score_board(&puzzle, &board);
    println!("\n========================================");
    println!("Final score: {matched_f}/{total_f}  (delta_total={total_delta})");

    // Save the new board if delta > 0
    if total_delta > 0 {
        let out_path = format!("output/vol-44_cluster_repair/board_after_repair.json");
        std::fs::create_dir_all("output/vol-44_cluster_repair").ok();
        let placement: Vec<_> = (0..puzzle.cell_count()).filter_map(|p| {
            board.get(p).map(|(pid, rot)| {
                serde_json::json!({ "pos": p, "piece_id": pid, "rotation": rot.as_u8() })
            })
        }).collect();
        let out = serde_json::json!({
            "matched": matched_f,
            "total": total_f,
            "placement": placement,
        });
        std::fs::write(&out_path, serde_json::to_string_pretty(&out).unwrap()).expect("write");
        println!("Saved to {out_path}");
    }
    let _ = is_perimeter_pos;  // suppress unused import warning
}
