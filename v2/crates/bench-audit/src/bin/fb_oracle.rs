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
    bc: Option<(i32, f64)>,
}

fn ask(
    ctx: &Ctx,
    placed: &HashMap<(usize, usize), (u16, u8)>,
    rows: &[usize],
    bmax: usize,
    want_bc: bool,
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
    let bc = if want_bc { Some(bottom_chain(ctx, &pools, bmax)) } else { None };
    AskResult {
        soft,
        bmin,
        log_at_bmin,
        pools: [pools[2].len(), pools[1].len(), pools[0].len()],
        bc,
    }
}

/// Tropical fast path: floor only (k=3 bands), capped. Returns -1 if
/// no filling within cap.
fn ask_floor(
    ctx: &Ctx,
    placed: &HashMap<(usize, usize), (u16, u8)>,
    rows: &[usize],
    cap: i32,
) -> i32 {
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
        used[pid as usize] = true;
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
    let f = band_floor_k3(ctx, rows, &t_n, &forced, &pools, cap, 16);
    if f >= INF { -1 } else { f }
}

// ---------------- tropical (min-plus) floor-only DP ----------------
// H6: the filter rung. State value = min breaks over fillings reaching
// that boundary profile. ~10-15x less state than counting (no b axis),
// integer ops. Exclusion ("best over w != w0") cannot use linearity;
// we keep per-row minima with arg + runner-up.
//
// Layout: between columns V[e0][e1][e2] (i32, INF=i32::MAX/4);
// mid-column with leading s axis. k=3 fixed (the only band size used
// for filtering); counting mode remains fully general.

const INF: i32 = i32::MAX / 4;

#[allow(clippy::too_many_arguments)]
fn band_floor_k3(
    ctx: &Ctx,
    rows: &[usize],
    t_n: &[u8; 16],
    forced: &HashMap<(usize, usize), (u16, u8)>,
    pools: &[Vec<u16>; 3],
    cap: i32,
    ncols: usize,
) -> i32 {
    assert_eq!(rows.len(), 3);
    let nc = NC;
    let sz3 = nc * nc * nc;
    let sz4 = nc * sz3;
    let mut v: Vec<i32> = Vec::new(); // between-column (sz3) or mid (sz4)
    let mut has_s = false;
    let mut started = false;

    for c in 0..ncols {
        let first_col = c == 0;
        for (i, &r) in rows.iter().enumerate() {
            let last_row = i == 2;
            let cands: Vec<(u16, u8)> = match forced.get(&(r, c)) {
                Some(&f) => vec![f],
                None => cell_cands(ctx, r, c, pools),
            };
            // group candidates: key (cb, n?, w?, e, s?)
            let mut groups: HashMap<GKey, ()> = HashMap::new();
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
                groups.entry((cb, kn, kw, o[1], ks)).or_insert(());
            }
            let osz = if last_row { sz3 } else { sz4 };
            let mut out = vec![INF; osz];
            // index helpers: state (e0,e1,e2) -> ((e0*nc)+e1)*nc+e2;
            // mid state (s,e0,e1,e2) -> s*sz3 + that.
            if !started {
                for (&(cb, _kn, _kw, e, s), _) in &groups {
                    let idx = (s as usize) * sz3 + (e as usize) * nc * nc;
                    let val = cb as i32;
                    if val < out[idx] {
                        out[idx] = val;
                    }
                }
                started = true;
            } else if first_col {
                // i>0: contract n via s axis; e_i axis is dummy (sum out
                // == min out). v is mid (sz4) with s leading.
                // reduce dummy e_i: positions of e_i in state: axis i.
                // build red[s][rest] = min over e_i of v
                let (red, rest_n) = trop_reduce_axis(&v, true, i, nc);
                // per rest position: min over s + arg + second
                let mut m1 = vec![INF; rest_n];
                let mut a1 = vec![255u8; rest_n];
                let mut m2 = vec![INF; rest_n];
                for s in 0..nc {
                    for q in 0..rest_n {
                        let val = red[s * rest_n + q];
                        if val < m1[q] {
                            m2[q] = m1[q];
                            m1[q] = val;
                            a1[q] = s as u8;
                        } else if val < m2[q] {
                            m2[q] = val;
                        }
                    }
                }
                for (&(cb, kn, _kw, e, s), _) in &groups {
                    for q in 0..rest_n {
                        let vm = red[kn as usize * rest_n + q]; // n matches s_top
                        let vx = if a1[q] == kn { m2[q] } else { m1[q] };
                        let best = (vm + cb as i32).min(vx + cb as i32 + 1);
                        if best > cap {
                            continue;
                        }
                        // write into out at (s, e at axis i, rest q)
                        let idx = trop_out_idx(s, e, i, q, last_row, nc);
                        if best < out[idx] {
                            out[idx] = best;
                        }
                    }
                }
            } else {
                let s_in = has_s;
                if s_in {
                    // contract s (n) and e_i (w) jointly with exclusion
                    // rest axes: the two e_j (j != i); rest_n = nc*nc
                    let rest_n = nc * nc;
                    // gather: g[s][w][rest] = v at (s, e_i=w, rest)
                    // then per rest: row minima over w per s, and over s.
                    let mut best =
                        |kn: u8, kw: u8, q: usize, tabs: &TropTabs| -> i32 {
                            let n0 = kn as usize;
                            let w0 = kw as usize;
                            let mm = tabs.val[(n0 * nc + w0) * rest_n + q];
                            let mx = {
                                let base = n0 * rest_n + q;
                                if tabs.row_a1[base] == kw {
                                    tabs.row_m2[base]
                                } else {
                                    tabs.row_m1[base]
                                }
                            };
                            let xm = {
                                let base = w0 * rest_n + q;
                                if tabs.col_a1[base] == kn {
                                    tabs.col_m2[base]
                                } else {
                                    tabs.col_m1[base]
                                }
                            };
                            let xb = q * nc + w0;
                            let xx = if tabs.xq_a1[xb] == kn {
                                tabs.xq_m2[xb]
                            } else {
                                tabs.xq_m1[xb]
                            };
                            mm.min(mx + 1).min(xm + 1).min(xx + 2)
                        };
                    let tabs = trop_tabs(&v, i, nc);
                    for (&(cb, kn, kw, e, s), _) in &groups {
                        for q in 0..rest_n {
                            let b = best(kn, kw, q, &tabs) + cb as i32;
                            if b > cap {
                                continue;
                            }
                            let idx = trop_out_idx(s, e, i, q, last_row, nc);
                            if b < out[idx] {
                                out[idx] = b;
                            }
                        }
                    }
                } else {
                    // i==0: contract w on axis 0 of between-column state
                    let rest_n = nc * nc;
                    let mut m1 = vec![INF; rest_n];
                    let mut a1 = vec![255u8; rest_n];
                    let mut m2 = vec![INF; rest_n];
                    for w in 0..nc {
                        for q in 0..rest_n {
                            let val = v[w * rest_n + q];
                            if val < m1[q] {
                                m2[q] = m1[q];
                                m1[q] = val;
                                a1[q] = w as u8;
                            } else if val < m2[q] {
                                m2[q] = val;
                            }
                        }
                    }
                    for (&(cb, _kn, kw, e, s), _) in &groups {
                        for q in 0..rest_n {
                            let vm = v[kw as usize * rest_n + q];
                            let vx = if a1[q] == kw { m2[q] } else { m1[q] };
                            let b = (vm.min(vx + 1)) + cb as i32;
                            if b > cap {
                                continue;
                            }
                            let idx = trop_out_idx(s, e, 0, q, last_row, nc);
                            if b < out[idx] {
                                out[idx] = b;
                            }
                        }
                    }
                }
                let _ = s_in;
            }
            has_s = !last_row;
            v = out;
        }
    }
    v.iter().copied().min().unwrap_or(INF)
}

struct TropTabs {
    val: Vec<i32>,    // [s][w][rest]
    row_m1: Vec<i32>, // per (s, rest): min over w
    row_a1: Vec<u8>,
    row_m2: Vec<i32>,
    col_m1: Vec<i32>, // per (w, rest): min over s
    col_a1: Vec<u8>,
    col_m2: Vec<i32>,
    // exact O(1) both-mismatch queries: per (rest q, excluded col w0),
    // the min/arg/second over rows s of rowmin_excluding_w0(s).
    // xx(n0,w0,q) = m1 if a1 != n0 else m2. (A greedy top-k skyline is
    // NOT exact here — adversarial entries sharing e1's column escape it.)
    xq_m1: Vec<i32>,
    xq_a1: Vec<u8>,
    xq_m2: Vec<i32>,
}

/// v is the mid-column state (s, e0, e1, e2) flattened; the contracted
/// w axis is e_i (i in 1..=2 when called). Returns gathered tables with
/// rest = the two e_j (j != i) in ascending j order.
fn trop_tabs(v: &[i32], i: usize, nc: usize) -> TropTabs {
    let rest_n = nc * nc;
    let mut val = vec![INF; nc * nc * rest_n];
    // axes of v: (s, e0, e1, e2) strides: s: nc^3, e0: nc^2, e1: nc, e2: 1
    let st = [nc * nc * nc, nc * nc, nc, 1];
    let w_stride = st[1 + i];
    let rest_axes: Vec<usize> = (0..3).filter(|&j| j != i).map(|j| st[1 + j]).collect();
    for s in 0..nc {
        for w in 0..nc {
            let base_in = s * st[0] + w * w_stride;
            let base_out = (s * nc + w) * rest_n;
            for qa in 0..nc {
                let off_a = base_in + qa * rest_axes[0];
                let out_a = base_out + qa * nc;
                for qb in 0..nc {
                    val[out_a + qb] = v[off_a + qb * rest_axes[1]];
                }
            }
        }
    }
    let mut row_m1 = vec![INF; nc * rest_n];
    let mut row_a1 = vec![255u8; nc * rest_n];
    let mut row_m2 = vec![INF; nc * rest_n];
    let mut col_m1 = vec![INF; nc * rest_n];
    let mut col_a1 = vec![255u8; nc * rest_n];
    let mut col_m2 = vec![INF; nc * rest_n];
    for s in 0..nc {
        for w in 0..nc {
            let base = (s * nc + w) * rest_n;
            for q in 0..rest_n {
                let x = val[base + q];
                let rb = s * rest_n + q;
                if x < row_m1[rb] {
                    row_m2[rb] = row_m1[rb];
                    row_m1[rb] = x;
                    row_a1[rb] = w as u8;
                } else if x < row_m2[rb] {
                    row_m2[rb] = x;
                }
                let cb = w * rest_n + q;
                if x < col_m1[cb] {
                    col_m2[cb] = col_m1[cb];
                    col_m1[cb] = x;
                    col_a1[cb] = s as u8;
                } else if x < col_m2[cb] {
                    col_m2[cb] = x;
                }
            }
        }
    }
    let mut xq_m1 = vec![INF; rest_n * nc];
    let mut xq_a1 = vec![255u8; rest_n * nc];
    let mut xq_m2 = vec![INF; rest_n * nc];
    for s in 0..nc {
        for q in 0..rest_n {
            let rb = s * rest_n + q;
            for w0 in 0..nc {
                let rm = if row_a1[rb] == w0 as u8 { row_m2[rb] } else { row_m1[rb] };
                let xb = q * nc + w0;
                if rm < xq_m1[xb] {
                    xq_m2[xb] = xq_m1[xb];
                    xq_m1[xb] = rm;
                    xq_a1[xb] = s as u8;
                } else if rm < xq_m2[xb] {
                    xq_m2[xb] = rm;
                }
            }
        }
    }
    TropTabs {
        val, row_m1, row_a1, row_m2, col_m1, col_a1, col_m2,
        xq_m1, xq_a1, xq_m2,
    }
}

/// Reduce (min) the dummy e_i axis of the mid state (s,e0,e1,e2).
/// Returns (red[s][rest], rest_n).
fn trop_reduce_axis(v: &[i32], _has_s: bool, i: usize, nc: usize) -> (Vec<i32>, usize) {
    let rest_n = nc * nc;
    let st = [nc * nc * nc, nc * nc, nc, 1];
    let i_stride = st[1 + i];
    let rest_axes: Vec<usize> = (0..3).filter(|&j| j != i).map(|j| st[1 + j]).collect();
    let mut red = vec![INF; nc * rest_n];
    for s in 0..nc {
        for qa in 0..nc {
            for qb in 0..nc {
                let q = qa * nc + qb;
                let base = s * st[0] + qa * rest_axes[0] + qb * rest_axes[1];
                let mut m = INF;
                for x in 0..nc {
                    let val = v[base + x * i_stride];
                    if val < m {
                        m = val;
                    }
                }
                red[s * rest_n + q] = m;
            }
        }
    }
    (red, rest_n)
}

/// Output index for the tropical DP. Output axes: mid (s,e0,e1,e2) or
/// final-row (e0,e1,e2); e_i = e, the rest q = (qa,qb) over j != i asc.
fn trop_out_idx(s: u8, e: u8, i: usize, q: usize, last_row: bool, nc: usize) -> usize {
    let (qa, qb) = (q / nc, q % nc);
    let mut coord = [0usize; 3];
    let mut others = (0..3).filter(|&j| j != i);
    let ja = others.next().unwrap();
    let jb = others.next().unwrap();
    coord[i] = e as usize;
    coord[ja] = qa;
    coord[jb] = qb;
    let base = (coord[0] * nc + coord[1]) * nc + coord[2];
    if last_row {
        base
    } else {
        (s as usize) * nc * nc * nc + base
    }
}

/// H5 (vol-217): bottom-row 1D chain profile — count row-15 fillings
/// (corner + 14 bottom edges + corner, S sides structural) paying b
/// mismatches on the 15 horizontal edges, over the REMAINING border
/// pool, repeats-allowed. V edges to row 14 excluded (relaxation).
/// The border-partition lever: stage 1's top-edge choice fixes the
/// complement available here; frames froze this, frame-free steers it.
fn bottom_chain(ctx: &Ctx, pools: &[Vec<u16>; 3], bmax: usize) -> (i32, f64) {
    let b = bmax + 1;
    let mut v = vec![0.0f64; NC * b];
    for c in 0..16 {
        let cands = cell_cands(ctx, 15, c, pools);
        let mut nv = vec![0.0f64; NC * b];
        if c == 0 {
            for (p, rt) in cands {
                let o = ctx.rot[p as usize][rt as usize];
                nv[(o[1] as usize) * b] += 1.0;
            }
        } else {
            let mut tot = vec![0.0f64; b];
            for e in 0..NC {
                for x in 0..b {
                    tot[x] += v[e * b + x];
                }
            }
            for (p, rt) in cands {
                let o = ctx.rot[p as usize][rt as usize];
                let (w, e) = (o[3] as usize, o[1] as usize);
                for x in 0..b {
                    nv[e * b + x] += v[w * b + x];
                }
                for x in 1..b {
                    nv[e * b + x] += tot[x - 1] - v[w * b + x - 1];
                }
            }
        }
        v = nv;
    }
    let mut counts = vec![0.0f64; b];
    for e in 0..NC {
        for x in 0..b {
            counts[x] += v[e * b + x];
        }
    }
    let bmin = counts.iter().position(|&x| x > 0.0).map(|i| i as i32).unwrap_or(-1);
    let lg = GAMMA.log10();
    let mut wmax = f64::NEG_INFINITY;
    let w: Vec<f64> = counts
        .iter()
        .enumerate()
        .map(|(i, &x)| {
            let l = if x > 0.0 { x.log10() + i as f64 * lg } else { f64::NEG_INFINITY };
            wmax = wmax.max(l);
            l
        })
        .collect();
    let soft = if wmax.is_finite() {
        wmax + w.iter().map(|&x| 10f64.powf(x - wmax)).sum::<f64>().log10()
    } else {
        f64::NEG_INFINITY
    };
    (bmin, soft)
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
    // tropical floor must equal the counting bmin on the same instance
    let trop = band_floor_k3(&ctx, &rows, &t_n, &forced, &pools, bmax as i32, 2);
    let bmin_count = dp.iter().position(|&x| x > 0.5).map(|i| i as i32).unwrap_or(-1);
    let trop_ok = trop == bmin_count;
    println!(
        "selftest {} (tropical {}: floor {} vs bmin {})",
        if ok && trop_ok { "PASS" } else { "FAIL" },
        if trop_ok { "ok" } else { "MISMATCH" },
        trop,
        bmin_count
    );
    println!("dp: {:?}", dp.iter().map(|&x| x.round() as i64).collect::<Vec<_>>());
    println!("bf: {:?}", bf.iter().map(|&x| x.round() as i64).collect::<Vec<_>>());
    i32::from(!(ok && trop_ok))
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
    let mut want_bc = false;
    let mut floor_only = false;
    let mut cap: i32 = 6;
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
            "--bottom-chain" => { want_bc = true; i += 1; }
            "--floor-only" => { floor_only = true; i += 1; }
            "--cap" => { cap = raw[i + 1].parse().unwrap(); i += 2; }
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

    if floor_only {
        let results: Vec<String> = inputs
            .par_iter()
            .map(|bpath| {
                let t0 = Instant::now();
                let placed =
                    load_board(std::slice::from_ref(bpath), truncate, frame.as_ref());
                let f = ask_floor(&ctx, &placed, &rows, cap);
                let ms = t0.elapsed().as_micros() as f64 / 1000.0;
                let tag = bpath.file_stem().unwrap().to_string_lossy().to_string();
                format!("{tag}\t{}..{}\t{f}\t{ms:.1}", rows[0], rows[k - 1])
            })
            .collect();
        let header = "tag\trows\tfloor\tms";
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
        return;
    }

    let results: Vec<String> = inputs
        .par_iter()
        .map(|bpath| {
            let t0 = Instant::now();
            let placed = load_board(
                std::slice::from_ref(bpath),
                truncate,
                frame.as_ref(),
            );
            let r = ask(&ctx, &placed, &rows, bmax, want_bc);
            let ms = t0.elapsed().as_millis();
            let tag = bpath.file_stem().unwrap().to_string_lossy().to_string();
            let bc_cols = match r.bc {
                Some((bf, bs)) => format!("\t{bf}\t{bs:.4}"),
                None => String::new(),
            };
            format!(
                "{tag}\t{}..{}\t{:.4}\t{}\t{:.3}\t{}/{}/{}\t{ms}{bc_cols}",
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

    let header = if want_bc {
        "tag\trows\tsoft_g03\tbmin\tlog_at_bmin\tpool_i/e/c\tms\tbc_floor\tbc_soft"
    } else {
        "tag\trows\tsoft_g03\tbmin\tlog_at_bmin\tpool_i/e/c\tms"
    };
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
