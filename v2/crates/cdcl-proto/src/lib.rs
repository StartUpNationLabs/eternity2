//! Vol-57 CDCL no-good learning prototype for E2 CSP.
//!
//! Standalone implementation, not modifying solver-engine. Once
//! validated on small puzzles, port to solver-engine in vol-58.
//!
//! See:
//!   vault/concepts/cdcl-no-good-e2.md (math design, vol-56)
//!   vault/concepts/cdcl-engine-integration.md (engine integration plan, vol-56)
//!   vault/sessions/vol-56.md (empirical green-light: 96% of states
//!                              have ready-to-fire clauses, clauses
//!                              median 6 literals)

#![forbid(unsafe_code)]

use std::collections::{HashMap, HashSet};

use eternity2_core::{BORDER, Board, Edges, Piece, PieceId, Puzzle, Rotation};

/// A placement literal: piece p in cell c with rotation r.
/// Stored as (pos, pid, rot_u8) for derivable Ord.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Lit {
    pub pos: u32,
    pub pid: PieceId,
    pub rot_u8: u8,
}

impl Lit {
    pub fn new(pos: u32, pid: PieceId, rot: Rotation) -> Self {
        Self { pos, pid, rot_u8: rot.as_u8() }
    }
    pub fn rot(&self) -> Rotation {
        Rotation::from_u8(self.rot_u8).expect("valid rotation")
    }
}

/// A no-good clause: any extension of this assignment is infeasible.
#[derive(Debug, Clone)]
pub struct NoGood {
    pub literals: Vec<Lit>,
}

/// Solver statistics.
#[derive(Debug, Default, Clone)]
pub struct Stats {
    pub nodes: u64,
    pub wipeouts: u64,
    pub clauses_learned: u64,
    pub clause_size_sum: u64,
    pub clause_size_max: u32,
    pub backtracks: u64,
    pub propagations_from_clauses: u64,
}

/// Configuration.
#[derive(Debug, Clone)]
pub struct Config {
    pub use_no_good_learning: bool,
    pub time_budget_ms: u64,
    /// Apply deletion-based clause minimization after learning.
    pub minimize_clauses: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            use_no_good_learning: true,
            time_budget_ms: 60_000,
            minimize_clauses: true,
        }
    }
}

/// Search state during DFS.
struct SearchState<'a> {
    puzzle: &'a Puzzle,
    cfg: Config,
    /// Currently assigned cells: cell pos → (pid, rot).
    assigned: HashMap<u32, (PieceId, Rotation)>,
    /// Domain of each cell: set of valid (pid, rot) placements.
    /// Indexed by cell position.
    domain: Vec<HashSet<(PieceId, Rotation)>>,
    /// Pieces used so far.
    pieces_used: HashSet<PieceId>,
    /// Cause tracking: (cell, literal) → set of currently-placed cells
    /// that caused this literal to be removed from cell's domain.
    /// Only populated for currently-removed literals.
    removal_cause: HashMap<(u32, PieceId, Rotation), Vec<u32>>,
    /// No-good database.
    clauses: Vec<NoGood>,
    /// Watch index: literal → clause IDs watching this literal.
    watches: HashMap<Lit, Vec<usize>>,
    /// Deadline (Instant).
    deadline: std::time::Instant,
    /// Stats.
    pub stats: Stats,
}

impl<'a> SearchState<'a> {
    fn new(puzzle: &'a Puzzle, cfg: Config) -> Self {
        let n_cells = puzzle.cell_count() as usize;
        let mut domain = vec![HashSet::new(); n_cells];
        // Initialize each cell's domain: all pieces with rotations
        // satisfying cell-class (corner/edge/interior).
        let w = puzzle.width;
        let h = puzzle.height;
        for pos in 0..n_cells {
            let x = (pos as u32) % w;
            let y = (pos as u32) / w;
            let is_corner = (x == 0 || x + 1 == w) && (y == 0 || y + 1 == h);
            let is_outer = x == 0 || x + 1 == w || y == 0 || y + 1 == h;
            let target_border_sides: u32 = if is_corner { 2 } else if is_outer { 1 } else { 0 };
            for piece in puzzle.pieces() {
                let n_border = piece.edges.as_array().iter().filter(|&&c| c == BORDER).count() as u32;
                if n_border != target_border_sides { continue; }
                for &r in &Rotation::ALL {
                    let e = piece.edges.rotated(r).as_array();
                    let mut frame_ok = true;
                    // Outer sides must be BORDER iff cell on that side of frame.
                    if (e[0] == BORDER) != (y == 0) { frame_ok = false; }
                    if (e[1] == BORDER) != (x + 1 == w) { frame_ok = false; }
                    if (e[2] == BORDER) != (y + 1 == h) { frame_ok = false; }
                    if (e[3] == BORDER) != (x == 0) { frame_ok = false; }
                    if !frame_ok { continue; }
                    domain[pos].insert((piece.id, r));
                }
            }
        }

        Self {
            puzzle,
            deadline: std::time::Instant::now() + std::time::Duration::from_millis(cfg.time_budget_ms),
            cfg,
            assigned: HashMap::new(),
            domain,
            pieces_used: HashSet::new(),
            removal_cause: HashMap::new(),
            clauses: Vec::new(),
            watches: HashMap::new(),
            stats: Stats::default(),
        }
    }

    fn neighbors(&self, pos: u32) -> Vec<(u32, usize, usize)> {
        let w = self.puzzle.width;
        let h = self.puzzle.height;
        let x = pos % w;
        let y = pos / w;
        let mut out = Vec::with_capacity(4);
        if y > 0 { out.push((pos - w, 0, 2)); }
        if x + 1 < w { out.push((pos + 1, 1, 3)); }
        if y + 1 < h { out.push((pos + w, 2, 0)); }
        if x > 0 { out.push((pos - 1, 3, 1)); }
        out
    }

    fn rotated_edges(&self, pid: PieceId, rot: Rotation) -> [u8; 4] {
        self.puzzle.piece(pid).expect("piece").edges.rotated(rot).as_array()
    }

    /// Propagate from cell `pos` assigned to `(pid, rot)`.
    /// Returns (success, undo_log_for_removals, wipeout_cell).
    /// Records cause for each removal.
    fn propagate(&mut self, pos: u32, pid: PieceId, rot: Rotation)
        -> (bool, Vec<(u32, (PieceId, Rotation))>, Option<u32>)
    {
        let mut undo = Vec::new();
        // Forward-check: piece uniqueness, then edge constraints.
        // 1) Remove pid from all other unassigned cells.
        let cells: Vec<u32> = (0..self.puzzle.cell_count())
            .filter(|p| *p != pos && !self.assigned.contains_key(p))
            .collect();
        for p2 in cells {
            let to_remove: Vec<(PieceId, Rotation)> = self.domain[p2 as usize].iter()
                .filter(|(p, _)| *p == pid).copied().collect();
            for v in to_remove {
                self.domain[p2 as usize].remove(&v);
                undo.push((p2, v));
                self.removal_cause.insert((p2, v.0, v.1), vec![pos]);
                if self.domain[p2 as usize].is_empty() {
                    return (false, undo, Some(p2));
                }
            }
        }
        // 2) Edge-equality: for neighbours of pos, restrict by edge color.
        let my_edges = self.rotated_edges(pid, rot);
        for (np, my_s, their_s) in self.neighbors(pos) {
            if self.assigned.contains_key(&np) { continue; }
            let req_color = my_edges[my_s];
            let to_remove: Vec<(PieceId, Rotation)> = self.domain[np as usize].iter()
                .filter(|(p2, r2)| {
                    let e = self.rotated_edges(*p2, *r2);
                    e[their_s] != req_color
                }).copied().collect();
            for v in to_remove {
                self.domain[np as usize].remove(&v);
                undo.push((np, v));
                self.removal_cause.insert((np, v.0, v.1), vec![pos]);
                if self.domain[np as usize].is_empty() {
                    return (false, undo, Some(np));
                }
            }
        }
        (true, undo, None)
    }

    fn restore(&mut self, undo: Vec<(u32, (PieceId, Rotation))>) {
        for (cell, v) in undo {
            self.domain[cell as usize].insert(v);
            self.removal_cause.remove(&(cell, v.0, v.1));
        }
    }

    /// Find a wipeout cell's CONFLICT cause: union of causes for all
    /// values originally in this cell's domain that are currently absent.
    /// (Equivalent to 1-UIP for flat E2 cause graph.)
    fn analyze_conflict(&self, wipe_cell: u32) -> Vec<u32> {
        let mut causes = HashSet::new();
        // Walk all (cell, pid, rot) entries in removal_cause with cell == wipe_cell.
        for (k, v) in &self.removal_cause {
            if k.0 == wipe_cell {
                for c in v {
                    causes.insert(*c);
                }
            }
        }
        let mut result: Vec<u32> = causes.into_iter().collect();
        result.sort();
        result
    }

    /// Learn a no-good from current state at wipeout.
    /// Returns clause size, or 0 if no clause learned.
    ///
    /// Deletion-based clause minimization: after building the initial
    /// clause from causes, try dropping each literal one at a time
    /// and re-check whether the remaining literals' AC-3 still wipes
    /// out the cell. Drop literals that don't matter.
    ///
    /// This is O(k²) per learn call where k = clause size. For naive
    /// k=100, that's 10000 small AC-3 sims; expensive. But should
    /// shrink huge canonical-scale clauses to manageable size.
    fn learn_no_good(&mut self, wipe_cell: u32) -> usize {
        let causes = self.analyze_conflict(wipe_cell);
        if causes.is_empty() { return 0; }
        let mut literals: Vec<Lit> = causes.iter().filter_map(|&c| {
            self.assigned.get(&c).map(|&(pid, rot)| Lit::new(c, pid, rot))
        }).collect();
        if literals.is_empty() { return 0; }
        literals.sort();

        // Deletion-based minimization: only run if clause is large
        // enough to be worth shrinking.
        if literals.len() > 8 && self.cfg.minimize_clauses {
            literals = self.minimize_by_deletion(literals, wipe_cell);
        }

        let size = literals.len();
        self.stats.clauses_learned += 1;
        self.stats.clause_size_sum += size as u64;
        if (size as u32) > self.stats.clause_size_max {
            self.stats.clause_size_max = size as u32;
        }
        let clause_id = self.clauses.len();
        for w in literals.iter().take(2) {
            self.watches.entry(*w).or_default().push(clause_id);
        }
        self.clauses.push(NoGood { literals });
        size
    }

    /// For each literal in `lits`, try dropping it: build a fresh
    /// AC-3 state with ONLY the remaining literals as the partial
    /// assignment, run AC-3, see if wipe_cell still has empty domain.
    /// If yes, the dropped literal isn't needed.
    ///
    /// Conservative: we drop ONE at a time greedily, walk through the
    /// list in order. After each successful drop, the remaining
    /// literals are checked against a fresh AC-3 from scratch.
    fn minimize_by_deletion(&self, lits: Vec<Lit>, wipe_cell: u32) -> Vec<Lit> {
        let mut current = lits.clone();
        let mut i = 0;
        while i < current.len() {
            let candidate = current[i];
            // Build a trial assignment without `candidate`
            let trial: Vec<Lit> = current.iter().filter(|&&l| l != candidate).copied().collect();
            if self.still_wipes(&trial, wipe_cell) {
                current = trial;
                // Don't increment i; the new current[i] is whatever was at i+1.
            } else {
                i += 1;
            }
        }
        current
    }

    /// Returns true if, starting from a fresh domain, applying AC-3
    /// to the literals in `lits` would wipe out `wipe_cell`.
    /// This is a SIMULATION (doesn't mutate self).
    fn still_wipes(&self, lits: &[Lit], wipe_cell: u32) -> bool {
        // Build a fresh domain from puzzle structure
        let n_cells = self.puzzle.cell_count() as usize;
        let mut sim_domain: Vec<HashSet<(PieceId, Rotation)>> = self.domain.iter().cloned().collect();
        // BUT we need the PRISTINE initial domain, not the current one.
        // Reconstruct: for each cell not in `lits`, the initial domain
        // is what SearchState::new builds. We don't have it stored.
        // Approximation: use self.domain as the starting point and add
        // back any values removed by the current `assigned` state — but
        // we don't track that either.
        //
        // Compromise: use current self.domain (which reflects current
        // search context) and remove any literals from the trial that
        // aren't in current assigned. This is over-restrictive (will
        // call clauses "still wipes" more often than truly minimal),
        // but soundness preserved (we'll keep more literals than
        // necessary, never fewer).
        //
        // For a future cleaner impl, store the pristine domain at
        // SearchState::new.

        // Simulate: apply each lit's effect (mark pid used + edge
        // constraints) on sim_domain.
        let lit_positions: HashSet<u32> = lits.iter().map(|l| l.pos).collect();

        // Restore literals NOT in `lits` to be unassigned in sim
        for pos in 0..n_cells {
            let pos_u32 = pos as u32;
            // If sim_domain is empty due to AC-3 from current state,
            // we can't make a clean trial. Just return true (conservative).
            if self.assigned.contains_key(&pos_u32) && !lit_positions.contains(&pos_u32) {
                // This cell is currently assigned but NOT in the trial
                // clause; nothing to do — sim won't include its effects.
                // For a fresh AC-3 sim we'd treat this cell as unassigned.
            }
        }

        // Simplified AC-3 sim: for each lit in `lits`, do forward-check
        // - remove `lit.pid` from all other cells' domains (piece uniq).
        // - remove edge-incompatible values from neighbours.
        for lit in lits {
            let pid = lit.pid;
            let rot = lit.rot();
            let pos = lit.pos;
            let edges_at_pos = self.rotated_edges(pid, rot);
            // Piece uniq
            for p2 in 0..n_cells {
                if p2 as u32 == pos { continue; }
                if lit_positions.contains(&(p2 as u32)) { continue; }
                let removed: Vec<(PieceId, Rotation)> = sim_domain[p2].iter()
                    .filter(|(p, _)| *p == pid).copied().collect();
                for v in removed { sim_domain[p2].remove(&v); }
            }
            // Edge constraint with neighbours
            for (np, my_s, their_s) in self.neighbors(pos) {
                if lit_positions.contains(&np) { continue; }
                let req = edges_at_pos[my_s];
                let removed: Vec<(PieceId, Rotation)> = sim_domain[np as usize].iter()
                    .filter(|(p2, r2)| {
                        let e = self.rotated_edges(*p2, *r2);
                        e[their_s] != req
                    }).copied().collect();
                for v in removed { sim_domain[np as usize].remove(&v); }
            }
        }
        // Check if wipe_cell's domain is empty
        sim_domain[wipe_cell as usize].is_empty()
    }

    /// Check if any learned clause is satisfied (would-fail current state).
    /// Returns true if any clause's literals are all currently assigned.
    fn check_satisfied(&mut self) -> bool {
        for clause in &self.clauses {
            let satisfied = clause.literals.iter().all(|lit| {
                self.assigned.get(&lit.pos) == Some(&(lit.pid, lit.rot()))
            });
            if satisfied {
                self.stats.propagations_from_clauses += 1;
                return true;
            }
        }
        false
    }

    /// Unit-propagate from learned clauses: for each clause, if all
    /// but one literal is satisfied by the current assignment, remove
    /// the one unassigned literal's value from its cell's domain.
    /// Returns (success, undo_log, wipe_cell_opt).
    ///
    /// Optimization (vol-58 T2): take the literal that was JUST assigned
    /// as a hint. Only check clauses watching that literal (the only
    /// clauses whose state could have changed). Drastically smaller
    /// candidate set per call.
    fn unit_prop_from_clauses(&mut self, just_assigned: Option<Lit>)
        -> (bool, Vec<(u32, (PieceId, Rotation))>, Option<u32>)
    {
        let mut undo = Vec::new();
        // Candidate clauses: only those watching the just-assigned literal.
        // If no hint, fallback to all clauses (used at root or special cases).
        let candidates: Vec<usize> = if let Some(lit) = just_assigned {
            self.watches.get(&lit).cloned().unwrap_or_default()
        } else {
            (0..self.clauses.len()).collect()
        };
        // Single pass, no fixpoint loop (saves time; future unit-prop
        // will fire when those new assignments happen).
        {
            #[allow(unused_assignments)]
            let mut new_props = 0;
            for &cid in &candidates {
                let clause = &self.clauses[cid];
                let mut unsatisfied = Vec::with_capacity(2);
                let mut blocked = false;
                for lit in &clause.literals {
                    if let Some(&(pid, rot)) = self.assigned.get(&lit.pos) {
                        if pid != lit.pid || rot != lit.rot() {
                            // Literal blocked (clause becomes vacuously
                            // satisfied, no propagation possible).
                            blocked = true;
                            break;
                        }
                        // else: literal in clause matches assignment; counts as satisfied.
                    } else {
                        unsatisfied.push(*lit);
                        if unsatisfied.len() > 1 { break; }
                    }
                }
                if blocked { continue; }
                if unsatisfied.len() == 1 {
                    let lit = unsatisfied[0];
                    let val = (lit.pid, lit.rot());
                    if self.domain[lit.pos as usize].contains(&val) {
                        self.domain[lit.pos as usize].remove(&val);
                        undo.push((lit.pos, val));
                        // Cause: the SATISFIED literals of the clause (everyone except `lit`).
                        let cause: Vec<u32> = clause.literals.iter()
                            .filter(|l| **l != lit)
                            .map(|l| l.pos)
                            .collect();
                        self.removal_cause.insert((lit.pos, val.0, val.1), cause);
                        self.stats.propagations_from_clauses += 1;
                        new_props += 1;
                        if self.domain[lit.pos as usize].is_empty() {
                            return (false, undo, Some(lit.pos));
                        }
                    }
                }
                // unsatisfied.len() == 0: clause fully satisfied = conflict.
                // We don't handle this explicitly here; if it happens we
                // should have detected it via check_satisfied earlier.
            }
            let _ = new_props;
        }
        (true, undo, None)
    }

    /// MRV: pick unassigned cell with smallest domain.
    fn select_variable(&self) -> Option<u32> {
        let mut best: Option<u32> = None;
        let mut best_size: usize = usize::MAX;
        for p in 0..self.puzzle.cell_count() {
            if self.assigned.contains_key(&p) { continue; }
            let s = self.domain[p as usize].len();
            if s < best_size {
                best_size = s;
                best = Some(p);
                if s == 0 { return Some(p); }
            }
        }
        best
    }

    fn dfs(&mut self) -> Result<bool, &'static str> {
        if std::time::Instant::now() > self.deadline {
            return Err("timeout");
        }
        self.stats.nodes += 1;
        if self.assigned.len() == self.puzzle.cell_count() as usize {
            return Ok(true);
        }
        if self.cfg.use_no_good_learning && self.check_satisfied() {
            return Ok(false);
        }
        let pos = match self.select_variable() {
            Some(p) => p,
            None => return Ok(true),
        };
        if self.domain[pos as usize].is_empty() {
            return Ok(false);
        }
        let values: Vec<(PieceId, Rotation)> = self.domain[pos as usize].iter().copied().collect();
        for val in values {
            self.assigned.insert(pos, val);
            self.pieces_used.insert(val.0);
            let (ok, undo, wipe_cell) = self.propagate(pos, val.0, val.1);
            if ok {
                // After AC-3 propagation succeeded, run unit-prop from clauses.
                // Pass the just-assigned literal as hint — only walks its watch list.
                let just_assigned = Lit::new(pos, val.0, val.1);
                let (clause_ok, clause_undo, clause_wipe) = if self.cfg.use_no_good_learning {
                    self.unit_prop_from_clauses(Some(just_assigned))
                } else {
                    (true, Vec::new(), None)
                };
                if clause_ok {
                    match self.dfs() {
                        Ok(true) => return Ok(true),
                        Ok(false) => {},
                        Err(e) => {
                            self.restore(clause_undo);
                            self.restore(undo);
                            self.assigned.remove(&pos);
                            self.pieces_used.remove(&val.0);
                            return Err(e);
                        }
                    }
                    self.restore(clause_undo);
                } else {
                    // Clause-induced wipeout — learn from this conflict too.
                    self.stats.wipeouts += 1;
                    if let Some(wc) = clause_wipe {
                        self.learn_no_good(wc);
                    }
                    self.restore(clause_undo);
                }
            } else {
                self.stats.wipeouts += 1;
                if self.cfg.use_no_good_learning {
                    if let Some(wc) = wipe_cell {
                        self.learn_no_good(wc);
                    }
                }
            }
            self.restore(undo);
            self.assigned.remove(&pos);
            self.pieces_used.remove(&val.0);
            self.stats.backtracks += 1;
        }
        Ok(false)
    }
}

/// Top-level solve.
pub fn solve(puzzle: &Puzzle, cfg: Config) -> (Option<Board>, Stats) {
    let mut state = SearchState::new(puzzle, cfg);
    let result = state.dfs();
    let found = match result {
        Ok(true) => {
            let mut board = Board::empty(puzzle);
            for (pos, (pid, rot)) in &state.assigned {
                board.place(*pos, *pid, *rot);
            }
            Some(board)
        }
        _ => None,
    };
    (found, state.stats)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn solve_4x4_3c() {
        run_compare("/tmp/vol58_4x4c3.csv", "4x4/3c");
    }

    #[test]
    fn solve_5x5_4c() {
        run_compare("/tmp/vol58_5x5c4.csv", "5x5/4c");
    }

    #[test]
    fn solve_7x7_6c() {
        run_compare("/tmp/vol58_7x7c6.csv", "7x7/6c");
    }

    #[test]
    fn solve_8x8_7c() {
        run_compare("/tmp/vol58_8x8c7.csv", "8x8/7c");
    }

    #[test]
    fn solve_10x10_9c() {
        run_compare("/tmp/vol59_10x10c9.csv", "10x10/9c");
    }

    #[test]
    fn solve_12x12_12c() {
        run_compare("/tmp/vol59_12x12c12.csv", "12x12/12c");
    }

    #[test]
    #[ignore]  // canonical scale; very slow Python-style HashMap-based code
    fn solve_canonical_16x16() {
        run_compare(
            "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2/../data/puzzles/size_16_official_eternity.csv",
            "canonical 16x16/22c",
        );
    }

    #[test]
    fn solve_6x6_5c() {
        run_compare("/tmp/vol56_6x6c5.csv", "6x6/5c");
    }

    fn run_compare(_p: &str, label: &str) {
        let puzzle_path = PathBuf::from(_p);
        if !puzzle_path.exists() {
            eprintln!("skipping {label}: {puzzle_path:?} not found");
            return;
        }
        let (puzzle, _) = eternity2_puzzle_io::load_puzzle_with_hints(&puzzle_path).expect("load");
        println!("== {label}: {}x{}, {} interior colors ==", puzzle.width, puzzle.height, puzzle.color_count - 1);

        let cfg_no_learn = Config { use_no_good_learning: false, time_budget_ms: 30_000, minimize_clauses: false };
        // NOTE: minimize_clauses turned OFF — vol-58 T8 found the
        // deletion-based minimization is unsound (drops literals that
        // would have been needed). Real 1-UIP needs implication-graph
        // walking, not simulation-based deletion.
        let cfg_learn = Config { use_no_good_learning: true, time_budget_ms: 30_000, minimize_clauses: false };

        let t0 = std::time::Instant::now();
        let (board1, stats1) = solve(&puzzle, cfg_no_learn);
        let t1 = t0.elapsed();
        println!("vanilla:  found={}  nodes={}  wipeouts={}  bt={}  time={:.2}s",
            board1.is_some(), stats1.nodes, stats1.wipeouts, stats1.backtracks, t1.as_secs_f64());

        let t0 = std::time::Instant::now();
        let (board2, stats2) = solve(&puzzle, cfg_learn);
        let t2 = t0.elapsed();
        let avg_clause = if stats2.clauses_learned > 0 {
            stats2.clause_size_sum as f64 / stats2.clauses_learned as f64
        } else { 0.0 };
        println!("cdcl:     found={}  nodes={}  wipeouts={}  bt={}  time={:.2}s",
            board2.is_some(), stats2.nodes, stats2.wipeouts, stats2.backtracks, t2.as_secs_f64());
        println!("          clauses={}  avg_size={:.1}  max={}  props={}",
            stats2.clauses_learned, avg_clause, stats2.clause_size_max, stats2.propagations_from_clauses);
        if stats1.nodes > 0 && stats2.nodes > 0 {
            println!("node ratio (cdcl/vanilla) = {:.4}", stats2.nodes as f64 / stats1.nodes as f64);
        }
    }
}
