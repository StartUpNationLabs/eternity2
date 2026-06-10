// Max-(II+IB) annealer. With rim targets (CLOISTER-II) the objective is
// the true interior contribution to total score: II + IB at the exact 1:1
// exchange rate (position-exact targets — the only sound coupling weight,
// vol-211 H2/H3 ablation refuted proxy weights). Free-rim: plain max-II.
//
// Moves (vol-211 mix): rot 15%, conflict-biased best-rot swap 35%,
// window/band LNS with greedy refill 30%, exact-region B&B on worst
// windows the rest. exact_region folds rim targets into its fixed
// constraints, so regions touching the rim optimize IB jointly.

use std::time::Instant;

use crate::model::{InteriorModel, RimTargets};
use crate::rng::Rng;

pub struct SaParams {
    pub seed: u64,
    pub budget_ms: u64,
    pub hinted: bool,
    pub t0: f64,
}

impl Default for SaParams {
    fn default() -> Self {
        Self { seed: 1, budget_ms: 30_000, hinted: false, t0: 1.5 }
    }
}

pub struct SaResult {
    pub seed: u64,
    pub best_ii: u32,
    pub best_ib: u32,
    pub best_state: Vec<(u16, u8)>,
    pub moves: u64,
}

struct St<'a> {
    m: &'a InteriorModel,
    targets: Option<&'a RimTargets>,
    cell_piece: Vec<u16>,
    cell_rot: Vec<u8>,
    piece_cell: Vec<u16>,
}

impl St<'_> {
    fn edges_at(&self, cell: usize) -> [u8; 4] {
        self.m.rot_edges[self.cell_piece[cell] as usize][self.cell_rot[cell] as usize]
    }

    fn rim_at(&self, cell: usize) -> u32 {
        let Some(tg) = self.targets else { return 0 };
        let e = self.edges_at(cell);
        (0..4)
            .filter(|&s| tg[cell][s] == Some(e[s]))
            .count() as u32
    }

    /// matched score incident to `cell`: II edges + rim target sides
    fn local(&self, cell: usize) -> u32 {
        let n = self.m.n;
        let e = self.edges_at(cell);
        let (y, x) = (cell / n, cell % n);
        let mut m = 0;
        if x > 0 && self.edges_at(cell - 1)[1] == e[3] {
            m += 1;
        }
        if x + 1 < n && self.edges_at(cell + 1)[3] == e[1] {
            m += 1;
        }
        if y > 0 && self.edges_at(cell - n)[2] == e[0] {
            m += 1;
        }
        if y + 1 < n && self.edges_at(cell + n)[0] == e[2] {
            m += 1;
        }
        m + self.rim_at(cell)
    }

    /// matched score over a region, internal edges counted once
    fn region(&self, cells: &[usize], member: &[bool]) -> u32 {
        let n = self.m.n;
        let mut m = 0;
        for &cell in cells {
            let e = self.edges_at(cell);
            let (y, x) = (cell / n, cell % n);
            if x > 0 && self.edges_at(cell - 1)[1] == e[3] {
                m += 1;
            }
            if y > 0 && self.edges_at(cell - n)[2] == e[0] {
                m += 1;
            }
            if x + 1 < n && !member[cell + 1] && self.edges_at(cell + 1)[3] == e[1] {
                m += 1;
            }
            if y + 1 < n && !member[cell + n] && self.edges_at(cell + n)[0] == e[2] {
                m += 1;
            }
            m += self.rim_at(cell);
        }
        m
    }

    fn full(&self) -> u32 {
        let n = self.m.n;
        let mut m = 0;
        for cell in 0..self.m.cells {
            let e = self.edges_at(cell);
            let (y, x) = (cell / n, cell % n);
            if x + 1 < n && self.edges_at(cell + 1)[3] == e[1] {
                m += 1;
            }
            if y + 1 < n && self.edges_at(cell + n)[0] == e[2] {
                m += 1;
            }
            m += self.rim_at(cell);
        }
        m
    }
}

/// Optimal reassignment of the region's own pieces (incumbent-seeded B&B,
/// never worsening). Rim targets are folded in as fixed constraints.
fn exact_region(st: &St, cells: &[usize], member: &[bool], node_cap: u64) -> (Vec<(u16, u8)>, u32) {
    let m = st.m;
    let n = m.n;
    let k = cells.len();
    let mut idx_of = vec![usize::MAX; m.cells];
    for (j, &c) in cells.iter().enumerate() {
        idx_of[c] = j;
    }
    let mut fixed: Vec<Vec<(usize, u8)>> = vec![Vec::new(); k];
    let mut earlier: Vec<Vec<(usize, usize)>> = vec![Vec::new(); k];
    for (j, &c) in cells.iter().enumerate() {
        let (y, x) = (c / n, c % n);
        let nbs: [(bool, usize, usize, usize); 4] = [
            (x > 0, c.wrapping_sub(1), 3, 1),
            (x + 1 < n, c + 1, 1, 3),
            (y > 0, c.wrapping_sub(n), 0, 2),
            (y + 1 < n, c + n, 2, 0),
        ];
        for &(ok, nc, my_side, their_side) in &nbs {
            if !ok {
                continue;
            }
            if member[nc] {
                let i = idx_of[nc];
                if i < j {
                    earlier[j].push((my_side, i));
                }
            } else {
                fixed[j].push((my_side, st.edges_at(nc)[their_side]));
            }
        }
        if let Some(tg) = st.targets {
            for s in 0..4 {
                if let Some(col) = tg[c][s] {
                    fixed[j].push((s, col));
                }
            }
        }
    }
    let mut suffix_max = vec![0u32; k + 1];
    for j in (0..k).rev() {
        suffix_max[j] = suffix_max[j + 1] + (fixed[j].len() + earlier[j].len()) as u32;
    }
    let pool: Vec<u16> = cells.iter().map(|&c| st.cell_piece[c]).collect();
    let cur: Vec<(u16, u8)> = cells
        .iter()
        .map(|&c| (st.cell_piece[c], st.cell_rot[c]))
        .collect();
    let place_matches = |asn: &[(u16, u8)], j: usize, pid: u16, rot: u8| -> u32 {
        let e = m.rot_edges[pid as usize][rot as usize];
        let mut mm = 0;
        for &(side, color) in &fixed[j] {
            if e[side] == color {
                mm += 1;
            }
        }
        for &(side, i) in &earlier[j] {
            let (ip, ir) = asn[i];
            if e[side] == m.rot_edges[ip as usize][ir as usize][(side + 2) % 4] {
                mm += 1;
            }
        }
        mm
    };
    let mut best_asn = cur.clone();
    let mut best_m = {
        let mut t = 0;
        for j in 0..k {
            t += place_matches(&cur, j, cur[j].0, cur[j].1);
        }
        t
    };
    let region_max = suffix_max[0];
    if best_m == region_max {
        return (best_asn, best_m);
    }

    struct Ctx<'a> {
        k: usize,
        pool: &'a [u16],
        suffix_max: &'a [u32],
        region_max: u32,
        nodes: u64,
        cap: u64,
    }
    #[allow(clippy::too_many_arguments)]
    fn go(
        ctx: &mut Ctx,
        place: &dyn Fn(&[(u16, u8)], usize, u16, u8) -> u32,
        j: usize,
        mm: u32,
        used: &mut u32,
        asn: &mut Vec<(u16, u8)>,
        best_m: &mut u32,
        best_asn: &mut Vec<(u16, u8)>,
    ) {
        if ctx.nodes > ctx.cap {
            return;
        }
        if j == ctx.k {
            if mm > *best_m {
                *best_m = mm;
                best_asn.clone_from(asn);
                if mm == ctx.region_max {
                    ctx.nodes = ctx.cap + 1;
                }
            }
            return;
        }
        if mm + ctx.suffix_max[j] <= *best_m {
            return;
        }
        let mut order = [(0u32, 0u8, 0u8); 64];
        let mut no = 0;
        for (pi, &pid) in ctx.pool.iter().enumerate() {
            if *used >> pi & 1 == 1 {
                continue;
            }
            for rot in 0..4u8 {
                order[no] = (place(asn, j, pid, rot), pi as u8, rot);
                no += 1;
            }
        }
        order[..no].sort_unstable_by(|a, b| b.0.cmp(&a.0));
        for &(madd, pi, rot) in &order[..no] {
            let pi = pi as usize;
            ctx.nodes += 1;
            if ctx.nodes > ctx.cap {
                return;
            }
            *used |= 1 << pi;
            asn[j] = (ctx.pool[pi], rot);
            go(ctx, place, j + 1, mm + madd, used, asn, best_m, best_asn);
            *used &= !(1 << pi);
        }
    }
    let mut ctx = Ctx { k, pool: &pool, suffix_max: &suffix_max, region_max, nodes: 0, cap: node_cap };
    let mut asn = cur;
    let mut used = 0u32;
    go(&mut ctx, &place_matches, 0, 0, &mut used, &mut asn, &mut best_m, &mut best_asn);
    (best_asn, best_m)
}

/// greedy completion of a partial scan prefix into a full assignment
/// (rim targets scored); used to seed SA from a DFS prefix
#[must_use]
pub fn greedy_complete(
    model: &InteriorModel,
    targets: Option<&RimTargets>,
    prefix_cells: &[(usize, (u16, u8))],
) -> Vec<(u16, u8)> {
    let n = model.n;
    let mut grid: Vec<(u16, u8)> = vec![(u16::MAX, 0); model.cells];
    let mut used = vec![false; model.np];
    for &(cell, (pid, rot)) in prefix_cells {
        grid[cell] = (pid, rot);
        used[pid as usize] = true;
    }
    for cell in 0..model.cells {
        if grid[cell].0 != u16::MAX {
            continue;
        }
        let (y, x) = (cell / n, cell % n);
        let mut best = (-1i64, 0u16, 0u8);
        for pid in 0..model.np as u16 {
            if used[pid as usize] {
                continue;
            }
            for rot in 0..4u8 {
                let e = model.rot_edges[pid as usize][rot as usize];
                let mut sc = 0i64;
                let mut nb = |ok: bool, nc: usize, my: usize, their: usize| {
                    if ok && grid[nc].0 != u16::MAX
                        && model.rot_edges[grid[nc].0 as usize][grid[nc].1 as usize][their]
                            == e[my]
                    {
                        sc += 1;
                    }
                };
                nb(x > 0, cell.wrapping_sub(1), 3, 1);
                nb(x + 1 < n, cell + 1, 1, 3);
                nb(y > 0, cell.wrapping_sub(n), 0, 2);
                nb(y + 1 < n, cell + n, 2, 0);
                if let Some(tg) = targets {
                    for s in 0..4 {
                        if tg[cell][s] == Some(e[s]) {
                            sc += 1;
                        }
                    }
                }
                if sc > best.0 {
                    best = (sc, pid, rot);
                }
            }
        }
        grid[cell] = (best.1, best.2);
        used[best.1 as usize] = true;
    }
    grid
}

#[allow(clippy::too_many_lines)]
pub fn sa_run(
    model: &InteriorModel,
    targets: Option<&RimTargets>,
    init: Option<&[(u16, u8)]>,
    p: &SaParams,
) -> SaResult {
    let cells = model.cells;
    let n = model.n;
    let mut rng = Rng::new(p.seed.wrapping_mul(0x9E37_79B9).wrapping_add(p.seed));
    let mut st = St {
        m: model,
        targets,
        cell_piece: (0..cells as u16).collect(),
        cell_rot: vec![0u8; cells],
        piece_cell: (0..cells as u16).collect(),
    };
    if let Some(init) = init {
        assert_eq!(init.len(), cells, "init must cover all cells");
        for (cell, &(pid, rot)) in init.iter().enumerate() {
            st.cell_piece[cell] = pid;
            st.cell_rot[cell] = rot;
            st.piece_cell[pid as usize] = cell as u16;
        }
    } else {
        let mut perm: Vec<u16> = (0..cells as u16).collect();
        rng.shuffle(&mut perm);
        for (cell, &pid) in perm.iter().enumerate() {
            st.cell_piece[cell] = pid;
            st.piece_cell[pid as usize] = cell as u16;
            st.cell_rot[cell] = (rng.next_u64() & 3) as u8;
        }
    }
    let hint_cell: Vec<bool> = {
        let mut v = vec![false; cells];
        if p.hinted {
            for &(cell, pid, rot) in &model.hints {
                let cur_cell = st.piece_cell[pid] as usize;
                let occupant = st.cell_piece[cell];
                st.cell_piece.swap(cell, cur_cell);
                st.piece_cell[pid] = cell as u16;
                st.piece_cell[occupant as usize] = cur_cell as u16;
                st.cell_rot[cell] = rot;
                v[cell] = true;
            }
        }
        v
    };

    let mut score = st.full();
    let mut best_score = score;
    let mut best_state: Vec<(u16, u8)> = (0..cells)
        .map(|c| (st.cell_piece[c], st.cell_rot[c]))
        .collect();

    let t_start = Instant::now();
    let mut temp = p.t0;
    let mut moves: u64 = 0;
    let mut last_improve: u64 = 0;
    let mut member = vec![false; cells];

    loop {
        moves += 1;
        if moves & 0x3FF == 0 {
            let el = t_start.elapsed().as_millis() as u64;
            if el >= p.budget_ms {
                break;
            }
            let frac = el as f64 / p.budget_ms as f64;
            temp = p.t0 * (0.005f64 / p.t0).powf(frac);
            if moves - last_improve > 2_000_000 {
                for (c, &(pid, rot)) in best_state.iter().enumerate() {
                    st.cell_piece[c] = pid;
                    st.cell_rot[c] = rot;
                    st.piece_cell[pid as usize] = c as u16;
                }
                score = best_score;
                temp = p.t0 * 0.5;
                last_improve = moves;
            }
        }
        let kind = rng.next_u64() % 100;
        let accept = |delta: i64, temp: f64, rng: &mut Rng| -> bool {
            delta >= 0 || rng.f64() < (delta as f64 / temp).exp()
        };
        if kind < 15 {
            let cell = rng.below(cells);
            if hint_cell[cell] {
                continue;
            }
            let old_rot = st.cell_rot[cell];
            let new_rot = ((old_rot as u64 + 1 + rng.next_u64() % 3) & 3) as u8;
            let before = st.local(cell);
            st.cell_rot[cell] = new_rot;
            let after = st.local(cell);
            let delta = after as i64 - before as i64;
            if accept(delta, temp, &mut rng) {
                score = (score as i64 + delta) as u32;
            } else {
                st.cell_rot[cell] = old_rot;
                continue;
            }
        } else if kind < 50 {
            // conflict-biased best-rot swap
            let mut a = rng.below(cells);
            for _ in 0..8 {
                let s = rng.below(cells);
                let (y, x) = (s / n, s % n);
                let deg = u32::from(x > 0)
                    + u32::from(x + 1 < n)
                    + u32::from(y > 0)
                    + u32::from(y + 1 < n)
                    + if st.targets.is_some() {
                        let (_, rk) = model.rim_sides(s);
                        rk as u32
                    } else {
                        0
                    };
                if st.local(s) < deg {
                    a = s;
                    break;
                }
            }
            let b = rng.below(cells);
            if a == b || hint_cell[a] || hint_cell[b] {
                continue;
            }
            let adjacent = a.abs_diff(b) == 1 || a.abs_diff(b) == n;
            let joint = |st: &St, member: &mut [bool]| -> u32 {
                if adjacent {
                    let cs = [a, b];
                    member[a] = true;
                    member[b] = true;
                    let v = st.region(&cs, member);
                    member[a] = false;
                    member[b] = false;
                    v
                } else {
                    st.local(a) + st.local(b)
                }
            };
            let (pa, ra) = (st.cell_piece[a], st.cell_rot[a]);
            let (pb, rb) = (st.cell_piece[b], st.cell_rot[b]);
            let before = joint(&st, &mut member);
            st.cell_piece[a] = pb;
            st.cell_piece[b] = pa;
            let mut best = (0u32, 0u8, 0u8);
            for ra2 in 0..4u8 {
                st.cell_rot[a] = ra2;
                for rb2 in 0..4u8 {
                    st.cell_rot[b] = rb2;
                    let v = joint(&st, &mut member);
                    if v >= best.0 {
                        best = (v, ra2, rb2);
                    }
                }
            }
            st.cell_rot[a] = best.1;
            st.cell_rot[b] = best.2;
            let delta = best.0 as i64 - before as i64;
            if accept(delta, temp, &mut rng) {
                st.piece_cell[pb as usize] = a as u16;
                st.piece_cell[pa as usize] = b as u16;
                score = (score as i64 + delta) as u32;
            } else {
                st.cell_piece[a] = pa;
                st.cell_rot[a] = ra;
                st.cell_piece[b] = pb;
                st.cell_rot[b] = rb;
                continue;
            }
        } else if kind < 80 {
            // window / band LNS with greedy refill
            let mut cs: Vec<usize> = Vec::new();
            if kind < 72 {
                let k = 2 + (rng.next_u64() % 4) as usize;
                let pick_worst = rng.next_u64() & 1 == 0;
                let mut wy = rng.below(n - k + 1);
                let mut wx = rng.below(n - k + 1);
                if pick_worst {
                    let mut worst = u32::MAX;
                    for _ in 0..8 {
                        let ty = rng.below(n - k + 1);
                        let tx = rng.below(n - k + 1);
                        let mut v = 0;
                        for dy in 0..k {
                            for dx in 0..k {
                                v += st.local((ty + dy) * n + tx + dx);
                            }
                        }
                        if v < worst {
                            worst = v;
                            wy = ty;
                            wx = tx;
                        }
                    }
                }
                for dy in 0..k {
                    for dx in 0..k {
                        let c = (wy + dy) * n + wx + dx;
                        if !hint_cell[c] {
                            cs.push(c);
                        }
                    }
                }
            } else {
                let len = (5 + (rng.next_u64() % 6) as usize).min(n);
                let horiz = rng.next_u64() & 1 == 0;
                let lane = rng.below(n);
                let off = rng.below(n - len + 1);
                for j in 0..len {
                    let c = if horiz { lane * n + off + j } else { (off + j) * n + lane };
                    if !hint_cell[c] {
                        cs.push(c);
                    }
                }
            }
            if cs.is_empty() {
                continue;
            }
            for &c in &cs {
                member[c] = true;
            }
            let before = st.region(&cs, &member);
            let saved: Vec<(u16, u8)> =
                cs.iter().map(|&c| (st.cell_piece[c], st.cell_rot[c])).collect();
            let mut pool: Vec<u16> = saved.iter().map(|&(p, _)| p).collect();
            rng.shuffle(&mut pool);
            let mut decided: Vec<bool> = (0..cells).map(|c| !member[c]).collect();
            for &c in &cs {
                let (y, x) = (c / n, c % n);
                let mut bestv = -1i64;
                let mut bestpick = (0usize, 0u8);
                for (pi, &pid) in pool.iter().enumerate() {
                    if pid == u16::MAX {
                        continue;
                    }
                    for rot in 0..4u8 {
                        let e = model.rot_edges[pid as usize][rot as usize];
                        let mut v = 0i64;
                        let mut nb = |ok: bool, nc: usize, my: usize, their: usize| {
                            if ok && decided[nc] && st.edges_at(nc)[their] == e[my] {
                                v += 1;
                            }
                        };
                        nb(x > 0, c.wrapping_sub(1), 3, 1);
                        nb(x + 1 < n, c + 1, 1, 3);
                        nb(y > 0, c.wrapping_sub(n), 0, 2);
                        nb(y + 1 < n, c + n, 2, 0);
                        if let Some(tg) = st.targets {
                            for s in 0..4 {
                                if tg[c][s] == Some(e[s]) {
                                    v += 1;
                                }
                            }
                        }
                        if v > bestv {
                            bestv = v;
                            bestpick = (pi, rot);
                        }
                    }
                }
                let (pi, rot) = bestpick;
                let pid = pool[pi];
                pool[pi] = u16::MAX;
                st.cell_piece[c] = pid;
                st.cell_rot[c] = rot;
                st.piece_cell[pid as usize] = c as u16;
                decided[c] = true;
            }
            let after = st.region(&cs, &member);
            let delta = after as i64 - before as i64;
            if accept(delta, temp, &mut rng) {
                score = (score as i64 + delta) as u32;
            } else {
                for (idx, &c) in cs.iter().enumerate() {
                    let (pid, rot) = saved[idx];
                    st.cell_piece[c] = pid;
                    st.cell_rot[c] = rot;
                    st.piece_cell[pid as usize] = c as u16;
                }
            }
            for &c in &cs {
                member[c] = false;
            }
        } else {
            // exact-region B&B on the worst sampled window
            let (kw, kh, cap, tries) = if kind < 97 {
                (3usize, 3usize, 3_000u64, 4usize)
            } else if rng.next_u64() & 1 == 0 {
                (5, 2, 200_000, 8)
            } else {
                (2, 5, 200_000, 8)
            };
            let mut wy = 0;
            let mut wx = 0;
            let mut worst = u32::MAX;
            for _ in 0..tries {
                let ty = rng.below(n - kh + 1);
                let tx = rng.below(n - kw + 1);
                let mut v = 0;
                for dy in 0..kh {
                    for dx in 0..kw {
                        v += st.local((ty + dy) * n + tx + dx);
                    }
                }
                if v < worst {
                    worst = v;
                    wy = ty;
                    wx = tx;
                }
            }
            let mut cs = Vec::with_capacity(kw * kh);
            for dy in 0..kh {
                for dx in 0..kw {
                    let c = (wy + dy) * n + wx + dx;
                    if !hint_cell[c] {
                        cs.push(c);
                    }
                }
            }
            if cs.len() < 2 {
                continue;
            }
            for &c in &cs {
                member[c] = true;
            }
            let before = st.region(&cs, &member);
            let (asn, after) = exact_region(&st, &cs, &member, cap);
            if after > before {
                for (j, &c) in cs.iter().enumerate() {
                    let (pid, rot) = asn[j];
                    st.cell_piece[c] = pid;
                    st.cell_rot[c] = rot;
                    st.piece_cell[pid as usize] = c as u16;
                }
                score += after - before;
            }
            for &c in &cs {
                member[c] = false;
            }
        }

        if score > best_score {
            best_score = score;
            for (c, slot) in best_state.iter_mut().enumerate() {
                *slot = (st.cell_piece[c], st.cell_rot[c]);
            }
            last_improve = moves;
        }
    }

    let best_ii = model.ii_matches(&best_state);
    let best_ib = targets.map_or(0, |tg| model.ib_matches(&best_state, tg));
    SaResult { seed: p.seed, best_ii, best_ib, best_state, moves }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sa_improves_and_accounts() {
        let (m, _, targets) = InteriorModel::synthetic(5, 5, 21);
        let p = SaParams { seed: 3, budget_ms: 1_500, ..SaParams::default() };
        let r = sa_run(&m, Some(&targets), None, &p);
        // recount must match the tracked best
        assert_eq!(m.ii_matches(&r.best_state), r.best_ii);
        assert_eq!(m.ib_matches(&r.best_state, &targets), r.best_ib);
        // permutation sanity
        let mut seen = vec![false; m.np];
        for &(pid, _) in &r.best_state {
            assert!(!seen[pid as usize]);
            seen[pid as usize] = true;
        }
        // a 1.5 s run on a 5x5 should comfortably beat a random start
        assert!(r.best_ii + r.best_ib > 30, "ii {} ib {}", r.best_ii, r.best_ib);
    }

    #[test]
    fn exact_region_never_worsens_and_respects_rim() {
        let (m, sol, targets) = InteriorModel::synthetic(4, 5, 33);
        let mut st = St {
            m: &m,
            targets: Some(&targets),
            cell_piece: sol.iter().map(|&(p, _)| p).collect(),
            cell_rot: sol.iter().map(|&(_, r)| r).collect(),
            piece_cell: vec![0; m.np],
        };
        for (c, &(p, _)) in sol.iter().enumerate() {
            st.piece_cell[p as usize] = c as u16;
        }
        // scramble a 2x2 window
        let cs = vec![5usize, 6, 9, 10];
        let mut member = vec![false; m.cells];
        for &c in &cs {
            member[c] = true;
        }
        st.cell_piece.swap(5, 10);
        st.cell_rot[5] = (st.cell_rot[5] + 1) & 3;
        let before = st.region(&cs, &member);
        let (asn, after) = exact_region(&st, &cs, &member, 1_000_000);
        assert!(after >= before);
        // optimal region on a scrambled perfect board must restore perfection
        for (j, &c) in cs.iter().enumerate() {
            st.cell_piece[c] = asn[j].0;
            st.cell_rot[c] = asn[j].1;
        }
        let full: Vec<(u16, u8)> = (0..m.cells)
            .map(|c| (st.cell_piece[c], st.cell_rot[c]))
            .collect();
        assert_eq!(m.count_breaks(&full, Some(&targets)), 0, "exact region restores perfect");
    }
}
