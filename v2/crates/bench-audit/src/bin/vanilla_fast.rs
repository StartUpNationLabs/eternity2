// Vol-32+ PoC — vanilla fast backtracker for E2 (no propagators, no ML).
// Row-major scan, dense arrays, pre-bucketed candidates by (north, west) edge pair.
// Goal: measure placements/sec; community benchmarks 97M-140M.
//
// Schema:
//   - rot_edges[piece_id][rot] = (N, E, S, W) in our color encoding
//   - cell_class[pos] = Corner|Edge|Interior (determines which pieces can go there)
//   - bucket[(class, N_required, W_required)] = list of (piece_id, rot) candidates
//   - placed[256] = Option<(piece, rot)>
//   - used[256] = bool
//   - At each cell, look up the (class, N_required, W_required) bucket and try each
//     un-used candidate.
//
// Run:
//   target/release/vanilla-fast --budget-ms 10000 --puzzle ../data/puzzles/size_16_official_eternity.csv

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Color, BORDER};

const N: usize = 16;
const N_POS: usize = N * N;
const N_PIECES: usize = 256;
const N_ROT: usize = 4;
const N_COLORS: usize = 23;  // 0=border, 1..22 interior

#[derive(Copy, Clone)]
struct PieceRot {
    piece_id: u16,
    rot: u8,
    n: u8,  // north edge
    e: u8,  // east edge
    s: u8,  // south edge
    w: u8,  // west edge
}

#[inline(always)]
fn pos_class(pos: usize) -> u8 {
    let y = pos / N;
    let x = pos % N;
    let top = y == 0;
    let bot = y == N - 1;
    let left = x == 0;
    let right = x == N - 1;
    let on_border = top || bot || left || right;
    let on_corner = (top || bot) && (left || right);
    if on_corner { 0 }       // corner
    else if on_border { 1 }  // edge
    else { 2 }               // interior
}

#[inline(always)]
fn need_north_border(pos: usize) -> bool {
    pos < N
}
#[inline(always)]
fn need_west_border(pos: usize) -> bool {
    pos % N == 0
}
#[inline(always)]
fn need_south_border(pos: usize) -> bool {
    pos >= N_POS - N
}
#[inline(always)]
fn need_east_border(pos: usize) -> bool {
    pos % N == N - 1
}

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    // CSV stores [top, right, bottom, left]
    // Rotation r: r=0 unchanged. r=1 turns 90° clockwise; what was top becomes right.
    // To get the new (top, right, bottom, left), we read the original with offset -r.
    let mut out = [0u8; 4];
    let mut i = 0;
    while i < 4 {
        out[i] = e[(i + 4 - (r as usize)) % 4];
        i += 1;
    }
    out
}

fn main() {
    let mut budget_ms: u64 = 10_000;
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut want_solve = false;
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget"); i += 2; }
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--solve" => { want_solve = true; i += 1; }
            other => panic!("unknown arg: {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    assert_eq!(puzzle.width as usize, N);
    assert_eq!(puzzle.height as usize, N);

    // Build per-piece rotation tables.
    let mut piece_rots: Vec<PieceRot> = Vec::with_capacity(N_PIECES * N_ROT);
    for pid in 0..N_PIECES as u16 {
        let p = puzzle.piece(pid).expect("piece");
        let base = p.edges.as_array();  // [top, right, bottom, left]
        for r in 0..N_ROT as u8 {
            let rotated = rotate_edges(base, r);
            piece_rots.push(PieceRot {
                piece_id: pid,
                rot: r,
                n: rotated[0],
                e: rotated[1],
                s: rotated[2],
                w: rotated[3],
            });
        }
    }

    // Bucket: (class, N_required_color, W_required_color) → list of indices into piece_rots
    // class ∈ {0=corner, 1=edge, 2=interior}
    // colors 0..22; we use 23 slots.
    // For corners: both N and W borders required (uniquely determined by class+pos), so bucket key = (0, 0, 0) suffices? No — corner positions can be TR (W not border) or BL (N not border). Use a 4-class scheme: corner-TL, corner-TR, corner-BL, corner-BR. Or compute on the fly.
    //
    // Simpler: per position, list of (piece_idx) compatible by class + border-requirements.
    // For interior cells, the bucket is keyed by (N_color_needed, W_color_needed) where
    // both come from already-placed neighbours. So bucketing is needed.
    //
    // We'll do TWO levels:
    //  - class_compatible[pos] = candidate piece_rot indices satisfying class+border constraints.
    //  - bucket_by_NW[(N_color, W_color)] = candidate piece_rot indices (any class).
    //    Then intersect at runtime by iterating bucket and filtering by class_compatible flag.
    //
    // Actually cleanest: build bucket_by_class_N_W: [3][23][23] -> Vec<u16>, where each
    // bucket contains pre-filtered indices that satisfy the class's border constraints
    // AND the required N, W edges.

    // class_border_compat[piece_rot_idx][class] = bool
    // Per class, the (north, west) border requirements:
    //  class 0 corner: 4 sub-types depending on which 2 borders meet — handled per-pos
    //  class 1 edge: exactly one side must be BORDER (north for top edge, south for bottom edge, east for right edge, west for left edge)
    //  class 2 interior: NO side may be BORDER
    //
    // For simplicity: bucket per POSITION, not per class — 256 buckets total but each
    // is shared via key lookup. We'll use a per-position cache instead.

    // Pre-compute per-position the set of (piece_idx) that satisfy the BORDER constraint
    // (regardless of neighbour matching).
    let n_prots = piece_rots.len();
    let mut pos_border_ok: Vec<Vec<u16>> = vec![Vec::new(); N_POS];
    for pos in 0..N_POS {
        let need_n_border = need_north_border(pos);
        let need_e_border = need_east_border(pos);
        let need_s_border = need_south_border(pos);
        let need_w_border = need_west_border(pos);
        for (idx, pr) in piece_rots.iter().enumerate() {
            let n_is_border = pr.n == BORDER;
            let e_is_border = pr.e == BORDER;
            let s_is_border = pr.s == BORDER;
            let w_is_border = pr.w == BORDER;
            if n_is_border != need_n_border { continue; }
            if e_is_border != need_e_border { continue; }
            if s_is_border != need_s_border { continue; }
            if w_is_border != need_w_border { continue; }
            pos_border_ok[pos].push(idx as u16);
        }
    }

    eprintln!("[init] piece_rots: {}, total candidate edges by position:", n_prots);
    let mut total = 0usize;
    for pos in 0..N_POS {
        total += pos_border_ok[pos].len();
    }
    let avg = total as f64 / N_POS as f64;
    eprintln!("[init] avg candidates/pos (border-only): {:.1}, total = {}", avg, total);

    // Pre-bucket: for each pos, group candidates by (N_color, W_color).
    // bucket[pos][n*N_COLORS + w] = Vec<piece_rot_idx>
    let mut bucket: Vec<Vec<Vec<u16>>> = (0..N_POS)
        .map(|_| vec![Vec::new(); N_COLORS * N_COLORS])
        .collect();
    for pos in 0..N_POS {
        for &pr_idx in &pos_border_ok[pos] {
            let pr = piece_rots[pr_idx as usize];
            let key = (pr.n as usize) * N_COLORS + (pr.w as usize);
            bucket[pos][key].push(pr_idx);
        }
    }
    let mut total_bucketed = 0usize;
    let mut max_bucket = 0usize;
    for pos in 0..N_POS {
        for b in &bucket[pos] {
            total_bucketed += b.len();
            if b.len() > max_bucket { max_bucket = b.len(); }
        }
    }
    eprintln!("[init] bucketed entries: {}, max bucket size: {}", total_bucketed, max_bucket);

    // Scan order: row-major (pos 0..N_POS)
    // At each cell:
    //   - if cell > 0 and same-row neighbour to left: N_color is from above (pos-N).s, W_color is from (pos-1).e
    //   - if cell on top row: N_color = BORDER
    //   - if cell at left edge: W_color = BORDER

    // Run depth-counting backtracker until budget expires.
    let mut placed: [Option<usize>; N_POS] = [None; N_POS];  // stores piece_rot_idx
    let mut used: [bool; N_PIECES] = [false; N_PIECES];

    let t0 = Instant::now();
    let deadline = t0 + std::time::Duration::from_millis(budget_ms);

    // Stats
    let mut total_placements: u64 = 0;
    let mut total_backtracks: u64 = 0;
    let mut max_depth: u32 = 0;
    let mut solved_count: u64 = 0;

    // Iterative DFS: stack-tracked state, each frame = (pos, iter index into candidates)
    // Frames track current candidate cursor at each depth.
    let mut frame_cursor: [usize; N_POS + 1] = [0; N_POS + 1];

    let mut depth: usize = 0;
    'outer: loop {
        if depth == N_POS {
            // Solved!
            solved_count += 1;
            if want_solve {
                eprintln!("[solve] FOUND in {} ms", t0.elapsed().as_millis());
                break;
            }
            // Just backtrack and continue counting
            depth -= 1;
            let prev_idx = placed[depth].unwrap();
            used[piece_rots[prev_idx].piece_id as usize] = false;
            placed[depth] = None;
            frame_cursor[depth] += 1;
            continue;
        }
        // Check budget
        if (total_placements & 0xFFFF) == 0 && Instant::now() >= deadline {
            break;
        }

        let pos = depth;
        let n_color = if pos < N {
            BORDER
        } else {
            // north neighbour
            let np = pos - N;
            let p_idx = placed[np].unwrap();
            piece_rots[p_idx].s
        };
        let w_color = if pos % N == 0 {
            BORDER
        } else {
            let np = pos - 1;
            let p_idx = placed[np].unwrap();
            piece_rots[p_idx].e
        };

        // Direct bucket lookup
        let key = (n_color as usize) * N_COLORS + (w_color as usize);
        let candidates = &bucket[pos][key];
        let mut cur = frame_cursor[depth];
        let mut found = None;
        while cur < candidates.len() {
            let pr_idx = candidates[cur] as usize;
            let pr = piece_rots[pr_idx];
            if used[pr.piece_id as usize] {
                cur += 1;
                continue;
            }
            found = Some((pr_idx, cur));
            break;
        }
        match found {
            Some((pr_idx, cur)) => {
                placed[depth] = Some(pr_idx);
                used[piece_rots[pr_idx].piece_id as usize] = true;
                frame_cursor[depth] = cur;
                total_placements += 1;
                depth += 1;
                if (depth as u32) > max_depth {
                    max_depth = depth as u32;
                }
                if depth < N_POS + 1 {
                    frame_cursor[depth] = 0;
                }
            }
            None => {
                if depth == 0 {
                    break 'outer;
                }
                depth -= 1;
                total_backtracks += 1;
                let prev_idx = placed[depth].unwrap();
                used[piece_rots[prev_idx].piece_id as usize] = false;
                placed[depth] = None;
                frame_cursor[depth] += 1;
            }
        }
    }

    let elapsed = t0.elapsed();
    let elapsed_s = elapsed.as_secs_f64();
    let placements_per_sec = (total_placements as f64) / elapsed_s;
    let backtracks_per_sec = (total_backtracks as f64) / elapsed_s;

    println!(
        "{{\"profile\":\"vanilla_fast\",\"budget_ms\":{budget_ms},\"elapsed_ms\":{},\"placements\":{},\"backtracks\":{},\"max_depth\":{},\"solved\":{},\"placements_per_sec\":{:.0},\"backtracks_per_sec\":{:.0}}}",
        elapsed.as_millis(),
        total_placements,
        total_backtracks,
        max_depth,
        solved_count,
        placements_per_sec,
        backtracks_per_sec,
    );
}
