// Multi-piece perturbation of a board's border. Pick k random edge cells,
// take a random PERMUTATION of their pieces, place with forced rotations.
// Compute LP UB. Repeat for many trials.
//
// Goal: find a multi-piece swap that INCREASES LP UB beyond the baseline.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::{
    is_perimeter_pos, lp_ub_with, perimeter_positions, strip_interior_except_hints, LpOptions,
};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, BORDER, PieceId, Position, Puzzle, Rotation};
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

fn forced_edge_rotation(puzzle: &Puzzle, pos: Position, pid: PieceId) -> Option<Rotation> {
    let (x, y) = puzzle.xy(pos);
    let outward_side = if y == 0 { Some(0u8) }
        else if y == puzzle.height - 1 { Some(2u8) }
        else if x == 0 { Some(3u8) }
        else if x == puzzle.width - 1 { Some(1u8) }
        else { None };
    let outward_side = outward_side?;
    let p = puzzle.piece(pid)?;
    for &r in &Rotation::ALL {
        let e = p.edges.rotated(r).as_array();
        if e[outward_side as usize] == BORDER {
            return Some(r);
        }
    }
    None
}

fn main() {
    let mut path_arg: Option<String> = None;
    let mut k: usize = 3;
    let mut trials: usize = 5;
    let mut seed_arg: u64 = 1;
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut iter = args.iter();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--k" => k = iter.next().unwrap().parse().unwrap(),
            "--trials" => trials = iter.next().unwrap().parse().unwrap(),
            "--seed" => seed_arg = iter.next().unwrap().parse().unwrap(),
            other => {
                if !other.starts_with("--") { path_arg = Some(other.to_string()); }
                else { eprintln!("(unrecognized: {other})"); }
            }
        }
    }
    let path_arg = path_arg.expect("usage: border_lp_perturb_k <board.json> [--k K] [--trials N]");

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let hint_positions: Vec<Position> = hints.hints.iter().map(|h| h.position).collect();

    let board = load_board(&PathBuf::from(&path_arg), &puzzle).expect("load board");
    let border_board = strip_interior_except_hints(&puzzle, &board, &hint_positions);

    let edge_positions: Vec<Position> = perimeter_positions(&puzzle)
        .into_iter()
        .filter(|&p| !is_corner_pos(&puzzle, p))
        .collect();

    let opts = LpOptions { verbose: false, threads: 8, time_limit_secs: 600.0, use_ipm: true, presolve: true, integer: false };
    eprintln!("Computing baseline LP UB on {} (k={k} trials={trials} seed={seed_arg})...", path_arg);
    let baseline = lp_ub_with(&puzzle, &border_board, opts.clone()).expect("baseline LP");
    println!("baseline\ttotal_ub={:.4}\ttime={:.1}s",
        baseline.total_ub, baseline.solve_secs);

    use std::cell::Cell;
    let rng_state = Cell::new(seed_arg.wrapping_mul(0x517cc1b727220a95).max(1));
    let next_u64 = || {
        let mut s = rng_state.get();
        s ^= s << 13;
        s ^= s >> 7;
        s ^= s << 17;
        rng_state.set(s);
        s
    };

    for trial in 0..trials {
        // Pick k distinct edge positions.
        let mut chosen: Vec<usize> = Vec::with_capacity(k);
        while chosen.len() < k {
            let idx = (next_u64() as usize) % edge_positions.len();
            if !chosen.contains(&idx) { chosen.push(idx); }
        }
        let positions: Vec<Position> = chosen.iter().map(|&i| edge_positions[i]).collect();
        let pids: Vec<PieceId> = positions.iter().map(|&p| border_board.get(p).unwrap().0).collect();

        // Random non-identity permutation of pids.
        let mut perm: Vec<usize> = (0..k).collect();
        // Use Fisher-Yates with our RNG.
        let mut is_identity = true;
        for attempt in 0..10 {
            // Re-shuffle.
            for i in (1..k).rev() {
                let j = (next_u64() as usize) % (i + 1);
                perm.swap(i, j);
            }
            is_identity = perm.iter().enumerate().all(|(i, &p)| i == p);
            if !is_identity { break; }
            if attempt == 9 { break; }
        }
        if is_identity { println!("trial_{trial}\tSKIPPED: identity perm"); continue; }

        // Compute forced rotations for new assignments.
        let mut new_pids_rots: Vec<Option<(PieceId, Rotation)>> = vec![None; k];
        for (slot, &origin) in perm.iter().enumerate() {
            let pos = positions[slot];
            let pid = pids[origin];
            new_pids_rots[slot] = forced_edge_rotation(&puzzle, pos, pid).map(|r| (pid, r));
        }
        if new_pids_rots.iter().any(|o| o.is_none()) {
            println!("trial_{trial}\tSKIPPED: rotation infeasible");
            continue;
        }

        // Construct perturbed board.
        let mut perturbed = border_board.clone();
        for (slot, opt) in new_pids_rots.iter().enumerate() {
            let (pid, rot) = opt.unwrap();
            perturbed.place(positions[slot], pid, rot);
        }

        // LP UB on perturbed.
        match lp_ub_with(&puzzle, &perturbed, opts.clone()) {
            Ok(r) => {
                let dub = r.total_ub - baseline.total_ub;
                println!("trial_{trial}\tk={k}\tpositions={:?}\tperm={:?}\ttotal_ub={:.4}\tdelta={:+.4}\ttime={:.1}s",
                    positions, perm, r.total_ub, dub, r.solve_secs);
                if dub > 0.5 {
                    // Save perturbed board for follow-up
                    std::fs::create_dir_all("output/vol-44_border_perturb_k").ok();
                    let placement: Vec<_> = (0..puzzle.cell_count()).filter_map(|p| {
                        perturbed.get(p).map(|(pid, rot)| {
                            serde_json::json!({ "pos": p, "piece_id": pid, "rotation": rot.as_u8() })
                        })
                    }).collect();
                    let out = serde_json::json!({ "ub_delta": dub, "placement": placement });
                    let out_path = format!("output/vol-44_border_perturb_k/improved_t{trial}_k{k}.json");
                    std::fs::write(&out_path, serde_json::to_string_pretty(&out).unwrap()).expect("write");
                    println!("  SAVED improved border: {out_path}");
                }
            }
            Err(e) => {
                println!("trial_{trial}\tERROR: {e}");
            }
        }
    }
}
