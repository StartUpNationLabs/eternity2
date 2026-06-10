// Exact border attach (HiGHS MIP), ported from vol-211 cloister_border.rs.
// Given a complete interior, assign the 60 border pieces to the ring
// (rotations forced grey-outward) maximizing BB + IB. Control: re-attaching
// the Bucas-469 interior recovers exactly 469 — the attach side is
// optimal-grade; rim-compatibility lives in the interior (vol-211 ★).

use std::collections::HashMap;

use eternity2_core::{Puzzle, BORDER};
use good_lp::{
    constraint, solvers::highs::highs, Expression, ProblemVariables, Solution, SolverModel,
    Variable, variable,
};

use crate::frame::{is_ring, W};

pub struct AttachOpts {
    pub time_limit_secs: f64,
    pub require_bb60: bool,
}

impl Default for AttachOpts {
    fn default() -> Self {
        Self { time_limit_secs: 120.0, require_bb60: false }
    }
}

pub struct AttachResult {
    /// full 256-cell placement (interior + ring)
    pub placement: Vec<(usize, u16, u8)>,
    pub obj: f64,
}

fn ring_positions() -> Vec<usize> {
    let mut v = Vec::with_capacity(60);
    for x in 0..W {
        v.push(x);
    }
    for y in 1..W {
        v.push(y * W + (W - 1));
    }
    for x in (0..W - 1).rev() {
        v.push((W - 1) * W + x);
    }
    for y in (1..W - 1).rev() {
        v.push(y * W);
    }
    v
}

fn is_corner(pos: usize) -> bool {
    pos == 0 || pos == W - 1 || pos == W * (W - 1) || pos == W * W - 1
}

/// the rotation putting grey side(s) exactly outward at `pos`, as edges
fn forced_rotation(pos: usize, base: [u8; 4]) -> Option<[u8; 4]> {
    let (y, x) = (pos / W, pos % W);
    let mut need_grey = Vec::new();
    if y == 0 {
        need_grey.push(0);
    }
    if y == W - 1 {
        need_grey.push(2);
    }
    if x == 0 {
        need_grey.push(3);
    }
    if x == W - 1 {
        need_grey.push(1);
    }
    for r in 0..4u8 {
        let e: [u8; 4] = core::array::from_fn(|s| base[(s + 4 - r as usize) % 4]);
        if need_grey.iter().all(|&s| e[s] == BORDER)
            && e.iter().filter(|&&c| c == BORDER).count() == need_grey.len()
        {
            return Some(e);
        }
    }
    None
}

#[allow(clippy::too_many_lines)]
pub fn attach(
    puzzle: &Puzzle,
    interior: &[(usize, u16, u8)],
    opts: &AttachOpts,
) -> Result<AttachResult, String> {
    let mut interior_place: HashMap<usize, (u16, u8)> = HashMap::new();
    for &(pos, pid, rot) in interior {
        if !is_ring(pos) {
            interior_place.insert(pos, (pid, rot));
        }
    }
    if interior_place.len() != 196 {
        return Err(format!("need full 196-cell interior, got {}", interior_place.len()));
    }
    let edges_of = |pid: u16, rot: u8| -> [u8; 4] {
        puzzle
            .piece(pid)
            .expect("piece")
            .edges
            .rotated(eternity2_core::Rotation::from_u8(rot).expect("rot"))
            .as_array()
    };

    let ring = ring_positions();
    let mut rim_color: HashMap<usize, u8> = HashMap::new();
    for &pos in &ring {
        if is_corner(pos) {
            continue;
        }
        let (y, x) = (pos / W, pos % W);
        let (npos, their_side) = if y == 0 {
            (pos + W, 0)
        } else if y == W - 1 {
            (pos - W, 2)
        } else if x == 0 {
            (pos + 1, 3)
        } else {
            (pos - 1, 1)
        };
        let (pid, rot) = interior_place[&npos];
        rim_color.insert(pos, edges_of(pid, rot)[their_side]);
    }

    let mut corner_pieces: Vec<u16> = Vec::new();
    let mut edge_pieces: Vec<u16> = Vec::new();
    for pid in 0..256u16 {
        let e = puzzle.piece(pid).expect("piece").edges.as_array();
        match e.iter().filter(|&&c| c == BORDER).count() {
            2 => corner_pieces.push(pid),
            1 => edge_pieces.push(pid),
            _ => {}
        }
    }
    let corner_positions: Vec<usize> = ring.iter().copied().filter(|&p| is_corner(p)).collect();
    let side_positions: Vec<usize> = ring.iter().copied().filter(|&p| !is_corner(p)).collect();
    let oriented = |pid: u16, pos: usize| -> Option<[u8; 4]> {
        forced_rotation(pos, puzzle.piece(pid).expect("piece").edges.as_array())
    };

    let mut prob = ProblemVariables::new();
    let mut x: HashMap<(u16, usize), Variable> = HashMap::new();
    for &p in &corner_pieces {
        for &q in &corner_positions {
            if oriented(p, q).is_some() {
                x.insert((p, q), prob.add(variable().binary()));
            }
        }
    }
    for &p in &edge_pieces {
        for &q in &side_positions {
            if oriented(p, q).is_some() {
                x.insert((p, q), prob.add(variable().binary()));
            }
        }
    }
    let n_ring = ring.len();
    let side_toward = |from: usize, to: usize| -> usize {
        let (fy, fx) = (from / W, from % W);
        let (ty, tx) = (to / W, to % W);
        if ty == fy {
            if tx == fx + 1 { 1 } else { 3 }
        } else if ty == fy + 1 {
            2
        } else {
            0
        }
    };
    let all_pieces_at = |q: usize| -> &[u16] {
        if is_corner(q) {
            &corner_pieces
        } else {
            &edge_pieces
        }
    };
    let mut constraints: Vec<good_lp::Constraint> = Vec::new();
    let mut z_vars: Vec<(usize, Vec<(u8, Variable)>)> = Vec::new();
    for i in 0..n_ring {
        let a = ring[i];
        let b = ring[(i + 1) % n_ring];
        let sa = side_toward(a, b);
        let mut colors: Vec<u8> = Vec::new();
        for &p in all_pieces_at(a) {
            if let Some(e) = oriented(p, a) {
                if !colors.contains(&e[sa]) {
                    colors.push(e[sa]);
                }
            }
        }
        let zc: Vec<(u8, Variable)> = colors
            .into_iter()
            .map(|c| (c, prob.add(variable().binary())))
            .collect();
        z_vars.push((i, zc));
    }

    let mut obj = Expression::from(0.0);
    for (_, zc) in &z_vars {
        for &(_, z) in zc {
            obj += z;
        }
    }
    for (&(p, q), &xv) in &x {
        if !is_corner(q) {
            let e = oriented(p, q).expect("legal");
            let (y, xx) = (q / W, q % W);
            let inward = if y == 0 {
                2
            } else if y == W - 1 {
                0
            } else if xx == 0 {
                1
            } else {
                3
            };
            if rim_color[&q] == e[inward] {
                obj += xv;
            }
        }
    }

    for &p in corner_pieces.iter().chain(edge_pieces.iter()) {
        let mut s = Expression::from(0.0);
        for ((pp, _), &xv) in &x {
            if *pp == p {
                s += xv;
            }
        }
        constraints.push(constraint!(s == 1.0));
    }
    for &q in corner_positions.iter().chain(side_positions.iter()) {
        let mut s = Expression::from(0.0);
        for ((_, qq), &xv) in &x {
            if *qq == q {
                s += xv;
            }
        }
        constraints.push(constraint!(s == 1.0));
    }
    if opts.require_bb60 {
        let mut all_z = Expression::from(0.0);
        for (_, zc) in &z_vars {
            for &(_, z) in zc {
                all_z += z;
            }
        }
        constraints.push(constraint!(all_z == 60.0));
    }
    for (i, zc) in &z_vars {
        let a = ring[*i];
        let b = ring[(*i + 1) % n_ring];
        let sa = side_toward(a, b);
        let sb = side_toward(b, a);
        let mut z_sum = Expression::from(0.0);
        for &(c, z) in zc {
            let mut sup_a = Expression::from(0.0);
            for &p in all_pieces_at(a) {
                if let Some(e) = oriented(p, a) {
                    if e[sa] == c {
                        if let Some(&xv) = x.get(&(p, a)) {
                            sup_a += xv;
                        }
                    }
                }
            }
            let mut sup_b = Expression::from(0.0);
            for &p in all_pieces_at(b) {
                if let Some(e) = oriented(p, b) {
                    if e[sb] == c {
                        if let Some(&xv) = x.get(&(p, b)) {
                            sup_b += xv;
                        }
                    }
                }
            }
            constraints.push(constraint!(z - sup_a <= 0.0));
            constraints.push(constraint!(z - sup_b <= 0.0));
            z_sum += z;
        }
        constraints.push(constraint!(z_sum <= 1.0));
    }

    let mut model = prob.maximise(obj.clone()).using(highs);
    model = model.set_time_limit(opts.time_limit_secs);
    model = model.set_parallel(good_lp::solvers::highs::HighsParallelType::On);
    for c in constraints {
        model = model.with(c);
    }
    let sol = model.solve().map_err(|e| format!("MIP solve: {e:?}"))?;
    let obj_val = sol.eval(&obj);

    let mut placement: Vec<(usize, u16, u8)> = interior_place
        .iter()
        .map(|(&pos, &(p, r))| (pos, p, r))
        .collect();
    let mut placed_ring = 0;
    for (&(p, q), &xv) in &x {
        if sol.value(xv) > 0.5 {
            let base = puzzle.piece(p).expect("piece").edges.as_array();
            let target = oriented(p, q).expect("legal");
            for r in 0..4u8 {
                let e: [u8; 4] = core::array::from_fn(|s| base[(s + 4 - r as usize) % 4]);
                if e == target {
                    placement.push((q, p, r));
                    placed_ring += 1;
                    break;
                }
            }
        }
    }
    if placed_ring != 60 {
        return Err(format!("ring assignment incomplete: {placed_ring}/60"));
    }
    placement.sort_unstable();
    Ok(AttachResult { placement, obj: obj_val })
}
