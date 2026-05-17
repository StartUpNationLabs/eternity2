// Vol-122 N2 — Enumerate piece-disjoint 4-corner cluster combinations.
//
// Input: SQLite DB from n1_corner_3x3_enum (12,958 valid 3×3 clusters).
// Output: SQLite DB with each row a 4-tuple (tl_id, tr_id, bl_id, br_id)
// where the 36 pieces used across the 4 clusters are all distinct.
//
// Strategy:
// 1. Load all clusters, group by corner, extract piece bitset for each.
// 2. For each TL × TR pair, check piece-disjoint (256-bit bitset AND = 0).
// 3. For each surviving (TL, TR), iterate BL → check disjoint from TL∪TR.
// 4. Same for BR.
//
// Use 256-bit bitset via (u128, u128) pair (matches PieceSet pattern).

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;
use std::sync::atomic::{AtomicU64, Ordering};

use rusqlite::{params, Connection};

#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
struct PieceSet {
    low: u128,
    high: u128,
}

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
struct ClusterRow {
    id: i64,
    pieces: PieceSet,
    pids: [u16; 9],  // piece IDs in local cell order
    rots: [u8; 9],
}

fn load_clusters(conn: &Connection, corner: &str) -> Vec<ClusterRow> {
    let q = format!("SELECT id,
        p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot,
        p3_pid, p3_rot, p4_pid, p4_rot, p5_pid, p5_rot,
        p6_pid, p6_rot, p7_pid, p7_rot, p8_pid, p8_rot
        FROM clusters WHERE corner = '{}' ORDER BY id", corner);
    let mut stmt = conn.prepare(&q).expect("prepare");
    let rows: Vec<ClusterRow> = stmt.query_map([], |r| {
        let id: i64 = r.get(0)?;
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
        Ok(ClusterRow { id, pieces, pids, rots })
    }).expect("query").filter_map(Result::ok).collect();
    rows
}

fn main() {
    let mut in_db = PathBuf::from("output/vol-122/n1_corner_3x3_clusters.sqlite");
    let mut out_db = PathBuf::from("output/vol-122/n2_four_corner_combinations.sqlite");
    let mut limit: u64 = 1_000_000;  // default: cap at 1M to avoid disk blowup
    let mut count_only: bool = false;
    let mut progress_every: u64 = 1_000_000;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--in" => in_db = PathBuf::from(args.next().unwrap()),
            "--out" => out_db = PathBuf::from(args.next().unwrap()),
            "--limit" => limit = args.next().unwrap().parse().unwrap(),
            "--count-only" => count_only = true,
            "--progress-every" => progress_every = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if count_only { limit = 0; }

    let conn_in = Connection::open(&in_db).expect("open input");
    println!("loading clusters from {}...", in_db.display());
    let tl = load_clusters(&conn_in, "TL");
    let tr = load_clusters(&conn_in, "TR");
    let bl = load_clusters(&conn_in, "BL");
    let br = load_clusters(&conn_in, "BR");
    println!("TL={} TR={} BL={} BR={}", tl.len(), tr.len(), bl.len(), br.len());

    let raw_product = (tl.len() as u128) * (tr.len() as u128)
                    * (bl.len() as u128) * (br.len() as u128);
    println!("raw 4-tuple space: {}", raw_product);

    // Open output DB
    std::fs::create_dir_all(out_db.parent().unwrap()).ok();
    let _ = std::fs::remove_file(&out_db);
    let conn_out = Connection::open(&out_db).expect("open output");
    conn_out.execute_batch("
        CREATE TABLE four_corner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tl_id INTEGER NOT NULL,
            tr_id INTEGER NOT NULL,
            bl_id INTEGER NOT NULL,
            br_id INTEGER NOT NULL,
            UNIQUE(tl_id, tr_id, bl_id, br_id)
        );
        CREATE INDEX idx_tl ON four_corner(tl_id);
    ").expect("create");

    let t0 = Instant::now();
    let found = AtomicU64::new(0);
    let explored = AtomicU64::new(0);
    let pruned_tltr = AtomicU64::new(0);
    let pruned_bl = AtomicU64::new(0);

    let mut tx = conn_out.unchecked_transaction().expect("tx");
    {
        let mut stmt = tx.prepare(
            "INSERT OR IGNORE INTO four_corner (tl_id, tr_id, bl_id, br_id) VALUES (?, ?, ?, ?)"
        ).expect("prepare insert");

        // Iterate TL × TR (must be piece-disjoint)
        for tl_row in &tl {
            for tr_row in &tr {
                if tl_row.pieces.intersects(&tr_row.pieces) {
                    pruned_tltr.fetch_add(1, Ordering::Relaxed);
                    continue;
                }
                let tl_tr_pieces = tl_row.pieces.or(&tr_row.pieces);

                // Iterate BL
                for bl_row in &bl {
                    if tl_tr_pieces.intersects(&bl_row.pieces) {
                        pruned_bl.fetch_add(1, Ordering::Relaxed);
                        continue;
                    }
                    let tl_tr_bl = tl_tr_pieces.or(&bl_row.pieces);

                    // Iterate BR
                    for br_row in &br {
                        explored.fetch_add(1, Ordering::Relaxed);
                        if tl_tr_bl.intersects(&br_row.pieces) {
                            continue;
                        }
                        // FOUND: piece-disjoint 4-tuple
                        let f = found.fetch_add(1, Ordering::Relaxed);
                        if f < limit {
                            stmt.execute(params![tl_row.id, tr_row.id, bl_row.id, br_row.id])
                                .expect("insert");
                        }
                        if (f + 1) % progress_every == 0 {
                            println!("  progress: explored={} found={} pruned_tltr={} pruned_bl={} elapsed={:.1}s",
                                explored.load(Ordering::Relaxed),
                                f + 1,
                                pruned_tltr.load(Ordering::Relaxed),
                                pruned_bl.load(Ordering::Relaxed),
                                t0.elapsed().as_secs_f64());
                        }
                    }
                }
            }
            // Per-TL progress
            let cur_found = found.load(Ordering::Relaxed);
            let cur_explored = explored.load(Ordering::Relaxed);
            if cur_explored > 0 && tl_row.id % 100 == 0 {
                println!("  TL id={}/{}, found so far={}, elapsed={:.1}s",
                    tl_row.id, tl.len(), cur_found, t0.elapsed().as_secs_f64());
            }
        }
    }
    tx.commit().expect("commit");

    let n_rows: i64 = conn_out.query_row("SELECT COUNT(*) FROM four_corner", [], |r| r.get(0)).unwrap();
    println!("\n=== TOTAL ===");
    println!("inserted: {}", n_rows);
    println!("found: {}", found.load(Ordering::Relaxed));
    println!("explored: {}", explored.load(Ordering::Relaxed));
    println!("pruned at TL+TR: {}", pruned_tltr.load(Ordering::Relaxed));
    println!("pruned at BL: {}", pruned_bl.load(Ordering::Relaxed));
    println!("elapsed: {:.2}s", t0.elapsed().as_secs_f64());
    println!("wrote: {}", out_db.display());
}
