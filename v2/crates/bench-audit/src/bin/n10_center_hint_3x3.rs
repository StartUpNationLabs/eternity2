// Vol-122 N10 — Enumerate all valid 3×3 blocks around the center hint (8,7).
//
// For each positioning (hint at local (hr, hc) where hr ∈ 0..3, hc ∈ 0..3),
// the 3×3 covers board rows (8-hr..8-hr+2) × cols (7-hc..7-hc+2).
//
// All 12 internal edges must match. Hint piece pinned. Other 4 hint pieces reserved.
//
// Storage: SQLite with WAL + sync=OFF, COMMIT EVERY 1M ROWS so we don't blow
// out memory with a giant transaction.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;
use std::sync::atomic::{AtomicU64, Ordering};
use std::io::Write;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use rusqlite::{params, Connection};

const BLOCK_N: usize = 3;
const BLOCK_CELLS: usize = BLOCK_N * BLOCK_N;

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
struct Cell { pid: u16, rot: u8, edges: [u8; 4] }

fn local_neighbors(idx: usize) -> Vec<(usize, u8, u8)> {
    let r = idx / BLOCK_N;
    let c = idx % BLOCK_N;
    let mut out = Vec::new();
    if r > 0 { out.push(((r - 1) * BLOCK_N + c, 0, 2)); }
    if c + 1 < BLOCK_N { out.push((r * BLOCK_N + (c + 1), 1, 3)); }
    if r + 1 < BLOCK_N { out.push(((r + 1) * BLOCK_N + c, 2, 0)); }
    if c > 0 { out.push((r * BLOCK_N + (c - 1), 3, 1)); }
    out
}

const COMMIT_EVERY: u64 = 1_000_000;

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
    pending: &mut Vec<[i64; 18]>,  // (pid, rot) × 9 = 18 fields per row
    conn: &Connection,
    position_label: &str,
) {
    if step == order.len() {
        count.fetch_add(1, Ordering::Relaxed);
        let mut row: [i64; 18] = [0; 18];
        for i in 0..BLOCK_CELLS {
            let c = block[i].expect("cell filled");
            row[i * 2] = c.pid as i64;
            row[i * 2 + 1] = c.rot as i64;
        }
        pending.push(row);
        if pending.len() as u64 >= COMMIT_EVERY {
            commit_pending(pending, conn, position_label, insertions);
        }
        return;
    }
    let cell = order[step];
    for &pid in interior_pieces {
        if used.contains(pid) { continue; }
        if hint_pids_reserved.contains(&pid) { continue; }
        for rot in 0..4u8 {
            let edges = rot_edges(pieces[pid as usize], rot);
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
            recurse(order, step + 1, block, used, interior_pieces, pieces, hint_pids_reserved,
                count, insertions, pending, conn, position_label);
            used.unset(pid);
            block[cell] = None;
        }
    }
}

fn commit_pending(pending: &mut Vec<[i64; 18]>, conn: &Connection, position_label: &str, insertions: &AtomicU64) {
    if pending.is_empty() { return; }
    let n = pending.len();
    let tx = conn.unchecked_transaction().expect("tx");
    {
        let mut stmt = tx.prepare(
            "INSERT INTO blocks_3x3 (position,
                p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot,
                p3_pid, p3_rot, p4_pid, p4_rot, p5_pid, p5_rot,
                p6_pid, p6_rot, p7_pid, p7_rot, p8_pid, p8_rot)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)").expect("prepare");
        for row in pending.iter() {
            stmt.execute(params![position_label,
                row[0], row[1], row[2], row[3], row[4], row[5],
                row[6], row[7], row[8], row[9], row[10], row[11],
                row[12], row[13], row[14], row[15], row[16], row[17]
            ]).expect("insert");
        }
    }
    tx.commit().expect("commit");
    pending.clear();
    let total = insertions.fetch_add(n as u64, Ordering::Relaxed) + n as u64;
    eprintln!("  [commit] +{} → total stored = {}", n, total);
    std::io::stderr().flush().ok();
}

fn enumerate_position(
    hint_local_r: usize,
    hint_local_c: usize,
    pieces: &Vec<[u8; 4]>,
    interior_pieces: &Vec<u16>,
    conn: &Connection,
) -> u64 {
    let hint_idx = hint_local_r * BLOCK_N + hint_local_c;
    let hint_pid: u16 = 138;
    let hint_rot: u8 = 0;
    let hint_edges = rot_edges(pieces[hint_pid as usize], hint_rot);

    let mut block: [Option<Cell>; BLOCK_CELLS] = [None; BLOCK_CELLS];
    block[hint_idx] = Some(Cell { pid: hint_pid, rot: hint_rot, edges: hint_edges });
    let mut used = PieceSet::new();
    used.set(hint_pid);
    let hint_pids_reserved: Vec<u16> = vec![207, 254, 180, 248];

    // BFS fill order starting from hint
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
    for i in 0..BLOCK_CELLS { if !visited[i] { order.push(i); } }

    let position_label = format!("hint_{}{}", hint_local_r, hint_local_c);
    eprintln!("\n=== position {}: hint at local ({},{}) ===", position_label, hint_local_r, hint_local_c);
    eprintln!("  3×3 covers board rows {}..={} × cols {}..={}",
        8 - hint_local_r, 8 - hint_local_r + 2,
        7 - hint_local_c, 7 - hint_local_c + 2);
    eprintln!("  fill order: {:?}", order);
    let count = AtomicU64::new(0);
    let insertions = AtomicU64::new(0);
    let mut pending: Vec<[i64; 18]> = Vec::new();
    let t0 = Instant::now();
    recurse(&order, 0, &mut block, &mut used, interior_pieces, pieces, &hint_pids_reserved,
        &count, &insertions, &mut pending, conn, &position_label);
    // Flush any remaining
    commit_pending(&mut pending, conn, &position_label, &insertions);
    let c = count.load(Ordering::Relaxed);
    eprintln!("  position {} complete: {} valid 3×3 in {:.2}s",
        position_label, c, t0.elapsed().as_secs_f64());
    c
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut out_db = PathBuf::from("output/vol-122/n10_center_hint_3x3.sqlite");
    let mut only_position: Option<(usize, usize)> = None;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--out" => out_db = PathBuf::from(args.next().unwrap()),
            "--only-position" => {
                let s = args.next().unwrap();
                let parts: Vec<&str> = s.split(',').collect();
                only_position = Some((parts[0].parse().unwrap(), parts[1].parse().unwrap()));
            }
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();
    let interior_pieces: Vec<u16> = (0..256u16).filter(|&pid| {
        let e = pieces[pid as usize];
        e.iter().filter(|&&x| x == 0).count() == 0
    }).collect();
    eprintln!("interior pieces: {}", interior_pieces.len());

    std::fs::create_dir_all(out_db.parent().unwrap()).ok();
    let _ = std::fs::remove_file(&out_db);
    let conn = Connection::open(&out_db).expect("open out");
    conn.execute_batch("
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = OFF;
        CREATE TABLE blocks_3x3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position TEXT NOT NULL,
            p0_pid INTEGER, p0_rot INTEGER, p1_pid INTEGER, p1_rot INTEGER,
            p2_pid INTEGER, p2_rot INTEGER, p3_pid INTEGER, p3_rot INTEGER,
            p4_pid INTEGER, p4_rot INTEGER, p5_pid INTEGER, p5_rot INTEGER,
            p6_pid INTEGER, p6_rot INTEGER, p7_pid INTEGER, p7_rot INTEGER,
            p8_pid INTEGER, p8_rot INTEGER
        );
        CREATE INDEX idx_position ON blocks_3x3(position);
    ").expect("create");

    let t_all = Instant::now();
    let mut total_count: u64 = 0;

    let positions: Vec<(usize, usize)> = if let Some(p) = only_position {
        vec![p]
    } else {
        // All 9 positions: hint at any of (0..3, 0..3)
        (0..3).flat_map(|r| (0..3).map(move |c| (r, c))).collect()
    };

    for (hr, hc) in positions {
        let c = enumerate_position(hr, hc, &pieces, &interior_pieces, &conn);
        total_count += c;
    }

    let n_rows: i64 = conn.query_row("SELECT COUNT(*) FROM blocks_3x3", [], |r| r.get(0)).unwrap();
    eprintln!("\n=== GRAND TOTAL ===");
    eprintln!("valid 3×3 found across all positions: {}", total_count);
    eprintln!("stored in DB: {}", n_rows);
    eprintln!("elapsed: {:.2}s", t_all.elapsed().as_secs_f64());
    eprintln!("wrote: {}", out_db.display());
}
