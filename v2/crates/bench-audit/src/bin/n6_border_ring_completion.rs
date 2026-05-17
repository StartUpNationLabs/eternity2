// Vol-122 N6 — 4-corner + border-ring completion enumerator.
//
// For each 4-tuple of piece-disjoint corner clusters (TL, TR, BL, BR),
// check if the 4 unfilled border segments (10 cells each) can be filled
// using the 40 remaining edge pieces such that:
//   - All consecutive border edges match colors.
//   - All 40 pieces are distinct AND not used by the 4 clusters.
//
// Strategy:
//   1. Iterate 4-cluster combinations with piece-disjoint pruning.
//   2. For each, do a 4-segment chain enumeration with shared piece-set.
//      Use backtracking: fill segments in order, tracking pieces used.
//   3. Store any (cluster 4-tuple, segment 4-tuple) that completes.
//
// Speed estimate: 10^12 piece-disjoint cluster combos × ~1ms chain check
// = 10^9 seconds (~30 years). Too slow naively.
//
// Optimization plan:
//   - Pre-compute per-cluster: the 2 BORDER-FACING colors (row strip start, col strip start).
//   - Group clusters by their (row_start_color, col_start_color) pair.
//   - For each (TL_row_color, TR_row_color) pair, pre-compute reachability of row-0
//     segment 10-cell chains with ALL edge pieces (no piece-set restriction yet).
//   - For each 4-cluster tuple, look up reachability per segment.
//   - If reachable WITHOUT piece-set restriction, then do the full piece-aware enumeration.
//
// This cuts to: 10^12 cluster tuples × 10ns reachability lookup = 10^4 seconds (~3 hours).

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::io::Write;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use rusqlite::{params, Connection};
use rayon::prelude::*;

#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
struct PieceSet { low: u128, high: u128 }
impl PieceSet {
    fn new() -> Self { Self { low: 0, high: 0 } }
    fn set(&mut self, pid: u16) {
        if pid < 128 { self.low |= 1u128 << pid; }
        else { self.high |= 1u128 << (pid - 128); }
    }
    fn or(&self, other: &Self) -> Self {
        Self { low: self.low | other.low, high: self.high | other.high }
    }
    fn intersects(&self, other: &Self) -> bool {
        (self.low & other.low) != 0 || (self.high & other.high) != 0
    }
    fn contains(&self, pid: u16) -> bool {
        if pid < 128 { (self.low >> pid) & 1 == 1 }
        else { (self.high >> (pid - 128)) & 1 == 1 }
    }
}

fn rot_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    match r {
        0 => e,
        1 => [e[3], e[0], e[1], e[2]],
        2 => [e[2], e[3], e[0], e[1]],
        _ => [e[1], e[2], e[3], e[0]],
    }
}

#[derive(Clone, Debug)]
struct Cluster {
    id: i64,
    pieces: PieceSet,
    /// For TL: row-0 east endpoint color (R of (0,2)).
    /// For TR: row-0 west endpoint color (L of (0,13)).
    /// For BL: row-15 east endpoint color (R of (15,2)).
    /// For BR: row-15 west endpoint color (L of (15,13)).
    row_color: u8,
    /// For TL: col-0 south endpoint color (B of (2,0)).
    /// For TR: col-15 south endpoint color (B of (2,15)).
    /// For BL: col-0 north endpoint color (T of (13,0)).
    /// For BR: col-15 north endpoint color (T of (13,15)).
    col_color: u8,
}

fn load_clusters(conn: &Connection, corner: char, pieces: &[[u8; 4]]) -> Vec<Cluster> {
    let label = match corner { 'L' => "TL", 'R' => "TR", 'l' => "BL", 'r' => "BR", _ => panic!() };
    let q = format!("SELECT id,
        p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot,
        p3_pid, p3_rot, p4_pid, p4_rot, p5_pid, p5_rot,
        p6_pid, p6_rot, p7_pid, p7_rot, p8_pid, p8_rot
        FROM clusters WHERE corner = '{}' ORDER BY id", label);
    let mut stmt = conn.prepare(&q).expect("prepare");
    let rows: Vec<Cluster> = stmt.query_map([], |r| {
        let id: i64 = r.get(0)?;
        let mut pids = [0u16; 9];
        let mut rots = [0u8; 9];
        let mut pset = PieceSet::new();
        for i in 0..9 {
            let pid: i64 = r.get(1 + i * 2)?;
            let rot: i64 = r.get(1 + i * 2 + 1)?;
            pids[i] = pid as u16;
            rots[i] = rot as u8;
            pset.set(pid as u16);
        }
        let (row_color, col_color) = match corner {
            'L' => {
                let e_row = rot_edges(pieces[pids[2] as usize], rots[2]);
                let e_col = rot_edges(pieces[pids[6] as usize], rots[6]);
                (e_row[1], e_col[2])  // R of (0,2), B of (2,0)
            }
            'R' => {
                let e_row = rot_edges(pieces[pids[0] as usize], rots[0]);
                let e_col = rot_edges(pieces[pids[8] as usize], rots[8]);
                (e_row[3], e_col[2])  // L of (0,13), B of (2,15)
            }
            'l' => {
                let e_row = rot_edges(pieces[pids[8] as usize], rots[8]);
                let e_col = rot_edges(pieces[pids[0] as usize], rots[0]);
                (e_row[1], e_col[0])  // R of (15,2), T of (13,0)
            }
            'r' => {
                let e_row = rot_edges(pieces[pids[6] as usize], rots[6]);
                let e_col = rot_edges(pieces[pids[2] as usize], rots[2]);
                (e_row[3], e_col[0])  // L of (15,13), T of (13,15)
            }
            _ => panic!(),
        };
        Ok(Cluster { id, pieces: pset, row_color, col_color })
    }).expect("query").filter_map(Result::ok).collect();
    rows
}

#[derive(Clone, Copy, Debug)]
struct EdgeOption {
    pid: u16,
    rot: u8,
    left: u8,   // input color for L→R traversal (or T→B for vertical)
    right: u8,  // output color
}

/// Pre-compute edge-piece options by border direction.
/// border_dir: 0=top (T=0, L→R), 1=right (R=0, T→B), 2=bot (B=0, L→R), 3=left (L=0, T→B).
fn precompute_edge_options(pieces: &[[u8; 4]]) -> [Vec<EdgeOption>; 4] {
    let mut by_dir: [Vec<EdgeOption>; 4] = Default::default();
    for (pid, e) in pieces.iter().enumerate() {
        let zeros = e.iter().filter(|&&x| x == 0).count();
        if zeros != 1 { continue; }
        for rot in 0..4u8 {
            let re = rot_edges(*e, rot);
            if re[0] == 0 {
                by_dir[0].push(EdgeOption { pid: pid as u16, rot, left: re[3], right: re[1] });
            }
            if re[1] == 0 {
                by_dir[1].push(EdgeOption { pid: pid as u16, rot, left: re[0], right: re[2] });
            }
            if re[2] == 0 {
                by_dir[2].push(EdgeOption { pid: pid as u16, rot, left: re[3], right: re[1] });
            }
            if re[3] == 0 {
                by_dir[3].push(EdgeOption { pid: pid as u16, rot, left: re[0], right: re[2] });
            }
        }
    }
    by_dir
}

/// Bucket edge options by their LEFT color. Returns options[dir][left_color] = Vec<EdgeOption>.
/// This eliminates per-step linear scans.
fn bucket_options_by_left(opts: &[Vec<EdgeOption>; 4]) -> [Vec<Vec<EdgeOption>>; 4] {
    let mut buckets: [Vec<Vec<EdgeOption>>; 4] = Default::default();
    for dir in 0..4 {
        buckets[dir] = vec![Vec::new(); 32];
        for opt in &opts[dir] {
            buckets[dir][opt.left as usize].push(*opt);
        }
    }
    buckets
}

/// Pre-compute (start_color, end_color) → existence-of-path matrix for 10-cell chain.
/// Independent of piece-uniqueness (= "loose" reachability).
/// Returns a 32x32 boolean matrix for each direction.
fn build_loose_reach_matrix(opts: &[EdgeOption], n_steps: usize) -> [[bool; 32]; 32] {
    let mut m = [[false; 32]; 32];
    for start in 0..32u8 {
        let mut cur = [false; 32];
        cur[start as usize] = true;
        for _ in 0..n_steps {
            let mut next = [false; 32];
            for opt in opts {
                if cur[opt.left as usize] {
                    next[opt.right as usize] = true;
                }
            }
            cur = next;
        }
        for end in 0..32 {
            m[start as usize][end] = cur[end];
        }
    }
    m
}

/// Sequentially fill 4 border chains (each 10 cells) with edge pieces.
/// Returns true if any joint assignment exists with all 4 chains valid and
/// piece-uniqueness maintained across all 40 pieces.
///
/// Returns true if found OR if budget exhausted (optimistic — false positives possible).
const TIGHT_NODE_BUDGET: u64 = 50_000;

#[allow(clippy::too_many_arguments)]
#[inline]
fn four_chain_jointly_exists(
    top_start: u8, top_end: u8,
    bot_start: u8, bot_end: u8,
    left_start: u8, left_end: u8,
    right_start: u8, right_end: u8,
    buckets: &[Vec<Vec<EdgeOption>>; 4],
    used_by_clusters: &PieceSet,
) -> bool {
    let mut used = *used_by_clusters;
    let mut budget: u64 = TIGHT_NODE_BUDGET;
    // Chain 0: top. Chain 1: bot. Chain 2: left. Chain 3: right.
    solve_chain(0, top_start, top_end, &buckets[0], &mut used, &mut budget,
        bot_start, bot_end, &buckets[2],
        left_start, left_end, &buckets[3],
        right_start, right_end, &buckets[1])
}

#[allow(clippy::too_many_arguments)]
fn solve_chain(
    step: usize,
    input: u8, target_end: u8,
    bucket0: &Vec<Vec<EdgeOption>>,
    used: &mut PieceSet,
    budget: &mut u64,
    bot_s: u8, bot_e: u8, bucket1: &Vec<Vec<EdgeOption>>,
    left_s: u8, left_e: u8, bucket2: &Vec<Vec<EdgeOption>>,
    right_s: u8, right_e: u8, bucket3: &Vec<Vec<EdgeOption>>,
) -> bool {
    if *budget == 0 { return true; }  // optimistic timeout
    *budget -= 1;
    if step == 10 {
        if input != target_end { return false; }
        return solve_chain1(0, bot_s, bot_e, bucket1, used, budget,
            left_s, left_e, bucket2, right_s, right_e, bucket3);
    }
    for &opt in &bucket0[input as usize] {
        if used.contains(opt.pid) { continue; }
        used.set(opt.pid);
        if solve_chain(step + 1, opt.right, target_end, bucket0, used, budget,
            bot_s, bot_e, bucket1, left_s, left_e, bucket2, right_s, right_e, bucket3) {
            return true;
        }
        if opt.pid < 128 { used.low &= !(1u128 << opt.pid); }
        else { used.high &= !(1u128 << (opt.pid - 128)); }
    }
    false
}

#[allow(clippy::too_many_arguments)]
fn solve_chain1(
    step: usize,
    input: u8, target_end: u8,
    bucket1: &Vec<Vec<EdgeOption>>,
    used: &mut PieceSet,
    budget: &mut u64,
    left_s: u8, left_e: u8, bucket2: &Vec<Vec<EdgeOption>>,
    right_s: u8, right_e: u8, bucket3: &Vec<Vec<EdgeOption>>,
) -> bool {
    if *budget == 0 { return true; }
    *budget -= 1;
    if step == 10 {
        if input != target_end { return false; }
        return solve_chain2(0, left_s, left_e, bucket2, used, budget,
            right_s, right_e, bucket3);
    }
    for &opt in &bucket1[input as usize] {
        if used.contains(opt.pid) { continue; }
        used.set(opt.pid);
        if solve_chain1(step + 1, opt.right, target_end, bucket1, used, budget,
            left_s, left_e, bucket2, right_s, right_e, bucket3) {
            return true;
        }
        if opt.pid < 128 { used.low &= !(1u128 << opt.pid); }
        else { used.high &= !(1u128 << (opt.pid - 128)); }
    }
    false
}

fn solve_chain2(
    step: usize,
    input: u8, target_end: u8,
    bucket2: &Vec<Vec<EdgeOption>>,
    used: &mut PieceSet,
    budget: &mut u64,
    right_s: u8, right_e: u8, bucket3: &Vec<Vec<EdgeOption>>,
) -> bool {
    if *budget == 0 { return true; }
    *budget -= 1;
    if step == 10 {
        if input != target_end { return false; }
        return solve_chain3(0, right_s, right_e, bucket3, used, budget);
    }
    for &opt in &bucket2[input as usize] {
        if used.contains(opt.pid) { continue; }
        used.set(opt.pid);
        if solve_chain2(step + 1, opt.right, target_end, bucket2, used, budget,
            right_s, right_e, bucket3) {
            return true;
        }
        if opt.pid < 128 { used.low &= !(1u128 << opt.pid); }
        else { used.high &= !(1u128 << (opt.pid - 128)); }
    }
    false
}

fn solve_chain3(
    step: usize,
    input: u8, target_end: u8,
    bucket3: &Vec<Vec<EdgeOption>>,
    used: &mut PieceSet,
    budget: &mut u64,
) -> bool {
    if *budget == 0 { return true; }
    *budget -= 1;
    if step == 10 {
        return input == target_end;
    }
    for &opt in &bucket3[input as usize] {
        if used.contains(opt.pid) { continue; }
        used.set(opt.pid);
        if solve_chain3(step + 1, opt.right, target_end, bucket3, used, budget) {
            return true;
        }
        if opt.pid < 128 { used.low &= !(1u128 << opt.pid); }
        else { used.high &= !(1u128 << (opt.pid - 128)); }
    }
    false
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut in_db = PathBuf::from("output/vol-122/n1_corner_3x3_clusters.sqlite");
    let mut out_db = PathBuf::from("output/vol-122/n6_border_ring_complete.sqlite");
    let mut max_iter: u64 = u64::MAX;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--in" => in_db = PathBuf::from(args.next().unwrap()),
            "--out" => out_db = PathBuf::from(args.next().unwrap()),
            "--max-iter" => max_iter = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    let conn_in = Connection::open(&in_db).expect("open");
    let tl = load_clusters(&conn_in, 'L', &pieces);
    let tr = load_clusters(&conn_in, 'R', &pieces);
    let bl = load_clusters(&conn_in, 'l', &pieces);
    let br = load_clusters(&conn_in, 'r', &pieces);
    eprintln!("clusters: TL={} TR={} BL={} BR={}", tl.len(), tr.len(), bl.len(), br.len());

    let edge_opts = precompute_edge_options(&pieces);
    let buckets = bucket_options_by_left(&edge_opts);

    // Pre-compute loose reachability matrices per direction (10-cell chains)
    let loose_top = build_loose_reach_matrix(&edge_opts[0], 10);
    let loose_right = build_loose_reach_matrix(&edge_opts[1], 10);
    let loose_bot = build_loose_reach_matrix(&edge_opts[2], 10);
    let loose_left = build_loose_reach_matrix(&edge_opts[3], 10);

    eprintln!("Pre-computed loose 10-cell reachability matrices (32x32 each).");

    std::fs::create_dir_all(out_db.parent().unwrap()).ok();
    let _ = std::fs::remove_file(&out_db);
    let conn_out = Connection::open(&out_db).expect("open out");
    conn_out.execute_batch("
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = OFF;
        CREATE TABLE four_corner_borders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tl_id INTEGER NOT NULL,
            tr_id INTEGER NOT NULL,
            bl_id INTEGER NOT NULL,
            br_id INTEGER NOT NULL
        );
    ").expect("create");

    let t0 = Instant::now();
    let explored = std::sync::Arc::new(AtomicU64::new(0));
    let l1_pass = std::sync::Arc::new(AtomicU64::new(0));
    let loose_pass = std::sync::Arc::new(AtomicU64::new(0));
    let tight_pass = std::sync::Arc::new(AtomicU64::new(0));
    let tl_processed = std::sync::Arc::new(AtomicU64::new(0));
    let inserted = std::sync::Arc::new(AtomicU64::new(0));
    let done_flag = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));

    // Spawn a heartbeat thread that polls atomics every 2 sec.
    {
        let explored_c = explored.clone();
        let l1_c = l1_pass.clone();
        let loose_c = loose_pass.clone();
        let tight_c = tight_pass.clone();
        let tl_c = tl_processed.clone();
        let ins_c = inserted.clone();
        let done_c = done_flag.clone();
        let n_tl = tl.len();
        std::thread::spawn(move || {
            while !done_c.load(Ordering::Relaxed) {
                std::thread::sleep(std::time::Duration::from_secs(2));
                let e = explored_c.load(Ordering::Relaxed);
                let elapsed = t0.elapsed().as_secs_f64();
                eprintln!("  TL={}/{} explored={} L1={} loose={} tight={} stored={} rate={:.0}/s elapsed={:.1}s",
                    tl_c.load(Ordering::Relaxed), n_tl, e,
                    l1_c.load(Ordering::Relaxed),
                    loose_c.load(Ordering::Relaxed),
                    tight_c.load(Ordering::Relaxed),
                    ins_c.load(Ordering::Relaxed),
                    e as f64 / elapsed.max(1e-6), elapsed);
                std::io::stderr().flush().ok();
            }
        });
    }

    // Each thread collects results in a local Vec, merged at the end into SQLite.
    let store_results: Mutex<Vec<(i64, i64, i64, i64)>> = Mutex::new(Vec::new());

    tl.par_iter().for_each(|tl_c| {
        let _idx = tl_processed.fetch_add(1, Ordering::Relaxed) + 1;
        // Early stop check
        if explored.load(Ordering::Relaxed) >= max_iter { return; }

        let mut local_explored: u64 = 0;
        let mut local_l1: u64 = 0;
        let mut local_loose: u64 = 0;
        let mut local_tight: u64 = 0;
        let mut local_stored: Vec<(i64, i64, i64, i64)> = Vec::new();
        let mut last_flush: u64 = 0;

        for tr_c in &tr {
            if tl_c.pieces.intersects(&tr_c.pieces) { continue; }
            if !loose_top[tl_c.row_color as usize][tr_c.row_color as usize] { continue; }
            let tl_tr = tl_c.pieces.or(&tr_c.pieces);

            for bl_c in &bl {
                if tl_tr.intersects(&bl_c.pieces) { continue; }
                if !loose_left[tl_c.col_color as usize][bl_c.col_color as usize] { continue; }
                let tl_tr_bl = tl_tr.or(&bl_c.pieces);

                for br_c in &br {
                    local_explored += 1;
                    // Flush counters more aggressively for visibility
                    if local_explored - last_flush >= 10_000 {
                        explored.fetch_add(local_explored - last_flush, Ordering::Relaxed);
                        l1_pass.fetch_add(local_l1, Ordering::Relaxed);
                        loose_pass.fetch_add(local_loose, Ordering::Relaxed);
                        tight_pass.fetch_add(local_tight, Ordering::Relaxed);
                        last_flush = local_explored;
                        local_l1 = 0; local_loose = 0; local_tight = 0;
                    }
                    if tl_tr_bl.intersects(&br_c.pieces) { continue; }
                    local_l1 += 1;

                    if !loose_bot[bl_c.row_color as usize][br_c.row_color as usize] { continue; }
                    if !loose_right[tr_c.col_color as usize][br_c.col_color as usize] { continue; }
                    local_loose += 1;

                    let combined = tl_tr_bl.or(&br_c.pieces);
                    if !four_chain_jointly_exists(
                        tl_c.row_color, tr_c.row_color,
                        bl_c.row_color, br_c.row_color,
                        tl_c.col_color, bl_c.col_color,
                        tr_c.col_color, br_c.col_color,
                        &buckets, &combined
                    ) { continue; }
                    local_tight += 1;

                    local_stored.push((tl_c.id, tr_c.id, bl_c.id, br_c.id));
                }
            }
        }
        // Final flush of any unflushed remainder
        explored.fetch_add(local_explored - last_flush, Ordering::Relaxed);
        l1_pass.fetch_add(local_l1, Ordering::Relaxed);
        loose_pass.fetch_add(local_loose, Ordering::Relaxed);
        tight_pass.fetch_add(local_tight, Ordering::Relaxed);
        if !local_stored.is_empty() {
            let mut g = store_results.lock().unwrap();
            g.extend(local_stored);
            inserted.store(g.len() as u64, Ordering::Relaxed);
        }
    });

    // Signal heartbeat thread to exit.
    done_flag.store(true, Ordering::Relaxed);
    // Drain results into SQLite (single thread)
    let results = store_results.into_inner().unwrap();
    let mut tx = conn_out.unchecked_transaction().expect("tx");
    let mut stmt = tx.prepare(
        "INSERT INTO four_corner_borders (tl_id, tr_id, bl_id, br_id) VALUES (?, ?, ?, ?)"
    ).expect("prepare");
    for (tl_id, tr_id, bl_id, br_id) in &results {
        stmt.execute(params![tl_id, tr_id, bl_id, br_id]).expect("insert");
    }
    drop(stmt);
    tx.commit().expect("commit");

    let n_rows: i64 = conn_out.query_row("SELECT COUNT(*) FROM four_corner_borders", [], |r| r.get(0)).unwrap();
    eprintln!("\n=== TOTAL ===");
    eprintln!("explored: {}", explored.load(Ordering::Relaxed));
    eprintln!("L1 pass: {}", l1_pass.load(Ordering::Relaxed));
    eprintln!("loose pass: {}", loose_pass.load(Ordering::Relaxed));
    eprintln!("tight pass: {}", tight_pass.load(Ordering::Relaxed));
    eprintln!("inserted: {}", n_rows);
    eprintln!("elapsed: {:.2}s", t0.elapsed().as_secs_f64());
    eprintln!("wrote: {}", out_db.display());
}
