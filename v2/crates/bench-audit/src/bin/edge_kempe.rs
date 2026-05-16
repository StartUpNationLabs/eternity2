// Vol-21 — Edge-grid dual / Kempe-chain operator.
//
// NOVEL IDEA: Instead of moving PIECES in cell space, we propose to
// flip EDGE COLORS in the edge dual graph, then repair pieces.
//
// For E2, each cell has 4 edges. The board has 480 internal edges.
// An edge is "mismatched" iff the two adjacent cells disagree on its
// color. Vol-20 proved our 457 has 23 mismatched edges across 38 cells.
//
// Edge-flip operator (atomic):
//   1) Pick a mismatched edge e = (u, v) with side colors (c_u, c_v).
//   2) Choose a target color c* (e.g., c_u, c_v, or any color).
//   3) On both sides of e, ATTEMPT to find pieces such that the
//      shared edge now has color c*, all OTHER edges at both cells
//      remain unchanged, AND no piece is reused.
//
// The interesting question: for each of the 23 mismatched edges of
// our 457 board, is there at least one (c*, piece_u', piece_v')
// triple that fixes that mismatch without breaking another edge?
//
// If YES → we have a +1 move on 457. Score 458.
// If NO  → the mismatch is "rigid" at the edge level; need wider chain.
//
// Then: extend to Kempe-2-chains (find a sequence of edge flips that
// collectively fix more mismatches than they break).
//
// CLI:
//   edge_kempe --board <path> [--width 1]
//
// width=1: single-edge flip test (this binary's PoC scope).

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

/// Returns all mismatched internal edges as `(pos_a, side_a, pos_b, side_b, color_a, color_b)`.
/// side encoding: 0=top, 1=right, 2=bottom, 3=left (matches Rotation indexing).
/// We canonicalize each edge by (min_pos, direction): horizontal edge between pos and pos+1 stored as (pos, 1, pos+1, 3, ...).
fn mismatched_edges(puzzle: &Puzzle, board: &Board) -> Vec<(u32, u8, u32, u8, u8, u8)> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut out: Vec<(u32, u8, u32, u8, u8, u8)> = Vec::new();
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some(e) = cell_edges(puzzle, board, pos) else { continue };
            // East (right edge of pos vs left edge of pos+1)
            if x + 1 < w {
                if let Some(ne) = cell_edges(puzzle, board, pos + 1) {
                    let ca = e[1];
                    let cb = ne[3];
                    if ca != BORDER && cb != BORDER && ca != cb {
                        out.push((pos, 1, pos + 1, 3, ca, cb));
                    }
                }
            }
            // South (bottom edge of pos vs top edge of pos+w)
            if y + 1 < h {
                if let Some(ne) = cell_edges(puzzle, board, pos + w) {
                    let ca = e[2];
                    let cb = ne[0];
                    if ca != BORDER && cb != BORDER && ca != cb {
                        out.push((pos, 2, pos + w, 0, ca, cb));
                    }
                }
            }
        }
    }
    out
}

/// Compute, for the given cell `pos`, all (pid, rot, edges) candidates
/// such that:
///   - the piece's `target_side` color equals `desired_color`
///   - all OTHER sides match neighbors that already exist on the board
///     EXCEPT for `target_side` (which is being redefined).
///
/// We MUST allow the piece on the OTHER side of the flip-edge to also
/// be reassigned, so we pass `relaxed_side` = the side that may differ
/// (caller will check pairing on the other cell separately).
///
/// border_class must match the cell's geometric border class.
///
/// Returns list of (piece_id, rotation, new_4_edges).
fn candidates_for_cell(
    puzzle: &Puzzle,
    board: &Board,
    used_pieces: &HashSet<u16>,
    pos: u32,
    target_side: u8,
    desired_color: u8,
) -> Vec<(u16, Rotation, [u8; 4])> {
    let w = puzzle.width;
    let h = puzzle.height;
    let x = pos % w;
    let y = pos / w;
    // Required neighbor colors for the THREE non-target sides:
    // sides: 0=top, 1=right, 2=bottom, 3=left
    let mut required: [Option<u8>; 4] = [None; 4];
    // Border requirements:
    if y == 0 { required[0] = Some(BORDER); }
    if x + 1 == w { required[1] = Some(BORDER); }
    if y + 1 == h { required[2] = Some(BORDER); }
    if x == 0 { required[3] = Some(BORDER); }
    // Neighbor color requirements:
    if y > 0 && required[0].is_none() {
        if let Some(ne) = cell_edges(puzzle, board, pos - w) {
            required[0] = Some(ne[2]);
        }
    }
    if x + 1 < w && required[1].is_none() {
        if let Some(ne) = cell_edges(puzzle, board, pos + 1) {
            required[1] = Some(ne[3]);
        }
    }
    if y + 1 < h && required[2].is_none() {
        if let Some(ne) = cell_edges(puzzle, board, pos + w) {
            required[2] = Some(ne[0]);
        }
    }
    if x > 0 && required[3].is_none() {
        if let Some(ne) = cell_edges(puzzle, board, pos - 1) {
            required[3] = Some(ne[1]);
        }
    }
    // Now override target_side with desired_color:
    required[target_side as usize] = Some(desired_color);

    let mut out = Vec::new();
    for piece in puzzle.pieces() {
        if used_pieces.contains(&piece.id) { continue; }
        for rot in Rotation::ALL {
            let e = piece.edges.rotated(rot).as_array();
            let mut ok = true;
            for s in 0..4 {
                if let Some(req) = required[s] {
                    if e[s] != req { ok = false; break; }
                }
            }
            if ok {
                out.push((piece.id, rot, e));
            }
        }
    }
    out
}

/// For each mismatched edge, test all (c*, piece_u', piece_v') triples
/// that resolve the mismatch and verify they don't break other edges.
/// Returns successful triples.
fn single_edge_flip_test(
    puzzle: &Puzzle,
    board: &Board,
) -> Vec<(u32, u8, u32, u8, u8, u16, Rotation, u16, Rotation)> {
    let mismatches = mismatched_edges(puzzle, board);
    eprintln!("Mismatched edges: {}", mismatches.len());

    let mut successes = Vec::new();
    for (i, &(pos_a, side_a, pos_b, side_b, ca, cb)) in mismatches.iter().enumerate() {
        // Determine current pieces at pos_a and pos_b (to free them as we test):
        let (orig_pid_a, _) = board.get(pos_a).unwrap();
        let (orig_pid_b, _) = board.get(pos_b).unwrap();

        // Used pieces = all placed pieces except orig_pid_a and orig_pid_b.
        let mut used: HashSet<u16> = HashSet::new();
        for pos in 0..puzzle.cell_count() {
            if pos == pos_a || pos == pos_b { continue; }
            if let Some((pid, _)) = board.get(pos) {
                used.insert(pid);
            }
        }

        // Sweep all possible target colors c* in 1..=color_count-1 (skip BORDER):
        let mut local_hits = 0;
        for c_star in 1..puzzle.color_count as u8 {
            // Candidates at pos_a (its target_side = side_a must equal c_star).
            // pos_b cannot use orig_pid_a, so add it to its used-set:
            let cand_a = candidates_for_cell(puzzle, board, &used, pos_a, side_a, c_star);
            if cand_a.is_empty() { continue; }

            for (pid_a_new, rot_a_new, _edges_a) in &cand_a {
                // pos_b candidates: exclude pid_a_new from available pieces.
                let mut used_b = used.clone();
                used_b.insert(*pid_a_new);
                let cand_b = candidates_for_cell(puzzle, board, &used_b, pos_b, side_b, c_star);
                for (pid_b_new, rot_b_new, _edges_b) in &cand_b {
                    if *pid_b_new == *pid_a_new { continue; } // safety
                    // Now check: are orig_pid_a and orig_pid_b still placeable elsewhere
                    // (or this might be a no-op rearrangement). For the SIMPLEST test:
                    // require that the pair (pid_a_new, pid_b_new) ⊆ {orig_pid_a, orig_pid_b}
                    // (i.e. a 2-piece swap at the flip edge) — OR allow more general
                    // assignments only if the "displaced" pieces can be swapped in.
                    //
                    // Phase 1 (this binary): only the 2-piece restricted case.
                    let pair_new: HashSet<u16> = [*pid_a_new, *pid_b_new].into_iter().collect();
                    let pair_orig: HashSet<u16> = [orig_pid_a, orig_pid_b].into_iter().collect();
                    if pair_new != pair_orig {
                        continue; // outside Phase 1 scope
                    }
                    // Score check: did we improve?
                    let mut test_board = board.clone();
                    test_board.place(pos_a, *pid_a_new, *rot_a_new);
                    test_board.place(pos_b, *pid_b_new, *rot_b_new);
                    let (s_new, _) = score_board(puzzle, &test_board);
                    let (s_old, _) = score_board(puzzle, board);
                    if s_new > s_old {
                        successes.push((
                            pos_a,
                            side_a,
                            pos_b,
                            side_b,
                            c_star,
                            *pid_a_new,
                            *rot_a_new,
                            *pid_b_new,
                            *rot_b_new,
                        ));
                        local_hits += 1;
                        eprintln!(
                            "  ★ FLIP ({},{}) ↔ ({},{}) [{}↔{}]: c*={}, pids {} ↔ {}, Δ={:+}",
                            pos_a / puzzle.width, pos_a % puzzle.width,
                            pos_b / puzzle.width, pos_b % puzzle.width,
                            ca, cb, c_star, pid_a_new, pid_b_new, s_new as i32 - s_old as i32,
                        );
                    }
                }
            }
        }
        if local_hits == 0 && i < 5 {
            eprintln!(
                "  edge {}/{} no Phase-1 fix: ({},{}) [{}↔{}]",
                i, mismatches.len(),
                pos_a / puzzle.width, pos_a % puzzle.width,
                ca, cb,
            );
        }
    }
    successes
}

/// Phase 2: edge-flip with N-piece widening.
/// Pick a mismatched edge (u, v) and a target color c*. Try to find a
/// permutation of pieces in a small region around (u, v) such that the
/// flip is realized. Greedy: BFS over pieces displaced.
///
/// Limit: max region cardinality K (e.g., 3..=6).
fn n_piece_flip_test(
    puzzle: &Puzzle,
    board: &Board,
    max_region: usize,
) -> Vec<(Vec<u32>, i32)> {
    let mismatches = mismatched_edges(puzzle, board);
    let (s_old, _) = score_board(puzzle, board);
    let mut successes: Vec<(Vec<u32>, i32)> = Vec::new();

    // For Phase 2 PoC, we pre-list, for each mismatched edge, all pieces
    // in the puzzle that could fix that edge from BOTH sides (i.e. the
    // piece has at least one rotation+side with color matching the other
    // side's current color). Then we look for a permutation of mismatch
    // cells that uses pieces ALREADY placed elsewhere on the board.

    // Heuristic: for each mismatched-edge endpoint, list candidate pieces
    // (currently placed elsewhere) that could replace it. If a piece P
    // currently at position p_other could go to pos_a, and the piece at
    // pos_a could go to p_other (or elsewhere), we have a 2-cycle.
    // Extend to longer chains.

    // For PoC: just measure how many candidate replacement pieces each
    // mismatch-cell has. This tells us if the edge-dual is more permissive
    // than the cell-dual at this depth.

    let mut all_cells_in_mismatches: HashSet<u32> = HashSet::new();
    for &(a, _, b, _, _, _) in &mismatches {
        all_cells_in_mismatches.insert(a);
        all_cells_in_mismatches.insert(b);
    }

    // For each mismatched-edge cell, count how many pieces (from anywhere
    // on the board) could plausibly replace it AT THAT cell while
    // matching the *current neighbor edges* (allowing the mismatch-edge
    // partner to be replaced too).
    let mut cell_candidate_counts: HashMap<u32, usize> = HashMap::new();
    let used_global: HashSet<u16> = (0..puzzle.cell_count())
        .filter_map(|pos| board.get(pos).map(|(pid, _)| pid))
        .collect();
    for &pos in &all_cells_in_mismatches {
        let (orig_pid, _) = board.get(pos).unwrap();
        let mut used = used_global.clone();
        used.remove(&orig_pid);
        // Candidates ignoring the target side (try all 4 sides as free).
        let w = puzzle.width;
        let h = puzzle.height;
        let x = pos % w;
        let y = pos / w;
        let mut required: [Option<u8>; 4] = [None; 4];
        if y == 0 { required[0] = Some(BORDER); }
        if x + 1 == w { required[1] = Some(BORDER); }
        if y + 1 == h { required[2] = Some(BORDER); }
        if x == 0 { required[3] = Some(BORDER); }
        // Get neighbor colors:
        if y > 0 && required[0].is_none() {
            if let Some(ne) = cell_edges(puzzle, board, pos - w) {
                required[0] = Some(ne[2]);
            }
        }
        if x + 1 < w && required[1].is_none() {
            if let Some(ne) = cell_edges(puzzle, board, pos + 1) {
                required[1] = Some(ne[3]);
            }
        }
        if y + 1 < h && required[2].is_none() {
            if let Some(ne) = cell_edges(puzzle, board, pos + w) {
                required[2] = Some(ne[0]);
            }
        }
        if x > 0 && required[3].is_none() {
            if let Some(ne) = cell_edges(puzzle, board, pos - 1) {
                required[3] = Some(ne[1]);
            }
        }
        // Count: alt pieces with k=4,3,2 matches against required-neighbor colors.
        let mut count4 = 0; let mut count3 = 0; let mut count2 = 0;
        for piece in puzzle.pieces() {
            if piece.id == orig_pid { continue; }
            let mut best_k = 0;
            for rot in Rotation::ALL {
                let e = piece.edges.rotated(rot).as_array();
                let mut k = 0;
                let mut border_ok = true;
                for s in 0..4 {
                    if let Some(req) = required[s] {
                        if req == BORDER {
                            // Border-class constraint: must be BORDER on that side.
                            if e[s] != BORDER { border_ok = false; break; }
                        } else if e[s] == req {
                            k += 1;
                        }
                    }
                }
                // also, if not at border, e[s] should NOT be BORDER on non-required sides
                if border_ok {
                    for s in 0..4 {
                        if required[s].is_none() && e[s] == BORDER { border_ok = false; break; }
                    }
                }
                if border_ok && k > best_k { best_k = k; }
            }
            if best_k == 4 { count4 += 1; }
            else if best_k == 3 { count3 += 1; }
            else if best_k == 2 { count2 += 1; }
        }
        cell_candidate_counts.insert(pos, count4 * 1_000_000 + count3 * 1_000 + count2);
    }
    let total_cells = cell_candidate_counts.len();
    let mut sum4: usize = 0; let mut sum3: usize = 0; let mut sum2: usize = 0;
    for &v in cell_candidate_counts.values() {
        sum4 += v / 1_000_000;
        sum3 += (v / 1_000) % 1_000;
        sum2 += v % 1_000;
    }
    eprintln!(
        "Phase 2 prelim: across {} mismatch cells, ALT-PIECE candidates:",
        total_cells,
    );
    eprintln!("  k=4 matches (perfect alt): total {} (avg {:.1}/cell)", sum4, sum4 as f64/total_cells as f64);
    eprintln!("  k=3 matches (1-conflict alt): total {} (avg {:.1}/cell)", sum3, sum3 as f64/total_cells as f64);
    eprintln!("  k=2 matches (2-conflict alt): total {} (avg {:.1}/cell)", sum2, sum2 as f64/total_cells as f64);
    // Optional: top cells by k=3 count
    let mut samp: Vec<(u32, u32)> = cell_candidate_counts.iter()
        .map(|(&p, &v)| (p, ((v / 1_000) % 1_000) as u32)).collect();
    samp.sort_by_key(|x| !x.1);
    eprintln!("  top cells by k=3 alt count:");
    for (pos, count) in samp.iter().take(10) {
        eprintln!("    ({},{}) → {} alt pieces with k=3", pos / puzzle.width, pos % puzzle.width, count);
    }

    let _ = (max_region, &mut successes, s_old);
    successes
}

/// Phase 3: cycle search over k=3 alt-piece graph.
///
/// Build directed graph:
///   For each mismatch cell `pos` and each k=3-alt piece P
///   currently at home_pos, add arrow (home_pos -> pos, gain).
/// Then find a CYCLE where total gain > 0.
///
/// Gain at `pos` = new_local_score - old_local_score, where new_local
/// considers the cell's neighbors as currently placed (but we'll allow
/// some neighbors to also be replaced if they're in the cycle).
fn phase3_cycle_search(puzzle: &Puzzle, board: &Board) {
    let mismatches = mismatched_edges(puzzle, board);
    let mut mismatch_cells: HashSet<u32> = HashSet::new();
    for &(a, _, b, _, _, _) in &mismatches {
        mismatch_cells.insert(a);
        mismatch_cells.insert(b);
    }

    // Build the piece-id -> home_pos map.
    let mut piece_home: HashMap<u16, u32> = HashMap::new();
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, _)) = board.get(pos) {
            piece_home.insert(pid, pos);
        }
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

    // For each (mismatch_cell, alt_piece, rotation) with k=3, record:
    //   (home_pos, target_pos, gain_at_target = 3 - old_local_score(target))
    //   alt_piece's rotation, edges array.
    //
    // gain_at_target is the gain at the target cell ONLY (does not yet
    // account for the loss at home_pos when home_pos's piece is removed).

    // Cell-by-cell: enumerate all alt-pieces at k=3.
    let mut arrows: Vec<(u32 /*home*/, u32 /*target*/, i32 /*gain_at_target*/, u16 /*pid*/, Rotation, [u8;4])> = Vec::new();

    for &pos in &mismatch_cells {
        let (orig_pid, orig_rot) = board.get(pos).unwrap();
        let orig_edges = puzzle.piece(orig_pid).unwrap().edges.rotated(orig_rot).as_array();
        let old_local = cell_local_score(puzzle, board, pos, orig_edges);

        let w = puzzle.width;
        let h = puzzle.height;
        let x = pos % w;
        let y = pos / w;
        let mut required: [Option<u8>; 4] = [None; 4];
        if y == 0 { required[0] = Some(BORDER); }
        if x + 1 == w { required[1] = Some(BORDER); }
        if y + 1 == h { required[2] = Some(BORDER); }
        if x == 0 { required[3] = Some(BORDER); }
        if y > 0 && required[0].is_none() {
            if let Some(ne) = cell_edges(puzzle, board, pos - w) { required[0] = Some(ne[2]); }
        }
        if x + 1 < w && required[1].is_none() {
            if let Some(ne) = cell_edges(puzzle, board, pos + 1) { required[1] = Some(ne[3]); }
        }
        if y + 1 < h && required[2].is_none() {
            if let Some(ne) = cell_edges(puzzle, board, pos + w) { required[2] = Some(ne[0]); }
        }
        if x > 0 && required[3].is_none() {
            if let Some(ne) = cell_edges(puzzle, board, pos - 1) { required[3] = Some(ne[1]); }
        }

        for piece in puzzle.pieces() {
            if piece.id == orig_pid { continue; }
            for rot in Rotation::ALL {
                let e = piece.edges.rotated(rot).as_array();
                // border-class constraint
                let mut border_ok = true;
                for s in 0..4 {
                    if let Some(req) = required[s] {
                        if req == BORDER && e[s] != BORDER { border_ok = false; break; }
                    }
                    if required[s].is_none() && e[s] == BORDER { border_ok = false; break; }
                }
                if !border_ok { continue; }
                let mut k = 0;
                for s in 0..4 {
                    if let Some(req) = required[s] {
                        if req != BORDER && e[s] == req { k += 1; }
                    }
                }
                if k == 3 {
                    if let Some(&home_pos) = piece_home.get(&piece.id) {
                        let gain_at_target = 3 - old_local as i32;
                        arrows.push((home_pos, pos, gain_at_target, piece.id, rot, e));
                    }
                }
            }
        }
    }
    eprintln!("Phase 3: {} k=3 arrows in mismatch graph", arrows.len());

    // Filter: only arrows where home_pos is itself in mismatch_cells (otherwise
    // moving away from home_pos may break a fully-matched cell, making the
    // cycle unprofitable). For Phase 3a focus on pure-mismatch cycles.
    let arrows_in: Vec<_> = arrows.iter()
        .filter(|(h, _, _, _, _, _)| mismatch_cells.contains(h))
        .collect();
    eprintln!("  ↳ {} arrows where home_pos is also a mismatch cell", arrows_in.len());

    // For each arrow whose home is also a mismatch cell, compute the loss at home_pos
    // when its piece is removed and replaced by some other piece (we don't know which yet —
    // upper bound is "lose all current local matches at home_pos").
    if arrows_in.is_empty() { return; }

    // Group arrows by target cell.
    let mut by_target: HashMap<u32, Vec<&(u32, u32, i32, u16, Rotation, [u8;4])>> = HashMap::new();
    for arr in &arrows_in {
        by_target.entry(arr.1).or_default().push(*arr);
    }

    // Build a directed graph: edge home_pos -> target_pos.
    // Look for 2-cycles, 3-cycles, ... where every cell in cycle is mismatch.
    // For 2-cycles: cells (A, B) where there's an arrow B->A and A->B.

    // 2-cycle search.
    let mut found_2: Vec<(u32, u32, i32)> = Vec::new();
    for &&(h_a, t_a, g_a, pid_a, rot_a, ea) in &arrows_in {
        for &&(h_b, t_b, g_b, pid_b, rot_b, eb) in &arrows_in {
            if pid_a == pid_b { continue; }
            // 2-cycle: A: home=h_a, target=t_a; B: home=h_b=t_a, target=t_b=h_a.
            if h_b == t_a && t_b == h_a {
                // Compute net Δ.
                // Get the original local score at h_a (which equals t_b) and at h_b (which equals t_a).
                let (orig_pid_a, orig_rot_a) = board.get(h_a).unwrap();
                let orig_edges_a = puzzle.piece(orig_pid_a).unwrap().edges.rotated(orig_rot_a).as_array();
                let s_old_a = cell_local_score(puzzle, board, h_a, orig_edges_a);
                let (orig_pid_b, orig_rot_b) = board.get(h_b).unwrap();
                let orig_edges_b = puzzle.piece(orig_pid_b).unwrap().edges.rotated(orig_rot_b).as_array();
                let s_old_b = cell_local_score(puzzle, board, h_b, orig_edges_b);

                // Construct tentative board: place pid_a at t_a (=h_b), pid_b at t_b (=h_a).
                let mut tent = board.clone();
                tent.place(t_a, pid_a, rot_a);
                tent.place(t_b, pid_b, rot_b);
                // Re-score the two cells using cell_local_score against TENTATIVE (so they see each other).
                let s_new_a_at_target = cell_local_score(puzzle, &tent, t_a, ea); // pid_a is at t_a
                let s_new_b_at_target = cell_local_score(puzzle, &tent, t_b, eb);
                let delta_per_pair = (s_new_a_at_target as i32 + s_new_b_at_target as i32)
                    - (s_old_a as i32 + s_old_b as i32);
                // shared-edge double-count check: t_a and t_b are 2-cycle. The shared edge between them
                // is counted once for s_new_a and once for s_new_b. So total adjacencies counted twice
                // for adjacent cells.
                let dx = (t_a as i32 % puzzle.width as i32) - (t_b as i32 % puzzle.width as i32);
                let dy = (t_a as i32 / puzzle.width as i32) - (t_b as i32 / puzzle.width as i32);
                let are_adjacent = dx.abs() + dy.abs() == 1;
                let net = if are_adjacent {
                    // shared edge double counted in both. Subtract once.
                    // figure out the shared edge value (match or not).
                    // simpler: also compute s_old similarly with double-counting and subtract.
                    let s_old_b_with_a = cell_local_score(puzzle, board, h_a, orig_edges_a);
                    let _ = s_old_b_with_a;
                    delta_per_pair // approximation — will recompute below if interesting
                } else {
                    delta_per_pair
                };
                if net > 0 || (net == 0 && (g_a + g_b) > 0) {
                    found_2.push((h_a, h_b, net));
                    eprintln!(
                        "  ★ 2-cycle: ({},{}) ↔ ({},{}) pids ({}, {}) → Δ_approx={:+} (g_a={}, g_b={})",
                        h_a/puzzle.width, h_a%puzzle.width,
                        h_b/puzzle.width, h_b%puzzle.width,
                        pid_a, pid_b, net, g_a, g_b,
                    );
                }
            }
        }
    }
    eprintln!("  Phase 3a: 2-cycles with Δ>0: {}", found_2.len());

    // 3-cycle search: A->B->C->A with all targets in mismatch and corresponding home matches.
    let mut found_3 = 0;
    for &&(h_a, t_a, _, pid_a, rot_a, ea) in &arrows_in {
        // B = arrows where home = t_a
        for &&(h_b, t_b, _, pid_b, rot_b, eb) in &arrows_in {
            if h_b != t_a || pid_b == pid_a { continue; }
            // C = arrows where home = t_b, target = h_a
            for &&(h_c, t_c, _, pid_c, rot_c, ec) in &arrows_in {
                if h_c != t_b || t_c != h_a || pid_c == pid_a || pid_c == pid_b { continue; }
                // We have 3-cycle. Compute Δ.
                let mut tent = board.clone();
                tent.place(t_a, pid_a, rot_a);
                tent.place(t_b, pid_b, rot_b);
                tent.place(t_c, pid_c, rot_c);
                let (s_new, _) = score_board(puzzle, &tent);
                let (s_old, _) = score_board(puzzle, board);
                let net = s_new as i32 - s_old as i32;
                if net >= 0 {
                    found_3 += 1;
                    eprintln!(
                        "  ★ 3-cycle: ({},{})→({},{})→({},{})→ pids ({},{},{}) Δ={:+}",
                        h_a/puzzle.width, h_a%puzzle.width,
                        h_b/puzzle.width, h_b%puzzle.width,
                        h_c/puzzle.width, h_c%puzzle.width,
                        pid_a, pid_b, pid_c, net,
                    );
                }
                let _ = (ea, eb, ec);
            }
        }
    }
    eprintln!("  Phase 3b: 3-cycles with Δ≥0: {}", found_3);
}

fn main() {
    let mut board_path = PathBuf::new();
    let mut max_region: usize = 3;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--max-region" => max_region = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("usage: edge_kempe --board <path> [--max-region 3]");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let board = load_board(&board_path, &puzzle);
    let (score, total) = score_board(&puzzle, &board);
    eprintln!("loaded board: {}/{}", score, total);

    eprintln!("\n=== Phase 1: single-edge flip with 2-piece swap ===");
    let phase1 = single_edge_flip_test(&puzzle, &board);
    eprintln!("Phase 1 successes: {}", phase1.len());

    eprintln!("\n=== Phase 2: candidate counts for mismatch cells ===");
    let phase2 = n_piece_flip_test(&puzzle, &board, max_region);
    eprintln!("Phase 2 successes (full chain): {}", phase2.len());

    eprintln!("\n=== Phase 3: k=3 alt-piece cycle search ===");
    phase3_cycle_search(&puzzle, &board);
}
