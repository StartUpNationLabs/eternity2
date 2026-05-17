// Decode a kissat SAT solution (v lines from stdin or file) + emit a board JSON.
// Usage:
//   sat_decode_to_board <puzzle.csv> <pinned-from.json> <free-cells-json> <model-file> <out.json>

use std::collections::HashMap;
use std::io::Read;
use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_sat_encoder::{VarMap, PinnedMap};
use eternity2_core::Rotation;
use serde_json::{json, Value};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 6 {
        eprintln!("usage: sat_decode_to_board <puzzle> <pinned-from> <free-cells-json> <model-file> <out>");
        std::process::exit(2);
    }
    let puzzle_path = PathBuf::from(&args[1]);
    let pinned_path = PathBuf::from(&args[2]);
    let free_cells_str = &args[3];
    let model_path = PathBuf::from(&args[4]);
    let out_path = PathBuf::from(&args[5]);

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let pinned_text = std::fs::read_to_string(&pinned_path).expect("read pinned");
    let pinned_data: Value = serde_json::from_str(&pinned_text).expect("parse pinned JSON");
    let mut pinned_board: HashMap<u32, (u16, u8)> = HashMap::new();
    if let Some(arr) = pinned_data.get("placement").and_then(|v| v.as_array()) {
        for entry in arr {
            let pos = entry["pos"].as_u64().unwrap() as u32;
            let pid = entry["piece_id"].as_u64().unwrap() as u16;
            let rot = entry["rotation"].as_u64().unwrap() as u8;
            pinned_board.insert(pos, (pid, rot));
        }
    }

    let free: Vec<u32> = serde_json::from_str(free_cells_str).expect("parse free-cells JSON");
    let free_set: std::collections::HashSet<u32> = free.iter().copied().collect();

    let mut pinned_map: PinnedMap = PinnedMap::new();
    for (&pos, &(pid, rot)) in &pinned_board {
        if free_set.contains(&pos) { continue; }
        let piece_idx = puzzle.pieces().iter().position(|p| p.id == pid).unwrap() as u32;
        let rot_val = match rot { 0 => Rotation::R0, 1 => Rotation::R90, 2 => Rotation::R180, _ => Rotation::R270 };
        pinned_map.insert(pos, (piece_idx, rot_val));
    }

    let vmap = VarMap::build_with_pinned(&puzzle, &pinned_map);

    let model_text = std::fs::read_to_string(&model_path).expect("read model file");

    let n_vars = vmap.n_vars as usize;
    let mut assignment = vec![false; n_vars];
    for line in model_text.lines() {
        if !line.starts_with("v ") { continue; }
        for tok in line[2..].split_whitespace() {
            let lit: i64 = tok.parse().unwrap_or(0);
            if lit == 0 { continue; }
            let var = lit.abs() as usize;
            if var > 0 && var <= n_vars {
                assignment[var - 1] = lit > 0;
            }
        }
    }

    let mut placement: Vec<(u32, u16, u8)> = Vec::new();
    let n_cells = puzzle.cell_count() as u32;

    for pos in 0..n_cells {
        if let Some(&(pid, rot)) = pinned_board.get(&pos) {
            if !free_set.contains(&pos) {
                placement.push((pos, pid, rot));
                continue;
            }
        }
        let opts = &vmap.cell_to_pr[pos as usize];
        let mut found = None;
        for &(piece_idx, rot, var) in opts {
            if (var as usize) - 1 < assignment.len() && assignment[(var as usize) - 1] {
                let pid = puzzle.pieces()[piece_idx as usize].id;
                let rot_u8: u8 = if rot == Rotation::R0 { 0 }
                                  else if rot == Rotation::R90 { 1 }
                                  else if rot == Rotation::R180 { 2 }
                                  else { 3 };
                found = Some((pid, rot_u8));
                break;
            }
        }
        if let Some((pid, rot_u8)) = found {
            placement.push((pos, pid, rot_u8));
        } else {
            eprintln!("WARNING: no assignment found for cell {pos}");
        }
    }

    let placement_json: Vec<_> = placement.iter().map(|&(pos, pid, rot)| {
        json!({"pos": pos, "piece_id": pid, "rotation": rot})
    }).collect();

    let board = json!({
        "source": "sat_decode_to_board",
        "n_placed": placement.len(),
        "placement": placement_json,
    });

    std::fs::write(&out_path, serde_json::to_string_pretty(&board).unwrap()).expect("write out");
    eprintln!("Wrote {}", out_path.display());
}
