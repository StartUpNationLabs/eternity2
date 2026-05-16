// Vol-21 — Edge-relax CHAIN finder.
//
// edge_relax discovered: under relaxed piece-uniqueness, the 457 board
// reaches 461. The slack involves:
//   - Duplicate pieces (4 pieces used twice): 82, 146, 205, 233
//   - Missing pieces (4 unused): 189, 204, 207, 245
//
// If we can find a piece-permutation chain that:
//   * places 82 at its secondary spot (2,3) [if currently 82 is at (2,2)]
//   * fills (2,2) [currently 82] with 189/204/207/245
//   * ...etc.
//
// then we exceed 457.
//
// This binary: build the "demand graph" of where each missing piece
// fits well, and search for a valid chain.

#![forbid(unsafe_code)]

use std::collections::{HashMap, HashSet};
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

fn main() {
    let mut board_path = PathBuf::new();
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("usage: edge_relax_chain --board <path>");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let board = load_board(&board_path, &puzzle);
    let (s_old, total) = score_board(&puzzle, &board);
    eprintln!("loaded board: {}/{}", s_old, total);

    // Compute placed/missing pieces.
    let placed: HashSet<u16> = (0..puzzle.cell_count())
        .filter_map(|pos| board.get(pos).map(|(pid, _)| pid)).collect();
    let missing: Vec<u16> = puzzle.pieces().iter()
        .map(|p| p.id).filter(|p| !placed.contains(p)).collect();
    eprintln!("missing pieces: {:?}", missing);
    assert!(missing.is_empty(), "board claims {} pieces placed but missing {} — bad input", placed.len(), missing.len());

    // For each piece in the catalog, compute its "demand" at each (pos, rot):
    //   demand(p, pos, rot) = local_score if placed there given current neighbors,
    //   with border-class match. We're looking for cells where pieces score k=4 or k=3.

    let mut piece_demand: HashMap<u16, Vec<(u32, Rotation, u32)>> = HashMap::new();
    let n_cells = puzzle.cell_count();
    for piece in puzzle.pieces() {
        let pid = piece.id;
        let pcls = border_class_of_piece(&puzzle, pid);
        for pos in 0..n_cells {
            if border_class_of_pos(&puzzle, pos) != pcls { continue; }
            for rot in Rotation::ALL {
                let e = piece.edges.rotated(rot).as_array();
                // border-side check (redundant with class but safe)
                let w = puzzle.width;
                let h = puzzle.height;
                let x = pos % w;
                let y = pos / w;
                if (e[0] == BORDER) != (y == 0) { continue; }
                if (e[1] == BORDER) != (x + 1 == w) { continue; }
                if (e[2] == BORDER) != (y + 1 == h) { continue; }
                if (e[3] == BORDER) != (x == 0) { continue; }
                let s = cell_local_score(&puzzle, &board, pos, e);
                piece_demand.entry(pid).or_default().push((pos, rot, s));
            }
        }
    }

    // For each piece, find its top-4 demand cells.
    eprintln!("\n=== Top demand cells per piece (showing only k≥3) ===");
    let mut pos_score_for_orig: HashMap<u32, u32> = HashMap::new();
    let mut pos_demand_high: HashMap<u32, Vec<(u16, Rotation, u32)>> = HashMap::new();
    let mut piece_best_alt: HashMap<u16, Vec<(u32, Rotation, u32)>> = HashMap::new();
    for (pid, demands) in &piece_demand {
        let mut sorted = demands.clone();
        sorted.sort_by_key(|x| !x.2);
        if let Some(best) = sorted.first() {
            // record only entries with score >= 3
            for d in &sorted {
                if d.2 >= 3 {
                    piece_best_alt.entry(*pid).or_default().push(*d);
                    pos_demand_high.entry(d.0).or_default().push((*pid, d.1, d.2));
                }
            }
            // record current placement's score for this piece.
            // The piece's current pos+rot may not be in our scan (if it's where
            // it currently is). We need the score at the actual placement.
            let _ = best;
        }
    }
    // Compute current placement local score per cell.
    for pos in 0..n_cells {
        if let Some((pid, rot)) = board.get(pos) {
            let e = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
            let s = cell_local_score(&puzzle, &board, pos, e);
            pos_score_for_orig.insert(pos, s);
        }
    }

    // 2-swap search: for every pair (A, B), check if swapping pieces (with best rot
    // at each new pos under current neighbors) gives Δ > 0.
    let (s_baseline, _) = score_board(&puzzle, &board);
    eprintln!("\n=== 2-swap exhaustive over relaxed-improvement region ===");
    // Limit to swaps where at least one of the swap endpoints is a mismatch cell
    // (cells where local score < 4).
    let interesting_cells: Vec<u32> = (0..n_cells).filter(|&pos| {
        let cur_score = pos_score_for_orig.get(&pos).copied().unwrap_or(0);
        let cell_max_score = {
            let w = puzzle.width;
            let h = puzzle.height;
            let x = pos % w;
            let y = pos / w;
            let mut m = 0;
            if y > 0 { m += 1; }
            if x + 1 < w { m += 1; }
            if y + 1 < h { m += 1; }
            if x > 0 { m += 1; }
            m
        };
        cur_score < cell_max_score
    }).collect();
    eprintln!("interesting (sub-optimal) cells: {}", interesting_cells.len());

    let mut swap_hits = 0;
    let mut t0 = std::time::Instant::now();
    let mut tried = 0u64;
    for i in 0..interesting_cells.len() {
        for j in (i+1)..n_cells as usize {
            let a = interesting_cells[i];
            let b = j as u32;
            // skip adjacent for simplicity in this phase, can extend later
            if border_class_of_pos(&puzzle, a) != border_class_of_pos(&puzzle, b) { continue; }
            let (pid_a, _) = board.get(a).unwrap();
            let (pid_b, _) = board.get(b).unwrap();
            if pid_a == pid_b { continue; }
            // place pid_a at b best rot, pid_b at a best rot.
            let mut tent = board.clone();
            let piece_a = puzzle.piece(pid_a).unwrap();
            let piece_b = puzzle.piece(pid_b).unwrap();
            let mut best_a = (0u32, Rotation::R0);
            let mut best_b = (0u32, Rotation::R0);
            let mut ok_a = false; let mut ok_b = false;
            for rot in Rotation::ALL {
                let e = piece_a.edges.rotated(rot).as_array();
                let w = puzzle.width;
                let h = puzzle.height;
                let x = b % w; let y = b / w;
                if (e[0] == BORDER) != (y == 0) { continue; }
                if (e[1] == BORDER) != (x + 1 == w) { continue; }
                if (e[2] == BORDER) != (y + 1 == h) { continue; }
                if (e[3] == BORDER) != (x == 0) { continue; }
                let s = cell_local_score(&puzzle, &board, b, e);
                if !ok_a || s > best_a.0 { best_a = (s, rot); ok_a = true; }
            }
            for rot in Rotation::ALL {
                let e = piece_b.edges.rotated(rot).as_array();
                let w = puzzle.width;
                let h = puzzle.height;
                let x = a % w; let y = a / w;
                if (e[0] == BORDER) != (y == 0) { continue; }
                if (e[1] == BORDER) != (x + 1 == w) { continue; }
                if (e[2] == BORDER) != (y + 1 == h) { continue; }
                if (e[3] == BORDER) != (x == 0) { continue; }
                let s = cell_local_score(&puzzle, &board, a, e);
                if !ok_b || s > best_b.0 { best_b = (s, rot); ok_b = true; }
            }
            if !ok_a || !ok_b { continue; }
            tent.place(b, pid_a, best_a.1);
            tent.place(a, pid_b, best_b.1);
            // need pass 2 to recalc with each other.
            let e_a = puzzle.piece(pid_a).unwrap().edges.rotated(best_a.1).as_array();
            let e_b = puzzle.piece(pid_b).unwrap().edges.rotated(best_b.1).as_array();
            let s_at_b = cell_local_score(&puzzle, &tent, b, e_a);
            let s_at_a = cell_local_score(&puzzle, &tent, a, e_b);
            // Original sum
            let s_orig_a = pos_score_for_orig.get(&a).copied().unwrap_or(0);
            let s_orig_b = pos_score_for_orig.get(&b).copied().unwrap_or(0);
            // delta: new - old, but for adjacent cells the shared edge is double-counted.
            // Use board-level score_board to be safe.
            let (s_new, _) = score_board(&puzzle, &tent);
            tried += 1;
            if s_new > s_baseline {
                swap_hits += 1;
                eprintln!(
                    "  ★ ({},{}) ↔ ({},{}) pids {}↔{} Δ={:+}, locals {}+{} → {}+{}",
                    a/puzzle.width, a%puzzle.width,
                    b/puzzle.width, b%puzzle.width,
                    pid_a, pid_b,
                    s_new as i32 - s_baseline as i32,
                    s_orig_a, s_orig_b, s_at_a, s_at_b,
                );
            }
        }
    }
    let dt = t0.elapsed().as_secs_f64();
    eprintln!("2-swap scan: {} swaps tried in {:.1}s, {} hits", tried, dt, swap_hits);

    // 3-cycle: A->B->C->A among interesting cells.
    // Bound search size: at most 500 cells × 500 × 500 = too much; restrict to top-50 of
    // interesting cells by mismatch.
    eprintln!("\n=== 3-cycle search among interesting cells (heuristic) ===");
    let mut int_sorted: Vec<u32> = interesting_cells.clone();
    // Sort by: cells with their original local score lowest first (most room to improve).
    int_sorted.sort_by_key(|&p| pos_score_for_orig.get(&p).copied().unwrap_or(0));
    let top50: Vec<u32> = int_sorted.into_iter().take(80).collect();
    eprintln!("top-80 cells by current local score (lowest first): {}", top50.len());

    let mut hits3 = 0;
    t0 = std::time::Instant::now();
    let mut tried3 = 0u64;
    for &a in &top50 {
        for &b in &top50 {
            if a == b { continue; }
            for &c in &top50 {
                if c == a || c == b { continue; }
                // border-class must allow rotation: a→b→c→a means piece(a)→b, piece(b)→c, piece(c)→a.
                let cls_a = border_class_of_pos(&puzzle, a);
                let cls_b = border_class_of_pos(&puzzle, b);
                let cls_c = border_class_of_pos(&puzzle, c);
                // Cycle requires pid border class matches position class along arrows.
                let (pa, _) = board.get(a).unwrap();
                let (pb, _) = board.get(b).unwrap();
                let (pc, _) = board.get(c).unwrap();
                if border_class_of_piece(&puzzle, pa) != cls_b { continue; }
                if border_class_of_piece(&puzzle, pb) != cls_c { continue; }
                if border_class_of_piece(&puzzle, pc) != cls_a { continue; }
                // Two-pass best-rot placement.
                let mut tent = board.clone();
                let place = |tent: &mut Board, brd: &Board, dst: u32, pid: u16| -> Option<Rotation> {
                    let piece = puzzle.piece(pid)?;
                    let w = puzzle.width;
                    let h = puzzle.height;
                    let x = dst % w; let y = dst / w;
                    let mut best: Option<(u32, Rotation)> = None;
                    for rot in Rotation::ALL {
                        let e = piece.edges.rotated(rot).as_array();
                        if (e[0] == BORDER) != (y == 0) { continue; }
                        if (e[1] == BORDER) != (x + 1 == w) { continue; }
                        if (e[2] == BORDER) != (y + 1 == h) { continue; }
                        if (e[3] == BORDER) != (x == 0) { continue; }
                        let s = cell_local_score(&puzzle, brd, dst, e);
                        if best.map(|(bb, _)| s > bb).unwrap_or(true) {
                            best = Some((s, rot));
                        }
                    }
                    best.map(|(_, r)| { tent.place(dst, pid, r); r })
                };
                if place(&mut tent, &board, b, pa).is_none() { continue; }
                if place(&mut tent, &board, c, pb).is_none() { continue; }
                if place(&mut tent, &board, a, pc).is_none() { continue; }
                // pass 2 — refine
                let t2 = tent.clone();
                place(&mut tent, &t2, b, pa);
                place(&mut tent, &t2, c, pb);
                place(&mut tent, &t2, a, pc);
                let (s_new, _) = score_board(&puzzle, &tent);
                tried3 += 1;
                if s_new > s_baseline {
                    hits3 += 1;
                    eprintln!(
                        "  ★★ 3-cycle ({},{})→({},{})→({},{}) Δ={:+}",
                        a/puzzle.width, a%puzzle.width,
                        b/puzzle.width, b%puzzle.width,
                        c/puzzle.width, c%puzzle.width,
                        s_new as i32 - s_baseline as i32,
                    );
                }
                let _ = (cls_a,);  // suppress unused warning
            }
        }
    }
    let dt3 = t0.elapsed().as_secs_f64();
    eprintln!("3-cycle scan: {} tried in {:.1}s, {} hits", tried3, dt3, hits3);
}
