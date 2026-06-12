// Vol-218 BANDSAW testbed: parametric N×N E2-like instances with
// hints, exact band machinery (distinct-piece counts, exhaustive B&B,
// meet-in-the-middle band-split solve) and the repeats-allowed
// counting/tropical oracle — all selftested against brute force.
//
// All band/endgame work is COLUMN-MAJOR: within a band, vertical
// coupling (N edges + border structure of the bottom row) binds at
// every column instead of after a full free row — the same collapse
// that makes conditioned band sub-problems enumerable at all
// (vol-217 finding; row-major free-row enumeration is ~1e8× wider).
//
// Cost convention (stage4_finish-compatible): each cell pays its N
// edge and its W edge; board-edge sides are structural (candidates
// filtered to have BORDER exactly on out-facing sides). A band's
// first row pays N against a given frontier (or nothing, if the
// frontier is None — BANDSAW bottom bands pay the join at join time).

use std::collections::HashMap;

use eternity2_generator::{generate_with_solution, GeneratorConfig};

pub const NONE_COLOR: u8 = u8::MAX;

pub struct Mini {
    pub n: usize,
    pub colors: u32,
    pub seed: u64,
    pub nc: usize,                    // dense color range 0..nc (border=0)
    pub rot: Vec<[[u8; 4]; 4]>,       // pid -> rot -> [N,E,S,W]
    pub hints: Vec<(usize, u16, u8)>, // (pos, pid, rot)
    pub solution: Vec<(u16, u8)>,     // canonical (pid, rot) per pos
}

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    let mut out = [0u8; 4];
    for i in 0..4 {
        out[i] = e[(i + 4 - r as usize) % 4];
    }
    out
}

/// E2-analog hint cells for an n×n board: four quarter hints at
/// rows/cols {2, n-3} plus the center analog of E2's (7,8).
#[must_use]
pub fn hint_cells(n: usize) -> [usize; 5] {
    let q = n - 3;
    let (cx, cy) = (n / 2 - 1, n / 2);
    [
        2 * n + 2,
        2 * n + q,
        cy * n + cx,
        q * n + 2,
        q * n + q,
    ]
}

impl Mini {
    #[must_use]
    pub fn from_seed(n: usize, colors: u32, seed: u64, hint_cells: &[usize]) -> Self {
        let (puzzle, solution) = generate_with_solution(GeneratorConfig {
            size: n as u32,
            interior_colors: colors,
            seed,
        })
        .expect("generator must succeed");
        // pieces() is SHUFFLED by the generator — index rot by piece id,
        // not iteration order (vol-218 M0 catch: 30 phantom breaks).
        let mut rot = vec![[[0u8; 4]; 4]; n * n];
        for p in puzzle.pieces() {
            let e = [p.edges.top(), p.edges.right(), p.edges.bottom(), p.edges.left()];
            let mut rr = [[0u8; 4]; 4];
            for r in 0..4 {
                rr[r] = rotate_edges(e, r as u8);
            }
            rot[p.id as usize] = rr;
        }
        // pieces are shuffled; solution[pos] indexes by position
        let mut sol = vec![(0u16, 0u8); n * n];
        for pl in &solution {
            sol[pl.position as usize] = (pl.piece_id, pl.rotation.as_u8());
        }
        let hints = hint_cells
            .iter()
            .map(|&pos| (pos, sol[pos].0, sol[pos].1))
            .collect();
        Mini { n, colors, seed, nc: colors as usize + 1, rot, hints, solution: sol }
    }

    /// Structural candidate test: BORDER exactly on out-facing sides.
    #[must_use]
    pub fn fits_cell(&self, pid: u16, rt: u8, r: usize, c: usize) -> bool {
        let o = self.rot[pid as usize][rt as usize];
        let out = [r == 0, c == self.n - 1, r == self.n - 1, c == 0];
        (0..4).all(|s| (o[s] == 0) == out[s])
    }

    /// All structural candidates at (r,c) from an availability mask
    /// over piece ids (bit pid set = available).
    #[must_use]
    pub fn cands_at(&self, r: usize, c: usize, avail: &[bool]) -> Vec<(u16, u8)> {
        let mut out = Vec::new();
        for pid in 0..self.n * self.n {
            if !avail[pid] {
                continue;
            }
            for rt in 0..4u8 {
                if self.fits_cell(pid as u16, rt, r, c) {
                    out.push((pid as u16, rt));
                }
            }
        }
        out
    }

    /// Breaks of a fully/partially placed board (placement[pos]);
    /// counts N and W edges between two PLACED cells only.
    #[must_use]
    pub fn breaks_of(&self, placement: &[Option<(u16, u8)>]) -> u32 {
        let n = self.n;
        let mut b = 0;
        for pos in 0..n * n {
            let Some((p, rt)) = placement[pos] else { continue };
            let o = self.rot[p as usize][rt as usize];
            let (r, c) = (pos / n, pos % n);
            if r > 0 {
                if let Some((p2, rt2)) = placement[pos - n] {
                    let o2 = self.rot[p2 as usize][rt2 as usize];
                    b += u32::from(o2[2] != o[0]);
                }
            }
            if c > 0 {
                if let Some((p2, rt2)) = placement[pos - 1] {
                    let o2 = self.rot[p2 as usize][rt2 as usize];
                    b += u32::from(o2[1] != o[3]);
                }
            }
        }
        b
    }
}

// ---------------- band region description ----------------

/// A band of `k` full rows `r0..r0+k`. `frontier[c]` = the color the
/// first band row's N edge must match at column c; NONE_COLOR = free
/// (no charge). Pool = explicit piece list; forced = (pos -> cand).
pub struct Band<'a> {
    pub mini: &'a Mini,
    pub r0: usize,
    pub k: usize,
    pub frontier: Option<Vec<u8>>,
    pub pool: Vec<u16>,
    pub forced: HashMap<usize, (u16, u8)>,
}

impl Band<'_> {
    /// Column-major cell sequence: (idx within band, r, c).
    fn cells(&self) -> Vec<(usize, usize)> {
        let mut v = Vec::with_capacity(self.k * self.mini.n);
        for c in 0..self.mini.n {
            for r in self.r0..self.r0 + self.k {
                v.push((r, c));
            }
        }
        v
    }

    /// Per-cell structural candidates over the band pool (pool-index
    /// based). Forced cells get exactly their single candidate.
    fn cand_table(&self) -> Vec<Vec<Cand>> {
        let m = self.mini;
        let mut avail = vec![false; m.n * m.n];
        for &p in &self.pool {
            avail[p as usize] = true;
        }
        let pool_idx: HashMap<u16, u8> = self
            .pool
            .iter()
            .enumerate()
            .map(|(i, &p)| (p, u8::try_from(i).expect("pool <= 64")))
            .collect();
        self.cells()
            .iter()
            .map(|&(r, c)| {
                let pos = r * m.n + c;
                let list: Vec<(u16, u8)> = match self.forced.get(&pos) {
                    Some(&f) => vec![f],
                    None => m.cands_at(r, c, &avail),
                };
                list.into_iter()
                    .map(|(p, rt)| {
                        let o = m.rot[p as usize][rt as usize];
                        Cand { pid: p, pi: pool_idx[&p], rt, n: o[0], e: o[1], s: o[2], w: o[3] }
                    })
                    .collect()
            })
            .collect()
    }
}

#[derive(Clone, Copy)]
pub struct Cand {
    pub pid: u16,
    pub pi: u8, // pool index (mask bit)
    pub rt: u8,
    pub n: u8,
    pub e: u8,
    pub s: u8,
    pub w: u8,
}

// ---------------- exact distinct-piece counting ----------------

pub struct ExactCounts {
    pub by_b: Vec<u64>, // completions paying exactly b, b <= bmax
    pub nodes: u64,
    pub capped: bool,
}

/// DFS count of distinct-piece band fillings by exact total cost.
/// Column-major. Budget prune at bmax. Loud cap.
#[must_use]
pub fn exact_count(band: &Band, bmax: u32, node_cap: u64) -> ExactCounts {
    let m = band.mini;
    let n = m.n;
    let cells = band.cells();
    let cands = band.cand_table();
    let total = cells.len();
    let mut used = vec![false; band.pool.len()];
    let mut south = vec![vec![0u8; n]; band.k]; // by band-row
    let mut east = vec![0u8; total];
    let mut by_b = vec![0u64; bmax as usize + 1];
    let mut nodes = 0u64;
    let mut capped = false;

    fn rec(
        d: usize,
        spent: u32,
        cells: &[(usize, usize)],
        cands: &[Vec<Cand>],
        band: &Band,
        used: &mut [bool],
        south: &mut [Vec<u8>],
        east: &mut [u8],
        by_b: &mut [u64],
        nodes: &mut u64,
        capped: &mut bool,
        bmax: u32,
        node_cap: u64,
    ) {
        if *capped {
            return;
        }
        if d == cells.len() {
            by_b[spent as usize] += 1;
            return;
        }
        let (r, c) = cells[d];
        let i = r - band.r0;
        let tn = if i == 0 {
            band.frontier.as_ref().map_or(NONE_COLOR, |f| f[c])
        } else {
            south[i - 1][c]
        };
        let tw = if c == 0 { NONE_COLOR } else { east[d - band.k] };
        for cd in &cands[d] {
            if used[cd.pi as usize] {
                continue;
            }
            let mut cost = spent;
            if tn != NONE_COLOR {
                cost += u32::from(cd.n != tn);
            }
            if tw != NONE_COLOR {
                cost += u32::from(cd.w != tw);
            }
            if cost > bmax {
                continue;
            }
            *nodes += 1;
            if *nodes >= node_cap {
                *capped = true;
                return;
            }
            used[cd.pi as usize] = true;
            south[i][c] = cd.s;
            east[d] = cd.e;
            rec(d + 1, cost, cells, cands, band, used, south, east, by_b, nodes, capped, bmax, node_cap);
            used[cd.pi as usize] = false;
        }
    }
    rec(0, 0, &cells, &cands, band, &mut used, &mut south, &mut east, &mut by_b, &mut nodes, &mut capped, bmax, node_cap);
    ExactCounts { by_b, nodes, capped }
}

// ---------------- repeats-allowed counting DP ----------------

/// Repeats-allowed count of band fillings by exact total cost
/// (transfer DP, column-major, inclusion-exclusion contractions).
/// Exact for the relaxed model — selftested against brute force.
#[must_use]
pub fn relax_profile(band: &Band, bmax: u32) -> Vec<f64> {
    let m = band.mini;
    let n = m.n;
    let nc = m.nc;
    let k = band.k;
    let b = bmax as usize + 1;
    let cands = band.cand_table();

    // state tensors: with-s  = [s][e_0..e_{k-1}][b]
    //                without = [e_0..e_{k-1}][b]
    let ek: usize = nc.pow(k as u32);
    let mut cur: Vec<f64> = Vec::new(); // without-s at column boundaries
    let mut have_any = false;

    for c in 0..n {
        let mut mid: Vec<f64> = Vec::new(); // with-s inside the column
        for i in 0..k {
            let d = c * k + i;
            let last = i == k - 1;
            let tn_frontier = if i == 0 {
                band.frontier.as_ref().map_or(NONE_COLOR, |f| f[c])
            } else {
                NONE_COLOR // matched against s axis
            };
            // group candidates by (n, w, e, s)
            let mut groups: HashMap<(u8, u8, u8, u8), f64> = HashMap::new();
            for cd in &cands[d] {
                *groups.entry((cd.n, cd.w, cd.e, cd.s)).or_insert(0.0) += 1.0;
            }
            // output tensor
            let out_has_s = !last;
            let out_sz = if out_has_s { nc * ek * b } else { ek * b };
            let mut out = vec![0.0f64; out_sz];
            // strides for e axes in the e-block (row-major e_0..e_{k-1})
            let estr: Vec<usize> = (0..k).map(|j| nc.pow((k - 1 - j) as u32)).collect();

            if !have_any && c == 0 && i == 0 {
                // very first cell: park e_1..e_{k-1} at 0
                for (&(cn, _w, e, s), &mult) in &groups {
                    let mut cost = 0usize;
                    if tn_frontier != NONE_COLOR {
                        cost += usize::from(cn != tn_frontier);
                    }
                    if cost >= b {
                        continue;
                    }
                    let eblock = e as usize * estr[0];
                    let off = if out_has_s {
                        (s as usize * ek + eblock) * b
                    } else {
                        eblock * b
                    };
                    out[off + cost] += mult;
                }
            } else if i == 0 {
                // column start: input = without-s [e][b]; contract w on e_0
                // sums over e_0:
                let mut sum_w = vec![0.0f64; ek / nc * b]; // [e_1..e_{k-1}][b]
                let rest = ek / nc;
                for w in 0..nc {
                    let base = w * rest * b;
                    for q in 0..rest * b {
                        sum_w[q] += cur[base + q];
                    }
                }
                for (&(cn, w, e, s), &mult) in &groups {
                    let mut c0 = 0usize;
                    if tn_frontier != NONE_COLOR {
                        c0 += usize::from(cn != tn_frontier);
                    }
                    let wmatch_base = w as usize * rest * b;
                    for q in 0..rest {
                        // q indexes e_1..e_{k-1}; output e_0 = e, others = q
                        let eblock = e as usize * estr[0] + q;
                        let off = if out_has_s {
                            (s as usize * ek + eblock) * b
                        } else {
                            eblock * b
                        };
                        let qb = q * b;
                        for bb in 0..b {
                            let matched = cur[wmatch_base + qb + bb];
                            let tot = sum_w[qb + bb];
                            // w match: cost c0; w mismatch: c0+1
                            if bb + c0 < b {
                                out[off + bb + c0] += mult * matched;
                            }
                            if bb + c0 + 1 < b {
                                out[off + bb + c0 + 1] += mult * (tot - matched);
                            }
                        }
                    }
                }
            } else {
                // mid column: input = with-s [s][e][b]; contract n on s
                // axis and (if c>0) w on e_i axis.
                let ei = estr[i];
                let with_w = c > 0;
                // we need, per (kn, kw, q over other axes): tin[kn,kw,q],
                // sum_s[kw,q], sum_w[kn,q], sum_sw[q].
                let oth: Vec<usize> = (0..k).filter(|&j| j != i).map(|j| estr[j]).collect();
                let rest: usize = nc.pow((k - 1) as u32);
                // q -> offset within the e-block: mixed radix over the
                // other axes (last axis = least significant digit)
                let mut qoff = vec![0usize; rest];
                for (q, slot) in qoff.iter_mut().enumerate() {
                    let mut rem = q;
                    let mut off = 0usize;
                    for &st in oth.iter().rev() {
                        off += (rem % nc) * st;
                        rem /= nc;
                    }
                    *slot = off;
                }
                let sb = ek * b; // s stride in with-s tensor
                // sums
                let mut sum_s = vec![0.0f64; ek * b]; // [e][b]
                for s in 0..nc {
                    let base = s * sb;
                    for x in 0..ek * b {
                        sum_s[x] += mid[base + x];
                    }
                }
                let (sum_w, sum_sw) = if with_w {
                    let mut sw = vec![0.0f64; nc * rest * b]; // [s][q][b]
                    let mut ssw = vec![0.0f64; rest * b]; // [q][b]
                    for s in 0..nc {
                        for w in 0..nc {
                            let base = s * sb + w * ei * b;
                            for q in 0..rest {
                                let src = base + qoff[q] * b;
                                let dst = (s * rest + q) * b;
                                for bb in 0..b {
                                    sw[dst + bb] += mid[src + bb];
                                }
                            }
                        }
                    }
                    for s in 0..nc {
                        let base = s * rest * b;
                        for x in 0..rest * b {
                            ssw[x] += sw[base + x];
                        }
                    }
                    (sw, ssw)
                } else {
                    (Vec::new(), Vec::new())
                };

                for (&(cn, w, e, s), &mult) in &groups {
                    let kn = cn as usize;
                    let kw = w as usize;
                    for q in 0..rest {
                        let eblock_out = e as usize * ei + qoff[q];
                        let off_out = if out_has_s {
                            (s as usize * ek + eblock_out) * b
                        } else {
                            eblock_out * b
                        };
                        if with_w {
                            let t_both = kn * sb + kw * ei * b + qoff[q] * b;
                            let t_sums = kw * ei * b + qoff[q] * b; // in sum_s
                            let t_sumw = (kn * rest + q) * b;
                            let t_ssw = q * b;
                            for bb in 0..b {
                                let both = mid[t_both + bb];
                                let nmatch = sum_w[t_sumw + bb]; // n matched, any w
                                let wmatch = sum_s[t_sums + bb]; // w matched, any n
                                let tot = sum_sw[t_ssw + bb];
                                let n_only = nmatch - both; // w mismatch
                                let w_only = wmatch - both; // n mismatch
                                let neither = tot - nmatch - wmatch + both;
                                if bb < b {
                                    out[off_out + bb] += mult * both;
                                }
                                if bb + 1 < b {
                                    out[off_out + bb + 1] += mult * (n_only + w_only);
                                }
                                if bb + 2 < b {
                                    out[off_out + bb + 2] += mult * neither;
                                }
                            }
                        } else {
                            // c == 0: only the n (s-axis) contraction
                            let t_match = kn * sb + qoff[q] * b; // e_i parked at 0
                            // sum over s of mid at e-block (e_i parked 0, q)
                            let t_tot = qoff[q] * b;
                            for bb in 0..b {
                                let matched = mid[t_match + bb];
                                let tot = sum_s[t_tot + bb];
                                if bb < b {
                                    out[off_out + bb] += mult * matched;
                                }
                                if bb + 1 < b {
                                    out[off_out + bb + 1] += mult * (tot - matched);
                                }
                            }
                        }
                    }
                }
            }
            if last {
                cur = out;
                have_any = true;
            } else {
                mid = out;
            }
        }
    }
    // readout: sum over all e axes
    let mut profile = vec![0.0f64; b];
    for chunk in cur.chunks(b) {
        for (bb, v) in chunk.iter().enumerate() {
            profile[bb] += v;
        }
    }
    profile
}

/// Repeats-allowed min cost (tropical floor): smallest b with
/// relax count > 0, escalating bmax. Admissible LB for the exact
/// distinct-piece min-break.
#[must_use]
pub fn relax_floor(band: &Band, bmax0: u32) -> u32 {
    let mut bmax = bmax0;
    loop {
        let prof = relax_profile(band, bmax);
        if let Some(bb) = prof.iter().position(|&x| x > 0.0) {
            return u32::try_from(bb).unwrap();
        }
        bmax *= 2;
        assert!(bmax <= 4096, "relax_floor: no filling at any cost?");
    }
}

// ---------------- exhaustive B&B (ground truth) ----------------

pub struct BbResult {
    pub best: Option<u32>,
    pub nodes: u64,
    pub elapsed_ms: u128,
    pub capped: bool,
    pub best_fill: Vec<(usize, u16, u8)>, // (pos, pid, rot)
}

/// Anytime branch-and-bound min-break fill of a band; exhaustive when
/// budget/node caps are not hit (capped=false ⇒ best is EXACT).
/// Column-major, cost-bucketed candidate order (greedy leftmost).
#[must_use]
pub fn bb_min_break(band: &Band, max_breaks: u32, budget_ms: u64, node_cap: u64) -> BbResult {
    let m = band.mini;
    let n = m.n;
    let cells = band.cells();
    let cands = band.cand_table();
    let total = cells.len();
    let t0 = std::time::Instant::now();

    let mut used = vec![false; band.pool.len()];
    let mut south = vec![vec![0u8; n]; band.k];
    let mut east = vec![0u8; total];
    let mut order: Vec<Vec<(u16, u8)>> = vec![Vec::new(); total]; // (cand idx, cost)
    let mut cursor = vec![0usize; total];
    let mut chosen = vec![0usize; total];
    let mut spent = vec![0u32; total + 1];
    let mut best: Option<u32> = None;
    let mut best_fill: Vec<(usize, u16, u8)> = Vec::new();
    let mut nodes = 0u64;
    let mut capped = false;

    let enter = |d: usize,
                 used: &[bool],
                 south: &[Vec<u8>],
                 east: &[u8],
                 order: &mut Vec<Vec<(u16, u8)>>,
                 cursor: &mut Vec<usize>| {
        let (r, c) = cells[d];
        let i = r - band.r0;
        let tn = if i == 0 {
            band.frontier.as_ref().map_or(NONE_COLOR, |f| f[c])
        } else {
            south[i - 1][c]
        };
        let tw = if c == 0 { NONE_COLOR } else { east[d - band.k] };
        let list = &cands[d];
        let mut buckets: [Vec<u16>; 3] = [Vec::new(), Vec::new(), Vec::new()];
        for (ci, cd) in list.iter().enumerate() {
            if used[cd.pi as usize] {
                continue;
            }
            let mut cost = 0u8;
            if tn != NONE_COLOR {
                cost += u8::from(cd.n != tn);
            }
            if tw != NONE_COLOR {
                cost += u8::from(cd.w != tw);
            }
            buckets[cost as usize].push(u16::try_from(ci).unwrap());
        }
        let o = &mut order[d];
        o.clear();
        for (cost, bucket) in buckets.iter().enumerate() {
            for &ci in bucket {
                o.push((ci, u8::try_from(cost).unwrap()));
            }
        }
        cursor[d] = 0;
    };

    let mut depth = 0usize;
    enter(0, &used, &south, &east, &mut order, &mut cursor);
    loop {
        if (nodes & 0x3FFF) == 0
            && (t0.elapsed().as_millis() as u64 >= budget_ms || nodes >= node_cap)
        {
            capped = true;
            break;
        }
        let budget = best.map_or(max_breaks, |bv| bv.saturating_sub(1).min(max_breaks));
        let mut advanced = false;
        {
            let mut oi = cursor[depth];
            while oi < order[depth].len() {
                let (ci, cost) = order[depth][oi];
                let ns = spent[depth] + u32::from(cost);
                if ns > budget {
                    oi = order[depth].len();
                    break;
                }
                let cd = cands[depth][ci as usize];
                if used[cd.pi as usize] {
                    oi += 1;
                    continue;
                }
                nodes += 1;
                chosen[depth] = oi;
                used[cd.pi as usize] = true;
                let (r, c) = cells[depth];
                south[r - band.r0][c] = cd.s;
                east[depth] = cd.e;
                spent[depth + 1] = ns;
                cursor[depth] = oi;
                depth += 1;
                advanced = true;
                break;
            }
            if !advanced {
                cursor[depth] = oi;
            }
        }
        if advanced {
            if depth == total {
                let tot = spent[total];
                if best.is_none_or(|bv| tot < bv) {
                    best = Some(tot);
                    best_fill = (0..total)
                        .map(|d| {
                            let cd = cands[d][order[d][chosen[d]].0 as usize];
                            let (r, c) = cells[d];
                            (r * n + c, cd.pid, cd.rt)
                        })
                        .collect();
                    if tot == 0 {
                        break;
                    }
                }
                depth -= 1;
                let cd = cands[depth][order[depth][chosen[depth]].0 as usize];
                used[cd.pi as usize] = false;
                cursor[depth] = chosen[depth] + 1;
            } else {
                enter(depth, &used, &south, &east, &mut order, &mut cursor);
            }
        } else {
            if depth == 0 {
                break;
            }
            depth -= 1;
            let cd = cands[depth][order[depth][chosen[depth]].0 as usize];
            used[cd.pi as usize] = false;
            cursor[depth] = chosen[depth] + 1;
        }
    }
    BbResult { best, nodes, elapsed_ms: t0.elapsed().as_millis(), capped, best_fill }
}

// ---------------- BANDSAW: meet-in-the-middle exact solve ----------------

pub struct BandsawResult {
    pub best: Option<u32>,
    pub final_budget: u32,
    pub top_raw: u64,
    pub bottom_raw: u64,
    pub top_keys: usize,
    pub bottom_keys: usize,
    pub bottom_mask_groups: usize,
    pub join_pairs: u64,
    pub elapsed_ms: u128,
    pub capped: bool,
}

fn pack_vec(v: &[u8]) -> u128 {
    let mut x = 0u128;
    for (i, &c) in v.iter().enumerate() {
        x |= u128::from(c) << (5 * i);
    }
    x
}

fn vec_mismatch(a: u128, b: u128, n: usize) -> u32 {
    let mut cnt = 0;
    for i in 0..n {
        let ca = (a >> (5 * i)) & 31;
        let cb = (b >> (5 * i)) & 31;
        cnt += u32::from(ca != cb);
    }
    cnt
}

/// Enumerate all distinct-piece fillings of a band at cost <= budget,
/// reporting (used-pool-mask, interface vector, cost) at each leaf.
/// `interface`: Top = souths of the LAST band row; Bottom = norths of
/// the FIRST band row (whose N edges are NOT charged here).
fn enumerate_band(
    band: &Band,
    budget: u32,
    charge_first_row_n: bool,
    interface_top: bool,
    node_cap: u64,
    mut leaf: impl FnMut(u64, u128, u32),
) -> (u64, u64, bool) {
    let m = band.mini;
    let n = m.n;
    let cells = band.cells();
    let cands = band.cand_table();
    let total = cells.len();
    let mut used_mask = 0u64;
    let mut used = vec![false; band.pool.len()];
    let mut south = vec![vec![0u8; n]; band.k];
    let mut north0 = vec![0u8; n];
    let mut east = vec![0u8; total];
    let mut raw = 0u64;
    let mut nodes = 0u64;
    let mut capped = false;

    #[allow(clippy::too_many_arguments)]
    fn rec(
        d: usize,
        spent: u32,
        budget: u32,
        charge_first: bool,
        iface_top: bool,
        cells: &[(usize, usize)],
        cands: &[Vec<Cand>],
        band: &Band,
        used: &mut [bool],
        used_mask: &mut u64,
        south: &mut [Vec<u8>],
        north0: &mut [u8],
        east: &mut [u8],
        raw: &mut u64,
        nodes: &mut u64,
        capped: &mut bool,
        node_cap: u64,
        leaf: &mut impl FnMut(u64, u128, u32),
    ) {
        if *capped {
            return;
        }
        if d == cells.len() {
            *raw += 1;
            let iface = if iface_top {
                pack_vec(&south[band.k - 1])
            } else {
                pack_vec(north0)
            };
            leaf(*used_mask, iface, spent);
            return;
        }
        let (r, c) = cells[d];
        let i = r - band.r0;
        let tn = if i == 0 {
            if charge_first {
                band.frontier.as_ref().map_or(NONE_COLOR, |f| f[c])
            } else {
                NONE_COLOR
            }
        } else {
            south[i - 1][c]
        };
        let tw = if c == 0 { NONE_COLOR } else { east[d - band.k] };
        for cd in &cands[d] {
            if used[cd.pi as usize] {
                continue;
            }
            let mut cost = spent;
            if tn != NONE_COLOR {
                cost += u32::from(cd.n != tn);
            }
            if tw != NONE_COLOR {
                cost += u32::from(cd.w != tw);
            }
            if cost > budget {
                continue;
            }
            *nodes += 1;
            if *nodes >= node_cap {
                *capped = true;
                return;
            }
            used[cd.pi as usize] = true;
            *used_mask |= 1u64 << cd.pi;
            south[i][c] = cd.s;
            if i == 0 {
                north0[c] = cd.n;
            }
            east[d] = cd.e;
            rec(d + 1, cost, budget, charge_first, iface_top, cells, cands, band, used, used_mask, south, north0, east, raw, nodes, capped, node_cap, leaf);
            used[cd.pi as usize] = false;
            *used_mask &= !(1u64 << cd.pi);
        }
    }
    rec(0, 0, budget, charge_first_row_n, interface_top, &cells, &cands, band, &mut used, &mut used_mask, &mut south, &mut north0, &mut east, &mut raw, &mut nodes, &mut capped, node_cap, &mut leaf);
    (raw, nodes, capped)
}

/// Exact min-break of a 2h-row band via meet-in-the-middle: split
/// into two h-row bands, enumerate both at budget B, hash-join on
/// (complement pool mask, interface vector), iterative deepening on B
/// from an admissible lower bound. Exact when not capped.
#[must_use]
pub fn bandsaw(band: &Band, lb: u32, node_cap: u64) -> BandsawResult {
    assert!(band.k % 2 == 0, "bandsaw needs an even row count");
    let m = band.mini;
    let h = band.k / 2;
    let t0 = std::time::Instant::now();

    let full_mask: u64 = if band.pool.len() == 64 {
        u64::MAX
    } else {
        (1u64 << band.pool.len()) - 1
    };
    let split = |rows_lo: bool| -> Band {
        Band {
            mini: m,
            r0: if rows_lo { band.r0 } else { band.r0 + h },
            k: h,
            frontier: if rows_lo { band.frontier.clone() } else { None },
            pool: band.pool.clone(),
            forced: band.forced.clone(),
        }
    };
    let top_band = split(true);
    let bot_band = split(false);

    let mut budget = lb;
    loop {
        let mut top: HashMap<(u64, u128), u32> = HashMap::new();
        let (top_raw, _tn, tcap) = enumerate_band(&top_band, budget, true, true, node_cap, |mask, v, cost| {
            top.entry((mask, v))
                .and_modify(|e| *e = (*e).min(cost))
                .or_insert(cost);
        });
        let mut bottom: HashMap<u64, HashMap<u128, u32>> = HashMap::new();
        let mut bottom_keys = 0usize;
        let (bottom_raw, _bn, bcap) = enumerate_band(&bot_band, budget, false, false, node_cap, |mask, v, cost| {
            let g = bottom.entry(mask).or_default();
            let e = g.entry(v).or_insert(u32::MAX);
            if cost < *e {
                if *e == u32::MAX {
                    bottom_keys += 1;
                }
                *e = cost;
            }
        });
        let capped = tcap || bcap;

        let mut best: Option<u32> = None;
        let mut join_pairs = 0u64;
        for (&(mask, v), &ct) in &top {
            let comp = full_mask & !mask;
            if let Some(g) = bottom.get(&comp) {
                for (&u, &cb) in g {
                    join_pairs += 1;
                    let tot = ct + cb + vec_mismatch(v, u, m.n);
                    if best.is_none_or(|bv| tot < bv) {
                        best = Some(tot);
                    }
                }
            }
        }
        let done = best.is_some_and(|bv| bv <= budget);
        if done || capped || budget > 512 {
            return BandsawResult {
                best,
                final_budget: budget,
                top_raw,
                bottom_raw,
                top_keys: top.len(),
                bottom_keys,
                bottom_mask_groups: bottom.len(),
                join_pairs,
                elapsed_ms: t0.elapsed().as_millis(),
                capped,
            };
        }
        budget += 1;
    }
}

// ---------------- entry helpers ----------------

/// Build the endgame band (rows r0..n) for an entry whose rows 0..r0
/// are placed. Pool = all pieces not used by the entry; forced = hints
/// inside the band. frontier = souths of row r0-1.
#[must_use]
pub fn endgame_band<'a>(m: &'a Mini, placement: &[Option<(u16, u8)>], r0: usize) -> Band<'a> {
    let n = m.n;
    let mut used = vec![false; n * n];
    for pos in 0..r0 * n {
        let (p, _) = placement[pos].expect("entry rows must be complete");
        assert!(!used[p as usize], "dup piece in entry");
        used[p as usize] = true;
    }
    let pool: Vec<u16> = (0..n * n)
        .filter(|&p| !used[p])
        .map(|p| u16::try_from(p).unwrap())
        .collect();
    let frontier: Vec<u8> = (0..n)
        .map(|c| {
            let (p, rt) = placement[(r0 - 1) * n + c].unwrap();
            m.rot[p as usize][rt as usize][2]
        })
        .collect();
    let forced: HashMap<usize, (u16, u8)> = m
        .hints
        .iter()
        .filter(|&&(pos, _, _)| pos >= r0 * n)
        .map(|&(pos, p, rt)| (pos, (p, rt)))
        .collect();
    Band { mini: m, r0, k: n - r0, frontier: Some(frontier), pool, forced }
}

// ---------------- tests ----------------

#[cfg(test)]
mod tests {
    use super::*;

    /// Plain brute force: distinct-piece fillings by exact cost,
    /// row-major recursion with NO pruning tricks (independent of the
    /// column-major machinery under test).
    fn brute_exact(band: &Band, bmax: u32) -> Vec<u64> {
        let m = band.mini;
        let n = m.n;
        let mut avail0 = vec![false; n * n];
        for &p in &band.pool {
            avail0[p as usize] = true;
        }
        let mut by_b = vec![0u64; bmax as usize + 1];
        // row-major cells
        let cells: Vec<(usize, usize)> = (band.r0..band.r0 + band.k)
            .flat_map(|r| (0..n).map(move |c| (r, c)))
            .collect();
        fn rec(
            d: usize,
            spent: u32,
            cells: &[(usize, usize)],
            band: &Band,
            grid: &mut Vec<Option<(u16, u8)>>,
            avail: &mut [bool],
            by_b: &mut [u64],
            bmax: u32,
        ) {
            let m = band.mini;
            let n = m.n;
            if d == cells.len() {
                by_b[spent as usize] += 1;
                return;
            }
            let (r, c) = cells[d];
            let pos = r * n + c;
            let forced = band.forced.get(&pos).copied();
            let cands: Vec<(u16, u8)> = match forced {
                Some(f) => vec![f],
                None => m.cands_at(r, c, avail),
            };
            for (p, rt) in cands {
                if !avail[p as usize] {
                    continue;
                }
                let o = m.rot[p as usize][rt as usize];
                let mut cost = spent;
                if r == band.r0 {
                    if let Some(f) = &band.frontier {
                        if f[c] != NONE_COLOR {
                            cost += u32::from(o[0] != f[c]);
                        }
                    }
                } else {
                    let (p2, rt2) = grid[pos - n].unwrap();
                    cost += u32::from(m.rot[p2 as usize][rt2 as usize][2] != o[0]);
                }
                if c > 0 {
                    if let Some((p2, rt2)) = grid[pos - 1] {
                        cost += u32::from(m.rot[p2 as usize][rt2 as usize][1] != o[3]);
                    }
                }
                if cost > bmax {
                    continue;
                }
                avail[p as usize] = false;
                grid[pos] = Some((p, rt));
                rec(d + 1, cost, cells, band, grid, avail, by_b, bmax);
                grid[pos] = None;
                avail[p as usize] = true;
            }
        }
        let mut grid = vec![None; n * n];
        rec(0, 0, &cells, band, &mut grid, &mut avail0, &mut by_b, bmax);
        by_b
    }

    /// Brute force with repeats allowed (pieces never consumed).
    fn brute_relax(band: &Band, bmax: u32) -> Vec<u64> {
        let m = band.mini;
        let n = m.n;
        let mut avail = vec![true; n * n];
        for p in 0..n * n {
            avail[p] = band.pool.contains(&(u16::try_from(p).unwrap()));
        }
        let mut by_b = vec![0u64; bmax as usize + 1];
        let cells: Vec<(usize, usize)> = (band.r0..band.r0 + band.k)
            .flat_map(|r| (0..n).map(move |c| (r, c)))
            .collect();
        fn rec(
            d: usize,
            spent: u32,
            cells: &[(usize, usize)],
            band: &Band,
            grid: &mut Vec<Option<(u16, u8)>>,
            avail: &[bool],
            by_b: &mut [u64],
            bmax: u32,
        ) {
            let m = band.mini;
            let n = m.n;
            if d == cells.len() {
                by_b[spent as usize] += 1;
                return;
            }
            let (r, c) = cells[d];
            let pos = r * n + c;
            let cands: Vec<(u16, u8)> = match band.forced.get(&pos).copied() {
                Some(f) => vec![f],
                None => m.cands_at(r, c, avail),
            };
            for (p, rt) in cands {
                let o = m.rot[p as usize][rt as usize];
                let mut cost = spent;
                if r == band.r0 {
                    if let Some(f) = &band.frontier {
                        if f[c] != NONE_COLOR {
                            cost += u32::from(o[0] != f[c]);
                        }
                    }
                } else {
                    let (p2, rt2) = grid[pos - n].unwrap();
                    cost += u32::from(m.rot[p2 as usize][rt2 as usize][2] != o[0]);
                }
                if c > 0 {
                    if let Some((p2, rt2)) = grid[pos - 1] {
                        cost += u32::from(m.rot[p2 as usize][rt2 as usize][1] != o[3]);
                    }
                }
                if cost > bmax {
                    continue;
                }
                grid[pos] = Some((p, rt));
                rec(d + 1, cost, cells, band, grid, avail, by_b, bmax);
                grid[pos] = None;
            }
        }
        let mut grid = vec![None; n * n];
        rec(0, 0, &cells, band, &mut grid, &avail, &mut by_b, bmax);
        by_b
    }

    fn canonical_prefix(m: &Mini, r0: usize) -> Vec<Option<(u16, u8)>> {
        let n = m.n;
        let mut placement = vec![None; n * n];
        for pos in 0..r0 * n {
            placement[pos] = Some(m.solution[pos]);
        }
        placement
    }

    #[test]
    fn dbg_canonical_zero_breaks_5x5() {
        let m = Mini::from_seed(5, 4, 11, &[]);
        let n = m.n;
        let mut placement = vec![None; n * n];
        for pos in 0..n * n {
            placement[pos] = Some(m.solution[pos]);
        }
        assert_eq!(m.breaks_of(&placement), 0, "canonical must score 0");
        // canonical band filling must be admissible candidate-wise
        let prefix = canonical_prefix(&m, 3);
        let band = endgame_band(&m, &prefix, 3);
        let cands = band.cand_table();
        for (d, &(r, c)) in band.cells().iter().enumerate() {
            let pos = r * n + c;
            let (p, rt) = m.solution[pos];
            assert!(
                cands[d].iter().any(|cd| cd.pid == p && cd.rt == rt),
                "canonical ({p},{rt}) missing from cands at ({r},{c})"
            );
        }
        let counts = exact_count(&band, 0, u64::MAX);
        assert!(counts.by_b[0] >= 1, "canonical 0-break filling not counted");
    }

    #[test]
    fn m0_exact_count_matches_brute_force() {
        for seed in [11u64, 12, 13] {
            let m = Mini::from_seed(5, 4, seed, &[]);
            for r0 in [3usize, 2] {
                let placement = canonical_prefix(&m, r0);
                let band = endgame_band(&m, &placement, r0);
                let bmax = 3;
                let brute = brute_exact(&band, bmax);
                let fast = exact_count(&band, bmax, u64::MAX);
                assert!(!fast.capped);
                assert_eq!(brute, fast.by_b, "seed {seed} r0 {r0}");
            }
        }
    }

    #[test]
    fn m0_relax_profile_matches_brute_force() {
        for seed in [11u64, 12, 13] {
            let m = Mini::from_seed(4, 3, seed, &[]);
            for r0 in [2usize] {
                let placement = canonical_prefix(&m, r0);
                let band = endgame_band(&m, &placement, r0);
                let bmax = 3;
                let brute = brute_relax(&band, bmax);
                let fast = relax_profile(&band, bmax);
                for bb in 0..=bmax as usize {
                    let bf = brute[bb] as f64;
                    assert!(
                        (fast[bb] - bf).abs() <= 1e-6 * bf.max(1.0),
                        "seed {seed} r0 {r0} b {bb}: relax {} vs brute {}",
                        fast[bb],
                        brute[bb]
                    );
                }
            }
        }
    }

    #[test]
    fn m0_bb_and_bandsaw_match_brute_min() {
        for seed in [11u64, 12, 13, 14] {
            let m = Mini::from_seed(5, 4, seed, &[]);
            let r0 = 3usize; // last 2 rows -> bandsaw splits 1+1
            let placement = canonical_prefix(&m, r0);
            let band = endgame_band(&m, &placement, r0);
            // brute min over generous bmax
            let brute = brute_exact(&band, 12);
            let bstar = brute
                .iter()
                .position(|&x| x > 0)
                .expect("some filling must exist") as u32;
            let bb = bb_min_break(&band, 16, u64::MAX, u64::MAX);
            assert!(!bb.capped);
            assert_eq!(bb.best, Some(bstar), "bb seed {seed}");
            let lb = relax_floor(&band, 4);
            assert!(lb <= bstar, "relax floor must lower-bound: seed {seed}");
            let saw = bandsaw(&band, lb, u64::MAX);
            assert!(!saw.capped);
            assert_eq!(saw.best, Some(bstar), "bandsaw seed {seed}");
        }
    }

    // 10×10 M0 checks: run in release (`cargo test -p
    // eternity2-bench-audit --release -- --ignored`); too slow in the
    // default debug suite.
    #[test]
    #[ignore]
    fn m0_canonical_solution_scores_zero() {
        let m = Mini::from_seed(10, 8, 101, &hint_cells(10));
        let n = m.n;
        let mut placement = vec![None; n * n];
        for pos in 0..n * n {
            placement[pos] = Some(m.solution[pos]);
        }
        assert_eq!(m.breaks_of(&placement), 0);
        // hints really are the canonical placements
        for &(pos, p, rt) in &m.hints {
            assert_eq!(m.solution[pos], (p, rt));
        }
        // endgame from the canonical prefix must complete at 0
        let prefix = canonical_prefix(&m, 6);
        let band = endgame_band(&m, &prefix, 6);
        let lb = relax_floor(&band, 4);
        assert_eq!(lb, 0);
        let saw = bandsaw(&band, lb, u64::MAX);
        assert!(!saw.capped);
        assert_eq!(saw.best, Some(0));
    }

    #[test]
    #[ignore]
    fn m0_bandsaw_matches_bb_on_canonical_10x10_perturbed() {
        // canonical prefix with 1-2 frontier columns corrupted:
        // nonzero min-break territory where exhaustive bb is still
        // tractable (a fully alien frontier puts b* high enough that
        // budget-bounded exhaustion explodes — measured 600 s+).
        for (seed, ncorrupt) in [(102u64, 1usize), (103, 2)] {
            let m = Mini::from_seed(10, 8, seed, &hint_cells(10));
            let prefix = canonical_prefix(&m, 6);
            let mut band = endgame_band(&m, &prefix, 6);
            let mut f = band.frontier.clone().unwrap();
            for j in 0..ncorrupt {
                let col = 3 + 3 * j;
                f[col] = if f[col] == 1 { 2 } else { 1 };
            }
            band.frontier = Some(f);
            let lb = relax_floor(&band, 8);
            let bb = bb_min_break(&band, 64, 600_000, u64::MAX);
            assert!(!bb.capped, "bb must exhaust (seed {seed})");
            let saw = bandsaw(&band, lb, u64::MAX);
            assert!(!saw.capped);
            assert_eq!(saw.best, bb.best, "seed {seed} corrupt {ncorrupt}");
        }
    }
}
