// Vol-21 — Bound-ascent search.
//
// NOVEL: optimize the RELAXED BOUND, not the score. The relaxed bound is
// the max-score that current cell-by-cell greedy can reach IF piece-
// uniqueness were relaxed. This is an upper bound on the achievable
// score in the current basin.
//
// Hypothesis: the bound-landscape is smoother than the score-landscape
// (since the bound interpolates an integer-programming relaxation).
// Climbing the bound might reach basins with bound = 480 (= solution).
//
// Algorithm:
//   1. Start with some board (canonical 457 or hint-only).
//   2. Compute relaxed-bound by iterating greedy fill.
//   3. Propose mutations: single-cell perturbations (random piece-swap)
//      or k-cell ALNS-style destroys.
//   4. After mutation + re-relaxed-iterate, accept if the new bound > old.
//   5. Acceptance: greedy or SA.
//
// Importantly: we DO NOT require the actual score to improve at each
// step. We're hill-climbing the BOUND, which can decrease the actual
// score temporarily as the basin shifts.

#![forbid(unsafe_code)]

use std::collections::{BTreeSet, HashMap};
use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::score_board_dense as score_board;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle, Rotation, BORDER};

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

/// Run relaxed-iterate to a fixed point. Returns the relaxed-bound score.
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

/// Single 2-piece swap mutation respecting border-class.
/// Returns (new_board, swap_descriptor).
fn random_swap(puzzle: &Puzzle, board: &Board, state: &mut u64, pinned: &BTreeSet<u32>) -> Option<(Board, (u32, u32))> {
    // Pick two random non-pinned positions of the same border-class.
    let mut by_class: HashMap<u8, Vec<u32>> = HashMap::new();
    for pos in 0..puzzle.cell_count() {
        if pinned.contains(&pos) { continue; }
        by_class.entry(border_class_of_pos(puzzle, pos)).or_default().push(pos);
    }
    let classes: Vec<u8> = by_class.keys().copied().collect();
    if classes.is_empty() { return None; }
    *state = state.wrapping_mul(0x9E3779B97F4A7C15) | 1;
    let cls = classes[(*state >> 32) as usize % classes.len()];
    let cells = by_class.get(&cls).unwrap();
    if cells.len() < 2 { return None; }
    *state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
    let i = (*state >> 32) as usize % cells.len();
    *state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
    let mut j = (*state >> 32) as usize % cells.len();
    if j == i { j = (j + 1) % cells.len(); }
    let pos_a = cells[i];
    let pos_b = cells[j];
    let (pid_a, rot_a) = board.get(pos_a)?;
    let (pid_b, rot_b) = board.get(pos_b)?;
    if pid_a == pid_b { return None; }
    let mut new_b = board.clone();
    new_b.place(pos_a, pid_b, rot_b);
    new_b.place(pos_b, pid_a, rot_a);
    Some((new_b, (pos_a, pos_b)))
}

fn main() {
    let mut board_path: Option<PathBuf> = None;
    let mut n_iters: u64 = 500;
    let mut seed: u64 = 1;
    let mut acceptance: String = "sa".to_string();
    let mut t_init: f64 = 1.5;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = Some(PathBuf::from(args.next().unwrap())),
            "--iters" => n_iters = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--acceptance" => acceptance = args.next().unwrap(),
            "--t-init" => t_init = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let total = 480u32;
    let pinned: BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();

    let board = if let Some(p) = board_path {
        load_board(&p, &puzzle)
    } else {
        // start from hint-only + arbitrary fill
        let mut b = Board::empty(&puzzle);
        for h in &hints.hints { b.place(h.position, h.piece_id, h.rotation); }
        // Fill with any valid piece
        let w = puzzle.width;
        let h = puzzle.height;
        let mut state = seed;
        let mut available: Vec<u16> = puzzle.pieces().iter().map(|p| p.id).collect();
        // Remove hints from available
        for hint in &hints.hints {
            available.retain(|&p| p != hint.piece_id);
        }
        for pos in 0..puzzle.cell_count() {
            if b.get(pos).is_some() { continue; }
            let cls = border_class_of_pos(&puzzle, pos);
            let mut chosen_idx: Option<usize> = None;
            for (idx, &pid) in available.iter().enumerate() {
                if border_class_of_piece(&puzzle, pid) != cls { continue; }
                let piece = puzzle.piece(pid).unwrap();
                let x = pos % w; let y = pos / w;
                let mut placed = false;
                for rot in Rotation::ALL {
                    let e = piece.edges.rotated(rot).as_array();
                    if (e[0] == BORDER) != (y == 0) { continue; }
                    if (e[1] == BORDER) != (x + 1 == w) { continue; }
                    if (e[2] == BORDER) != (y + 1 == h) { continue; }
                    if (e[3] == BORDER) != (x == 0) { continue; }
                    b.place(pos, pid, rot);
                    chosen_idx = Some(idx);
                    placed = true;
                    break;
                }
                if placed { break; }
            }
            if let Some(idx) = chosen_idx { available.swap_remove(idx); }
            // suppress unused warning
            let _ = state;
        }
        b
    };

    let (s0, _) = score_board(&puzzle, &board);
    let b0 = relaxed_bound(&puzzle, &board);
    eprintln!("initial: score={}/{}, bound={}, gap={:+}", s0, total, b0, b0 as i32 - s0 as i32);

    let mut current = board.clone();
    let mut current_bound = b0;
    let mut best = current.clone();
    let mut best_bound = b0;
    let mut best_score = s0;
    let mut state = seed;
    let mut accepts = 0u64;
    let mut t = t_init;
    let cooling = 0.9999;
    let t0 = Instant::now();

    for iter in 0..n_iters {
        let Some((cand_board, _swap)) = random_swap(&puzzle, &current, &mut state, &pinned) else { continue };
        let new_bound = relaxed_bound(&puzzle, &cand_board);
        let delta = new_bound as i32 - current_bound as i32;
        let accept = if acceptance == "greedy" {
            delta >= 0
        } else {
            // SA
            state = state.wrapping_mul(0x9E3779B97F4A7C15) | 1;
            let r = (state >> 32) as f64 / (u32::MAX as f64);
            delta >= 0 || r < (-(delta as f64).min(20.0) / t).exp()
        };
        if accept {
            current = cand_board;
            current_bound = new_bound;
            accepts += 1;
            let (s, _) = score_board(&puzzle, &current);
            if new_bound > best_bound || (new_bound == best_bound && s > best_score) {
                best_bound = new_bound;
                best = current.clone();
                best_score = s;
                eprintln!(
                    "iter {} t={:.3}: score={}/{} bound={} (gap={:+}) ** NEW BEST **",
                    iter, t, s, total, new_bound, new_bound as i32 - s as i32
                );
            } else if iter % 50 == 0 {
                eprintln!(
                    "iter {} t={:.3}: score={}/{} bound={} (gap={:+}) accept={}",
                    iter, t, s, total, new_bound, new_bound as i32 - s as i32, accepts,
                );
            }
        }
        t *= cooling;
    }
    let dt = t0.elapsed().as_secs_f64();
    let (s_final, _) = score_board(&puzzle, &best);
    eprintln!("\n=== Final ===");
    eprintln!("best score: {}/{}, best bound: {}, gap: {:+}", s_final, total, best_bound, best_bound as i32 - s_final as i32);
    eprintln!("{} iters, {} accepts in {:.1}s", n_iters, accepts, dt);

    let out = format!("output/v21_bound_ascent_b{}_s{}.json", best_bound, s_final);
    let json = serde_json::json!({
        "matched_best": s_final,
        "relaxed_bound": best_bound,
        "placement": (0..puzzle.cell_count()).map(|p| {
            best.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    std::fs::write(&out, serde_json::to_string_pretty(&json).unwrap()).expect("write");
    eprintln!("Saved {}", out);
}
