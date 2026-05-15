// MIP solve (binary x, binary y) on a fixed-border canonical E2 board.
//
// This is the EXACT integer optimum subject to the LP formulation's
// constraints. HiGHS branch-and-bound finds:
//   - Best feasible integer solution (lower bound on basin ceiling)
//   - Best dual bound (upper bound, tighter than LP relaxation as the
//     B&B progresses).
//
// Usage: border_mip <board.json> [--time-limit-secs N]

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::{lp_ub_with, strip_interior_except_hints, LpOptions};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
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

fn main() {
    let mut path_arg: Option<String> = None;
    let mut time_limit_secs: f64 = 3600.0;
    let mut threads: u32 = 8;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--time-limit-secs" => time_limit_secs = args.next().unwrap().parse().unwrap(),
            "--threads" => threads = args.next().unwrap().parse().unwrap(),
            _ => {
                if path_arg.is_none() { path_arg = Some(a); }
                else { eprintln!("(unrecognized: {a})"); }
            }
        }
    }
    let path_arg = path_arg.expect("usage: border_mip <board.json> [--time-limit-secs N]");

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let hint_positions: Vec<Position> = hints.hints.iter().map(|h| h.position).collect();

    let board = load_board(&PathBuf::from(&path_arg), &puzzle).expect("load board");
    let border_board = strip_interior_except_hints(&puzzle, &board, &hint_positions);

    let opts = LpOptions {
        verbose: true,
        threads,
        time_limit_secs,
        use_ipm: false, // MIP uses simplex for relaxations
        presolve: true,
        integer: true,
        force_bi_match: Vec::new(),
    };
    eprintln!("Running MIP on {path_arg} with time_limit={time_limit_secs}s threads={threads}");
    match lp_ub_with(&puzzle, &border_board, opts) {
        Ok(r) => {
            println!("{path_arg}\tbb={}\tbi_ub={:.4}\tinterior_ub={:.4}\ttotal={:.4}\ttime={:.1}s",
                r.bb_matches, r.bi_ub, r.interior_ub, r.total_ub, r.solve_secs);
        }
        Err(e) => {
            eprintln!("{path_arg}\tERROR: {e}");
        }
    }
}
