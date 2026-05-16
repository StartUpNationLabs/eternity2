// Vol-21 — TARGET-EDGE bipartite matching.
//
// Given a starting board (e.g., our 457), compute the "ideal" 4-tuple
// edge target at each cell using the RELAXED iterative best-piece
// procedure. The result is a 461-equivalent placement with 4 duplicate
// pieces.
//
// Then: solve a bipartite assignment problem:
//   - Left: 256 piece IDs
//   - Right: 256 cell positions
//   - Weight: best k-match score for (piece, position) given the
//     ideal-edge environment at position.
//
// Use Hungarian algorithm to maximize total k. Piece-uniqueness is
// then automatic.
//
// HYPOTHESIS: max-weight bipartite matching with EDGE-TARGETS as
// guidance reaches > 457.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::path::PathBuf;

use eternity2_bench_audit::score_board_dense as score_board;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle, Rotation, BORDER};

// Vol-118 T9: thin wrapper around canonical load_board for backward-compat.
fn load_board(path: &std::path::Path, puzzle: &Puzzle) -> Board {
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

/// Hungarian algorithm for SQUARE bipartite matching (n x n).
/// `cost[i*n + j]` = cost of assigning left i to right j.
/// Minimizes total cost; for maximization, negate costs.
/// Returns the assignment vector: `out[i] = j` (right index for left i).
fn hungarian(cost: &[i64], n: usize) -> Vec<usize> {
    // Following standard O(n^3) implementation.
    let inf = i64::MAX / 4;
    let mut u = vec![0i64; n + 1];
    let mut v = vec![0i64; n + 1];
    let mut p = vec![0usize; n + 1];
    let mut way = vec![0usize; n + 1];
    for i in 1..=n {
        p[0] = i;
        let mut j0 = 0usize;
        let mut minv = vec![inf; n + 1];
        let mut used = vec![false; n + 1];
        loop {
            used[j0] = true;
            let i0 = p[j0];
            let mut delta = inf;
            let mut j1 = 0usize;
            for j in 1..=n {
                if !used[j] {
                    let cur = cost[(i0 - 1) * n + (j - 1)] - u[i0] - v[j];
                    if cur < minv[j] {
                        minv[j] = cur;
                        way[j] = j0;
                    }
                    if minv[j] < delta {
                        delta = minv[j];
                        j1 = j;
                    }
                }
            }
            for j in 0..=n {
                if used[j] {
                    u[p[j]] += delta;
                    v[j] -= delta;
                } else {
                    minv[j] -= delta;
                }
            }
            j0 = j1;
            if p[j0] == 0 { break; }
        }
        loop {
            let j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
            if j0 == 0 { break; }
        }
    }
    let mut ans = vec![0usize; n];
    for j in 1..=n {
        if p[j] != 0 { ans[p[j] - 1] = j - 1; }
    }
    ans
}

/// Phase 1: compute the "ideal-edge board" by relaxed iteration.
fn relaxed_edge_target(puzzle: &Puzzle, board: &Board) -> Board {
    let mut b = board.clone();
    let n_cells = puzzle.cell_count();
    let max_iters = 20;
    for _ in 0..max_iters {
        let mut changes = 0u32;
        for pos in 0..n_cells {
            let cur_local = b.get(pos).map(|(pid, rot)| {
                let e = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
                cell_local_score(puzzle, &b, pos, e)
            }).unwrap_or(0);
            // best piece+rot (no uniqueness):
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
    b
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
        eprintln!("usage: edge_target_match --board <path>");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let board = load_board(&board_path, &puzzle);
    let (s_old, total) = score_board(&puzzle, &board);
    eprintln!("baseline: {}/{}", s_old, total);

    // Vol-116 T1 — collect canonical hints from puzzle. The Hungarian
    // matching below will EXCLUDE hint positions and hint pieces from
    // their respective per-class pools so hints stay pinned through
    // the matching step. This preserves canonical hint compliance
    // end-to-end through the bound-ascent + Hungarian + ALNS pipeline.
    let hint_positions: std::collections::HashSet<u32> =
        hints.hints.iter().map(|h| h.position).collect();
    let hint_pieces: std::collections::HashSet<u16> =
        hints.hints.iter().map(|h| h.piece_id).collect();
    eprintln!("canonical hints: {} (pinned through Hungarian)", hints.hints.len());

    // Compute the relaxed 461-equivalent target.
    let mut target = relaxed_edge_target(&puzzle, &board);
    let (s_target, _) = score_board(&puzzle, &target);
    eprintln!("relaxed target: {}/{}", s_target, total);
    let n_cells = puzzle.cell_count() as usize;
    let mut iter = 0u32;
    let mut prev_score = 0u32;
    let mut best_seen = s_old;

    // Build cost matrix: cost[pid * n + pos] = -best_k for piece pid at pos, given target neighbors.
    // First we need to compute the target's edge-environment at each cell:
    // Specifically, the colors that each cell's 4 neighbors HAVE in the target.
    // For each cell pos, compute the "ideal neighbors" colors (in target).

    // The matching is over BORDER CLASS partitions:
    // - corner pieces (cls=2) must go to corner positions (cls=2): 4 of each
    // - edge pieces (cls=1) → edge positions: 56 of each
    // - inner pieces (cls=0) → inner positions: 196 of each

    let mut positions_by_cls: HashMap<u8, Vec<u32>> = HashMap::new();
    let mut pieces_by_cls: HashMap<u8, Vec<u16>> = HashMap::new();
    for pos in 0..puzzle.cell_count() {
        // Vol-116 T1: exclude hint positions from the matching pool.
        if hint_positions.contains(&pos) { continue; }
        positions_by_cls.entry(border_class_of_pos(&puzzle, pos)).or_default().push(pos);
    }
    for piece in puzzle.pieces() {
        // Vol-116 T1: exclude hint pieces from the matching pool.
        if hint_pieces.contains(&piece.id) { continue; }
        pieces_by_cls.entry(border_class_of_piece(&puzzle, piece.id)).or_default().push(piece.id);
    }
    for (k, v) in &positions_by_cls {
        eprintln!("border_class={}: {} positions, {} pieces", k, v.len(), pieces_by_cls.get(k).map(|x| x.len()).unwrap_or(0));
    }

    // Iterative refinement: target -> match -> new target -> match ...
    let mut new_board = Board::empty(&puzzle);
    loop {
    iter += 1;
    // Vol-116 T1: pre-place canonical hints on new_board at every iteration.
    // The Hungarian step writes other cells in-place below; we re-clear
    // and re-place hints first to avoid stale data.
    new_board = Board::empty(&puzzle);
    for h in &hints.hints {
        new_board.place(h.position, h.piece_id, h.rotation);
    }
    let mut total_k = 0i64;
    for cls in [0u8, 1, 2] {
        let pieces_vec = pieces_by_cls.get(&cls).cloned().unwrap_or_default();
        let positions_vec = positions_by_cls.get(&cls).cloned().unwrap_or_default();
        let n = pieces_vec.len();
        if n != positions_vec.len() {
            eprintln!("cls {}: mismatch {} pieces vs {} positions; skipping", cls, n, positions_vec.len());
            continue;
        }
        if n == 0 { continue; }
        eprintln!("\nbuilding {}x{} cost matrix for cls {}...", n, n, cls);
        // For each (piece, position): best k_matches across all 4 rotations.
        let mut cost = vec![0i64; n * n];
        let mut best_rots = vec![Rotation::R0; n * n];
        for (pi, &pid) in pieces_vec.iter().enumerate() {
            let piece = puzzle.piece(pid).unwrap();
            for (pj, &pos) in positions_vec.iter().enumerate() {
                let w = puzzle.width;
                let h = puzzle.height;
                let x = pos % w;
                let y = pos / w;
                let mut best_k = 0u32;
                let mut best_rot = Rotation::R0;
                for rot in Rotation::ALL {
                    let e = piece.edges.rotated(rot).as_array();
                    if (e[0] == BORDER) != (y == 0) { continue; }
                    if (e[1] == BORDER) != (x + 1 == w) { continue; }
                    if (e[2] == BORDER) != (y + 1 == h) { continue; }
                    if (e[3] == BORDER) != (x == 0) { continue; }
                    let k = cell_local_score(&puzzle, &target, pos, e);
                    if k > best_k { best_k = k; best_rot = rot; }
                }
                cost[pi * n + pj] = -(best_k as i64);
                best_rots[pi * n + pj] = best_rot;
            }
        }
        eprintln!("  solving Hungarian...");
        let t0 = std::time::Instant::now();
        let assignment = hungarian(&cost, n);
        let dt = t0.elapsed().as_secs_f64();
        let class_k: i64 = (0..n).map(|i| -cost[i * n + assignment[i]]).sum();
        eprintln!("  solved in {:.1}s, class total k = {}", dt, class_k);
        total_k += class_k;
        for (pi, &pj) in assignment.iter().enumerate() {
            let pid = pieces_vec[pi];
            let pos = positions_vec[pj];
            let rot = best_rots[pi * n + pj];
            new_board.place(pos, pid, rot);
        }
    }
    let (s_new, _) = score_board(&puzzle, &new_board);
    eprintln!("\n=== iter {}: Hungarian-matched board score: {}/{}", iter, s_new, total);
    eprintln!("Δ vs baseline {}: {:+}", s_old, s_new as i32 - s_old as i32);
    if s_new > best_seen { best_seen = s_new; }
    if s_new == prev_score || iter >= 10 {
        eprintln!("converged (or iter cap); best seen this run: {}", best_seen);
        break;
    }
    prev_score = s_new;
    // Re-compute target from new_board.
    target = relaxed_edge_target(&puzzle, &new_board);
    let (st2, _) = score_board(&puzzle, &target);
    eprintln!("  new relaxed target: {}/{}", st2, total);
    }

    let (s_new, _) = score_board(&puzzle, &new_board);
    eprintln!("\nFinal: {}/{} (best across iters: {})", s_new, total, best_seen);

    // Save it.
    if s_new > 0 {
        let out_path = format!("output/v21_target_match_{}.json", s_new);
        let json = serde_json::json!({
            "matched_best": s_new,
            "placement": (0..puzzle.cell_count()).map(|p| {
                new_board.get(p).map(|(pid, rot)| serde_json::json!({
                    "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
        });
        std::fs::write(&out_path, serde_json::to_string_pretty(&json).unwrap()).expect("write");
        eprintln!("Saved to {}", out_path);
    }
}
