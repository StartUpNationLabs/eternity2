// Vol-21 — ALTERNATING bound-ascent + score-recovery.
//
// One step of bound-ascent (single swap that increases relaxed bound),
// followed by short ALNS to recover the score in the new basin.
//
// This is the key composition: bound-ascent moves us to a higher-
// bound basin; ALNS climbs the score within that basin.

#![forbid(unsafe_code)]

use std::collections::{BTreeSet, HashMap};
use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::score_board_dense as score_board;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle, Rotation, BORDER};
use eternity2_localsearch::{
    polish_rotations, piece_swap_hillclimb, run_alns, Acceptance, AlnsConfig, ConflictDriven,
    DestroyOp, MwpmDefectPair, RandomRegion, RepairKind, WorstBand, WorstWindow,
};

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> eternity2_core::Board {
    eternity2_export::load_board(path, puzzle).expect("load_board")
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

/// Single 2-piece swap mutation respecting border-class. Returns the new board IF
/// the swap STRICTLY INCREASES the bound. Otherwise None.
fn bound_increasing_swap(puzzle: &Puzzle, board: &Board, state: &mut u64, pinned: &BTreeSet<u32>, max_tries: u64) -> Option<Board> {
    let current_bound = relaxed_bound(puzzle, board);
    let mut by_class: HashMap<u8, Vec<u32>> = HashMap::new();
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

fn main() {
    let mut board_path = PathBuf::new();
    let mut n_outer: u64 = 20;
    let mut alns_ms: u64 = 30_000;
    let mut seed: u64 = 1;
    let mut max_bound_tries: u64 = 500;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--n-outer" => n_outer = args.next().unwrap().parse().unwrap(),
            "--alns-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--max-bound-tries" => max_bound_tries = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("usage: edge_bound_score_alt --board <path> [--n-outer N] [--alns-ms MS] [--seed S]");
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
    let mut best = current.clone();
    let mut state = seed;
    let t0 = Instant::now();

    for outer in 0..n_outer {
        eprintln!("\n=== outer {}: bound-ascent step ===", outer);
        let prev_bound = relaxed_bound(&puzzle, &current);
        match bound_increasing_swap(&puzzle, &current, &mut state, &pinned, max_bound_tries) {
            Some(new_b) => {
                let (s_after, _) = score_board(&puzzle, &new_b);
                let bound_after = relaxed_bound(&puzzle, &new_b);
                eprintln!("found bound-incrementing swap: bound {} → {}, score {}/{}",
                    prev_bound, bound_after, s_after, total);
                current = new_b;
            }
            None => {
                eprintln!("no bound-incrementing swap found in {} tries (bound={} stuck)",
                    max_bound_tries, prev_bound);
                break;
            }
        }
        // Now run ALNS to recover score
        let cfg = AlnsConfig {
            time_budget_ms: alns_ms,
            repair_budget_ms: 1500,
            acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
            segment_iters: 50,
            seed: seed.wrapping_add(outer * 17),
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
        let (alns_board, _) = run_alns(&puzzle, &current, ops.as_mut_slice(), &cfg);
        let (alns_board, _) = polish_rotations(&puzzle, &alns_board, &pinned);
        let (alns_board, _) = piece_swap_hillclimb(&puzzle, &alns_board, &pinned);
        let (s_alns, _) = score_board(&puzzle, &alns_board);
        let bound_alns = relaxed_bound(&puzzle, &alns_board);
        eprintln!("ALNS recovery: score={}/{} bound={}", s_alns, total, bound_alns);
        if s_alns > best_score {
            best_score = s_alns;
            best = alns_board.clone();
            eprintln!("** NEW BEST: {}", best_score);
            let out_path = format!("output/v21_alt_best_{}.json", best_score);
            let json = serde_json::json!({
                "matched_best": best_score,
                "placement": (0..puzzle.cell_count()).map(|p| {
                    best.get(p).map(|(pid, rot)| serde_json::json!({
                        "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                    }))
                }).collect::<Vec<_>>(),
            });
            std::fs::write(&out_path, serde_json::to_string_pretty(&json).unwrap()).expect("write");
            eprintln!("Saved {}", out_path);
        }
        current = alns_board;
    }
    let dt = t0.elapsed().as_secs_f64();
    eprintln!("\n=== Final: initial {} → best {} in {:.1}s ===", s0, best_score, dt);
}
