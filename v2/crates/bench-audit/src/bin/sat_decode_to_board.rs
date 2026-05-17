// Decode a kissat SAT solution (v lines from stdin) + emit a board JSON.
// Usage:
//   kissat <cnf> | sat_decode_to_board --puzzle <csv> --pinned-from <board.json> \
//     --free-cells <json-list> --out <board.json>
//
// Reconstructs the VarMap consistent with sat_e2 encoding, parses kissat model,
// decodes back to a Board, writes JSON.

use std::collections::HashMap;
use std::io::{self, BufRead, Write};
use std::path::PathBuf;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_sat_encoder::{decode_model, VarMap, PinnedMap};
use eternity2_core::Rotation;
use serde_json::{json, Value};

#[derive(Parser)]
struct Args {
    #[arg(long)]
    puzzle: PathBuf,

    #[arg(long)]
    pinned_from: PathBuf,

    #[arg(long)]
    free_cells: String,

    #[arg(long)]
    out: PathBuf,

    /// Path to kissat stdout (default: stdin)
    #[arg(long)]
    model: Option<PathBuf>,
}

fn main() {
    let args = Args::parse();
    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).expect("load puzzle");

    // Parse pinned board
    let pinned_text = std::fs::read_to_string(&args.pinned_from).expect("read pinned");
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

    // Parse free cells JSON
    let free: Vec<u32> = serde_json::from_str(&args.free_cells).expect("parse free-cells JSON");
    let free_set: std::collections::HashSet<u32> = free.iter().copied().collect();

    // Build PinnedMap excluding free cells
    let mut pinned_map: PinnedMap = PinnedMap::new();
    for (&pos, &(pid, rot)) in &pinned_board {
        if free_set.contains(&pos) { continue; }
        // Find piece index for this pid
        let piece_idx = puzzle.pieces().iter().position(|p| p.id == pid).unwrap() as u32;
        let rot_val = match rot { 0 => Rotation::R0, 1 => Rotation::R90, 2 => Rotation::R180, _ => Rotation::R270 };
        pinned_map.insert(pos, (piece_idx, rot_val));
    }

    let vmap = VarMap::build_with_pinned(&puzzle, &pinned_map);

    // Read SAT model
    let model_text = if let Some(path) = args.model {
        std::fs::read_to_string(path).expect("read model file")
    } else {
        let mut s = String::new();
        io::stdin().lock().read_to_string(&mut s).expect("read stdin");
        s
    };

    let mut assignment = vec![false; vmap.n_vars];
    for line in model_text.lines() {
        if !line.starts_with("v ") { continue; }
        for tok in line[2..].split_whitespace() {
            let lit: i64 = tok.parse().unwrap_or(0);
            if lit == 0 { continue; }
            let var = lit.abs() as usize;
            if var > 0 && var <= vmap.n_vars {
                assignment[var - 1] = lit > 0;
            }
        }
    }

    // Decode model (excluding the pinned cells which decode_model can't handle directly)
    // We need to build a Board manually: for pinned cells, use their pinned values; for free,
    // find the var assigned to true.
    let mut placement: Vec<(u32, u16, u8)> = Vec::new();
    let n_cells = puzzle.cell_count() as u32;

    for pos in 0..n_cells {
        if let Some(&(pid, rot)) = pinned_board.get(&pos) {
            if !free_set.contains(&pos) {
                placement.push((pos, pid, rot));
                continue;
            }
        }
        // Free cell: find the var that's set to true in cell_to_pr[pos]
        let opts = &vmap.cell_to_pr[pos as usize];
        let mut found = None;
        for &(piece_idx, rot, var) in opts {
            if (var as usize) - 1 < assignment.len() && assignment[(var as usize) - 1] {
                let pid = puzzle.pieces()[piece_idx as usize].id;
                let rot_u8 = match rot { Rotation::R0 => 0, Rotation::R90 => 1, Rotation::R180 => 2, Rotation::R270 => 3 };
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

    std::fs::write(&args.out, serde_json::to_string_pretty(&board).unwrap()).expect("write out");
    eprintln!("Wrote {}", args.out.display());
}

use std::io::Read;
