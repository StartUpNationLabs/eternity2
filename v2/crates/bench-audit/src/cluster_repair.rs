// Cluster-repair MIP: rearrange the pieces in a small subset of cells
// to maximise matched edges (internal + boundary), holding all other
// cells fixed.
//
// Option (a) (this module): permute existing pieces in the cluster.

use std::collections::{HashMap, HashSet};

use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use good_lp::{
    constraint, solvers::highs::{highs, HighsSolverType},
    Expression, ProblemVariables, Solution, SolverModel, Variable, variable,
};

/// Result of a cluster repair.
#[derive(Debug, Clone)]
pub struct ClusterRepair {
    /// New (cell -> (piece_id, rotation)) assignments. Only K cells.
    pub assignments: Vec<(Position, PieceId, Rotation)>,
    /// Score delta (new internal+boundary matches − old).
    pub delta: i32,
    /// Total objective from MIP (matched edges in E_in + E_bdy).
    pub obj_value: f64,
    /// Solve time.
    pub solve_secs: f64,
}

#[derive(Debug, Clone, Copy)]
pub struct ClusterOptions {
    pub time_limit_secs: f64,
    pub threads: u32,
    pub verbose: bool,
}

impl Default for ClusterOptions {
    fn default() -> Self { ClusterOptions { time_limit_secs: 60.0, threads: 4, verbose: false } }
}

/// Given a board and a region of cells R, solve a small MIP that permutes
/// the pieces currently in R (with rotation choice) to maximise matched edges
/// internal to R and on R's external boundary. All cells outside R are
/// held fixed.
///
/// Setting R = a single mismatch cluster gives "option (a)" — within-cluster
/// permutation. Setting R = cluster ∪ halo gives "option (b)" — local
/// neighbourhood swap.
pub fn repair_cluster(
    puzzle: &Puzzle,
    board: &Board,
    cluster: &[Position],
    opts: ClusterOptions,
) -> Result<ClusterRepair, String> {
    let w = puzzle.width;
    let h = puzzle.height;
    let cluster_set: HashSet<Position> = cluster.iter().copied().collect();

    // Current pieces in K.
    let mut pieces: Vec<(PieceId, Rotation, [u8; 4])> = Vec::with_capacity(cluster.len());
    for &c in cluster {
        let (pid, rot) = board.get(c).ok_or_else(|| format!("cell {c} not placed"))?;
        let p = puzzle.piece(pid).ok_or_else(|| format!("piece {pid} not found"))?;
        let e = p.edges.rotated(Rotation::R0).as_array();
        let _ = rot; // we don't need the current rotation here; we'll re-choose
        pieces.push((pid, Rotation::R0, e));
    }

    // Internal edges of K (cells both in K).
    let mut e_in: Vec<(Position, Position, u8)> = Vec::new();
    // (a, b, dir): dir=0 horizontal (a left, b right), dir=1 vertical (a top, b bottom).
    for &c in cluster {
        let (x, y) = puzzle.xy(c);
        if x + 1 < w {
            let n = y * w + (x + 1);
            if cluster_set.contains(&n) { e_in.push((c, n, 0)); }
        }
        if y + 1 < h {
            let n = (y + 1) * w + x;
            if cluster_set.contains(&n) { e_in.push((c, n, 1)); }
        }
    }

    // Boundary edges of K: (cell_in_K, side_of_cell, required_color_from_outside).
    // side = 0 top, 1 right, 2 bottom, 3 left.
    let mut e_bdy: Vec<(Position, u8, u8)> = Vec::new();
    for &c in cluster {
        let (x, y) = puzzle.xy(c);
        let nbrs: [(i64, i64, u8, u8); 4] = [
            (x as i64, y as i64 - 1, 0, 2),     // top neighbor, our side 0, their side 2
            (x as i64 + 1, y as i64, 1, 3),     // right
            (x as i64, y as i64 + 1, 2, 0),     // bottom
            (x as i64 - 1, y as i64, 3, 1),     // left
        ];
        for &(nx, ny, our_side, their_side) in &nbrs {
            if nx < 0 || ny < 0 || nx >= w as i64 || ny >= h as i64 { continue; }
            let n = (ny as u32) * w + (nx as u32);
            if cluster_set.contains(&n) { continue; }  // internal edge, handled above
            // Get the external neighbor's color on the shared side.
            if let Some((npid, nrot)) = board.get(n) {
                if let Some(np) = puzzle.piece(npid) {
                    let ne = np.edges.rotated(nrot).as_array();
                    let req_color = ne[their_side as usize];
                    e_bdy.push((c, our_side, req_color));
                }
            }
        }
    }

    // Build MIP.
    let mut problem = ProblemVariables::new();
    // x[i, c, r] for piece i in cluster at cell c with rotation r.
    let n_pieces = pieces.len();
    let mut x: HashMap<(usize, Position, Rotation), Variable> = HashMap::new();
    // Per-cell, per-rotation list of (piece_index, rotated_edges).
    // Used to build a[c, side, k] expressions.

    // For each piece i and rotation r, precompute rotated edges.
    let rotated_edges: Vec<[[u8; 4]; 4]> = pieces.iter().map(|(pid, _, _)| {
        let p = puzzle.piece(*pid).unwrap();
        let mut r4 = [[0u8; 4]; 4];
        for (k, &rot) in Rotation::ALL.iter().enumerate() {
            r4[k] = p.edges.rotated(rot).as_array();
        }
        r4
    }).collect();

    // Map cell -> (piece-index-in-`pieces`, current-rotation) for warmstart.
    let mut current_at: HashMap<Position, (usize, Rotation)> = HashMap::new();
    for &c in cluster {
        if let Some((bpid, brot)) = board.get(c) {
            for (i, &(pid, _, _)) in pieces.iter().enumerate() {
                if pid == bpid { current_at.insert(c, (i, brot)); break; }
            }
        }
    }

    for i in 0..n_pieces {
        for &c in cluster {
            for &r in &Rotation::ALL {
                let mut vd = variable().binary();
                if let Some(&(ci, crot)) = current_at.get(&c) {
                    let val = if ci == i && crot == r { 1.0 } else { 0.0 };
                    vd = vd.initial(val);
                }
                let v = problem.add(vd);
                x.insert((i, c, r), v);
            }
        }
    }

    // y vars: per internal edge, per color. Warmstart from the current board:
    // for each internal edge, if the current pieces match at color k_current, set
    // y_in[ei, k_current] = 1, others = 0.
    let max_color = (puzzle.color_count.saturating_sub(1)) as u8;
    let mut y_in: HashMap<(usize, u8), Variable> = HashMap::new();
    for (ei, &(c1, c2, dir)) in e_in.iter().enumerate() {
        let (s1, s2) = if dir == 0 { (1u8, 3u8) } else { (2u8, 0u8) };
        let cur_match_color = {
            let (pid1, rot1) = board.get(c1).unwrap();
            let (pid2, rot2) = board.get(c2).unwrap();
            let e1 = puzzle.piece(pid1).unwrap().edges.rotated(rot1).as_array();
            let e2 = puzzle.piece(pid2).unwrap().edges.rotated(rot2).as_array();
            if e1[s1 as usize] == e2[s2 as usize] && e1[s1 as usize] != 0 {
                Some(e1[s1 as usize])
            } else {
                None
            }
        };
        for k in 1..=max_color {
            let init = if Some(k) == cur_match_color { 1.0 } else { 0.0 };
            y_in.insert((ei, k), problem.add(variable().binary().initial(init)));
        }
    }
    // y_bdy[bi]: 1 iff current cell matches the required boundary color.
    let mut y_bdy: Vec<Variable> = Vec::with_capacity(e_bdy.len());
    for &(c, side, kreq) in &e_bdy {
        let (pid, rot) = board.get(c).unwrap();
        let e = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
        let init = if e[side as usize] == kreq { 1.0 } else { 0.0 };
        y_bdy.push(problem.add(variable().binary().initial(init)));
    }

    // Objective.
    let obj_in: Expression = y_in.values().copied().sum();
    let obj_bdy: Expression = y_bdy.iter().copied().sum();
    let obj: Expression = obj_in + obj_bdy;

    let mut hp = problem.maximise(obj).using(highs);
    hp.set_verbose(opts.verbose);
    let mut hp = hp.set_time_limit(opts.time_limit_secs);
    if opts.threads > 1 {
        hp = hp.set_threads(opts.threads);
        hp = hp.set_parallel(good_lp::solvers::highs::HighsParallelType::On);
    }
    let mut model = hp;

    // Constraints.
    // Cell coverage: exactly one (piece, rot) at each cell.
    for &c in cluster {
        let mut terms: Vec<Variable> = Vec::new();
        for i in 0..n_pieces {
            for &r in &Rotation::ALL {
                terms.push(x[&(i, c, r)]);
            }
        }
        let sum: Expression = terms.into_iter().sum();
        model = model.with(constraint!(sum == 1.0));
    }
    // Piece usage: each piece placed exactly once.
    for i in 0..n_pieces {
        let mut terms: Vec<Variable> = Vec::new();
        for &c in cluster {
            for &r in &Rotation::ALL {
                terms.push(x[&(i, c, r)]);
            }
        }
        let sum: Expression = terms.into_iter().sum();
        model = model.with(constraint!(sum == 1.0));
    }

    // Helper: build a[c, side, k] expression: mass of cells (i, r) with rotated_edges[r][side] == k.
    let a_mass = |c: Position, side: u8, k: u8| -> Expression {
        let mut terms: Vec<Variable> = Vec::new();
        for i in 0..n_pieces {
            for (ri, &r) in Rotation::ALL.iter().enumerate() {
                if rotated_edges[i][ri][side as usize] == k {
                    terms.push(x[&(i, c, r)]);
                }
            }
        }
        terms.into_iter().sum::<Expression>()
    };

    // Internal edge constraints: y_in[ei, k] ≤ a[c1, s1, k], y_in[ei, k] ≤ a[c2, s2, k].
    for (ei, &(c1, c2, dir)) in e_in.iter().enumerate() {
        let (s1, s2) = if dir == 0 { (1u8, 3u8) } else { (2u8, 0u8) };
        for k in 1..=max_color {
            let yv = y_in[&(ei, k)];
            let a1 = a_mass(c1, s1, k);
            let a2 = a_mass(c2, s2, k);
            model = model.with(constraint!(yv <= a1));
            model = model.with(constraint!(yv <= a2));
        }
    }
    // Boundary edge constraints: y_bdy[bi] ≤ a[c, side, k*] (k* = required color from outside).
    for (bi, &(c, side, kreq)) in e_bdy.iter().enumerate() {
        let yv = y_bdy[bi];
        let a = a_mass(c, side, kreq);
        model = model.with(constraint!(yv <= a));
    }

    let t0 = std::time::Instant::now();
    let sol = model.solve().map_err(|e| format!("MIP solve: {e:?}"))?;
    let solve_secs = t0.elapsed().as_secs_f64();

    // Extract assignment.
    let mut assignments: Vec<(Position, PieceId, Rotation)> = Vec::with_capacity(cluster.len());
    for &c in cluster {
        let mut found = false;
        for i in 0..n_pieces {
            for &r in &Rotation::ALL {
                let v = x[&(i, c, r)];
                if sol.value(v) > 0.5 {
                    assignments.push((c, pieces[i].0, r));
                    found = true;
                    break;
                }
            }
            if found { break; }
        }
    }

    // Compute current internal+boundary matches in the input board.
    let mut old_obj = 0i32;
    for &(c1, c2, dir) in &e_in {
        let (s1, s2) = if dir == 0 { (1u8, 3u8) } else { (2u8, 0u8) };
        let (pid1, rot1) = board.get(c1).unwrap();
        let (pid2, rot2) = board.get(c2).unwrap();
        let e1 = puzzle.piece(pid1).unwrap().edges.rotated(rot1).as_array();
        let e2 = puzzle.piece(pid2).unwrap().edges.rotated(rot2).as_array();
        if e1[s1 as usize] == e2[s2 as usize] { old_obj += 1; }
    }
    for &(c, side, kreq) in &e_bdy {
        let (pid, rot) = board.get(c).unwrap();
        let e = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
        if e[side as usize] == kreq { old_obj += 1; }
    }

    let new_obj_int: i32 = y_in.values().map(|v| sol.value(*v).round() as i32).sum::<i32>()
        + y_bdy.iter().map(|v| sol.value(*v).round() as i32).sum::<i32>();

    Ok(ClusterRepair {
        assignments,
        delta: new_obj_int - old_obj,
        obj_value: new_obj_int as f64,
        solve_secs,
    })
}
