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
