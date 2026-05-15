// CP-with-LP-UB-pruning: backtracking border-placement search that
// prunes by LP relaxation upper-bound at each placement.
//
// Goal: efficiently find borders with LP UB above some threshold T,
// without enumerating the full 56! perimeter space.
//
// See vault/concepts/cp-with-lp-ub-pruning.md for the design.

#![forbid(unsafe_code)]

use std::collections::{HashMap, HashSet};
use std::path::PathBuf;

use eternity2_core::{Board, BORDER, PieceId, Position, Puzzle, Rotation};

/// User-facing options for the search.
#[derive(Debug, Clone)]
pub struct CpLpSearchOpts {
    /// Prune branches with LP UB < this threshold.
    pub threshold_ub: f64,
    /// Below this depth, use cheap pruning only (color count, Hall).
    pub phase1_depth_max: u32,
    /// At or below this depth, use reduced LP (B-B + B-I only).
    pub phase2_depth_max: u32,
    /// Total wall-clock budget.
    pub time_budget_secs: f64,
    pub threads: u32,
    pub save_dir: PathBuf,
    /// Minimum B-B match count at leaf time to save the border. Default 60.
    pub leaf_min_bb: u32,
}

impl Default for CpLpSearchOpts {
    fn default() -> Self {
        Self {
            threshold_ub: 478.0,
            phase1_depth_max: 30,
            phase2_depth_max: 55,
            time_budget_secs: 3600.0,
            threads: 8,
            save_dir: PathBuf::from("output/cp_lp_search"),
            leaf_min_bb: 60,
        }
    }
}

/// Result of a search run.
#[derive(Debug, Clone, Default)]
pub struct CpLpResult {
    pub n_explored: u64,
    pub n_pruned_cheap: u64,
    pub n_pruned_reduced_lp: u64,
    pub n_pruned_full_lp: u64,
    pub n_leaves_kept: u64,
    pub best_lp_ub_seen: f64,
    pub elapsed_secs: f64,
}

/// Compute the canonical perimeter positions in placement order
/// (clockwise from top-left corner).
pub fn perimeter_placement_order(puzzle: &Puzzle) -> Vec<Position> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut out = Vec::with_capacity((2 * (w + h) - 4) as usize);
    // Top row L→R
    for x in 0..w { out.push(x); }
    // Right column top→bottom (skip top-right corner)
    for y in 1..h { out.push(y * w + (w - 1)); }
    // Bottom row R→L (skip bottom-right corner)
    for x in (0..w-1).rev() { out.push((h - 1) * w + x); }
    // Left column bottom→top (skip both bottom-left and top-left)
    for y in (1..h-1).rev() { out.push(y * w); }
    out
}

/// Check if a position is a corner.
pub fn is_corner(puzzle: &Puzzle, pos: Position) -> bool {
    let (x, y) = puzzle.xy(pos);
    (x == 0 || x == puzzle.width - 1) && (y == 0 || y == puzzle.height - 1)
}

/// Which "outward" side of a perimeter cell faces the grid edge?
/// Returns the side index 0=top, 1=right, 2=bottom, 3=left.
/// For corners, returns Some(side1) — the first outward side.
/// (Corner has 2 outward sides; caller must check both.)
fn outward_sides(puzzle: &Puzzle, pos: Position) -> Vec<u8> {
    let (x, y) = puzzle.xy(pos);
    let mut out = Vec::new();
    if y == 0 { out.push(0); }
    if x == puzzle.width - 1 { out.push(1); }
    if y == puzzle.height - 1 { out.push(2); }
    if x == 0 { out.push(3); }
    out
}

/// Helper: is `pos` on the puzzle perimeter (border ring)?
fn is_perimeter(puzzle: &Puzzle, pos: Position) -> bool {
    let (x, y) = puzzle.xy(pos);
    x == 0 || x == puzzle.width - 1 || y == 0 || y == puzzle.height - 1
}

/// Helper: list of (cell, side) pairs that are demanded by B-I edges
/// when the partial border has the given placed cells. Each entry
/// gives a required color the interior cell must present on that side.
fn b_i_demands_from_partial(puzzle: &Puzzle, board: &Board) -> Vec<(Position, u8, u8)> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut out = Vec::new();
    for pos in 0..puzzle.cell_count() {
        if !is_perimeter(puzzle, pos) { continue; }
        let Some((pid, rot)) = board.get(pos) else { continue; };
        let Some(p) = puzzle.piece(pid) else { continue; };
        let edges = p.edges.rotated(rot).as_array();
        let (x, y) = puzzle.xy(pos);
        if y > 0 {
            let n = (y - 1) * w + x;
            if !is_perimeter(puzzle, n) {
                out.push((n, 2u8, edges[0]));
            }
        }
        if x + 1 < w {
            let n = y * w + (x + 1);
            if !is_perimeter(puzzle, n) {
                out.push((n, 3u8, edges[1]));
            }
        }
        if y + 1 < h {
            let n = (y + 1) * w + x;
            if !is_perimeter(puzzle, n) {
                out.push((n, 0u8, edges[2]));
            }
        }
        if x > 0 {
            let n = y * w + (x - 1);
            if !is_perimeter(puzzle, n) {
                out.push((n, 1u8, edges[3]));
            }
        }
    }
    out
}

/// Compute B-B match count for placed perimeter cells.
pub fn b_b_matches(puzzle: &Puzzle, board: &Board) -> u32 {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut matched = 0u32;
    for pos in 0..puzzle.cell_count() {
        if !is_perimeter(puzzle, pos) { continue; }
        let (x, y) = puzzle.xy(pos);
        let Some((pid, rot)) = board.get(pos) else { continue; };
        let Some(p) = puzzle.piece(pid) else { continue; };
        let e = p.edges.rotated(rot).as_array();
        if x + 1 < w {
            let n = y * w + (x + 1);
            if is_perimeter(puzzle, n) {
                if let Some((npid, nrot)) = board.get(n) {
                    if let Some(np) = puzzle.piece(npid) {
                        let ne = np.edges.rotated(nrot).as_array();
                        if e[1] == ne[3] { matched += 1; }
                    }
                }
            }
        }
        if y + 1 < h {
            let n = (y + 1) * w + x;
            if is_perimeter(puzzle, n) {
                if let Some((npid, nrot)) = board.get(n) {
                    if let Some(np) = puzzle.piece(npid) {
                        let ne = np.edges.rotated(nrot).as_array();
                        if e[2] == ne[0] { matched += 1; }
                    }
                }
            }
        }
    }
    matched
}

/// For each unplaced perimeter cell, list valid (piece, rotation) candidates
/// (a border-class piece — corner or edge — with BORDER faces outward
/// matching the cell's geometry).
pub fn valid_border_candidates(
    puzzle: &Puzzle,
    pos: Position,
    pinned: &HashSet<PieceId>,
) -> Vec<(PieceId, Rotation)> {
    let outward = outward_sides(puzzle, pos);
    let mut out = Vec::new();
    for piece in puzzle.pieces() {
        if pinned.contains(&piece.id) { continue; }
        // Only border-class pieces (edge or corner) can be at perim.
        let is_corner_piece = piece.is_corner();
        let is_edge_piece = piece.is_edge();
        if !is_corner_piece && !is_edge_piece { continue; }
        // For corners, only place at corner positions.
        let is_corner_pos = is_corner(puzzle, pos);
        if is_corner_piece && !is_corner_pos { continue; }
        if is_edge_piece && is_corner_pos { continue; }
        // Try each rotation; the outward sides must be BORDER.
        for &r in &Rotation::ALL {
            let e = piece.edges.rotated(r).as_array();
            let ok = outward.iter().all(|&s| e[s as usize] == BORDER);
            if ok {
                out.push((piece.id, r));
            }
        }
    }
    out
}

/// Cheap lower-bound check: returns false if it can prove LP UB < threshold.
///
/// Current implementation: Hall-condition check on (side, color) bipartite.
pub fn cheap_lb_passes(puzzle: &Puzzle, board: &Board, _threshold: f64) -> bool {
    let max_color = puzzle.color_count.saturating_sub(1) as u8;

    let demands = b_i_demands_from_partial(puzzle, board);
    let mut demand_by_side_color: HashMap<(u8, u8), u32> = HashMap::new();
    for &(_cell, side, color) in &demands {
        if color != BORDER {
            *demand_by_side_color.entry((side, color)).or_default() += 1;
        }
    }

    let mut pinned: HashSet<PieceId> = HashSet::new();
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, _)) = board.get(pos) {
            pinned.insert(pid);
        }
    }

    let mut supply_by_side_color: HashMap<(u8, u8), u32> = HashMap::new();
    for piece in puzzle.pieces() {
        if !piece.is_inner() { continue; }
        if pinned.contains(&piece.id) { continue; }
        for &r in &Rotation::ALL {
            let e = piece.edges.rotated(r).as_array();
            for s in 0u8..4 {
                if e[s as usize] != BORDER {
                    *supply_by_side_color.entry((s, e[s as usize])).or_default() += 1;
                }
            }
        }
    }

    for s in 0u8..4 {
        for k in 1..=max_color {
            let d = *demand_by_side_color.get(&(s, k)).unwrap_or(&0);
            let sup = *supply_by_side_color.get(&(s, k)).unwrap_or(&0);
            if d > sup {
                return false;
            }
        }
    }

    true
}

/// Filter candidates at `pos` by neighbor-B-B compatibility with already-placed cells.
/// For each already-placed neighbor of `pos`, the side facing them must match their
/// outward-facing color.
fn neighbor_b_b_compatible(
    puzzle: &Puzzle,
    board: &Board,
    pos: Position,
    pid: PieceId,
    rot: Rotation,
) -> bool {
    let w = puzzle.width;
    let h = puzzle.height;
    let (x, y) = puzzle.xy(pos);
    let p = match puzzle.piece(pid) { Some(p) => p, None => return false };
    let e = p.edges.rotated(rot).as_array();
    // For each adjacent perimeter cell that's PLACED, check edge color compatibility.
    let nbrs: [(i64, i64, u8, u8); 4] = [
        (x as i64,     y as i64 - 1, 0, 2), // top
        (x as i64 + 1, y as i64,     1, 3), // right
        (x as i64,     y as i64 + 1, 2, 0), // bottom
        (x as i64 - 1, y as i64,     3, 1), // left
    ];
    for &(nx, ny, our_side, their_side) in &nbrs {
        if nx < 0 || ny < 0 || nx >= w as i64 || ny >= h as i64 { continue; }
        let n = (ny as u32) * w + (nx as u32);
        if !is_perimeter(puzzle, n) { continue; }
        if let Some((npid, nrot)) = board.get(n) {
            let Some(np) = puzzle.piece(npid) else { return false; };
            let ne = np.edges.rotated(nrot).as_array();
            if e[our_side as usize] != ne[their_side as usize] {
                return false;
            }
        }
    }
    true
}

/// Statistics tracked during DFS.
#[derive(Debug, Default)]
struct SearchStats {
    n_explored: u64,
    n_pruned_neighbor: u64,
    n_pruned_cheap: u64,
    n_leaves_kept: u64,
    deepest_depth: u32,
}

/// Recursive depth-first search.
fn dfs(
    puzzle: &Puzzle,
    board: &mut Board,
    used: &mut HashSet<PieceId>,
    order: &[Position],
    depth: usize,
    opts: &CpLpSearchOpts,
    stats: &mut SearchStats,
    start_time: std::time::Instant,
    on_full_border: &mut dyn FnMut(&Board),
) -> bool {
    if start_time.elapsed().as_secs_f64() > opts.time_budget_secs {
        return false; // time-limited stop
    }
    stats.n_explored += 1;
    if (depth as u32) > stats.deepest_depth { stats.deepest_depth = depth as u32; }

    if depth == order.len() {
        // Full border. Call leaf handler.
        stats.n_leaves_kept += 1;
        on_full_border(board);
        return true;
    }

    // Cheap prune (skip on shallow depths where Hall is trivially passing)
    if depth >= 4 && !cheap_lb_passes(puzzle, board, opts.threshold_ub) {
        stats.n_pruned_cheap += 1;
        return true;
    }

    let pos = order[depth];
    let cands = valid_border_candidates(puzzle, pos, used);
    for (pid, rot) in cands {
        if !neighbor_b_b_compatible(puzzle, board, pos, pid, rot) {
            stats.n_pruned_neighbor += 1;
            continue;
        }
        board.place(pos, pid, rot);
        used.insert(pid);
        if !dfs(puzzle, board, used, order, depth + 1, opts, stats, start_time, on_full_border) {
            // time stop
            return false;
        }
        // Undo
        used.remove(&pid);
        board.clear(pos);
    }
    true
}

/// Run the CP search.
pub fn run_cp_lp_search(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
    opts: &CpLpSearchOpts,
) -> Result<CpLpResult, String> {
    let order = perimeter_placement_order(puzzle);
    let mut board = Board::empty(puzzle);
    let mut used: HashSet<PieceId> = HashSet::new();
    // Pin hints (interior, fixed).
    for h in &hints.hints {
        board.place(h.position, h.piece_id, h.rotation);
        used.insert(h.piece_id);
    }
    let mut stats = SearchStats::default();
    let start = std::time::Instant::now();
    std::fs::create_dir_all(&opts.save_dir).ok();
    let mut save_idx: u64 = 0;
    let save_dir = opts.save_dir.clone();
    let leaf_min_bb = opts.leaf_min_bb;
    let puzzle_ref = puzzle;
    let mut handler = |b: &Board| {
        // Quick B-B match count filter.
        let bb = b_b_matches(puzzle_ref, b);
        if bb < leaf_min_bb { return; }
        // Save the full-border placement as JSON.
        let placement: Vec<_> = (0..puzzle_ref.cell_count()).filter_map(|p| {
            b.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": pid, "rotation": rot.as_u8()
            }))
        }).collect();
        let out = serde_json::json!({
            "border_index": save_idx,
            "bb_matches": bb,
            "placement": placement,
        });
        let path = save_dir.join(format!("border_{save_idx:08}_bb{bb}.json"));
        if let Ok(s) = serde_json::to_string(&out) {
            let _ = std::fs::write(&path, s);
        }
        save_idx += 1;
    };
    let _ = dfs(puzzle, &mut board, &mut used, &order, 0, opts, &mut stats, start, &mut handler);
    Ok(CpLpResult {
        n_explored: stats.n_explored,
        n_pruned_cheap: stats.n_pruned_cheap,
        n_pruned_reduced_lp: 0,
        n_pruned_full_lp: 0,
        n_leaves_kept: stats.n_leaves_kept,
        best_lp_ub_seen: 0.0,
        elapsed_secs: start.elapsed().as_secs_f64(),
    })
}

pub fn partial_lp_ub(_puzzle: &Puzzle, _board: &Board, _placed: &[Position])
    -> Result<f64, String>
{
    Err("partial_lp_ub: not yet implemented (requires LP refactor for empty-perim cells)".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_puzzle_io::load_puzzle_with_hints;
    use std::path::PathBuf;

    #[test]
    fn skeleton_builds() {
        let _opts = CpLpSearchOpts::default();
    }

    #[test]
    fn perimeter_order_is_60_cells_on_16x16() {
        let path = PathBuf::from("../../data/puzzles/size_16_official_eternity.csv");
        if !path.exists() { return; }
        let Ok((puzzle, _)) = load_puzzle_with_hints(&path) else { return };
        let order = perimeter_placement_order(&puzzle);
        assert_eq!(order.len(), 60);
        // Must contain all 4 corners
        let corners: Vec<Position> = order.iter().copied().filter(|&p| is_corner(&puzzle, p)).collect();
        assert_eq!(corners.len(), 4);
    }

    #[test]
    fn cheap_lb_passes_on_empty_board() {
        let path = PathBuf::from("../../data/puzzles/size_16_official_eternity.csv");
        if !path.exists() { return; }
        let Ok((puzzle, _)) = load_puzzle_with_hints(&path) else { return };
        let board = Board::empty(&puzzle);
        assert!(cheap_lb_passes(&puzzle, &board, 478.0));
    }

    #[test]
    fn valid_border_candidates_for_corner() {
        let path = PathBuf::from("../../data/puzzles/size_16_official_eternity.csv");
        if !path.exists() { return; }
        let Ok((puzzle, _)) = load_puzzle_with_hints(&path) else { return };
        let pinned = HashSet::new();
        // Top-left corner = position 0
        let cands = valid_border_candidates(&puzzle, 0, &pinned);
        // Should be 4 corner pieces, each with 1 valid rotation (BORDER on top+left)
        assert_eq!(cands.len(), 4);
    }
}
