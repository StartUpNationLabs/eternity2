// Exact endgames. At a deep DFS prefix, the leftover pieces are assigned
// OPTIMALLY (min mismatches, counting fixed rim targets) so every deep
// prefix yields a complete, scored board (anytime break minimization).
//
//   exact_tail  — last ≤ n cells (one row), B&B with an admissible
//                 satisfiability lower bound; handles forced (hint) cells.
//   exact_tail2 — last 2n cells (two rows) as a column-pair B&B; used as
//                 post-hoc polish (in-DFS it loses to exact_tail under time
//                 pressure — vol-211 measurement).

use crate::dfs::{CellPlan, Src};
use crate::model::{InteriorModel, RimTargets, Tables};

pub const TAIL_CAP: u64 = 2_000_000;

/// MIDDEN: returned when no mask-respecting completion was found —
/// callers must NOT record completions at or above this value
pub const TAIL_INFEASIBLE: u32 = 1_000_000;

/// once-per-process cap-hit warning (vol-213 TAIL_CAP lesson)
static CAP_HIT_WARNED: std::sync::atomic::AtomicBool =
    std::sync::atomic::AtomicBool::new(false);

struct TailCtx<'a> {
    tables: &'a Tables,
    plans: &'a [CellPlan],
    start_d: usize,
    pieces: &'a [u16],
    /// per tail offset: forced (pid, rot) in search space
    forced: Vec<Option<(u16, u8)>>,
    /// pool index of the forced piece per tail offset
    forced_pi: Vec<Option<usize>>,
    /// pool indices reserved for forced cells (unusable elsewhere)
    reserved: u64,
    /// static_cands[j]: (cost vs prefix-known constraints, pool idx),
    /// cost-sorted. Admissible per-cell LB = first available entry's
    /// cost (vol-216: value-based, strictly ≥ the old 0/1 sat bound).
    static_cands: Vec<Vec<(u32, u8)>>,
    /// forced cells' static cost (their LB contribution)
    static_forced: Vec<u32>,
    nodes: u64,
    cap: u64,
    abort_at: u32,
    best_mis: u32,
    best_asn: Vec<(u16, u8)>,
    asn: Vec<(u16, u8)>,
    /// per-level candidate scratch (k>14 safe; was a [_; 56] array)
    scratch: Vec<Vec<(u32, u8, u8)>>,
    /// MIDDEN: cells allowed to pay mismatches (None = all)
    break_cells: Option<&'a [bool]>,
}

fn mismatches_at(
    tables: &Tables,
    plan: &CellPlan,
    grid: &[(u16, u8)],
    e: &[u8; 4],
) -> u32 {
    let mut m = 0;
    for i in 0..plan.k as usize {
        let want = match plan.src[i] {
            Src::Fixed(c) => c,
            Src::Placed { cell, their_side } => {
                let (p, r) = grid[cell as usize];
                tables.rot_edges[p as usize][r as usize][their_side as usize]
            }
        };
        if e[plan.sides[i] as usize] != want {
            m += 1;
        }
    }
    m
}

impl TailCtx<'_> {
    fn lb_rest(&self, j: usize, used: u64) -> u32 {
        let k = self.pieces.len();
        let mut lb = 0;
        for jj in j..k {
            if self.forced_pi[jj].is_some() {
                lb += self.static_forced[jj];
                continue;
            }
            let blocked = used | self.reserved;
            lb += self.static_cands[jj]
                .iter()
                .find(|&&(_, pi)| blocked >> pi & 1 == 0)
                .map_or(TAIL_INFEASIBLE, |&(c, _)| c);
        }
        lb
    }

    fn go(&mut self, grid: &mut Vec<(u16, u8)>, j: usize, mis: u32, used: u64) {
        let k = self.pieces.len();
        let cut = self.best_mis.min(self.abort_at);
        if mis >= cut || self.nodes > self.cap {
            return;
        }
        if j == k {
            self.best_mis = mis;
            self.best_asn.clone_from(&self.asn);
            return;
        }
        if mis + self.lb_rest(j, used) >= cut {
            return;
        }
        let d = self.start_d + j;
        let plan = &self.plans[d];
        let cell = plan.cell as usize;
        if let Some((fp, fr)) = self.forced[j] {
            let e = self.tables.rot_edges[fp as usize][fr as usize];
            let m = mismatches_at(self.tables, plan, grid, &e);
            self.nodes += 1;
            if mis + m >= self.best_mis.min(self.abort_at) || self.nodes > self.cap {
                return;
            }
            let pi = self.forced_pi[j].expect("forced idx");
            grid[cell] = (fp, fr);
            self.asn[j] = (fp, fr);
            self.go(grid, j + 1, mis + m, used | 1 << pi);
            grid[cell] = (u16::MAX, 0);
            return;
        }
        // candidates ordered by local mismatch
        // MIDDEN: non-mask cells admit only 0-mismatch candidates
        let must_be_perfect = self.break_cells.is_some_and(|m| !m[cell]);
        let mut order = std::mem::take(&mut self.scratch[j]);
        order.clear();
        for (pi, &pid) in self.pieces.iter().enumerate() {
            if used >> pi & 1 == 1 || self.reserved >> pi & 1 == 1 {
                continue;
            }
            for rot in 0..4u8 {
                let e = self.tables.rot_edges[pid as usize][rot as usize];
                let m = mismatches_at(self.tables, plan, grid, &e);
                if must_be_perfect && m > 0 {
                    continue;
                }
                order.push((m, pi as u8, rot));
            }
        }
        order.sort_unstable_by_key(|&(m, ..)| m);
        for &(m, pi, rot) in &order {
            self.nodes += 1;
            if mis + m >= self.best_mis.min(self.abort_at) || self.nodes > self.cap {
                break;
            }
            let pid = self.pieces[pi as usize];
            grid[cell] = (pid, rot);
            self.asn[j] = (pid, rot);
            self.go(grid, j + 1, mis + m, used | 1 << pi);
            grid[cell] = (u16::MAX, 0);
        }
        self.scratch[j] = order;
    }
}

/// Exact min-cost bipartite assignment (Hungarian, O(k³)) on a square
/// cost matrix with `INF_COST` for forbidden entries. Used as the root
/// lower bound of `exact_tail` (vol-216): assignment-aware, strictly ≥
/// the per-cell Σ-min bound.
const INF_COST: i64 = 1 << 40;

fn hungarian_lb(cost: &[Vec<i64>]) -> i64 {
    let k = cost.len();
    let mut u = vec![0i64; k + 1];
    let mut v = vec![0i64; k + 1];
    let mut p = vec![0usize; k + 1];
    let mut way = vec![0usize; k + 1];
    for i in 1..=k {
        p[0] = i;
        let mut j0 = 0usize;
        let mut minv = vec![i64::MAX; k + 1];
        let mut used = vec![false; k + 1];
        loop {
            used[j0] = true;
            let i0 = p[j0];
            let mut delta = i64::MAX;
            let mut j1 = 0usize;
            for j in 1..=k {
                if used[j] {
                    continue;
                }
                let cur = cost[i0 - 1][j - 1] - u[i0] - v[j];
                if cur < minv[j] {
                    minv[j] = cur;
                    way[j] = j0;
                }
                if minv[j] < delta {
                    delta = minv[j];
                    j1 = j;
                }
            }
            for j in 0..=k {
                if used[j] {
                    u[p[j]] += delta;
                    v[j] -= delta;
                } else {
                    minv[j] -= delta;
                }
            }
            j0 = j1;
            if p[j0] == 0 {
                break;
            }
        }
        loop {
            let j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
            if j0 == 0 {
                break;
            }
        }
    }
    (1..=k).map(|j| cost[p[j] - 1][j - 1]).sum()
}

/// Optimal assignment of the k = pieces.len() leftover pieces to the last k
/// scan positions. `grid` is scratch: tail cells must be empty on entry and
/// are restored to empty on exit. `forced_by_cell` is indexed by CELL id.
/// Returns (min mismatches incl. fixed rim sides, assignment by tail offset)
/// — always returns an assignment (greedy incumbent).
pub fn exact_tail(
    tables: &Tables,
    plans: &[CellPlan],
    scan: &[usize],
    grid: &mut Vec<(u16, u8)>,
    start_d: usize,
    pieces: &[u16],
    forced_by_cell: &[Option<(u16, u8)>],
    abort_at: u32,
    cap: u64,
    break_cells: Option<&[bool]>,
) -> (u32, Vec<(u16, u8)>) {
    let k = pieces.len();
    debug_assert_eq!(start_d + k, scan.len());
    let forced: Vec<Option<(u16, u8)>> = (0..k)
        .map(|j| forced_by_cell[plans[start_d + j].cell as usize])
        .collect();
    let forced_pi: Vec<Option<usize>> = forced
        .iter()
        .map(|f| {
            f.map(|(fp, _)| pieces.iter().position(|&p| p == fp).expect("forced in pool"))
        })
        .collect();
    let reserved = forced_pi
        .iter()
        .flatten()
        .fold(0u64, |m, &pi| m | 1 << pi);
    // static per-(cell, piece) min-rot cost vs PREFIX-KNOWN constraints
    // (vol-216): value-based admissible LB inputs + Hungarian root bound
    let mut static_cands: Vec<Vec<(u32, u8)>> = Vec::with_capacity(k);
    let mut static_forced: Vec<u32> = vec![0; k];
    let mut static_cost: Vec<Vec<u32>> = vec![vec![0; k]; k];
    for j in 0..k {
        let plan = &plans[start_d + j];
        // (side, color) pairs decided by the prefix (not by tail cells)
        let mut known: Vec<(u8, u8)> = Vec::with_capacity(4);
        for i in 0..plan.k as usize {
            match plan.src[i] {
                Src::Fixed(c) => known.push((plan.sides[i], c)),
                Src::Placed { cell, their_side } => {
                    let (p, r) = grid[cell as usize];
                    if p != u16::MAX {
                        known.push((
                            plan.sides[i],
                            tables.rot_edges[p as usize][r as usize][their_side as usize],
                        ));
                    }
                }
            }
        }
        let cost_of = |pid: u16, rot: u8| -> u32 {
            let e = tables.rot_edges[pid as usize][rot as usize];
            known
                .iter()
                .filter(|&&(s, c)| e[s as usize] != c)
                .count() as u32
        };
        let must_be_perfect =
            break_cells.is_some_and(|m| !m[plan.cell as usize]);
        let mut cands: Vec<(u32, u8)> = Vec::with_capacity(k);
        for (pi, &pid) in pieces.iter().enumerate() {
            let c = (0..4u8).map(|r| cost_of(pid, r)).min().expect("rot");
            static_cost[j][pi] = if must_be_perfect && c > 0 {
                TAIL_INFEASIBLE
            } else {
                c
            };
            if !(must_be_perfect && c > 0) {
                cands.push((c, pi as u8));
            }
        }
        cands.sort_unstable();
        static_cands.push(cands);
        if let Some((fp, fr)) = forced[j] {
            static_forced[j] = cost_of(fp, fr);
        }
    }

    // greedy incumbent
    let mut ctx = TailCtx {
        tables,
        plans,
        start_d,
        pieces,
        forced,
        forced_pi,
        reserved,
        static_cands,
        static_forced,
        nodes: 0,
        cap,
        abort_at,
        best_mis: 0,
        best_asn: vec![(0, 0); k],
        asn: vec![(0, 0); k],
        scratch: vec![Vec::with_capacity(4 * k); k],
        break_cells,
    };
    {
        let mut used = 0u64;
        let mut mis = 0u32;
        let mut greedy_ok = true;
        for j in 0..k {
            let plan = &ctx.plans[start_d + j];
            let cell = plan.cell as usize;
            let must_be_perfect = break_cells.is_some_and(|m| !m[cell]);
            let mut bm = u32::MAX;
            let mut bpick = (0usize, 0u8);
            if let Some((fp, fr)) = ctx.forced[j] {
                let e = tables.rot_edges[fp as usize][fr as usize];
                bm = mismatches_at(tables, plan, grid, &e);
                bpick = (ctx.forced_pi[j].expect("idx"), fr);
                let _ = fp;
            } else {
                for (pi, &pid) in pieces.iter().enumerate() {
                    if used >> pi & 1 == 1 || ctx.reserved >> pi & 1 == 1 {
                        continue;
                    }
                    for rot in 0..4u8 {
                        let e = tables.rot_edges[pid as usize][rot as usize];
                        let m = mismatches_at(tables, plan, grid, &e);
                        if must_be_perfect && m > 0 {
                            continue;
                        }
                        if m < bm {
                            bm = m;
                            bpick = (pi, rot);
                        }
                    }
                }
            }
            if bm == u32::MAX {
                greedy_ok = false;
                break;
            }
            let (pi, rot) = bpick;
            used |= 1 << pi;
            grid[cell] = (pieces[pi], rot);
            ctx.best_asn[j] = (pieces[pi], rot);
            mis += bm;
        }
        ctx.best_mis = if greedy_ok {
            mis
        } else {
            ctx.abort_at.min(TAIL_INFEASIBLE)
        };
        // clear tail for the B&B
        for j in 0..k {
            grid[ctx.plans[start_d + j].cell as usize] = (u16::MAX, 0);
        }
    }
    if ctx.best_mis > 0 && ctx.abort_at > 0 {
        // vol-216 root cut: exact assignment relaxation (Hungarian) over
        // static costs. If even the relaxation can't beat the cut, the
        // whole B&B is skippable. Forced cells admit only their piece.
        let cut = i64::from(ctx.best_mis.min(ctx.abort_at));
        let cost_mat: Vec<Vec<i64>> = (0..k)
            .map(|j| {
                (0..k)
                    .map(|pi| match ctx.forced_pi[j] {
                        Some(fpi) if pi == fpi => i64::from(ctx.static_forced[j]),
                        Some(_) => INF_COST,
                        None if ctx.reserved >> pi & 1 == 1 => INF_COST,
                        None => i64::from(static_cost[j][pi]).min(INF_COST),
                    })
                    .collect()
            })
            .collect();
        let root_lb = hungarian_lb(&cost_mat);
        if root_lb < cut {
            ctx.go(grid, 0, 0, 0);
        }
    }
    // vol-213 lesson: a silently-capped "exact" method is greedy in
    // disguise (cost 2 invisible breaks on witness A). Surface it once.
    if ctx.nodes > ctx.cap
        && !CAP_HIT_WARNED.swap(true, std::sync::atomic::Ordering::Relaxed)
    {
        eprintln!(
            "WARN exact_tail: node cap {} hit — incumbent may be non-optimal (raise --et-cap)",
            ctx.cap
        );
    }
    // ensure tail empty on exit
    for j in 0..k {
        grid[plans[start_d + j].cell as usize] = (u16::MAX, 0);
    }
    (ctx.best_mis, ctx.best_asn)
}

// ----------------------------------------------------------------- tail2

/// Exact two-row endgame: the last 2n cells solved as a column-pair B&B
/// (top = row n-2, bottom = row n-1, columns left to right; bottom's up
/// edge is the just-placed top). Cell order of the returned assignment is
/// ROW-MAJOR offsets within the 2-row block (not scan order). Forced cells
/// supported; fixed rim targets scored. Node-capped, abort-bounded,
/// greedy-seeded.
#[allow(clippy::too_many_lines)]
pub fn exact_tail2(
    model: &InteriorModel,
    tables: &Tables,
    grid: &[(u16, u8)],
    pieces: &[u16],
    forced_by_cell: &[Option<(u16, u8)>],
    targets: Option<&RimTargets>,
    abort_at: u32,
    node_cap: u64,
) -> (u32, Vec<(u16, u8)>) {
    let n = model.n;
    let k = 2 * n;
    debug_assert_eq!(pieces.len(), k);
    let start = (n - 2) * n;
    let up11: Vec<u8> = (0..n)
        .map(|c| {
            let (p, r) = grid[start + c - n];
            tables.rot_edges[p as usize][r as usize][2]
        })
        .collect();
    let fixed_cost = |cell: usize, e: &[u8; 4]| -> u32 {
        let Some(tg) = targets else { return 0 };
        let mut m = 0;
        for s in 0..4 {
            if tg[cell][s].is_some_and(|c| c != e[s]) {
                m += 1;
            }
        }
        m
    };
    let pool_pi = |fp: u16| pieces.iter().position(|&p| p == fp).expect("forced in pool");
    let f_top: Vec<Option<(usize, u8)>> = (0..n)
        .map(|c| forced_by_cell[start + c].map(|(fp, fr)| (pool_pi(fp), fr)))
        .collect();
    let f_bot: Vec<Option<(usize, u8)>> = (0..n)
        .map(|c| forced_by_cell[start + n + c].map(|(fp, fr)| (pool_pi(fp), fr)))
        .collect();
    let reserved: u64 = f_top
        .iter()
        .chain(f_bot.iter())
        .flatten()
        .fold(0u64, |m, &(pi, _)| m | 1 << pi);
    // per-color index over the pool: (pi, rot) whose N edge == color
    let mut by_n: Vec<Vec<(u8, u8)>> = vec![Vec::new(); model.ncolors];
    for (pi, &pid) in pieces.iter().enumerate() {
        for rot in 0..4u8 {
            let e = tables.rot_edges[pid as usize][rot as usize];
            by_n[e[0] as usize].push((pi as u8, rot));
        }
    }

    // candidate pairs for one column, cost-sorted
    #[allow(clippy::too_many_arguments)]
    let column_pairs = |used: u64,
                        c: usize,
                        lt: Option<u8>,
                        lb_: Option<u8>,
                        max_cost: u32,
                        out: &mut Vec<(u32, u8, u8, u8, u8)>| {
        out.clear();
        let top_cell = start + c;
        let bot_cell = start + n + c;
        let up = up11[c];
        // enumerate tops: tier 0 = N matches up; tier 1 = N mismatches (+1)
        let try_top = |pi: usize, rt: u8, up_cost: u32, out: &mut Vec<(u32, u8, u8, u8, u8)>| {
            if used >> pi & 1 == 1 {
                return;
            }
            match f_top[c] {
                Some((fpi, fr)) if pi != fpi || rt != fr => return,
                None if reserved >> pi & 1 == 1 => return,
                _ => {}
            }
            let et = tables.rot_edges[pieces[pi] as usize][rt as usize];
            let cost_t = up_cost
                + u32::from(lt.is_some_and(|l| et[3] != l))
                + fixed_cost(top_cell, &et);
            if cost_t > max_cost {
                return;
            }
            // bottoms: tier 0 = N matches top's S; tier 1 = mismatch (+1)
            let try_bot =
                |pb: usize, rb: u8, up_cost_b: u32, out: &mut Vec<(u32, u8, u8, u8, u8)>| {
                    if pb == pi || used >> pb & 1 == 1 {
                        return;
                    }
                    match f_bot[c] {
                        Some((fpi, fr)) if pb != fpi || rb != fr => return,
                        None if reserved >> pb & 1 == 1 => return,
                        _ => {}
                    }
                    let eb = tables.rot_edges[pieces[pb] as usize][rb as usize];
                    let cost = cost_t
                        + up_cost_b
                        + u32::from(lb_.is_some_and(|l| eb[3] != l))
                        + fixed_cost(bot_cell, &eb);
                    if cost <= max_cost {
                        out.push((cost, pi as u8, rt, pb as u8, rb));
                    }
                };
            for &(pb, rb) in &by_n[et[2] as usize] {
                try_bot(pb as usize, rb, 0, out);
            }
            if cost_t + 1 <= max_cost {
                for pb in 0..pieces.len() {
                    for rb in 0..4u8 {
                        let eb = tables.rot_edges[pieces[pb] as usize][rb as usize];
                        if eb[0] != et[2] {
                            try_bot(pb, rb, 1, out);
                        }
                    }
                }
            }
        };
        for &(pi, rt) in &by_n[up as usize] {
            try_top(pi as usize, rt, 0, out);
        }
        if max_cost >= 1 {
            for pi in 0..pieces.len() {
                for rt in 0..4u8 {
                    let et = tables.rot_edges[pieces[pi] as usize][rt as usize];
                    if et[0] != up {
                        try_top(pi, rt, 1, out);
                    }
                }
            }
        }
        out.sort_unstable_by_key(|&(m, ..)| m);
    };

    // greedy incumbent
    let mut best_asn: Vec<(u16, u8)> = vec![(0, 0); k];
    let best_mis: u32;
    {
        let mut used = 0u64;
        let mut mis = 0u32;
        let mut lt = None;
        let mut lb_ = None;
        let mut scratch = Vec::new();
        for c in 0..n {
            column_pairs(used, c, lt, lb_, 999, &mut scratch);
            let &(m, pt, rt, pb, rb) = scratch.first().expect("greedy pair");
            mis += m;
            used |= 1 << pt | 1 << pb;
            let et = tables.rot_edges[pieces[pt as usize] as usize][rt as usize];
            let eb = tables.rot_edges[pieces[pb as usize] as usize][rb as usize];
            lt = Some(et[1]);
            lb_ = Some(eb[1]);
            best_asn[c] = (pieces[pt as usize], rt);
            best_asn[n + c] = (pieces[pb as usize], rb);
        }
        best_mis = mis;
    }
    if best_mis == 0 || abort_at == 0 {
        return (best_mis, best_asn);
    }

    // column B&B
    struct S2 {
        nodes: u64,
        cap: u64,
        abort_at: u32,
        best_mis: u32,
        best_asn: Vec<(u16, u8)>,
        asn: Vec<(u16, u8)>,
    }
    let mut s = S2 {
        nodes: 0,
        cap: node_cap,
        abort_at,
        best_mis,
        best_asn,
        asn: vec![(0, 0); k],
    };
    // recursion via explicit closure-free helper
    fn go2(
        s: &mut S2,
        n: usize,
        pieces: &[u16],
        tables: &Tables,
        column_pairs: &dyn Fn(u64, usize, Option<u8>, Option<u8>, u32, &mut Vec<(u32, u8, u8, u8, u8)>),
        c: usize,
        mis: u32,
        used: u64,
        lt: Option<u8>,
        lb_: Option<u8>,
    ) {
        let cut = s.best_mis.min(s.abort_at);
        if mis >= cut || s.nodes > s.cap {
            return;
        }
        if c == n {
            s.best_mis = mis;
            s.best_asn.clone_from(&s.asn);
            return;
        }
        let mut pairs = Vec::new();
        column_pairs(used, c, lt, lb_, cut - mis - 1, &mut pairs);
        for &(m, pt, rt, pb, rb) in &pairs {
            s.nodes += 1;
            if mis + m >= s.best_mis.min(s.abort_at) || s.nodes > s.cap {
                return;
            }
            let et = tables.rot_edges[pieces[pt as usize] as usize][rt as usize];
            let eb = tables.rot_edges[pieces[pb as usize] as usize][rb as usize];
            s.asn[c] = (pieces[pt as usize], rt);
            s.asn[n + c] = (pieces[pb as usize], rb);
            go2(
                s,
                n,
                pieces,
                tables,
                column_pairs,
                c + 1,
                mis + m,
                used | 1 << pt | 1 << pb,
                Some(et[1]),
                Some(eb[1]),
            );
        }
    }
    go2(&mut s, n, pieces, tables, &column_pairs, 0, 0, 0, None, None);
    (s.best_mis, s.best_asn)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dfs::{build_plans, Scan};
    use crate::rng::Rng;

    /// brute force over all assignments of `pieces` to the tail (k small)
    fn brute_min(
        tables: &Tables,
        plans: &[CellPlan],
        grid: &mut Vec<(u16, u8)>,
        start_d: usize,
        pieces: &[u16],
    ) -> u32 {
        fn rec(
            tables: &Tables,
            plans: &[CellPlan],
            grid: &mut Vec<(u16, u8)>,
            start_d: usize,
            pieces: &[u16],
            j: usize,
            used: u64,
            mis: u32,
            best: &mut u32,
        ) {
            let k = pieces.len();
            if j == k {
                *best = (*best).min(mis);
                return;
            }
            let plan = &plans[start_d + j];
            for (pi, &pid) in pieces.iter().enumerate() {
                if used >> pi & 1 == 1 {
                    continue;
                }
                for rot in 0..4u8 {
                    let e = tables.rot_edges[pid as usize][rot as usize];
                    let m = mismatches_at(tables, plan, grid, &e);
                    grid[plan.cell as usize] = (pid, rot);
                    rec(tables, plans, grid, start_d, pieces, j + 1, used | 1 << pi, mis + m, best);
                    grid[plan.cell as usize] = (u16::MAX, 0);
                }
            }
        }
        let mut best = u32::MAX;
        rec(tables, plans, grid, start_d, pieces, 0, 0, 0, &mut best);
        best
    }

    #[test]
    fn exact_tail_k6_optimal_vs_brute_force() {
        // vol-216 bound upgrade must preserve exactness at k=6
        for seed in 0..4u64 {
            let (m, sol, targets) = InteriorModel::synthetic(4, 5, 300 + seed);
            let so = Scan::RowMajor.order(m.n);
            let plans = build_plans(&m, &so, Some(&targets));
            let tables = Tables::build(&m, false);
            let k = 6usize;
            let start_d = m.cells - k;
            let mut grid: Vec<(u16, u8)> = vec![(u16::MAX, 0); m.cells];
            let mut rng = Rng::new(seed);
            for d in 0..start_d {
                let cell = so[d];
                let (p, mut r) = sol[cell];
                if rng.below(3) == 0 {
                    r = (r + 1) & 3;
                }
                grid[cell] = (p, r);
            }
            let pieces: Vec<u16> = (start_d..m.cells).map(|d| sol[so[d]].0).collect();
            let forced: Vec<Option<(u16, u8)>> = vec![None; m.cells];
            let (mis, _) = exact_tail(
                &tables, &plans, &so, &mut grid, start_d, &pieces, &forced, u32::MAX,
                TAIL_CAP, None,
            );
            let want = brute_min(&tables, &plans, &mut grid, start_d, &pieces);
            assert_eq!(mis, want, "seed {seed}");
        }
    }

    #[test]
    fn exact_tail_k20_smoke() {
        // k > 14 support (the old fixed [_;56] candidate array would
        // overflow at k=20); perfect tail of a clean solution must be 0
        let (m, sol, targets) = InteriorModel::synthetic(5, 6, 42);
        let so = Scan::RowMajor.order(m.n);
        let plans = build_plans(&m, &so, Some(&targets));
        let tables = Tables::build(&m, false);
        let k = 20usize;
        let start_d = m.cells - k;
        let mut grid: Vec<(u16, u8)> = vec![(u16::MAX, 0); m.cells];
        for d in 0..start_d {
            grid[so[d]] = sol[so[d]];
        }
        let pieces: Vec<u16> = (start_d..m.cells).map(|d| sol[so[d]].0).collect();
        let forced: Vec<Option<(u16, u8)>> = vec![None; m.cells];
        let (mis, _) = exact_tail(
            &tables, &plans, &so, &mut grid, start_d, &pieces, &forced, u32::MAX,
            TAIL_CAP, None,
        );
        assert_eq!(mis, 0, "clean prefix must complete perfectly at k=20");
    }

    #[test]
    fn hungarian_lb_basic() {
        // 3x3 with known optimum 5 (1+3+1)
        let c = vec![
            vec![1, 2, 9],
            vec![4, 3, 7],
            vec![9, 8, 1],
        ];
        assert_eq!(hungarian_lb(&c), 1 + 3 + 1);
        // forbidden entries force the expensive diagonal
        let c2 = vec![
            vec![5, INF_COST],
            vec![INF_COST, 5],
        ];
        assert_eq!(hungarian_lb(&c2), 10);
    }

    #[test]
    fn exact_tail_is_optimal_vs_brute_force() {
        for seed in 0..6u64 {
            let (m, sol, targets) = InteriorModel::synthetic(4, 4, 100 + seed);
            let scan = if seed % 2 == 0 { Scan::RowMajor } else { Scan::Boustro };
            let so = scan.order(m.n);
            let plans = build_plans(&m, &so, Some(&targets));
            let tables = Tables::build(&m, false);
            let k = 4usize;
            let start_d = m.cells - k;
            // prefix from a SCRAMBLED solution (so the tail is non-trivial):
            // rotate some prefix rots to inject mismatches
            let mut grid: Vec<(u16, u8)> = vec![(u16::MAX, 0); m.cells];
            let mut rng = Rng::new(seed);
            for d in 0..start_d {
                let cell = so[d];
                let (p, mut r) = sol[cell];
                if rng.below(3) == 0 {
                    r = (r + 1) & 3;
                }
                grid[cell] = (p, r);
            }
            let pieces: Vec<u16> = (start_d..m.cells).map(|d| sol[so[d]].0).collect();
            let forced: Vec<Option<(u16, u8)>> = vec![None; m.cells];
            let (mis, asn) =
                exact_tail(
                    &tables, &plans, &so, &mut grid, start_d, &pieces, &forced, u32::MAX,
                    TAIL_CAP, None,
                );
            let want = brute_min(&tables, &plans, &mut grid, start_d, &pieces);
            assert_eq!(mis, want, "seed {seed} scan {}", scan.name());
            // assignment must reproduce the claimed mismatch count
            for (j, &pr) in asn.iter().enumerate() {
                grid[so[start_d + j]] = pr;
            }
            let total = m.count_breaks(&grid, Some(&targets));
            let prefix_mis = {
                for d in start_d..m.cells {
                    grid[so[d]] = (u16::MAX, 0);
                }
                // recount prefix-only breaks by zeroing tail contribution:
                // recompute via per-cell plan mismatches
                let mut s = 0;
                for d in 0..start_d {
                    let plan = &plans[d];
                    let (p, r) = grid[plan.cell as usize];
                    let e = tables.rot_edges[p as usize][r as usize];
                    s += mismatches_at(&tables, plan, &grid, &e);
                }
                s
            };
            assert_eq!(total, prefix_mis + mis, "seed {seed}");
        }
    }
}
