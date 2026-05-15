// Take a board's border, swap two edge pieces, compute LP UB on the perturbed
// border. Repeat for many random swap-pairs. Records the spread of UBs.
//
// Question being asked: is the LP UB sensitive to local border perturbations?
// If yes, hill-climbing over borders by LP UB might find a higher-UB region.
// If no, the LP UB is a stable basin-property and perturbations don't help.
//
// Usage: border_lp_perturb <board.json> [--swaps N] [--seed S]

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::{
    is_perimeter_pos, lp_ub_with, perimeter_positions, strip_interior_except_hints, LpOptions,
};
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

fn is_corner_pos(puzzle: &Puzzle, pos: Position) -> bool {
    let (x, y) = puzzle.xy(pos);
    (x == 0 || x == puzzle.width - 1) && (y == 0 || y == puzzle.height - 1)
}

/// Forced rotation for an edge piece at `pos`: the BORDER side faces outward.
fn forced_edge_rotation(puzzle: &Puzzle, pos: Position, pid: PieceId) -> Option<Rotation> {
    let (x, y) = puzzle.xy(pos);
    // Which "outward" side faces border? side index: 0=top,1=right,2=bot,3=left
    let mut outward_side = None;
    if y == 0 { outward_side = Some(0u8); }
    else if y == puzzle.height - 1 { outward_side = Some(2u8); }
    else if x == 0 { outward_side = Some(3u8); }
    else if x == puzzle.width - 1 { outward_side = Some(1u8); }
    let outward_side = outward_side?;
    let p = puzzle.piece(pid)?;
    for &r in &Rotation::ALL {
        let e = p.edges.rotated(r).as_array();
        if e[outward_side as usize] == eternity2_core::BORDER {
            return Some(r);
        }
    }
    None
}

fn forced_corner_rotation(puzzle: &Puzzle, pos: Position, pid: PieceId) -> Option<Rotation> {
    let (x, y) = puzzle.xy(pos);
    // Corner has TWO outward sides facing border.
    let mut outward = [false; 4];
    if y == 0 { outward[0] = true; }
    if x == puzzle.width - 1 { outward[1] = true; }
    if y == puzzle.height - 1 { outward[2] = true; }
    if x == 0 { outward[3] = true; }
    let p = puzzle.piece(pid)?;
    for &r in &Rotation::ALL {
        let e = p.edges.rotated(r).as_array();
        let mut ok = true;
        for (i, want) in outward.iter().enumerate() {
            if *want && e[i] != eternity2_core::BORDER { ok = false; break; }
        }
        if ok {
            return Some(r);
        }
    }
    None
}

fn main() {
    let mut path_arg: Option<String> = None;
    let mut swaps: usize = 5;
    let mut seed_arg: u64 = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--swaps" => swaps = args.next().unwrap().parse().unwrap(),
            "--seed" => seed_arg = args.next().unwrap().parse().unwrap(),
            _ => {
                if path_arg.is_none() { path_arg = Some(a); }
                else { eprintln!("(unrecognized: {a})"); }
            }
        }
    }
    let path_arg = path_arg.expect("usage: border_lp_perturb <board.json> [--swaps N] [--seed S]");

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let hint_positions: Vec<Position> = hints.hints.iter().map(|h| h.position).collect();

    let board = load_board(&PathBuf::from(&path_arg), &puzzle).expect("load board");
    let border_board = strip_interior_except_hints(&puzzle, &board, &hint_positions);

    // Collect the non-corner perimeter positions (edge cells).
    let edge_positions: Vec<Position> = perimeter_positions(&puzzle)
        .into_iter()
        .filter(|&p| !is_corner_pos(&puzzle, p))
        .collect();

    // Compute baseline UB.
    let opts = LpOptions { verbose: false, threads: 8, time_limit_secs: 600.0, use_ipm: true, presolve: true, integer: false, force_bi_match: Vec::new() };
    eprintln!("Computing baseline LP UB on {} ...", path_arg);
    let baseline = lp_ub_with(&puzzle, &border_board, opts.clone()).expect("baseline LP");
    println!("baseline\ttotal_ub={:.4}\tbi_ub={:.4}\tinterior_ub={:.4}\ttime={:.1}s",
        baseline.total_ub, baseline.bi_ub, baseline.interior_ub, baseline.solve_secs);

    // RNG
    use std::cell::Cell;
    let rng_state = Cell::new(seed_arg.wrapping_mul(0x517cc1b727220a95));
    let mut next_u64 = || {
        let mut s = rng_state.get();
        s ^= s << 13;
        s ^= s >> 7;
        s ^= s << 17;
        rng_state.set(s);
        s
    };

    for swap_i in 0..swaps {
        // Pick two distinct edge positions.
        let i = (next_u64() as usize) % edge_positions.len();
        let mut j = (next_u64() as usize) % edge_positions.len();
        while j == i { j = (next_u64() as usize) % edge_positions.len(); }
        let p1 = edge_positions[i];
        let p2 = edge_positions[j];
        let (pid1, _r1) = border_board.get(p1).expect("p1 occupied");
        let (pid2, _r2) = border_board.get(p2).expect("p2 occupied");

        // Compute forced rotations at swapped positions.
        let new_r1 = forced_edge_rotation(&puzzle, p1, pid2);
        let new_r2 = forced_edge_rotation(&puzzle, p2, pid1);
        if new_r1.is_none() || new_r2.is_none() {
            println!("swap_{swap_i}\tp1={p1}\tp2={p2}\tSKIPPED: rotation infeasible");
            continue;
        }
        let new_r1 = new_r1.unwrap();
        let new_r2 = new_r2.unwrap();

        // Construct perturbed board.
        let mut perturbed = border_board.clone();
        perturbed.place(p1, pid2, new_r1);
        perturbed.place(p2, pid1, new_r2);

        // LP UB on perturbed.
        match lp_ub_with(&puzzle, &perturbed, opts.clone()) {
            Ok(r) => {
                let dub = r.total_ub - baseline.total_ub;
                println!("swap_{swap_i}\tp1={p1}\tp2={p2}\ttotal_ub={:.4}\tdelta={:+.4}\ttime={:.1}s",
                    r.total_ub, dub, r.solve_secs);
            }
            Err(e) => {
                println!("swap_{swap_i}\tp1={p1}\tp2={p2}\tERROR: {e}");
            }
        }
    }
}
