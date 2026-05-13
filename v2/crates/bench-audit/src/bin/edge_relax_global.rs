// Vol-21 — Global relaxed-bound exploration.
//
// What is the absolute MAX of `edge_relax(B)` over all starting boards B?
// This gives the true relaxed-uniqueness upper bound on E2.
//
// Strategy: run relaxed-greedy from many random starting boards. Each
// starts with random piece assignments (with border-class respected),
// then iterates the relaxed greedy step. Record the max final score.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::score_board_dense as score_board;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle, Rotation, BORDER};

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

fn border_class_of_piece(puzzle: &Puzzle, pid: u16) -> u8 {
    let e = puzzle.piece(pid).unwrap().edges.as_array();
    e.iter().filter(|&&c| c == BORDER).count() as u8
}

fn rand_seed(state: &mut u64) -> u64 {
    *state = state.wrapping_mul(0x2545F4914F6CDD1D).wrapping_add(1442695040888963407);
    *state
}

/// Build a random starting board: at each cell, place a random piece of
/// the right border-class with a random rotation.
fn random_board(puzzle: &Puzzle, seed: u64) -> Board {
    let mut state = seed.wrapping_mul(0x9E3779B97F4A7C15) | 1;
    let mut by_class: HashMap<u8, Vec<u16>> = HashMap::new();
    for piece in puzzle.pieces() {
        by_class.entry(border_class_of_piece(puzzle, piece.id)).or_default().push(piece.id);
    }
    let mut board = Board::empty(puzzle);
    for pos in 0..puzzle.cell_count() {
        let cls = border_class_of_pos(puzzle, pos);
        let pids = by_class.get(&cls).unwrap();
        let pid_idx = (rand_seed(&mut state) >> 32) as usize % pids.len();
        let pid = pids[pid_idx];
        let rot_idx = (rand_seed(&mut state) >> 32) as u8 % 4;
        let piece = puzzle.piece(pid).unwrap();
        // Find a rotation that satisfies the border constraint.
        let w = puzzle.width;
        let h = puzzle.height;
        let x = pos % w;
        let y = pos / w;
        let n_top = y == 0;
        let n_right = x + 1 == w;
        let n_bot = y + 1 == h;
        let n_left = x == 0;
        let mut placed_rot: Option<Rotation> = None;
        for delta in 0..4 {
            let rot = Rotation::from_u8((rot_idx + delta) % 4).unwrap();
            let e = piece.edges.rotated(rot).as_array();
            if (e[0] == BORDER) != n_top { continue; }
            if (e[1] == BORDER) != n_right { continue; }
            if (e[2] == BORDER) != n_bot { continue; }
            if (e[3] == BORDER) != n_left { continue; }
            placed_rot = Some(rot);
            break;
        }
        if let Some(rot) = placed_rot {
            board.place(pos, pid, rot);
        }
    }
    board
}

fn relaxed_iterate(puzzle: &Puzzle, board: &mut Board, max_iters: u32) -> u32 {
    let n_cells = puzzle.cell_count();
    let mut iter = 0;
    loop {
        iter += 1;
        let mut changes = 0u32;
        for pos in 0..n_cells {
            let cur_local = board.get(pos).map(|(pid, rot)| {
                let e = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
                cell_local_score(puzzle, board, pos, e)
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
                    let s = cell_local_score(puzzle, board, pos, e);
                    if best.map(|(_, _, b)| s > b).unwrap_or(true) {
                        best = Some((piece.id, rot, s));
                    }
                }
            }
            if let Some((pid, rot, s)) = best {
                let cur = board.get(pos);
                let cur_pid = cur.map(|(p, _)| p).unwrap_or(0);
                let cur_rot = cur.map(|(_, r)| r).unwrap_or(Rotation::R0);
                if (pid, rot) != (cur_pid, cur_rot) && s > cur_local {
                    board.place(pos, pid, rot);
                    changes += 1;
                }
            }
        }
        if changes == 0 || iter >= max_iters { break; }
    }
    iter
}

fn main() {
    let mut n_trials: u64 = 100;
    let mut args = std::env::args().skip(1);
    let mut seed_start: u64 = 1;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--n" => n_trials = args.next().unwrap().parse().unwrap(),
            "--seed-start" => seed_start = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let total = 480u32;

    let mut max_score = 0u32;
    let mut max_seed = 0u64;
    let t0 = Instant::now();
    let mut hist: HashMap<u32, u32> = HashMap::new();
    for trial in 0..n_trials {
        let seed = seed_start + trial;
        let mut board = random_board(&puzzle, seed);
        let iters = relaxed_iterate(&puzzle, &mut board, 50);
        let (s, _) = score_board(&puzzle, &board);
        *hist.entry(s).or_default() += 1;
        if s > max_score {
            max_score = s;
            max_seed = seed;
            eprintln!("trial {} (seed {}): {} iters → {}/{}", trial, seed, iters, s, total);
        }
    }
    let dt = t0.elapsed().as_secs_f64();
    eprintln!("\n=== Final ===");
    eprintln!("max relaxed score: {}/{} (seed {})", max_score, total, max_seed);
    eprintln!("ran {} trials in {:.1}s", n_trials, dt);
    let mut scores: Vec<u32> = hist.keys().copied().collect();
    scores.sort();
    eprintln!("score distribution:");
    for s in scores {
        eprintln!("  {}: {}", s, hist[&s]);
    }
}
