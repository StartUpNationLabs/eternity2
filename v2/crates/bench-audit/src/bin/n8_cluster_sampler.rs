// Vol-122 N8 — Streaming sampler of (4 corner clusters + valid border ring)
// → partial board JSON outputs.
//
// For each random sample:
//   1. Pick 4 random clusters (one per corner), one tries until piece-disjoint.
//   2. Attempt to complete the 4 border segments (10 cells each) via joint
//      backtracker with node-budget.
//   3. If success, write 96-cell partial board JSON: 4 corners (36 cells) +
//      4 border strips (40 cells) + 20 cells of clusters' borders (already
//      in clusters) = 76 unique cells. Actually:
//        - 4 clusters × 9 cells = 36 cells (includes the 5 hint cells).
//        - 4 border segments × 10 cells = 40 cells.
//        - Total: 76 cells (well, but row 0 has 16 cells; clusters cover 5
//          cells each at row 0 corners — wait, TL covers (0,0),(0,1),(0,2)
//          = 3 row-0 cells. TR covers (0,13),(0,14),(0,15) = 3. So row 0 =
//          3+3+10 = 16 cells exact. Same for col 0, row 15, col 15.).
//
// Output: one JSON per success in output/vol-122/n8_samples/.
//
// Run for a fixed number of seconds, then exit.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::{Instant, Duration};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::io::Write;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use serde_json::json;
use rusqlite::Connection;
use rayon::prelude::*;

const SIDE: usize = 16;

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
    corner: char,  // 'L'=TL, 'R'=TR, 'l'=BL, 'r'=BR
    pids: [u16; 9],
    rots: [u8; 9],
    pieces: PieceSet,
    row_color: u8,
    col_color: u8,
}

fn load_clusters(conn: &Connection, corner_label: &str, pieces: &[[u8; 4]]) -> Vec<Cluster> {
    let label_char = match corner_label {
        "TL" => 'L', "TR" => 'R', "BL" => 'l', "BR" => 'r', _ => panic!(),
    };
    let q = format!("SELECT id,
        p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot,
        p3_pid, p3_rot, p4_pid, p4_rot, p5_pid, p5_rot,
        p6_pid, p6_rot, p7_pid, p7_rot, p8_pid, p8_rot
        FROM clusters WHERE corner = '{}' ORDER BY id", corner_label);
    let mut stmt = conn.prepare(&q).expect("prepare");
    stmt.query_map([], |r| {
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
        let (row_color, col_color) = match label_char {
            'L' => {
                let e_row = rot_edges(pieces[pids[2] as usize], rots[2]);
                let e_col = rot_edges(pieces[pids[6] as usize], rots[6]);
                (e_row[1], e_col[2])
            }
            'R' => {
                let e_row = rot_edges(pieces[pids[0] as usize], rots[0]);
                let e_col = rot_edges(pieces[pids[8] as usize], rots[8]);
                (e_row[3], e_col[2])
            }
            'l' => {
                let e_row = rot_edges(pieces[pids[8] as usize], rots[8]);
                let e_col = rot_edges(pieces[pids[0] as usize], rots[0]);
                (e_row[1], e_col[0])
            }
            'r' => {
                let e_row = rot_edges(pieces[pids[6] as usize], rots[6]);
                let e_col = rot_edges(pieces[pids[2] as usize], rots[2]);
                (e_row[3], e_col[0])
            }
            _ => panic!(),
        };
        Ok(Cluster { id, corner: label_char, pids, rots, pieces: pset, row_color, col_color })
    }).expect("query").filter_map(Result::ok).collect()
}

#[derive(Clone, Copy, Debug)]
struct EdgeOption { pid: u16, rot: u8, left: u8, right: u8 }

fn precompute_edge_options(pieces: &[[u8; 4]]) -> [Vec<EdgeOption>; 4] {
    let mut by_dir: [Vec<EdgeOption>; 4] = Default::default();
    for (pid, e) in pieces.iter().enumerate() {
        let zeros = e.iter().filter(|&&x| x == 0).count();
        if zeros != 1 { continue; }
        for rot in 0..4u8 {
            let re = rot_edges(*e, rot);
            if re[0] == 0 { by_dir[0].push(EdgeOption { pid: pid as u16, rot, left: re[3], right: re[1] }); }
            if re[1] == 0 { by_dir[1].push(EdgeOption { pid: pid as u16, rot, left: re[0], right: re[2] }); }
            if re[2] == 0 { by_dir[2].push(EdgeOption { pid: pid as u16, rot, left: re[3], right: re[1] }); }
            if re[3] == 0 { by_dir[3].push(EdgeOption { pid: pid as u16, rot, left: re[0], right: re[2] }); }
        }
    }
    by_dir
}

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

/// Try to fill one chain. Returns the (pids, rots) of the 10 cells if found.
/// `used` is updated with placed pieces on success.
fn try_solve_chain(
    n_cells: usize,
    start_input: u8,
    end_output: u8,
    bucket: &Vec<Vec<EdgeOption>>,
    used: &mut PieceSet,
    budget: &mut u64,
    result_pids: &mut Vec<u16>,
    result_rots: &mut Vec<u8>,
) -> bool {
    if *budget == 0 { return false; }
    *budget -= 1;
    if result_pids.len() == n_cells {
        return start_input == end_output;
    }
    for &opt in &bucket[start_input as usize] {
        if used.contains(opt.pid) { continue; }
        used.set(opt.pid);
        result_pids.push(opt.pid);
        result_rots.push(opt.rot);
        if try_solve_chain(n_cells, opt.right, end_output, bucket, used, budget,
            result_pids, result_rots) {
            return true;
        }
        result_pids.pop();
        result_rots.pop();
        if opt.pid < 128 { used.low &= !(1u128 << opt.pid); }
        else { used.high &= !(1u128 << (opt.pid - 128)); }
    }
    false
}

/// Fill all 4 border chains starting from cluster set. Returns full segment
/// data if successful (per-segment pids+rots), else None.
fn complete_border_ring(
    tl: &Cluster, tr: &Cluster, bl: &Cluster, br: &Cluster,
    buckets: &[Vec<Vec<EdgeOption>>; 4],
    initial_used: PieceSet,
) -> Option<([Vec<u16>; 4], [Vec<u8>; 4])> {
    let mut used = initial_used;
    let mut budget: u64 = 1_000_000;  // generous per-tuple budget

    // Chain order: top → bottom → left → right
    let mut top_pids = Vec::with_capacity(10);
    let mut top_rots = Vec::with_capacity(10);
    if !try_solve_chain(10, tl.row_color, tr.row_color, &buckets[0], &mut used, &mut budget,
        &mut top_pids, &mut top_rots) { return None; }

    let mut bot_pids = Vec::with_capacity(10);
    let mut bot_rots = Vec::with_capacity(10);
    if !try_solve_chain(10, bl.row_color, br.row_color, &buckets[2], &mut used, &mut budget,
        &mut bot_pids, &mut bot_rots) { return None; }

    let mut left_pids = Vec::with_capacity(10);
    let mut left_rots = Vec::with_capacity(10);
    if !try_solve_chain(10, tl.col_color, bl.col_color, &buckets[3], &mut used, &mut budget,
        &mut left_pids, &mut left_rots) { return None; }

    let mut right_pids = Vec::with_capacity(10);
    let mut right_rots = Vec::with_capacity(10);
    if !try_solve_chain(10, tr.col_color, br.col_color, &buckets[1], &mut used, &mut budget,
        &mut right_pids, &mut right_rots) { return None; }

    Some(([top_pids, bot_pids, left_pids, right_pids],
          [top_rots, bot_rots, left_rots, right_rots]))
}

fn build_partial_json(
    tl: &Cluster, tr: &Cluster, bl: &Cluster, br: &Cluster,
    seg_pids: &[Vec<u16>; 4], seg_rots: &[Vec<u8>; 4],
) -> serde_json::Value {
    let mut placement = Vec::new();
    // Cluster placements (9 cells each, local idx → board position)
    let cluster_data: [(&Cluster, [(usize, usize); 9]); 4] = [
        (tl, [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2),(2,0),(2,1),(2,2)]),
        (tr, [(0,13),(0,14),(0,15),(1,13),(1,14),(1,15),(2,13),(2,14),(2,15)]),
        (bl, [(13,0),(13,1),(13,2),(14,0),(14,1),(14,2),(15,0),(15,1),(15,2)]),
        (br, [(13,13),(13,14),(13,15),(14,13),(14,14),(14,15),(15,13),(15,14),(15,15)]),
    ];
    for (cl, cells) in &cluster_data {
        for (i, (r, c)) in cells.iter().enumerate() {
            placement.push(json!({
                "pos": r * SIDE + c,
                "piece_id": cl.pids[i] as u32,
                "rotation": cl.rots[i] as u32,
            }));
        }
    }
    // Border-strip placements
    // Top: cells (0,3)..(0,12)
    for (i, c) in (3..13).enumerate() {
        placement.push(json!({
            "pos": 0 * SIDE + c,
            "piece_id": seg_pids[0][i] as u32,
            "rotation": seg_rots[0][i] as u32,
        }));
    }
    // Bot: cells (15,3)..(15,12)
    for (i, c) in (3..13).enumerate() {
        placement.push(json!({
            "pos": 15 * SIDE + c,
            "piece_id": seg_pids[1][i] as u32,
            "rotation": seg_rots[1][i] as u32,
        }));
    }
    // Left: cells (3,0)..(12,0)
    for (i, r) in (3..13).enumerate() {
        placement.push(json!({
            "pos": r * SIDE,
            "piece_id": seg_pids[2][i] as u32,
            "rotation": seg_rots[2][i] as u32,
        }));
    }
    // Right: cells (3,15)..(12,15)
    for (i, r) in (3..13).enumerate() {
        placement.push(json!({
            "pos": r * SIDE + 15,
            "piece_id": seg_pids[3][i] as u32,
            "rotation": seg_rots[3][i] as u32,
        }));
    }
    json!({
        "source": "vol122_n8_cluster_sampler",
        "tl_id": tl.id, "tr_id": tr.id, "bl_id": bl.id, "br_id": br.id,
        "n_placed": placement.len(),
        "placement": placement,
    })
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut in_db = PathBuf::from("output/vol-122/n1_corner_3x3_clusters.sqlite");
    let mut out_dir = PathBuf::from("output/vol-122/n8_samples");
    let mut budget_secs: u64 = 60;
    let mut seed: u64 = 0xC0FFEE;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--in" => in_db = PathBuf::from(args.next().unwrap()),
            "--out-dir" => out_dir = PathBuf::from(args.next().unwrap()),
            "--budget-secs" => budget_secs = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    let conn = Connection::open(&in_db).expect("open in");
    let tl = load_clusters(&conn, "TL", &pieces);
    let tr = load_clusters(&conn, "TR", &pieces);
    let bl = load_clusters(&conn, "BL", &pieces);
    let br = load_clusters(&conn, "BR", &pieces);
    eprintln!("loaded clusters: TL={} TR={} BL={} BR={}", tl.len(), tr.len(), bl.len(), br.len());

    let edge_opts = precompute_edge_options(&pieces);
    let buckets = bucket_options_by_left(&edge_opts);

    std::fs::create_dir_all(&out_dir).expect("create out dir");

    let total_attempts = std::sync::Arc::new(AtomicU64::new(0));
    let total_disjoint = std::sync::Arc::new(AtomicU64::new(0));
    let total_success = std::sync::Arc::new(AtomicU64::new(0));
    let t0 = Instant::now();
    let stop = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));

    // Heartbeat thread
    {
        let ta = total_attempts.clone();
        let td = total_disjoint.clone();
        let ts = total_success.clone();
        let stop_c = stop.clone();
        std::thread::spawn(move || {
            while !stop_c.load(Ordering::Relaxed) {
                std::thread::sleep(Duration::from_secs(2));
                let a = ta.load(Ordering::Relaxed);
                let d = td.load(Ordering::Relaxed);
                let s = ts.load(Ordering::Relaxed);
                let elapsed = t0.elapsed().as_secs_f64();
                eprintln!("  attempts={} disjoint={} success={} rate={:.0}/s elapsed={:.1}s",
                    a, d, s, a as f64 / elapsed.max(1e-6), elapsed);
                std::io::stderr().flush().ok();
            }
        });
    }

    let _out_mutex = Mutex::new(0u64);  // file naming counter (unused, kept for future)

    // Stop after budget_secs via a watchdog thread.
    {
        let stop_c = stop.clone();
        std::thread::spawn(move || {
            std::thread::sleep(Duration::from_secs(budget_secs));
            stop_c.store(true, Ordering::Relaxed);
        });
    }

    // Per-thread random state
    (0..rayon::current_num_threads()).into_par_iter().for_each(|thread_id| {
        let mut rng_state = seed.wrapping_add(thread_id as u64 * 2654435761);
        let mut rand = || {
            rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            rng_state
        };
        while !stop.load(Ordering::Relaxed) {
            total_attempts.fetch_add(1, Ordering::Relaxed);
            let i_tl = (rand() as usize) % tl.len();
            let i_tr = (rand() as usize) % tr.len();
            let i_bl = (rand() as usize) % bl.len();
            let i_br = (rand() as usize) % br.len();
            let tlc = &tl[i_tl];
            let trc = &tr[i_tr];
            let blc = &bl[i_bl];
            let brc = &br[i_br];

            let combined = tlc.pieces.or(&trc.pieces).or(&blc.pieces).or(&brc.pieces);
            let total_bits = combined.low.count_ones() + combined.high.count_ones();
            if total_bits != 36 { continue; }
            total_disjoint.fetch_add(1, Ordering::Relaxed);

            if let Some((seg_pids, seg_rots)) = complete_border_ring(tlc, trc, blc, brc, &buckets, combined) {
                let n = total_success.fetch_add(1, Ordering::Relaxed);
                let board = build_partial_json(tlc, trc, blc, brc, &seg_pids, &seg_rots);
                let file = out_dir.join(format!("n8_sample_{:06}_t{}.json", n, thread_id));
                let s = serde_json::to_string_pretty(&board).expect("ser");
                std::fs::write(&file, s).expect("write");
            }
        }
    });

    stop.store(true, Ordering::Relaxed);
    // Race: stop the time-limit polling via a simple sleep
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_secs(budget_secs));
        stop.store(true, Ordering::Relaxed);
    });

    let elapsed = t0.elapsed().as_secs_f64();
    eprintln!("\n=== TOTAL ===");
    eprintln!("attempts: {}", total_attempts.load(Ordering::Relaxed));
    eprintln!("piece-disjoint: {}", total_disjoint.load(Ordering::Relaxed));
    eprintln!("ring-complete successes: {}", total_success.load(Ordering::Relaxed));
    eprintln!("elapsed: {:.2}s", elapsed);
    eprintln!("wrote to: {}", out_dir.display());
}
