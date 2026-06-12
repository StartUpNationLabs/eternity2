// Vol-217: full-board frame-free N-row band break-profile oracle.
// Rust port of scripts/v217_crossing/fb_oracle.py — the Python file is
// the reference spec; this port must match its counts EXACTLY (see
// --selftest and the cross-validation in vault/sessions/vol-217.md).
//
// Given a board state with rows 0..r0-1 complete, computes the
// break-cost profile (number of band fillings paying exactly b breaks,
// b <= bmax) of rows r0..r0+k-1 over all 16 columns, frame-free:
// flank/bottom candidates come from the REMAINING border pieces with
// border sides structural; clue hints pinned; placed band cells
// forced; S of the bottom band row free (or structural at row 15);
// repeats-allowed relaxation (declared; vol-217 A/B: benign).
//
//   fb_oracle --rows 11 --k 3 --truncate-rows 11 BOARD.json...
//   fb_oracle --batch LIST.tsv --rows 8 --k 3 --truncate-rows 8 --out OUT.tsv
//   fb_oracle --selftest

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::io::Write;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use rayon::prelude::*;

const NC: usize = 23;
const GAMMA: f64 = 0.3;

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    let mut out = [0u8; 4];
    for i in 0..4 {
        out[i] = e[(i + 4 - r as usize) % 4];
    }
    out
}

struct Ctx {
    rot: Vec<[[u8; 4]; 4]>,           // pid -> rot -> [N,E,S,W]
    kind: Vec<u8>,                    // 0 corner, 1 edge, 2 interior
    hints: Vec<(usize, u16, u8)>,     // (pos, pid, rot)
}

fn build_ctx(puzzle_path: &PathBuf) -> Ctx {
    let (puzzle, hints) = load_puzzle_with_hints(puzzle_path).expect("load puzzle");
    let mut rot = Vec::with_capacity(256);
    let mut kind = Vec::with_capacity(256);
    for p in puzzle.pieces() {
        let e = [p.edges.top(), p.edges.right(), p.edges.bottom(), p.edges.left()];
        let mut rr = [[0u8; 4]; 4];
        for r in 0..4 {
            rr[r] = rotate_edges(e, r as u8);
        }
        rot.push(rr);
        let z = e.iter().filter(|&&c| c == 0).count();
        kind.push(match z {
            2 => 0,
            1 => 1,
            _ => 2,
        });
    }
    let hv = hints
        .hints
        .iter()
        .map(|h| (h.position as usize, h.piece_id, h.rotation.as_u8()))
        .collect();
    Ctx { rot, kind, hints: hv }
}

// ---------------- tensor ----------------

struct Tensor {
    dims: Vec<usize>,
    strides: Vec<usize>,
    data: Vec<f64>,
}

impl Tensor {
    fn zeros(dims: Vec<usize>) -> Self {
        let mut strides = vec![0usize; dims.len()];
        let mut acc = 1usize;
        for i in (0..dims.len()).rev() {
            strides[i] = acc;
            acc *= dims[i];
        }
        Tensor { dims: dims.clone(), strides, data: vec![0.0; acc] }
    }

    /// Sum over one axis, returning a dense tensor without it.
    /// Row-major contiguous: layout is [outer][n][inner].
    fn sum_axis(&self, ax: usize) -> Tensor {
        let mut nd: Vec<usize> = self.dims.clone();
        nd.remove(ax);
        let mut out = Tensor::zeros(nd);
        let n = self.dims[ax];
        let outer: usize = self.dims[..ax].iter().product();
        let inner: usize = self.dims[ax + 1..].iter().product();
        for o in 0..outer {
            let ibase = o * n * inner;
            let obase = o * inner;
            for j in 0..n {
                let jb = ibase + j * inner;
                for q in 0..inner {
                    out.data[obase + q] += self.data[jb + q];
                }
            }
        }
        out
    }
}

#[inline]
fn shift_add(dst: &mut [f64], src: &[f64], c: usize, bmax: usize) {
    let b = bmax + 1;
    if c == 0 {
        for i in 0..b {
            dst[i] += src[i];
        }
    } else if c <= bmax {
        for i in c..b {
            dst[i] += src[i - c];
        }
    }
}

// candidate group key: (cost, n?, w?, e, s?) with Option encoded as 255
type GKey = (u8, u8, u8, u8, u8);
const NONE: u8 = 255;

fn cell_cands(ctx: &Ctx, r: usize, c: usize, pools: &[Vec<u16>; 3]) -> Vec<(u16, u8)> {
    let mut out = Vec::new();
    if r == 15 && (c == 0 || c == 15) {
        let want = if c == 0 { (2usize, 3usize) } else { (2usize, 1usize) };
        for &p in &pools[0] {
            for rt in 0..4u8 {
                let o = ctx.rot[p as usize][rt as usize];
                if o[want.0] == 0 && o[want.1] == 0 {
                    out.push((p, rt));
                }
            }
        }
    } else if r == 15 || c == 0 || c == 15 {
        let side = if r == 15 { 2 } else if c == 0 { 3 } else { 1 };
        for &p in &pools[1] {
            for rt in 0..4u8 {
                if ctx.rot[p as usize][rt as usize][side] == 0 {
                    out.push((p, rt));
                }
            }
        }
    } else {
        for &p in &pools[2] {
            for rt in 0..4u8 {
                out.push((p, rt));
            }
        }
    }
    out
}

#[allow(clippy::too_many_arguments)]
fn band_profile(
    ctx: &Ctx,
    rows: &[usize],
    t_n: &[u8; 16],
    forced: &HashMap<(usize, usize), (u16, u8)>,
    pools: &[Vec<u16>; 3],
    bmax: usize,
    ncols: usize,
) -> (Vec<f64>, f64) {
    let k = rows.len();
    let b = bmax + 1;
    let mut t: Option<Tensor> = None;
    let mut logscale = 0.0f64;

    for c in 0..ncols {
        let first_col = c == 0;
        for (i, &r) in rows.iter().enumerate() {
            let last_row = i == k - 1;
            let cands: Vec<(u16, u8)> = match forced.get(&(r, c)) {
                Some(&f) => vec![f],
                None => cell_cands(ctx, r, c, pools),
            };
            assert!(!cands.is_empty(), "no candidates at ({r},{c})");
            let mut groups: HashMap<GKey, f64> = HashMap::new();
            for (p, rt) in cands {
                let o = ctx.rot[p as usize][rt as usize];
                let mut cb = 0u8;
                let kn;
                if i == 0 {
                    cb += u8::from(o[0] != t_n[c]);
                    kn = NONE;
                } else {
                    kn = o[0];
                }
                let kw = if first_col { NONE } else { o[3] };
                let ks = if last_row { NONE } else { o[2] };
                *groups.entry((cb, kn, kw, o[1], ks)).or_insert(0.0) += 1.0;
            }

            let mut odims: Vec<usize> = Vec::new();
            if !last_row {
                odims.push(NC);
            }
            odims.extend(std::iter::repeat(NC).take(k));
            odims.push(b);
            let mut out = Tensor::zeros(odims);
            // output coordinate layout: [s?] e_0..e_{k-1} b
            // we always accumulate into slices with s (opt), e_i set and
            // the OTHER e-axes + b iterated in lockstep with the input.
            let o_s_stride = if last_row { 0 } else { out.strides[0] };
            let o_e_stride = out.strides[if last_row { i } else { 1 + i }];
            // "rest" axes of the output: all e_j (j != i), then b — same
            // relative order as in the input tensors below.
            let mut o_rest: Vec<(usize, usize)> = Vec::new(); // (dim, stride)
            for j in 0..k {
                if j != i {
                    o_rest.push((NC, out.strides[if last_row { j } else { 1 + j }]));
                }
            }
            let ob_stride = *out.strides.last().unwrap();

            match &t {
                None => {
                    // very first cell: park unbuilt e-axes at 0
                    for (&(cb, _kn, _kw, e, s), &m) in &groups {
                        if cb as usize <= bmax {
                            let mut off = e as usize * o_e_stride;
                            if !last_row {
                                off += s as usize * o_s_stride;
                            }
                            out.data[off + cb as usize * ob_stride] += m;
                        }
                    }
                }
                Some(tin) => {
                    let s_in = tin.dims.len() == k + 2;
                    let ei_ax = usize::from(s_in) + i;
                    // per-q output offsets (excl. s/e contributions), once per step
                    let rest_total: usize = o_rest.iter().map(|&(d, _)| d).product();
                    let mut offs_out = vec![0usize; rest_total];
                    for (q, o) in offs_out.iter_mut().enumerate() {
                        *o = mixed_offset(q, &o_rest);
                    }
                    if first_col {
                        // i>0 here; contract n via s-axis, sum out dummy e_i
                        let ts = tin.sum_axis(ei_ax); // (s, rest..., b)
                        let sum_s = ts.sum_axis(0); // (rest..., b)
                        for (&(cb, kn, _kw, e, s), &m) in &groups {
                            let am_base = kn as usize * ts.strides[0];
                            let so = if last_row { 0 } else { s as usize * o_s_stride };
                            let eo = e as usize * o_e_stride + so;
                            let (c0, c1) = (cb as usize, cb as usize + 1);
                            for q in 0..rest_total {
                                let iin = q * b;
                                let oo = eo + offs_out[q];
                                let am = &ts.data[am_base + iin..am_base + iin + b];
                                let tot = &sum_s.data[iin..iin + b];
                                let dst = &mut out.data[oo..oo + b];
                                fused2(dst, am, tot, m, c0, c1, bmax);
                            }
                        }
                    } else if s_in {
                        // contract n (axis 0) and w (axis ei_ax)
                        let sum_s = tin.sum_axis(0);
                        let sum_e = tin.sum_axis(ei_ax);
                        let sum_se = sum_e.sum_axis(0);
                        let tin_n_s = tin.strides[0];
                        let tin_w_s = tin.strides[ei_ax];
                        let ss_w_s = sum_s.strides[ei_ax - 1];
                        let se_n_s = sum_e.strides[0];
                        let tin_rest = rest_strides(&tin.dims, &tin.strides, &[0, ei_ax]);
                        let ss_rest = rest_strides(&sum_s.dims, &sum_s.strides, &[ei_ax - 1]);
                        let se_rest = rest_strides(&sum_e.dims, &sum_e.strides, &[0]);
                        let mut offs_tin = vec![0usize; rest_total];
                        let mut offs_ss = vec![0usize; rest_total];
                        let mut offs_se = vec![0usize; rest_total];
                        for q in 0..rest_total {
                            offs_tin[q] = mixed_offset(q, &tin_rest);
                            offs_ss[q] = mixed_offset(q, &ss_rest);
                            offs_se[q] = mixed_offset(q, &se_rest);
                        }
                        for (&(cb, kn, kw, e, s), &m) in &groups {
                            let nb = kn as usize * tin_n_s + kw as usize * tin_w_s;
                            let wb = kw as usize * ss_w_s;
                            let eb = kn as usize * se_n_s;
                            let so = if last_row { 0 } else { s as usize * o_s_stride };
                            let eo = e as usize * o_e_stride + so;
                            let (c0, c1, c2) =
                                (cb as usize, cb as usize + 1, cb as usize + 2);
                            for q in 0..rest_total {
                                let off_tin = nb + offs_tin[q];
                                let off_ss = wb + offs_ss[q];
                                let off_se = eb + offs_se[q];
                                let off_sse = q * b;
                                let oo = eo + offs_out[q];
                                let amm = &tin.data[off_tin..off_tin + b];
                                let row_s = &sum_s.data[off_ss..off_ss + b];
                                let row_e = &sum_e.data[off_se..off_se + b];
                                let tot = &sum_se.data[off_sse..off_sse + b];
                                let dst = &mut out.data[oo..oo + b];
                                fused3(dst, amm, row_s, row_e, tot, m, c0, c1, c2, bmax);
                            }
                        }
                    } else {
                        // i==0, c>0: contract w only (axis 0)
                        let sum_e = tin.sum_axis(0);
                        let tin_w_s = tin.strides[0];
                        for (&(cb, _kn, kw, e, s), &m) in &groups {
                            let am_base = kw as usize * tin_w_s;
                            let so = if last_row { 0 } else { s as usize * o_s_stride };
                            let eo = e as usize * o_e_stride + so;
                            let (c0, c1) = (cb as usize, cb as usize + 1);
                            for q in 0..rest_total {
                                let iin = q * b;
                                let oo = eo + offs_out[q];
                                let am = &tin.data[am_base + iin..am_base + iin + b];
                                let tot = &sum_e.data[iin..iin + b];
                                let dst = &mut out.data[oo..oo + b];
                                fused2(dst, am, tot, m, c0, c1, bmax);
                            }
                        }
                    }
                }
            }
            t = Some(out);
        }
        let tt = t.as_mut().unwrap();
        let mx = tt.data.iter().cloned().fold(0.0f64, f64::max);
        if mx > 1e250 {
            for v in tt.data.iter_mut() {
                *v /= mx;
            }
            logscale += mx.log10();
        }
        assert_eq!(tt.dims.len(), k + 1, "s axis must be consumed at column end");
    }

    let tt = t.unwrap();
    let mut counts = vec![0.0f64; b];
    for (idx, &v) in tt.data.iter().enumerate() {
        counts[idx % b] += v;
    }
    (counts, logscale)
}

/// rest axes = all axes except `skip` and the last (b). Returns (dim, stride) list.
fn rest_strides(dims: &[usize], strides: &[usize], skip: &[usize]) -> Vec<(usize, usize)> {
    let mut out = Vec::new();
    for ax in 0..dims.len() - 1 {
        if !skip.contains(&ax) {
            out.push((dims[ax], strides[ax]));
        }
    }
    out
}

/// Decompose flat rest-index q (mixed radix over the rest dims, B-major
/// excluded) into an offset using the given (dim, stride) list.
#[inline]
fn mixed_offset(mut q: usize, rest: &[(usize, usize)]) -> usize {
    let mut off = 0usize;
    for &(d, s) in rest.iter().rev() {
        off += (q % d) * s;
        q /= d;
    }
    off
}

/// dst[x+c0] += m*match[x]; dst[x+c1] += m*(tot[x]-match[x])
#[inline]
fn fused2(dst: &mut [f64], am: &[f64], tot: &[f64], m: f64, c0: usize, c1: usize, bmax: usize) {
    let b = bmax + 1;
    if c0 <= bmax {
        for x in 0..b - c0 {
            dst[x + c0] += m * am[x];
        }
    }
    if c1 <= bmax {
        for x in 0..b - c1 {
            dst[x + c1] += m * (tot[x] - am[x]);
        }
    }
}

/// 4-branch inclusion-exclusion in one pass:
/// dst[x+c0] += m*amm; dst[x+c1] += m*(row_s+row_e-2amm);
/// dst[x+c2] += m*(tot-row_s-row_e+amm)
#[allow(clippy::too_many_arguments)]
#[inline]
fn fused3(
    dst: &mut [f64],
    amm: &[f64],
    row_s: &[f64],
    row_e: &[f64],
    tot: &[f64],
    m: f64,
    c0: usize,
    c1: usize,
    c2: usize,
    bmax: usize,
) {
    let b = bmax + 1;
    if c0 <= bmax {
        for x in 0..b - c0 {
            dst[x + c0] += m * amm[x];
        }
    }
    if c1 <= bmax {
        for x in 0..b - c1 {
            dst[x + c1] += m * (row_s[x] + row_e[x] - 2.0 * amm[x]);
        }
    }
    if c2 <= bmax {
        for x in 0..b - c2 {
            dst[x + c2] += m * (tot[x] - row_s[x] - row_e[x] + amm[x]);
        }
    }
}

// ---------------- board loading / ask ----------------

fn load_board(
    paths: &[PathBuf],
    truncate_rows: Option<usize>,
    frame: Option<&PathBuf>,
) -> HashMap<(usize, usize), (u16, u8)> {
    let mut placed: HashMap<(usize, usize), (u16, u8)> = HashMap::new();
    let mut put = |r: usize, c: usize, cur: (u16, u8), placed: &mut HashMap<_, _>| {
        if let Some(tr) = truncate_rows {
            if r >= tr {
                return;
            }
        }
        let prev = placed.insert((r, c), cur);
        assert!(prev.is_none() || prev == Some(cur), "conflict at ({r},{c})");
    };
    for path in paths {
        let v: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(path).expect("read board"))
                .expect("parse board");
        for (i, e) in v["placement"].as_array().expect("placement").iter().enumerate() {
            if e.is_null() {
                continue;
            }
            let pos = e.get("pos").and_then(|p| p.as_u64()).unwrap_or(i as u64) as usize;
            put(
                pos / 16,
                pos % 16,
                (
                    e["piece_id"].as_u64().unwrap() as u16,
                    e["rotation"].as_u64().unwrap() as u8,
                ),
                &mut placed,
            );
        }
    }
    if let Some(fp) = frame {
        let v: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(fp).expect("read frame"))
                .expect("parse frame");
        for (i, e) in v["placement"].as_array().expect("placement").iter().enumerate() {
            if e.is_null() {
                continue;
            }
            let pos = e.get("pos").and_then(|p| p.as_u64()).unwrap_or(i as u64) as usize;
            let (r, c) = (pos / 16, pos % 16);
            if r == 0 || r == 15 || c == 0 || c == 15 {
                put(
                    r,
                    c,
                    (
                        e["piece_id"].as_u64().unwrap() as u16,
                        e["rotation"].as_u64().unwrap() as u8,
                    ),
                    &mut placed,
                );
            }
        }
    }
    placed
}

struct AskResult {
    soft: f64,
    bmin: i32,
    log_at_bmin: f64,
    pools: [usize; 3],
}

fn ask(
    ctx: &Ctx,
    placed: &HashMap<(usize, usize), (u16, u8)>,
    rows: &[usize],
    bmax: usize,
) -> AskResult {
    let r0 = rows[0];
    let mut t_n = [0u8; 16];
    for c in 0..16 {
        let &(p, rt) = placed
            .get(&(r0 - 1, c))
            .unwrap_or_else(|| panic!("row {} incomplete at col {c}", r0 - 1));
        t_n[c] = ctx.rot[p as usize][rt as usize][2];
    }
    let mut used = vec![false; 256];
    for &(p, _) in placed.values() {
        assert!(!used[p as usize], "duplicate piece {p}");
        used[p as usize] = true;
    }
    let mut forced: HashMap<(usize, usize), (u16, u8)> = HashMap::new();
    for (&(r, c), &pr) in placed {
        if rows.contains(&r) {
            forced.insert((r, c), pr);
        }
    }
    for &(pos, pid, rot) in &ctx.hints {
        let (r, c) = (pos / 16, pos % 16);
        if placed.contains_key(&(r, c)) {
            continue;
        }
        used[pid as usize] = true; // reserve
        if rows.contains(&r) {
            forced.insert((r, c), (pid, rot));
        }
    }
    let mut pools: [Vec<u16>; 3] = [Vec::new(), Vec::new(), Vec::new()];
    for p in 0..256u16 {
        if !used[p as usize] {
            pools[ctx.kind[p as usize] as usize].push(p);
        }
    }
    let (counts, logscale) = band_profile(ctx, rows, &t_n, &forced, &pools, bmax, 16);
    let b = bmax + 1;
    let mut logs = vec![f64::NEG_INFINITY; b];
    for i in 0..b {
        if counts[i] > 0.0 {
            logs[i] = counts[i].log10() + logscale;
        }
    }
    let lg = GAMMA.log10();
    let w: Vec<f64> = logs.iter().enumerate().map(|(i, &l)| l + i as f64 * lg).collect();
    let wmax = w.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let soft = if wmax.is_finite() {
        wmax + w.iter().map(|&x| 10f64.powf(x - wmax)).sum::<f64>().log10()
    } else {
        f64::NEG_INFINITY
    };
    let bmin = counts.iter().position(|&x| x > 0.0).map(|i| i as i32).unwrap_or(-1);
    let log_at_bmin = if bmin >= 0 { logs[bmin as usize] } else { f64::NEG_INFINITY };
    AskResult {
        soft,
        bmin,
        log_at_bmin,
        pools: [pools[2].len(), pools[1].len(), pools[0].len()],
    }
}

// ---------------- selftest (mirror of the Python selftest) ----------------

fn selftest(puzzle: &PathBuf) -> i32 {
    let ctx = build_ctx(puzzle);
    let edges: Vec<u16> = (0..256u16).filter(|&p| ctx.kind[p as usize] == 1).take(3).collect();
    let inter: Vec<u16> = (0..256u16).filter(|&p| ctx.kind[p as usize] == 2).take(3).collect();
    let pools: [Vec<u16>; 3] = [vec![], edges.clone(), inter.clone()];
    let mut forced = HashMap::new();
    forced.insert((13usize, 1usize), (inter[0], 2u8));
    let mut t_n = [1u8; 16];
    t_n[0] = 4;
    t_n[1] = 7;
    let bmax = 14;
    let rows = [12usize, 13, 14];
    let (counts, lsc) = band_profile(&ctx, &rows, &t_n, &forced, &pools, bmax, 2);
    let dp: Vec<f64> = counts.iter().map(|&x| x * 10f64.powf(lsc)).collect();

    // brute force
    let oe = |pr: (u16, u8)| ctx.rot[pr.0 as usize][pr.1 as usize];
    let c0: Vec<Vec<(u16, u8)>> = rows
        .iter()
        .map(|&r| cell_cands(&ctx, r, 0, &pools))
        .collect();
    let c1: Vec<Vec<(u16, u8)>> = vec![
        inter.iter().flat_map(|&p| (0..4u8).map(move |rt| (p, rt))).collect(),
        vec![forced[&(13, 1)]],
        inter.iter().flat_map(|&p| (0..4u8).map(move |rt| (p, rt))).collect(),
    ];
    let mut bf = vec![0.0f64; bmax + 1];
    for &a in &c0[0] {
        for &b_ in &c0[1] {
            for &cc in &c0[2] {
                let (aa, bb, ccc) = (oe(a), oe(b_), oe(cc));
                let base = u32::from(aa[0] != t_n[0])
                    + u32::from(aa[2] != bb[0])
                    + u32::from(bb[2] != ccc[0]);
                for &d in &c1[0] {
                    let dd = oe(d);
                    let cd = base + u32::from(dd[0] != t_n[1]) + u32::from(aa[1] != dd[3]);
                    for &e in &c1[1] {
                        let ee = oe(e);
                        let ce = cd + u32::from(dd[2] != ee[0]) + u32::from(bb[1] != ee[3]);
                        for &f in &c1[2] {
                            let ff = oe(f);
                            let cf = (ce
                                + u32::from(ee[2] != ff[0])
                                + u32::from(ccc[1] != ff[3])) as usize;
                            if cf <= bmax {
                                bf[cf] += 1.0;
                            }
                        }
                    }
                }
            }
        }
    }
    let ok = dp
        .iter()
        .zip(bf.iter())
        .all(|(&x, &y)| (x - y).abs() <= 1e-6 * y.max(1.0));
    println!("selftest {}", if ok { "PASS" } else { "FAIL" });
    println!("dp: {:?}", dp.iter().map(|&x| x.round() as i64).collect::<Vec<_>>());
    println!("bf: {:?}", bf.iter().map(|&x| x.round() as i64).collect::<Vec<_>>());
    i32::from(!ok)
}

// ---------------- main ----------------

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut puzzle = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut rows0: usize = 11;
    let mut k: usize = 3;
    let mut truncate: Option<usize> = None;
    let mut bmax: usize = 14;
    let mut frame: Option<PathBuf> = None;
    let mut batch: Option<PathBuf> = None;
    let mut out_path: Option<PathBuf> = None;
    let mut threads: usize = 1;
    let mut want_selftest = false;
    let mut boards: Vec<PathBuf> = Vec::new();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--puzzle" => { puzzle = PathBuf::from(&raw[i + 1]); i += 2; }
            "--rows" => { rows0 = raw[i + 1].parse().unwrap(); i += 2; }
            "--k" => { k = raw[i + 1].parse().unwrap(); i += 2; }
            "--truncate-rows" => { truncate = Some(raw[i + 1].parse().unwrap()); i += 2; }
            "--bmax" => { bmax = raw[i + 1].parse().unwrap(); i += 2; }
            "--frame" => { frame = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--batch" => { batch = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--out" => { out_path = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--threads" => { threads = raw[i + 1].parse().unwrap(); i += 2; }
            "--selftest" => { want_selftest = true; i += 1; }
            other => { boards.push(PathBuf::from(other)); i += 1; }
        }
    }
    if want_selftest {
        std::process::exit(selftest(&puzzle));
    }
    let ctx = build_ctx(&puzzle);
    let rows: Vec<usize> = (rows0..rows0 + k).collect();

    let inputs: Vec<PathBuf> = if let Some(bp) = &batch {
        std::fs::read_to_string(bp)
            .expect("batch list")
            .lines()
            .filter(|l| !l.trim().is_empty())
            .map(PathBuf::from)
            .collect()
    } else {
        boards.clone()
    };

    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .ok();

    let results: Vec<String> = inputs
        .par_iter()
        .map(|bpath| {
            let t0 = Instant::now();
            let placed = load_board(
                std::slice::from_ref(bpath),
                truncate,
                frame.as_ref(),
            );
            let r = ask(&ctx, &placed, &rows, bmax);
            let ms = t0.elapsed().as_millis();
            let tag = bpath.file_stem().unwrap().to_string_lossy().to_string();
            format!(
                "{tag}\t{}..{}\t{:.4}\t{}\t{:.3}\t{}/{}/{}\t{ms}",
                rows[0],
                rows[k - 1],
                r.soft,
                r.bmin,
                r.log_at_bmin,
                r.pools[0],
                r.pools[1],
                r.pools[2]
            )
        })
        .collect();

    let header = "tag\trows\tsoft_g03\tbmin\tlog_at_bmin\tpool_i/e/c\tms";
    match out_path {
        Some(p) => {
            let mut f = std::fs::File::create(p).expect("out");
            writeln!(f, "{header}").unwrap();
            for line in results {
                writeln!(f, "{line}").unwrap();
            }
        }
        None => {
            println!("{header}");
            for line in results {
                println!("{line}");
            }
        }
    }
}
