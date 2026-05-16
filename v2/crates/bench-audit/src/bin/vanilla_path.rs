// Vol-36 T1 — raw-DFS backtracker with custom cell-visit path.
//
// vanilla_fast is hardcoded row-major (n_color = chosen[pos-N], w_color =
// chosen[pos-1]). For path-based search we need to handle that any of the
// 4 NESW neighbours may or may not be placed when we visit a cell. The
// constraint pattern is path-determined, not row/col-determined.
//
// Design:
// - Path is a Vec<u16> of length 256, permutation of 0..256.
// - For each path-step d, pre-compute the bitmask of which neighbours
//   come BEFORE d in the path (N=1, E=2, S=4, W=8 → pattern[d] ∈ 0..16).
// - For each step, bucket candidates by the constrained colors only.
//   Bucket count = 23^popcount(pattern[d]). Border-need is fixed per cell.
//
// Hot loop mirrors vanilla_fast. No snapshot infra (keep simple).
//
// Built-in paths:
//   --path-mode row-major          (matches vanilla_fast)
//   --path-mode hint-link          (5 hints connected by shortest paths,
//                                  then centre-out spiral, then border ring)

#![forbid(unsafe_code)]

use std::collections::{HashSet, VecDeque};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, PieceId, Rotation, BORDER};
use rayon::prelude::*;

const N: usize = 16;
const N_POS: usize = N * N;
const N_PIECES: usize = 256;
const N_ROT: usize = 4;
const N_COLORS: usize = 23;

// NESW constraint flags: 1=N, 2=E, 4=S, 8=W
const F_N: u8 = 1;
const F_E: u8 = 2;
const F_S: u8 = 4;
const F_W: u8 = 8;

#[inline(always)]
fn pos_xy(pos: usize) -> (i32, i32) {
    ((pos % N) as i32, (pos / N) as i32)
}
#[inline(always)]
fn xy_pos(x: i32, y: i32) -> usize {
    (y * N as i32 + x) as usize
}
#[inline(always)]
fn in_bounds(x: i32, y: i32) -> bool {
    x >= 0 && x < N as i32 && y >= 0 && y < N as i32
}

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    let mut out = [0u8; 4];
    let mut i = 0;
    while i < 4 {
        out[i] = e[(i + 4 - (r as usize)) % 4];
        i += 1;
    }
    out
}

// Borders fixed by position (independent of path order).
#[inline(always)]
fn need_n_border(pos: usize) -> bool { pos < N }
#[inline(always)]
fn need_w_border(pos: usize) -> bool { pos % N == 0 }
#[inline(always)]
fn need_s_border(pos: usize) -> bool { pos >= N_POS - N }
#[inline(always)]
fn need_e_border(pos: usize) -> bool { pos % N == N - 1 }

#[derive(Copy, Clone)]
struct PieceRot {
    piece_id: u16,
    rot: u8,
    n: u8, e: u8, s: u8, w: u8,
}

/// Append unique positions from a candidate iterator, BFS-style.
fn push_unique(out: &mut Vec<usize>, seen: &mut HashSet<usize>, p: usize) {
    if seen.insert(p) {
        out.push(p);
    }
}

/// Shortest-grid-path (Manhattan, 4-connected, in_bounds) from a to b.
/// Returns the positions along the path EXCLUDING a (caller already added a).
fn grid_path_excl_start(a: usize, b: usize) -> Vec<usize> {
    let (ax, ay) = pos_xy(a);
    let (bx, by) = pos_xy(b);
    let mut prev: Vec<i32> = vec![-1; N_POS];
    let mut visited = vec![false; N_POS];
    visited[a] = true;
    let mut q: VecDeque<usize> = VecDeque::new();
    q.push_back(a);
    while let Some(c) = q.pop_front() {
        if c == b { break; }
        let (cx, cy) = pos_xy(c);
        for (dx, dy) in [(-1, 0), (1, 0), (0, -1), (0, 1)] {
            let nx = cx + dx;
            let ny = cy + dy;
            if !in_bounds(nx, ny) { continue; }
            let np = xy_pos(nx, ny);
            if visited[np] { continue; }
            visited[np] = true;
            prev[np] = c as i32;
            q.push_back(np);
        }
    }
    if !visited[b] { return Vec::new(); }
    let _ = (ax, ay, bx, by);
    let mut rev: Vec<usize> = Vec::new();
    let mut cur = b;
    while cur != a {
        rev.push(cur);
        cur = prev[cur] as usize;
    }
    rev.reverse();
    rev
}

/// Build the hint-link path: visit 5 canonical hint positions in fixed
/// order, connected by shortest grid paths. Then fill interior (centre-out
/// spiral). Then border ring.
fn build_hint_link_path(hint_positions: &[usize]) -> Vec<usize> {
    let mut path: Vec<usize> = Vec::new();
    let mut seen: HashSet<usize> = HashSet::new();
    // Order hints by their natural sequence on the canonical 16x16 puzzle.
    // E2 hints (typical 5-clue): pos 34, 45, 135, 210, 221.
    // We use the actual provided list in the order given.
    if let Some(&first) = hint_positions.first() {
        push_unique(&mut path, &mut seen, first);
    }
    for w in hint_positions.windows(2) {
        let a = w[0];
        let b = w[1];
        for p in grid_path_excl_start(a, b) {
            push_unique(&mut path, &mut seen, p);
        }
    }
    // Centre-out spiral for the interior (skip already-seen).
    // Walk outward from the geometric centre by increasing Chebyshev distance.
    let cx = (N / 2) as i32 - 1; // 7
    let cy = (N / 2) as i32 - 1; // 7
    for radius in 0..N as i32 {
        for dx in -radius..=radius {
            for dy in -radius..=radius {
                if dx.abs().max(dy.abs()) != radius { continue; }
                let x = cx + dx;
                let y = cy + dy;
                if !in_bounds(x, y) { continue; }
                push_unique(&mut path, &mut seen, xy_pos(x, y));
            }
        }
    }
    assert_eq!(path.len(), N_POS, "hint-link path must cover all 256 positions");
    path
}

fn build_row_major_path() -> Vec<usize> {
    (0..N_POS).collect()
}

/// "border-then-hints" — border ring (56 cells), then 5 hint positions
/// + their immediate neighbours (so hint pieces land at hint positions
/// before drifting), then row-major remaining interior.
/// CANONICAL-RESPECTING variant of border-first.
fn build_border_then_hints_path(hint_positions: &[usize]) -> Vec<usize> {
    let mut path: Vec<usize> = Vec::new();
    let mut seen: HashSet<usize> = HashSet::new();
    // Phase 1: border ring (top, right, bottom, left)
    for x in 0..N { push_unique(&mut path, &mut seen, xy_pos(x as i32, 0)); }
    for y in 1..N { push_unique(&mut path, &mut seen, xy_pos(N as i32 - 1, y as i32)); }
    for x in (0..(N - 1)).rev() { push_unique(&mut path, &mut seen, xy_pos(x as i32, N as i32 - 1)); }
    for y in (1..(N - 1)).rev() { push_unique(&mut path, &mut seen, xy_pos(0, y as i32)); }
    // Phase 2: visit hint positions early. To ensure each hint position
    // has at least one already-placed neighbour, connect via shortest grid
    // path from the border ring; cells visited along the way are placed too.
    // Simplest deterministic version: bridge from the nearest already-placed
    // cell to each hint, in order of the hint list, picking the shortest
    // route each time.
    for &h in hint_positions {
        // Find closest already-placed cell to h
        let (hx, hy) = pos_xy(h);
        let mut best: Option<(usize, i32)> = None;
        for (i, &p) in path.iter().enumerate() {
            let (px, py) = pos_xy(p);
            let d = (px - hx).abs() + (py - hy).abs();
            match best {
                None => best = Some((i, d)),
                Some((_, bd)) if d < bd => best = Some((i, d)),
                _ => {}
            }
        }
        let (start_idx, _) = best.unwrap();
        let start = path[start_idx];
        for p in grid_path_excl_start(start, h) {
            push_unique(&mut path, &mut seen, p);
        }
    }
    // Phase 3: row-major remaining interior cells
    for y in 1..(N - 1) {
        for x in 1..(N - 1) {
            push_unique(&mut path, &mut seen, xy_pos(x as i32, y as i32));
        }
    }
    assert_eq!(path.len(), N_POS);
    path
}

/// "hint-then-outspiral" — 5 canonical hints connected by shortest paths
/// (centre region, ~50 cells), then SPIRAL OUTWARD by increasing
/// Chebyshev distance from board centre, finishing on the border ring.
/// Hypothesis: get the centre stuck/decided early, then let outer rings
/// fill with the centre boundary already fixed.
fn build_hint_then_outspiral_path(hint_positions: &[usize]) -> Vec<usize> {
    let mut path: Vec<usize> = Vec::new();
    let mut seen: HashSet<usize> = HashSet::new();
    // Phase 1: hint-link region (same as build_hint_link_path's first phase)
    if let Some(&first) = hint_positions.first() {
        push_unique(&mut path, &mut seen, first);
    }
    for w in hint_positions.windows(2) {
        for p in grid_path_excl_start(w[0], w[1]) {
            push_unique(&mut path, &mut seen, p);
        }
    }
    // Phase 2: cells ordered by DECREASING Chebyshev distance from centre.
    // I.e. start with cells AT Chebyshev distance 7 (rare) and walk inward.
    // No — we want OUTWARD: start with smallest remaining radius (close to
    // hint region) and increase to 7 (border). Same direction as before
    // but ensures hints are visited FIRST regardless of their radius.
    let cx = (N / 2) as i32 - 1; // 7
    let cy = (N / 2) as i32 - 1; // 7
    for radius in 0..N as i32 {
        for dx in -radius..=radius {
            for dy in -radius..=radius {
                if dx.abs().max(dy.abs()) != radius { continue; }
                let x = cx + dx;
                let y = cy + dy;
                if !in_bounds(x, y) { continue; }
                push_unique(&mut path, &mut seen, xy_pos(x, y));
            }
        }
    }
    assert_eq!(path.len(), N_POS);
    path
}

/// "hint-then-borderin" — hint-link region first, then border ring,
/// then row-major interior. Hypothesis: hint region "decides" early
/// → constraints transmit outward → border-fit becomes deterministic →
/// interior is over-constrained but a few valid completions remain.
fn build_hint_then_borderin_path(hint_positions: &[usize]) -> Vec<usize> {
    let mut path: Vec<usize> = Vec::new();
    let mut seen: HashSet<usize> = HashSet::new();
    // Phase 1: hint-link (centre)
    if let Some(&first) = hint_positions.first() {
        push_unique(&mut path, &mut seen, first);
    }
    for w in hint_positions.windows(2) {
        for p in grid_path_excl_start(w[0], w[1]) {
            push_unique(&mut path, &mut seen, p);
        }
    }
    // Phase 2: border ring (top, right, bottom, left)
    for x in 0..N { push_unique(&mut path, &mut seen, xy_pos(x as i32, 0)); }
    for y in 1..N { push_unique(&mut path, &mut seen, xy_pos(N as i32 - 1, y as i32)); }
    for x in (0..(N - 1)).rev() { push_unique(&mut path, &mut seen, xy_pos(x as i32, N as i32 - 1)); }
    for y in (1..(N - 1)).rev() { push_unique(&mut path, &mut seen, xy_pos(0, y as i32)); }
    // Phase 3: row-major interior (any unvisited cells)
    for y in 1..(N - 1) {
        for x in 1..(N - 1) {
            push_unique(&mut path, &mut seen, xy_pos(x as i32, y as i32));
        }
    }
    assert_eq!(path.len(), N_POS);
    path
}

/// "centre-sandwich" — start at hints + immediate 1-hop neighbours (~25 cells),
/// then top half top-down (rows 0..7), then bottom half bottom-up (rows 15..8),
/// converging at row 7-8 from both sides.
fn build_centre_sandwich_path(hint_positions: &[usize]) -> Vec<usize> {
    let mut path: Vec<usize> = Vec::new();
    let mut seen: HashSet<usize> = HashSet::new();
    // Phase 1: hints + their 1-hop neighbours
    for &h in hint_positions {
        push_unique(&mut path, &mut seen, h);
        let (x, y) = pos_xy(h);
        for (dx, dy) in [(-1, 0), (1, 0), (0, -1), (0, 1)] {
            let nx = x + dx;
            let ny = y + dy;
            if !in_bounds(nx, ny) { continue; }
            push_unique(&mut path, &mut seen, xy_pos(nx, ny));
        }
    }
    // Phase 2: top half rows 0..7 row-major
    for y in 0..N / 2 {
        for x in 0..N {
            push_unique(&mut path, &mut seen, xy_pos(x as i32, y as i32));
        }
    }
    // Phase 3: bottom half rows N-1..N/2 in reverse (row-major)
    for y in (N / 2..N).rev() {
        for x in 0..N {
            push_unique(&mut path, &mut seen, xy_pos(x as i32, y as i32));
        }
    }
    assert_eq!(path.len(), N_POS);
    path
}

/// Border-ring first, then concentric inward squares, hint-aware:
/// visit border ring (0..N-1, then inner ring, etc.) but VISIT HINT POSITIONS
/// IN PATH ORDER at the natural step they fall on.
/// This is just plain "spiral inward from outside" — but distinct from
/// row-major because it processes border before any interior cell.
fn build_outer_spiral_path() -> Vec<usize> {
    let mut path: Vec<usize> = Vec::new();
    let mut seen: HashSet<usize> = HashSet::new();
    let mut layer = 0;
    while layer * 2 < N {
        let lo = layer;
        let hi = N - 1 - layer;
        if lo == hi {
            // Single cell layer (centre of odd-sized board — N/A for N=16)
            push_unique(&mut path, &mut seen, xy_pos(lo as i32, lo as i32));
        } else {
            // Top row (lo..=hi)
            for x in lo..=hi { push_unique(&mut path, &mut seen, xy_pos(x as i32, lo as i32)); }
            // Right col (lo+1..=hi)
            for y in (lo + 1)..=hi { push_unique(&mut path, &mut seen, xy_pos(hi as i32, y as i32)); }
            // Bottom row (hi-1..=lo, reverse)
            for x in (lo..=hi - 1).rev() { push_unique(&mut path, &mut seen, xy_pos(x as i32, hi as i32)); }
            // Left col (hi-1..=lo+1, reverse)
            for y in (lo + 1..=hi - 1).rev() { push_unique(&mut path, &mut seen, xy_pos(lo as i32, y as i32)); }
        }
        layer += 1;
    }
    assert_eq!(path.len(), N_POS);
    path
}

/// Border ring first (entire perimeter in row/col order), then row-major interior.
/// Distinct from outer-spiral: the interior portion uses row-major rather than
/// continuing the spiral.
fn build_border_first_path() -> Vec<usize> {
    let mut path: Vec<usize> = Vec::new();
    let mut seen: HashSet<usize> = HashSet::new();
    // Border ring (top, right, bottom, left)
    for x in 0..N { push_unique(&mut path, &mut seen, xy_pos(x as i32, 0)); }
    for y in 1..N { push_unique(&mut path, &mut seen, xy_pos(N as i32 - 1, y as i32)); }
    for x in (0..(N - 1)).rev() { push_unique(&mut path, &mut seen, xy_pos(x as i32, N as i32 - 1)); }
    for y in (1..(N - 1)).rev() { push_unique(&mut path, &mut seen, xy_pos(0, y as i32)); }
    // Row-major interior
    for y in 1..(N - 1) {
        for x in 1..(N - 1) {
            push_unique(&mut path, &mut seen, xy_pos(x as i32, y as i32));
        }
    }
    assert_eq!(path.len(), N_POS);
    path
}

/// Vol-121 T2 — xorshift64 seeded RNG for path randomization. Deterministic
/// per seed so basins are reproducible.
#[inline(always)]
fn next_xorshift64(state: &mut u64) -> u64 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    *state
}

fn fisher_yates_shuffle(v: &mut [usize], seed: u64) {
    let mut state: u64 = seed.wrapping_mul(0x9E37_79B9_7F4A_7C15).wrapping_add(0xDEAD_BEEF_CAFE_BABE);
    if state == 0 { state = 0x1234_5678_9ABC_DEF0; }
    let n = v.len();
    if n < 2 { return; }
    for i in (1..n).rev() {
        let j = (next_xorshift64(&mut state) as usize) % (i + 1);
        v.swap(i, j);
    }
}

/// Vol-121 T2 — full random permutation of 0..N_POS, seeded.
/// Maximum basin diversity but ignores constraint-propagation locality.
fn build_random_path(seed: u64) -> Vec<usize> {
    let mut path: Vec<usize> = (0..N_POS).collect();
    fisher_yates_shuffle(&mut path, seed);
    path
}

/// Vol-121 T2 — border-first (60 perimeter cells, deterministic), then
/// RANDOM permutation of 196 interior cells, seeded.
/// Preserves border-CSP-tightness while randomizing interior search tree.
fn build_border_first_random_interior_path(seed: u64) -> Vec<usize> {
    let mut path: Vec<usize> = Vec::new();
    let mut seen: HashSet<usize> = HashSet::new();
    for x in 0..N { push_unique(&mut path, &mut seen, xy_pos(x as i32, 0)); }
    for y in 1..N { push_unique(&mut path, &mut seen, xy_pos(N as i32 - 1, y as i32)); }
    for x in (0..(N - 1)).rev() { push_unique(&mut path, &mut seen, xy_pos(x as i32, N as i32 - 1)); }
    for y in (1..(N - 1)).rev() { push_unique(&mut path, &mut seen, xy_pos(0, y as i32)); }
    let border_len = path.len();
    assert_eq!(border_len, 4 * N - 4);
    // Collect interior, randomize.
    let mut interior: Vec<usize> = Vec::new();
    for y in 1..(N - 1) {
        for x in 1..(N - 1) {
            interior.push(xy_pos(x as i32, y as i32));
        }
    }
    fisher_yates_shuffle(&mut interior, seed);
    path.extend(interior);
    assert_eq!(path.len(), N_POS);
    path
}

fn main() {
    let mut budget_ms: u64 = 10_000;
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut path_mode = String::from("hint-link");
    let mut path_csv: Option<PathBuf> = None;
    let mut threads: usize = 1;
    let mut thread_id_offset: usize = 0;
    let mut pin_hints = false;
    let mut save_best: Option<PathBuf> = None;
    let mut dump_path: bool = false;
    let mut path_seed: u64 = 1; // vol-121 T2: used only by random* path modes

    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget-ms"); i += 2; }
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--path-mode" => { path_mode = raw[i + 1].clone(); i += 2; }
            "--path-csv" => { path_csv = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--path-seed" => { path_seed = raw[i + 1].parse().expect("path-seed"); i += 2; }
            "--threads" => { threads = raw[i + 1].parse().expect("threads"); i += 2; }
            "--thread-id-offset" => { thread_id_offset = raw[i + 1].parse().expect("thread-id-offset"); i += 2; }
            "--pin-hints" => { pin_hints = true; i += 1; }
            "--save-best" => { save_best = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--dump-path" => { dump_path = true; i += 1; }
            other => panic!("unknown arg: {other}"),
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    assert_eq!(puzzle.width as usize, N);
    assert_eq!(puzzle.height as usize, N);

    let hint_positions: Vec<usize> = hints.hints.iter().map(|h| h.position as usize).collect();
    eprintln!("[init] hint positions: {hint_positions:?}");

    let path: Vec<usize> = if let Some(p) = path_csv.as_ref() {
        let s = std::fs::read_to_string(p).expect("read path-csv");
        let v: Vec<usize> = s.lines().filter_map(|l| l.trim().parse().ok()).collect();
        assert_eq!(v.len(), N_POS, "path-csv must have {} positions", N_POS);
        v
    } else {
        match path_mode.as_str() {
            "row-major" => build_row_major_path(),
            "hint-link" => build_hint_link_path(&hint_positions),
            "outer-spiral" => build_outer_spiral_path(),
            "border-first" => build_border_first_path(),
            "border-then-hints" => build_border_then_hints_path(&hint_positions),
            "hint-then-outspiral" => build_hint_then_outspiral_path(&hint_positions),
            "hint-then-borderin" => build_hint_then_borderin_path(&hint_positions),
            "centre-sandwich" => build_centre_sandwich_path(&hint_positions),
            // Vol-121 T2 — randomized paths. --path-seed N gives reproducibility.
            "random" => build_random_path(path_seed),
            "border-first-random" => build_border_first_random_interior_path(path_seed),
            other => panic!("unknown path-mode: {other}"),
        }
    };
    assert_eq!(path.len(), N_POS);
    let mut seen = HashSet::new();
    for &p in &path { assert!(seen.insert(p), "path has duplicate pos {p}"); }

    if dump_path {
        for &p in &path { println!("{p}"); }
        return;
    }

    // path_idx[pos] = step at which pos is visited
    let mut path_idx: [u16; N_POS] = [u16::MAX; N_POS];
    for (step, &p) in path.iter().enumerate() {
        path_idx[p] = step as u16;
    }

    // Per-step constraint mask: which NESW neighbours are visited BEFORE step d.
    // Also record the path-step (depth at which that neighbour was placed) so we
    // can look up its color cheaply at runtime via chosen[step] (path-major).
    // For each step d, store for each of the 4 directions: Option<step_of_neighbour>.
    // Directions order: N (y-1), E (x+1), S (y+1), W (x-1).
    let mut step_constraint: Vec<[Option<u16>; 4]> = vec![[None; 4]; N_POS];
    for d in 0..N_POS {
        let pos = path[d];
        let (x, y) = pos_xy(pos);
        let deltas: [(i32, i32); 4] = [(0, -1), (1, 0), (0, 1), (-1, 0)]; // N,E,S,W
        for (i, (dx, dy)) in deltas.iter().enumerate() {
            let nx = x + dx;
            let ny = y + dy;
            if !in_bounds(nx, ny) { continue; }
            let nb_pos = xy_pos(nx, ny);
            let nb_step = path_idx[nb_pos] as usize;
            if nb_step < d {
                step_constraint[d][i] = Some(nb_step as u16);
            }
        }
    }

    // Build per-piece rotation table.
    let mut piece_rots: Vec<PieceRot> = Vec::with_capacity(N_PIECES * N_ROT);
    for pid in 0..N_PIECES as u16 {
        let p = puzzle.piece(pid).expect("piece");
        let base = p.edges.as_array();
        for r in 0..N_ROT as u8 {
            let rotated = rotate_edges(base, r);
            piece_rots.push(PieceRot {
                piece_id: pid, rot: r,
                n: rotated[0], e: rotated[1], s: rotated[2], w: rotated[3],
            });
        }
    }

    // For each step d, pre-bucket by the constrained-side colors.
    // Per step we have a mask m ∈ {0..15}, popcount k ∈ {0..4}.
    // We pack the constrained colors (in N, E, S, W order, ONLY for sides
    // where mask bit is set) into a u32 key. Bucket count = 23^k.
    // step_bucket_data[d]: flat Vec<u32> of candidate entries for step d
    // step_bucket_starts[d]: Vec<u32> of length 23^k + 1; bucket [i, i+1) is the slice.
    // step_bucket_stride[d]: the multiplier per constrained side, ordered N,E,S,W.
    let mut pid_global_count: [u32; N_PIECES] = [0; N_PIECES];
    for pr in &piece_rots { pid_global_count[pr.piece_id as usize] += 1; }

    let mut hint_at: Vec<Option<(u16, u8)>> = vec![None; N_POS];
    if pin_hints {
        for h in hints.hints.iter() {
            hint_at[h.position as usize] = Some((h.piece_id, h.rotation.as_u8()));
        }
    }

    // Compute mask per step
    let step_mask: Vec<u8> = (0..N_POS).map(|d| {
        let mut m = 0u8;
        if step_constraint[d][0].is_some() { m |= F_N; }
        if step_constraint[d][1].is_some() { m |= F_E; }
        if step_constraint[d][2].is_some() { m |= F_S; }
        if step_constraint[d][3].is_some() { m |= F_W; }
        m
    }).collect();

    let mut step_bucket_data: Vec<Vec<u32>> = vec![Vec::new(); N_POS];
    let mut step_bucket_starts: Vec<Vec<u32>> = vec![Vec::new(); N_POS];
    let mut step_n_buckets: Vec<u32> = vec![1; N_POS];

    for d in 0..N_POS {
        let pos = path[d];
        let n_b = need_n_border(pos);
        let e_b = need_e_border(pos);
        let s_b = need_s_border(pos);
        let w_b = need_w_border(pos);

        let m = step_mask[d];
        let k = m.count_ones();
        let n_buckets = pow23(k as usize) as u32;
        step_n_buckets[d] = n_buckets;
        step_bucket_starts[d] = vec![0u32; (n_buckets as usize) + 1];

        let hint_here = hint_at[pos];

        // Step 1: count entries per bucket
        let mut counts = vec![0u32; n_buckets as usize];
        let mut pre_entries: Vec<(u32, u32)> = Vec::new(); // (entry, bucket_idx)
        for pr in piece_rots.iter() {
            if (pr.n == BORDER) != n_b { continue; }
            if (pr.e == BORDER) != e_b { continue; }
            if (pr.s == BORDER) != s_b { continue; }
            if (pr.w == BORDER) != w_b { continue; }
            if let Some((hpid, hrot)) = hint_here {
                if pr.piece_id != hpid || pr.rot != hrot { continue; }
            }
            let bidx = compute_bucket_idx(m, pr.n, pr.e, pr.s, pr.w);
            counts[bidx as usize] += 1;
            let entry = pack_entry(pr.piece_id, pr.rot, pr.n, pr.e, pr.s, pr.w);
            pre_entries.push((entry, bidx));
        }
        // Prefix-sum
        let mut acc: u32 = 0;
        for i in 0..n_buckets as usize {
            step_bucket_starts[d][i] = acc;
            acc += counts[i];
        }
        step_bucket_starts[d][n_buckets as usize] = acc;
        step_bucket_data[d] = vec![0u32; acc as usize];
        let mut cursor = step_bucket_starts[d].clone();
        for (entry, bidx) in pre_entries.iter() {
            let dst = cursor[*bidx as usize] as usize;
            step_bucket_data[d][dst] = *entry;
            cursor[*bidx as usize] += 1;
        }
        // Sort each sub-bucket by piece-rarity (rare first → fewer 'used' rejections)
        for bi in 0..n_buckets as usize {
            let s = step_bucket_starts[d][bi] as usize;
            let e = step_bucket_starts[d][bi + 1] as usize;
            if e - s <= 1 { continue; }
            step_bucket_data[d][s..e].sort_by_key(|&en| pid_global_count[((en >> 22) & 0x1ff) as usize]);
        }
    }

    let total_entries: usize = step_bucket_data.iter().map(|c| c.len()).sum();
    let total_buckets: u32 = step_n_buckets.iter().sum();
    eprintln!("[init] path mode: {} | total entries: {} | total buckets: {} | hint-pinned: {}",
        if path_csv.is_some() { "csv".into() } else { path_mode.clone() },
        total_entries, total_buckets, pin_hints);
    eprintln!("[init] step-0 entries: {} (mask={}, buckets={})",
        step_bucket_data[0].len(), step_mask[0], step_n_buckets[0]);
    eprintln!("[init] step-128 entries: {} (mask={}, buckets={})",
        step_bucket_data.get(128).map(|v| v.len()).unwrap_or(0), step_mask.get(128).copied().unwrap_or(0), step_n_buckets.get(128).copied().unwrap_or(0));
    eprintln!("[init] step-255 entries: {} (mask={}, buckets={})",
        step_bucket_data[N_POS - 1].len(), step_mask[N_POS - 1], step_n_buckets[N_POS - 1]);

    let t0 = Instant::now();
    let deadline = t0 + std::time::Duration::from_millis(budget_ms);
    let total_placements_atomic = AtomicU64::new(0);
    let total_backtracks_atomic = AtomicU64::new(0);
    let max_depth_atomic = AtomicU64::new(0);
    let solved_count_atomic = AtomicU64::new(0);

    #[derive(Clone)]
    struct ThreadResult {
        thread_id: usize,
        placements: u64,
        backtracks: u64,
        max_depth: u32,
        solved: u64,
        best_chosen: Vec<u32>, // path-major: indexed by step
    }

    let path_arc = std::sync::Arc::new(path.clone());
    let step_constraint_arc = std::sync::Arc::new(step_constraint.clone());
    let step_mask_arc = std::sync::Arc::new(step_mask.clone());
    let step_bucket_data_arc = std::sync::Arc::new(step_bucket_data);
    let step_bucket_starts_arc = std::sync::Arc::new(step_bucket_starts);

    eprintln!("[init] running {} worker(s) for {} ms", threads, budget_ms);

    let thread_results: Vec<ThreadResult> = (0..threads).into_par_iter().map(|thread_idx| {
        let thread_id = thread_idx + thread_id_offset;
        let _path = path_arc.clone();
        let step_constraint = step_constraint_arc.clone();
        let step_mask = step_mask_arc.clone();
        let step_bucket_data_global = step_bucket_data_arc.clone();
        let step_bucket_starts = step_bucket_starts_arc.clone();

        // Per-thread: shuffle entries WITHIN each (step, bucket) sub-slice for basin diversity.
        let mut my_bucket_data: Vec<Vec<u32>> = (*step_bucket_data_global).clone();
        if thread_id > 0 {
            let mut rng_state: u64 = (thread_id as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15)
                .wrapping_add(0xDEAD_BEEF_CAFE_BABE);
            let mut next_rand = |state: &mut u64| -> u64 {
                *state ^= *state << 13;
                *state ^= *state >> 7;
                *state ^= *state << 17;
                *state
            };
            for d in 0..N_POS {
                let starts = &step_bucket_starts[d];
                for bi in 0..starts.len() - 1 {
                    let s = starts[bi] as usize;
                    let e = starts[bi + 1] as usize;
                    let len = e - s;
                    if len <= 1 { continue; }
                    for i in (1..len).rev() {
                        let j = (next_rand(&mut rng_state) as usize) % (i + 1);
                        my_bucket_data[d].swap(s + i, s + j);
                    }
                }
            }
        }

        let mut chosen: Vec<u32> = vec![0u32; N_POS];
        let mut frame_end: Vec<u32> = vec![0u32; N_POS];
        let mut cursor: Vec<u32> = vec![0u32; N_POS];
        let mut used: [bool; N_PIECES] = [false; N_PIECES];

        let mut total_placements: u64 = 0;
        let mut total_backtracks: u64 = 0;
        let mut max_depth: u32 = 0;
        let mut solved_count: u64 = 0;
        let mut best_chosen: Vec<u32> = vec![0u32; N_POS];

        let mut depth: usize = 0;

        // enter_fresh: compute the bucket slice for step `depth` based on placed neighbours.
        macro_rules! enter_fresh {
            ($d:expr) => {{
                let d = $d;
                let constraints = step_constraint[d];
                let m = step_mask[d];
                let mut need_n: u8 = 0;
                let mut need_e: u8 = 0;
                let mut need_s: u8 = 0;
                let mut need_w: u8 = 0;
                if let Some(st) = constraints[0] { need_n = entry_s(chosen[st as usize]); }
                if let Some(st) = constraints[1] { need_e = entry_w(chosen[st as usize]); }
                if let Some(st) = constraints[2] { need_s = entry_n(chosen[st as usize]); }
                if let Some(st) = constraints[3] { need_w = entry_e(chosen[st as usize]); }
                let bidx = compute_needed_bucket_idx(m, need_n, need_e, need_s, need_w) as usize;
                let starts = &step_bucket_starts[d];
                frame_end[d] = starts[bidx + 1];
                cursor[d] = starts[bidx];
            }};
        }

        enter_fresh!(0);

        'outer: loop {
            if (total_placements & 0x3FFFF) == 0 && Instant::now() >= deadline {
                break;
            }
            let end = frame_end[depth];
            let mut cur = cursor[depth];
            let cands = &my_bucket_data[depth];
            let mut found = u32::MAX;
            while cur < end {
                let entry = cands[cur as usize];
                let pid = ((entry >> 22) & 0x1ff) as usize;
                if !used[pid] {
                    found = entry;
                    break;
                }
                cur += 1;
            }
            if found != u32::MAX {
                chosen[depth] = found;
                let pid = ((found >> 22) & 0x1ff) as usize;
                used[pid] = true;
                cursor[depth] = cur;
                total_placements += 1;
                depth += 1;
                if depth as u32 > max_depth {
                    max_depth = depth as u32;
                    best_chosen.copy_from_slice(&chosen);
                }
                if depth == N_POS {
                    solved_count += 1;
                    eprintln!("[t{thread_id}] [solve] FOUND in {} ms", t0.elapsed().as_millis());
                    depth -= 1;
                    let pid = ((chosen[depth] >> 22) & 0x1ff) as usize;
                    used[pid] = false;
                    cursor[depth] += 1;
                    continue;
                }
                enter_fresh!(depth);
            } else {
                if depth == 0 { break 'outer; }
                depth -= 1;
                total_backtracks += 1;
                let pid = ((chosen[depth] >> 22) & 0x1ff) as usize;
                used[pid] = false;
                cursor[depth] += 1;
            }
        }

        total_placements_atomic.fetch_add(total_placements, Ordering::Relaxed);
        total_backtracks_atomic.fetch_add(total_backtracks, Ordering::Relaxed);
        max_depth_atomic.fetch_max(max_depth as u64, Ordering::Relaxed);
        solved_count_atomic.fetch_add(solved_count, Ordering::Relaxed);

        ThreadResult {
            thread_id,
            placements: total_placements,
            backtracks: total_backtracks,
            max_depth,
            solved: solved_count,
            best_chosen,
        }
    }).collect();

    let global_best = thread_results.iter().max_by_key(|r| r.max_depth).expect("at least one thread");
    let best_depth_path = global_best.max_depth;
    let total_placements = total_placements_atomic.load(Ordering::Relaxed);
    let total_backtracks = total_backtracks_atomic.load(Ordering::Relaxed);
    let max_depth = max_depth_atomic.load(Ordering::Relaxed) as u32;
    let solved_count = solved_count_atomic.load(Ordering::Relaxed);

    let elapsed = t0.elapsed();
    let elapsed_s = elapsed.as_secs_f64();
    let pps = (total_placements as f64) / elapsed_s;

    for r in &thread_results {
        let t_pps = r.placements as f64 / elapsed_s;
        eprintln!("  thread {}: depth={} placements={} ({:.0} pp/s)", r.thread_id, r.max_depth, r.placements, t_pps);
    }

    println!(
        "{{\"profile\":\"vanilla_path\",\"path_mode\":\"{path_mode}\",\"budget_ms\":{budget_ms},\"elapsed_ms\":{},\"placements\":{},\"backtracks\":{},\"max_depth\":{},\"solved\":{},\"placements_per_sec\":{:.0}}}",
        elapsed.as_millis(),
        total_placements,
        total_backtracks,
        max_depth,
        solved_count,
        pps,
    );

    // Reconstruct board from path-major best_chosen → canonical position order.
    let best_chosen = &global_best.best_chosen;
    let mut placement: Vec<Option<(u16, u8)>> = vec![None; N_POS];
    for step in 0..best_depth_path as usize {
        let entry = best_chosen[step];
        let pid = ((entry >> 22) & 0x1ff) as u16;
        let rot = ((entry >> 20) & 0x3) as u8;
        let pos = path_arc[step];
        placement[pos] = Some((pid, rot));
    }

    // Score (matched_edges) on the canonical board.
    let mut board = Board::empty(&puzzle);
    for (pos, slot) in placement.iter().enumerate() {
        if let Some((pid, rot)) = slot {
            if let Some(r) = Rotation::from_u8(*rot) {
                board.place(pos as u32, PieceId::from(*pid), r);
            }
        }
    }
    let bucas = bucas_url(&puzzle, &board, "size_16_official_eternity");
    eprintln!("[bucas] {bucas}");

    // Matched edges (mirror vanilla_fast's calculation, but in canonical pos order)
    let mut matched_internal = 0u32;
    let mut matched_border = 0u32;
    for pos in 0..N_POS {
        if placement[pos].is_none() { continue; }
        let (pid, rot) = placement[pos].unwrap();
        let pr = &piece_rots[pid as usize * N_ROT + rot as usize];
        let x = pos % N;
        let y = pos / N;
        if x + 1 < N {
            if let Some((npid, nrot)) = placement[pos + 1] {
                let npr = &piece_rots[npid as usize * N_ROT + nrot as usize];
                if pr.e == npr.w { matched_internal += 1; }
            }
        }
        if y + 1 < N {
            if let Some((npid, nrot)) = placement[pos + N] {
                let npr = &piece_rots[npid as usize * N_ROT + nrot as usize];
                if pr.s == npr.n { matched_internal += 1; }
            }
        }
        if y == 0 && pr.n == BORDER { matched_border += 1; }
        if x == N - 1 && pr.e == BORDER { matched_border += 1; }
        if y == N - 1 && pr.s == BORDER { matched_border += 1; }
        if x == 0 && pr.w == BORDER { matched_border += 1; }
    }
    let best_score = matched_internal + matched_border;
    eprintln!("[best-partial] depth-along-path={} matched_internal={} matched_border={} matched_total={}/480",
        best_depth_path, matched_internal, matched_border, best_score);

    if let Some(path) = save_best {
        let mut json = String::from("{\"placement\": [");
        for (i, p) in placement.iter().enumerate() {
            if i > 0 { json.push(','); }
            match p {
                None => json.push_str("null"),
                Some((pid, rot)) => json.push_str(&format!("{{\"piece_id\":{},\"rotation\":{}}}", pid, rot)),
            }
        }
        json.push_str("]}");
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).ok();
        }
        std::fs::write(&path, &json).expect("write save-best");
        eprintln!("[saved] {} (depth-along-path={} score={})", path.display(), best_depth_path, best_score);
    }
}

// Packed candidate entry (path variant needs all 4 colors since the bucket
// key is dynamic per-step). Layout (u32): piece_id (9) | rot (2) | n (5) | e (5) | s (5) | w (5).
// Total: 9+2+5*4 = 31 bits.
#[inline(always)]
fn pack_entry(piece_id: u16, rot: u8, n: u8, e: u8, s: u8, w: u8) -> u32 {
    ((piece_id as u32) << 22)
        | ((rot as u32) << 20)
        | ((n as u32) << 15)
        | ((e as u32) << 10)
        | ((s as u32) << 5)
        | (w as u32)
}
#[inline(always)] fn entry_n(p: u32) -> u8 { ((p >> 15) & 0x1f) as u8 }
#[inline(always)] fn entry_e(p: u32) -> u8 { ((p >> 10) & 0x1f) as u8 }
#[inline(always)] fn entry_s(p: u32) -> u8 { ((p >> 5) & 0x1f) as u8 }
#[inline(always)] fn entry_w(p: u32) -> u8 { (p & 0x1f) as u8 }

#[inline(always)]
fn pow23(k: usize) -> u32 {
    match k {
        0 => 1,
        1 => 23,
        2 => 529,
        3 => 12167,
        4 => 279841,
        _ => unreachable!("k>4 impossible"),
    }
}

/// Compute bucket index for a candidate given its 4 colors and the step's mask.
/// We pack colors of constrained sides in N, E, S, W order, base-23.
#[inline(always)]
fn compute_bucket_idx(mask: u8, n: u8, e: u8, s: u8, w: u8) -> u32 {
    let mut idx: u32 = 0;
    if mask & F_N != 0 { idx = idx * 23 + n as u32; }
    if mask & F_E != 0 { idx = idx * 23 + e as u32; }
    if mask & F_S != 0 { idx = idx * 23 + s as u32; }
    if mask & F_W != 0 { idx = idx * 23 + w as u32; }
    idx
}

/// Same idx layout but used at runtime: given the colors NEEDED at this step,
/// compute the bucket index. (Colors from already-placed neighbours.)
#[inline(always)]
fn compute_needed_bucket_idx(mask: u8, need_n: u8, need_e: u8, need_s: u8, need_w: u8) -> u32 {
    compute_bucket_idx(mask, need_n, need_e, need_s, need_w)
}
