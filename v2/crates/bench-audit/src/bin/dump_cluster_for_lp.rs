// Vol-55 — dump a small rectangular cluster of cells from a saved board
// as JSON suitable for a Python LP/MIP test.
//
// Usage: dump_cluster_for_lp <board.json> <x0> <y0> <w> <h> <out.json>
//
// Output JSON shape:
// {
//   "puzzle": {
//     "n_pieces": 256,
//     "pieces": [[N, E, S, W], ...]   (color or 255 for BORDER)
//   },
//   "cluster": {
//     "x0": ..., "y0": ..., "w": ..., "h": ...,
//     "cells": [
//        { "pos": ..., "x": ..., "y": ...,
//          "is_border_cell": ...,            // is on outer ring of 16x16
//          "current_pid": ..., "current_rot": ... }
//     ],
//     "internal_edges": [
//        { "edge_id": ..., "c1_pos": ..., "c2_pos": ..., "dir": "E"/"S",
//          "c1_side": ..., "c2_side": ... }   // 0/1/2/3 for N/E/S/W
//     ]
//   },
//   "pieces_used_outside_cluster": [...]    // can't be reused inside
// }

use std::collections::HashSet;
use std::path::{Path, PathBuf};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Rotation, BORDER};
use eternity2_solver_trait as _;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}

fn is_border_cell(x: u32, y: u32, w: u32, h: u32) -> bool {
    x == 0 || x + 1 == w || y == 0 || y + 1 == h
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() < 6 {
        eprintln!("usage: dump_cluster_for_lp <board.json> <x0> <y0> <w> <h> <out.json>");
        std::process::exit(2);
    }
    let board_path = PathBuf::from(&args[0]);
    let x0: u32 = args[1].parse().expect("x0");
    let y0: u32 = args[2].parse().expect("y0");
    let cw: u32 = args[3].parse().expect("w");
    let ch: u32 = args[4].parse().expect("h");
    let out_path = PathBuf::from(&args[5]);
    let board = load_board(&board_path, &puzzle).expect("load board");

    let pw = puzzle.width;
    let ph = puzzle.height;

    // 1. Puzzle pieces array
    let mut pieces_json = Vec::with_capacity(puzzle.pieces().len());
    for piece in puzzle.pieces() {
        let e = piece.edges.as_array();
        pieces_json.push(serde_json::json!([e[0], e[1], e[2], e[3]]));
    }

    // 2. Cluster cells
    let mut cluster_cells = Vec::new();
    let mut cluster_positions: HashSet<u32> = HashSet::new();
    for dy in 0..ch {
        for dx in 0..cw {
            let x = x0 + dx;
            let y = y0 + dy;
            if x >= pw || y >= ph { continue; }
            let pos = y * pw + x;
            let is_b = is_border_cell(x, y, pw, ph);
            let (cur_pid, cur_rot) = board.get(pos).map(|(p, r)| (p as u32, r.as_u8())).unwrap_or((u32::MAX, u8::MAX));
            cluster_cells.push(serde_json::json!({
                "pos": pos,
                "x": x,
                "y": y,
                "is_border_cell": is_b,
                "current_pid": if cur_pid == u32::MAX { serde_json::Value::Null } else { serde_json::Value::Number(cur_pid.into()) },
                "current_rot": if cur_rot == u8::MAX { serde_json::Value::Null } else { serde_json::Value::Number(cur_rot.into()) },
            }));
            cluster_positions.insert(pos);
        }
    }

    // 3. Internal edges within cluster
    let mut edges = Vec::new();
    let mut edge_id = 0u32;
    for dy in 0..ch {
        for dx in 0..cw {
            let x = x0 + dx;
            let y = y0 + dy;
            if x >= pw || y >= ph { continue; }
            let pos = y * pw + x;
            if !cluster_positions.contains(&pos) { continue; }
            // East
            if x + 1 < pw {
                let east = pos + 1;
                if cluster_positions.contains(&east) {
                    edges.push(serde_json::json!({
                        "edge_id": edge_id, "c1_pos": pos, "c2_pos": east, "dir": "E",
                        "c1_side": 1, "c2_side": 3,
                    }));
                    edge_id += 1;
                }
            }
            // South
            if y + 1 < ph {
                let south = pos + pw;
                if cluster_positions.contains(&south) {
                    edges.push(serde_json::json!({
                        "edge_id": edge_id, "c1_pos": pos, "c2_pos": south, "dir": "S",
                        "c1_side": 2, "c2_side": 0,
                    }));
                    edge_id += 1;
                }
            }
        }
    }

    // 4. Pieces used OUTSIDE the cluster (these are unavailable for the LP)
    let mut pieces_used_outside: Vec<u32> = Vec::new();
    for pos in 0..puzzle.cell_count() {
        if cluster_positions.contains(&pos) { continue; }
        if let Some((pid, _)) = board.get(pos) {
            pieces_used_outside.push(pid as u32);
        }
    }

    // 5. Boundary constraints: edges where one cell is in cluster, neighbor is outside cluster.
    // The cluster cell's edge color toward outside is FIXED to match the (already-placed) neighbour.
    let mut boundary = Vec::new();
    for &pos in &cluster_positions {
        let x = pos % pw;
        let y = pos / pw;
        let dirs: [(i32, i32, usize, usize, &str); 4] = [
            (0, -1, 0, 2, "N"), (1, 0, 1, 3, "E"), (0, 1, 2, 0, "S"), (-1, 0, 3, 1, "W"),
        ];
        for (dx, dy, my_side, their_side, name) in dirs {
            let nx = x as i32 + dx;
            let ny = y as i32 + dy;
            if nx < 0 || nx >= pw as i32 || ny < 0 || ny >= ph as i32 { continue; }
            let npos = (ny as u32) * pw + nx as u32;
            if cluster_positions.contains(&npos) { continue; }
            // Neighbor is outside cluster; its color (if placed) determines our edge.
            if let Some((npid, nrot)) = board.get(npos) {
                let nedges = puzzle.piece(npid).expect("piece").edges.rotated(nrot).as_array();
                let forced_color = nedges[their_side];
                boundary.push(serde_json::json!({
                    "pos": pos, "side": my_side, "dir": name, "color": forced_color,
                }));
            }
        }
    }

    // Also any cell on the outer ring of the puzzle has BORDER on its outer side(s).
    let mut frame = Vec::new();
    for &pos in &cluster_positions {
        let x = pos % pw;
        let y = pos / pw;
        if y == 0 { frame.push(serde_json::json!({ "pos": pos, "side": 0, "color": BORDER })); }
        if x + 1 == pw { frame.push(serde_json::json!({ "pos": pos, "side": 1, "color": BORDER })); }
        if y + 1 == ph { frame.push(serde_json::json!({ "pos": pos, "side": 2, "color": BORDER })); }
        if x == 0 { frame.push(serde_json::json!({ "pos": pos, "side": 3, "color": BORDER })); }
    }

    let out = serde_json::json!({
        "puzzle": { "n_pieces": pieces_json.len(), "pieces": pieces_json },
        "cluster": {
            "x0": x0, "y0": y0, "w": cw, "h": ch,
            "cells": cluster_cells,
            "internal_edges": edges,
            "boundary_edges": boundary,
            "frame_edges": frame,
        },
        "pieces_used_outside_cluster": pieces_used_outside,
        "border_sentinel": BORDER,
    });

    let s = serde_json::to_string_pretty(&out).expect("ser");
    std::fs::write(&out_path, s).expect("write");
    eprintln!("wrote {:?}  cells={}  edges={}  bound={}  frame={}  pieces_used_outside={}",
        out_path, cluster_positions.len(), edge_id, boundary.len(), frame.len(),
        out["pieces_used_outside_cluster"].as_array().map(|a| a.len()).unwrap_or(0));
}
