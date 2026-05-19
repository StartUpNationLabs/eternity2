// V150 WEAVING — fast Rust port of the row-greedy / col-greedy
// constructive builder.
//
// Python PoC (scripts/v150_weaving/) scored 369-389/480 in 0.3s per
// board. Goal here: scale to 100k+ seeds, find the tail of the
// score distribution.
//
// Algorithm per build:
//   Given a scan_order (row-major or col-major), for each pos in order:
//     - Find piece+rotation in remaining inventory that satisfies the
//       cell's border constraints (mandatory zero sides at perimeter)
//       AND maximizes edge-match with placed neighbours.
//     - Mismatches are ALLOWED. We place SOMETHING at every cell.
//   Score the resulting complete board (matched-edges).

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_core::BORDER;
use eternity2_puzzle_io::load_puzzle;

/// Minimal xorshift64* PRNG; no external dep.
struct XorShift(u64);
impl XorShift {
    #[inline]
    fn new(seed: u64) -> Self { Self(seed.wrapping_add(0x9E3779B97F4A7C15)) }
    #[inline]
    fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x.wrapping_mul(0x2545F4914F6CDD1D)
    }
    #[inline]
    fn gen_range(&mut self, bound: usize) -> usize {
        (self.next_u64() as usize) % bound.max(1)
    }
}

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

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    let mut out = [0u8; 4];
    for i in 0..4 {
        out[i] = e[(i + 4 - (r as usize)) % 4];
    }
    out
}

#[inline] fn pos_row(pos: usize) -> usize { pos / N }
#[inline] fn pos_col(pos: usize) -> usize { pos % N }

#[derive(Clone, Copy)]
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
        _ => CellClass::Corner, // 3+ border sides shouldn't happen on canonical
    }
}

#[inline]
fn class_matches(cc: CellClass, pc: CellClass) -> bool {
    matches!((cc, pc),
        (CellClass::Corner, CellClass::Corner) |
        (CellClass::Edge, CellClass::Edge) |
        (CellClass::Interior, CellClass::Interior)
    )
}

/// Build a list of (n_color_needed, e_color_needed, s_color_needed, w_color_needed)
/// per cell, where `BORDER` means OOB-must-border, and `u8::MAX` means free.
/// We rebuild this incrementally during DFS.
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

/// Mandatory border sides at pos. Returns (n_border, e_border, s_border, w_border).
#[inline]
fn border_constraint(pos: usize) -> [bool; 4] {
    let r = pos_row(pos);
    let c = pos_col(pos);
    [r == 0, c == N - 1, r == N - 1, c == 0]
}

/// Score a complete board (matched-edges).
fn score_board(board: &[Option<usize>], piece_rots: &[PieceRot]) -> u32 {
    let mut matched = 0u32;
    for r in 0..N {
        for c in 0..N {
            let pos = r * N + c;
            let cell = match board[pos] {
                Some(idx) => piece_rots[idx],
                None => continue,
            };
            if c < N - 1 {
                if let Some(idx) = board[pos + 1] {
                    let nb = piece_rots[idx];
                    if cell.e == nb.w && cell.e != BORDER {
                        matched += 1;
                    }
                }
            }
            if r < N - 1 {
                if let Some(idx) = board[pos + N] {
                    let nb = piece_rots[idx];
                    if cell.s == nb.n && cell.s != BORDER {
                        matched += 1;
                    }
                }
            }
        }
    }
    matched
}

/// Single constructive build. Returns (board, score).
fn build_one(
    piece_rots: &[PieceRot],
    pieces_by_class: &[Vec<u32>; 3],  // [corner, edge, interior] → piece_rot indices
    scan_order: &[usize],
    rng: &mut XorShift,
) -> (Vec<Option<usize>>, u32) {
    let mut board: Vec<Option<usize>> = vec![None; N_POS];
    let mut used = vec![false; N_PIECES];

    // For each cell, iterate candidates in shuffled order, pick the
    // one with most matched edges to placed neighbours.
    for &pos in scan_order {
        let cc = cell_class(pos);
        let class_idx = match cc {
            CellClass::Corner => 0,
            CellClass::Edge => 1,
            CellClass::Interior => 2,
        };
        let bc = border_constraint(pos);

        // Read neighbour constraints (color or None).
        let r = pos_row(pos);
        let c = pos_col(pos);
        let n_c = if r > 0 { board[pos - N].map(|idx| piece_rots[idx].s) } else { None };
        let e_c = if c < N - 1 { board[pos + 1].map(|idx| piece_rots[idx].w) } else { None };
        let s_c = if r < N - 1 { board[pos + N].map(|idx| piece_rots[idx].n) } else { None };
        let w_c = if c > 0 { board[pos - 1].map(|idx| piece_rots[idx].e) } else { None };

        let mut best_idx: u32 = u32::MAX;
        let mut best_matches: i32 = -1;

        // Shuffle candidates for randomized tiebreaks (Fisher-Yates).
        let mut cands = pieces_by_class[class_idx].clone();
        for i in (1..cands.len()).rev() {
            let j = rng.gen_range(i + 1);
            cands.swap(i, j);
        }

        for &pr_idx in &cands {
            let pr = piece_rots[pr_idx as usize];
            if used[pr.piece_id as usize] { continue; }
            if !class_matches(cc, piece_class(&pr)) { continue; }
            // Border-side constraints.
            if bc[0] && pr.n != BORDER { continue; }
            if bc[1] && pr.e != BORDER { continue; }
            if bc[2] && pr.s != BORDER { continue; }
            if bc[3] && pr.w != BORDER { continue; }
            // Non-border sides must NOT be border.
            if !bc[0] && pr.n == BORDER { continue; }
            if !bc[1] && pr.e == BORDER { continue; }
            if !bc[2] && pr.s == BORDER { continue; }
            if !bc[3] && pr.w == BORDER { continue; }
            // Count matches with placed neighbours.
            let mut m: i32 = 0;
            if let Some(nc) = n_c { if pr.n == nc && pr.n != BORDER { m += 1; } }
            if let Some(ec) = e_c { if pr.e == ec && pr.e != BORDER { m += 1; } }
            if let Some(sc) = s_c { if pr.s == sc && pr.s != BORDER { m += 1; } }
            if let Some(wc) = w_c { if pr.w == wc && pr.w != BORDER { m += 1; } }
            if m > best_matches {
                best_matches = m;
                best_idx = pr_idx;
            }
        }

        if best_idx != u32::MAX {
            board[pos] = Some(best_idx as usize);
            used[piece_rots[best_idx as usize].piece_id as usize] = true;
        }
        // else: cell remains None (rare in practice; corner-class constraint always feasible).
    }

    let s = score_board(&board, piece_rots);
    (board, s)
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut n_seeds: u64 = 10_000;
    let mut budget_ms: u64 = u64::MAX;
    let mut scan_mode: String = "row".into();
    let mut verbose = false;
    let mut min_score_report: u32 = 380;
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--n-seeds" => { n_seeds = raw[i + 1].parse().expect("n-seeds"); i += 2; }
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget"); i += 2; }
            "--scan" => { scan_mode = raw[i + 1].clone(); i += 2; }
            "--min-report" => { min_score_report = raw[i + 1].parse().expect("min-report"); i += 2; }
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

    // Index piece_rots by class.
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
    eprintln!("[init] scan_mode: {} ({} positions)", scan_mode, scan_order.len());
    eprintln!("[init] n_seeds: {}, budget_ms: {}", n_seeds, budget_ms);

    let t0 = Instant::now();
    let deadline = t0 + std::time::Duration::from_millis(budget_ms);

    let mut best_score: u32 = 0;
    let mut best_seed: u64 = 0;
    // Histogram bucket: 0-479 score.
    let mut hist: Vec<u64> = vec![0; 481];
    let mut n_built: u64 = 0;
    let mut sum_score: u64 = 0;

    let report_interval: u64 = 5000;

    for seed in 0..n_seeds {
        if Instant::now() >= deadline { break; }
        let mut rng = XorShift::new(seed);
        let (_board, s) = build_one(&piece_rots, &by_class, &scan_order, &mut rng);
        hist[s as usize] += 1;
        sum_score += s as u64;
        n_built += 1;
        if s > best_score {
            best_score = s;
            best_seed = seed;
            eprintln!("[best] seed={seed} score={s} ({}ms)", t0.elapsed().as_millis());
        }
        if verbose && s >= min_score_report {
            eprintln!("[hi] seed={seed} score={s}");
        }
        if n_built % report_interval == 0 {
            let elapsed_ms = t0.elapsed().as_millis() as u64;
            let rate = (n_built as f64) / (elapsed_ms as f64 / 1000.0);
            eprintln!("[progress] n={n_built} avg={} best={} rate={:.0} boards/s ({}ms)",
                sum_score / n_built.max(1), best_score, rate, elapsed_ms);
        }
    }

    let elapsed = t0.elapsed();
    let rate = (n_built as f64) / elapsed.as_secs_f64();
    let avg = sum_score as f64 / n_built.max(1) as f64;

    println!("{{\"profile\":\"weaving_v150\",\"scan\":\"{scan_mode}\",\"n_built\":{n_built},\"elapsed_ms\":{},\"boards_per_sec\":{:.0},\"avg_score\":{:.1},\"best_score\":{best_score},\"best_seed\":{best_seed}}}",
        elapsed.as_millis(), rate, avg);

    eprintln!("[histogram] top of distribution:");
    for s in (best_score.saturating_sub(20)..=best_score).rev() {
        if hist[s as usize] > 0 {
            eprintln!("  score={s}: {} boards", hist[s as usize]);
        }
    }
    let median_idx = n_built / 2;
    let mut cum: u64 = 0;
    let mut median: u32 = 0;
    for (s, &c) in hist.iter().enumerate() {
        cum += c;
        if cum >= median_idx {
            median = s as u32;
            break;
        }
    }
    eprintln!("[stats] avg={:.1} median={} max={}", avg, median, best_score);
}
