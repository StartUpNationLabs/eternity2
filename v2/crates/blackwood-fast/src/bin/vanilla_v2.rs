// vanilla_v2 — vol-106 T3 — apply blackwood-fast optimizations to vanilla DFS.
//
// Combines vanilla_fastest's smart per-position bucketing (border
// constraints implicit + bucket-sort by rare-pid-first) with
// blackwood-fast's optimization patterns (const-generic, u64 bitset,
// sentinel-terminated lists, unsafe inner loop with pointer walk).
//
// Goal: beat both blackwood-fast (74 M nps on canonical) and
// vanilla_fastest (73 M pp/s on canonical).

#![allow(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_core::{Color, Puzzle, Rotation, BORDER};
use eternity2_puzzle_io::load_puzzle;

// 16x16 const generics. To support other sizes, monomorphize new
// const-generic clones.
const N: usize = 16;
const N_POS: usize = N * N;
const N_PIECES: usize = N_POS;
const N_COLORS: usize = 32; // generous bound; canonical uses 23 (BORDER+22)
const N_ROT: usize = 4;
const NW_KEYS: usize = N_COLORS * N_COLORS;

/// Packed entry: 16-bit piece_id (low 9 bits) | 2-bit rot | 5-bit s (south color) | 5-bit e (east color) | 11-bit padding.
/// Layout in u32 (low-to-high):
///   bits 0..4   = e (east color)
///   bits 5..9   = s (south color)
///   bits 10..11 = rotation
///   bits 12..20 = piece_id (256 = 9 bits)
///   bits 21..31 = unused (so sentinel u32::MAX is still distinguishable)
#[inline(always)]
fn pack_entry(piece_id: u16, rot: u8, s: u8, e: u8) -> u32 {
    (e as u32) | ((s as u32) << 5) | ((rot as u32) << 10) | ((piece_id as u32) << 12)
}
#[inline(always)]
fn entry_pid(p: u32) -> u32 { (p >> 12) & 0x1FF }
#[inline(always)]
fn entry_rot(p: u32) -> u8 { ((p >> 10) & 0x3) as u8 }
#[inline(always)]
fn entry_s(p: u32) -> u8 { ((p >> 5) & 0x1F) as u8 }
#[inline(always)]
fn entry_e(p: u32) -> u8 { (p & 0x1F) as u8 }

const SENTINEL: u32 = u32::MAX;

#[inline(always)]
fn rotate_edges(e: [Color; 4], r: u8) -> [Color; 4] {
    let mut out = [0u8; 4];
    let mut i = 0;
    while i < 4 {
        out[i] = e[(i + r as usize) & 3];
        i += 1;
    }
    out
}

fn need_north_border(pos: usize) -> bool { pos < N }
fn need_west_border(pos: usize) -> bool { pos % N == 0 }
fn need_south_border(pos: usize) -> bool { pos >= N_POS - N }
fn need_east_border(pos: usize) -> bool { pos % N == N - 1 }

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut puzzle_path = PathBuf::from(
        "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv",
    );
    let mut budget_ms: u64 = 5000;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&args[i + 1]); i += 2; }
            "--budget-ms" => { budget_ms = args[i + 1].parse().expect("budget"); i += 2; }
            _ => { eprintln!("unknown arg: {}", args[i]); std::process::exit(1); }
        }
    }

    let puzzle: Puzzle = load_puzzle(&puzzle_path).expect("load puzzle");
    assert_eq!(puzzle.width as usize, N);
    assert_eq!(puzzle.height as usize, N);

    // Precompute piece rotations.
    struct PieceRot { piece_id: u16, rot: u8, n: u8, e: u8, s: u8, w: u8 }
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

    // Build per-position buckets keyed by (north_color, west_color).
    // Border constraints (north/east/south/west) are baked into bucket
    // construction: a position at row 0 column 0 only includes piece-rots
    // with north=BORDER AND west=BORDER. Same idea as vanilla_fastest.
    let total_keys = N_POS * NW_KEYS;
    let mut counts: Vec<u32> = vec![0; total_keys];
    for pos in 0..N_POS {
        let need_n = need_north_border(pos);
        let need_e = need_east_border(pos);
        let need_s = need_south_border(pos);
        let need_w = need_west_border(pos);
        for pr in piece_rots.iter() {
            if (pr.n == BORDER) != need_n { continue; }
            if (pr.e == BORDER) != need_e { continue; }
            if (pr.s == BORDER) != need_s { continue; }
            if (pr.w == BORDER) != need_w { continue; }
            let key = (pr.n as usize) * N_COLORS + (pr.w as usize);
            counts[pos * NW_KEYS + key] += 1;
        }
    }

    // Build CSR-style entries with a SENTINEL u32::MAX after each bucket.
    // bucket_starts[k] is the start of bucket k in `entries`; the bucket
    // is terminated when the inner loop reads SENTINEL.
    let mut bucket_starts: Vec<u32> = vec![0; total_keys + 1];
    let mut acc: u32 = 0;
    for k in 0..total_keys {
        bucket_starts[k] = acc;
        // Each bucket: [data..., SENTINEL]. Empty bucket: just [SENTINEL].
        acc += counts[k] + 1;
    }
    bucket_starts[total_keys] = acc;

    let mut entries: Vec<u32> = vec![SENTINEL; acc as usize];
    let mut cursor_fill: Vec<u32> = bucket_starts.clone();
    // counts → fill positions; SENTINEL is already there for empty buckets.
    for pos in 0..N_POS {
        let need_n = need_north_border(pos);
        let need_e = need_east_border(pos);
        let need_s = need_south_border(pos);
        let need_w = need_west_border(pos);
        for pr in piece_rots.iter() {
            if (pr.n == BORDER) != need_n { continue; }
            if (pr.e == BORDER) != need_e { continue; }
            if (pr.s == BORDER) != need_s { continue; }
            if (pr.w == BORDER) != need_w { continue; }
            let key = (pr.n as usize) * N_COLORS + (pr.w as usize);
            let idx = pos * NW_KEYS + key;
            let dst = cursor_fill[idx] as usize;
            entries[dst] = pack_entry(pr.piece_id, pr.rot, pr.s, pr.e);
            cursor_fill[idx] += 1;
        }
    }

    // Sort each non-empty bucket by piece-id rarity (rare first, like vanilla_fastest).
    let mut pid_count: [u32; N_PIECES] = [0; N_PIECES];
    for &e in &entries {
        if e != SENTINEL { pid_count[entry_pid(e) as usize] += 1; }
    }
    for k in 0..total_keys {
        let s = bucket_starts[k] as usize;
        let e_end = bucket_starts[k + 1] as usize - 1; // exclude sentinel slot
        if e_end > s + 1 {
            entries[s..e_end].sort_by_key(|&e| pid_count[entry_pid(e) as usize]);
        }
    }

    // Stats reporting.
    let nonempty = (0..total_keys).filter(|&k| {
        bucket_starts[k + 1] - bucket_starts[k] > 1
    }).count();
    eprintln!(
        "[vanilla_v2] piece_rots={} buckets={} non_empty={}",
        piece_rots.len(),
        total_keys,
        nonempty
    );

    // Search state — all stack-allocated.
    // 256-bit bitset as [u64; 4]; LLVM keeps it in L1 (32 bytes).
    let mut used: [u64; 4] = [0; 4];
    let mut chosen: [u32; N_POS] = [0; N_POS];
    let mut frame_cursor: [u32; N_POS] = [0; N_POS];

    // Raw pointers for the hottest reads.
    let entries_ptr = entries.as_ptr();
    let bucket_starts_ptr = bucket_starts.as_ptr();

    let t0 = Instant::now();
    let deadline_us = (budget_ms as u128) * 1000;

    let mut placements: u64 = 0;
    let mut backtracks: u64 = 0;
    let mut max_depth: u32 = 0;
    let mut depth: usize = 0;

    let init_key = (BORDER as usize) * N_COLORS + (BORDER as usize);
    frame_cursor[0] = unsafe { *bucket_starts_ptr.add(init_key) };

    'outer: loop {
        if (placements & 0x3FFFF) == 0 && t0.elapsed().as_micros() >= deadline_us {
            break 'outer;
        }

        let mut cur = unsafe { *frame_cursor.get_unchecked(depth) };
        let mut found: u32 = SENTINEL;
        // Sentinel-terminated walk through the candidate bucket.
        loop {
            let entry = unsafe { *entries_ptr.add(cur as usize) };
            if entry == SENTINEL { break; }
            let pid = ((entry >> 12) & 0x1FF) as usize;
            let word = pid >> 6;
            let bit = 1u64 << (pid & 63);
            if (unsafe { *used.get_unchecked(word) } & bit) != 0 {
                cur += 1;
                continue;
            }
            found = entry;
            unsafe { *used.get_unchecked_mut(word) |= bit; }
            cur += 1;
            break;
        }

        if found != SENTINEL {
            unsafe {
                *chosen.get_unchecked_mut(depth) = found;
                *frame_cursor.get_unchecked_mut(depth) = cur;
            }
            placements += 1;
            depth += 1;
            if depth as u32 > max_depth {
                max_depth = depth as u32;
            }
            if depth == N_POS {
                depth -= 1;
                let pid = entry_pid(unsafe { *chosen.get_unchecked(depth) }) as usize;
                unsafe {
                    *used.get_unchecked_mut(pid >> 6) &= !(1u64 << (pid & 63));
                }
                continue;
            }
            // Compute new cursor for depth `depth`.
            let pos = depth;
            let n_color = if pos < N {
                BORDER
            } else {
                entry_s(unsafe { *chosen.get_unchecked(pos - N) })
            };
            let w_color = if pos % N == 0 {
                BORDER
            } else {
                entry_e(unsafe { *chosen.get_unchecked(pos - 1) })
            };
            let key = (n_color as usize) * N_COLORS + (w_color as usize);
            let bkt_idx = pos * NW_KEYS + key;
            unsafe {
                *frame_cursor.get_unchecked_mut(depth) =
                    *bucket_starts_ptr.add(bkt_idx);
            }
        } else {
            // Backtrack.
            backtracks += 1;
            if depth == 0 { break 'outer; }
            depth -= 1;
            let pid = entry_pid(unsafe { *chosen.get_unchecked(depth) }) as usize;
            unsafe {
                *used.get_unchecked_mut(pid >> 6) &= !(1u64 << (pid & 63));
            }
            // Advance cursor for retry at this depth.
            unsafe {
                *frame_cursor.get_unchecked_mut(depth) += 0; // no-op: cur was already advanced before placement
            }
        }
    }

    let elapsed = t0.elapsed();
    let pps = (placements as f64) / elapsed.as_secs_f64();
    let bps = (backtracks as f64) / elapsed.as_secs_f64();
    println!(
        "{{\"profile\":\"vanilla_v2\",\"budget_ms\":{},\"elapsed_ms\":{},\"placements\":{},\"backtracks\":{},\"max_depth\":{},\"placements_per_sec\":{:.0},\"backtracks_per_sec\":{:.0}}}",
        budget_ms,
        elapsed.as_millis(),
        placements,
        backtracks,
        max_depth,
        pps,
        bps
    );
}
