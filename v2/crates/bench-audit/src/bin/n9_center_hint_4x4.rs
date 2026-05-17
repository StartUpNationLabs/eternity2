// Vol-122 N9 — Enumerate all valid 4×4 blocks around the center hint (8,7).
//
// The 4×4 block can be positioned with the hint at any of 16 cells. We
// enumerate ONE positioning at a time (configurable via --position arg).
//
// Default: hint at local (2,1) → 4×4 top-left at board (6,6), hint at board (8,7).
//
// Reserve all 5 hint pieces (only the hint at (8,7) is used; others must NOT
// be used in the 4×4 since they're reserved for other positions).
//
// All 24 internal edges of the 4×4 must match. No border constraints (4×4 is
// in interior). Output to SQLite + per-positioning progress.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;
use std::sync::atomic::{AtomicU64, Ordering};
use std::io::Write;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use rusqlite::{params, Connection};

const BLOCK_N: usize = 4;
const BLOCK_CELLS: usize = BLOCK_N * BLOCK_N;
const SIDE: usize = 16;

#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
struct PieceSet { low: u128, high: u128 }
impl PieceSet {
    fn new() -> Self { Self { low: 0, high: 0 } }
    fn set(&mut self, pid: u16) {
        if pid < 128 { self.low |= 1u128 << pid; }
        else { self.high |= 1u128 << (pid - 128); }
    }
    fn unset(&mut self, pid: u16) {
        if pid < 128 { self.low &= !(1u128 << pid); }
        else { self.high &= !(1u128 << (pid - 128)); }
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

#[derive(Clone, Copy, Debug)]
struct PieceRot { pid: u16, rot: u8, edges: [u8; 4] }

#[derive(Clone, Copy, Debug)]
struct Cell { pid: u16, rot: u8, edges: [u8; 4] }

/// Cell layout in local 4×4: idx = r * 4 + c, r in 0..4, c in 0..4.
fn local_neighbors(idx: usize) -> Vec<(usize, u8, u8)> {
    // Returns (neighbor_idx, this_side, neighbor_side) for placed neighbors only.
    let r = idx / BLOCK_N;
    let c = idx % BLOCK_N;
    let mut out = Vec::new();
    if r > 0 { out.push(((r - 1) * BLOCK_N + c, 0, 2)); }
    if c + 1 < BLOCK_N { out.push((r * BLOCK_N + (c + 1), 1, 3)); }
    if r + 1 < BLOCK_N { out.push(((r + 1) * BLOCK_N + c, 2, 0)); }
    if c > 0 { out.push((r * BLOCK_N + (c - 1), 3, 1)); }
    out
}

#[allow(clippy::too_many_arguments)]
fn recurse(
    order: &[usize],
    step: usize,
    block: &mut [Option<Cell>; BLOCK_CELLS],
    used: &mut PieceSet,
    interior_pieces: &Vec<u16>,
    pieces: &Vec<[u8; 4]>,
    hint_pids_reserved: &[u16],
    count: &AtomicU64,
    insertions: &AtomicU64,
    stmt: &mut rusqlite::Statement,
    position_label: &str,
    store_limit: u64,
) {
    if step == order.len() {
        let c = count.fetch_add(1, Ordering::Relaxed) + 1;
        if insertions.load(Ordering::Relaxed) < store_limit {
            let pids: Vec<i64> = (0..BLOCK_CELLS).map(|i| block[i].unwrap().pid as i64).collect();
            let rots: Vec<i64> = (0..BLOCK_CELLS).map(|i| block[i].unwrap().rot as i64).collect();
            stmt.execute(params![
                position_label,
                pids[0], rots[0], pids[1], rots[1], pids[2], rots[2], pids[3], rots[3],
                pids[4], rots[4], pids[5], rots[5], pids[6], rots[6], pids[7], rots[7],
                pids[8], rots[8], pids[9], rots[9], pids[10], rots[10], pids[11], rots[11],
                pids[12], rots[12], pids[13], rots[13], pids[14], rots[14], pids[15], rots[15],
            ]).expect("insert");
            insertions.fetch_add(1, Ordering::Relaxed);
        }
        if c % 100_000 == 0 {
            eprintln!("  {} found so far at step {} (stored: {})", c, step, insertions.load(Ordering::Relaxed));
            std::io::stderr().flush().ok();
        }
        return;
    }
    let cell = order[step];
    for &pid in interior_pieces {
        if used.contains(pid) { continue; }
        if hint_pids_reserved.contains(&pid) { continue; }
        for rot in 0..4u8 {
            let edges = rot_edges(pieces[pid as usize], rot);
            // Check against placed neighbors
            let mut ok = true;
            for (nb_idx, this_side, nb_side) in local_neighbors(cell) {
                if let Some(nb) = block[nb_idx] {
                    if edges[this_side as usize] != nb.edges[nb_side as usize] || edges[this_side as usize] == 0 {
                        ok = false;
                        break;
                    }
                }
            }
            if !ok { continue; }
            block[cell] = Some(Cell { pid, rot, edges });
            used.set(pid);
            recurse(order, step + 1, block, used, interior_pieces, pieces, hint_pids_reserved, count, insertions, stmt, position_label, store_limit);
            used.unset(pid);
            block[cell] = None;
        }
    }
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut out_db = PathBuf::from("output/vol-122/n9_center_hint_4x4.sqlite");
    let mut hint_local_r: usize = 2;  // hint at local row 2
    let mut hint_local_c: usize = 1;  // hint at local col 1
    let mut store_limit: u64 = u64::MAX;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--out" => out_db = PathBuf::from(args.next().unwrap()),
            "--hint-local-r" => hint_local_r = args.next().unwrap().parse().unwrap(),
            "--hint-local-c" => hint_local_c = args.next().unwrap().parse().unwrap(),
            "--store-limit" => store_limit = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    // Interior pieces only (4×4 is entirely interior on canonical 16×16).
    let interior_pieces: Vec<u16> = (0..256u16).filter(|&pid| {
        let e = pieces[pid as usize];
        e.iter().filter(|&&x| x == 0).count() == 0
    }).collect();
    eprintln!("interior pieces: {}", interior_pieces.len());

    // 4×4 board-position: hint at (8,7) means block top-left is at:
    // (8 - hint_local_r, 7 - hint_local_c)
    let block_r0 = 8 - hint_local_r;
    let block_c0 = 7 - hint_local_c;
    eprintln!("4×4 block at board (r={}..={}, c={}..={}), hint at local ({},{}) = board (8,7)",
        block_r0, block_r0 + 3, block_c0, block_c0 + 3, hint_local_r, hint_local_c);

    // Place hint piece (piece 138 rot 0)
    let hint_idx = hint_local_r * BLOCK_N + hint_local_c;
    let hint_pid: u16 = 138;
    let hint_rot: u8 = 0;
    let hint_edges = rot_edges(pieces[hint_pid as usize], hint_rot);

    let mut block: [Option<Cell>; BLOCK_CELLS] = [None; BLOCK_CELLS];
    block[hint_idx] = Some(Cell { pid: hint_pid, rot: hint_rot, edges: hint_edges });
    let mut used = PieceSet::new();
    used.set(hint_pid);

    // Reserve the other 4 hint pieces from being used in the 4×4.
    let hint_pids_reserved: Vec<u16> = vec![207, 254, 180, 248];

    // Fill order: start from cells adjacent to the hint, then expand outward (MRV-like).
    let mut order: Vec<usize> = Vec::new();
    let mut visited = vec![false; BLOCK_CELLS];
    visited[hint_idx] = true;
    let mut frontier: Vec<usize> = Vec::new();
    for (nb, _, _) in local_neighbors(hint_idx) { frontier.push(nb); }
    while !frontier.is_empty() {
        let mut next_frontier: Vec<usize> = Vec::new();
        for &cell in &frontier {
            if visited[cell] { continue; }
            visited[cell] = true;
            order.push(cell);
            for (nb, _, _) in local_neighbors(cell) {
                if !visited[nb] { next_frontier.push(nb); }
            }
        }
        frontier = next_frontier;
    }
    // Add any remaining cells (corners of 4×4 might not be reached from one neighbor of hint)
    for i in 0..BLOCK_CELLS { if !visited[i] { order.push(i); visited[i] = true; } }
    eprintln!("fill order ({}): {:?}", order.len(), order);

    // Setup SQLite output
    std::fs::create_dir_all(out_db.parent().unwrap()).ok();
    let _ = std::fs::remove_file(&out_db);
    let conn = Connection::open(&out_db).expect("open out");
    conn.execute_batch("
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = OFF;
        CREATE TABLE blocks_4x4 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position TEXT NOT NULL,
            p0_pid INTEGER, p0_rot INTEGER, p1_pid INTEGER, p1_rot INTEGER,
            p2_pid INTEGER, p2_rot INTEGER, p3_pid INTEGER, p3_rot INTEGER,
            p4_pid INTEGER, p4_rot INTEGER, p5_pid INTEGER, p5_rot INTEGER,
            p6_pid INTEGER, p6_rot INTEGER, p7_pid INTEGER, p7_rot INTEGER,
            p8_pid INTEGER, p8_rot INTEGER, p9_pid INTEGER, p9_rot INTEGER,
            p10_pid INTEGER, p10_rot INTEGER, p11_pid INTEGER, p11_rot INTEGER,
            p12_pid INTEGER, p12_rot INTEGER, p13_pid INTEGER, p13_rot INTEGER,
            p14_pid INTEGER, p14_rot INTEGER, p15_pid INTEGER, p15_rot INTEGER
        );
    ").expect("create");

    let count = AtomicU64::new(0);
    let insertions = AtomicU64::new(0);
    let position_label = format!("hint_{},{}", hint_local_r, hint_local_c);
    let t0 = Instant::now();

    let mut tx = conn.unchecked_transaction().expect("tx");
    {
        let mut stmt = tx.prepare(
            "INSERT INTO blocks_4x4 (position,
                p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot, p3_pid, p3_rot,
                p4_pid, p4_rot, p5_pid, p5_rot, p6_pid, p6_rot, p7_pid, p7_rot,
                p8_pid, p8_rot, p9_pid, p9_rot, p10_pid, p10_rot, p11_pid, p11_rot,
                p12_pid, p12_rot, p13_pid, p13_rot, p14_pid, p14_rot, p15_pid, p15_rot)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)").expect("prepare");
        recurse(&order, 0, &mut block, &mut used, &interior_pieces, &pieces, &hint_pids_reserved, &count, &insertions, &mut stmt, &position_label, store_limit);
    }
    tx.commit().expect("commit");

    let n_rows: i64 = conn.query_row("SELECT COUNT(*) FROM blocks_4x4", [], |r| r.get(0)).unwrap();
    eprintln!("\n=== TOTAL ===");
    eprintln!("position: {}", position_label);
    eprintln!("valid 4x4 found: {}", count.load(Ordering::Relaxed));
    eprintln!("stored: {}", n_rows);
    eprintln!("elapsed: {:.2}s", t0.elapsed().as_secs_f64());
    eprintln!("wrote: {}", out_db.display());
}
