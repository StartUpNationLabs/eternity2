// Break-DFS over the interior, free-rim or border-anchored.
//
// Mechanics (ported from vol-211 cloister.rs, generalized):
//   - scan order is a permutation of cells (row-major / boustrophedon);
//     a cell's constraints at placement = already-placed neighbors + fixed
//     rim targets from the anchored frame (CLOISTER-II: IB edges are real
//     edges from cell 1, entering the same break budget as II edges);
//   - candidates come from precomputed per-(color,color) lists (pair NW /
//     pair NE / singles), shuffled per epoch — vol-212 measured this 1.56×
//     faster than bitset-intersection candidates (lists ARE the
//     intersection, paid at build time), so the vol-211 architecture
//     stands; extra constraints beyond the pair (bordered last column,
//     bottom-row rim) are post-filters;
//   - scheduled break gates: the (j+1)-th mismatch may only be spent at
//     scan depth ≥ schedule[j]; break candidates violate EXACTLY ONE
//     constraint and only at cells with ≥ 2 constraints;
//   - hints fix (piece, rot), not edge perfection: forced cells pay normal
//     break costs; hard neighbor pre-filters only before the first gate;
//     1 break reserved per unplaced gated hint (else ordinary breaks
//     starve the deep hints — every vol-211 seed died at cell 180);
//   - exact endgame at depth cells−k: optimal completion of the leftovers,
//     anytime-minimizing total breaks across thousands of completions;
//   - optional discrepancy bound (LDS-style): a path may take a
//     non-first candidate at most `max_disc` times.
//   - the vol-211 rim-supply two-pass tie-break is NOT ported (refuted,
//     −2 II).

use std::time::Instant;

use crate::endgame::{exact_tail, exact_tail2};
use crate::model::{
    mask_clear, mask_get, mask_set, InteriorModel, PieceMask, RimTargets, Tables, WORDS,
};
use crate::rng::Rng;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Scan {
    RowMajor,
    Boustro,
}

impl Scan {
    #[must_use]
    pub fn order(self, n: usize) -> Vec<usize> {
        match self {
            Self::RowMajor => (0..n * n).collect(),
            Self::Boustro => {
                let mut v = Vec::with_capacity(n * n);
                for y in 0..n {
                    if y % 2 == 0 {
                        v.extend((0..n).map(|x| y * n + x));
                    } else {
                        v.extend((0..n).rev().map(|x| y * n + x));
                    }
                }
                v
            }
        }
    }

    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::RowMajor => "row",
            Self::Boustro => "boustro",
        }
    }
}

#[derive(Clone, Copy)]
pub enum Src {
    /// neighbor placed earlier in scan order: read its facing side
    Placed { cell: u16, their_side: u8 },
    /// rim color target from the anchored frame
    Fixed(u8),
}

const NO_VIOLATE: u8 = 0xFF;

#[derive(Clone, Copy)]
enum Tab {
    /// pair_nw keyed by (ccol[n], ccol[w])
    PairNW { n: u8, w: u8 },
    PairNE { n: u8, e: u8 },
    Single { side: u8, i: u8 },
    Free,
}

/// one candidate segment: a base list + post-filters. Segment 0 is the
/// cost-0 segment (all constraints matched); later segments each violate
/// exactly one constraint (cost 1) and exist only for cells with k ≥ 2.
#[derive(Clone, Copy)]
struct Seg {
    tab: Tab,
    /// constraint indices that must additionally match
    extra: [u8; 3],
    n_extra: u8,
    /// constraint index that must mismatch (NO_VIOLATE for segment 0)
    violate: u8,
}

pub struct CellPlan {
    pub cell: u16,
    /// number of constraints known at placement time
    pub k: u8,
    /// my side for constraint i
    pub sides: [u8; 4],
    pub src: [Src; 4],
    segs: Vec<Seg>,
}

fn make_seg(sides: &[u8; 4], k: usize, exclude: Option<usize>) -> Seg {
    let active: Vec<usize> = (0..k).filter(|&i| Some(i) != exclude).collect();
    let find = |side: u8| active.iter().copied().find(|&i| sides[i] == side);
    let (i_n, i_e, i_s, i_w) = (find(0), find(1), find(2), find(3));
    let (tab, covered): (Tab, Vec<usize>) = match (i_n, i_w, i_e) {
        (Some(n), Some(w), _) => (Tab::PairNW { n: n as u8, w: w as u8 }, vec![n, w]),
        (Some(n), None, Some(e)) => (Tab::PairNE { n: n as u8, e: e as u8 }, vec![n, e]),
        (Some(n), None, None) => (Tab::Single { side: 0, i: n as u8 }, vec![n]),
        (None, Some(w), _) => (Tab::Single { side: 3, i: w as u8 }, vec![w]),
        (None, None, Some(e)) => (Tab::Single { side: 1, i: e as u8 }, vec![e]),
        (None, None, None) => i_s.map_or((Tab::Free, vec![]), |s| {
            (Tab::Single { side: 2, i: s as u8 }, vec![s])
        }),
    };
    let mut extra = [0u8; 3];
    let mut n_extra = 0u8;
    for &i in &active {
        if !covered.contains(&i) {
            extra[n_extra as usize] = i as u8;
            n_extra += 1;
        }
    }
    Seg {
        tab,
        extra,
        n_extra,
        violate: exclude.map_or(NO_VIOLATE, |i| i as u8),
    }
}

pub fn build_plans(
    model: &InteriorModel,
    scan: &[usize],
    targets: Option<&RimTargets>,
) -> Vec<CellPlan> {
    let n = model.n;
    let mut pos_in_scan = vec![0usize; model.cells];
    for (d, &c) in scan.iter().enumerate() {
        pos_in_scan[c] = d;
    }
    scan.iter()
        .map(|&cell| {
            let (y, x) = (cell / n, cell % n);
            let mut sides = [0u8; 4];
            let mut src = [Src::Fixed(0); 4];
            let mut k = 0u8;
            let nb: [(usize, Option<usize>); 4] = [
                (0, (y > 0).then(|| cell - n)),
                (1, (x + 1 < n).then(|| cell + 1)),
                (2, (y + 1 < n).then(|| cell + n)),
                (3, (x > 0).then(|| cell - 1)),
            ];
            for (s, nc) in nb {
                match nc {
                    Some(ncell) => {
                        if pos_in_scan[ncell] < pos_in_scan[cell] {
                            sides[k as usize] = s as u8;
                            src[k as usize] = Src::Placed {
                                cell: ncell as u16,
                                their_side: ((s + 2) % 4) as u8,
                            };
                            k += 1;
                        }
                    }
                    None => {
                        if let Some(tg) = targets {
                            if let Some(c) = tg[cell][s] {
                                sides[k as usize] = s as u8;
                                src[k as usize] = Src::Fixed(c);
                                k += 1;
                            }
                        }
                    }
                }
            }
            let mut segs = vec![make_seg(&sides, k as usize, None)];
            if k >= 2 {
                for i in 0..k as usize {
                    segs.push(make_seg(&sides, k as usize, Some(i)));
                }
            }
            CellPlan { cell: cell as u16, k, sides, src, segs }
        })
        .collect()
}

#[derive(Clone, Copy)]
struct Cursor {
    seg: u8,
    idx: u32,
    started: bool,
}

impl Cursor {
    const FRESH: Self = Self { seg: 0, idx: 0, started: false };
}

// --------------------------------------------------------------------- run

pub struct DfsParams {
    pub seed: u64,
    pub budget_ms: u64,
    pub restart_ms: u64,
    pub hinted: bool,
    /// ascending depth gates; len = break budget
    pub schedule: Vec<usize>,
    /// 0 = off; clamped to n (one row)
    pub exact_tail_k: usize,
    /// two-row endgame as the in-DFS trigger (vol-211: post-hoc only)
    pub tail2: bool,
    /// LDS-style bound on non-first choices per path
    pub max_disc: Option<u32>,
    pub scan: Scan,
}

impl Default for DfsParams {
    fn default() -> Self {
        Self {
            seed: 1,
            budget_ms: 30_000,
            restart_ms: 5_000,
            hinted: false,
            schedule: Vec::new(),
            exact_tail_k: 0,
            tail2: false,
            max_disc: None,
            scan: Scan::RowMajor,
        }
    }
}

pub struct DfsResult {
    pub seed: u64,
    pub max_depth: usize,
    pub nodes: u64,
    pub ms_at_max: u128,
    /// best complete assignment and its total breaks
    /// (II mismatches + rim-target mismatches)
    pub complete: Option<(Vec<(u16, u8)>, u32)>,
    pub completes_found: u64,
    /// cells scan[0..max_depth] at the max-depth moment
    pub best_prefix: Vec<(u16, u8)>,
    pub epochs: u64,
}

#[allow(clippy::too_many_lines)]
pub fn dfs_run(
    model: &InteriorModel,
    targets: Option<&RimTargets>,
    p: &DfsParams,
) -> DfsResult {
    let cells = model.cells;
    let n = model.n;
    let scan = p.scan.order(n);
    let plans = build_plans(model, &scan, targets);
    let mut pos_in_scan = vec![0usize; cells];
    for (d, &c) in scan.iter().enumerate() {
        pos_in_scan[c] = d;
    }
    let budget = p.schedule.len() as u32;
    let first_gate = p.schedule.first().copied().unwrap_or(usize::MAX);

    // pre-gate hint protection: neighbors facing a pre-gate forced cell
    // must present the hint's color (sound: those mismatches are unpayable)
    let mut req: Vec<[Option<u8>; 4]> = vec![[None; 4]; cells];
    let mut forced_by_cell: Vec<Option<(u16, u8)>> = vec![None; cells];
    let mut hint_scanpos: Vec<usize> = Vec::new();
    if p.hinted {
        for &(cell, pid, rot) in &model.hints {
            forced_by_cell[cell] = Some((pid as u16, rot));
            let d = pos_in_scan[cell];
            hint_scanpos.push(d);
            if d < first_gate {
                let e = model.rot_edges[pid][rot as usize];
                let plan = &plans[d];
                for i in 0..plan.k as usize {
                    if let Src::Placed { cell: nc, their_side } = plan.src[i] {
                        req[nc as usize][their_side as usize] =
                            Some(e[plan.sides[i] as usize]);
                    }
                }
            }
        }
    }
    // break reservation: # gated (deep) forced cells at scan pos >= d
    let mut hint_after = vec![0u32; cells + 1];
    for d in (0..cells).rev() {
        let deep_hint_here = hint_scanpos.iter().any(|&hd| hd == d && hd >= first_gate);
        hint_after[d] = hint_after[d + 1] + u32::from(deep_hint_here);
    }
    let cell_has_req: Vec<bool> = req
        .iter()
        .map(|r| r.iter().any(Option::is_some))
        .collect();
    // schedule padded with a sentinel so the hot loop indexes directly
    let mut sched_at = p.schedule.clone();
    sched_at.push(usize::MAX);

    let k_exact = if p.tail2 { 2 * n } else { p.exact_tail_k.min(n) };
    if k_exact > 0 {
        let lo = if p.tail2 { (n - 2) * n } else { cells - k_exact };
        assert!(
            scan[cells - k_exact..].iter().all(|&c| c >= lo),
            "scan tail must cover the last row(s)"
        );
    }

    let mut rng = Rng::new(p.seed);
    let mut tables = Tables::build(model, p.hinted);
    let mut grid: Vec<(u16, u8)> = vec![(u16::MAX, 0); cells];
    let mut cursors: Vec<Cursor> = vec![Cursor::FRESH; cells + 1];
    let mut cost_at = vec![0u32; cells + 1];
    let mut yields = vec![0u32; cells + 1];
    let mut disc_flag = vec![false; cells + 1];

    let mut max_depth = 0usize;
    let mut ms_at_max: u128 = 0;
    let mut best_prefix: Vec<(u16, u8)> = Vec::new();
    let mut best_complete: Option<(Vec<(u16, u8)>, u32)> = None;
    let mut completes_found: u64 = 0;
    let mut nodes: u64 = 0;
    let mut epochs: u64 = 0;
    let t0 = Instant::now();

    'epoch: loop {
        epochs += 1;
        tables.shuffle_lists(&mut rng);
        let mut avail: PieceMask = [0; WORDS];
        for pid in 0..model.np as u16 {
            mask_set(&mut avail, pid);
        }
        grid.iter_mut().for_each(|g| *g = (u16::MAX, 0));
        cursors.iter_mut().for_each(|c| *c = Cursor::FRESH);
        cost_at.iter_mut().for_each(|c| *c = 0);
        yields.iter_mut().for_each(|y| *y = 0);
        disc_flag.iter_mut().for_each(|f| *f = false);
        let mut spent: u32 = 0;
        let mut disc: u32 = 0;
        let epoch_t0 = Instant::now();

        let mut d = 0usize;
        let mut backtrack_now = false;
        loop {
            if k_exact > 0 && d == cells - k_exact && !backtrack_now {
                let mut rest: Vec<u16> = Vec::with_capacity(k_exact);
                for pid in 0..model.np as u16 {
                    if mask_get(&avail, pid) {
                        rest.push(pid);
                    }
                }
                let abort_at = best_complete
                    .as_ref()
                    .map_or(u32::MAX, |&(_, b)| b.saturating_sub(spent));
                if abort_at > 0 {
                    let (mis, asn) = if p.tail2 {
                        exact_tail2(
                            model, &tables, &grid, &rest, &forced_by_cell, targets,
                            abort_at, 30_000,
                        )
                    } else {
                        exact_tail(
                            &tables, &plans, &scan, &mut grid, d, &rest,
                            &forced_by_cell, abort_at,
                        )
                    };
                    completes_found += 1;
                    if best_complete.as_ref().is_none_or(|&(_, b)| spent + mis < b) {
                        let mut full = grid.clone();
                        if p.tail2 {
                            let start = (n - 2) * n;
                            for (j, &pr) in asn.iter().enumerate() {
                                full[start + j] = pr;
                            }
                        } else {
                            for (j, &pr) in asn.iter().enumerate() {
                                full[scan[d + j]] = pr;
                            }
                        }
                        let recount = model.count_breaks(&full, targets);
                        assert_eq!(recount, spent + mis, "endgame break accounting");
                        best_complete = Some((full.clone(), spent + mis));
                        if spent + mis == 0 {
                            return DfsResult {
                                seed: p.seed,
                                max_depth: cells,
                                nodes,
                                ms_at_max: t0.elapsed().as_millis(),
                                complete: best_complete,
                                completes_found,
                                best_prefix: full,
                                epochs,
                            };
                        }
                    }
                }
                backtrack_now = true;
            }
            if d == cells {
                let recount = model.count_breaks(&grid, targets);
                assert_eq!(recount, spent, "break accounting");
                completes_found += 1;
                if best_complete.as_ref().is_none_or(|&(_, b)| spent < b) {
                    best_complete = Some((grid.clone(), spent));
                }
                if spent == 0 {
                    return DfsResult {
                        seed: p.seed,
                        max_depth: cells,
                        nodes,
                        ms_at_max: t0.elapsed().as_millis(),
                        complete: best_complete,
                        completes_found,
                        best_prefix: grid,
                        epochs,
                    };
                }
                backtrack_now = true;
            }
            nodes += 1;
            if nodes & 0xFFFF == 0 {
                if t0.elapsed().as_millis() as u64 >= p.budget_ms {
                    return DfsResult {
                        seed: p.seed,
                        max_depth,
                        nodes,
                        ms_at_max,
                        complete: best_complete,
                        completes_found,
                        best_prefix,
                        epochs,
                    };
                }
                if epoch_t0.elapsed().as_millis() as u64 >= p.restart_ms {
                    continue 'epoch;
                }
            }

            let mut placed = false;
            if !backtrack_now {
                let plan = &plans[d];
                let cell = plan.cell as usize;
                if let Some((fp, fr)) = forced_by_cell[cell] {
                    if !cursors[d].started && mask_get(&avail, fp) {
                        cursors[d].started = true;
                        let e = tables.rot_edges[fp as usize][fr as usize];
                        let mut cost = 0u32;
                        for i in 0..plan.k as usize {
                            let want = match plan.src[i] {
                                Src::Fixed(c) => c,
                                Src::Placed { cell: nc, their_side } => {
                                    let (np_, nr) = grid[nc as usize];
                                    tables.rot_edges[np_ as usize][nr as usize]
                                        [their_side as usize]
                                }
                            };
                            if e[plan.sides[i] as usize] != want {
                                cost += 1;
                            }
                        }
                        let gate_ok = cost == 0
                            || (spent + cost <= budget
                                && d >= p.schedule[(spent + cost - 1) as usize]);
                        if gate_ok {
                            grid[cell] = (fp, fr);
                            mask_clear(&mut avail, fp);
                            cost_at[d] = cost;
                            spent += cost;
                            placed = true;
                        }
                    }
                } else {
                    let mut ccol = [0u8; 4];
                    for i in 0..plan.k as usize {
                        ccol[i] = match plan.src[i] {
                            Src::Fixed(c) => c,
                            Src::Placed { cell: nc, their_side } => {
                                let (np_, nr) = grid[nc as usize];
                                tables.rot_edges[np_ as usize][nr as usize]
                                    [their_side as usize]
                            }
                        };
                    }
                    let break_open = spent + 1 + hint_after[d] <= budget
                        && d >= sched_at[(spent as usize).min(budget as usize)]
                        && plan.k >= 2;
                    // LDS: once the discrepancy budget is full, a cell that
                    // already yielded may not deviate further — unless it
                    // already holds a counted deviation
                    let lds_block = p
                        .max_disc
                        .is_some_and(|m| disc >= m && yields[d] >= 1 && !disc_flag[d]);
                    if !lds_block {
                        let mut cur = cursors[d];
                        cur.started = true;
                        let nseg = if break_open { plan.segs.len() } else { 1 };
                        let rq = &req[cell];
                        let has_req = cell_has_req[cell];
                        'segs: while (cur.seg as usize) < nseg {
                            let seg = &plan.segs[cur.seg as usize];
                            let list: &[u16] = match seg.tab {
                                Tab::PairNW { n: ni, w: wi } => {
                                    &tables.pair_nw[ccol[ni as usize] as usize
                                        * tables.ncolors
                                        + ccol[wi as usize] as usize]
                                }
                                Tab::PairNE { n: ni, e: ei } => {
                                    &tables.pair_ne[ccol[ni as usize] as usize
                                        * tables.ncolors
                                        + ccol[ei as usize] as usize]
                                }
                                Tab::Single { side, i } => {
                                    &tables.single[side as usize][ccol[i as usize] as usize]
                                }
                                Tab::Free => &tables.free,
                            };
                            while (cur.idx as usize) < list.len() {
                                let c = list[cur.idx as usize];
                                cur.idx += 1;
                                let pid = c >> 2;
                                if !mask_get(&avail, pid) {
                                    continue;
                                }
                                let rot = (c & 3) as u8;
                                let e = &tables.rot_edges[pid as usize][rot as usize];
                                let mut ok = true;
                                for xi in 0..seg.n_extra as usize {
                                    let i = seg.extra[xi] as usize;
                                    if e[plan.sides[i] as usize] != ccol[i] {
                                        ok = false;
                                        break;
                                    }
                                }
                                if !ok {
                                    continue;
                                }
                                if seg.violate != NO_VIOLATE {
                                    let i = seg.violate as usize;
                                    if e[plan.sides[i] as usize] == ccol[i] {
                                        continue;
                                    }
                                }
                                if has_req
                                    && (0..4).any(|s| rq[s].is_some_and(|c2| c2 != e[s]))
                                {
                                    continue;
                                }
                                let cost = u32::from(seg.violate != NO_VIOLATE);
                                grid[cell] = (pid, rot);
                                mask_clear(&mut avail, pid);
                                cost_at[d] = cost;
                                spent += cost;
                                yields[d] += 1;
                                if yields[d] == 2 {
                                    disc += 1;
                                    disc_flag[d] = true;
                                }
                                placed = true;
                                break 'segs;
                            }
                            cur.seg += 1;
                            cur.idx = 0;
                        }
                        cursors[d] = cur;
                    }
                }
            }

            if placed {
                d += 1;
                if d > max_depth {
                    max_depth = d;
                    ms_at_max = t0.elapsed().as_millis();
                    best_prefix = (0..d).map(|j| grid[scan[j]]).collect();
                }
            } else {
                backtrack_now = false;
                cursors[d] = Cursor::FRESH;
                yields[d] = 0;
                if disc_flag[d] {
                    disc -= 1;
                    disc_flag[d] = false;
                }
                if d == 0 {
                    continue 'epoch;
                }
                d -= 1;
                let cell = plans[d].cell as usize;
                let (pid, _) = grid[cell];
                mask_set(&mut avail, pid);
                grid[cell] = (u16::MAX, 0);
                spent -= cost_at[d];
                cost_at[d] = 0;
                if forced_by_cell[cell].is_some() {
                    cursors[d] = Cursor::FRESH;
                    loop {
                        if d == 0 {
                            continue 'epoch;
                        }
                        d -= 1;
                        let cell = plans[d].cell as usize;
                        let (pid, _) = grid[cell];
                        mask_set(&mut avail, pid);
                        grid[cell] = (u16::MAX, 0);
                        spent -= cost_at[d];
                        cost_at[d] = 0;
                        if forced_by_cell[cell].is_none() {
                            break;
                        }
                        cursors[d] = Cursor::FRESH;
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// brute-force reference: all (pid, rot, cost) candidates at a cell
    fn reference_cands(
        tables: &Tables,
        model: &InteriorModel,
        plan: &CellPlan,
        ccol: &[u8; 4],
        avail: &PieceMask,
        break_open: bool,
        hinted: bool,
    ) -> Vec<(u16, u8, u32)> {
        let mut hint_piece = vec![false; model.np];
        if hinted {
            for &(_, pid, _) in &model.hints {
                hint_piece[pid] = true;
            }
        }
        let mut out = Vec::new();
        for pid in 0..tables.np as u16 {
            if !mask_get(avail, pid) || hint_piece[pid as usize] {
                continue;
            }
            for rot in 0..4u8 {
                let e = tables.rot_edges[pid as usize][rot as usize];
                let mut mis = 0u32;
                for i in 0..plan.k as usize {
                    if e[plan.sides[i] as usize] != ccol[i] {
                        mis += 1;
                    }
                }
                if mis == 0 {
                    out.push((pid, rot, 0));
                } else if mis == 1 && break_open && plan.k >= 2 {
                    out.push((pid, rot, 1));
                }
            }
        }
        out
    }

    /// drain all candidates at a cell through the segment machinery
    fn drain(
        tables: &Tables,
        plan: &CellPlan,
        ccol: &[u8; 4],
        avail: &PieceMask,
        break_open: bool,
    ) -> Vec<(u16, u8, u32)> {
        let mut out = Vec::new();
        let nseg = if break_open { plan.segs.len() } else { 1 };
        for (si, seg) in plan.segs.iter().enumerate().take(nseg) {
            let list: &[u16] = match seg.tab {
                Tab::PairNW { n, w } => {
                    &tables.pair_nw
                        [ccol[n as usize] as usize * tables.ncolors + ccol[w as usize] as usize]
                }
                Tab::PairNE { n, e } => {
                    &tables.pair_ne
                        [ccol[n as usize] as usize * tables.ncolors + ccol[e as usize] as usize]
                }
                Tab::Single { side, i } => {
                    &tables.single[side as usize][ccol[i as usize] as usize]
                }
                Tab::Free => &tables.free,
            };
            for &c in list {
                let pid = c >> 2;
                if !mask_get(avail, pid) {
                    continue;
                }
                let rot = (c & 3) as u8;
                let e = tables.rot_edges[pid as usize][rot as usize];
                let mut ok = true;
                for xi in 0..seg.n_extra as usize {
                    let i = seg.extra[xi] as usize;
                    if e[plan.sides[i] as usize] != ccol[i] {
                        ok = false;
                        break;
                    }
                }
                if !ok {
                    continue;
                }
                if seg.violate != NO_VIOLATE {
                    let i = seg.violate as usize;
                    if e[plan.sides[i] as usize] == ccol[i] {
                        continue;
                    }
                }
                out.push((pid, rot, u32::from(si > 0)));
            }
        }
        out
    }

    #[test]
    fn segments_enumerate_reference_set() {
        for (hinted, scan) in [(false, Scan::Boustro), (true, Scan::RowMajor)] {
            let (mut m, sol, targets) = InteriorModel::synthetic(5, 5, 3);
            if hinted {
                m.hints.push((7, sol[7].0 as usize, sol[7].1));
            }
            let so = scan.order(5);
            let plans = build_plans(&m, &so, Some(&targets));
            let tables = Tables::build(&m, hinted);
            let mut grid = vec![(u16::MAX, 0u8); m.cells];
            let mut avail: PieceMask = [0; WORDS];
            for pid in 0..m.np as u16 {
                mask_set(&mut avail, pid);
            }
            let mut placed_to = 0usize;
            for d in [5usize, 12, 19, 24] {
                while placed_to < d {
                    let cell = so[placed_to];
                    let pid = placed_to as u16;
                    grid[cell] = (pid, (placed_to % 4) as u8);
                    mask_clear(&mut avail, pid);
                    placed_to += 1;
                }
                let plan = &plans[d];
                let mut ccol = [0u8; 4];
                for i in 0..plan.k as usize {
                    ccol[i] = match plan.src[i] {
                        Src::Fixed(c) => c,
                        Src::Placed { cell, their_side } => {
                            let (p2, r) = grid[cell as usize];
                            assert!(p2 != u16::MAX, "plan must reference placed cells");
                            tables.rot_edges[p2 as usize][r as usize][their_side as usize]
                        }
                    };
                }
                for break_open in [false, true] {
                    let got = drain(&tables, plan, &ccol, &avail, break_open);
                    let mut got_sorted = got.clone();
                    got_sorted.sort_unstable();
                    let mut want =
                        reference_cands(&tables, &m, plan, &ccol, &avail, break_open, hinted);
                    want.sort_unstable();
                    assert_eq!(got_sorted, want, "d={d} break_open={break_open}");
                    // cost-0 strictly before breaks in yield order
                    if let Some(fb) = got.iter().position(|&(_, _, c)| c > 0) {
                        assert!(got[..fb].iter().all(|&(_, _, c)| c == 0));
                        assert!(got[fb..].iter().all(|&(_, _, c)| c == 1));
                    }
                }
            }
        }
    }

    #[test]
    fn perfect_dfs_solves_synthetic_free_and_bordered() {
        for seed in 1..=3u64 {
            let (m, _, targets) = InteriorModel::synthetic(5, 6, seed * 11);
            for tg in [None, Some(&targets)] {
                let p = DfsParams {
                    seed,
                    budget_ms: 20_000,
                    restart_ms: 2_000,
                    exact_tail_k: 0,
                    ..DfsParams::default()
                };
                let r = dfs_run(&m, tg, &p);
                let (grid, breaks) =
                    r.complete.unwrap_or_else(|| panic!("no completion seed {seed}"));
                assert_eq!(breaks, 0);
                assert_eq!(m.count_breaks(&grid, tg), 0);
                let mut seen = vec![false; m.np];
                for &(pid, _) in &grid {
                    assert!(!seen[pid as usize]);
                    seen[pid as usize] = true;
                }
            }
        }
    }

    #[test]
    fn break_dfs_with_exact_tail_completes_and_accounts() {
        let (m, _, targets) = InteriorModel::synthetic(6, 4, 5);
        let p = DfsParams {
            seed: 2,
            budget_ms: 3_000,
            restart_ms: 1_000,
            schedule: vec![20, 26, 30],
            exact_tail_k: 6,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(m.count_breaks(&grid, Some(&targets)), breaks);
    }

    #[test]
    fn hints_respected_with_breaks() {
        let (mut m, sol, targets) = InteriorModel::synthetic(5, 4, 9);
        for &cell in &[6usize, 12, 22] {
            m.hints.push((cell, sol[cell].0 as usize, sol[cell].1));
        }
        let p = DfsParams {
            seed: 4,
            budget_ms: 10_000,
            restart_ms: 2_000,
            hinted: true,
            schedule: vec![15, 18, 21, 23],
            exact_tail_k: 5,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(m.count_breaks(&grid, Some(&targets)), breaks);
        for &(cell, pid, rot) in &m.hints {
            assert_eq!(grid[cell], (pid as u16, rot), "hint at {cell}");
        }
    }

    #[test]
    fn boustro_dfs_with_tail_completes() {
        let (m, _, targets) = InteriorModel::synthetic(6, 4, 17);
        let p = DfsParams {
            seed: 3,
            budget_ms: 3_000,
            restart_ms: 1_000,
            schedule: vec![18, 24, 30],
            exact_tail_k: 6,
            scan: Scan::Boustro,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(m.count_breaks(&grid, Some(&targets)), breaks);
    }
}
