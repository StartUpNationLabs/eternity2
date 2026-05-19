// V155 WEAVING-PRIOR — beam search with empirical-frequency prior.
//
// Fork of v151_weaving_beam. The only change: when sorting children
// at each depth, ties on score are broken by prior(piece_id, position)
// — the frequency that piece appears at that cell in high-score DB
// boards. Loaded from --prior-file <path>.
//
// Pure from-scratch (doesn't anchor on any single board). The corpus
// distribution informs WHICH piece to try first when scores tie.

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
    state_hash: u64,
}

impl BeamState {
    fn new() -> Self {
        Self {
            chosen: vec![u32::MAX; N_POS],
            used_mask: [0u64; 4],
            score: 0,
            prior_sum: 0,
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
    let mut save_best_path: Option<PathBuf> = None;
    let mut tiebreak_seed: u64 = 0;  // 0 = deterministic; nonzero = randomized tiebreak
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
            "--save-best" => { save_best_path = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--seed" => { tiebreak_seed = raw[i + 1].parse().expect("seed"); i += 2; }
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
                let mut child = state.clone();
                child.chosen[pos] = pr_idx;
                child.mark_used(pr.piece_id);
                child.score = state.score + d as u32;
                child.prior_sum = state.prior_sum + prior_inc;
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
        if prior_alpha > 0.0 {
            let alpha_int = (prior_alpha * 1000.0) as i64;
            children.sort_unstable_by(|a, b| {
                let ka = (a.score as i64) * 1_000_000 + alpha_int * (a.prior_sum as i64);
                let kb = (b.score as i64) * 1_000_000 + alpha_int * (b.prior_sum as i64);
                kb.cmp(&ka).then(seeded_tiebreak(a.state_hash, b.state_hash, tiebreak_seed))
            });
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
        println!("{{\"profile\":\"weaving_prior_v155\",\"scan\":\"{scan_mode}\",\"beam_width\":{beam_width},\"prior\":{},\"elapsed_ms\":{},\"beam_final\":{},\"best_score\":{}}}",
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
        println!("{{\"profile\":\"weaving_prior_v155\",\"elapsed_ms\":{},\"best_score\":0,\"error\":\"empty_beam\"}}",
            elapsed.as_millis());
    }
}
