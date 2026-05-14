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
    let mut pin_hints = false;
    let mut save_best: Option<PathBuf> = None;
    let mut threads: usize = 1;
    // Vol-34 T1 — periodic deep-partial sampling for diverse basin seeding.
    let mut snapshot_dir: Option<PathBuf> = None;
    let mut snapshot_interval_ms: u64 = 60_000;
    let mut snapshot_min_depth: u32 = 200;
    // Vol-34 T1b — when true, snapshot ANY visit at depth ≥ min-depth that
    // satisfies the interval gate, not just visits that beat current
    // max_depth. Boosts basin diversity at the cost of more disk writes.
    let mut snapshot_on_visit = false;
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget"); i += 2; }
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--solve" => { want_solve = true; i += 1; }
            "--pin-hints" => { pin_hints = true; i += 1; }
            "--save-best" => { save_best = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--threads" => { threads = raw[i + 1].parse().expect("threads"); i += 2; }
            "--snapshot-dir" => { snapshot_dir = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--snapshot-interval-ms" => {
                snapshot_interval_ms = raw[i + 1].parse().expect("snapshot-interval-ms");
                i += 2;
            }
            "--snapshot-min-depth" => {
                snapshot_min_depth = raw[i + 1].parse().expect("snapshot-min-depth");
                i += 2;
            }
            "--snapshot-on-visit" => { snapshot_on_visit = true; i += 1; }
            other => panic!("unknown arg: {other}"),
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
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

    // Bucket sort: within each bucket, sort entries by piece-id RARITY (descending).
    // Pieces appearing in fewer buckets are less likely to be already placed.
    // Heuristic: rare pieces first → 'used' check fails earlier → fewer iterations on avg.
    let mut pid_global_count: [u32; N_PIECES] = [0; N_PIECES];
    for &entry in &bucket_data {
        pid_global_count[(entry >> 12) as usize] += 1;
    }
    for pos in 0..N_POS {
        for key in 0..NW_KEYS {
            let idx = pos * NW_KEYS + key;
            let start = bucket_starts[idx] as usize;
            let end = bucket_starts[idx + 1] as usize;
            if end - start <= 1 { continue; }
            bucket_data[start..end].sort_by_key(|&e| pid_global_count[(e >> 12) as usize]);
        }
    }
    eprintln!("[init] buckets sorted by pid rarity (ascending count = rare first)");

    // Hint table: hint_at[pos] = Some(packed_entry) for hint positions, None otherwise.
    // When pin_hints is true, at hint positions we ONLY consider the hint entry.
    let mut hint_at: Vec<Option<u32>> = vec![None; N_POS];
    if pin_hints {
        for h in hints.hints.iter() {
            let pos = h.position as usize;
            let pid = h.piece_id;
            let rot = h.rotation.as_u8();
            // Find the matching piece_rot to pack
            let pr = piece_rots.iter()
                .find(|pr| pr.piece_id == pid && pr.rot == rot)
                .expect("hint piece+rot not found");
            hint_at[pos] = Some(pack_entry(pr.piece_id, pr.rot, pr.s, pr.e));
        }
        eprintln!("[init] {} hints pinned: {:?}",
            hint_at.iter().filter(|h| h.is_some()).count(),
            hint_at.iter().enumerate().filter_map(|(p, h)| h.map(|_| p)).collect::<Vec<_>>(),
        );
    }

    // Hint pool: bucket_data-like vec where hint positions get their own (single-entry)
    // bucket. We append all hint entries to bucket_data, and override
    // bucket_starts/end logic to point here for hint positions.
    let hint_pool_start = bucket_data.len() as u32;
    for h in &hint_at {
        if let Some(entry) = h {
            bucket_data.push(*entry);
        }
    }
    // hint_entry_idx[pos] = index into bucket_data where this hint's entry lives, or u32::MAX if no hint.
    let mut hint_entry_idx: Vec<u32> = vec![u32::MAX; N_POS];
    {
        let mut idx = hint_pool_start;
        for (pos, h) in hint_at.iter().enumerate() {
            if h.is_some() {
                hint_entry_idx[pos] = idx;
                idx += 1;
            }
        }
    }

    let t0 = Instant::now();
    let deadline = t0 + std::time::Duration::from_millis(budget_ms);

    // Aggregate stats across threads (atomics)
    let total_placements_atomic = AtomicU64::new(0);
    let total_backtracks_atomic = AtomicU64::new(0);
    let max_depth_atomic = AtomicU64::new(0);
    let solved_count_atomic = AtomicU64::new(0);

    eprintln!("[init] running {} worker(s) for {} ms", threads, budget_ms);

    // Per-thread results
    #[derive(Clone)]
    struct ThreadResult {
        thread_id: usize,
        placements: u64,
        backtracks: u64,
        max_depth: u32,
        solved: u64,
        best_chosen: Vec<u32>,
        depth_placements: Vec<u64>,
        bucket_data_seed: u64,
    }

    let thread_results: Vec<ThreadResult> = (0..threads).into_par_iter().map(|thread_id| {
        // Per-thread bucket_data: clone the global, then shuffle within each bucket
        // using thread_id as seed (thread 0 keeps the rare-first order from the global).
        let mut my_bucket_data = bucket_data.clone();
        if thread_id > 0 {
            // xorshift64 with seed = thread_id+0xDEADBEEF
            let mut rng_state: u64 = (thread_id as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15)
                .wrapping_add(0xDEAD_BEEF_CAFE_BABE);
            let mut next_rand = |state: &mut u64| -> u64 {
                *state ^= *state << 13;
                *state ^= *state >> 7;
                *state ^= *state << 17;
                *state
            };
            // Fisher-Yates per bucket
            for pos in 0..N_POS {
                for key in 0..NW_KEYS {
                    let idx = pos * NW_KEYS + key;
                    let start = bucket_starts[idx] as usize;
                    let end = bucket_starts[idx + 1] as usize;
                    let len = end - start;
                    if len <= 1 { continue; }
                    for i in (1..len).rev() {
                        let j = (next_rand(&mut rng_state) as usize) % (i + 1);
                        my_bucket_data.swap(start + i, start + j);
                    }
                }
            }
        }

        // Per-thread search state
        let mut chosen: Vec<u32> = vec![0u32; N_POS];
        let mut frame_cursor: Vec<u32> = vec![0u32; N_POS + 1];
        let mut bucket_start_at_depth: Vec<u32> = vec![0u32; N_POS];
        let mut bucket_end_at_depth: Vec<u32> = vec![0u32; N_POS];
        let mut used: [bool; N_PIECES] = [false; N_PIECES];

        let mut total_placements: u64 = 0;
        let mut total_backtracks: u64 = 0;
        let mut max_depth: u32 = 0;
        let mut solved_count: u64 = 0;
        let mut depth_placements: Vec<u64> = vec![0u64; N_POS + 1];
        let mut best_depth: u32 = 0;
        let mut best_chosen: Vec<u32> = vec![0u32; N_POS];

        // Vol-34 T1 — periodic deep-partial snapshots
        let mut last_snapshot_ms: u64 = 0;
        let mut snapshot_index: u32 = 0;

        let mut depth: usize = 0;

        // Helper: enter depth d freshly (compute bucket).
        macro_rules! enter_fresh {
            ($d:expr) => {{
                let d = $d;
                let pos = d;
                let n_color = if pos < N { BORDER } else { entry_s(chosen[pos - N]) };
                let w_color = if pos % N == 0 { BORDER } else { entry_e(chosen[pos - 1]) };
                let hint_idx = hint_entry_idx[pos];
                if hint_idx != u32::MAX {
                    let hint_entry = my_bucket_data[hint_idx as usize];
                    let hint_pid = entry_piece_id(hint_entry);
                    let hint_rot = entry_rot(hint_entry);
                    let pr = &piece_rots[hint_pid as usize * N_ROT + hint_rot as usize];
                    if pr.n == n_color && pr.w == w_color {
                        bucket_start_at_depth[d] = hint_idx;
                        bucket_end_at_depth[d] = hint_idx + 1;
                        frame_cursor[d] = hint_idx;
                    } else {
                        bucket_start_at_depth[d] = 0;
                        bucket_end_at_depth[d] = 0;
                        frame_cursor[d] = 0;
                    }
                } else {
                    let key = (n_color as usize) * N_COLORS + (w_color as usize);
                    let bkt_idx = pos * NW_KEYS + key;
                    bucket_start_at_depth[d] = bucket_starts[bkt_idx];
                    bucket_end_at_depth[d] = bucket_starts[bkt_idx + 1];
                    frame_cursor[d] = bucket_starts[bkt_idx];
                }
            }};
        }

        enter_fresh!(0);

        'outer: loop {
            if (total_placements & 0x3FFFF) == 0 && Instant::now() >= deadline {
                break;
            }
            let end = bucket_end_at_depth[depth];
            let mut cur = frame_cursor[depth];
            let mut found = u32::MAX;
            while cur < end {
                let entry = my_bucket_data[cur as usize];
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
                let is_new_max = depth as u32 > max_depth;
                if is_new_max {
                    max_depth = depth as u32;
                    best_chosen.copy_from_slice(&chosen);
                    best_depth = max_depth;
                }
                // Vol-34 T1 snapshot logic: fire on a new max-depth, OR (if
                // --snapshot-on-visit) on ANY visit at depth ≥ min-depth.
                // Rate-limited by snapshot_interval_ms per thread.
                let depth_now = depth as u32;
                let snapshot_trigger = (is_new_max && depth_now >= snapshot_min_depth)
                    || (snapshot_on_visit && depth_now >= snapshot_min_depth);
                if snapshot_trigger {
                    if let Some(dir) = snapshot_dir.as_ref() {
                        let now_ms = t0.elapsed().as_millis() as u64;
                        if now_ms.saturating_sub(last_snapshot_ms) >= snapshot_interval_ms
                            || last_snapshot_ms == 0
                        {
                            last_snapshot_ms = now_ms;
                            let path = dir.join(format!(
                                "t{thread_id:02}_s{snapshot_index:03}_d{depth_now:03}.json"
                            ));
                            snapshot_index += 1;
                            // For new-max snapshots use best_chosen (which equals
                            // current chosen since we just copied). For on-visit
                            // snapshots use chosen directly.
                            let src = if is_new_max { &best_chosen } else { &chosen };
                            let mut snap: Vec<Option<(u16, u8)>> = vec![None; N_POS];
                            for p_i in 0..depth_now as usize {
                                let e = src[p_i];
                                snap[p_i] = Some((entry_piece_id(e), entry_rot(e)));
                            }
                            if pin_hints {
                                for h in hints.hints.iter() {
                                    let pp = h.position as usize;
                                    if snap[pp].is_none() {
                                        snap[pp] = Some((h.piece_id, h.rotation.as_u8()));
                                    }
                                }
                            }
                            let mut placement_json = String::from("{\"placement\": [");
                            for (p_i, slot) in snap.iter().enumerate() {
                                if p_i > 0 {
                                    placement_json.push(',');
                                }
                                match slot {
                                    None => placement_json.push_str("null"),
                                    Some((pid, rot)) => placement_json.push_str(&format!(
                                        "{{\"piece_id\":{pid},\"rotation\":{rot}}}"
                                    )),
                                }
                            }
                            placement_json.push_str("]}");
                            if let Some(parent) = path.parent() {
                                std::fs::create_dir_all(parent).ok();
                            }
                            if let Err(e) = std::fs::write(&path, &placement_json) {
                                eprintln!("[t{thread_id}] snapshot write failed: {e}");
                            }
                        }
                    }
                }
                if depth == N_POS {
                    solved_count += 1;
                    if want_solve {
                        eprintln!("[t{thread_id}] [solve] FOUND in {} ms", t0.elapsed().as_millis());
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
                if depth == 0 { break 'outer; }
                depth -= 1;
                total_backtracks += 1;
                let pid = (chosen[depth] >> 12) as usize;
                used[pid] = false;
                frame_cursor[depth] += 1;
            }
        }

        total_placements_atomic.fetch_add(total_placements, Ordering::Relaxed);
        total_backtracks_atomic.fetch_add(total_backtracks, Ordering::Relaxed);
        max_depth_atomic.fetch_max(max_depth as u64, Ordering::Relaxed);
        solved_count_atomic.fetch_add(solved_count, Ordering::Relaxed);

        let _ = best_depth;  // included in result
        ThreadResult {
            thread_id,
            placements: total_placements,
            backtracks: total_backtracks,
            max_depth,
            solved: solved_count,
            best_chosen,
            depth_placements,
            bucket_data_seed: thread_id as u64,
        }
    }).collect();

    // Pick global best across threads
    let global_best = thread_results.iter().max_by_key(|r| r.max_depth).expect("at least one thread");
    let best_chosen = global_best.best_chosen.clone();
    let best_depth = global_best.max_depth;
    let total_placements = total_placements_atomic.load(Ordering::Relaxed);
    let total_backtracks = total_backtracks_atomic.load(Ordering::Relaxed);
    let max_depth = max_depth_atomic.load(Ordering::Relaxed) as u32;
    let solved_count = solved_count_atomic.load(Ordering::Relaxed);

    // Aggregate per-depth placements
    let mut depth_placements: [u64; N_POS + 1] = [0u64; N_POS + 1];
    for r in &thread_results {
        for d in 0..=N_POS {
            depth_placements[d] += r.depth_placements[d];
        }
    }

    // Per-thread summary
    eprintln!("[per-thread] results:");
    for r in &thread_results {
        let pps = r.placements as f64 / t0.elapsed().as_secs_f64();
        eprintln!("  thread {}: depth={} placements={} ({:.0} pp/s)", r.thread_id, r.max_depth, r.placements, pps);
    }

    let mut best_score: u32 = 0;  // computed later

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

    // Compute matched edges on the best partial.
    // For each placed cell, check right and down edges against neighbours (if placed too).
    let mut matched_internal = 0u32;
    let mut matched_border = 0u32;
    for pos in 0..best_depth as usize {
        let entry = best_chosen[pos];
        let pid = entry_piece_id(entry) as usize;
        let rot = entry_rot(entry) as usize;
        let pr = &piece_rots[pid * N_ROT + rot];
        // East match (if right neighbour placed)
        let x = pos % N;
        let y = pos / N;
        if x + 1 < N {
            let np = pos + 1;
            if (np as u32) < best_depth {
                let np_entry = best_chosen[np];
                let np_pr = &piece_rots[entry_piece_id(np_entry) as usize * N_ROT + entry_rot(np_entry) as usize];
                if pr.e == np_pr.w { matched_internal += 1; }
            }
        }
        // South match
        if y + 1 < N {
            let np = pos + N;
            if (np as u32) < best_depth {
                let np_entry = best_chosen[np];
                let np_pr = &piece_rots[entry_piece_id(np_entry) as usize * N_ROT + entry_rot(np_entry) as usize];
                if pr.s == np_pr.n { matched_internal += 1; }
            }
        }
        // Border edges — count border-meets-border matches as matched
        if y == 0 && pr.n == BORDER { matched_border += 1; }
        if x == N - 1 && pr.e == BORDER { matched_border += 1; }
        if y == N - 1 && pr.s == BORDER { matched_border += 1; }
        if x == 0 && pr.w == BORDER { matched_border += 1; }
    }
    best_score = matched_internal + matched_border;
    eprintln!("[best-partial] depth={} matched_internal={} matched_border={} matched_total={}/480",
        best_depth, matched_internal, matched_border, best_score);

    // Construct a Board for canonical scoring + bucas URL.
    let mut board = Board::empty(&puzzle);
    for pos in 0..best_depth as usize {
        let entry = best_chosen[pos];
        let pid = entry_piece_id(entry);
        let rot_u8 = entry_rot(entry);
        if let Some(rot) = Rotation::from_u8(rot_u8) {
            board.place(pos as u32, PieceId::from(pid), rot);
        }
    }
    let bucas = bucas_url(&puzzle, &board, "size_16_official_eternity");
    eprintln!("[bucas] {}", bucas);

    // Save EACH THREAD's best partial as a separate file when --save-best is set + multi-thread.
    if let (true, Some(base_path)) = (threads > 1, save_best.as_ref()) {
        for r in &thread_results {
            let mut placement: Vec<Option<(u16, u8)>> = vec![None; N_POS];
            for pos in 0..r.max_depth as usize {
                let e = r.best_chosen[pos];
                placement[pos] = Some((entry_piece_id(e), entry_rot(e)));
            }
            if pin_hints {
                for h in hints.hints.iter() {
                    let pos = h.position as usize;
                    if placement[pos].is_none() {
                        placement[pos] = Some((h.piece_id, h.rotation.as_u8()));
                    }
                }
            }
            // Per-thread filename: insert ".tN." before extension
            let stem = base_path.file_stem().unwrap().to_string_lossy().to_string();
            let ext = base_path.extension().map(|e| e.to_string_lossy().to_string()).unwrap_or_else(|| "json".into());
            let parent = base_path.parent().unwrap_or(std::path::Path::new(""));
            let per_thread_path = parent.join(format!("{}.t{}.{}", stem, r.thread_id, ext));
            let mut json = String::from("{\"placement\": [");
            for (i, p) in placement.iter().enumerate() {
                if i > 0 { json.push(','); }
                match p {
                    None => json.push_str("null"),
                    Some((pid, rot)) => json.push_str(&format!("{{\"piece_id\":{},\"rotation\":{}}}", pid, rot)),
                }
            }
            json.push_str("]}");
            if let Some(parent) = per_thread_path.parent() {
                std::fs::create_dir_all(parent).ok();
            }
            std::fs::write(&per_thread_path, json).expect("write per-thread");
            eprintln!("[saved] thread {} → {} (depth={})", r.thread_id, per_thread_path.display(), r.max_depth);
        }
    }

    // Save best partial if requested
    if let Some(path) = save_best {
        let mut placement: Vec<Option<(u16, u8)>> = vec![None; N_POS];
        for pos in 0..best_depth as usize {
            let e = best_chosen[pos];
            placement[pos] = Some((entry_piece_id(e), entry_rot(e)));
        }
        // CRITICAL: if pin_hints, ALWAYS include hints in the saved partial
        // even if they're at positions beyond max_depth — otherwise downstream
        // ALNS will fill those positions with non-hint pieces, producing
        // boards that violate canonical 5-clue constraints.
        if pin_hints {
            for h in hints.hints.iter() {
                let pos = h.position as usize;
                if placement[pos].is_none() {
                    placement[pos] = Some((h.piece_id, h.rotation.as_u8()));
                }
            }
        }
        // Write pt_e2-format JSON
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
        std::fs::write(&path, json).expect("write save-best");
        eprintln!("[saved] best partial → {}", path.display());
    }
}
