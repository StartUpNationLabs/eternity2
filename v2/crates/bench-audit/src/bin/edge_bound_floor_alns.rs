// Vol-22 T1 — Bound-floor ALNS.
//
// Vol-21 proved: ALNS doesn't preserve bound; bound-ascent gains are
// undone within 30s recovery. Fix: after each ALNS run, REJECT the
// repaired board if its bound dropped below the previous bound.
//
// Algorithm:
//   1. From a starting board B0 with bound b0:
//   2. Bound-ascent N swaps → B1 with bound b1 > b0.
//   3. Run ALNS for T ms on B1 → B1_repaired with bound b_repaired.
//   4. If b_repaired >= b1 (preserved bound): accept, continue.
//      If b_repaired < b1: reject the repair, try a different ALNS
//      seed or different operator weights.
//
// Hypothesis: under bound-floor rejection, ALNS will eventually find
// a score-improving move that doesn't drop bound. The trick is to
// generate ENOUGH candidates because most ALNS moves DO drop bound.

#![forbid(unsafe_code)]

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::score_board_dense as score_board;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle, Rotation, BORDER};
use eternity2_localsearch::{
    polish_rotations, piece_swap_hillclimb, run_alns, Acceptance, AlnsConfig, ConflictDriven,
    DestroyOp, MwpmDefectPair, RandomRegion, RepairKind, WorstBand, WorstWindow,
};

fn load_board(path: &std::path::Path, puzzle: &Puzzle) -> Board {
    let raw = std::fs::read_to_string(path).expect("read");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let mut b = Board::empty(puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for p in arr {
            if p.is_null() { continue; }
            let pos = p["pos"].as_u64().unwrap() as u32;
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot = Rotation::from_u8(p["rotation"].as_u64().unwrap() as u8).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn cell_edges(puzzle: &Puzzle, board: &Board, pos: u32) -> Option<[u8; 4]> {
    board.get(pos).map(|(pid, rot)| {
        let piece = puzzle.piece(pid).expect("piece");
        piece.edges.rotated(rot).as_array()
    })
}

fn cell_local_score(puzzle: &Puzzle, board: &Board, pos: u32, edges: [u8; 4]) -> u32 {
    let w = puzzle.width;
    let h = puzzle.height;
    let x = pos % w;
    let y = pos / w;
    let mut s = 0u32;
    if y > 0 {
        if let Some(ne) = cell_edges(puzzle, board, pos - w) {
            if edges[0] != BORDER && ne[2] != BORDER && edges[0] == ne[2] { s += 1; }
        }
    }
    if x + 1 < w {
        if let Some(ne) = cell_edges(puzzle, board, pos + 1) {
            if edges[1] != BORDER && ne[3] != BORDER && edges[1] == ne[3] { s += 1; }
        }
    }
    if y + 1 < h {
        if let Some(ne) = cell_edges(puzzle, board, pos + w) {
            if edges[2] != BORDER && ne[0] != BORDER && edges[2] == ne[0] { s += 1; }
        }
    }
    if x > 0 {
        if let Some(ne) = cell_edges(puzzle, board, pos - 1) {
            if edges[3] != BORDER && ne[1] != BORDER && edges[3] == ne[1] { s += 1; }
        }
    }
    s
}

fn relaxed_bound(puzzle: &Puzzle, board: &Board) -> u32 {
    let mut b = board.clone();
    let n_cells = puzzle.cell_count();
    for _ in 0..20 {
        let mut changes = 0u32;
        for pos in 0..n_cells {
            let cur_local = b.get(pos).map(|(pid, rot)| {
                let e = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
                cell_local_score(puzzle, &b, pos, e)
            }).unwrap_or(0);
            let mut best: Option<(u16, Rotation, u32)> = None;
            let w = puzzle.width;
            let h = puzzle.height;
            let x = pos % w;
            let y = pos / w;
            for piece in puzzle.pieces() {
                for rot in Rotation::ALL {
                    let e = piece.edges.rotated(rot).as_array();
                    if (e[0] == BORDER) != (y == 0) { continue; }
                    if (e[1] == BORDER) != (x + 1 == w) { continue; }
                    if (e[2] == BORDER) != (y + 1 == h) { continue; }
                    if (e[3] == BORDER) != (x == 0) { continue; }
                    let s = cell_local_score(puzzle, &b, pos, e);
                    if best.map(|(_, _, b_)| s > b_).unwrap_or(true) {
                        best = Some((piece.id, rot, s));
                    }
                }
            }
            if let Some((pid, rot, s)) = best {
                let cur = b.get(pos);
                let cur_pid = cur.map(|(p, _)| p).unwrap_or(0);
                let cur_rot = cur.map(|(_, r)| r).unwrap_or(Rotation::R0);
                if (pid, rot) != (cur_pid, cur_rot) && s > cur_local {
                    b.place(pos, pid, rot);
                    changes += 1;
                }
            }
        }
        if changes == 0 { break; }
    }
    score_board(puzzle, &b).0
}

fn border_class_of_pos(puzzle: &Puzzle, pos: u32) -> u8 {
    let x = pos % puzzle.width;
    let y = pos / puzzle.width;
    let mut n = 0u8;
    if x == 0 { n += 1; }
    if x == puzzle.width - 1 { n += 1; }
    if y == 0 { n += 1; }
    if y == puzzle.height - 1 { n += 1; }
    n
}

/// Try to find a bound-ascending swap. Up to max_tries random transpositions.
fn bound_ascending_swap(puzzle: &Puzzle, board: &Board, state: &mut u64, pinned: &BTreeSet<u32>, current_bound: u32, max_tries: u64) -> Option<Board> {
    let mut by_class: std::collections::HashMap<u8, Vec<u32>> = std::collections::HashMap::new();
    for pos in 0..puzzle.cell_count() {
        if pinned.contains(&pos) { continue; }
        by_class.entry(border_class_of_pos(puzzle, pos)).or_default().push(pos);
    }
    let classes: Vec<u8> = by_class.keys().copied().collect();
    if classes.is_empty() { return None; }
    for _ in 0..max_tries {
        *state = state.wrapping_mul(0x9E3779B97F4A7C15) | 1;
        let cls = classes[(*state >> 32) as usize % classes.len()];
        let cells = by_class.get(&cls).unwrap();
        if cells.len() < 2 { continue; }
        *state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let i = (*state >> 32) as usize % cells.len();
        *state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let mut j = (*state >> 32) as usize % cells.len();
        if j == i { j = (j + 1) % cells.len(); }
        let pos_a = cells[i];
        let pos_b = cells[j];
        let (pid_a, rot_a) = board.get(pos_a)?;
        let (pid_b, rot_b) = board.get(pos_b)?;
        if pid_a == pid_b { continue; }
        let mut new_b = board.clone();
        new_b.place(pos_a, pid_b, rot_b);
        new_b.place(pos_b, pid_a, rot_a);
        let new_bound = relaxed_bound(puzzle, &new_b);
        if new_bound > current_bound { return Some(new_b); }
    }
    None
}

fn build_alns_ops() -> Vec<Box<dyn DestroyOp>> {
    vec![
        Box::new(RandomRegion { k: 4 }),
        Box::new(WorstWindow { k: 5 }),
        Box::new(ConflictDriven { max_size: 30 }),
        Box::new(ConflictDriven { max_size: 80 }),
        Box::new(MwpmDefectPair { max_pairs: 12 }),
        Box::new(WorstBand { k_rows: 4 }),
    ]
}

fn try_alns_with_bound_floor(
    puzzle: &Puzzle,
    start: &Board,
    pinned: &BTreeSet<u32>,
    bound_floor: u32,
    alns_ms: u64,
    seed: u64,
    n_attempts: u32,
) -> Option<Board> {
    // Run ALNS up to n_attempts times with different seeds; return the FIRST result
    // whose bound >= bound_floor, preferring higher score among such results.
    let mut best_accepted: Option<(u32, Board)> = None;
    for k in 0..n_attempts {
        let cfg = AlnsConfig {
            time_budget_ms: alns_ms,
            repair_budget_ms: 1500,
            acceptance: Acceptance::SimulatedAnnealing { t: 1.0 + (k as f64) * 0.5 },
            segment_iters: 50,
            seed: seed.wrapping_add((k as u64).wrapping_mul(17)),
            verbose: false,
            repair: RepairKind::Sa,
            cp_fallback_to_sa: true,
            pinned_positions: pinned.iter().copied().collect::<Vec<u32>>(),
            iter_budget: 0,
            lex_break_isoscore: false,
            checkpoint_path: None,
            checkpoint_every_ms: 60_000,
            repair_step_budget: 0,
            cp_repair_parallel: false,
        };
        let mut ops = build_alns_ops();
        let (alns_board, _stats) = run_alns(puzzle, start, ops.as_mut_slice(), &cfg);
        let (alns_board, _) = polish_rotations(puzzle, &alns_board, pinned);
        let (alns_board, _) = piece_swap_hillclimb(puzzle, &alns_board, pinned);
        let new_bound = relaxed_bound(puzzle, &alns_board);
        let (new_score, _) = score_board(puzzle, &alns_board);
        eprintln!("  attempt {}: score={}, bound={} (floor={})", k, new_score, new_bound, bound_floor);
        if new_bound >= bound_floor {
            if best_accepted.as_ref().map(|(s, _)| new_score > *s).unwrap_or(true) {
                best_accepted = Some((new_score, alns_board));
            }
        }
    }
    best_accepted.map(|(_, b)| b)
}

fn main() {
    let mut board_path = PathBuf::new();
    let mut n_outer: u64 = 10;
    let mut alns_ms: u64 = 30_000;
    let mut seed: u64 = 1;
    let mut max_bound_tries: u64 = 500;
    let mut n_alns_attempts: u32 = 5;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--n-outer" => n_outer = args.next().unwrap().parse().unwrap(),
            "--alns-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--max-bound-tries" => max_bound_tries = args.next().unwrap().parse().unwrap(),
            "--n-attempts" => n_alns_attempts = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("usage: edge_bound_floor_alns --board <path> [--n-outer N] [--alns-ms MS] [--n-attempts K]");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let total = 480u32;
    let pinned: BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();

    let mut current = load_board(&board_path, &puzzle);
    let (s0, _) = score_board(&puzzle, &current);
    let b0 = relaxed_bound(&puzzle, &current);
    eprintln!("initial: score={}/{}, bound={}, gap={:+}", s0, total, b0, b0 as i32 - s0 as i32);

    let mut best_score = s0;
    let mut best_bound = b0;
    let mut best = current.clone();
    let mut state = seed;
    let t0 = Instant::now();

    for outer in 0..n_outer {
        let cur_bound = relaxed_bound(&puzzle, &current);
        let (cur_score, _) = score_board(&puzzle, &current);
        eprintln!("\n=== outer {}: score={}, bound={} ===", outer, cur_score, cur_bound);

        let Some(ascended) = bound_ascending_swap(&puzzle, &current, &mut state, &pinned, cur_bound, max_bound_tries) else {
            eprintln!("no bound-ascending swap found in {} tries (bound={} stuck)", max_bound_tries, cur_bound);
            break;
        };
        let asc_bound = relaxed_bound(&puzzle, &ascended);
        let (asc_score, _) = score_board(&puzzle, &ascended);
        eprintln!("bound-ascended: score={}, bound={} (Δbound=+{})", asc_score, asc_bound, asc_bound - cur_bound);

        // ALNS with bound-floor rejection
        eprintln!("running ALNS up to {} attempts with bound_floor={}", n_alns_attempts, asc_bound);
        match try_alns_with_bound_floor(&puzzle, &ascended, &pinned, asc_bound, alns_ms, seed.wrapping_add(outer * 91), n_alns_attempts) {
            Some(repaired) => {
                let (s_new, _) = score_board(&puzzle, &repaired);
                let b_new = relaxed_bound(&puzzle, &repaired);
                eprintln!("ACCEPTED repair: score={}, bound={}", s_new, b_new);
                current = repaired;
                if s_new > best_score || (s_new == best_score && b_new > best_bound) {
                    best_score = s_new;
                    best_bound = b_new;
                    best = current.clone();
                    eprintln!("** NEW BEST: score={}, bound={}", best_score, best_bound);
                    let out_path = format!("output/v22_bound_floor_s{}_b{}.json", s_new, b_new);
                    let json = serde_json::json!({
                        "matched_best": s_new,
                        "relaxed_bound": b_new,
                        "placement": (0..puzzle.cell_count()).map(|p| {
                            best.get(p).map(|(pid, rot)| serde_json::json!({
                                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                            }))
                        }).collect::<Vec<_>>(),
                    });
                    std::fs::write(&out_path, serde_json::to_string_pretty(&json).unwrap()).expect("write");
                    eprintln!("Saved {}", out_path);
                }
            }
            None => {
                eprintln!("NO repair preserved bound_floor {}; falling back to original board", asc_bound);
                // Don't update `current`; try another bound-ascent next iter
            }
        }
    }
    let dt = t0.elapsed().as_secs_f64();
    eprintln!("\n=== Final: score {} → best {}, bound {} → best {} in {:.1}s ===",
        s0, best_score, b0, best_bound, dt);
}
