// Adaptive Large Neighborhood Search for Eternity II.
//
// Framework: maintain a current board; each iteration picks a "destroy"
// operator from a portfolio (with adaptive weights), uses it to choose
// a subset of cells to free, then calls CP-based repair to find a new
// assignment for those cells. Accept moves under a configurable
// criterion (greedy / simulated-annealing / record-to-record).
//
// Operator portfolio:
//   - RandomRegion(k): free a uniform-random k×k window.
//   - WorstWindow(k):  free the k×k window with lowest matched-edge
//                      density (analog of vol. 2's `worst_region_repair`).
//   - ConflictDriven:  seed at a random mismatched edge; BFS-grow the
//                      free set through 4-adjacency until size cap.
//   - MwpmDefectPair:  build the mismatched-edge graph; min-weight
//                      matching; destroy-set = union of cells on
//                      shortest paths between matched defect pairs.
//                      (See RESEARCH_NOTES_4 SESSION 2 plan for the
//                      derivation — this is a destroy-set heuristic,
//                      not a correction algorithm.)
//
// Adaptive weights follow Ropke & Pisinger 2006: each operator earns
// reward σ1 for a new best, σ2 for an improving accepted move, σ3 for
// a non-improving accepted move, σ4 (=0) for a rejected move. Every
// `segment_iters` iterations, weights = (1-r)·old + r·(reward/count).

use std::collections::{BTreeSet, VecDeque};

use eternity2_core::{Board, Hint, Hints, PieceId, Position, Puzzle, BORDER};
use eternity2_events::BufferSink;
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

use crate::repair::repair_region; // not directly used, but signals intent
use crate::pt;                     // re-use Rng/scoring conventions
use crate::{run_sa_from, SaConfig}; // SA-based repair (CP-free)

// ----- Rng (small reproducible PRNG, splitmix64) -----------------------

#[derive(Clone)]
pub struct AlnsRng { state: u64 }

impl AlnsRng {
    pub fn new(seed: u64) -> Self { Self { state: seed.wrapping_add(0x9E37_79B9_7F4A_7C15) } }
    pub fn next_u64(&mut self) -> u64 {
        let mut z = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        self.state = z;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    pub fn next_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / ((1u64 << 53) as f64)
    }
    pub fn range(&mut self, n: u32) -> u32 {
        if n == 0 { 0 } else { (self.next_u64() % (n as u64)) as u32 }
    }
}

// ----- Scoring helpers --------------------------------------------------

/// Vol-16 — was `iter().find` (O(n)). Now delegates to the O(1) lookup
/// on Puzzle. Inlined so score_board's hot loop sees a single load.
#[inline]
fn lookup_piece<'a>(puzzle: &'a Puzzle, id: PieceId) -> Option<&'a eternity2_core::Piece> {
    puzzle.piece(id)
}

pub fn score_board(puzzle: &Puzzle, board: &Board) -> u32 {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut matches = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue };
            let Some(p) = lookup_piece(puzzle, pid) else { continue };
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup_piece(puzzle, rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        if e[1] == re[3] && e[1] != BORDER && e[1] != 0 { matches += 1; }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        if e[2] == be[0] && e[2] != BORDER && e[2] != 0 { matches += 1; }
                    }
                }
            }
        }
    }
    matches
}

// ----- Mismatch enumeration --------------------------------------------

#[derive(Debug, Clone, Copy)]
pub struct Mismatch {
    pub cell_a: Position,
    pub cell_b: Position,
    pub horizontal: bool,
}

pub fn find_mismatches(puzzle: &Puzzle, board: &Board) -> Vec<Mismatch> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut out = Vec::new();
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue };
            let Some(p) = lookup_piece(puzzle, pid) else { continue };
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup_piece(puzzle, rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        let (ca, cb) = (e[1], re[3]);
                        if ca != BORDER && cb != BORDER && ca != 0 && cb != 0 && ca != cb {
                            out.push(Mismatch { cell_a: pos, cell_b: pos + 1, horizontal: true });
                        }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        let (ca, cb) = (e[2], be[0]);
                        if ca != BORDER && cb != BORDER && ca != 0 && cb != 0 && ca != cb {
                            out.push(Mismatch { cell_a: pos, cell_b: pos + w, horizontal: false });
                        }
                    }
                }
            }
        }
    }
    out
}

// ----- CP repair on an arbitrary free-set -------------------------------

/// Repair strategy used after a destroy operator chooses a free-set.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RepairKind {
    /// Cell-CP: pin non-free cells as Hints, let the engine reconstruct
    /// the free region. Fast when feasible. ABORTS on plateau states
    /// because AC3 wipes — see RESEARCH_NOTES_4 vol. 4 F2 finding.
    Cp,
    /// Simulated annealing: pin non-free cells, run SA's random swap/
    /// rotate moves on the free cells. Does NOT propagate
    /// arc-consistency, so works on plateau states where CP fails.
    /// Cheaper per attempt but doesn't enumerate all completions.
    Sa,
}

/// Pin every cell EXCEPT `free_set` as a Hint; run cell-CP for `budget_ms`.
/// Returns the new board iff CP fills the free set; otherwise `None`.
pub fn cp_repair(
    puzzle: &Puzzle,
    board: &Board,
    free_set: &BTreeSet<Position>,
    budget_ms: u64,
) -> Option<Board> {
    let n_cells = puzzle.cell_count();
    let mut hs: Vec<Hint> = Vec::with_capacity((n_cells as usize).saturating_sub(free_set.len()));
    for pos in 0..n_cells {
        if free_set.contains(&pos) { continue; }
        if let Some((pid, rot)) = board.get(pos) {
            hs.push(Hint { position: pos, piece_id: pid, rotation: rot });
        }
    }
    let hints = Hints::new(hs);

    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.hints = hints;

    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let new_board = match outcome {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::TimedOut { best_partial, .. } | SolveOutcome::Cancelled { best_partial, .. } => best_partial,
        SolveOutcome::Exhausted | SolveOutcome::Error(_) => return None,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next()?,
    };

    for &pos in free_set {
        if new_board.get(pos).is_none() { return None; }
    }
    Some(new_board)
}

/// SA-based repair: pin non-free cells, run SA on the free cells for
/// `budget_ms`. The free cells already have pieces from `board`; SA
/// just shuffles them via random swaps and rotations.
///
/// Falls back here when CP repair fails (AC3 wipeout on plateau states).
/// Less expressive than CP — won't enumerate all completions — but
/// always returns a board because the pinned-cell scheme bypasses
/// arc-consistency entirely.
pub fn sa_repair(
    puzzle: &Puzzle,
    board: &Board,
    free_set: &BTreeSet<Position>,
    budget_ms: u64,
    seed: u64,
) -> Board {
    let n_cells = puzzle.cell_count();
    let mut pinned: Vec<Position> = Vec::with_capacity((n_cells as usize).saturating_sub(free_set.len()));
    for pos in 0..n_cells {
        if !free_set.contains(&pos) { pinned.push(pos); }
    }
    let mut cfg = SaConfig::default();
    cfg.time_budget_ms = budget_ms;
    cfg.seed = seed;
    cfg.pinned_positions = pinned;
    // Keep cooling fast for short repair bursts.
    cfg.cooling_period = 500;
    let out = run_sa_from(puzzle, board, &cfg);
    out.best_board
}

/// Dispatch on RepairKind. Returns `Some(board)` whenever a repair
/// completes; CP can fail (returns None), SA always succeeds.
pub fn repair(
    puzzle: &Puzzle,
    board: &Board,
    free_set: &BTreeSet<Position>,
    budget_ms: u64,
    kind: RepairKind,
    seed: u64,
) -> Option<Board> {
    match kind {
        RepairKind::Cp => cp_repair(puzzle, board, free_set, budget_ms),
        RepairKind::Sa => Some(sa_repair(puzzle, board, free_set, budget_ms, seed)),
    }
}

// ----- Destroy operators ------------------------------------------------

pub trait DestroyOp {
    fn name(&self) -> &str;
    fn destroy(&mut self, puzzle: &Puzzle, board: &Board, rng: &mut AlnsRng) -> BTreeSet<Position>;
}

pub struct RandomRegion { pub k: u32 }
impl DestroyOp for RandomRegion {
    fn name(&self) -> &str { "random_region" }
    fn destroy(&mut self, puzzle: &Puzzle, _board: &Board, rng: &mut AlnsRng) -> BTreeSet<Position> {
        let w = puzzle.width;
        let h = puzzle.height;
        let k = self.k.min(w).min(h);
        let x0 = rng.range(w.saturating_sub(k) + 1);
        let y0 = rng.range(h.saturating_sub(k) + 1);
        let mut s = BTreeSet::new();
        for dy in 0..k {
            for dx in 0..k {
                s.insert((y0 + dy) * w + (x0 + dx));
            }
        }
        s
    }
}

pub struct WorstWindow { pub k: u32 }
impl DestroyOp for WorstWindow {
    fn name(&self) -> &str { "worst_window" }
    fn destroy(&mut self, puzzle: &Puzzle, board: &Board, _rng: &mut AlnsRng) -> BTreeSet<Position> {
        let w = puzzle.width;
        let h = puzzle.height;
        let k = self.k.min(w).min(h);
        // Score per cell: # matched edges incident. Window score = sum.
        let mut cell_match = vec![0u32; (w * h) as usize];
        for y in 0..h {
            for x in 0..w {
                let pos = y * w + x;
                let Some((pid, rot)) = board.get(pos) else { continue };
                let Some(p) = lookup_piece(puzzle, pid) else { continue };
                let e = p.edges.rotated(rot).as_array();
                if x + 1 < w {
                    if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                        if let Some(rp) = lookup_piece(puzzle, rpid) {
                            let re = rp.edges.rotated(rrot).as_array();
                            if e[1] == re[3] && e[1] != BORDER && e[1] != 0 {
                                cell_match[pos as usize] += 1;
                                cell_match[(y * w + (x + 1)) as usize] += 1;
                            }
                        }
                    }
                }
                if y + 1 < h {
                    if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                        if let Some(bp) = lookup_piece(puzzle, bpid) {
                            let be = bp.edges.rotated(brot).as_array();
                            if e[2] == be[0] && e[2] != BORDER && e[2] != 0 {
                                cell_match[pos as usize] += 1;
                                cell_match[((y + 1) * w + x) as usize] += 1;
                            }
                        }
                    }
                }
            }
        }
        let mut best = (u32::MAX, 0u32, 0u32);
        for y0 in 0..=(h.saturating_sub(k)) {
            for x0 in 0..=(w.saturating_sub(k)) {
                let mut s = 0u32;
                for dy in 0..k {
                    for dx in 0..k {
                        s += cell_match[((y0 + dy) * w + (x0 + dx)) as usize];
                    }
                }
                if s < best.0 { best = (s, x0, y0); }
            }
        }
        let mut out = BTreeSet::new();
        for dy in 0..k {
            for dx in 0..k {
                out.insert((best.2 + dy) * w + (best.1 + dx));
            }
        }
        out
    }
}

pub struct ConflictDriven { pub max_size: u32 }
impl DestroyOp for ConflictDriven {
    fn name(&self) -> &str { "conflict_driven" }
    fn destroy(&mut self, puzzle: &Puzzle, board: &Board, rng: &mut AlnsRng) -> BTreeSet<Position> {
        let mismatches = find_mismatches(puzzle, board);
        if mismatches.is_empty() {
            // Nothing wrong to anchor on; fall back to a random region.
            return RandomRegion { k: 4 }.destroy(puzzle, board, rng);
        }
        // Pick a random mismatch as the seed.
        let m = mismatches[(rng.range(mismatches.len() as u32)) as usize];
        let w = puzzle.width;
        let h = puzzle.height;
        let mut s = BTreeSet::new();
        let mut q: VecDeque<Position> = VecDeque::new();
        s.insert(m.cell_a); q.push_back(m.cell_a);
        s.insert(m.cell_b); q.push_back(m.cell_b);
        // Grow via 4-adjacency until size cap.
        while let Some(p) = q.pop_front() {
            if s.len() as u32 >= self.max_size { break; }
            let x = p % w;
            let y = p / w;
            // Random shuffle of 4 neighbors so growth isn't directional.
            let mut nbrs: [(i32, i32); 4] = [(1, 0), (-1, 0), (0, 1), (0, -1)];
            for i in 0..4 {
                let j = (rng.range(4 - i as u32) + i as u32) as usize;
                nbrs.swap(i, j);
            }
            for (dx, dy) in &nbrs {
                let nx = x as i32 + dx;
                let ny = y as i32 + dy;
                if nx < 0 || ny < 0 || nx as u32 >= w || ny as u32 >= h { continue; }
                let np = ny as u32 * w + nx as u32;
                if s.insert(np) {
                    q.push_back(np);
                    if s.len() as u32 >= self.max_size { break; }
                }
            }
        }
        s
    }
}

// MWPM destroy: see RESEARCH_NOTES_4 SESSION 2 plan for derivation. We
// build the mismatched-edge graph (nodes = mismatched interior edges),
// compute pairwise Manhattan distance between defect midpoints, run
// min-weight matching. Destroy-set = union of cells on the shortest
// cell-paths between matched defect pairs.
//
// For small N (≈30-60 defects) we use a brute-force / greedy matching
// (sufficient quality at this scale; exact blossom is a future
// optimization). For "weight" we use the L1 distance between defect
// cell-pair midpoints.
pub struct MwpmDefectPair { pub max_pairs: u32 }

impl MwpmDefectPair {
    fn defect_midpoint(m: &Mismatch, w: u32) -> (i32, i32) {
        // Midpoint of the edge between cell_a and cell_b. Use 2× scale
        // to stay in integers: cell (x,y) → (2x+1, 2y+1).
        let ax = (m.cell_a % w) as i32;
        let ay = (m.cell_a / w) as i32;
        let bx = (m.cell_b % w) as i32;
        let by = (m.cell_b / w) as i32;
        (ax + bx, ay + by) // 2× midpoint (integer)
    }

    /// Greedy matching: repeatedly pick the closest unpaired pair.
    /// Returns vec of (i, j) index pairs in the input array.
    fn greedy_matching(midpoints: &[(i32, i32)], max_pairs: u32) -> Vec<(usize, usize)> {
        let n = midpoints.len();
        if n < 2 { return Vec::new(); }
        // Precompute pairwise distances.
        let mut edges: Vec<(i32, usize, usize)> = Vec::with_capacity(n * (n - 1) / 2);
        for i in 0..n {
            for j in (i + 1)..n {
                let d = (midpoints[i].0 - midpoints[j].0).abs() + (midpoints[i].1 - midpoints[j].1).abs();
                edges.push((d, i, j));
            }
        }
        edges.sort_unstable_by_key(|e| e.0);
        let mut matched = vec![false; n];
        let mut pairs = Vec::new();
        for (_, i, j) in edges {
            if pairs.len() as u32 >= max_pairs { break; }
            if !matched[i] && !matched[j] {
                matched[i] = true;
                matched[j] = true;
                pairs.push((i, j));
            }
        }
        pairs
    }

    /// Cells on the shortest L1-path between two cells (Bresenham-style).
    /// We return a 1-cell-wide path; widening to a small "tube" gives CP
    /// more room.
    fn cells_on_path(a: Position, b: Position, w: u32) -> Vec<Position> {
        let mut out = Vec::new();
        let (mut x, mut y) = ((a % w) as i32, (a / w) as i32);
        let (bx, by) = ((b % w) as i32, (b / w) as i32);
        out.push(a);
        while (x, y) != (bx, by) {
            if x < bx { x += 1; }
            else if x > bx { x -= 1; }
            else if y < by { y += 1; }
            else { y -= 1; }
            out.push(y as u32 * w + x as u32);
        }
        out
    }
}

impl DestroyOp for MwpmDefectPair {
    fn name(&self) -> &str { "mwpm_defect_pair" }
    fn destroy(&mut self, puzzle: &Puzzle, board: &Board, rng: &mut AlnsRng) -> BTreeSet<Position> {
        let mismatches = find_mismatches(puzzle, board);
        if mismatches.len() < 2 {
            return RandomRegion { k: 4 }.destroy(puzzle, board, rng);
        }
        let w = puzzle.width;
        let midpoints: Vec<(i32, i32)> = mismatches.iter().map(|m| Self::defect_midpoint(m, w)).collect();
        let pairs = Self::greedy_matching(&midpoints, self.max_pairs);

        let mut s = BTreeSet::new();
        for (i, j) in pairs {
            // Pick a representative cell on each side of each defect:
            // use cell_a of mismatch i and cell_a of mismatch j as the
            // path endpoints. (Either endpoint of either defect works
            // — we just need a route through the relevant region.)
            let a = mismatches[i].cell_a;
            let b = mismatches[j].cell_a;
            for c in Self::cells_on_path(a, b, w) { s.insert(c); }
            // Also include both endpoints' "other side" so the defect's
            // two cells are both freed.
            s.insert(mismatches[i].cell_b);
            s.insert(mismatches[j].cell_b);
        }
        s
    }
}

/// Vol-17 — destroy a full horizontal band of `k_rows` adjacent rows
/// chosen to maximize the count of mismatched edges falling inside.
/// Motivated by the vol-17 calibrated_v17a 447 board where ALL 33
/// mismatches concentrated in rows 0-3 forming one 51-cell connected
/// component — bigger than any of the k≤30 destroy ops can swallow.
/// Pair with `RepairKind::Cp` to let the engine search-fill the band
/// against the now-pinned bottom 12 rows. Pinned positions (canonical
/// hints) inside the band are still respected upstream.
pub struct WorstBand {
    /// Width of the band in rows. For 16×16 canonical E2, 4 captures
    /// the observed cluster; values up to 6-8 are reasonable.
    pub k_rows: u32,
}
impl DestroyOp for WorstBand {
    fn name(&self) -> &str { "worst_band" }
    fn destroy(&mut self, puzzle: &Puzzle, board: &Board, _rng: &mut AlnsRng) -> BTreeSet<Position> {
        let w = puzzle.width;
        let h = puzzle.height;
        let k = self.k_rows.min(h).max(1);
        // Per-row mismatch count = sum over interior edges incident on row y
        // that are mismatched.
        let mismatches = find_mismatches(puzzle, board);
        let mut per_row = vec![0u32; h as usize];
        for m in &mismatches {
            let ya = m.cell_a / w;
            let yb = m.cell_b / w;
            per_row[ya as usize] += 1;
            if yb != ya { per_row[yb as usize] += 1; }
        }
        // Window of k consecutive rows with max total mismatches.
        let mut best = (0u32, 0u32); // (score, y_start)
        for y0 in 0..=(h.saturating_sub(k)) {
            let mut s = 0u32;
            for dy in 0..k { s += per_row[(y0 + dy) as usize]; }
            if s > best.0 { best = (s, y0); }
        }
        // If no mismatches at all, default to a top band so the repair
        // explores SOMETHING (rather than empty set causing a no-op).
        let y_start = if best.0 == 0 { 0 } else { best.1 };
        let mut out = BTreeSet::new();
        for dy in 0..k {
            let y = y_start + dy;
            for x in 0..w {
                out.insert(y * w + x);
            }
        }
        out
    }
}

/// Vol-17 NOVEL — destroy a single ROW (1 × W = 16 cells) whose
/// mismatch density is the worst. Smaller than WorstBand{4} but still
/// touches the entire row, allowing piece-uniqueness across a thin
/// strip to be re-optimised.
///
/// Useful as a "scalpel" complement to the bigger WorstBand: probe
/// individual rows of the cluster, each of which is a tractable
/// 16-cell CP-repair problem.
pub struct WorstRow;

impl DestroyOp for WorstRow {
    fn name(&self) -> &str { "worst_row" }
    fn destroy(&mut self, puzzle: &Puzzle, board: &Board, _rng: &mut AlnsRng) -> BTreeSet<Position> {
        let w = puzzle.width;
        let h = puzzle.height;
        let mismatches = find_mismatches(puzzle, board);
        let mut per_row = vec![0u32; h as usize];
        for m in &mismatches {
            per_row[(m.cell_a / w) as usize] += 1;
            let yb = m.cell_b / w;
            if yb != m.cell_a / w { per_row[yb as usize] += 1; }
        }
        let mut best_row = 0u32;
        let mut best_score = 0u32;
        for y in 0..h {
            if per_row[y as usize] > best_score {
                best_score = per_row[y as usize];
                best_row = y;
            }
        }
        let mut out = BTreeSet::new();
        for x in 0..w {
            out.insert(best_row * w + x);
        }
        out
    }
}

/// Vol-17 NOVEL — destroy the ENTIRE connected component of mismatched
/// cells, no matter how big. Adjacent (4-neighbour) cells that both
/// touch at least one mismatch are part of the same component.
///
/// Differs from `ConflictDriven { max_size }`: that one BFS-grows from
/// a random mismatch with a fixed size cap, so it can miss the larger
/// component or stop short of bridges. ComponentDestroy explicitly
/// computes the connected-component closure and frees ALL of it.
///
/// For boards with one big component (vol-17 calibrated_v17a 447:
/// 51 cells in one component) this exactly matches the cluster size,
/// which neither ConflictDriven{30} nor ConflictDriven{80} can do —
/// 30 misses cells and 80 over-includes harmless cells.
///
/// Cost: O(W*H) BFS per call. Negligible vs CP-repair budget.
pub struct ComponentDestroy {
    /// Skip if component size > this. ALNS can't usefully repair a
    /// 200-cell free region in 1.5s; bail out and let other ops try.
    /// Set to a high value (e.g. n_cells) to never bail.
    pub max_size: u32,
    /// Lower bound on component size to bother destroying. A
    /// 2-cell component is just one mismatched edge — RandomRegion
    /// handles that better. Default 6.
    pub min_size: u32,
}

impl DestroyOp for ComponentDestroy {
    fn name(&self) -> &str { "component_destroy" }
    fn destroy(&mut self, puzzle: &Puzzle, board: &Board, rng: &mut AlnsRng) -> BTreeSet<Position> {
        let w = puzzle.width;
        let h = puzzle.height;
        let mismatches = find_mismatches(puzzle, board);
        if mismatches.is_empty() {
            return RandomRegion { k: 4 }.destroy(puzzle, board, rng);
        }
        // Build set of cells that touch a mismatched edge.
        let mut mismatch_cells: std::collections::BTreeSet<Position> = std::collections::BTreeSet::new();
        for m in &mismatches {
            mismatch_cells.insert(m.cell_a);
            mismatch_cells.insert(m.cell_b);
        }
        // BFS components.
        let mut visited: std::collections::BTreeSet<Position> = std::collections::BTreeSet::new();
        let mut components: Vec<Vec<Position>> = Vec::new();
        for &start in &mismatch_cells {
            if visited.contains(&start) { continue; }
            let mut comp = Vec::new();
            let mut queue: VecDeque<Position> = VecDeque::new();
            queue.push_back(start);
            visited.insert(start);
            while let Some(p) = queue.pop_front() {
                comp.push(p);
                let x = p % w; let y = p / w;
                let mut nbrs: Vec<Position> = Vec::new();
                if x + 1 < w { nbrs.push(p + 1); }
                if x > 0 { nbrs.push(p - 1); }
                if y + 1 < h { nbrs.push(p + w); }
                if y > 0 { nbrs.push(p - w); }
                for n in nbrs {
                    if mismatch_cells.contains(&n) && !visited.contains(&n) {
                        visited.insert(n);
                        queue.push_back(n);
                    }
                }
            }
            components.push(comp);
        }
        // Select the largest component that fits within [min_size, max_size].
        components.sort_by_key(|c| std::cmp::Reverse(c.len()));
        for comp in &components {
            let n = comp.len() as u32;
            if n >= self.min_size && n <= self.max_size {
                return comp.iter().copied().collect();
            }
        }
        // No suitable component: fall back to ConflictDriven.
        ConflictDriven { max_size: 30 }.destroy(puzzle, board, rng)
    }
}

/// Vol-17 NOVEL — destroy a connected component of mismatched cells
/// AND a 1-cell border around it, so the CP-repair has neighbouring
/// free cells to rotate into matching positions. Useful when the
/// component is fully surrounded by matched cells whose edge-pieces
/// are themselves involved (so re-rotating those edges may help).
pub struct ComponentPlusHaloDestroy {
    pub max_size: u32,
    pub min_size: u32,
}

impl DestroyOp for ComponentPlusHaloDestroy {
    fn name(&self) -> &str { "component_plus_halo" }
    fn destroy(&mut self, puzzle: &Puzzle, board: &Board, rng: &mut AlnsRng) -> BTreeSet<Position> {
        // Reuse ComponentDestroy.
        let core = ComponentDestroy { max_size: self.max_size, min_size: self.min_size }
            .destroy(puzzle, board, rng);
        if core.is_empty() { return core; }
        let w = puzzle.width;
        let h = puzzle.height;
        let mut out = core.clone();
        for &p in &core {
            let x = p % w; let y = p / w;
            if x + 1 < w { out.insert(p + 1); }
            if x > 0 { out.insert(p - 1); }
            if y + 1 < h { out.insert(p + w); }
            if y > 0 { out.insert(p - w); }
        }
        out
    }
}

// ----- Acceptance criterion --------------------------------------------

#[derive(Debug, Clone, Copy)]
pub enum Acceptance {
    Greedy,
    SimulatedAnnealing { t: f64 },
    RecordToRecord { deviation: f64 },
}

impl Acceptance {
    pub fn accept(&self, delta: i32, rng: &mut AlnsRng, best_score: u32, new_score: u32) -> bool {
        match self {
            Acceptance::Greedy => delta > 0,
            Acceptance::SimulatedAnnealing { t } => {
                if delta >= 0 { return true; }
                let p = (delta as f64 / t).exp();
                rng.next_f64() < p
            }
            Acceptance::RecordToRecord { deviation } => {
                (new_score as f64) >= (best_score as f64) - deviation
            }
        }
    }
}

// ----- Adaptive operator weights ---------------------------------------

#[derive(Debug, Clone)]
pub struct AdaptiveWeights {
    weights: Vec<f64>,
    segment_reward: Vec<f64>,
    segment_count: Vec<u32>,
    decay: f64,
    pub sigma_new_best: f64,    // σ1
    pub sigma_improve: f64,     // σ2
    pub sigma_accept_worse: f64, // σ3
    pub sigma_reject: f64,      // σ4
}

impl AdaptiveWeights {
    pub fn uniform(n: usize) -> Self {
        Self {
            weights: vec![1.0; n],
            segment_reward: vec![0.0; n],
            segment_count: vec![0; n],
            decay: 0.1,
            sigma_new_best: 33.0,
            sigma_improve: 9.0,
            sigma_accept_worse: 13.0,
            sigma_reject: 0.0,
        }
    }

    pub fn select(&self, rng: &mut AlnsRng) -> usize {
        let total: f64 = self.weights.iter().sum();
        let r = rng.next_f64() * total;
        let mut acc = 0.0;
        for (i, w) in self.weights.iter().enumerate() {
            acc += w;
            if r < acc { return i; }
        }
        self.weights.len() - 1
    }

    pub fn reward(&mut self, op_idx: usize, sigma: f64) {
        self.segment_reward[op_idx] += sigma;
        self.segment_count[op_idx] += 1;
    }

    pub fn update_weights(&mut self) {
        for i in 0..self.weights.len() {
            if self.segment_count[i] > 0 {
                let avg_reward = self.segment_reward[i] / (self.segment_count[i] as f64);
                self.weights[i] = (1.0 - self.decay) * self.weights[i] + self.decay * avg_reward;
            } else {
                // No samples this segment — gentle decay toward floor.
                self.weights[i] = self.weights[i] * (1.0 - self.decay * 0.5);
            }
            self.weights[i] = self.weights[i].max(0.01); // never let it go to zero
            self.segment_reward[i] = 0.0;
            self.segment_count[i] = 0;
        }
    }

    pub fn weights(&self) -> &[f64] { &self.weights }
}

// ----- ALNS config + driver --------------------------------------------

pub struct AlnsConfig {
    pub time_budget_ms: u64,
    pub repair_budget_ms: u64,
    pub acceptance: Acceptance,
    pub segment_iters: u32,
    pub seed: u64,
    pub verbose: bool,
    /// Primary repair kind. Default: SA (works on plateau states).
    pub repair: RepairKind,
    /// If `repair == Cp` and CP fails, retry once with SA. Default true.
    pub cp_fallback_to_sa: bool,
    /// Cell positions that destroy operators are not allowed to free.
    /// Used to keep the 5 canonical E2 hints pinned during ALNS. Empty
    /// = unconstrained (legacy vol-12 behaviour — score is then *not*
    /// the official canonical-E2 score). Set this to
    /// `hints.iter().map(|h| h.position).collect()` for canonical
    /// scoring. Fixed in vol-14 after discovering canonical hints
    /// were being swapped out, invalidating the 443/480 score.
    pub pinned_positions: Vec<Position>,
}

impl Default for AlnsConfig {
    fn default() -> Self {
        Self {
            time_budget_ms: 600_000,
            repair_budget_ms: 500,
            acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
            segment_iters: 50,
            seed: 0xA1_A2_A3_A4,
            verbose: false,
            repair: RepairKind::Sa,
            cp_fallback_to_sa: true,
            pinned_positions: Vec::new(),
        }
    }
}

pub struct AlnsStats {
    pub iters: u32,
    pub repair_failures: u32,
    pub accepted_improving: u32,
    pub accepted_worse: u32,
    pub rejected: u32,
    pub per_op_accepts: Vec<u32>,
    pub per_op_invocations: Vec<u32>,
    pub op_names: Vec<String>,
    pub best_score_history: Vec<(u32, u32)>, // (iter, score) on each new best
}

pub fn run_alns(
    puzzle: &Puzzle,
    initial: &Board,
    ops: &mut [Box<dyn DestroyOp>],
    cfg: &AlnsConfig,
) -> (Board, AlnsStats) {
    let mut rng = AlnsRng::new(cfg.seed);
    let mut weights = AdaptiveWeights::uniform(ops.len());
    let mut current = initial.clone();
    let mut current_score = score_board(puzzle, &current);
    let mut best = current.clone();
    let mut best_score = current_score;

    let mut stats = AlnsStats {
        iters: 0, repair_failures: 0,
        accepted_improving: 0, accepted_worse: 0, rejected: 0,
        per_op_accepts: vec![0; ops.len()],
        per_op_invocations: vec![0; ops.len()],
        op_names: ops.iter().map(|o| o.name().to_string()).collect(),
        best_score_history: vec![(0, best_score)],
    };

    let t_start = std::time::Instant::now();
    let mut last_log = t_start;

    let pinned_set: BTreeSet<Position> = cfg.pinned_positions.iter().copied().collect();

    while t_start.elapsed().as_millis() < cfg.time_budget_ms as u128 {
        stats.iters += 1;
        let op_idx = weights.select(&mut rng);
        stats.per_op_invocations[op_idx] += 1;

        let mut free_set = ops[op_idx].destroy(puzzle, &current, &mut rng);
        // Vol-14 fix: pinned positions are never freed by destroy operators.
        // Without this, canonical E2 hints get swapped out and the reported
        // score is for a different puzzle.
        if !pinned_set.is_empty() {
            for p in &pinned_set { free_set.remove(p); }
        }
        if free_set.is_empty() { continue; }

        // Iteration-specific seed so SA repairs don't all walk the same path.
        let iter_seed = cfg.seed ^ ((stats.iters as u64).wrapping_mul(0xDEADBEEFCAFE0001));
        let new_board = match repair(puzzle, &current, &free_set, cfg.repair_budget_ms, cfg.repair, iter_seed) {
            Some(b) => b,
            None => {
                if cfg.repair == RepairKind::Cp && cfg.cp_fallback_to_sa {
                    match repair(puzzle, &current, &free_set, cfg.repair_budget_ms, RepairKind::Sa, iter_seed) {
                        Some(b) => b,
                        None => { stats.repair_failures += 1; continue; }
                    }
                } else { stats.repair_failures += 1; continue; }
            }
        };
        let new_score = score_board(puzzle, &new_board);
        let delta = new_score as i32 - current_score as i32;

        let accepted = cfg.acceptance.accept(delta, &mut rng, best_score, new_score);
        let mut sigma = weights.sigma_reject;
        if accepted {
            stats.per_op_accepts[op_idx] += 1;
            current = new_board;
            current_score = new_score;
            if new_score > best_score {
                best = current.clone();
                best_score = new_score;
                stats.best_score_history.push((stats.iters, best_score));
                sigma = weights.sigma_new_best;
            } else if delta > 0 {
                sigma = weights.sigma_improve;
                stats.accepted_improving += 1;
            } else {
                sigma = weights.sigma_accept_worse;
                stats.accepted_worse += 1;
            }
        } else {
            stats.rejected += 1;
        }
        weights.reward(op_idx, sigma);

        if stats.iters % cfg.segment_iters == 0 {
            weights.update_weights();
            if cfg.verbose && last_log.elapsed().as_secs() >= 2 {
                eprintln!("[ALNS iter {}] t={:.1}s best={} current={} op_weights={:?}",
                    stats.iters,
                    t_start.elapsed().as_secs_f64(),
                    best_score, current_score,
                    weights.weights().iter().map(|w| format!("{:.2}", w)).collect::<Vec<_>>());
                last_log = std::time::Instant::now();
            }
        }
    }

    (best, stats)
}

// Re-export so the binary doesn't need to know internal modules.
pub use AlnsConfig as Config;

// Suppress dead-code warnings for items we deliberately keep public.
#[allow(dead_code)]
fn _force_referenced_items() {
    let _ = repair_region;
    let _ = pt::PtConfig::default();
}
