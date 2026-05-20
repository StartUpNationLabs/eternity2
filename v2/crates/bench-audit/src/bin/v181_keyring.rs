// V178 STIGMA — V175 GAUNTLET + pheromone-adjacency ranking signal.
//
// In addition to V175's prior_sum and GAUNTLET scan orders, this binary
// loads a piece-pair-direction pheromone matrix τ[p1, p2, d] and uses
// the sum of τ-bonuses across the new placement's already-placed
// neighbors as an extra signal in beam ranking.
//
// CLI:
//   --pheromone-file PATH    — JSON with {"shape": [256,256,4], "data": [...]}
//   --pheromone-weight λ     — multiplier on pheromone sum (default 0.0)
//
// At each placement of piece p at pos with already-placed neighbors:
//   pher_inc = τ[neighbor_N, p, S] + τ[p, neighbor_E, W] + τ[p, neighbor_S, N] + τ[neighbor_W, p, E]
//   ... etc. (directional, only from placed neighbors)
//
// Pheromone sum accumulates across the build; combined score
// for ranking = score + α·prior_sum + λ·pheromone_sum.
//
// Fork of v155_weaving_prior. The novelty is in `build_scan_order`:
//   --scan row        top-to-bottom row-major (V155 default)
//   --scan col        L-to-R column-major (V155)
//   --scan row_rev    bottom-up row-major
//   --scan col_rev    right-to-left column-major
//   --scan zigzag     row 0 L→R, row 1 R→L, etc (boustrophedon)
//   --scan zigzag_rev row 15 L→R, row 14 R→L, etc
//   --scan spiral_in  spiral inward from (0,0)
//   --scan spiral_out spiral outward from center
//
// Each scan order gives different basin geography because:
//   - the prior is consulted in different (piece, position) orders,
//   - hints (135, 210, 34, 221, 45) are encountered earlier or later,
//   - error accumulation paths differ (early errors compound later).
//
// Pure from-scratch (doesn't anchor on any single board).

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_core::BORDER;
use eternity2_puzzle_io::load_puzzle;

const N: usize = 16;
const N_POS: usize = N * N;
const N_PIECES: usize = 256;
const N_ROT: usize = 4;

#[derive(Clone, Copy)]
#[allow(dead_code)]
struct PieceRot {
    piece_id: u16,
    rot: u8,
    n: u8, e: u8, s: u8, w: u8,
}

#[derive(Clone)]
struct BeamState {
    chosen: Vec<u32>,
    used_mask: [u64; 4],
    score: u32,
    /// Total prior weight: sum of prior(piece, position) for all placed cells.
    prior_sum: u32,
    /// V178 — accumulated pheromone weight across all placed adjacencies
    /// in this partial board. Used as additional ranking signal.
    pheromone_sum: f64,
    /// V181 KEYRING — accumulated 2x2 patch score (categorical: +1 for
    /// high-only patches, 0 for neutral, -0.2 for low-only).
    patch_sum: f64,
    state_hash: u64,
}

impl BeamState {
    fn new() -> Self {
        Self {
            chosen: vec![u32::MAX; N_POS],
            used_mask: [0u64; 4],
            score: 0,
            prior_sum: 0,
            pheromone_sum: 0.0,
            patch_sum: 0.0,
            state_hash: 0,
        }
    }
    #[inline] fn is_used(&self, pid: u16) -> bool {
        let pid = pid as usize;
        (self.used_mask[pid / 64] >> (pid % 64)) & 1 == 1
    }
    #[inline] fn mark_used(&mut self, pid: u16) {
        let pid = pid as usize;
        self.used_mask[pid / 64] |= 1u64 << (pid % 64);
    }
}

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    let mut out = [0u8; 4];
    for i in 0..4 {
        out[i] = e[(i + 4 - (r as usize)) % 4];
    }
    out
}

#[inline] fn pos_row(pos: usize) -> usize { pos / N }
#[inline] fn pos_col(pos: usize) -> usize { pos % N }

#[derive(Clone, Copy, PartialEq)]
enum CellClass { Corner, Edge, Interior }

#[inline]
fn cell_class(pos: usize) -> CellClass {
    let r = pos_row(pos);
    let c = pos_col(pos);
    let on_h = r == 0 || r == N - 1;
    let on_v = c == 0 || c == N - 1;
    match (on_h, on_v) {
        (true, true) => CellClass::Corner,
        (true, false) | (false, true) => CellClass::Edge,
        _ => CellClass::Interior,
    }
}

#[inline]
fn piece_class(pr: &PieceRot) -> CellClass {
    let n_border = (pr.n == BORDER) as u32 + (pr.e == BORDER) as u32
        + (pr.s == BORDER) as u32 + (pr.w == BORDER) as u32;
    match n_border {
        2 => CellClass::Corner,
        1 => CellClass::Edge,
        0 => CellClass::Interior,
        _ => CellClass::Corner,
    }
}

#[inline]
fn class_matches(cc: CellClass, pc: CellClass) -> bool { cc == pc }

fn build_scan_order(mode: &str) -> Vec<usize> {
    match mode {
        "row" => (0..N_POS).collect(),
        "col" => {
            let mut o = Vec::with_capacity(N_POS);
            for c in 0..N {
                for r in 0..N {
                    o.push(r * N + c);
                }
            }
            o
        }
        "row_rev" => {
            let mut o = Vec::with_capacity(N_POS);
            for r in (0..N).rev() {
                for c in 0..N {
                    o.push(r * N + c);
                }
            }
            o
        }
        "col_rev" => {
            let mut o = Vec::with_capacity(N_POS);
            for c in (0..N).rev() {
                for r in 0..N {
                    o.push(r * N + c);
                }
            }
            o
        }
        "zigzag" => {
            let mut o = Vec::with_capacity(N_POS);
            for r in 0..N {
                if r % 2 == 0 {
                    for c in 0..N { o.push(r * N + c); }
                } else {
                    for c in (0..N).rev() { o.push(r * N + c); }
                }
            }
            o
        }
        "zigzag_rev" => {
            let mut o = Vec::with_capacity(N_POS);
            for r in (0..N).rev() {
                let phase = (N - 1 - r) % 2;
                if phase == 0 {
                    for c in 0..N { o.push(r * N + c); }
                } else {
                    for c in (0..N).rev() { o.push(r * N + c); }
                }
            }
            o
        }
        "spiral_in" => {
            // Spiral from outside in, starting top-left, going clockwise.
            let mut o = Vec::with_capacity(N_POS);
            let mut top = 0i32; let mut bot = (N - 1) as i32;
            let mut left = 0i32; let mut right = (N - 1) as i32;
            while top <= bot && left <= right {
                for c in left..=right { o.push((top as usize) * N + c as usize); }
                top += 1;
                for r in top..=bot { o.push((r as usize) * N + right as usize); }
                right -= 1;
                if top <= bot {
                    for c in (left..=right).rev() { o.push((bot as usize) * N + c as usize); }
                    bot -= 1;
                }
                if left <= right {
                    for r in (top..=bot).rev() { o.push((r as usize) * N + left as usize); }
                    left += 1;
                }
            }
            o
        }
        "spiral_out" => {
            // Same cells as spiral_in but reversed: from center to outside.
            let mut inward = build_scan_order("spiral_in");
            inward.reverse();
            inward
        }
        "diagonal" => {
            // Anti-diagonal scan: (r+c) constant per diagonal.
            let mut o = Vec::with_capacity(N_POS);
            for d in 0..(2 * N - 1) {
                for r in 0..N {
                    if d >= r && d - r < N {
                        o.push(r * N + (d - r));
                    }
                }
            }
            o
        }
        _ => panic!("unknown scan mode {mode}"),
    }
}

#[inline]
fn border_constraint(pos: usize) -> [bool; 4] {
    let r = pos_row(pos);
    let c = pos_col(pos);
    [r == 0, c == N - 1, r == N - 1, c == 0]
}

#[inline]
fn delta_score(
    pr: &PieceRot,
    pos: usize,
    chosen: &[u32],
    piece_rots: &[PieceRot],
) -> i32 {
    let r = pos_row(pos);
    let c = pos_col(pos);
    let mut d: i32 = 0;
    if r > 0 {
        let np = chosen[pos - N];
        if np != u32::MAX {
            let nb = piece_rots[np as usize];
            if pr.n == nb.s && pr.n != BORDER { d += 1; }
        }
    }
    if c < N - 1 {
        let np = chosen[pos + 1];
        if np != u32::MAX {
            let nb = piece_rots[np as usize];
            if pr.e == nb.w && pr.e != BORDER { d += 1; }
        }
    }
    if r < N - 1 {
        let np = chosen[pos + N];
        if np != u32::MAX {
            let nb = piece_rots[np as usize];
            if pr.s == nb.n && pr.s != BORDER { d += 1; }
        }
    }
    if c > 0 {
        let np = chosen[pos - 1];
        if np != u32::MAX {
            let nb = piece_rots[np as usize];
            if pr.w == nb.e && pr.w != BORDER { d += 1; }
        }
    }
    d
}

fn state_hash(used_mask: &[u64; 4], score: u32) -> u64 {
    let mut h: u64 = 0xcbf29ce484222325;
    for &m in used_mask {
        h ^= m;
        h = h.wrapping_mul(0x100000001b3);
    }
    h ^= score as u64;
    h = h.wrapping_mul(0x100000001b3);
    h
}

/// Seeded tiebreak comparator for two state-hashes. If seed==0, deterministic
/// (just compare hashes). If seed!=0, mix seed into each side and compare —
/// gives different orderings for different seeds.
fn seeded_tiebreak(a: u64, b: u64, seed: u64) -> std::cmp::Ordering {
    if seed == 0 {
        a.cmp(&b)
    } else {
        let ka = a.wrapping_mul(seed).wrapping_add(seed);
        let kb = b.wrapping_mul(seed).wrapping_add(seed);
        ka.cmp(&kb)
    }
}

fn path_hash(used_mask: &[u64; 4], chosen: &[u32], scan_order: &[usize], depth: usize, recent_k: usize) -> u64 {
    let mut h: u64 = 0xcbf29ce484222325;
    for &m in used_mask {
        h ^= m;
        h = h.wrapping_mul(0x100000001b3);
    }
    let lo = depth.saturating_sub(recent_k);
    for d in lo..depth {
        let pos = scan_order[d];
        h ^= chosen[pos] as u64;
        h = h.wrapping_mul(0x100000001b3);
    }
    h
}

/// V178 — pheromone delta when placing piece p at pos with current
/// neighbors. Pheromone matrix is τ[p1, p2, d] where d ∈ {0=N, 1=E, 2=S, 3=W}.
/// We add τ[neighbor_N, p, S] (from N-neighbor, p's south is below) and
/// τ[p, neighbor_E, W] etc. The matrix is symmetric in the sense that
/// the build script writes both (p1→p2,d) and (p2→p1,d_reverse).
#[inline]
fn pheromone_delta(
    pheromone: &[f64],
    pr: &PieceRot,
    pos: usize,
    chosen: &[u32],
    piece_rots: &[PieceRot],
) -> f64 {
    let r = pos_row(pos);
    let c = pos_col(pos);
    let p1 = pr.piece_id as usize;
    let mut s = 0.0f64;
    let idx = |p1: usize, p2: usize, d: usize| (p1 * N_PIECES + p2) * 4 + d;
    if r > 0 {
        let np = chosen[pos - N];
        if np != u32::MAX {
            let p2 = piece_rots[np as usize].piece_id as usize;
            // p2 is north of p1 — τ[p2, p1, S] (p2's south = p1)
            s += pheromone[idx(p2, p1, 2)];
        }
    }
    if c < N - 1 {
        let np = chosen[pos + 1];
        if np != u32::MAX {
            let p2 = piece_rots[np as usize].piece_id as usize;
            // p2 is east of p1 — τ[p1, p2, E]
            s += pheromone[idx(p1, p2, 1)];
        }
    }
    if r < N - 1 {
        let np = chosen[pos + N];
        if np != u32::MAX {
            let p2 = piece_rots[np as usize].piece_id as usize;
            // p2 is south of p1 — τ[p1, p2, S]
            s += pheromone[idx(p1, p2, 2)];
        }
    }
    if c > 0 {
        let np = chosen[pos - 1];
        if np != u32::MAX {
            let p2 = piece_rots[np as usize].piece_id as usize;
            // p2 is west of p1 — τ[p2, p1, E] (p2's east = p1)
            s += pheromone[idx(p2, p1, 1)];
        }
    }
    s
}

/// Load pheromone JSON {"data": flat list of N_PIECES²·4 floats}.
/// V181 — load patch prior JSON into a u64 → f32 HashMap.
fn load_patch_prior(path: &PathBuf) -> std::collections::HashMap<u64, f32> {
    let raw = std::fs::read_to_string(path).expect("read patch prior");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse patch prior");
    let patches = v["patches"].as_object().expect("patches object");
    let mut out = std::collections::HashMap::with_capacity(patches.len());
    for (k, val) in patches {
        let key: u64 = k.parse().expect("patch u64 key");
        let s = val["s"].as_f64().expect("patch score") as f32;
        out.insert(key, s);
    }
    out
}

/// V181 — compute patch key matching Python encoding (10 bits per cell × 4 cells).
/// Cells in order: TL, TR, BL, BR.
#[inline]
fn patch_key(tl_pid: u16, tl_rot: u8, tr_pid: u16, tr_rot: u8,
             bl_pid: u16, bl_rot: u8, br_pid: u16, br_rot: u8) -> u64 {
    let enc = |pid: u16, rot: u8| ((pid as u64) << 2) | (rot as u64);
    (enc(tl_pid, tl_rot) << 30) | (enc(tr_pid, tr_rot) << 20)
        | (enc(bl_pid, bl_rot) << 10) | enc(br_pid, br_rot)
}

/// V181 — compute patch contribution when placing pr at pos.
/// Up to 4 patches contain this cell (one per quadrant TL/TR/BL/BR position
/// of the 2x2 patch). For each, check if all 4 cells are placed; if yes,
/// look up patch score and accumulate.
#[inline]
fn patch_delta(
    patch_prior: &std::collections::HashMap<u64, f32>,
    pr: &PieceRot,
    pos: usize,
    chosen: &[u32],
    piece_rots: &[PieceRot],
) -> f64 {
    let r = pos_row(pos);
    let c = pos_col(pos);
    let mut s = 0.0f64;

    // Helper: get (pid, rot) at a position, or None if not placed.
    let get = |p: i32| -> Option<(u16, u8)> {
        if p < 0 || p >= (N_POS as i32) { return None; }
        let idx = chosen[p as usize];
        if idx == u32::MAX { return None; }
        let pr = piece_rots[idx as usize];
        Some((pr.piece_id, pr.rot))
    };

    // The placement is at (r, c) with pieces (pr.piece_id, pr.rot).
    // 4 candidate 2x2 patches contain (r, c):
    //   Patch A: (r-1, c-1) is TL, our cell is BR.
    //   Patch B: (r-1, c)   is TL, our cell is BL.
    //   Patch C: (r, c-1)   is TL, our cell is TR.
    //   Patch D: (r, c)     is TL, our cell is TL.

    // Patch A: TL=(r-1,c-1), TR=(r-1,c), BL=(r,c-1), BR=our
    if r >= 1 && c >= 1 {
        let tl = get((r as i32 - 1) * N as i32 + (c as i32 - 1));
        let tr = get((r as i32 - 1) * N as i32 + c as i32);
        let bl = get(r as i32 * N as i32 + (c as i32 - 1));
        if let (Some((tlp, tlr)), Some((trp, trr)), Some((blp, blr))) = (tl, tr, bl) {
            let key = patch_key(tlp, tlr, trp, trr, blp, blr, pr.piece_id, pr.rot);
            if let Some(&v) = patch_prior.get(&key) {
                s += v as f64;
            }
        }
    }
    // Patch B: TL=(r-1,c), TR=(r-1,c+1), BL=our, BR=(r,c+1)
    if r >= 1 && c + 1 < N {
        let tl = get((r as i32 - 1) * N as i32 + c as i32);
        let tr = get((r as i32 - 1) * N as i32 + (c as i32 + 1));
        let br = get(r as i32 * N as i32 + (c as i32 + 1));
        if let (Some((tlp, tlr)), Some((trp, trr)), Some((brp, brr))) = (tl, tr, br) {
            let key = patch_key(tlp, tlr, trp, trr, pr.piece_id, pr.rot, brp, brr);
            if let Some(&v) = patch_prior.get(&key) {
                s += v as f64;
            }
        }
    }
    // Patch C: TL=(r,c-1), TR=our, BL=(r+1,c-1), BR=(r+1,c)
    if r + 1 < N && c >= 1 {
        let tl = get(r as i32 * N as i32 + (c as i32 - 1));
        let bl = get((r as i32 + 1) * N as i32 + (c as i32 - 1));
        let br = get((r as i32 + 1) * N as i32 + c as i32);
        if let (Some((tlp, tlr)), Some((blp, blr)), Some((brp, brr))) = (tl, bl, br) {
            let key = patch_key(tlp, tlr, pr.piece_id, pr.rot, blp, blr, brp, brr);
            if let Some(&v) = patch_prior.get(&key) {
                s += v as f64;
            }
        }
    }
    // Patch D: TL=our, TR=(r,c+1), BL=(r+1,c), BR=(r+1,c+1)
    if r + 1 < N && c + 1 < N {
        let tr = get(r as i32 * N as i32 + (c as i32 + 1));
        let bl = get((r as i32 + 1) * N as i32 + c as i32);
        let br = get((r as i32 + 1) * N as i32 + (c as i32 + 1));
        if let (Some((trp, trr)), Some((blp, blr)), Some((brp, brr))) = (tr, bl, br) {
            let key = patch_key(pr.piece_id, pr.rot, trp, trr, blp, blr, brp, brr);
            if let Some(&v) = patch_prior.get(&key) {
                s += v as f64;
            }
        }
    }
    s
}

fn load_pheromone(path: &PathBuf) -> Vec<f64> {
    let raw = std::fs::read_to_string(path).expect("read pheromone");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse pheromone");
    let arr = v["data"].as_array().expect("pheromone.data array");
    let expected = N_PIECES * N_PIECES * 4;
    assert_eq!(arr.len(), expected, "pheromone length mismatch");
    arr.iter().map(|x| x.as_f64().expect("float")).collect()
}

/// Load prior matrix from JSON. Returns 256x256 array of (piece_id, pos) → count.
fn load_prior(path: &PathBuf) -> Vec<Vec<u32>> {
    let raw = std::fs::read_to_string(path).expect("read prior file");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse prior json");
    let m = v["matrix"].as_array().expect("matrix");
    let mut out: Vec<Vec<u32>> = Vec::with_capacity(N_PIECES);
    for row in m {
        let r = row.as_array().expect("row");
        let mut rv: Vec<u32> = Vec::with_capacity(N_POS);
        for cell in r {
            rv.push(cell.as_u64().expect("count") as u32);
        }
        out.push(rv);
    }
    out
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut prior_path: Option<PathBuf> = None;
    let mut beam_width: usize = 1024;
    let mut budget_ms: u64 = u64::MAX;
    let mut scan_mode: String = "row".into();
    let mut verbose = false;
    let mut dedup_path_flag = false;
    let mut dedup_recent_k: usize = 4;
    let mut prior_alpha: f64 = 0.0;  // weight of prior_sum in combined score
    let mut pheromone_path: Option<PathBuf> = None;
    let mut pheromone_weight: f64 = 0.0;
    let mut patch_path: Option<PathBuf> = None;
    let mut patch_weight: f64 = 0.0;
    let mut save_best_path: Option<PathBuf> = None;
    let mut tiebreak_seed: u64 = 0;  // 0 = deterministic; nonzero = randomized tiebreak
    // V171/V165 STOCHASTIC BEAM — sample K children from softmax(score + α·prior).
    // When > 0.0, replaces top-K deterministic with weighted random sampling
    // (Gumbel-top-K). This injects real diversity across seeds.
    let mut stochastic_temperature: f64 = 0.0;
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--prior-file" => { prior_path = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--beam-width" => { beam_width = raw[i + 1].parse().expect("beam-width"); i += 2; }
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget"); i += 2; }
            "--scan" => { scan_mode = raw[i + 1].clone(); i += 2; }
            "--dedup-path" => { dedup_path_flag = true; i += 1; }
            "--dedup-recent" => { dedup_recent_k = raw[i + 1].parse().expect("dedup-recent"); i += 2; }
            "--prior-alpha" => { prior_alpha = raw[i + 1].parse().expect("prior-alpha"); i += 2; }
            "--pheromone-file" => { pheromone_path = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--pheromone-weight" => { pheromone_weight = raw[i + 1].parse().expect("pheromone-weight"); i += 2; }
            "--patch-file" => { patch_path = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--patch-weight" => { patch_weight = raw[i + 1].parse().expect("patch-weight"); i += 2; }
            "--save-best" => { save_best_path = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--seed" => { tiebreak_seed = raw[i + 1].parse().expect("seed"); i += 2; }
            "--stochastic-temperature" => { stochastic_temperature = raw[i + 1].parse().expect("stochastic-temperature"); i += 2; }
            "--verbose" => { verbose = true; i += 1; }
            other => { eprintln!("unknown arg {other}"); std::process::exit(2); }
        }
    }

    let puzzle = load_puzzle(&puzzle_path).expect("load puzzle");
    assert_eq!(puzzle.width as usize, N);
    assert_eq!(puzzle.height as usize, N);

    let mut piece_rots: Vec<PieceRot> = Vec::with_capacity(N_PIECES * N_ROT);
    for pid in 0..N_PIECES as u16 {
        let p = puzzle.piece(pid).expect("piece");
        let base = p.edges.as_array();
        for r in 0..N_ROT as u8 {
            let rot = rotate_edges(base, r);
            piece_rots.push(PieceRot {
                piece_id: pid, rot: r,
                n: rot[0], e: rot[1], s: rot[2], w: rot[3],
            });
        }
    }

    let mut by_class: [Vec<u32>; 3] = [Vec::new(), Vec::new(), Vec::new()];
    for (i, pr) in piece_rots.iter().enumerate() {
        let cc = piece_class(pr);
        let idx = match cc {
            CellClass::Corner => 0,
            CellClass::Edge => 1,
            CellClass::Interior => 2,
        };
        by_class[idx].push(i as u32);
    }

    let scan_order = build_scan_order(&scan_mode);

    let prior: Option<Vec<Vec<u32>>> = prior_path.as_ref().map(|p| {
        eprintln!("[init] loading prior from {}", p.display());
        load_prior(p)
    });

    // V178 — load pheromone matrix (flat float vec, 256*256*4 entries).
    let pheromone: Option<Vec<f64>> = pheromone_path.as_ref().map(|p| {
        eprintln!("[init] loading pheromone from {}", p.display());
        load_pheromone(p)
    });
    if pheromone.is_some() {
        eprintln!("[init] pheromone weight λ = {}", pheromone_weight);
    }

    // V181 KEYRING — load patch prior (HashMap u64 → f32).
    let patch_prior: Option<std::collections::HashMap<u64, f32>> = patch_path.as_ref().map(|p| {
        eprintln!("[init] loading patch prior from {}", p.display());
        let h = load_patch_prior(p);
        eprintln!("[init] {} patches loaded, patch weight μ = {}", h.len(), patch_weight);
        h
    });

    eprintln!("[init] piece_rots: {}, by_class: corner={} edge={} interior={}",
        piece_rots.len(), by_class[0].len(), by_class[1].len(), by_class[2].len());
    eprintln!("[init] scan_mode: {} K={} prior={}", scan_mode, beam_width, prior.is_some());

    let t0 = Instant::now();
    let deadline = t0 + std::time::Duration::from_millis(budget_ms);

    let mut beam: Vec<BeamState> = vec![BeamState::new()];

    for depth in 0..N_POS {
        if Instant::now() >= deadline {
            eprintln!("[abort] budget at depth {depth}");
            break;
        }
        let pos = scan_order[depth];
        let cc = cell_class(pos);
        let class_idx = match cc {
            CellClass::Corner => 0,
            CellClass::Edge => 1,
            CellClass::Interior => 2,
        };
        let bc = border_constraint(pos);

        let mut children: Vec<BeamState> = Vec::with_capacity(beam.len() * 16);
        for state in &beam {
            for &pr_idx in &by_class[class_idx] {
                let pr = piece_rots[pr_idx as usize];
                if state.is_used(pr.piece_id) { continue; }
                if !class_matches(cc, piece_class(&pr)) { continue; }
                if bc[0] && pr.n != BORDER { continue; }
                if bc[1] && pr.e != BORDER { continue; }
                if bc[2] && pr.s != BORDER { continue; }
                if bc[3] && pr.w != BORDER { continue; }
                if !bc[0] && pr.n == BORDER { continue; }
                if !bc[1] && pr.e == BORDER { continue; }
                if !bc[2] && pr.s == BORDER { continue; }
                if !bc[3] && pr.w == BORDER { continue; }
                let d = delta_score(&pr, pos, &state.chosen, &piece_rots);
                let prior_inc = match &prior {
                    Some(p) => p[pr.piece_id as usize][pos],
                    None => 0,
                };
                let pher_inc = match &pheromone {
                    Some(p) => pheromone_delta(p, &pr, pos, &state.chosen, &piece_rots),
                    None => 0.0,
                };
                let patch_inc = match &patch_prior {
                    Some(pp) => patch_delta(pp, &pr, pos, &state.chosen, &piece_rots),
                    None => 0.0,
                };
                let mut child = state.clone();
                child.chosen[pos] = pr_idx;
                child.mark_used(pr.piece_id);
                child.score = state.score + d as u32;
                child.prior_sum = state.prior_sum + prior_inc;
                child.pheromone_sum = state.pheromone_sum + pher_inc;
                child.patch_sum = state.patch_sum + patch_inc;
                child.state_hash = if dedup_path_flag {
                    path_hash(&child.used_mask, &child.chosen, &scan_order, depth + 1, dedup_recent_k)
                } else {
                    state_hash(&child.used_mask, child.score)
                };
                children.push(child);
            }
        }

        if children.is_empty() {
            eprintln!("[dead-end] depth={depth} pos={pos} beam={}", beam.len());
            break;
        }

        // Sort: combined score = score + alpha * prior_sum / max_prior_norm.
        // Default alpha=0 → pure score with prior tiebreak. alpha>0 → blends.
        // We use integer arithmetic for stability: combined = score * 1000000 + alpha_int * prior_sum.
        // Tiebreak: if seed != 0, use seeded state_hash to randomize ties;
        // if seed == 0, deterministic (state_hash ordering).
        //
        // V171/V165 STOCHASTIC BEAM: if stochastic_temperature > 0, sort by
        // (combined_score / T) + Gumbel(0,1) noise. This is the standard
        // Gumbel-top-K trick: top-K under additive Gumbel noise = K-without-
        // replacement samples from softmax(score/T). Reproducible because
        // the Gumbel is seeded by (state_hash, tiebreak_seed).
        if stochastic_temperature > 0.0 {
            // Compute logit = (score + alpha·prior_sum) / T.
            let alpha = if prior_alpha > 0.0 { prior_alpha } else { 0.0 };
            let inv_t = 1.0 / stochastic_temperature;
            let mut keyed: Vec<(f64, BeamState)> = Vec::with_capacity(children.len());
            for c in children.drain(..) {
                let logit = (c.score as f64 + alpha * c.prior_sum as f64
                             + pheromone_weight * c.pheromone_sum
                             + patch_weight * c.patch_sum) * inv_t;
                // Seeded Gumbel: u ~ U(0,1) from (state_hash, seed), g = -log(-log(u))
                let h = c.state_hash
                    .wrapping_mul(0x9E37_79B9_7F4A_7C15)
                    .wrapping_add(tiebreak_seed.wrapping_mul(0xBF58_476D_1CE4_E5B9));
                let u = ((h >> 11) as f64) / ((1u64 << 53) as f64);
                let u = u.max(1.0e-300).min(1.0 - 1.0e-16);
                let g = -((-u.ln()).ln());
                let key = logit + g;
                keyed.push((key, c));
            }
            // Sort descending by perturbed key.
            keyed.sort_unstable_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
            children = keyed.into_iter().map(|(_, c)| c).collect();
        } else if pheromone_weight > 0.0 || prior_alpha > 0.0 || patch_weight > 0.0 {
            let alpha = prior_alpha;
            let lambda = pheromone_weight;
            let mu = patch_weight;
            // f64 combined key; sort by descending.
            let mut keyed: Vec<(f64, BeamState)> = Vec::with_capacity(children.len());
            for c in children.drain(..) {
                let key = c.score as f64 + alpha * c.prior_sum as f64
                          + lambda * c.pheromone_sum + mu * c.patch_sum;
                keyed.push((key, c));
            }
            keyed.sort_unstable_by(|a, b| {
                b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal)
                    .then(seeded_tiebreak(a.1.state_hash, b.1.state_hash, tiebreak_seed))
            });
            children = keyed.into_iter().map(|(_, c)| c).collect();
        } else {
            children.sort_unstable_by(|a, b| {
                b.score.cmp(&a.score)
                    .then(b.prior_sum.cmp(&a.prior_sum))
                    .then(seeded_tiebreak(a.state_hash, b.state_hash, tiebreak_seed))
            });
        }

        // Dedup + truncate.
        let mut seen: std::collections::HashSet<u64> = std::collections::HashSet::with_capacity(beam_width * 2);
        let mut deduped: Vec<BeamState> = Vec::with_capacity(beam_width);
        for c in children.into_iter() {
            if seen.insert(c.state_hash) {
                deduped.push(c);
                if deduped.len() >= beam_width { break; }
            }
        }
        beam = deduped;

        if verbose && depth % 32 == 0 {
            let top = beam.first().map(|s| s.score).unwrap_or(0);
            let bot = beam.last().map(|s| s.score).unwrap_or(0);
            eprintln!("[d={depth}] beam={} top={} bot={} ({}ms)",
                beam.len(), top, bot, t0.elapsed().as_millis());
        }
    }

    let elapsed = t0.elapsed();
    let best = beam.iter().max_by_key(|s| s.score);
    if let Some(b) = best {
        println!("{{\"profile\":\"v181_keyring\",\"scan\":\"{scan_mode}\",\"beam_width\":{beam_width},\"prior\":{},\"elapsed_ms\":{},\"beam_final\":{},\"best_score\":{}}}",
            prior.is_some(), elapsed.as_millis(), beam.len(), b.score);
        eprintln!("[stats] beam_final={} best={}", beam.len(), b.score);
        for (i, s) in beam.iter().take(10).enumerate() {
            eprintln!("  [{}] score={} prior_sum={}", i, s.score, s.prior_sum);
        }
        // Save best as JSON for ALNS feed (placement format compatible
        // with alns_only --cp-board).
        if let Some(path) = save_best_path {
            let mut placement_json = String::from("{\"placement\":[");
            for pos in 0..N_POS {
                if pos > 0 { placement_json.push(','); }
                if b.chosen[pos] == u32::MAX {
                    placement_json.push_str("null");
                } else {
                    let pr = piece_rots[b.chosen[pos] as usize];
                    placement_json.push_str(&format!(
                        "{{\"piece_id\":{},\"rotation\":{},\"pos\":{}}}",
                        pr.piece_id, pr.rot, pos
                    ));
                }
            }
            placement_json.push_str(&format!("], \"matched\":{}}}", b.score));
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent).ok();
            }
            std::fs::write(&path, &placement_json).expect("write save-best");
            eprintln!("[save-best] {} (score={})", path.display(), b.score);
        }
    } else {
        println!("{{\"profile\":\"v181_keyring\",\"elapsed_ms\":{},\"best_score\":0,\"error\":\"empty_beam\"}}",
            elapsed.as_millis());
    }
}
