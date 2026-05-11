// Eternity-II local-search engine. Implements simulated annealing
// over the space of complete piece placements, with five neighborhood
// operators inspired by Wauters et al. META'10 ("Guide-and-Observe
// Hyper-Heuristic"). The objective is matching-edge count; secondary
// objectives (color frequency balance) break ties during selection.
//
// Why local search? CP backtracking (our solver-engine) plateaus in
// the "Goldilocks zone" of constraint density on hard instances. The
// only published technique reaching 461+/480 on real Eternity II is a
// metaheuristic of this shape (Wauters; Verhaard's 467 is closer to
// portfolio CP+heuristics, with different ingredients we keep separate).
//
// Design notes:
//   - We operate on a fully-placed board (no holes). Initial state is
//     a greedy random placement; iteratively we improve.
//   - State carries scoring caches so that neighborhood moves update
//     the score in O(neighbours_touched) rather than O(board).
//   - Borders are constrained: corner-pieces only go to corner cells,
//     edge-pieces only to non-corner border cells, interiors to
//     interiors. Moves that violate this are rejected up-front.
//
// What is NOT here yet:
//   - The integration with eternity2-solver-engine (CP-then-LS hybrid).
//   - Distributed restarts.

#![forbid(unsafe_code)]

use eternity2_core::{
    Board, Color, PieceId, Position, Puzzle, Rotation, BORDER,
};

/// Configuration for the simulated-annealing local search.
#[derive(Debug, Clone, Copy)]
pub struct SaConfig {
    /// Initial temperature. Wauters et al. used 5000 for E2 specifically.
    pub temperature_start: f64,
    /// Lower bound on temperature; search stops or restarts here.
    pub temperature_min: f64,
    /// Geometric cooling factor applied each `cooling_period` steps.
    pub cooling: f64,
    /// Number of accepted+rejected moves between cooling steps.
    pub cooling_period: u64,
    /// Hard cap on number of iterations (0 = unlimited).
    pub max_iters: u64,
    /// Optional wall-clock budget in milliseconds (0 = unlimited).
    pub time_budget_ms: u64,
    /// PRNG seed for reproducibility.
    pub seed: u64,
}

impl Default for SaConfig {
    fn default() -> Self {
        // T_start picked so a single-edge loss (delta = -1) is accepted
        // with p ≈ 0.6 initially (exp(-1/2)) and dropping toward 0.5
        // after a few hundred cooling steps. Wauters et al. report
        // T_start=5000 but they aggregate multiple objectives; for
        // pure edge-match (delta ∈ [-8, +8] per swap) that would be
        // ~random walk. We use a delta-calibrated scale here.
        Self {
            temperature_start: 2.0,
            temperature_min: 0.05,
            cooling: 0.999,
            cooling_period: 5000,
            max_iters: 0,
            time_budget_ms: 0,
            seed: 0xE2_E2_E2_E2,
        }
    }
}

/// Outcome of a local-search run.
#[derive(Debug, Clone)]
pub struct SaOutcome {
    /// Best board encountered (may equal final or be an earlier snapshot).
    pub best_board: Board,
    /// Number of edges matched in `best_board`.
    pub best_score: u32,
    /// Total interior edges (denominator for `best_score`).
    pub total_edges: u32,
    /// Iterations performed (accepted + rejected combined).
    pub iterations: u64,
    /// Wall-clock microseconds of the run.
    pub elapsed_us: u128,
}

// ============================================================
// Static piece-classification by border-edge count, used to keep
// moves on-class (corner ⇆ corner only, etc).
// ============================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CellClass {
    Corner,
    Edge,
    Interior,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PieceClass {
    Corner,  // 2 BORDER edges
    Edge,    // 1 BORDER edge
    Interior, // 0 BORDER edges
}

fn classify_cell(puzzle: &Puzzle, pos: Position) -> CellClass {
    let mask = puzzle.border_mask(pos);
    let n_border = mask.iter().filter(|b| **b).count();
    match n_border {
        2 => CellClass::Corner,
        1 => CellClass::Edge,
        _ => CellClass::Interior,
    }
}

fn classify_piece(piece_edges: [Color; 4]) -> PieceClass {
    let n_border = piece_edges.iter().filter(|c| **c == BORDER).count();
    match n_border {
        2 => PieceClass::Corner,
        1 => PieceClass::Edge,
        _ => PieceClass::Interior,
    }
}

fn cell_class_matches(c: CellClass, p: PieceClass) -> bool {
    matches!(
        (c, p),
        (CellClass::Corner, PieceClass::Corner)
            | (CellClass::Edge, PieceClass::Edge)
            | (CellClass::Interior, PieceClass::Interior)
    )
}

// ============================================================
// SplitMix64 PRNG (same family as the generator crate uses).
// ============================================================

#[derive(Debug, Clone, Copy)]
struct Rng(u64);

impl Rng {
    fn new(seed: u64) -> Self { Self(seed.wrapping_add(0x9E37_79B9_7F4A_7C15)) }
    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn gen_range(&mut self, n: u32) -> u32 {
        if n == 0 { return 0; }
        (self.next_u64() % u64::from(n)) as u32
    }
    fn next_f64(&mut self) -> f64 {
        // Generate a double in [0, 1).
        let bits = self.next_u64() >> 11;
        (bits as f64) * (1.0 / ((1u64 << 53) as f64))
    }
}

// ============================================================
// Run-time state
// ============================================================

struct State<'a> {
    puzzle: &'a Puzzle,
    // For each piece-id × rotation, the rotated edges. Indexed
    // as `[piece_id*4 + rot]`. Cached at construction to keep the
    // inner loop hot.
    piece_rot_edges: Vec<[Color; 4]>,
    // For each cell, its class.
    cell_class: Vec<CellClass>,
    // For each piece-id, its class.
    piece_class: Vec<PieceClass>,
    // Pre-bucketed piece lists per class. Used to draw on-class swap
    // partners cheaply.
    corner_pieces: Vec<PieceId>,
    edge_pieces: Vec<PieceId>,
    interior_pieces: Vec<PieceId>,
    // Pre-bucketed cell lists per class.
    corner_cells: Vec<Position>,
    edge_cells: Vec<Position>,
    interior_cells: Vec<Position>,
}

impl<'a> State<'a> {
    fn new(puzzle: &'a Puzzle) -> Self {
        let pieces = puzzle.pieces();
        let max_piece_index = pieces.iter().map(|p| usize::from(p.id) + 1).max().unwrap_or(0);
        let mut piece_rot_edges = vec![[0u8; 4]; max_piece_index * 4];
        let mut piece_class = vec![PieceClass::Interior; max_piece_index];
        let mut corner_pieces = Vec::new();
        let mut edge_pieces = Vec::new();
        let mut interior_pieces = Vec::new();
        for piece in pieces {
            let pid = usize::from(piece.id);
            for r in 0..4u8 {
                let rot = Rotation::from_u8(r).unwrap();
                let e = piece.edges.rotated(rot).as_array();
                piece_rot_edges[pid * 4 + r as usize] = e;
            }
            let class = classify_piece(piece.edges.as_array());
            piece_class[pid] = class;
            match class {
                PieceClass::Corner => corner_pieces.push(piece.id),
                PieceClass::Edge => edge_pieces.push(piece.id),
                PieceClass::Interior => interior_pieces.push(piece.id),
            }
        }

        let n_cells = puzzle.cell_count() as usize;
        let mut cell_class = Vec::with_capacity(n_cells);
        let mut corner_cells = Vec::new();
        let mut edge_cells = Vec::new();
        let mut interior_cells = Vec::new();
        for pos in 0..puzzle.cell_count() {
            let c = classify_cell(puzzle, pos);
            cell_class.push(c);
            match c {
                CellClass::Corner => corner_cells.push(pos),
                CellClass::Edge => edge_cells.push(pos),
                CellClass::Interior => interior_cells.push(pos),
            }
        }

        Self {
            puzzle,
            piece_rot_edges,
            cell_class,
            piece_class,
            corner_pieces,
            edge_pieces,
            interior_pieces,
            corner_cells,
            edge_cells,
            interior_cells,
        }
    }

    fn edges_for(&self, piece_id: PieceId, rotation: Rotation) -> [Color; 4] {
        let idx = usize::from(piece_id) * 4 + usize::from(rotation.as_u8());
        self.piece_rot_edges[idx]
    }

    /// Build a feasible initial placement: pieces of correct class are
    /// dropped into cells of correct class in seed-random order. Border
    /// rotation is forced to the unique rotation that puts BORDER on
    /// the outward-facing sides. Interior rotation is random.
    fn random_initial(&self, rng: &mut Rng) -> Board {
        let mut board = Board::empty(self.puzzle);
        // Helper: pick rotation that maximises border-match for a corner
        // or edge cell; for interiors choose at random.
        let pick_rot = |pid: PieceId, pos: Position, rng: &mut Rng| -> Rotation {
            let mask = self.puzzle.border_mask(pos);
            let [tb, rb, bb, lb] = mask;
            // For non-interior cells, find a rotation r such that
            // edges[s] == BORDER iff mask[s] is true for sides
            // (top, right, bot, left).
            if matches!(self.cell_class[pos as usize], CellClass::Interior) {
                Rotation::from_u8(rng.gen_range(4) as u8).unwrap()
            } else {
                let mut best = Rotation::from_u8(0).unwrap();
                for r in 0..4u8 {
                    let rot = Rotation::from_u8(r).unwrap();
                    let e = self.edges_for(pid, rot);
                    if (e[0] == BORDER) == tb
                        && (e[1] == BORDER) == rb
                        && (e[2] == BORDER) == bb
                        && (e[3] == BORDER) == lb
                    {
                        best = rot;
                        break;
                    }
                }
                best
            }
        };
        // Shuffle each piece pool then drop one-by-one into matching cells.
        let mut do_class = |pieces: &mut Vec<PieceId>, cells: &[Position], rng: &mut Rng, board: &mut Board| {
            // Fisher-Yates over piece pool.
            for i in (1..pieces.len()).rev() {
                let j = rng.gen_range((i + 1) as u32) as usize;
                pieces.swap(i, j);
            }
            for (i, &pos) in cells.iter().enumerate() {
                let pid = pieces[i];
                let rot = pick_rot(pid, pos, rng);
                board.place(pos, pid, rot);
            }
        };
        let mut corner = self.corner_pieces.clone();
        let mut edge = self.edge_pieces.clone();
        let mut interior = self.interior_pieces.clone();
        do_class(&mut corner, &self.corner_cells, rng, &mut board);
        do_class(&mut edge, &self.edge_cells, rng, &mut board);
        do_class(&mut interior, &self.interior_cells, rng, &mut board);
        board
    }

    /// Take a possibly-partial `initial` board and produce a full
    /// placement: keep all already-placed cells, then fill the empties
    /// with random class-matching pieces (picking a class-correct
    /// rotation).
    fn fill_in_initial(&self, initial: &Board, rng: &mut Rng) -> Board {
        let mut board = initial.clone();
        // Identify which pieces are already used (by piece-id).
        let n_pieces = self.piece_class.len();
        let mut used = vec![false; n_pieces];
        for c in board.cells() {
            if let Some((pid, _rot)) = c {
                used[usize::from(*pid)] = true;
            }
        }
        // Build leftover pools per class.
        let mut leftover_corner: Vec<PieceId> = Vec::new();
        let mut leftover_edge: Vec<PieceId> = Vec::new();
        let mut leftover_interior: Vec<PieceId> = Vec::new();
        for (pid_idx, was_used) in used.iter().enumerate() {
            if *was_used { continue; }
            // Reverse-lookup: piece_class[pid] is class
            let pid_u16 = pid_idx as u16;
            match self.piece_class[pid_idx] {
                PieceClass::Corner => leftover_corner.push(pid_u16),
                PieceClass::Edge => leftover_edge.push(pid_u16),
                PieceClass::Interior => leftover_interior.push(pid_u16),
            }
        }
        // Find empty cells per class.
        let mut empty_corner: Vec<Position> = Vec::new();
        let mut empty_edge: Vec<Position> = Vec::new();
        let mut empty_interior: Vec<Position> = Vec::new();
        for pos in 0..self.puzzle.cell_count() {
            if board.get(pos).is_some() { continue; }
            match self.cell_class[pos as usize] {
                CellClass::Corner => empty_corner.push(pos),
                CellClass::Edge => empty_edge.push(pos),
                CellClass::Interior => empty_interior.push(pos),
            }
        }
        // Shuffle leftover pieces then drop them into empty cells.
        let shuffle = |v: &mut Vec<PieceId>, rng: &mut Rng| {
            for i in (1..v.len()).rev() {
                let j = rng.gen_range((i + 1) as u32) as usize;
                v.swap(i, j);
            }
        };
        shuffle(&mut leftover_corner, rng);
        shuffle(&mut leftover_edge, rng);
        shuffle(&mut leftover_interior, rng);
        let pick_rot = |pid: PieceId, pos: Position, rng: &mut Rng, st: &State| -> Rotation {
            let mask = st.puzzle.border_mask(pos);
            let [tb, rb, bb, lb] = mask;
            if matches!(st.cell_class[pos as usize], CellClass::Interior) {
                Rotation::from_u8(rng.gen_range(4) as u8).unwrap()
            } else {
                for r in 0..4u8 {
                    let rot = Rotation::from_u8(r).unwrap();
                    let e = st.edges_for(pid, rot);
                    if (e[0] == BORDER) == tb
                        && (e[1] == BORDER) == rb
                        && (e[2] == BORDER) == bb
                        && (e[3] == BORDER) == lb
                    { return rot; }
                }
                Rotation::from_u8(0).unwrap()
            }
        };
        for (i, &pos) in empty_corner.iter().enumerate() {
            if i >= leftover_corner.len() { break; }
            let pid = leftover_corner[i];
            board.place(pos, pid, pick_rot(pid, pos, rng, self));
        }
        for (i, &pos) in empty_edge.iter().enumerate() {
            if i >= leftover_edge.len() { break; }
            let pid = leftover_edge[i];
            board.place(pos, pid, pick_rot(pid, pos, rng, self));
        }
        for (i, &pos) in empty_interior.iter().enumerate() {
            if i >= leftover_interior.len() { break; }
            let pid = leftover_interior[i];
            board.place(pos, pid, pick_rot(pid, pos, rng, self));
        }
        board
    }

    /// Count matching interior edges (the maximisation target).
    ///
    /// An interior edge between two adjacent cells matches iff the
    /// two facing colors are equal AND non-zero (a BORDER on an
    /// interior edge means the placement is invalid for that side,
    /// so we exclude it).
    fn score(&self, board: &Board) -> u32 {
        let w = self.puzzle.width;
        let h = self.puzzle.height;
        let mut matches = 0u32;
        for y in 0..h {
            for x in 0..w {
                let pos = y * w + x;
                let cell = board.get(pos);
                let Some((pid, rot)) = cell else { continue; };
                let e = self.edges_for(pid, rot);
                // Compare with right neighbour and below neighbour to
                // avoid double-counting. Treat off-board (border) edges
                // as required-BORDER on outward sides.
                if x + 1 < w {
                    let r_cell = board.get(y * w + (x + 1));
                    if let Some((rpid, rrot)) = r_cell {
                        let re = self.edges_for(rpid, rrot);
                        if e[1] == re[3] && e[1] != 0 {
                            matches += 1;
                        }
                    }
                }
                if y + 1 < h {
                    let b_cell = board.get((y + 1) * w + x);
                    if let Some((bpid, brot)) = b_cell {
                        let be = self.edges_for(bpid, brot);
                        if e[2] == be[0] && e[2] != 0 {
                            matches += 1;
                        }
                    }
                }
            }
        }
        matches
    }

    /// Total interior edges (target denominator).
    fn total_interior_edges(&self) -> u32 {
        let w = self.puzzle.width;
        let h = self.puzzle.height;
        // Horizontal interior edges: (w-1) per row × h rows
        // Vertical interior edges: w per column × (h-1) gaps
        (w - 1) * h + w * (h - 1)
    }
}

/// Compute the edge-match contribution of a single cell. Counts the
/// number of matching edges on its 4 sides (each counted once per
/// shared edge; this function returns only this cell's view, so it
/// returns 4 if all 4 neighbours match, but each match contributes 1
/// to the cell-vs-neighbour edge, NOT 1 to each of the two cells).
///
/// Used for incremental delta computation: changing piece-at-pos
/// affects this cell's contribution AND each neighbour's contribution
/// at the shared edge, but since matches are symmetric, the delta in
/// global score = (new local matches) - (old local matches).
fn local_match_count(state: &State, board: &Board, pos: Position) -> u32 {
    let Some((pid, rot)) = board.get(pos) else { return 0; };
    let e = state.edges_for(pid, rot);
    let w = state.puzzle.width;
    let h = state.puzzle.height;
    let (x, y) = (pos % w, pos / w);
    let mut m = 0u32;
    // Top neighbour
    if y > 0 {
        if let Some((np, nr)) = board.get((y - 1) * w + x) {
            let ne = state.edges_for(np, nr);
            if e[0] == ne[2] && e[0] != 0 { m += 1; }
        }
    }
    // Right
    if x + 1 < w {
        if let Some((np, nr)) = board.get(y * w + (x + 1)) {
            let ne = state.edges_for(np, nr);
            if e[1] == ne[3] && e[1] != 0 { m += 1; }
        }
    }
    // Bottom
    if y + 1 < h {
        if let Some((np, nr)) = board.get((y + 1) * w + x) {
            let ne = state.edges_for(np, nr);
            if e[2] == ne[0] && e[2] != 0 { m += 1; }
        }
    }
    // Left
    if x > 0 {
        if let Some((np, nr)) = board.get(y * w + (x - 1)) {
            let ne = state.edges_for(np, nr);
            if e[3] == ne[1] && e[3] != 0 { m += 1; }
        }
    }
    m
}

/// Pick the rotation of `pid` at `pos` that maximises edge matches
/// with currently-placed neighbours. For border cells, only border-
/// compatible rotations are considered.
fn best_rotation(state: &State, board: &Board, pos: Position, pid: PieceId) -> Rotation {
    let mask = state.puzzle.border_mask(pos);
    let [tb, rb, bb, lb] = mask;
    let is_interior = matches!(state.cell_class[pos as usize], CellClass::Interior);
    let mut best_rot = Rotation::from_u8(0).unwrap();
    let mut best_count = u32::MAX; // sentinel; we only set after first valid try
    let mut seen_any = false;
    for r in 0..4u8 {
        let rot = Rotation::from_u8(r).unwrap();
        let e = state.edges_for(pid, rot);
        if !is_interior {
            // Must align borders. Reject misaligned rotations.
            if (e[0] == BORDER) != tb
                || (e[1] == BORDER) != rb
                || (e[2] == BORDER) != bb
                || (e[3] == BORDER) != lb
            { continue; }
        }
        // Tentatively place and count local matches.
        let saved = board.get(pos);
        // Use a const local "what would the count be" — we don't
        // mutate the actual board by writing then reverting; instead
        // compute by emulating the comparison.
        let m = match_count_with(state, board, pos, e);
        // Discount: we don't want to write to board. Hack: we
        // compute equivalent of placing this piece-rot at pos.
        let _ = saved;
        if !seen_any || m > best_count {
            best_count = m;
            best_rot = rot;
            seen_any = true;
        }
    }
    best_rot
}

/// Hypothetical local match-count if the piece-rotation with edges
/// `e_hypo` were at `pos`. Doesn't mutate board.
fn match_count_with(state: &State, board: &Board, pos: Position, e_hypo: [Color; 4]) -> u32 {
    let w = state.puzzle.width;
    let h = state.puzzle.height;
    let (x, y) = (pos % w, pos / w);
    let mut m = 0u32;
    if y > 0 {
        if let Some((np, nr)) = board.get((y - 1) * w + x) {
            let ne = state.edges_for(np, nr);
            if e_hypo[0] == ne[2] && e_hypo[0] != 0 { m += 1; }
        }
    }
    if x + 1 < w {
        if let Some((np, nr)) = board.get(y * w + (x + 1)) {
            let ne = state.edges_for(np, nr);
            if e_hypo[1] == ne[3] && e_hypo[1] != 0 { m += 1; }
        }
    }
    if y + 1 < h {
        if let Some((np, nr)) = board.get((y + 1) * w + x) {
            let ne = state.edges_for(np, nr);
            if e_hypo[2] == ne[0] && e_hypo[2] != 0 { m += 1; }
        }
    }
    if x > 0 {
        if let Some((np, nr)) = board.get(y * w + (x - 1)) {
            let ne = state.edges_for(np, nr);
            if e_hypo[3] == ne[1] && e_hypo[3] != 0 { m += 1; }
        }
    }
    m
}

/// Variant of `run_sa` that starts from a caller-supplied initial board.
/// Used by the CP+LS hybrid: seed LS with the CP solver's `best_partial`
/// (filling any unplaced cells randomly with class-matching pieces).
///
/// The supplied board may be partial (cells = None). Unplaced cells get
/// a random class-matching piece in a valid rotation. Already-placed
/// cells are kept as-is at the start; LS is then free to move any piece
/// during search (we do NOT pin user placements).
pub fn run_sa_from(puzzle: &Puzzle, initial: &Board, cfg: &SaConfig) -> SaOutcome {
    let started = std::time::Instant::now();
    let state = State::new(puzzle);
    let mut rng = Rng::new(cfg.seed);

    let mut board = state.fill_in_initial(initial, &mut rng);
    run_sa_loop(&state, &mut board, &mut rng, cfg, started)
}

/// Run simulated annealing on `puzzle`. Returns the best board found.
///
/// Status: v1.
/// - Random initial placement (correct piece-class per cell, border
///   rotations forced).
/// - Two neighborhood operators chosen at random each iteration:
///     (a) "rotate": pick a cell and try a random different rotation
///     (b) "swap+best-rot": pick two same-class cells, swap pieces,
///         re-rotate both to their best orientation.
/// - SA acceptance with geometric cooling.
/// - Re-anneal: when temperature falls below `temperature_min`, reset
///   temperature to `temperature_start` and continue. This keeps the
///   walk from freezing at a poor local optimum.
/// - Incremental scoring: changes touch at most 2 cells (swap) or 1
///   cell (rotate), so we compute the score delta from local counts
///   alone instead of re-scanning the whole board.
pub fn run_sa(puzzle: &Puzzle, cfg: &SaConfig) -> SaOutcome {
    let started = std::time::Instant::now();
    let state = State::new(puzzle);
    let mut rng = Rng::new(cfg.seed);

    let mut board = state.random_initial(&mut rng);
    run_sa_loop(&state, &mut board, &mut rng, cfg, started)
}

fn run_sa_loop(
    state: &State<'_>,
    board: &mut Board,
    rng: &mut Rng,
    cfg: &SaConfig,
    started: std::time::Instant,
) -> SaOutcome {
    let mut score = state.score(board);
    let mut best_board = board.clone();
    let mut best_score = score;
    let total_edges = state.total_interior_edges();

    let mut temp = cfg.temperature_start;
    let mut iters: u64 = 0;
    let mut since_cool: u64 = 0;
    let mut accepts: u64 = 0;
    let mut rejects: u64 = 0;
    let _ = (accepts, rejects); // placeholder for future telemetry

    let timed_out = |start: &std::time::Instant| -> bool {
        cfg.time_budget_ms != 0
            && start.elapsed().as_millis() >= u128::from(cfg.time_budget_ms)
    };

    loop {
        if cfg.max_iters != 0 && iters >= cfg.max_iters { break; }
        if timed_out(&started) { break; }
        if best_score == total_edges { break; }

        // Choose move type. 30% rotate, 70% swap+best-rot. Rationale:
        // rotates are cheap and target small local issues; swaps are
        // the long-range moves needed to escape configurations.
        let move_kind = rng.gen_range(10);
        if move_kind < 3 {
            // ROTATE-ONLY: pick a cell, try a random different rotation.
            let n_cells = state.puzzle.cell_count();
            let pos = rng.gen_range(n_cells);
            let Some((pid, old_rot)) = board.get(pos) else { continue; };
            let cell_is_interior = matches!(state.cell_class[pos as usize], CellClass::Interior);
            if !cell_is_interior {
                // Border cells have a single valid rotation, rotate-only
                // is a no-op for them.
                iters += 1;
                since_cool += 1;
                continue;
            }
            // Try a random different rotation
            let mut new_r = rng.gen_range(4) as u8;
            if new_r == old_rot.as_u8() {
                new_r = (new_r + 1) & 0b11;
            }
            let new_rot = Rotation::from_u8(new_r).unwrap();
            let old_local = local_match_count(&state, &board, pos);
            let e_new = state.edges_for(pid, new_rot);
            let new_local = match_count_with(&state, &board, pos, e_new);
            let delta = (new_local as i64) - (old_local as i64);
            let accept = if delta >= 0 {
                true
            } else {
                let p = (-(delta as f64) / temp).exp();
                rng.next_f64() < p
            };
            if accept {
                board.place(pos, pid, new_rot);
                score = (score as i64 + delta) as u32;
                if score > best_score {
                    best_score = score;
                    best_board = board.clone();
                }
                accepts += 1;
            } else {
                rejects += 1;
            }
        } else {
            // SWAP+BEST-ROT: pick two same-class cells, swap, then
            // re-rotate both to best orientation.
            let class_pick = rng.gen_range(3);
            let cells = match class_pick {
                0 => &state.corner_cells,
                1 => &state.edge_cells,
                _ => &state.interior_cells,
            };
            if cells.len() < 2 {
                iters += 1;
                since_cool += 1;
                continue;
            }
            let i = rng.gen_range(cells.len() as u32) as usize;
            let mut j = rng.gen_range(cells.len() as u32) as usize;
            if i == j { j = (j + 1) % cells.len(); }
            let p_i = cells[i];
            let p_j = cells[j];

            let Some((pid_i, rot_i)) = board.get(p_i) else { continue; };
            let Some((pid_j, rot_j)) = board.get(p_j) else { continue; };

            let old_local_i = local_match_count(&state, &board, p_i);
            let old_local_j = local_match_count(&state, &board, p_j);
            // Edge between i and j (if adjacent) would be double-counted
            // when computing locals; subtract once to avoid double-counting
            // ourselves into trouble in the delta calculation.
            let adjacent_edge_match = adjacent_match(&state, &board, p_i, p_j);
            let old_local = old_local_i + old_local_j - adjacent_edge_match;

            // Tentatively perform swap: piece at i goes to j, piece at j goes to i.
            board.place(p_i, pid_j, rot_j);
            board.place(p_j, pid_i, rot_i);
            // Choose best rotations after swap, using fresh neighbour info.
            // For border cells this is the only valid rotation; for
            // interior it's the score-maximising one.
            let best_rot_i = best_rotation(&state, &board, p_i, pid_j);
            board.place(p_i, pid_j, best_rot_i);
            let best_rot_j = best_rotation(&state, &board, p_j, pid_i);
            board.place(p_j, pid_i, best_rot_j);

            let new_local_i = local_match_count(&state, &board, p_i);
            let new_local_j = local_match_count(&state, &board, p_j);
            let new_adj = adjacent_match(&state, &board, p_i, p_j);
            let new_local = new_local_i + new_local_j - new_adj;

            let delta = (new_local as i64) - (old_local as i64);
            let accept = if delta >= 0 {
                true
            } else {
                let p = (-(delta as f64) / temp).exp();
                rng.next_f64() < p
            };
            if accept {
                score = (score as i64 + delta) as u32;
                if score > best_score {
                    best_score = score;
                    best_board = board.clone();
                }
                accepts += 1;
            } else {
                // Revert.
                board.place(p_i, pid_i, rot_i);
                board.place(p_j, pid_j, rot_j);
                rejects += 1;
            }
        }

        iters += 1;
        since_cool += 1;
        if since_cool >= cfg.cooling_period {
            temp *= cfg.cooling;
            since_cool = 0;
            // Re-anneal: if temperature has frozen, reset to start.
            // Wauters et al. don't explicitly describe this but
            // local-search practice on hard problems uses restarts
            // to escape frozen states.
            if temp < cfg.temperature_min {
                temp = cfg.temperature_start;
            }
        }
    }

    SaOutcome {
        best_board,
        best_score,
        total_edges,
        iterations: iters,
        elapsed_us: started.elapsed().as_micros(),
    }
}

/// Returns 1 if cells a and b are adjacent AND their shared edge matches.
fn adjacent_match(state: &State, board: &Board, a: Position, b: Position) -> u32 {
    let w = state.puzzle.width;
    let (ax, ay) = (a % w, a / w);
    let (bx, by) = (b % w, b / w);
    let dx = (ax as i32) - (bx as i32);
    let dy = (ay as i32) - (by as i32);
    if dx.unsigned_abs() + dy.unsigned_abs() != 1 {
        return 0;
    }
    let Some((pa, ra)) = board.get(a) else { return 0; };
    let Some((pb, rb)) = board.get(b) else { return 0; };
    let ea = state.edges_for(pa, ra);
    let eb = state.edges_for(pb, rb);
    // Determine the shared-edge sides.
    let (side_a, side_b) = if dx == 1 && dy == 0 {
        (3usize, 1usize) // a is right of b → a's left ↔ b's right
    } else if dx == -1 && dy == 0 {
        (1, 3)
    } else if dy == 1 && dx == 0 {
        (0, 2)
    } else {
        (2, 0)
    };
    if ea[side_a] == eb[side_b] && ea[side_a] != 0 { 1 } else { 0 }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mini smoke test: tiny puzzle, ensure run_sa terminates and
    // never reports a score greater than total_edges.
    #[test]
    fn sa_runs_and_score_in_range() {
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig {
            size: 4,
            interior_colors: 4,
            seed: 7,
        })
        .expect("gen");
        let cfg = SaConfig {
            max_iters: 5_000,
            time_budget_ms: 2_000,
            ..Default::default()
        };
        let out = run_sa(&puzzle, &cfg);
        assert!(out.best_score <= out.total_edges, "score {} > total {}", out.best_score, out.total_edges);
        // Sanity: 4×4 has 24 interior edges.
        assert_eq!(out.total_edges, 24);
    }
}
