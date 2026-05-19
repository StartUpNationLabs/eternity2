// V151 WEAVING-Beam — layered beam-search constructive builder.
//
// At each depth d (scan_order[d] = position), maintain top-K partial
// states. Expand each by all valid (piece, rot) candidates; prune to
// top-K by score.
//
// State representation:
//   chosen: [u32; 256] — piece_rot index per position (u32::MAX = unplaced).
//   used_mask: [u64; 4] — 256-bit bitmask of used pieces.
//   score: u32.
//
// Memory: K × (256*4 + 32 + 4) ≈ K * 1060 bytes. K=4096 → 4MB. Fine.
//
// Performance: per-depth work is K * |C| * 4-side-check + sort.
// K=1024 × |C|=200 × 4 ops × 256 depths ≈ 200M ops ≈ 1 sec in Rust.

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
    chosen: Vec<u32>,           // [u32; N_POS]; u32::MAX = unplaced
    used_mask: [u64; 4],         // 256-bit bitmask
    score: u32,
    /// Lightweight hash for dedup (combines used_mask + recent chosen).
    state_hash: u64,
}

impl BeamState {
    fn new() -> Self {
        Self {
            chosen: vec![u32::MAX; N_POS],
            used_mask: [0u64; 4],
            score: 0,
            state_hash: 0,
        }
    }
    #[inline]
    fn is_used(&self, pid: u16) -> bool {
        let pid = pid as usize;
        (self.used_mask[pid / 64] >> (pid % 64)) & 1 == 1
    }
    #[inline]
    fn mark_used(&mut self, pid: u16) {
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
fn class_matches(cc: CellClass, pc: CellClass) -> bool {
    cc == pc
}

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

/// Compute delta-score from placing pr at pos given the current board state in `chosen`.
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
    // N neighbour
    if r > 0 {
        let np = chosen[pos - N];
        if np != u32::MAX {
            let nb = piece_rots[np as usize];
            if pr.n == nb.s && pr.n != BORDER { d += 1; }
        }
    }
    // E neighbour
    if c < N - 1 {
        let np = chosen[pos + 1];
        if np != u32::MAX {
            let nb = piece_rots[np as usize];
            if pr.e == nb.w && pr.e != BORDER { d += 1; }
        }
    }
    // S neighbour
    if r < N - 1 {
        let np = chosen[pos + N];
        if np != u32::MAX {
            let nb = piece_rots[np as usize];
            if pr.s == nb.n && pr.s != BORDER { d += 1; }
        }
    }
    // W neighbour
    if c > 0 {
        let np = chosen[pos - 1];
        if np != u32::MAX {
            let nb = piece_rots[np as usize];
            if pr.w == nb.e && pr.w != BORDER { d += 1; }
        }
    }
    d
}

/// Hash for deduplication. Combines used_mask (so different used-piece sets
/// have different hashes) with the score bucket.
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

/// Path-aware hash. Combines used_mask with the last-K placements' piece-ids.
/// Helps maintain beam diversity even when many states share a high prefix.
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

/// 1-step lookahead score: given a candidate placement at depth d,
/// compute the best NEXT-cell delta and add it. This is cheaper than
/// full rollout (O(|C|) vs O(N-d)*|C|) and captures the most common
/// "row-end constraints next-row-start" coupling.
#[allow(dead_code)]
fn lookahead_1_score(
    state: &BeamState,
    next_depth: usize,
    scan_order: &[usize],
    piece_rots: &[PieceRot],
    by_class: &[Vec<u32>; 3],
) -> i32 {
    if next_depth >= N_POS { return 0; }
    let pos = scan_order[next_depth];
    let cc = cell_class(pos);
    let class_idx = match cc {
        CellClass::Corner => 0,
        CellClass::Edge => 1,
        CellClass::Interior => 2,
    };
    let bc = border_constraint(pos);
    let mut best = -1i32;
    for &pr_idx in &by_class[class_idx] {
        let pr = piece_rots[pr_idx as usize];
        let pid = pr.piece_id as usize;
        if (state.used_mask[pid / 64] >> (pid % 64)) & 1 == 1 { continue; }
        if !class_matches(cc, piece_class(&pr)) { continue; }
        if bc[0] && pr.n != BORDER { continue; }
        if bc[1] && pr.e != BORDER { continue; }
        if bc[2] && pr.s != BORDER { continue; }
        if bc[3] && pr.w != BORDER { continue; }
        if !bc[0] && pr.n == BORDER { continue; }
        if !bc[1] && pr.e == BORDER { continue; }
        if !bc[2] && pr.s == BORDER { continue; }
        if !bc[3] && pr.w == BORDER { continue; }
        let d = delta_score(&pr, pos, &state.chosen, piece_rots);
        if d > best { best = d; }
    }
    best.max(0)
}

/// Greedy rollout from a partial state to completion at depth 256.
/// Returns the final score reached. Used as a heuristic ranking signal
/// for beam-search ("value to go" rather than "value so far").
fn greedy_rollout(
    state: &BeamState,
    start_depth: usize,
    scan_order: &[usize],
    piece_rots: &[PieceRot],
    by_class: &[Vec<u32>; 3],
) -> u32 {
    let mut chosen = state.chosen.clone();
    let mut used_mask = state.used_mask;
    let mut score = state.score;
    for d in start_depth..N_POS {
        let pos = scan_order[d];
        let cc = cell_class(pos);
        let class_idx = match cc {
            CellClass::Corner => 0,
            CellClass::Edge => 1,
            CellClass::Interior => 2,
        };
        let bc = border_constraint(pos);
        let mut best: Option<(u32, i32)> = None;
        for &pr_idx in &by_class[class_idx] {
            let pr = piece_rots[pr_idx as usize];
            let pid = pr.piece_id as usize;
            if (used_mask[pid / 64] >> (pid % 64)) & 1 == 1 { continue; }
            if !class_matches(cc, piece_class(&pr)) { continue; }
            if bc[0] && pr.n != BORDER { continue; }
            if bc[1] && pr.e != BORDER { continue; }
            if bc[2] && pr.s != BORDER { continue; }
            if bc[3] && pr.w != BORDER { continue; }
            if !bc[0] && pr.n == BORDER { continue; }
            if !bc[1] && pr.e == BORDER { continue; }
            if !bc[2] && pr.s == BORDER { continue; }
            if !bc[3] && pr.w == BORDER { continue; }
            let delta = delta_score(&pr, pos, &chosen, piece_rots);
            match best {
                None => best = Some((pr_idx, delta)),
                Some((_, bd)) if delta > bd => best = Some((pr_idx, delta)),
                _ => {}
            }
        }
        if let Some((pr_idx, delta)) = best {
            chosen[pos] = pr_idx;
            let pid = piece_rots[pr_idx as usize].piece_id as usize;
            used_mask[pid / 64] |= 1u64 << (pid % 64);
            score = score.wrapping_add(delta as u32);
        }
        // else: cell skipped (rare).
    }
    score
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut beam_width: usize = 256;
    let mut budget_ms: u64 = u64::MAX;
    let mut scan_mode: String = "row".into();
    let mut verbose = false;
    let mut dedup = true;
    let mut dedup_path = false;
    let mut dedup_recent_k: usize = 4;
    let mut rollout = false;
    let mut rollout_freq: usize = 16;  // rollout every N depths
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--beam-width" => { beam_width = raw[i + 1].parse().expect("beam-width"); i += 2; }
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget"); i += 2; }
            "--scan" => { scan_mode = raw[i + 1].clone(); i += 2; }
            "--no-dedup" => { dedup = false; i += 1; }
            "--dedup-path" => { dedup_path = true; i += 1; }
            "--dedup-recent" => { dedup_recent_k = raw[i + 1].parse().expect("dedup-recent"); i += 2; }
            "--rollout" => { rollout = true; i += 1; }
            "--rollout-freq" => { rollout_freq = raw[i + 1].parse().expect("rollout-freq"); i += 2; }
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

    // Pre-index piece_rots by class for fast lookup per cell.
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

    eprintln!("[init] piece_rots: {}, by_class: corner={} edge={} interior={}",
        piece_rots.len(), by_class[0].len(), by_class[1].len(), by_class[2].len());
    eprintln!("[init] scan_mode: {} K={} dedup={}", scan_mode, beam_width, dedup);

    let t0 = Instant::now();
    let deadline = t0 + std::time::Duration::from_millis(budget_ms);

    // Initial beam: one empty state.
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

        // Generate children of each beam state at this position.
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
                let mut child = state.clone();
                child.chosen[pos] = pr_idx;
                child.mark_used(pr.piece_id);
                child.score = state.score + d as u32;
                // Path-aware hash: includes the LAST FEW placed-piece IDs in
                // the hash, so two states with same used-mask but different
                // recent path are distinguished. depth here = depth+1 after
                // this child placement.
                child.state_hash = if dedup_path {
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

        // If rollout enabled AND this depth is a rollout-freq boundary AND
        // the children list is large enough that rollout pruning helps:
        // rank by rollout score (current_score + estimated rollout-to-end).
        let use_rollout_here = rollout && (depth + 1) % rollout_freq == 0
            && children.len() > beam_width
            && depth + 1 < N_POS;
        if use_rollout_here {
            // Compute rollout score for each candidate. We use the SCORE at
            // rollout completion (not delta) as the ranking signal.
            // This is expensive: O(children * (N_POS - depth)).
            let mut scored: Vec<(u32, BeamState)> = children.into_iter().map(|c| {
                let rs = greedy_rollout(&c, depth + 1, &scan_order, &piece_rots, &by_class);
                (rs, c)
            }).collect();
            scored.sort_unstable_by(|a, b| b.0.cmp(&a.0));
            children = scored.into_iter().map(|(_, c)| c).collect();
        } else {
            // Sort by score descending.
            children.sort_unstable_by(|a, b| b.score.cmp(&a.score));
        }

        if dedup {
            let mut seen: std::collections::HashSet<u64> = std::collections::HashSet::with_capacity(beam_width * 2);
            let mut deduped: Vec<BeamState> = Vec::with_capacity(beam_width);
            for c in children.into_iter() {
                if seen.insert(c.state_hash) {
                    deduped.push(c);
                    if deduped.len() >= beam_width { break; }
                }
            }
            beam = deduped;
        } else {
            children.truncate(beam_width);
            beam = children;
        }

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
        println!("{{\"profile\":\"weaving_beam_v151\",\"scan\":\"{scan_mode}\",\"beam_width\":{beam_width},\"dedup\":{dedup},\"elapsed_ms\":{},\"beam_final\":{},\"best_score\":{}}}",
            elapsed.as_millis(), beam.len(), b.score);
        eprintln!("[stats] beam_final={} best={}", beam.len(), b.score);
        // Top of beam.
        let n_show = beam.len().min(10);
        for (i, s) in beam.iter().take(n_show).enumerate() {
            eprintln!("  [{}] score={}", i, s.score);
        }
    } else {
        println!("{{\"profile\":\"weaving_beam_v151\",\"elapsed_ms\":{},\"best_score\":0,\"error\":\"empty_beam\"}}",
            elapsed.as_millis());
    }
}
