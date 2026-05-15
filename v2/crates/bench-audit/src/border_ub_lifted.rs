// Lifted LP-relaxation upper bound for canonical-E2 interior score.
//
// Polyhedral lifting via McCormick envelope on bilinear edge-match products.
// See vault/concepts/lifted-lp-formulation.md for the math.
//
// Key idea: in the standard LP we have y[e,k] ≤ min(a, b) (loose).
// Here we introduce z[e, p1, r1, p2, r2] for each color-matched
// (piece-rotation, piece-rotation) pair across each I-I edge, with
// McCormick constraints:
//   z ≤ x[c1, p1, r1]
//   z ≤ x[c2, p2, r2]
//   z ≥ x[c1, p1, r1] + x[c2, p2, r2] - 1
//   z ≥ 0
//
// The objective sums z over color-matched pairs.

use std::collections::HashMap;

use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use good_lp::{
    constraint, solvers::highs::{highs, HighsSolverType},
    Expression, ProblemVariables, Solution, SolverModel, Variable, variable,
};

use crate::border_ub::{
    b_b_match_count, b_i_constraints, is_perimeter_pos, perimeter_positions,
    LpOptions,
};

/// Result of a lifted LP solve.
#[derive(Debug, Clone)]
pub struct LiftedLpUb {
    pub bb_matches: u32,
    pub bi_ub: f64,
    pub interior_ub: f64,
    pub total_ub: f64,
    pub n_x: usize,
    pub n_z: usize,
    pub n_y_bi: usize,
    pub n_constraints: usize,
    pub n_z_per_edge_avg: f64,
    pub solve_secs: f64,
}

/// Options for column-generation lifted LP.
#[derive(Debug, Clone)]
pub struct ColumnGenOpts {
    pub base_lp_opts: LpOptions,
    /// Threshold for "active" candidates (x value > this triggers inclusion).
    pub x_active_threshold: f64,
    /// Max number of column-gen iterations.
    pub max_iters: u32,
}

impl Default for ColumnGenOpts {
    fn default() -> Self {
        Self {
            base_lp_opts: LpOptions::default(),
            x_active_threshold: 0.05,
            max_iters: 5,
        }
    }
}

/// Run the column-generated lifted LP.
///
/// Phase 1: standard LP (x + y) gives an upper bound and identifies
/// candidates with positive fractional x values.
/// Phase 2: lifted LP with z-vars ONLY for "active" candidates
/// (x value > opts.x_active_threshold in phase 1).
///
/// This dramatically reduces z-var count while preserving most of
/// the lifting's tightening power.
/// Cutting-plane lifted LP (v3).
///
/// Iteratively:
///   1. Solve current LP (standard at first; with cuts added later).
///   2. For each pair (p1,r1,p2,r2) where x1+x2 > 1+eps in current LP,
///      compute the potential z-value if McCormick were added.
///      Identify the top-K pairs with largest violation.
///   3. Add z-var + McCormick for those K pairs.
///   4. Re-solve.
///   5. Repeat until no more cuts found or max_iters reached.
///
/// Returns the final LP UB (always ≤ standard LP UB; should be tighter
/// if cuts are found that tighten the relaxation).
pub fn cutting_plane_lifted_lp_ub(
    puzzle: &Puzzle,
    board: &Board,
    opts: ColumnGenOpts,
) -> Result<LiftedLpUb, String> {
    // For now this is a stub — actual implementation needs incremental
    // model rebuilding which good_lp doesn't directly support. The
    // simpler path: solve once, then identify violations, then build a
    // NEW LP with added z-vars + McCormick, solve again, etc.
    //
    // Each iteration is essentially a fresh column_generated_lifted_lp_ub
    // call with progressively more z-vars.
    Err("cutting_plane_lifted_lp_ub: deferred (requires LP rebuild loop)".to_string())
}

pub fn column_generated_lifted_lp_ub(
    puzzle: &Puzzle,
    board: &Board,
    opts: ColumnGenOpts,
) -> Result<LiftedLpUb, String> {
    let w = puzzle.width;
    let h = puzzle.height;

    let bb = b_b_match_count(puzzle, board);
    let bi = b_i_constraints(puzzle, board);

    // Interior cells, hints, pinned pieces.
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

    // ============ PHASE 1: standard LP to get x-values ============
    eprintln!("[col-gen] Phase 1: standard LP to extract x-values");
    let t1 = std::time::Instant::now();
    let mut problem1 = ProblemVariables::new();
    let mut x_var1: HashMap<(Position, PieceId, Rotation), Variable> = HashMap::new();
    let mut x_per_cell1: HashMap<Position, Vec<(Variable, [u8; 4])>> = HashMap::new();
    let mut x_per_piece1: HashMap<PieceId, Vec<Variable>> = HashMap::new();
    for &c in &interior_cells {
        let cands = &cell_cands[&c];
        let mut cell_vars = Vec::with_capacity(cands.len());
        for &(pid, rot, e) in cands {
            let v = problem1.add(variable().min(0.0).max(1.0));
            x_var1.insert((c, pid, rot), v);
            cell_vars.push((v, e));
            x_per_piece1.entry(pid).or_default().push(v);
        }
        x_per_cell1.insert(c, cell_vars);
    }
    let max_color = (puzzle.color_count.saturating_sub(1)) as u8;
    let n_y1 = ii_edges.len() * max_color as usize;
    let y_list1: Vec<Variable> = problem1.add_vector(variable().min(0.0).max(1.0), n_y1);
    let n_y_bi1 = bi.len();
    let y_bi_list1: Vec<Variable> = problem1.add_vector(variable().min(0.0).max(1.0), n_y_bi1);

    let obj1: Expression = y_list1.iter().copied().sum::<Expression>()
        + y_bi_list1.iter().copied().sum::<Expression>();
    let mut hp1 = problem1.maximise(obj1).using(highs);
    hp1.set_verbose(false);
    let mut hp1 = hp1.set_time_limit(opts.base_lp_opts.time_limit_secs);
    if opts.base_lp_opts.threads > 1 {
        hp1 = hp1.set_threads(opts.base_lp_opts.threads);
        hp1 = hp1.set_parallel(good_lp::solvers::highs::HighsParallelType::On);
    }
    if opts.base_lp_opts.use_ipm { hp1 = hp1.set_solver(HighsSolverType::Ipm); }
    hp1 = hp1.set_presolve(good_lp::solvers::highs::HighsPresolveType::On);
    let mut model1 = hp1;

    // Constraints (same as standard LP).
    for &c in &interior_cells {
        let sum: Expression = x_per_cell1[&c].iter().map(|&(v,_)| v).sum();
        model1 = model1.with(constraint!(sum == 1.0));
    }
    for (_pid, vars) in &x_per_piece1 {
        let sum: Expression = vars.iter().copied().sum();
        model1 = model1.with(constraint!(sum == 1.0));
    }
    for (&c, &(pid, rot)) in &hint_at {
        let v = x_var1[&(c, pid, rot)];
        model1 = model1.with(constraint!(v == 1.0));
    }
    for (i, &(cell, side, color)) in bi.iter().enumerate() {
        let y_bi_v = y_bi_list1[i];
        let supply: Expression = x_per_cell1[&cell].iter()
            .filter(|(_, e)| e[side as usize] == color)
            .map(|&(v, _)| v).sum();
        model1 = model1.with(constraint!(y_bi_v <= supply));
    }
    for (i, &(c1, c2, dir)) in ii_edges.iter().enumerate() {
        let (s1, s2) = if dir == 0 { (1u8, 3u8) } else { (2u8, 0u8) };
        let mut a_b: Vec<Vec<Variable>> = vec![Vec::new(); (max_color as usize) + 1];
        let mut b_b: Vec<Vec<Variable>> = vec![Vec::new(); (max_color as usize) + 1];
        for &(v, e) in &x_per_cell1[&c1] {
            let k = e[s1 as usize] as usize;
            if k > 0 { a_b[k].push(v); }
        }
        for &(v, e) in &x_per_cell1[&c2] {
            let k = e[s2 as usize] as usize;
            if k > 0 { b_b[k].push(v); }
        }
        for k in 1..=max_color as usize {
            let yv = y_list1[i * max_color as usize + (k - 1)];
            let a: Expression = a_b[k].iter().copied().sum();
            let b: Expression = b_b[k].iter().copied().sum();
            model1 = model1.with(constraint!(yv <= a));
            model1 = model1.with(constraint!(yv <= b));
        }
    }
    let sol1 = model1.solve().map_err(|e| format!("phase-1 LP: {e:?}"))?;
    let phase1_secs = t1.elapsed().as_secs_f64();
    eprintln!("[col-gen] Phase 1 LP solved in {:.1}s", phase1_secs);

    // Extract x-values per cell for "active" candidates.
    let thresh = opts.x_active_threshold;
    let mut active_cands: HashMap<Position, Vec<(PieceId, Rotation, [u8; 4])>> = HashMap::new();
    let mut total_active = 0usize;
    for &c in &interior_cells {
        let cands = &cell_cands[&c];
        let mut active = Vec::new();
        for &(pid, rot, e) in cands {
            let v = x_var1[&(c, pid, rot)];
            let val = sol1.value(v);
            if val > thresh {
                active.push((pid, rot, e));
            }
        }
        if active.is_empty() {
            // Fall back: include all candidates (shouldn't happen for hints).
            active = cands.clone();
        }
        total_active += active.len();
        active_cands.insert(c, active);
    }
    let avg_active = total_active as f64 / interior_cells.len() as f64;
    eprintln!("[col-gen] {} active candidates total, avg {:.1} per cell (threshold {})",
              total_active, avg_active, thresh);

    // ============ PHASE 2: lifted LP with z-vars only for active candidates ============
    eprintln!("[col-gen] Phase 2: lifted LP with restricted z-vars");
    let t2 = std::time::Instant::now();
    let mut problem2 = ProblemVariables::new();
    let mut x_var2: HashMap<(Position, PieceId, Rotation), Variable> = HashMap::new();
    let mut x_per_cell2: HashMap<Position, Vec<(Variable, [u8; 4])>> = HashMap::new();
    let mut x_per_piece2: HashMap<PieceId, Vec<Variable>> = HashMap::new();
    let mut total_x2 = 0usize;
    // KEEP ALL x-vars (not just active) for correctness — only z-vars are restricted.
    for &c in &interior_cells {
        let cands = &cell_cands[&c];
        let mut cell_vars = Vec::with_capacity(cands.len());
        for &(pid, rot, e) in cands {
            let v = problem2.add(variable().min(0.0).max(1.0));
            x_var2.insert((c, pid, rot), v);
            cell_vars.push((v, e));
            x_per_piece2.entry(pid).or_default().push(v);
            total_x2 += 1;
        }
        x_per_cell2.insert(c, cell_vars);
    }

    // Now z-vars: only for (active1, active2) pairs that are color-matched.
    let mut z_var2: HashMap<(usize, PieceId, Rotation, PieceId, Rotation), Variable> = HashMap::new();
    let mut z_per_edge2: Vec<Vec<Variable>> = vec![Vec::new(); ii_edges.len()];
    let mut z_count = 0usize;
    for (ei, &(c1, c2, dir)) in ii_edges.iter().enumerate() {
        let (s1, s2) = if dir == 0 { (1u8, 3u8) } else { (2u8, 0u8) };
        let a1 = &active_cands[&c1];
        let a2 = &active_cands[&c2];
        for &(pid1, rot1, e1) in a1 {
            let color1 = e1[s1 as usize];
            if color1 == 0 { continue; }
            for &(pid2, rot2, e2) in a2 {
                let color2 = e2[s2 as usize];
                if color1 != color2 { continue; }
                if pid1 == pid2 { continue; }
                let z = problem2.add(variable().min(0.0).max(1.0));
                z_var2.insert((ei, pid1, rot1, pid2, rot2), z);
                z_per_edge2[ei].push(z);
                z_count += 1;
            }
        }
    }
    let avg_z = if ii_edges.is_empty() { 0.0 } else { z_count as f64 / ii_edges.len() as f64 };
    eprintln!("[col-gen] Phase 2: {} z-vars total, avg {:.1} per edge", z_count, avg_z);

    // ALSO add y-vars (standard LP per-edge, per-color) as fallback for inactive pairs.
    let n_y2 = ii_edges.len() * max_color as usize;
    let y_list2: Vec<Variable> = problem2.add_vector(variable().min(0.0).max(1.0), n_y2);

    let n_y_bi2 = bi.len();
    let y_bi_list2: Vec<Variable> = problem2.add_vector(variable().min(0.0).max(1.0), n_y_bi2);

    // Objective: z-credit + y-fallback (with per-edge cap = 1) + B-I.
    // Per-edge cap below ensures total ≤ 1 = correctness.
    let obj2: Expression = z_var2.values().copied().sum::<Expression>()
        + y_list2.iter().copied().sum::<Expression>()
        + y_bi_list2.iter().copied().sum::<Expression>();
    let mut hp2 = problem2.maximise(obj2).using(highs);
    hp2.set_verbose(opts.base_lp_opts.verbose);
    let mut hp2 = hp2.set_time_limit(opts.base_lp_opts.time_limit_secs);
    if opts.base_lp_opts.threads > 1 {
        hp2 = hp2.set_threads(opts.base_lp_opts.threads);
        hp2 = hp2.set_parallel(good_lp::solvers::highs::HighsParallelType::On);
    }
    if opts.base_lp_opts.use_ipm { hp2 = hp2.set_solver(HighsSolverType::Ipm); }
    hp2 = hp2.set_presolve(good_lp::solvers::highs::HighsPresolveType::On);
    let mut model2 = hp2;

    // Constraints in phase 2.
    for &c in &interior_cells {
        let sum: Expression = x_per_cell2[&c].iter().map(|&(v,_)| v).sum();
        model2 = model2.with(constraint!(sum == 1.0));
    }
    for (_pid, vars) in &x_per_piece2 {
        let sum: Expression = vars.iter().copied().sum();
        model2 = model2.with(constraint!(sum == 1.0));
    }
    for (&c, &(pid, rot)) in &hint_at {
        let v = x_var2[&(c, pid, rot)];
        model2 = model2.with(constraint!(v == 1.0));
    }
    for (i, &(cell, side, color)) in bi.iter().enumerate() {
        let y_bi_v = y_bi_list2[i];
        let supply: Expression = x_per_cell2[&cell].iter()
            .filter(|(_, e)| e[side as usize] == color)
            .map(|&(v, _)| v).sum();
        model2 = model2.with(constraint!(y_bi_v <= supply));
    }
    // McCormick + per-edge cuts for each z-var.
    let mut n_mc = 0usize;
    for (ei, &(c1, c2, dir)) in ii_edges.iter().enumerate() {
        let (s1, s2) = if dir == 0 { (1u8, 3u8) } else { (2u8, 0u8) };
        let a1 = &active_cands[&c1];
        let a2 = &active_cands[&c2];
        for &(pid1, rot1, e1) in a1 {
            let color1 = e1[s1 as usize];
            if color1 == 0 { continue; }
            for &(pid2, rot2, e2) in a2 {
                let color2 = e2[s2 as usize];
                if color1 != color2 { continue; }
                if pid1 == pid2 { continue; }
                let z = z_var2[&(ei, pid1, rot1, pid2, rot2)];
                let x1 = x_var2[&(c1, pid1, rot1)];
                let x2 = x_var2[&(c2, pid2, rot2)];
                model2 = model2.with(constraint!(z <= x1));
                model2 = model2.with(constraint!(z <= x2));
                model2 = model2.with(constraint!(z >= x1 + x2 - 1.0));
                n_mc += 3;
            }
        }
    }
    // Add y-var standard LP constraints (per edge × per color, y ≤ side mass).
    for (i, &(c1, c2, dir)) in ii_edges.iter().enumerate() {
        let (s1, s2) = if dir == 0 { (1u8, 3u8) } else { (2u8, 0u8) };
        let mut a_b: Vec<Vec<Variable>> = vec![Vec::new(); (max_color as usize) + 1];
        let mut b_b: Vec<Vec<Variable>> = vec![Vec::new(); (max_color as usize) + 1];
        for &(v, e) in &x_per_cell2[&c1] {
            let k = e[s1 as usize] as usize;
            if k > 0 { a_b[k].push(v); }
        }
        for &(v, e) in &x_per_cell2[&c2] {
            let k = e[s2 as usize] as usize;
            if k > 0 { b_b[k].push(v); }
        }
        for k in 1..=max_color as usize {
            let yv = y_list2[i * max_color as usize + (k - 1)];
            let a: Expression = a_b[k].iter().copied().sum();
            let b: Expression = b_b[k].iter().copied().sum();
            model2 = model2.with(constraint!(yv <= a));
            model2 = model2.with(constraint!(yv <= b));
        }
    }

    // Per-edge cap: sum(z over this edge) + sum(y over this edge) ≤ 1
    // Ensures total match credit ≤ 1 per edge (correctness).
    for (ei, _) in ii_edges.iter().enumerate() {
        let mut terms: Vec<Variable> = z_per_edge2[ei].clone();
        for k in 1..=max_color as usize {
            terms.push(y_list2[ei * max_color as usize + (k - 1)]);
        }
        if terms.is_empty() { continue; }
        let sum: Expression = terms.into_iter().sum();
        model2 = model2.with(constraint!(sum <= 1.0));
    }

    let sol2 = model2.solve().map_err(|e| format!("phase-2 LP: {e:?}"))?;
    let phase2_secs = t2.elapsed().as_secs_f64();
    eprintln!("[col-gen] Phase 2 LP solved in {:.1}s", phase2_secs);

    let z_sum: f64 = z_var2.values().map(|v| sol2.value(*v)).sum();
    let y_sum: f64 = y_list2.iter().map(|v| sol2.value(*v)).sum();
    let interior_ub = z_sum + y_sum;
    let bi_ub: f64 = y_bi_list2.iter().map(|v| sol2.value(*v)).sum();
    let total = bb as f64 + bi_ub + interior_ub;
    eprintln!("[col-gen] Phase 2: z_sum={:.3}, y_sum={:.3}, bi_ub={:.3}, total={:.3}",
              z_sum, y_sum, bi_ub, total);

    Ok(LiftedLpUb {
        bb_matches: bb,
        bi_ub,
        interior_ub,
        total_ub: total,
        n_x: total_x2,
        n_z: z_count,
        n_y_bi: n_y_bi2,
        n_constraints: interior_cells.len() + x_per_piece2.len() + hint_at.len()
            + n_y_bi2 + n_mc + ii_edges.len(),
        n_z_per_edge_avg: avg_z,
        solve_secs: phase1_secs + phase2_secs,
    })
}

/// Same `cell_candidates` logic as `border_ub` (private there). Recomputed here.
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

/// Compute the lifted LP UB on interior score given a fixed border board.
pub fn lifted_lp_ub(puzzle: &Puzzle, board: &Board) -> Result<LiftedLpUb, String> {
    lifted_lp_ub_with(puzzle, board, LpOptions::default())
}

pub fn lifted_lp_ub_with(
    puzzle: &Puzzle,
    board: &Board,
    opts: LpOptions,
) -> Result<LiftedLpUb, String> {
    let w = puzzle.width;
    let h = puzzle.height;

    let bb = b_b_match_count(puzzle, board);
    let bi = b_i_constraints(puzzle, board);

    // Interior cells, hints, pinned pieces.
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

    // Candidate lists per cell.
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

    // I-I edges.
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

    // ============ Build LP ============
    let mut problem = ProblemVariables::new();

    // x-vars: per (cell, piece, rotation), as in standard LP.
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
            // Warmstart: 1.0 if hint, else 0.0 (no warmstart for non-hint).
            if let Some(&(hpid, hrot)) = hint_at.get(&c) {
                if pid == hpid && rot == hrot {
                    vd = vd.initial(1.0);
                } else {
                    vd = vd.initial(0.0);
                }
            }
            let v = problem.add(vd);
            x_var.insert((c, pid, rot), v);
            cell_vars.push((v, e));
            x_per_piece.entry(pid).or_default().push(v);
            total_x += 1;
        }
        x_per_cell.insert(c, cell_vars);
    }

    // z-vars: for each I-I edge × color-matched (cand1, cand2) pair.
    // z_vars_by_edge[edge_idx] = Vec<(Variable, p1, r1, p2, r2)> (annotations
    // for diagnostics).
    let mut z_var: HashMap<(usize, PieceId, Rotation, PieceId, Rotation), Variable> = HashMap::new();
    let mut z_per_edge: Vec<Vec<Variable>> = vec![Vec::new(); ii_edges.len()];
    let mut z_count_per_edge: Vec<usize> = vec![0; ii_edges.len()];

    for (ei, &(c1, c2, dir)) in ii_edges.iter().enumerate() {
        let (s1, s2) = if dir == 0 { (1u8, 3u8) } else { (2u8, 0u8) };
        let cands1 = &cell_cands[&c1];
        let cands2 = &cell_cands[&c2];
        for &(pid1, rot1, e1) in cands1 {
            let color1 = e1[s1 as usize];
            if color1 == 0 { continue; } // BORDER, skip
            for &(pid2, rot2, e2) in cands2 {
                let color2 = e2[s2 as usize];
                if color1 != color2 { continue; } // not color-matched
                if pid1 == pid2 { continue; } // can't use same piece twice
                let z = problem.add(variable().min(0.0).max(1.0));
                z_var.insert((ei, pid1, rot1, pid2, rot2), z);
                z_per_edge[ei].push(z);
                z_count_per_edge[ei] += 1;
            }
        }
    }
    let n_z = z_count_per_edge.iter().sum::<usize>();
    let n_z_per_edge_avg = if ii_edges.is_empty() { 0.0 } else { n_z as f64 / ii_edges.len() as f64 };
    eprintln!("Lifted LP: {} z-vars total, avg {:.1} per I-I edge", n_z, n_z_per_edge_avg);

    // y_bi vars: per B-I edge (same as standard LP, no lifting here).
    let n_y_bi = bi.len();
    let y_bi_list: Vec<Variable> = (0..n_y_bi)
        .map(|_| problem.add({
            let mut vd = variable().min(0.0).max(1.0);
            if opts.integer { vd = vd.binary(); }
            vd
        }))
        .collect();

    // Objective: sum of all z + sum of y_bi.
    let obj_z: Expression = z_var.values().copied().sum();
    let obj_bi: Expression = y_bi_list.iter().copied().sum();
    let obj: Expression = obj_z + obj_bi;

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

    // ============ Constraints ============
    // Cell coverage: ∀c interior, Σ x[c, _, _] = 1.
    for &c in &interior_cells {
        let cell_vars = &x_per_cell[&c];
        let sum: Expression = cell_vars.iter().map(|&(v, _)| v).sum();
        model = model.with(constraint!(sum == 1.0));
    }

    // Piece usage: ∀p interior used, Σ x[_, p, _] = 1.
    for (_pid, vars) in &x_per_piece {
        let sum: Expression = vars.iter().copied().sum();
        model = model.with(constraint!(sum == 1.0));
    }

    // Hint pins.
    for (&c, &(pid, rot)) in &hint_at {
        let v = x_var[&(c, pid, rot)];
        model = model.with(constraint!(v == 1.0));
    }

    // B-I constraints: y_bi[i] ≤ Σ x[c, p, r where rotated-edge[side] = color].
    for (i, &(cell, side, color)) in bi.iter().enumerate() {
        let y_bi_v = y_bi_list[i];
        let supply: Expression = x_per_cell[&cell].iter()
            .filter(|(_, e)| e[side as usize] == color)
            .map(|&(v, _)| v)
            .sum();
        model = model.with(constraint!(y_bi_v <= supply));
        if opts.force_bi_match.contains(&(cell, side, color)) {
            model = model.with(constraint!(y_bi_v == 1.0));
        }
    }

    // ===== The lifting constraints: McCormick on each z =====
    // For each I-I edge (c1, c2) and each (p1,r1,p2,r2) we instantiated:
    //   z ≤ x[c1, p1, r1]
    //   z ≤ x[c2, p2, r2]
    //   z ≥ x[c1, p1, r1] + x[c2, p2, r2] - 1
    let mut n_mccormick_constraints = 0usize;
    for (ei, &(c1, c2, _dir)) in ii_edges.iter().enumerate() {
        let cands1 = &cell_cands[&c1];
        let cands2 = &cell_cands[&c2];
        let (s1, s2) = {
            let (_, _, d) = ii_edges[ei];
            if d == 0 { (1u8, 3u8) } else { (2u8, 0u8) }
        };
        for &(pid1, rot1, e1) in cands1 {
            let color1 = e1[s1 as usize];
            if color1 == 0 { continue; }
            for &(pid2, rot2, e2) in cands2 {
                let color2 = e2[s2 as usize];
                if color1 != color2 { continue; }
                if pid1 == pid2 { continue; }
                let key = (ei, pid1, rot1, pid2, rot2);
                let z = z_var[&key];
                let x1 = x_var[&(c1, pid1, rot1)];
                let x2 = x_var[&(c2, pid2, rot2)];
                model = model.with(constraint!(z <= x1));
                model = model.with(constraint!(z <= x2));
                model = model.with(constraint!(z >= x1 + x2 - 1.0));
                n_mccormick_constraints += 3;
            }
        }
    }

    // Also: per-edge sum-of-z ≤ 1 (at most one (p1,r1,p2,r2) pair matches per edge).
    // This is a *valid* cut tightening the LP further.
    for ei in 0..ii_edges.len() {
        if z_per_edge[ei].is_empty() { continue; }
        let sum: Expression = z_per_edge[ei].iter().copied().sum();
        model = model.with(constraint!(sum <= 1.0));
    }
    let n_edge_sum_constraints = ii_edges.len();

    let n_constraints = interior_cells.len() + x_per_piece.len() + hint_at.len()
        + bi.len() + n_mccormick_constraints + n_edge_sum_constraints;

    let t0 = std::time::Instant::now();
    let sol = model.solve().map_err(|e| format!("Lifted LP solve: {e:?}"))?;
    let solve_secs = t0.elapsed().as_secs_f64();

    let interior_ub: f64 = z_var.values().map(|v| sol.value(*v)).sum();
    let bi_ub: f64 = y_bi_list.iter().map(|v| sol.value(*v)).sum();
    let total = bb as f64 + bi_ub + interior_ub;

    Ok(LiftedLpUb {
        bb_matches: bb,
        bi_ub,
        interior_ub,
        total_ub: total,
        n_x: total_x,
        n_z,
        n_y_bi,
        n_constraints,
        n_z_per_edge_avg,
        solve_secs,
    })
}
