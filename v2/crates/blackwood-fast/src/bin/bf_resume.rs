// V192-T1: bf_resume — load a partial board JSON, crop to last fully-clean
// row, run hard-edge-match DFS to extend forward.
//
// User idea (vol-192): bf_bw partials have ~7-8 errors near the end. Walk
// back to the last clean row, then resume DFS with strict edge-matching
// (no breaks). Backtrack when stuck. Goal: deep CLEAN partials.

use eternity2_blackwood_fast::{score_board, solve_raw_with_initial_board, RowMajorIndex, PieceRot};
#[allow(unused_imports)]
use eternity2_blackwood_fast::*;
use eternity2_puzzle_io::load_puzzle_with_hints;
use serde_json::Value;
use std::path::PathBuf;

const N: usize = 16;
const WH: usize = 256;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut puzzle_path = PathBuf::from(
        "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv",
    );
    let mut budget_ms: u64 = 5000;
    let mut input_path: Option<PathBuf> = None;
    let mut output_path: Option<PathBuf> = None;
    let mut verbose = false;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&args[i + 1]); i += 2; }
            "--budget-ms" => { budget_ms = args[i + 1].parse().expect("budget"); i += 2; }
            "--input" => { input_path = Some(PathBuf::from(&args[i + 1])); i += 2; }
            "--output" => { output_path = Some(PathBuf::from(&args[i + 1])); i += 2; }
            "--verbose" => { verbose = true; i += 1; }
            _ => { eprintln!("unknown arg: {}", args[i]); std::process::exit(1); }
        }
    }
    let input_path = input_path.expect("--input required");

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    assert_eq!(puzzle.width as usize, N);
    assert_eq!(puzzle.height as usize, N);

    // Load JSON partial.
    let raw = std::fs::read_to_string(&input_path).expect("read input");
    let json: Value = serde_json::from_str(&raw).expect("parse json");
    let placement = json.get("placement").and_then(|v| v.as_array()).expect("placement array");

    // pl[pos] = Option<(piece_id, rot)>
    let mut pl_in: Vec<Option<(u16, u8)>> = vec![None; WH];
    for ent in placement {
        let pos = ent.get("pos").and_then(|v| v.as_u64()).expect("pos") as usize;
        let pid = ent.get("piece_id").and_then(|v| v.as_u64()).expect("piece_id") as u16;
        let rot = ent.get("rotation").and_then(|v| v.as_u64()).unwrap_or(0) as u8;
        if pos < WH {
            pl_in[pos] = Some((pid, rot));
        }
    }

    // Build RowMajorIndex (gives us piece_id -> piece_idx mapping).
    let index = RowMajorIndex::build(&puzzle);
    let n_pieces = index.n_pieces;
    assert_eq!(n_pieces, 256);

    // Map piece_id -> piece_idx
    let mut pid_to_idx: std::collections::HashMap<u16, u16> = std::collections::HashMap::new();
    for (idx, &pid) in index.piece_ids.iter().enumerate() {
        pid_to_idx.insert(pid, idx as u16);
    }

    // Helper to get edges of placed cell.
    // PieceRot encodes (piece_idx, rot); index.edges[piece_idx*4 + rot] = [n, e, s, w].
    let get_edges = |piece_id: u16, rot: u8| -> [u8; 4] {
        let pi = pid_to_idx[&piece_id] as usize;
        index.edges[pi * 4 + rot as usize]
    };

    // Detect mismatches: edge between two placed cells that disagree.
    let mut bad_cells: Vec<bool> = vec![false; WH];
    let mut n_mismatches = 0;
    for pos in 0..WH {
        if pl_in[pos].is_none() { continue; }
        let (pid, rot) = pl_in[pos].unwrap();
        let edges = get_edges(pid, rot);
        let r = pos / N;
        let c = pos % N;
        // East neighbor
        if c < N - 1 {
            if let Some((rpid, rrot)) = pl_in[pos + 1] {
                let r_edges = get_edges(rpid, rrot);
                if edges[1] != r_edges[3] {
                    bad_cells[pos] = true;
                    bad_cells[pos + 1] = true;
                    n_mismatches += 1;
                }
            }
        }
        // South neighbor
        if r < N - 1 {
            if let Some((spid, srot)) = pl_in[pos + 16] {
                let s_edges = get_edges(spid, srot);
                if edges[2] != s_edges[0] {
                    bad_cells[pos] = true;
                    bad_cells[pos + 16] = true;
                    n_mismatches += 1;
                }
            }
        }
    }

    // Find the last fully-clean row R: largest R such that rows 0..=R have
    // all cells placed AND none are bad.
    let mut last_clean_row: i32 = -1;
    for r in 0..N {
        let mut row_clean = true;
        for c in 0..N {
            let pos = r * N + c;
            if pl_in[pos].is_none() || bad_cells[pos] {
                row_clean = false;
                break;
            }
        }
        if row_clean {
            last_clean_row = r as i32;
        } else {
            break;
        }
    }

    if verbose {
        let placed_in = pl_in.iter().filter(|x| x.is_some()).count();
        eprintln!("[bf_resume] input: placed={} mismatches={} last_clean_row={}",
                  placed_in, n_mismatches, last_clean_row);
    }

    // Build initial_board, is_pinned, pieces_used from rows 0..=last_clean_row.
    let mut initial_board: [PieceRot; WH] = [PieceRot::NONE; WH];
    let mut is_pinned: [bool; WH] = [false; WH];
    let mut pieces_used: [u64; 4] = [0; 4];
    let crop_until = if last_clean_row < 0 { 0 } else { (last_clean_row as usize + 1) * N };
    for pos in 0..crop_until {
        if let Some((pid, rot)) = pl_in[pos] {
            let pi = pid_to_idx[&pid];
            initial_board[pos] = PieceRot::new(pi, rot);
            is_pinned[pos] = true;
            pieces_used[(pi as usize) >> 6] |= 1u64 << (pi & 63);
        }
    }

    let n_placed_initial: usize = initial_board.iter().filter(|p| p.0 != PieceRot::NONE.0).count();
    if verbose {
        eprintln!("[bf_resume] cropped initial_board: {} cells placed (rows 0..{})",
                  n_placed_initial, last_clean_row + 1);
    }

    let t0 = std::time::Instant::now();
    let (stats, board) = solve_raw_with_initial_board(
        &index,
        initial_board,
        is_pinned,
        pieces_used,
        budget_ms * 1000,
    );
    let elapsed = t0.elapsed();
    let nps = (stats.nodes as f64) / elapsed.as_secs_f64();
    let score = score_board(&puzzle, &board);

    let placed_after: usize = board.iter().filter(|(pid, _)| *pid != u16::MAX).count();

    if let Some(out_path) = &output_path {
        let mut placements: Vec<serde_json::Value> = Vec::new();
        for (pos, &(pid, rot)) in board.iter().enumerate() {
            if pid == u16::MAX { continue; }
            placements.push(serde_json::json!({
                "pos": pos as u32,
                "piece_id": pid,
                "rotation": rot.as_u8(),
            }));
        }
        let out = serde_json::json!({
            "placement": placements,
            "source": "bf_resume",
            "input_path": input_path.display().to_string(),
            "input_placed": n_placed_initial,
            "last_clean_row": last_clean_row,
            "max_depth": stats.max_depth,
            "score": score,
            "matched": score,
            "placed": placed_after,
            "budget_ms": budget_ms,
        });
        std::fs::create_dir_all(out_path.parent().unwrap_or(std::path::Path::new("."))).ok();
        std::fs::write(out_path, serde_json::to_string(&out).unwrap()).expect("write");
        if verbose {
            eprintln!("[bf_resume] wrote {}", out_path.display());
        }
    }

    println!(
        "{{\"profile\":\"bf_resume\",\"budget_ms\":{},\"elapsed_ms\":{},\"nodes\":{},\"max_depth\":{},\"placed_initial\":{},\"placed_final\":{},\"score\":{},\"nps\":{:.0}}}",
        budget_ms, elapsed.as_millis(), stats.nodes, stats.max_depth,
        n_placed_initial, placed_after, score, nps
    );
}
