// ISENTROPE (vol-209) — tiling-count entropy W_Γ(n) for canonical E2's piece-alphabet.
// Rust port of scripts/v209_isentrope/count_entropy.py (validated there:
// n=1 W=784, n=2 reusable W=4550669, n=2 distinct W=4059952).
//
// W_Γ(n) = # valid (all internal edges matched) n×n interior blocks from E2's pieces,
// free-floating (free top/left/right borders). S_Γ(n) = log10 W_Γ(n).
//   Variant A (reusable / color-grammar): broken-profile transfer DP, exact.
//   Variant B (distinct / true-E2): DFS with used-set, exact small-n.
//
// Edge index [N,E,S,W] = [0,1,2,3] (matches Edges::as_array). BORDER = 0 in core.
// Usage: isentrope_count [--max-a N] [--max-b N]

use std::collections::HashMap;
use eternity2_core::BORDER;
use eternity2_puzzle_io::load_puzzle;

const NN: usize = 0; // unused placeholder to keep imports tidy
const FREE: u8 = 255; // sentinel "no constraint" (top/left border)

#[derive(Clone, Copy)]
struct Pl { n: u8, e: u8, s: u8, w: u8 }

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    let mut out = [0u8; 4];
    for i in 0..4 { out[i] = e[(i + 4 - (r as usize)) % 4]; }
    out
}

fn build_interior_placements(puzzle: &eternity2_core::Puzzle) -> Vec<Pl> {
    let mut pls = Vec::new();
    for pid in 0..256u16 {
        let p = match puzzle.piece(pid) { Some(p) => p, None => continue };
        let base = p.edges.as_array();
        if base.iter().any(|&c| c == BORDER) { continue; } // interior only
        let mut seen: Vec<[u8;4]> = Vec::new();
        for r in 0..4u8 {
            let ed = rotate_edges(base, r);
            if seen.contains(&ed) { continue; }
            seen.push(ed);
            pls.push(Pl { n: ed[0], e: ed[1], s: ed[2], w: ed[3] });
        }
    }
    pls
}

// Variant A: reusable pieces. Broken-profile DP with PACKED u64 state key.
// Colors are 1..=22 (interior); we pack each profile slot + pend in 5 bits.
// FREE sentinel = 31 (0b11111). Layout: bits [0,5) = profile[0], [5,10) = profile[1],
// ..., [5n, 5n+5) = pend. n<=12 fits in u64 (13*5=65 > 64 -> cap n<=12).
const SLOT_BITS: u64 = 5;
const SLOT_MASK: u64 = 0x1F;
const PFREE: u64 = 31; // 5-bit FREE sentinel (distinct from colors 1..22)

#[inline] fn get_slot(state: u64, idx: usize) -> u64 { (state >> (idx as u64 * SLOT_BITS)) & SLOT_MASK }
#[inline] fn set_slot(state: u64, idx: usize, val: u64) -> u64 {
    (state & !(SLOT_MASK << (idx as u64 * SLOT_BITS))) | (val << (idx as u64 * SLOT_BITS))
}

fn count_reusable(n: usize, place: &[Pl]) -> (u128, bool) {
    assert!(n <= 12, "packed state supports n<=12");
    // pre-bucket placements by N color (1..22). FREE-N means any placement.
    let mut by_n: Vec<Vec<Pl>> = vec![Vec::new(); 32];
    for &p in place { by_n[p.n as usize].push(p); }
    let all: Vec<Pl> = place.to_vec();

    // pend slot index = n (after the n profile slots).
    let pend_idx = n;
    // start: all profile slots = PFREE, pend = PFREE.
    let mut start: u64 = 0;
    for i in 0..=n { start = set_slot(start, i, PFREE); }
    let mut states: HashMap<u64, u128> = HashMap::new();
    states.insert(start, 1u128);
    let mut overflow = false;

    for _y in 0..n {
        for x in 0..n {
            let mut new: HashMap<u64, u128> = HashMap::with_capacity(states.len() * 2);
            for (&state, &cnt) in states.iter() {
                let need_n = get_slot(state, x);
                let need_w = get_slot(state, pend_idx);
                let cands: &[Pl] = if need_n == PFREE { &all } else { &by_n[need_n as usize] };
                for p in cands {
                    if need_w != PFREE && p.w as u64 != need_w { continue; }
                    let mut ns = set_slot(state, x, p.s as u64);
                    let npend = if x < n - 1 { p.e as u64 } else { PFREE };
                    ns = set_slot(ns, pend_idx, npend);
                    let e = new.entry(ns).or_insert(0u128);
                    *e = e.checked_add(cnt).unwrap_or_else(|| { overflow = true; u128::MAX });
                }
            }
            states = new;
        }
    }
    let total: u128 = states.values().fold(0u128, |a, &b| a.saturating_add(b));
    (total, !overflow)
}

// ---- ROW-TRANSFER POWER ITERATION (reusable pieces) — exact entropy density ----
// The seam between two rows is the n-vector of vertical colors (the row-above's
// S-colors = the row-below's N-demands), packed in a u64 (5 bits/slot, n<=12).
// One ROW STEP maps a weighted seam-distribution v to T·v, where T applies one row:
// given N-demands (the incoming seam slots), fill the row left-to-right (column DP),
// producing outgoing seam = the row's S-colors. Power iteration on T converges to
// the Perron eigenvalue lambda = per-row growth; entropy density per CELL = log10(lambda)/n.
//
// Apply T to a single incoming seam: column-DP over the n cells of one row.
// state during the row = (x position implicit, pend = W-demand for next cell,
//   out_seam-so-far = packed S-colors of cells placed so far). N-demand for cell x
//   = slot x of the incoming seam. Output: map out_seam -> weight.
fn apply_row(in_seam: u64, n: usize, by_n: &[Vec<Pl>], all: &[Pl],
             out: &mut HashMap<u64, f64>, w_in: f64) {
    // micro-DP: vector of (out_seam_partial, pend) -> weight, swept x=0..n-1.
    // pend = PFREE at x=0 (left border free).
    let mut cur: HashMap<(u64, u64), f64> = HashMap::new();
    cur.insert((0u64, PFREE), w_in);
    for x in 0..n {
        let need_n = get_slot(in_seam, x);
        let mut nxt: HashMap<(u64, u64), f64> = HashMap::with_capacity(cur.len() * 4);
        for ((oseam, pend), wv) in cur.iter() {
            let cands: &[Pl] = if need_n == PFREE { all } else { &by_n[need_n as usize] };
            for p in cands {
                if *pend != PFREE && p.w as u64 != *pend { continue; }
                let no = set_slot(*oseam, x, p.s as u64);
                let npend = if x < n - 1 { p.e as u64 } else { PFREE };
                *nxt.entry((no, npend)).or_insert(0.0) += *wv;
            }
        }
        cur = nxt;
    }
    for ((oseam, _pend), wv) in cur.iter() {
        *out.entry(*oseam).or_insert(0.0) += *wv;
    }
}

// Returns (lambda_per_row, density_per_cell, iters). density = log10(lambda)/n.
fn entropy_density_power(n: usize, place: &[Pl], max_iter: usize, tol: f64) -> (f64, f64, usize) {
    assert!(n <= 12);
    let mut by_n: Vec<Vec<Pl>> = vec![Vec::new(); 32];
    for &p in place { by_n[p.n as usize].push(p); }
    let all: Vec<Pl> = place.to_vec();
    // initial seam distribution: all-FREE seam (top border free) weight 1.
    let mut start: u64 = 0;
    for i in 0..n { start = set_slot(start, i, PFREE); }
    let mut v: HashMap<u64, f64> = HashMap::new();
    v.insert(start, 1.0);
    let mut lambda = 0.0;
    let mut iters = 0;
    for it in 0..max_iter {
        let mut nv: HashMap<u64, f64> = HashMap::with_capacity(v.len() * 2);
        for (&seam, &w) in v.iter() {
            if w == 0.0 { continue; }
            apply_row(seam, n, &by_n, &all, &mut nv, w);
        }
        // norm = total weight; ratio to previous total = lambda estimate
        let norm: f64 = nv.values().sum();
        let prev: f64 = v.values().sum();
        let lam = norm / prev;
        // renormalize to avoid overflow
        let inv = 1.0 / norm;
        for w in nv.values_mut() { *w *= inv; }
        v = nv;
        iters = it + 1;
        if it > 2 && (lam - lambda).abs() / lam < tol { lambda = lam; break; }
        lambda = lam;
    }
    (lambda, lambda.log10() / n as f64, iters)
}

// ---- SCARCITY RATIO by sampling: rho(n) = W_distinct(n)/W_reusable(n) ----
// = P(uniform random valid reusable n×n block uses all-distinct pieces). Exact
// distinct count is exponential; we sample uniformly via suffix-count weighting.
// Reuse packed u64 state (profile[0..n] + pend at slot n). placements carry pid.
struct PlP { pid: u16, n: u8, e: u8, s: u8, w: u8 }

fn build_interior_placements_p(puzzle: &eternity2_core::Puzzle) -> Vec<PlP> {
    let mut v = Vec::new();
    for pid in 0..256u16 {
        let p = match puzzle.piece(pid) { Some(p) => p, None => continue };
        let base = p.edges.as_array();
        if base.iter().any(|&c| c == BORDER) { continue; }
        let mut seen: Vec<[u8;4]> = Vec::new();
        for r in 0..4u8 {
            let ed = rotate_edges(base, r);
            if seen.contains(&ed) { continue; }
            seen.push(ed);
            v.push(PlP { pid, n: ed[0], e: ed[1], s: ed[2], w: ed[3] });
        }
    }
    v
}

// xorshift64 RNG seeded from a constant (Math.random unavailable in workflows; here
// we just want reproducible sampling).
struct Rng(u64);
impl Rng {
    fn next_f64(&mut self) -> f64 {
        let mut x = self.0;
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        self.0 = x;
        (x >> 11) as f64 / (1u64 << 53) as f64
    }
}

fn sample_ratio(n: usize, place: &[PlP], nsamples: u64, seed: u64) -> (f64, f64, u64, f64) {
    assert!(n <= 12);
    let mut by_n: Vec<Vec<&PlP>> = vec![Vec::new(); 32];
    for p in place { by_n[p.n as usize].push(p); }
    let all: Vec<&PlP> = place.iter().collect();
    let total = n * n;
    let pend_idx = n;
    let mut start: u64 = 0;
    for i in 0..=n { start = set_slot(start, i, PFREE); }

    // forward reachable sets per cell (0..=total)
    let mut reach: Vec<std::collections::HashSet<u64>> = vec![std::collections::HashSet::new(); total + 1];
    reach[0].insert(start);
    for k in 0..total {
        let x = k % n;
        let cur: Vec<u64> = reach[k].iter().copied().collect();
        for st in cur {
            let need_n = get_slot(st, x);
            let need_w = get_slot(st, pend_idx);
            let cands: &[&PlP] = if need_n == PFREE { &all } else { &by_n[need_n as usize] };
            for p in cands {
                if need_w != PFREE && p.w as u64 != need_w { continue; }
                let mut ns = set_slot(st, x, p.s as u64);
                let npend = if x < n - 1 { p.e as u64 } else { PFREE };
                ns = set_slot(ns, pend_idx, npend);
                reach[k + 1].insert(ns);
            }
        }
    }
    // backward suffix counts (f64)
    let mut suffix: Vec<HashMap<u64, f64>> = vec![HashMap::new(); total + 1];
    for &st in reach[total].iter() { suffix[total].insert(st, 1.0); }
    for k in (0..total).rev() {
        let x = k % n;
        let mut sc: HashMap<u64, f64> = HashMap::with_capacity(reach[k].len());
        for &st in reach[k].iter() {
            let need_n = get_slot(st, x);
            let need_w = get_slot(st, pend_idx);
            let cands: &[&PlP] = if need_n == PFREE { &all } else { &by_n[need_n as usize] };
            let mut tot = 0.0;
            for p in cands {
                if need_w != PFREE && p.w as u64 != need_w { continue; }
                let mut ns = set_slot(st, x, p.s as u64);
                let npend = if x < n - 1 { p.e as u64 } else { PFREE };
                ns = set_slot(ns, pend_idx, npend);
                tot += suffix[k + 1].get(&ns).copied().unwrap_or(0.0);
            }
            sc.insert(st, tot);
        }
        suffix[k] = sc;
    }
    let w_reusable = suffix[0].get(&start).copied().unwrap_or(0.0);

    // forward sampling weighted by suffix counts; check distinctness
    let mut rng = Rng(seed | 1);
    let mut distinct: u64 = 0;
    let mut ok: u64 = 0;
    let mut chosen_pids: Vec<u16> = Vec::with_capacity(total);
    for _ in 0..nsamples {
        let mut st = start;
        chosen_pids.clear();
        let mut dead = false;
        for k in 0..total {
            let x = k % n;
            let need_n = get_slot(st, x);
            let need_w = get_slot(st, pend_idx);
            let cands: &[&PlP] = if need_n == PFREE { &all } else { &by_n[need_n as usize] };
            // total suffix weight
            let mut wsum = 0.0;
            for p in cands {
                if need_w != PFREE && p.w as u64 != need_w { continue; }
                let mut ns = set_slot(st, x, p.s as u64);
                let npend = if x < n - 1 { p.e as u64 } else { PFREE };
                ns = set_slot(ns, pend_idx, npend);
                wsum += suffix[k + 1].get(&ns).copied().unwrap_or(0.0);
            }
            if wsum == 0.0 { dead = true; break; }
            let mut r = rng.next_f64() * wsum;
            let mut picked: Option<(u16, u64)> = None;
            for p in cands {
                if need_w != PFREE && p.w as u64 != need_w { continue; }
                let mut ns = set_slot(st, x, p.s as u64);
                let npend = if x < n - 1 { p.e as u64 } else { PFREE };
                ns = set_slot(ns, pend_idx, npend);
                let w = suffix[k + 1].get(&ns).copied().unwrap_or(0.0);
                if w == 0.0 { continue; }
                r -= w;
                if r <= 0.0 { picked = Some((p.pid, ns)); break; }
            }
            let (pid, ns) = picked.unwrap();
            chosen_pids.push(pid);
            st = ns;
        }
        if dead { continue; }
        ok += 1;
        // distinctness: sort+dedup
        let mut tmp = chosen_pids.clone();
        tmp.sort_unstable();
        tmp.dedup();
        if tmp.len() == chosen_pids.len() { distinct += 1; }
    }
    let rho = if ok > 0 { distinct as f64 / ok as f64 } else { f64::NAN };
    (w_reusable, rho, ok, rho.max(1e-12))
}

// Variant B: distinct pieces. DFS row-major with used bitset over piece ids.
// place_by_piece: we need piece_id per placement to enforce distinctness.
struct PlD { pid: u16, n: u8, e: u8, s: u8, w: u8 }

fn build_interior_placements_d(puzzle: &eternity2_core::Puzzle) -> Vec<PlD> {
    let mut pls = Vec::new();
    for pid in 0..256u16 {
        let p = match puzzle.piece(pid) { Some(p) => p, None => continue };
        let base = p.edges.as_array();
        if base.iter().any(|&c| c == BORDER) { continue; }
        let mut seen: Vec<[u8;4]> = Vec::new();
        for r in 0..4u8 {
            let ed = rotate_edges(base, r);
            if seen.contains(&ed) { continue; }
            seen.push(ed);
            pls.push(PlD { pid, n: ed[0], e: ed[1], s: ed[2], w: ed[3] });
        }
    }
    pls
}

fn count_distinct(n: usize, place: &[PlD], node_cap: u64) -> (u128, bool, u64) {
    let mut used = vec![false; 256];
    let mut profile = vec![FREE; n];
    let mut cnt: u128 = 0;
    let mut nodes: u64 = 0;
    let mut stop = false;
    // recursive closure via explicit stack-free recursion: use an inner fn with refs.
    fn dfs(idx: usize, pend: u8, n: usize, place: &[PlD], used: &mut [bool],
           profile: &mut [u8], cnt: &mut u128, nodes: &mut u64, node_cap: u64, stop: &mut bool) {
        if *stop { return; }
        *nodes += 1;
        if *nodes > node_cap { *stop = true; return; }
        if idx == n * n { *cnt += 1; return; }
        let x = idx % n;
        let need_n = profile[x];
        let need_w = pend;
        for p in place {
            if used[p.pid as usize] { continue; }
            if need_n != FREE && p.n != need_n { continue; }
            if need_w != FREE && p.w != need_w { continue; }
            used[p.pid as usize] = true;
            let old = profile[x];
            profile[x] = p.s;
            let npend = if x < n - 1 { p.e } else { FREE };
            dfs(idx + 1, npend, n, place, used, profile, cnt, nodes, node_cap, stop);
            profile[x] = old;
            used[p.pid as usize] = false;
            if *stop { return; }
        }
    }
    dfs(0, FREE, n, place, &mut used, &mut profile, &mut cnt, &mut nodes, node_cap, &mut stop);
    (cnt, !stop, nodes)
}

fn main() {
    let _ = NN;
    let mut max_a = 6usize;
    let mut max_b = 5usize;
    let mut power_max = 0usize; // if >0, run row-transfer power iteration for widths 1..=power_max
    let mut sample_max = 0usize; // if >0, sample scarcity ratio rho(n) for n=2..=sample_max
    let mut nsamples: u64 = 200_000;
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--max-a" => { max_a = args[i+1].parse().unwrap(); i += 2; }
            "--max-b" => { max_b = args[i+1].parse().unwrap(); i += 2; }
            "--power-max" => { power_max = args[i+1].parse().unwrap(); i += 2; }
            "--sample-max" => { sample_max = args[i+1].parse().unwrap(); i += 2; }
            "--nsamples" => { nsamples = args[i+1].parse().unwrap(); i += 2; }
            _ => { i += 1; }
        }
    }
    let puzzle = load_puzzle(std::path::Path::new("../data/puzzles/size_16_official_eternity.csv"))
        .expect("load puzzle");
    let place = build_interior_placements(&puzzle);
    let place_d = build_interior_placements_d(&puzzle);
    eprintln!("[init] interior placements: {}", place.len());

    println!("variant,n,W,S_log10,S_over_n2,exact,nodes,secs");
    // Variant A
    for n in 1..=max_a {
        let t = std::time::Instant::now();
        let (w, exact) = count_reusable(n, &place);
        let secs = t.elapsed().as_secs_f64();
        let s = if w > 0 { (w as f64).log10() } else { f64::NEG_INFINITY };
        println!("A,{},{},{:.6},{:.6},{},,{:.2}", n, w, s, s / (n * n) as f64, exact, secs);
        eprintln!("[A] n={n}: W={w} S={s:.4} S/n2={:.5} ({secs:.1}s){}",
                  s/(n*n) as f64, if exact {""} else {" OVERFLOW"});
        if secs > 600.0 { eprintln!("[A] n={n} took {secs:.0}s; stopping"); break; }
    }
    // Variant B
    for n in 1..=max_b {
        let t = std::time::Instant::now();
        let (w, exact, nodes) = count_distinct(n, &place_d, 200_000_000_000);
        let secs = t.elapsed().as_secs_f64();
        let s = if w > 0 { (w as f64).log10() } else { f64::NEG_INFINITY };
        println!("B,{},{},{:.6},{:.6},{},{},{:.2}", n, w, s, s / (n * n) as f64, exact, nodes, secs);
        eprintln!("[B] n={n}: W={w} S={s:.4} S/n2={:.5} [{}] nodes={nodes} ({secs:.1}s)",
                  s/(n*n) as f64, if exact {"exact"} else {"PARTIAL"});
        if !exact { eprintln!("[B] n={n} hit node cap; stop"); break; }
        if secs > 1200.0 { eprintln!("[B] n={n} took {secs:.0}s; stopping"); break; }
    }
    // Row-transfer power iteration: exact per-cell entropy DENSITY h(n) = log10(lambda)/n
    // (lambda = Perron eigenvalue of the row-transfer operator). As n grows, h(n)
    // converges to the topological entropy density h_inf of E2's color grammar.
    if power_max > 0 {
        eprintln!("[POWER] row-transfer entropy density (reusable grammar):");
        println!("# power-iteration: variant=P, S_over_n2 column = per-cell density log10(lambda)/n");
        for n in 1..=power_max {
            let t = std::time::Instant::now();
            let (lambda, density, iters) = entropy_density_power(n, &place, 2000, 1e-13);
            let secs = t.elapsed().as_secs_f64();
            // also report per-row entropy log10(lambda) for context
            println!("P,{},,{:.10},{:.10},,{},{:.2}", n, lambda.log10(), density, iters, secs);
            eprintln!("[P] width n={n}: lambda(per-row)={lambda:.6} log10(lambda)={:.6} \
                       density/cell={density:.8} (iters={iters}, {secs:.1}s)", lambda.log10());
            if secs > 600.0 { eprintln!("[P] n={n} took {secs:.0}s; stopping"); break; }
        }
    }
    // Scarcity ratio rho(n) = W_distinct/W_reusable by uniform sampling.
    if sample_max > 0 {
        let place_p = build_interior_placements_p(&puzzle);
        eprintln!("[SAMPLE] scarcity ratio rho(n)=W_distinct/W_reusable (n={nsamples} samples each):");
        println!("# sampling: variant=R, W column = W_reusable, S_log10 = rho, S_over_n2 = 95%CI");
        for n in 2..=sample_max {
            let t = std::time::Instant::now();
            let (wre, rho, ok, _) = sample_ratio(n, &place_p, nsamples, 0x9E3779B97F4A7C15 ^ (n as u64));
            let secs = t.elapsed().as_secs_f64();
            let ci = if ok > 0 { 1.96 * (rho * (1.0 - rho) / ok as f64).sqrt() } else { 0.0 };
            let s_dist = if rho > 0.0 { (wre).log10() + rho.log10() } else { f64::NEG_INFINITY };
            println!("R,{},{:.0},{:.6},{:.6},,{},{:.2}", n, wre, rho, ci, ok, secs);
            eprintln!("[R] n={n}: W_reusable={wre:.3e} rho={rho:.4} ±{ci:.4} \
                       S_distinct≈{s_dist:.3} (S/n²={:.4}) ok={ok} ({secs:.1}s)", s_dist/(n*n) as f64);
            if secs > 600.0 { eprintln!("[R] n={n} took {secs:.0}s; stopping"); break; }
        }
    }
}
