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

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let board_path = args.get(0).cloned()
        .unwrap_or_else(|| "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json".to_string());
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let mut board = load_board(&PathBuf::from(&board_path), &puzzle).expect("load board");
    let (matched_0, total_0) = score_board(&puzzle, &board);
    println!("Initial score: {matched_0}/{total_0}");

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

    let opts = ClusterOptions { time_limit_secs: 60.0, threads: 4, verbose: false };
    let mut total_delta: i32 = 0;

    for (idx, c_coords) in clusters.iter().enumerate() {
        let cluster: Vec<Position> = c_coords.iter().map(|&(x,y)| y * puzzle.width + x).collect();
        println!("\n=== Cluster C{idx} size={} cells={:?} ===", c_coords.len(), c_coords);
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
