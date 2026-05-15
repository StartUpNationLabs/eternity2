// LP-relaxation upper bound on interior score given a fixed border placement.
//
// See vault/concepts/border-enum-lp-ub.md for the math.

use std::collections::HashMap;

use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use good_lp::{
    constraint, solvers::highs::{highs, HighsSolverType},
    Expression, ProblemVariables, Solution, SolverModel, Variable, variable,
};

#[derive(Debug, Clone, Copy)]
pub struct LpOptions {
    pub verbose: bool,
    pub threads: u32,
    pub time_limit_secs: f64,
    pub use_ipm: bool,
    pub presolve: bool,
    pub integer: bool,         // make x[c,p,r] and y[edge,k] binary (MIP mode)
}

impl Default for LpOptions {
    fn default() -> Self {
        Self {
            verbose: false,
            threads: 8,
            time_limit_secs: 300.0,
            use_ipm: true,
            presolve: true,
            integer: false,
        }
    }
}

#[must_use]
pub fn is_perimeter_pos(puzzle: &Puzzle, pos: Position) -> bool {
    let (x, y) = puzzle.xy(pos);
    x == 0 || x == puzzle.width - 1 || y == 0 || y == puzzle.height - 1
}

#[must_use]
pub fn perimeter_positions(puzzle: &Puzzle) -> Vec<Position> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut out = Vec::with_capacity(((2 * w + 2 * h) - 4) as usize);
    for x in 0..w { out.push(x); }
    if h > 2 {
        for y in 1..h - 1 { out.push(y * w + (w - 1)); }
    }
    for x in (0..w).rev() { out.push((h - 1) * w + x); }
    if h > 2 {
        for y in (1..h - 1).rev() { out.push(y * w); }
    }
    out
}

#[must_use]
pub fn b_b_match_count(puzzle: &Puzzle, board: &Board) -> u32 {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut matched = 0u32;
    for pos in perimeter_positions(puzzle) {
        let (x, y) = puzzle.xy(pos);
        let Some((pid, rot)) = board.get(pos) else { continue; };
        let Some(p) = puzzle.piece(pid) else { continue; };
        let e = p.edges.rotated(rot).as_array();
        if x + 1 < w {
            let n = y * w + (x + 1);
            if is_perimeter_pos(puzzle, n) {
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
            if is_perimeter_pos(puzzle, n) {
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

#[must_use]
pub fn b_i_constraints(puzzle: &Puzzle, board: &Board) -> Vec<(Position, u8, u8)> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut out = Vec::new();
    for pos in perimeter_positions(puzzle) {
        let (x, y) = puzzle.xy(pos);
        let Some((pid, rot)) = board.get(pos) else { continue; };
        let Some(p) = puzzle.piece(pid) else { continue; };
        let edges = p.edges.rotated(rot).as_array();
        if y > 0 {
            let n = (y - 1) * w + x;
            if !is_perimeter_pos(puzzle, n) {
                out.push((n, 2u8, edges[0]));
            }
        }
        if x + 1 < w {
            let n = y * w + (x + 1);
            if !is_perimeter_pos(puzzle, n) {
                out.push((n, 3u8, edges[1]));
            }
        }
        if y + 1 < h {
            let n = (y + 1) * w + x;
            if !is_perimeter_pos(puzzle, n) {
                out.push((n, 0u8, edges[2]));
            }
        }
        if x > 0 {
            let n = y * w + (x - 1);
            if !is_perimeter_pos(puzzle, n) {
                out.push((n, 1u8, edges[3]));
            }
        }
    }
    out
}

fn cell_candidates(
    puzzle: &Puzzle,
    pinned_pieces: &[PieceId],
) -> Vec<(PieceId, Rotation, [u8; 4])> {
    let mut out = Vec::new();
    for piece in puzzle.pieces() {
        if !piece.is_inner() { continue; }
        if pinned_pieces.contains(&piece.id) { continue; }
        for &r in &Rotation::ALL {
            let e = piece.edges.rotated(r).as_array();
            out.push((piece.id, r, e));
        }
    }
    out
}

#[derive(Debug, Clone)]
pub struct LpUb {
    pub bb_matches: u32,
    pub bi_matches: u32,    // rounded LP B-I match value (was: forced)
    pub bi_ub: f64,         // exact LP B-I match
    pub interior_ub: f64,
    pub total_ub: f64,
    pub n_x: usize,
    pub n_y: usize,
    pub n_constraints: usize,
    pub solve_secs: f64,
    /// Per-color sum of y_in (interior LP UB broken down by color k=1..max_color).
    /// Index 0 unused; entries [1..=max_color] valid. None if not collected.
    pub per_color_ii_ub: Option<Vec<f64>>,
}

pub fn lp_ub(puzzle: &Puzzle, board: &Board) -> Result<LpUb, String> {
    lp_ub_with(puzzle, board, LpOptions::default())
}

/// Compute the LP-relaxation UB on interior score given a fixed border board.
/// `board` must have perimeter cells (and possibly hints) placed; non-pinned
/// interior cells are free in the LP.
pub fn lp_ub_with(puzzle: &Puzzle, board: &Board, opts: LpOptions) -> Result<LpUb, String> {
    let w = puzzle.width;
    let h = puzzle.height;

    let bb = b_b_match_count(puzzle, board);
    let bi = b_i_constraints(puzzle, board);
    let mut bi_by_cell: HashMap<Position, Vec<(u8, u8)>> = HashMap::new();
    for (cell, side, color) in &bi {
        bi_by_cell.entry(*cell).or_default().push((*side, *color));
    }

    let mut interior_cells: Vec<Position> = Vec::new();
    let mut pinned_pieces: Vec<PieceId> = Vec::new();
    let mut hint_at: HashMap<Position, (PieceId, Rotation)> = HashMap::new();
    for pos in 0..puzzle.cell_count() {
        if is_perimeter_pos(puzzle, pos) {
            if let Some((pid, _)) = board.get(pos) {
                pinned_pieces.push(pid);
            }
            continue;
        }
        if let Some((pid, rot)) = board.get(pos) {
            pinned_pieces.push(pid);
            hint_at.insert(pos, (pid, rot));
        }
        interior_cells.push(pos);
    }

    let mut cell_cands: HashMap<Position, Vec<(PieceId, Rotation, [u8; 4])>> = HashMap::new();
    for &c in &interior_cells {
        if let Some(&(pid, rot)) = hint_at.get(&c) {
            let p = puzzle.piece(pid).ok_or_else(|| format!("hint pid {pid}"))?;
            let e = p.edges.rotated(rot).as_array();
            cell_cands.insert(c, vec![(pid, rot, e)]);
        } else {
            let cands = cell_candidates(puzzle, &pinned_pieces);
            if cands.is_empty() {
                return Err(format!("infeasible: cell {c} has 0 candidates"));
            }
            cell_cands.insert(c, cands);
        }
    }

    let mut problem = ProblemVariables::new();
    let mut x_var: HashMap<(Position, PieceId, Rotation), Variable> = HashMap::new();
    let mut x_per_cell: HashMap<Position, Vec<(Variable, [u8; 4])>> = HashMap::new();
    let mut x_per_piece: HashMap<PieceId, Vec<Variable>> = HashMap::new();

    let mut total_x = 0usize;
    for &c in &interior_cells {
        let cands = &cell_cands[&c];
        let mut cell_vars = Vec::with_capacity(cands.len());
        for &(pid, rot, e) in cands {
            let mut vd = variable().min(0.0).max(1.0);
            if opts.integer { vd = vd.binary(); }
            let v = problem.add(vd);
            x_var.insert((c, pid, rot), v);
            cell_vars.push((v, e));
            x_per_piece.entry(pid).or_default().push(v);
            total_x += 1;
        }
        x_per_cell.insert(c, cell_vars);
    }

    let mut ii_edges: Vec<(Position, Position, u8)> = Vec::new();
    for &c1 in &interior_cells {
        let (x1, y1) = puzzle.xy(c1);
        if x1 + 1 < w {
            let c2 = y1 * w + (x1 + 1);
            if !is_perimeter_pos(puzzle, c2) {
                ii_edges.push((c1, c2, 0));
            }
        }
        if y1 + 1 < h {
            let c2 = (y1 + 1) * w + x1;
            if !is_perimeter_pos(puzzle, c2) {
                ii_edges.push((c1, c2, 1));
            }
        }
    }

    // Colors are 1..=(color_count-1); color_count includes BORDER=0.
    let max_color = (puzzle.color_count.saturating_sub(1)) as u8;
    let n_y = ii_edges.len() * max_color as usize;
    let y_def = {
        let vd = variable().min(0.0).max(1.0);
        if opts.integer { vd.binary() } else { vd }
    };
    let y_list: Vec<Variable> = problem.add_vector(y_def.clone(), n_y);

    // B-I match variables: one per B-I edge (interior_cell, side, required_color).
    let n_y_bi = bi.len();
    let y_bi_list: Vec<Variable> = problem.add_vector(y_def, n_y_bi);

    let obj_ii: Expression = y_list.iter().copied().sum();
    let obj_bi: Expression = y_bi_list.iter().copied().sum();
    let obj: Expression = obj_ii + obj_bi;
    let mut hp = problem.maximise(obj).using(highs);
    hp.set_verbose(opts.verbose);
    let mut hp = hp.set_time_limit(opts.time_limit_secs);
    if opts.threads > 1 {
        hp = hp.set_threads(opts.threads);
        hp = hp.set_parallel(good_lp::solvers::highs::HighsParallelType::On);
    }
    if opts.use_ipm {
        hp = hp.set_solver(HighsSolverType::Ipm);
    }
    hp = hp.set_presolve(if opts.presolve {
        good_lp::solvers::highs::HighsPresolveType::On
    } else {
        good_lp::solvers::highs::HighsPresolveType::Off
    });
    let mut model = hp;

    for &c in &interior_cells {
        let cell_vars = &x_per_cell[&c];
        let sum: Expression = cell_vars.iter().map(|&(v, _)| v).sum();
        model = model.with(constraint!(sum == 1.0));
    }

    for (_pid, vars) in &x_per_piece {
        let sum: Expression = vars.iter().copied().sum();
        model = model.with(constraint!(sum == 1.0));
    }

    for (&c, &(pid, rot)) in &hint_at {
        let v = x_var[&(c, pid, rot)];
        model = model.with(constraint!(v == 1.0));
    }

    // B-I match constraints: y_bi[i] ≤ Σ x[c, p, r where rotated-edge[side] == required_color].
    for (i, &(cell, side, color)) in bi.iter().enumerate() {
        let y_bi_v = y_bi_list[i];
        let supply: Expression = x_per_cell[&cell].iter()
            .filter(|(_, e)| e[side as usize] == color)
            .map(|&(v, _)| v)
            .sum();
        model = model.with(constraint!(y_bi_v <= supply));
    }

    let mut n_y_constraints = bi.len();
    for (i, &(c1, c2, dir)) in ii_edges.iter().enumerate() {
        let (s1, s2) = if dir == 0 { (1u8, 3u8) } else { (2u8, 0u8) };
        let mut a_buckets: Vec<Vec<Variable>> = vec![Vec::new(); (max_color as usize) + 1];
        let mut b_buckets: Vec<Vec<Variable>> = vec![Vec::new(); (max_color as usize) + 1];
        for &(v, e) in &x_per_cell[&c1] {
            let k = e[s1 as usize] as usize;
            if k > 0 && k <= max_color as usize {
                a_buckets[k].push(v);
            }
        }
        for &(v, e) in &x_per_cell[&c2] {
            let k = e[s2 as usize] as usize;
            if k > 0 && k <= max_color as usize {
                b_buckets[k].push(v);
            }
        }
        for k in 1..=max_color as usize {
            let yv = y_list[i * max_color as usize + (k - 1)];
            let a_expr: Expression = a_buckets[k].iter().copied().sum();
            let b_expr: Expression = b_buckets[k].iter().copied().sum();
            model = model.with(constraint!(yv <= a_expr));
            model = model.with(constraint!(yv <= b_expr));
            n_y_constraints += 2;
        }
    }

    let n_constraints = interior_cells.len() + x_per_piece.len() + hint_at.len() + n_y_constraints;

    let t0 = std::time::Instant::now();
    let sol = model.solve().map_err(|e| format!("LP solve: {e:?}"))?;
    let solve_secs = t0.elapsed().as_secs_f64();

    let interior_ub: f64 = y_list.iter().map(|v| sol.value(*v)).sum();
    let bi_ub: f64 = y_bi_list.iter().map(|v| sol.value(*v)).sum();
    let bi_matches = bi_ub.round() as u32; // for legacy reporting
    let total = bb as f64 + bi_ub + interior_ub;

    // Per-color y_in breakdown.
    // y_list indexed: y_list[edge_idx * max_color + (k-1)] for k=1..=max_color.
    let mut per_color = vec![0.0f64; (max_color as usize) + 1];
    for (ei, _) in ii_edges.iter().enumerate() {
        for k in 1..=max_color as usize {
            let v = y_list[ei * max_color as usize + (k - 1)];
            per_color[k] += sol.value(v);
        }
    }

    Ok(LpUb {
        bb_matches: bb,
        bi_matches,
        bi_ub,
        interior_ub,
        total_ub: total,
        n_x: total_x,
        n_y,
        n_constraints,
        solve_secs,
        per_color_ii_ub: Some(per_color),
    })
}

/// Strip interior placements except hint positions; keep all perimeter cells.
pub fn strip_interior_except_hints(
    puzzle: &Puzzle,
    board: &Board,
    hint_positions: &[Position],
) -> Board {
    let mut out = Board::empty(puzzle);
    for pos in 0..puzzle.cell_count() {
        if is_perimeter_pos(puzzle, pos) || hint_positions.contains(&pos) {
            if let Some((pid, rot)) = board.get(pos) {
                out.place(pos, pid, rot);
            }
        }
    }
    out
}
