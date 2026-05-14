// Vol-32+ PoC — vanilla fast backtracker for E2 (no propagators, no ML).
// Row-major scan, dense arrays, pre-bucketed candidates by (pos, north_color, west_color).
// v2 — optimised hot loop:
//   - Packed candidate entries (piece_id, S, E) in u32; no piece_rots indirection in inner loop
//   - Flat bucket storage (bucket_data + bucket_offsets) for cache locality
//   - Track placed-S and placed-E directly on stacks
//   - u16::MAX sentinel (no Option<>)
//
// Goal: hit community-class throughput (97M-140M placements/sec).
//
// Run:
//   target/release/vanilla_fast --budget-ms 10000 --puzzle ../data/puzzles/size_16_official_eternity.csv

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::BORDER;

const N: usize = 16;
const N_POS: usize = N * N;
const N_PIECES: usize = 256;
const N_ROT: usize = 4;
const N_COLORS: usize = 23;  // 0=border, 1..22 interior
const NW_KEYS: usize = N_COLORS * N_COLORS;  // 529

// Packed candidate entry: (piece_id : 9 bits | rot : 2 | S : 5 | E : 5) — fits in u32.
// We don't need N, W in the entry (those are the bucket key).
// piece_id in 0..256 → 9 bits. rot 0..3 → 2 bits. S, E in 0..22 → 5 bits each.
// We pack as: (piece_id << 12) | (rot << 10) | (S << 5) | E
#[inline(always)]
fn pack_entry(piece_id: u16, rot: u8, s: u8, e: u8) -> u32 {
    ((piece_id as u32) << 12) | ((rot as u32) << 10) | ((s as u32) << 5) | (e as u32)
}
#[inline(always)]
fn entry_piece_id(p: u32) -> u16 { (p >> 12) as u16 }
#[inline(always)]
fn entry_rot(p: u32) -> u8 { ((p >> 10) & 0x3) as u8 }
#[inline(always)]
fn entry_s(p: u32) -> u8 { ((p >> 5) & 0x1f) as u8 }
#[inline(always)]
fn entry_e(p: u32) -> u8 { (p & 0x1f) as u8 }

#[inline(always)]
fn need_north_border(pos: usize) -> bool { pos < N }
#[inline(always)]
fn need_west_border(pos: usize) -> bool { pos % N == 0 }
#[inline(always)]
fn need_south_border(pos: usize) -> bool { pos >= N_POS - N }
#[inline(always)]
fn need_east_border(pos: usize) -> bool { pos % N == N - 1 }

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    // CSV stores [top, right, bottom, left]
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

    // Build per-piece rotation tables temporarily.
    #[derive(Copy, Clone)]
    struct PieceRot {
        piece_id: u16,
        rot: u8,
        n: u8,
        e: u8,
        s: u8,
        w: u8,
    }
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

    // For each pos, group candidates by (N, W) into a contiguous slice.
    // Layout: bucket_data is one big Vec<u32>. bucket_starts[pos * NW_KEYS + key] gives
    // start index; bucket_lens stores length. Both indexed by pos * NW_KEYS + key.
    // Total entries: ~157k (avg 600 candidates/pos × 256 pos / ~600 keys/pos coverage)
    // But many (pos, key) pairs are empty. We pre-compute per-(pos,key) the candidate slice.
    let total_keys = N_POS * NW_KEYS;
    let mut bucket_starts: Vec<u32> = vec![0; total_keys + 1];
    let mut bucket_lens: Vec<u16> = vec![0; total_keys];

    // First pass: count.
    let mut counts: Vec<u32> = vec![0; total_keys];
    for pos in 0..N_POS {
        let need_n_border = need_north_border(pos);
        let need_e_border = need_east_border(pos);
        let need_s_border = need_south_border(pos);
        let need_w_border = need_west_border(pos);
        for pr in piece_rots.iter() {
            let n_is_border = pr.n == BORDER;
            let e_is_border = pr.e == BORDER;
            let s_is_border = pr.s == BORDER;
            let w_is_border = pr.w == BORDER;
            if n_is_border != need_n_border { continue; }
            if e_is_border != need_e_border { continue; }
            if s_is_border != need_s_border { continue; }
            if w_is_border != need_w_border { continue; }
            let key = (pr.n as usize) * N_COLORS + (pr.w as usize);
            counts[pos * NW_KEYS + key] += 1;
        }
    }
    // Prefix-sum into bucket_starts
    let mut acc: u32 = 0;
    for i in 0..total_keys {
        bucket_starts[i] = acc;
        acc += counts[i];
    }
    bucket_starts[total_keys] = acc;
    let total_entries = acc as usize;

    // Allocate flat data array
    let mut bucket_data: Vec<u32> = vec![0u32; total_entries];

    // Second pass: fill, using counts as cursors
    let mut cursor: Vec<u32> = bucket_starts.clone();
    for pos in 0..N_POS {
        let need_n_border = need_north_border(pos);
        let need_e_border = need_east_border(pos);
        let need_s_border = need_south_border(pos);
        let need_w_border = need_west_border(pos);
        for pr in piece_rots.iter() {
            let n_is_border = pr.n == BORDER;
            let e_is_border = pr.e == BORDER;
            let s_is_border = pr.s == BORDER;
            let w_is_border = pr.w == BORDER;
            if n_is_border != need_n_border { continue; }
            if e_is_border != need_e_border { continue; }
            if s_is_border != need_s_border { continue; }
            if w_is_border != need_w_border { continue; }
            let key = (pr.n as usize) * N_COLORS + (pr.w as usize);
            let idx = pos * NW_KEYS + key;
            let dst = cursor[idx] as usize;
            bucket_data[dst] = pack_entry(pr.piece_id, pr.rot, pr.s, pr.e);
            cursor[idx] += 1;
            bucket_lens[idx] += 1;
        }
    }

    eprintln!("[init] piece_rots: {}, bucket entries: {}", piece_rots.len(), total_entries);
    let max_b = bucket_lens.iter().copied().max().unwrap_or(0);
    let nonempty = bucket_lens.iter().filter(|&&l| l > 0).count();
    eprintln!("[init] max bucket: {}, non-empty: {}/{}", max_b, nonempty, total_keys);

    // Search state — keep per-depth packed entry chosen + cursor into that bucket.
    let mut chosen: Vec<u32> = vec![0u32; N_POS];  // packed entries
    let mut frame_cursor: Vec<u32> = vec![0u32; N_POS + 1];
    let mut bucket_start_at_depth: Vec<u32> = vec![0u32; N_POS];
    let mut bucket_end_at_depth: Vec<u32> = vec![0u32; N_POS];
    // `used` as plain bool array — faster than bitmask on M1 because single-byte loads.
    let mut used: [bool; N_PIECES] = [false; N_PIECES];

    let t0 = Instant::now();
    let deadline = t0 + std::time::Duration::from_millis(budget_ms);

    let mut total_placements: u64 = 0;
    let mut total_backtracks: u64 = 0;
    let mut max_depth: u32 = 0;
    let mut solved_count: u64 = 0;
    // Per-depth placement counter for profiling distribution
    let mut depth_placements: [u64; N_POS + 1] = [0u64; N_POS + 1];

    let mut depth: usize = 0;

    // For each depth, when entering, we COMPUTE the bucket once: derive (N, W) from
    // placed neighbours (which are the chosen entries at depth-N and depth-1).
    // Stored in bucket_start_at_depth / bucket_end_at_depth and reused on backtrack.
    // On entry to depth d (fresh): compute and store bucket.
    // On backtrack to depth d: reuse stored bucket, advance frame_cursor.

    // Helper: enter depth d freshly (compute bucket).
    macro_rules! enter_fresh {
        ($d:expr) => {{
            let d = $d;
            let pos = d;
            let n_color = if pos < N {
                BORDER
            } else {
                entry_s(chosen[pos - N])
            };
            let w_color = if pos % N == 0 {
                BORDER
            } else {
                entry_e(chosen[pos - 1])
            };
            let key = (n_color as usize) * N_COLORS + (w_color as usize);
            let bkt_idx = pos * NW_KEYS + key;
            bucket_start_at_depth[d] = bucket_starts[bkt_idx];
            bucket_end_at_depth[d] = bucket_starts[bkt_idx + 1];
            frame_cursor[d] = bucket_starts[bkt_idx];
        }};
    }

    enter_fresh!(0);

    'outer: loop {
        // Check budget every 256k placements
        if (total_placements & 0x3FFFF) == 0 && Instant::now() >= deadline {
            break;
        }

        let end = bucket_end_at_depth[depth];
        let mut cur = frame_cursor[depth];
        let mut found = u32::MAX;
        // Hot loop: scan bucket for first un-used piece.
        while cur < end {
            let entry = bucket_data[cur as usize];
            let pid = (entry >> 12) as usize;
            if !used[pid] {
                found = entry;
                break;
            }
            cur += 1;
        }

        if found != u32::MAX {
            chosen[depth] = found;
            let pid = (found >> 12) as usize;
            used[pid] = true;
            frame_cursor[depth] = cur;
            total_placements += 1;
            depth_placements[depth] += 1;
            depth += 1;
            if depth as u32 > max_depth {
                max_depth = depth as u32;
            }
            if depth == N_POS {
                solved_count += 1;
                if want_solve {
                    eprintln!("[solve] FOUND in {} ms", t0.elapsed().as_millis());
                    break;
                }
                depth -= 1;
                let pid = (chosen[depth] >> 12) as usize;
                used[pid] = false;
                frame_cursor[depth] += 1;
                continue;
            }
            enter_fresh!(depth);
        } else {
            if depth == 0 {
                break 'outer;
            }
            depth -= 1;
            total_backtracks += 1;
            let pid = (chosen[depth] >> 12) as usize;
            used[pid] = false;
            frame_cursor[depth] += 1;
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

    // Depth distribution — group by ranges of 20 for readability
    eprintln!("[depth-dist] placements at depth-range:");
    for lo in (0..N_POS as u32).step_by(20) {
        let hi = (lo + 19).min(N_POS as u32 - 1);
        let sum: u64 = (lo..=hi).map(|d| depth_placements[d as usize]).sum();
        if sum > 0 {
            eprintln!("  d={:>3}-{:>3}: {:>15} ({:>5.1}%)", lo, hi, sum, sum as f64 * 100.0 / total_placements as f64);
        }
    }
}
