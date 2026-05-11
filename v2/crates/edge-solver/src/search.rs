// Branch-and-bound search in edge-space.
//
// Variables: the 480 interior edges. Domain: {1..n_colors-1}.
// Constraints:
//   (1) Per-cell, the assigned edges around the cell must be a partial
//       prefix of some piece-rotation 4-tuple (with unassigned sides
//       as wildcards). Boundary sides are pre-fixed to BORDER, encoded
//       into cell_shape_mask.
//   (2) Piece-uniqueness: each piece may satisfy at most one cell. We
//       enforce this incrementally — when a cell's row-mask collapses
//       to "rows of a single piece," we commit that piece, removing it
//       from circulation for all other cells. May cascade.
// Score: number of assigned edges (maximize). Partial MAX-CSP.

use eternity2_core::{Color, PieceId, Puzzle, BORDER};

use crate::tables::{
    mask_and_into, mask_copy, mask_for_each, mask_popcount, Tables,
};
use crate::topology::Topology;

#[derive(Debug, Clone)]
pub struct SearchConfig {
    pub time_budget_ms: u64,
    pub seed: u64,
    /// If true, commit pieces during edge-search when a cell's
    /// row-mask collapses onto a single piece (across rotations).
    /// Without this, the search treats piece-uniqueness as a recovery-
    /// time problem, which collapses many "valid edge colorings" onto
    /// unrealisable boards.
    pub propagate_piece_uniqueness: bool,
    /// Stop on first complete assignment (n_edges == assigned). When
    /// false, search continues — useful for exhausting all solutions
    /// or for benchmarking branching dynamics.
    pub stop_on_first: bool,
    /// Emit per-decision tracing to stderr. Slow; only for debugging.
    pub trace: bool,
}

impl Default for SearchConfig {
    fn default() -> Self {
        Self {
            time_budget_ms: 0,
            seed: 0,
            propagate_piece_uniqueness: true,
            stop_on_first: true,
            trace: false,
        }
    }
}

#[derive(Debug, Clone, Copy, Default)]
pub struct SearchStats {
    pub nodes: u64,
    pub backtracks: u64,
    pub propagations: u64,
    pub piece_commits: u64,
    pub edges_assigned_best: u32,
    pub time_us: u64,
}

pub struct Search<'a> {
    pub puzzle: &'a Puzzle,
    pub topology: &'a Topology,
    pub tables: &'a Tables,
    pub config: SearchConfig,
    pub edge_color: Vec<Option<Color>>,
    /// cell_rows_alive[c]: rows still consistent with c's assigned
    /// edges AND not-yet-committed pieces. Stored as one big flat
    /// vector of u64; cell c lives at `c*words_per_mask .. (c+1)*words_per_mask`.
    pub cell_rows_alive: Vec<u64>,
    /// Bitmask over rows of pieces NOT yet committed. Initially all-ones
    /// for valid row ids. When a piece is committed, all its rows are
    /// cleared here.
    pub available_rows: Vec<u64>,
    /// For each piece id, Some(cell) if committed at that cell.
    pub piece_committed_at: Vec<Option<u32>>,
    /// For each cell, Some(piece) if a piece has been committed to it.
    pub cell_committed_piece: Vec<Option<PieceId>>,
    pub best_edge_color: Vec<Option<Color>>,
    pub best_score: u32,
    pub stats: SearchStats,
    pub started_us: u64,
}

/// Undo record for one `assign` call. Snapshots everything modified.
pub struct AssignUndo {
    pub edge: u32,
    /// Snapshots: cell index → prior cell_rows_alive slice (only cells
    /// whose mask we actually changed during this assign).
    pub cell_snapshots: Vec<(u32, Vec<u64>)>,
    /// Prior available_rows if it changed. Empty Vec means unchanged.
    pub available_snapshot: Option<Vec<u64>>,
    /// Pieces committed during this assign call: (piece_id, cell).
    pub pieces_committed: Vec<(PieceId, u32)>,
}

impl<'a> Search<'a> {
    #[must_use]
    pub fn new(
        puzzle: &'a Puzzle,
        topology: &'a Topology,
        tables: &'a Tables,
        config: SearchConfig,
    ) -> Self {
        let n_edges = topology.n_edges as usize;
        let n_cells = topology.n_cells as usize;
        let wpm = tables.words_per_mask;
        let mut cell_rows_alive = vec![0u64; n_cells * wpm];
        for c in 0..n_cells {
            let src = tables.cell_shape_mask(c as u32);
            let dst = &mut cell_rows_alive[c * wpm..(c + 1) * wpm];
            mask_copy(dst, src);
        }
        // available_rows starts as the union of all cell_shape_masks
        // (i.e., every row that fits SOME cell). This is just "all
        // valid rows" — pieces that don't fit any cell can't be
        // assigned, but those don't exist for a well-formed puzzle.
        let mut available_rows = vec![0u64; wpm];
        for rid in 0..tables.n_rows as usize {
            available_rows[rid / 64] |= 1u64 << (rid % 64);
        }
        Self {
            puzzle,
            topology,
            tables,
            config,
            edge_color: vec![None; n_edges],
            cell_rows_alive,
            available_rows,
            piece_committed_at: vec![None; tables.max_piece_id as usize + 1],
            cell_committed_piece: vec![None; n_cells],
            best_edge_color: vec![None; n_edges],
            best_score: 0,
            stats: SearchStats::default(),
            started_us: 0,
        }
    }

    #[inline]
    fn cell_mask(&self, c: u32) -> &[u64] {
        let wpm = self.tables.words_per_mask;
        let i = c as usize * wpm;
        &self.cell_rows_alive[i..i + wpm]
    }

    #[inline]
    fn cell_mask_mut(&mut self, c: u32) -> &mut [u64] {
        let wpm = self.tables.words_per_mask;
        let i = c as usize * wpm;
        &mut self.cell_rows_alive[i..i + wpm]
    }

    /// Number of assigned edges.
    pub fn assigned_count(&self) -> u32 {
        self.edge_color.iter().filter(|o| o.is_some()).count() as u32
    }

    /// Determine if `mask` (intersected with `available_rows`) has all
    /// set bits belonging to a single piece. If yes, return that piece.
    /// If empty after intersection, return None (caller checks
    /// emptiness independently).
    fn collapsed_to_piece(&self, mask: &[u64]) -> Option<PieceId> {
        let wpm = self.tables.words_per_mask;
        let mut first_pid: Option<u32> = None;
        for w_idx in 0..wpm {
            let word = mask[w_idx] & self.available_rows[w_idx];
            if word == 0 {
                continue;
            }
            // Walk set bits; check all belong to the same piece.
            let mut w = word;
            while w != 0 {
                let bit = w.trailing_zeros();
                let rid = (w_idx as u32) * 64 + bit;
                let row = self.tables.rows[rid as usize];
                let pid = u32::from(row.piece_id);
                match first_pid {
                    None => first_pid = Some(pid),
                    Some(existing) if existing != pid => return None,
                    _ => {}
                }
                w &= w - 1;
            }
        }
        first_pid.map(|p| p as PieceId)
    }

    /// Snapshot a cell's mask into the undo log (idempotently — at most
    /// once per cell per assign call).
    fn snapshot_cell(&self, cell: u32, undo: &mut AssignUndo) {
        if undo.cell_snapshots.iter().any(|(c, _)| *c == cell) {
            return;
        }
        let snap: Vec<u64> = self.cell_mask(cell).to_vec();
        undo.cell_snapshots.push((cell, snap));
    }

    fn snapshot_available(&self, undo: &mut AssignUndo) {
        if undo.available_snapshot.is_none() {
            undo.available_snapshot = Some(self.available_rows.clone());
        }
    }

    /// Pin an edge to a color and propagate to fixpoint:
    ///  - tighten the two adjacent cells via side_color_mask
    ///  - if a cell collapses to a single piece, commit that piece
    ///  - committing a piece clears its rows from `available_rows`,
    ///    which then tightens every other cell — cascade.
    /// Returns Ok(undo) on success, Err(undo) on contradiction.
    pub fn assign(&mut self, edge: u32, color: Color) -> Result<AssignUndo, AssignUndo> {
        debug_assert!(self.edge_color[edge as usize].is_none());
        self.edge_color[edge as usize] = Some(color);
        let mut undo = AssignUndo {
            edge,
            cell_snapshots: Vec::new(),
            available_snapshot: None,
            pieces_committed: Vec::new(),
        };

        // Step 1: tighten the two adjacent cells with the side-color mask.
        let cells = self.topology.edge_cells[edge as usize];
        let mut dirty: Vec<u32> = Vec::new();
        for (c, side) in cells.iter().copied() {
            self.snapshot_cell(c, &mut undo);
            let scm: Vec<u64> = self.tables.side_color_mask(side, color).to_vec();
            let mask = self.cell_mask_mut(c);
            mask_and_into(mask, &scm);
            self.stats.propagations += 1;
            dirty.push(c);
        }

        // Step 2: propagate-to-fixpoint. For each dirty cell, intersect
        // with available_rows and check empty/collapsed. On collapse,
        // commit the piece — clearing its rows from available_rows —
        // which dirties every other cell. Iterate.
        while let Some(c) = dirty.pop() {
            // Skip cells that already have a committed piece — they're
            // fully decided.
            if self.cell_committed_piece[c as usize].is_some() {
                continue;
            }
            // Compute the cell's "live" rows = cell_rows_alive[c] ∩ available_rows.
            // (cell_rows_alive itself isn't kept narrowed by `available_rows`
            // automatically; intersecting on read is cheap.)
            let wpm = self.tables.words_per_mask;
            let i = c as usize * wpm;
            // Compute popcount of (cell_rows_alive[c] AND available_rows).
            let mut all_zero = true;
            for w in 0..wpm {
                if self.cell_rows_alive[i + w] & self.available_rows[w] != 0 {
                    all_zero = false;
                    break;
                }
            }
            if all_zero {
                return Err(undo);
            }
            if !self.config.propagate_piece_uniqueness {
                continue;
            }
            // Check if collapsed to a single piece.
            let mask_slice: Vec<u64> = (0..wpm)
                .map(|w| self.cell_rows_alive[i + w] & self.available_rows[w])
                .collect();
            if let Some(pid) = self.collapsed_to_piece(&mask_slice) {
                // Commit. Skip if this piece is the same as the cell's
                // shape — but it shouldn't be assigned already (we checked above).
                self.snapshot_available(&mut undo);
                let piece_mask = self.tables.piece_mask(pid);
                // Clear piece_mask from available_rows.
                for w in 0..wpm {
                    self.available_rows[w] &= !piece_mask[w];
                }
                debug_assert!(
                    self.piece_committed_at[u32::from(pid) as usize].is_none(),
                    "double-commit piece {pid}"
                );
                debug_assert!(
                    self.cell_committed_piece[c as usize].is_none(),
                    "double-commit cell {c}"
                );
                self.piece_committed_at[u32::from(pid) as usize] = Some(c);
                self.cell_committed_piece[c as usize] = Some(pid);
                undo.pieces_committed.push((pid, c));
                self.stats.piece_commits += 1;
                if self.config.trace {
                    eprintln!("  commit piece {pid} → cell {c}");
                }
                // Every other cell with assigned-edges might now be
                // affected. Conservatively, dirty all uncommitted cells.
                for other in 0..self.topology.n_cells {
                    if other == c { continue; }
                    if self.cell_committed_piece[other as usize].is_some() { continue; }
                    dirty.push(other);
                }
            }
        }

        Ok(undo)
    }

    /// Undo a successful or failed assign.
    pub fn restore(&mut self, undo: AssignUndo) {
        self.edge_color[undo.edge as usize] = None;
        for (pid, cell) in undo.pieces_committed.into_iter().rev() {
            self.piece_committed_at[u32::from(pid) as usize] = None;
            self.cell_committed_piece[cell as usize] = None;
        }
        if let Some(prior) = undo.available_snapshot {
            self.available_rows = prior;
        }
        for (c, prior) in undo.cell_snapshots.into_iter().rev() {
            let mask = self.cell_mask_mut(c);
            mask_copy(mask, &prior);
        }
    }

    /// Pick the next edge to assign: tightest adjacent-cell first.
    pub fn select_edge(&self) -> Option<u32> {
        let mut best: Option<(u32, u64)> = None;
        let n = self.topology.n_edges;
        let wpm = self.tables.words_per_mask;
        for e in 0..n {
            if self.edge_color[e as usize].is_some() {
                continue;
            }
            let cells = self.topology.edge_cells[e as usize];
            // Score = min over the two adjacent cells of (cell_rows_alive ∩ available_rows) popcount.
            let cell_pop = |c: u32| -> u64 {
                let i = c as usize * wpm;
                let mut p = 0u32;
                for w in 0..wpm {
                    p += (self.cell_rows_alive[i + w] & self.available_rows[w]).count_ones();
                }
                p as u64
            };
            let p0 = cell_pop(cells[0].0);
            let p1 = cell_pop(cells[1].0);
            let score = p0.min(p1);
            match best {
                None => best = Some((e, score)),
                Some((_, s)) if score < s => best = Some((e, score)),
                _ => {}
            }
        }
        best.map(|(e, _)| e)
    }

    /// Live-color domain for an edge: intersect the two adjacent cells'
    /// (cell_rows_alive ∩ available_rows) projections onto the edge's
    /// facing side.
    pub fn edge_live_colors(&self, edge: u32) -> Vec<Color> {
        let cells = self.topology.edge_cells[edge as usize];
        let wpm = self.tables.words_per_mask;
        let mut per_cell: [Vec<bool>; 2] = [
            vec![false; self.tables.n_colors as usize],
            vec![false; self.tables.n_colors as usize],
        ];
        for (idx, (c, side)) in cells.iter().copied().enumerate() {
            let i = c as usize * wpm;
            let mut mask_slice = vec![0u64; wpm];
            for w in 0..wpm {
                mask_slice[w] = self.cell_rows_alive[i + w] & self.available_rows[w];
            }
            mask_for_each(&mask_slice, |rid| {
                let row = self.tables.rows[rid as usize];
                let c_idx = row.edges[side] as usize;
                per_cell[idx][c_idx] = true;
            });
        }
        let mut colors = Vec::new();
        for k in 0..self.tables.n_colors as usize {
            if per_cell[0][k] && per_cell[1][k] && k != BORDER as usize {
                colors.push(k as Color);
            }
        }
        colors
    }

    pub fn check_score(&mut self) {
        let s = self.assigned_count();
        if s > self.best_score {
            self.best_score = s;
            self.best_edge_color.clone_from(&self.edge_color);
            self.stats.edges_assigned_best = s;
        }
    }

    pub fn recurse(&mut self, clock_us: &dyn Fn() -> u64) -> RecurseResult {
        self.stats.nodes += 1;
        self.check_score();
        if self.config.time_budget_ms != 0 {
            let elapsed_us = clock_us().saturating_sub(self.started_us);
            if elapsed_us / 1000 >= self.config.time_budget_ms {
                return RecurseResult::TimedOut;
            }
        }
        let Some(edge) = self.select_edge() else {
            return RecurseResult::AllAssigned;
        };
        let colors = self.edge_live_colors(edge);
        if self.config.trace {
            eprintln!("[node {}] depth={} edge={} live_colors={:?} assigned={}",
                self.stats.nodes, self.assigned_count(), edge, colors,
                self.assigned_count());
        }
        if colors.is_empty() {
            return RecurseResult::DeadEnd;
        }
        for color in colors {
            match self.assign(edge, color) {
                Ok(undo) => {
                    let sub = self.recurse(clock_us);
                    match sub {
                        RecurseResult::TimedOut => {
                            self.restore(undo);
                            return RecurseResult::TimedOut;
                        }
                        RecurseResult::AllAssigned if self.config.stop_on_first => {
                            self.restore(undo);
                            return RecurseResult::AllAssigned;
                        }
                        _ => self.restore(undo),
                    }
                }
                Err(undo) => {
                    self.stats.backtracks += 1;
                    self.restore(undo);
                }
            }
        }
        RecurseResult::Exhausted
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RecurseResult {
    AllAssigned,
    Exhausted,
    TimedOut,
    DeadEnd,
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_core::{Edges, Piece, Puzzle};

    fn tiny_solvable_2x2() -> Puzzle {
        let pieces = vec![
            Piece::new(0, Edges::new(BORDER, 1, 1, BORDER)),
            Piece::new(1, Edges::new(BORDER, BORDER, 1, 1)),
            Piece::new(2, Edges::new(1, 1, BORDER, BORDER)),
            Piece::new(3, Edges::new(1, BORDER, BORDER, 1)),
        ];
        Puzzle::new(2, 2, 2, pieces).unwrap()
    }

    #[test]
    fn solves_trivial_2x2() {
        let puzzle = tiny_solvable_2x2();
        let topo = Topology::new(&puzzle);
        let tables = Tables::new(&puzzle, &topo);
        let mut s = Search::new(&puzzle, &topo, &tables, SearchConfig::default());
        let clock = || 0u64;
        let r = s.recurse(&clock);
        assert!(matches!(r, RecurseResult::AllAssigned | RecurseResult::Exhausted),
            "got {r:?}");
        assert_eq!(s.best_score, topo.n_edges, "should assign all {} edges", topo.n_edges);
    }
}
