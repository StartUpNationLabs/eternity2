// Vol-122 N11 — Joint anchor sampler.
//
// Inputs:
//   --corner-db = n1_corner_3x3_clusters.sqlite (12,958 corner clusters)
//   --center-db = n10b_indexed.sqlite (millions of center-hint 3×3 blocks)
//
// Strategy:
//   Random sample 5-tuples (TL, TR, BL, BR, CENTER) such that:
//     - All 5 are piece-disjoint (44 unique pieces).
//   For each valid sample, build a 44-cell partial board JSON and save.
//   Stops after --budget-secs or --max-samples successful saves.
//
// The 44-cell partial has all 5 canonical hints + matched-edge anchors at
// corners and center. CSP-fill + ALNS can then attempt to complete to a
// full board.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::{Instant, Duration};
use std::sync::atomic::{AtomicU64, Ordering};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use rusqlite::Connection;
use serde_json::json;

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
}

#[derive(Clone, Debug)]
struct Cluster3x3 {
    label: String,
    pids: [u16; 9],
    rots: [u8; 9],
    pieces: PieceSet,
}

fn load_corner_clusters(conn: &Connection, corner_label: &str) -> Vec<Cluster3x3> {
    let q = format!("SELECT
        p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot,
        p3_pid, p3_rot, p4_pid, p4_rot, p5_pid, p5_rot,
        p6_pid, p6_rot, p7_pid, p7_rot, p8_pid, p8_rot
        FROM clusters WHERE corner = '{}' ORDER BY id", corner_label);
    let mut stmt = conn.prepare(&q).expect("prepare");
    stmt.query_map([], |r| {
        let mut pids = [0u16; 9];
        let mut rots = [0u8; 9];
        let mut pieces = PieceSet::new();
        for i in 0..9 {
            let pid: i64 = r.get(i * 2)?;
            let rot: i64 = r.get(i * 2 + 1)?;
            pids[i] = pid as u16;
            rots[i] = rot as u8;
            pieces.set(pid as u16);
        }
        Ok(Cluster3x3 { label: corner_label.to_string(), pids, rots, pieces })
    }).expect("query").filter_map(Result::ok).collect()
}

fn load_center_clusters(conn: &Connection, limit: u64) -> Vec<(u8, Cluster3x3)> {
    let q = format!("SELECT position,
        p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot,
        p3_pid, p3_rot, p4_pid, p4_rot, p5_pid, p5_rot,
        p6_pid, p6_rot, p7_pid, p7_rot, p8_pid, p8_rot
        FROM blocks_3x3 LIMIT {}", limit);
    let mut stmt = conn.prepare(&q).expect("prepare");
    stmt.query_map([], |r| {
        let position: i64 = r.get(0)?;
        let mut pids = [0u16; 9];
        let mut rots = [0u8; 9];
        let mut pieces = PieceSet::new();
        for i in 0..9 {
            let pid: i64 = r.get(1 + i * 2)?;
            let rot: i64 = r.get(1 + i * 2 + 1)?;
            pids[i] = pid as u16;
            rots[i] = rot as u8;
            pieces.set(pid as u16);
        }
        Ok((position as u8, Cluster3x3 {
            label: format!("CENTER_p{}", position),
            pids, rots, pieces
        }))
    }).expect("query").filter_map(Result::ok).collect()
}

fn build_partial_json(
    tl: &Cluster3x3, tr: &Cluster3x3, bl: &Cluster3x3, br: &Cluster3x3,
    center_pos: u8, center: &Cluster3x3,
) -> serde_json::Value {
    let mut placement = Vec::new();
    // Cluster cell layouts in board coords
    // TL covers (0..2, 0..2). Local idx 3r + c → board (r, c).
    for i in 0..9 {
        let r = i / 3;
        let c = i % 3;
        placement.push(json!({"pos": r * SIDE + c, "piece_id": tl.pids[i] as u32, "rotation": tl.rots[i] as u32}));
    }
    // TR covers (0..2, 13..15)
    for i in 0..9 {
        let r = i / 3;
        let c = (i % 3) + 13;
        placement.push(json!({"pos": r * SIDE + c, "piece_id": tr.pids[i] as u32, "rotation": tr.rots[i] as u32}));
    }
    // BL covers (13..15, 0..2)
    for i in 0..9 {
        let r = (i / 3) + 13;
        let c = i % 3;
        placement.push(json!({"pos": r * SIDE + c, "piece_id": bl.pids[i] as u32, "rotation": bl.rots[i] as u32}));
    }
    // BR covers (13..15, 13..15)
    for i in 0..9 {
        let r = (i / 3) + 13;
        let c = (i % 3) + 13;
        placement.push(json!({"pos": r * SIDE + c, "piece_id": br.pids[i] as u32, "rotation": br.rots[i] as u32}));
    }
    // Center 3×3 covers board rows (8-hr..=8-hr+2) × cols (7-hc..=7-hc+2)
    // where center_pos = 3*hr + hc.
    let hr = (center_pos / 3) as usize;
    let hc = (center_pos % 3) as usize;
    let block_r0 = 8 - hr;
    let block_c0 = 7 - hc;
    for i in 0..9 {
        let r = block_r0 + (i / 3);
        let c = block_c0 + (i % 3);
        placement.push(json!({"pos": r * SIDE + c, "piece_id": center.pids[i] as u32, "rotation": center.rots[i] as u32}));
    }
    json!({
        "source": "vol122_n11_joint_anchor",
        "tl_label": tl.label, "tr_label": tr.label, "bl_label": bl.label, "br_label": br.label,
        "center_position": center_pos,
        "n_placed": placement.len(),
        "placement": placement,
    })
}

fn main() {
    let mut corner_db = PathBuf::from("output/vol-122/n1_corner_3x3_clusters.sqlite");
    let mut center_db = PathBuf::from("output/vol-122/n10b_indexed.sqlite");
    let mut out_dir = PathBuf::from("output/vol-122/n11_samples");
    let mut max_samples: u64 = 100;
    let mut budget_secs: u64 = 120;
    let mut center_limit: u64 = 100_000;  // load this many center 3×3s for sampling
    let mut seed: u64 = 0xC0FFEE;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--corner-db" => corner_db = PathBuf::from(args.next().unwrap()),
            "--center-db" => center_db = PathBuf::from(args.next().unwrap()),
            "--out-dir" => out_dir = PathBuf::from(args.next().unwrap()),
            "--max-samples" => max_samples = args.next().unwrap().parse().unwrap(),
            "--budget-secs" => budget_secs = args.next().unwrap().parse().unwrap(),
            "--center-limit" => center_limit = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let _puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let conn_corner = Connection::open(&corner_db).expect("open corner db");
    let tl = load_corner_clusters(&conn_corner, "TL");
    let tr = load_corner_clusters(&conn_corner, "TR");
    let bl = load_corner_clusters(&conn_corner, "BL");
    let br = load_corner_clusters(&conn_corner, "BR");
    eprintln!("corner clusters: TL={} TR={} BL={} BR={}", tl.len(), tr.len(), bl.len(), br.len());

    let conn_center = Connection::open(&center_db).expect("open center db");
    let centers = load_center_clusters(&conn_center, center_limit);
    eprintln!("center clusters loaded: {}", centers.len());

    if centers.is_empty() {
        eprintln!("no center clusters yet; exit");
        return;
    }

    std::fs::create_dir_all(&out_dir).expect("create out dir");

    let t0 = Instant::now();
    let attempts = AtomicU64::new(0);
    let disjoint = AtomicU64::new(0);
    let saved = AtomicU64::new(0);

    // Simple LCG random
    let mut rng_state = seed;
    let mut rand = || {
        rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        rng_state
    };

    while saved.load(Ordering::Relaxed) < max_samples
        && t0.elapsed() < Duration::from_secs(budget_secs)
    {
        attempts.fetch_add(1, Ordering::Relaxed);
        let i_tl = (rand() as usize) % tl.len();
        let i_tr = (rand() as usize) % tr.len();
        let i_bl = (rand() as usize) % bl.len();
        let i_br = (rand() as usize) % br.len();
        let i_c = (rand() as usize) % centers.len();
        let tlc = &tl[i_tl];
        let trc = &tr[i_tr];
        let blc = &bl[i_bl];
        let brc = &br[i_br];
        let (center_pos, cc) = &centers[i_c];

        let combined = tlc.pieces.or(&trc.pieces).or(&blc.pieces).or(&brc.pieces).or(&cc.pieces);
        let bits = combined.low.count_ones() + combined.high.count_ones();
        // Expected: 9*5 = 45 bits if all disjoint, but center hint (piece 138)
        // is reserved at (8,7) and may overlap if any corner cluster contains
        // it. Hint pieces are reserved → corners shouldn't contain piece 138.
        // So we expect exactly 45 unique pieces.
        if bits != 45 { continue; }
        disjoint.fetch_add(1, Ordering::Relaxed);

        let n = saved.fetch_add(1, Ordering::Relaxed);
        let board = build_partial_json(tlc, trc, blc, brc, *center_pos, cc);
        let file = out_dir.join(format!("n11_sample_{:04}.json", n));
        std::fs::write(&file, serde_json::to_string_pretty(&board).expect("ser")).expect("write");

        if (n + 1) % 10 == 0 {
            eprintln!("[{:.1}s] attempts={} disjoint={} saved={}",
                t0.elapsed().as_secs_f64(),
                attempts.load(Ordering::Relaxed),
                disjoint.load(Ordering::Relaxed),
                n + 1);
        }
    }

    eprintln!("\n=== TOTAL ===");
    eprintln!("attempts: {}", attempts.load(Ordering::Relaxed));
    eprintln!("piece-disjoint (45 unique): {}", disjoint.load(Ordering::Relaxed));
    eprintln!("saved partial boards: {}", saved.load(Ordering::Relaxed));
    eprintln!("elapsed: {:.2}s", t0.elapsed().as_secs_f64());
    eprintln!("wrote to: {}", out_dir.display());
}
