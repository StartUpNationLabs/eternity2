// Vol-21 — relaxed-bound from the 5-canonical-hint-only starting state.
//
// What is the relaxed-edge bound if we ONLY have the 5 canonical
// hints placed, and let the relaxed iteration fill in the rest with
// the locally-best piece (uniqueness relaxed)?
//
// This gives a theoretical UPPER BOUND on what any 5-hint-respecting
// solution could achieve under cell-by-cell greedy maximization.

#![forbid(unsafe_code)]

use std::path::PathBuf;

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

fn relax_to_max(puzzle: &Puzzle, board: &mut Board) {
    let n_cells = puzzle.cell_count();
    for _ in 0..50 {
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
        if changes == 0 { break; }
    }
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let total = 480u32;

    eprintln!("=== hint-only relaxed bound ===");
    let mut board = Board::empty(&puzzle);
    for h in &hints.hints {
        board.place(h.position, h.piece_id, h.rotation);
    }
    eprintln!("Placed {} hints", hints.hints.len());

    // First: pure-hint placed score (only ~ 0 since hints are isolated)
    let (s_hint_only, _) = score_board(&puzzle, &board);
    eprintln!("score with only hints: {}/{}", s_hint_only, total);

    // Now: greedy fill with relaxed piece-uniqueness.
    // But: starting from a near-empty board, the greedy needs to fill cells first.
    // Modification: at each unplaced cell, find best piece (any, since uniqueness is relaxed).
    let n_cells = puzzle.cell_count();
    for pos in 0..n_cells {
        if board.get(pos).is_some() { continue; }
        // Find any piece+rot for this cell that matches border-class.
        let w = puzzle.width;
        let h = puzzle.height;
        let x = pos % w;
        let y = pos / w;
        for piece in puzzle.pieces() {
            let mut ok_rot: Option<Rotation> = None;
            for rot in Rotation::ALL {
                let e = piece.edges.rotated(rot).as_array();
                if (e[0] == BORDER) != (y == 0) { continue; }
                if (e[1] == BORDER) != (x + 1 == w) { continue; }
                if (e[2] == BORDER) != (y + 1 == h) { continue; }
                if (e[3] == BORDER) != (x == 0) { continue; }
                ok_rot = Some(rot);
                break;
            }
            if let Some(rot) = ok_rot {
                board.place(pos, piece.id, rot);
                break;
            }
        }
    }
    let (s_init_filled, _) = score_board(&puzzle, &board);
    eprintln!("after fill (any piece): {}/{}", s_init_filled, total);

    // Iterate relaxed-greedy.
    relax_to_max(&puzzle, &mut board);
    let (s_final, _) = score_board(&puzzle, &board);
    eprintln!("after relaxed iteration: {}/{}", s_final, total);

    // Run again from many random initial fills.
    eprintln!("\n=== multi-seed: relaxed max from {N} random fills (hints fixed) ===", N = 50);
    let mut max_seen = s_final;
    for seed in 1..=50u64 {
        let mut b = Board::empty(&puzzle);
        for h in &hints.hints {
            b.place(h.position, h.piece_id, h.rotation);
        }
        let mut state = seed.wrapping_mul(0x9E3779B97F4A7C15);
        for pos in 0..n_cells {
            if b.get(pos).is_some() { continue; }
            let w = puzzle.width;
            let h2 = puzzle.height;
            let x = pos % w;
            let y = pos / w;
            // Random piece + rot fitting border-class
            let mut tries = 0;
            loop {
                state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                let pid_idx = (state >> 32) as usize % puzzle.pieces().len();
                let piece = &puzzle.pieces()[pid_idx];
                let rot_idx = ((state >> 16) as u8) % 4;
                let rot = Rotation::from_u8(rot_idx).unwrap();
                let e = piece.edges.rotated(rot).as_array();
                if (e[0] == BORDER) != (y == 0) { tries += 1; if tries > 100 { break; } continue; }
                if (e[1] == BORDER) != (x + 1 == w) { tries += 1; if tries > 100 { break; } continue; }
                if (e[2] == BORDER) != (y + 1 == h2) { tries += 1; if tries > 100 { break; } continue; }
                if (e[3] == BORDER) != (x == 0) { tries += 1; if tries > 100 { break; } continue; }
                b.place(pos, piece.id, rot);
                break;
            }
        }
        relax_to_max(&puzzle, &mut b);
        let (s, _) = score_board(&puzzle, &b);
        if s > max_seen { max_seen = s; eprintln!("seed {}: {}/{}", seed, s, total); }
    }
    eprintln!("\nGlobal max relaxed (hint-respecting): {}/{}", max_seen, total);
}
