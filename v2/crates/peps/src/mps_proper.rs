// Proper boundary-MPS contraction with per-bond chi-truncation — reaches width 16.
//
// The existing mps.rs `absorb_row` materializes the full K^size boundary tensor
// (overflows isize at K=23,size=16). This module keeps the boundary as a true MPS
// (a chain of rank-3 tensors with bounded virtual bonds) and never forms K^size.
//
// Boundary MPS: Vec of `size` tensors A_x with shape [left_bond, K (physical S-color),
// right_bond]. It represents the (unnormalized) distribution over boundary color
// vectors (s_0,...,s_{size-1}) handed from the row above to the row below.
//
// Applying one row of cell tensors Cell_x[N,E,S,W] (an MPO with horizontal bonds
// E=W of dimension K and vertical "physical" legs N (in) / S (out)):
//   new boundary MPS tensor at column x:
//     B_x[(a,p), S, (b,q)] = sum_{N} A_x[a, N, b] * Cell_x[N, q_out=E, S, p_in=W]
//   where p = incoming horizontal bond (W) from column x-1, q = outgoing (E) to x+1.
//   Left border: column 0's W is fixed to BORDER. Right border: column size-1's E=BORDER.
//   The combined left bond is (a,p), right bond (b,q); we then SVD-truncate to chi.
//
// We carry log-scale normalization to avoid overflow across 16 rows.

use crate::PepsContext;
use crate::tensor::build_all_cell_tensors;
use eternity2_core::BORDER;
use ndarray::{Array2, Array3, Axis};
use ndarray_linalg::SVD;

/// One MPS site tensor: shape [left, phys(K), right].
type Site = Array3<f64>;

#[derive(Clone)]
pub struct Mps {
    pub sites: Vec<Site>,
    pub log_norm: f64, // accumulated log of extracted norms
    pub k: usize,
}

impl Mps {
    /// Initial boundary: all N = BORDER (top border). Represented as a product MPS
    /// (bond dim 1) with each physical leg a delta at BORDER.
    fn initial(k: usize, size: usize) -> Self {
        let mut sites = Vec::with_capacity(size);
        for _ in 0..size {
            let mut a = Array3::<f64>::zeros((1, k, 1));
            a[[0, BORDER as usize, 0]] = 1.0;
            sites.push(a);
        }
        Mps { sites, log_norm: 0.0, k }
    }

    fn total_log(&self) -> f64 {
        // contract the whole MPS with all physical legs summed? No — we need the
        // FULL sum over boundary colors with the bottom-row border applied. For the
        // entropy we want Z = sum over all completions; the row sweep already applied
        // rows. The final scalar = contract remaining MPS with physical legs FREE-summed
        // EXCEPT the bottom border slices S=BORDER (handled by the last row's cells).
        // Here `total_log` returns log of the scalar obtained by summing all physical
        // legs (used after the last row, where S has been border-forced by cells).
        // Contract left-to-right: vector v (size left_bond) = ones row.
        let mut v: Array2<f64> = Array2::ones((1, 1)); // [1, left_bond=1]
        for site in &self.sites {
            // sum over physical -> matrix [left, right]
            let (l, kk, r) = (site.shape()[0], site.shape()[1], site.shape()[2]);
            let mut m = Array2::<f64>::zeros((l, r));
            for a in 0..l {
                for p in 0..kk {
                    for b in 0..r {
                        m[[a, b]] += site[[a, p, b]];
                    }
                }
            }
            v = v.dot(&m); // [1,l]·[l,r] = [1,r]
        }
        let s: f64 = v.sum();
        if s <= 0.0 { f64::NEG_INFINITY } else { self.log_norm + s.ln() }
    }
}

/// Apply one row (cell tensors for columns 0..size) to the boundary MPS, with
/// chi-truncation. Cell_x has shape [N,E,S,W] = [k,k,k,k].
fn apply_row(mps: &Mps, row: &[ndarray::Array4<f64>], chi: usize) -> Mps {
    let size = row.len();
    let k = mps.k;
    // Build new (un-truncated) sites, bond = old_bond * horizontal_bond(k).
    // We sweep left->right, building each site, then do an SVD left-canonical sweep
    // with truncation.
    let mut new_sites: Vec<Site> = Vec::with_capacity(size);
    for x in 0..size {
        let a = &mps.sites[x]; // [la, N, ra]
        let cell = &row[x];     // [N,E,S,W]
        let (la, _kn, ra) = (a.shape()[0], a.shape()[1], a.shape()[2]);
        // horizontal bond dims: left p (=W), right q (=E). At borders fix to BORDER.
        let p_dim = if x == 0 { 1 } else { k };
        let q_dim = if x == size - 1 { 1 } else { k };
        // new tensor B[(la,p), S, (ra,q)]
        let mut b = Array3::<f64>::zeros((la * p_dim, k, ra * q_dim));
        for n in 0..k {
            for s in 0..k {
                for pp in 0..p_dim {
                    let w = if x == 0 { BORDER as usize } else { pp };
                    for qq in 0..q_dim {
                        let e = if x == size - 1 { BORDER as usize } else { qq };
                        let cval = cell[[n, e, s, w]];
                        if cval == 0.0 { continue; }
                        for al in 0..la {
                            for ar in 0..ra {
                                let av = a[[al, n, ar]];
                                if av == 0.0 { continue; }
                                b[[al * p_dim + pp, s, ar * q_dim + qq]] += av * cval;
                            }
                        }
                    }
                }
            }
        }
        new_sites.push(b);
    }
    // Left-to-right SVD compression sweep with truncation to chi.
    let mut log_norm = mps.log_norm;
    let mut carry: Option<Array2<f64>> = None; // [carry_bond, left_of_next]
    for x in 0..size {
        let mut site = new_sites[x].clone();
        let (l, kk, r) = (site.shape()[0], site.shape()[1], site.shape()[2]);
        // absorb carry into left bond
        if let Some(c) = carry.take() {
            // c: [cl, l]; site: [l,kk,r] -> [cl,kk,r]
            let cl = c.shape()[0];
            let mut ns = Array3::<f64>::zeros((cl, kk, r));
            for a in 0..cl {
                for p in 0..kk {
                    for b in 0..r {
                        let mut acc = 0.0;
                        for m in 0..l {
                            acc += c[[a, m]] * site[[m, p, b]];
                        }
                        ns[[a, p, b]] = acc;
                    }
                }
            }
            site = ns;
        }
        let (l, kk, r) = (site.shape()[0], site.shape()[1], site.shape()[2]);
        if x == size - 1 {
            // last site: no further factorization; keep, normalize.
            let nrm = frob(&site);
            if nrm > 0.0 { site.mapv_inplace(|v| v / nrm); log_norm += nrm.ln(); }
            new_sites[x] = site;
            break;
        }
        // reshape [l,kk,r] -> matrix [(l*kk), r], SVD = U S Vt
        let mat = site.to_shape((l * kk, r)).unwrap().to_owned();
        let (u_opt, sv, vt_opt) = mat.svd(true, true).expect("svd");
        let u = u_opt.unwrap();   // [(l*kk), min]
        let vt = vt_opt.unwrap(); // [min, r]
        let keep = if chi > 0 { chi.min(sv.len()) } else { sv.len() };
        // truncated U -> new left-canonical site [l, kk, keep]
        let uk = u.slice(ndarray::s![.., ..keep]).to_owned();
        let site_new = uk.to_shape((l, kk, keep)).unwrap().to_owned();
        new_sites[x] = site_new;
        // carry = S_keep * Vt_keep : [keep, r]
        let mut sm = Array2::<f64>::zeros((keep, r));
        for i in 0..keep {
            for j in 0..r {
                sm[[i, j]] = sv[i] * vt[[i, j]];
            }
        }
        // normalize carry to keep magnitudes controlled
        let nrm = frob2(&sm);
        if nrm > 0.0 { sm.mapv_inplace(|v| v / nrm); log_norm += nrm.ln(); }
        carry = Some(sm);
    }
    Mps { sites: new_sites, log_norm, k }
}

fn frob(a: &Array3<f64>) -> f64 { a.iter().map(|&v| v * v).sum::<f64>().sqrt() }
fn frob2(a: &Array2<f64>) -> f64 { a.iter().map(|&v| v * v).sum::<f64>().sqrt() }

/// All-cell color-signature marginals via top/bottom environments + per-row L/R
/// sweep. O(size) MPS sweeps total, then per cell a local contraction — vastly
/// cheaper than one-contraction-per-(piece,rot). chi-truncated.
/// Returns, per cell, HashMap<[n,e,s,w] -> unnormalized weight>.
pub fn cell_marginals(
    ctx: &PepsContext,
    cells: &[ndarray::Array4<f64>],
    chi: usize,
) -> Vec<std::collections::HashMap<[u8; 4], f64>> {
    use std::collections::HashMap;
    let size = ctx.size;
    let k = ctx.k_colors;
    // top_env[r] = MPS over N-demands of row r (after rows 0..r-1).
    let mut top_env: Vec<Mps> = Vec::with_capacity(size + 1);
    {
        let mut mps = Mps::initial(k, size);
        top_env.push(mps_clone(&mps));
        for r in 0..size {
            let row: Vec<_> = (0..size).map(|x| cells[r * size + x].clone()).collect();
            mps = apply_row(&mps, &row, chi);
            top_env.push(mps_clone(&mps));
        }
    }
    // bot_env[r] = MPS after applying transposed rows size-1..r (from the bottom up).
    // Physical leg of bot_env[r] = "outgoing" of the last transposed row applied (row r)
    // = row r's N = S of row r-1. So bot_env[r+1] has physical leg = S of row r, which is
    // the "below" constraint for row r in the combine.
    let mut bot_env: Vec<Mps> = vec![Mps::initial(k, size); size + 1];
    {
        let mut mps = Mps::initial(k, size);
        bot_env[size] = mps_clone(&mps);
        for r in (0..size).rev() {
            let row_t: Vec<_> = (0..size).map(|x| transpose_ns(&cells[r * size + x])).collect();
            mps = apply_row(&mps, &row_t, chi);
            bot_env[r] = mps_clone(&mps);
        }
    }
    let mut out: Vec<HashMap<[u8; 4], f64>> = vec![HashMap::new(); size * size];
    for r in 0..size {
        let top = &top_env[r];      // physical leg = N of row r
        let bot = &bot_env[r + 1];  // physical leg = N of row r+1 = S of row r
        // lenv[x] keyed (ta, ba, W_into_x) = contraction of columns 0..x-1.
        // (forward; identical recursion to the validated open-sweep, sans open cell.)
        let mut lenv: Vec<HashMap<(usize, usize, usize), f64>> = vec![HashMap::new(); size + 1];
        lenv[0].insert((0, 0, BORDER as usize), 1.0);
        for x in 0..size {
            let tsite = &top.sites[x]; let bsite = &bot.sites[x]; let cell = &cells[r * size + x];
            let ra = tsite.shape()[2]; let rb = bsite.shape()[2];
            let e_dim = if x == size - 1 { 1 } else { k };
            let mut nxt: HashMap<(usize, usize, usize), f64> = HashMap::new();
            for (&(ta, ba, h), &wv) in lenv[x].iter() {
                let w_in = if x == 0 { BORDER as usize } else { h };
                for nn in 0..k { for ss in 0..k { for ee in 0..e_dim {
                    let e = if x == size - 1 { BORDER as usize } else { ee };
                    let cval = cell[[nn, e, ss, w_in]];
                    if cval == 0.0 { continue; }
                    for arp in 0..ra {
                        let tv = tsite[[ta, nn, arp]]; if tv == 0.0 { continue; }
                        for brp in 0..rb {
                            let bv = bsite[[ba, ss, brp]]; if bv == 0.0 { continue; }
                            *nxt.entry((arp, brp, e)).or_insert(0.0) += wv * cval * tv * bv;
                        }
                    }
                }}}
            }
            lenv[x + 1] = nxt;
        }
        // renv[x] keyed (tar, bar, E_outof_x) = contraction of columns x+1..size-1 (mirror,
        // swept right-to-left). renv[size-1] base: nothing to the right; E_outof_{size-1}=
        // BORDER, right bonds trivial(1).
        let mut renv: Vec<HashMap<(usize, usize, usize), f64>> = vec![HashMap::new(); size + 1];
        // renv[size-1]: columns size..end = empty; key (right-bond_top, right-bond_bot, E=BORDER)
        {
            let ts = &top.sites[size - 1]; let bs = &bot.sites[size - 1];
            for tar in 0..ts.shape()[2] { for bar in 0..bs.shape()[2] {
                renv[size - 1].insert((tar, bar, BORDER as usize), 1.0);
            }}
        }
        for x in (1..size).rev() {
            // build renv[x-1] (cols x..size-1) by absorbing column x into renv[x].
            let tsite = &top.sites[x]; let bsite = &bot.sites[x]; let cell = &cells[r * size + x];
            let la = tsite.shape()[0]; let lb = bsite.shape()[0];
            let e_dim = if x == size - 1 { 1 } else { k };
            let mut cur: HashMap<(usize, usize, usize), f64> = HashMap::new();
            for (&(tar, bar, e_out), &wv) in renv[x].iter() {
                // e_out = E_outof_x. We sum over W_into_x (= E_outof_{x-1}).
                for nn in 0..k { for ss in 0..k {
                    let e = if x == size - 1 { BORDER as usize } else { e_out };
                    for ta in 0..la {
                        let tv = tsite[[ta, nn, tar]]; if tv == 0.0 { continue; }
                        for ba in 0..lb {
                            let bv = bsite[[ba, ss, bar]]; if bv == 0.0 { continue; }
                            for w_in in 0..k {
                                let cval = cell[[nn, e, ss, w_in]];
                                if cval == 0.0 { continue; }
                                // key by left bonds of col x (= right bonds of col x-1) and
                                // E_outof_{x-1} = W_into_x = w_in.
                                *cur.entry((ta, ba, w_in)).or_insert(0.0) += wv * cval * tv * bv;
                            }
                        }
                    }
                }}
            }
            renv[x - 1] = cur;
        }
        // combine per cell x: marginal[n,e,s,w] = sum_{ta,ba,tar,bar}
        //   lenv[x](ta,ba,w) * top[ta,n,tar] * bot[ba,s,bar] * cell[n,e,s,w] * renv[x](tar,bar,e)
        for x in 0..size {
            let tsite = &top.sites[x]; let bsite = &bot.sites[x]; let cell = &cells[r * size + x];
            let ra = tsite.shape()[2]; let rb = bsite.shape()[2];
            let e_dim = if x == size - 1 { 1 } else { k };
            let mut marg: HashMap<[u8; 4], f64> = HashMap::new();
            for (&(ta, ba, wd), &lw) in lenv[x].iter() {
                let w_in = if x == 0 { BORDER as usize } else { wd };
                for nn in 0..k { for ss in 0..k { for ee in 0..e_dim {
                    let e = if x == size - 1 { BORDER as usize } else { ee };
                    let cval = cell[[nn, e, ss, w_in]];
                    if cval == 0.0 { continue; }
                    for arp in 0..ra {
                        let tv = tsite[[ta, nn, arp]]; if tv == 0.0 { continue; }
                        for brp in 0..rb {
                            let bv = bsite[[ba, ss, brp]]; if bv == 0.0 { continue; }
                            let rw = renv[x].get(&(arp, brp, e)).copied().unwrap_or(0.0);
                            if rw == 0.0 { continue; }
                            *marg.entry([nn as u8, e as u8, ss as u8, w_in as u8]).or_insert(0.0)
                                += lw * cval * tv * bv * rw;
                        }
                    }
                }}}
            }
            out[r * size + x] = marg;
        }
    }
    out
}

fn mps_clone(m: &Mps) -> Mps { Mps { sites: m.sites.clone(), log_norm: m.log_norm, k: m.k } }

fn transpose_ns(cell: &ndarray::Array4<f64>) -> ndarray::Array4<f64> {
    let k = cell.shape()[0];
    let mut t = ndarray::Array4::<f64>::zeros((k, k, k, k));
    for n in 0..k { for e in 0..k { for s in 0..k { for w in 0..k {
        t[[s, e, n, w]] = cell[[n, e, s, w]];
    }}}}
    t
}

/// log(Z) from PREBUILT cell tensors (allows pinning / mu weights), chi-truncated MPS.
pub fn log_z_mps_cells(ctx: &PepsContext, cells: &[ndarray::Array4<f64>], chi: usize) -> f64 {
    let size = ctx.size;
    let k = ctx.k_colors;
    let mut mps = Mps::initial(k, size);
    for r in 0..size {
        let row: Vec<_> = (0..size).map(|x| cells[r * size + x].clone()).collect();
        mps = apply_row(&mps, &row, chi);
    }
    mps.total_log()
}

/// log(Z) = log number of valid reusable colorings of the bordered size×size board,
/// via chi-truncated boundary MPS. Returns natural log.
pub fn log_z_mps(ctx: &PepsContext, chi: usize) -> f64 {
    let mu = vec![0.0f64; ctx.n_pieces];
    let pinned = vec![None; ctx.size * ctx.size];
    let cells = build_all_cell_tensors(ctx, &mu, &pinned);
    log_z_mps_cells(ctx, &cells, chi)
}

/// Debug: top_env[size] fully summed and bot_env[0] fully summed should both == Z.
pub fn debug_envs(ctx: &PepsContext, cells: &[ndarray::Array4<f64>], chi: usize) {
    let size = ctx.size; let k = ctx.k_colors;
    // down-sweep
    let mut mps = Mps::initial(k, size);
    for r in 0..size {
        let row: Vec<_> = (0..size).map(|x| cells[r*size+x].clone()).collect();
        mps = apply_row(&mps, &row, chi);
    }
    println!("top_env[size].total_log -> Z' = {:.4}", mps.total_log().exp());
    // up-sweep transposed
    let mut mps2 = Mps::initial(k, size);
    for r in (0..size).rev() {
        let row_t: Vec<_> = (0..size).map(|x| transpose_ns(&cells[r*size+x])).collect();
        mps2 = apply_row(&mps2, &row_t, chi);
    }
    println!("bot_env[0].total_log -> Z'' = {:.4}", mps2.total_log().exp());
}
