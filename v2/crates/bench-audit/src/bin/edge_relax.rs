// Vol-21 — Relaxation test: what's the max score when piece-uniqueness
// is RELAXED?
//
// For each cell on the 457 board (or any starting board), find the BEST
// piece from the FULL piece catalog (no uniqueness constraint), placed
// at its best rotation given current neighbors. Greedy iteration to
// convergence.
//
// This gives an UPPER BOUND on what's achievable if we could ignore
// piece-uniqueness. The gap between this bound and 457 measures how
// much "slack" the piece-set has.
//
// If gap > 0: piece-uniqueness is the binding constraint; we need to
//             smartly swap pieces to claim that slack.
// If gap = 0: edge-coloring at current placement is already maximal;
//             the only way past 457 is a fundamentally different
//             ROTATION pattern, not different pieces.
//
// Either result is informative.

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_bench_audit::score_board_dense as score_board;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle, Rotation, BORDER};

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

/// Score local cell with given edges against existing board neighbors.
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

/// For cell at pos, find the best (piece, rotation) in the entire catalog
/// that respects border constraints. No uniqueness.
fn best_piece_rot(puzzle: &Puzzle, board: &Board, pos: u32) -> Option<(u16, Rotation, u32)> {
    let w = puzzle.width;
    let h = puzzle.height;
    let x = pos % w;
    let y = pos / w;
    let mut best: Option<(u16, Rotation, u32)> = None;
    for piece in puzzle.pieces() {
        for rot in Rotation::ALL {
            let e = piece.edges.rotated(rot).as_array();
            // Border match.
            let n_at_top = y == 0;
            let n_at_right = x + 1 == w;
            let n_at_bot = y + 1 == h;
            let n_at_left = x == 0;
            if (e[0] == BORDER) != n_at_top { continue; }
            if (e[1] == BORDER) != n_at_right { continue; }
            if (e[2] == BORDER) != n_at_bot { continue; }
            if (e[3] == BORDER) != n_at_left { continue; }
            let s = cell_local_score(puzzle, board, pos, e);
            if best.map(|(_, _, sc)| s > sc).unwrap_or(true) {
                best = Some((piece.id, rot, s));
            }
        }
    }
    best
}

fn main() {
    let mut board_path = PathBuf::new();
    let mut max_iters: u32 = 20;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--max-iters" => max_iters = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("usage: edge_relax --board <path> [--max-iters 20]");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let mut board = load_board(&board_path, &puzzle);
    let (score, total) = score_board(&puzzle, &board);
    eprintln!("loaded board: {}/{}", score, total);
    eprintln!("piece-uniqueness RELAXED: every cell free to pick ANY piece");

    // Greedy: iterate over cells in a deterministic order. For each cell, pick the
    // best piece+rotation given current neighbors. Repeat until no improvements
    // for a full pass.
    let mut iter = 0u32;
    loop {
        iter += 1;
        let mut changes = 0u32;
        let mut score_delta = 0i32;
        for pos in 0..puzzle.cell_count() {
            let cur = board.get(pos);
            let cur_local = cur.map(|(pid, rot)| {
                let e = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
                cell_local_score(&puzzle, &board, pos, e)
            }).unwrap_or(0);
            if let Some((new_pid, new_rot, new_local)) = best_piece_rot(&puzzle, &board, pos) {
                let cur_pid = cur.map(|(p, _)| p).unwrap_or(0);
                let cur_rot = cur.map(|(_, r)| r).unwrap_or(Rotation::R0);
                if (new_pid, new_rot) != (cur_pid, cur_rot) && new_local > cur_local {
                    board.place(pos, new_pid, new_rot);
                    changes += 1;
                    score_delta += new_local as i32 - cur_local as i32;
                }
            }
        }
        let (s_now, _) = score_board(&puzzle, &board);
        eprintln!("iter {}: {} changes, score now {}/{} (local Δ={:+})", iter, changes, s_now, total, score_delta);
        if changes == 0 || iter >= max_iters {
            break;
        }
    }

    // Final report.
    let (final_score, _) = score_board(&puzzle, &board);
    use std::collections::HashMap;
    let mut piece_use: HashMap<u16, u32> = HashMap::new();
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, _)) = board.get(pos) {
            *piece_use.entry(pid).or_default() += 1;
        }
    }
    let unique = piece_use.len();
    let max_use = piece_use.values().copied().max().unwrap_or(0);
    let multi = piece_use.values().filter(|&&c| c > 1).count();
    eprintln!("\n=== RELAXED RESULT ===");
    eprintln!("Final score: {}/{}", final_score, total);
    eprintln!("Distinct pieces used: {}/{}", unique, puzzle.cell_count());
    eprintln!("Pieces used > 1 time: {} (max use: {})", multi, max_use);
    eprintln!("Gap from baseline 457: {:+}", final_score as i32 - 457);

    // Diagnostics: which pieces are duplicates, and at which positions?
    eprintln!("\n=== Duplicate pieces (relaxed only) ===");
    let mut pieces_at_pos: HashMap<u16, Vec<u32>> = HashMap::new();
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, _)) = board.get(pos) {
            pieces_at_pos.entry(pid).or_default().push(pos);
        }
    }
    let mut dup_pieces: Vec<(u16, Vec<u32>)> = pieces_at_pos.into_iter()
        .filter(|(_, v)| v.len() > 1).collect();
    dup_pieces.sort_by_key(|(p, _)| *p);
    for (pid, ps) in &dup_pieces {
        eprintln!(
            "  pid {} used at {:?}",
            pid,
            ps.iter().map(|p| (p / puzzle.width, p % puzzle.width)).collect::<Vec<_>>()
        );
    }

    eprintln!("\n=== Missing pieces (in catalog but not on relaxed board) ===");
    let placed: std::collections::HashSet<u16> = (0..puzzle.cell_count())
        .filter_map(|pos| board.get(pos).map(|(pid, _)| pid)).collect();
    let missing: Vec<u16> = puzzle.pieces().iter()
        .map(|p| p.id).filter(|p| !placed.contains(p)).collect();
    eprintln!("  {} missing pieces: {:?}", missing.len(), missing);
}
