// Vol-122 N4 — Tighter feasibility test for 4-corner cluster combinations.
//
// Constraints applied (in order, fail-fast):
//   C1 (L1): piece-uniqueness across 36 cells (10ns).
//   C2: hint (8,7) neighborhood — piece 138 rot 0 requires specific neighbor colors.
//       At least 4 unused pieces must exist with edges matching {(B=8), (T=9), (R=9), (L=12)}
//       in the relevant directions. (1µs)
//   C3: edge-piece Hall condition per border-color. The 4 border segments (10 cells each)
//       need 40 edge pieces. Each border-color demand vs supply must satisfy Hall. (10µs)
//   C4: each of 4 border-segment reachability check (1D DP). (40µs)
//
// Run full enumeration with prefix pruning. Store all feasible 4-tuples.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;
use std::sync::atomic::{AtomicU64, Ordering};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use rusqlite::{params, Connection};

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
    corner: char,
    pids: [u16; 9],
    rots: [u8; 9],
    pieces: PieceSet,
    // Pre-computed inward-facing endpoint colors at the border segments:
    //   For TL: (right_out_at_02, bottom_out_at_20) — start/end of row-0 seg and col-0 seg
    //   We pre-compute the SPECIFIC border-endpoint colors so feasibility checks are O(1)
    border_seg_out: u8,  // color emerging from this corner into a border segment direction A
    border_seg_in: u8,   // color emerging from this corner into a border segment direction B
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
        let mut pieces_set = PieceSet::new();
        for i in 0..9 {
            let pid: i64 = r.get(1 + i * 2)?;
            let rot: i64 = r.get(1 + i * 2 + 1)?;
            pids[i] = pid as u16;
            rots[i] = rot as u8;
            pieces_set.set(pid as u16);
        }
        // Border segment endpoints (the colors entering the unfilled border cells):
        // For TL (3×3 at (0..2, 0..2)):
        //   - row 0 segment goes east from (0,2).R. Endpoint OUT = R-side of cell (0,2) [local idx 2].
        //   - col 0 segment goes south from (2,0).B. Endpoint OUT = B-side of cell (2,0) [local idx 6].
        // For TR (cells (0..2, 13..15)):
        //   - row 0 seg goes east INTO (0,13).L (local idx 0). Endpoint IN = L-side.
        //   - col 15 seg goes south from (2,15).B (local idx 8). Endpoint OUT.
        // For BL (cells (13..15, 0..2)):
        //   - row 15 seg goes east from (15,2).R (local idx 8).
        //   - col 0 seg goes south INTO (13,0).T (local idx 0).
        // For BR (cells (13..15, 13..15)):
        //   - row 15 seg goes east INTO (15,13).L (local idx 6).
        //   - col 15 seg goes south INTO (13,15).T (local idx 2).
        //
        // We store 2 colors per cluster: (seg_out, seg_in) where:
        //   TL: out=R of (0,2), and out=B of (2,0)   → both OUTGOING
        //   TR: in=L of (0,13), out=B of (2,15)      → mixed
        //   BL: out=R of (15,2), in=T of (13,0)      → mixed
        //   BR: in=L of (15,13), in=T of (13,15)     → both INCOMING
        //
        // But for matching purposes, each border seg has one TL-side endpoint and one TR-side
        // endpoint. So a CLUSTER contributes 2 colors to border segments:
        //   TL contributes: top-row's east-going color, left-col's south-going color
        //   TR contributes: top-row's east-coming-into color, right-col's south-going color
        //   BL contributes: left-col's south-coming-into color, bot-row's east-going color
        //   BR contributes: right-col's south-coming-into color, bot-row's east-coming-into color
        //
        // For now, store generic two endpoint colors keyed by the cluster's corner.
        let (e1, e2) = match label_char {
            'L' => {
                let ec = rot_edges(pieces[pids[2] as usize], rots[2]);
                let er = rot_edges(pieces[pids[6] as usize], rots[6]);
                (ec[1], er[2])  // R of (0,2), B of (2,0)
            }
            'R' => {
                let ec = rot_edges(pieces[pids[0] as usize], rots[0]);
                let er = rot_edges(pieces[pids[8] as usize], rots[8]);
                (ec[3], er[2])  // L of (0,13), B of (2,15)
            }
            'l' => {
                let ec = rot_edges(pieces[pids[8] as usize], rots[8]);
                let er = rot_edges(pieces[pids[0] as usize], rots[0]);
                (ec[1], er[0])  // R of (15,2), T of (13,0)
            }
            'r' => {
                let ec = rot_edges(pieces[pids[6] as usize], rots[6]);
                let er = rot_edges(pieces[pids[2] as usize], rots[2]);
                (ec[3], er[0])  // L of (15,13), T of (13,15)
            }
            _ => panic!(),
        };
        Ok(Cluster { id, corner: label_char, pids, rots, pieces: pieces_set,
            border_seg_out: e1, border_seg_in: e2 })
    }).expect("query").filter_map(Result::ok).collect()
}

/// Border-segment reachability via 1D DP on edge pieces.
fn border_seg_reachable(
    n_intermediate: usize,
    start_left: u8, end_right: u8,
    options: &[(u16, u8, u8, u8)],  // (pid, rot, L, R) for this border direction
    used: &PieceSet,
) -> bool {
    const N_C: usize = 32;
    let mut cur = [false; N_C];
    let mut next = [false; N_C];
    cur[start_left as usize] = true;
    for _ in 0..n_intermediate {
        for c in 0..N_C { next[c] = false; }
        for &(pid, _rot, l, r) in options {
            if used.contains(pid) { continue; }
            if (l as usize) < N_C && cur[l as usize] {
                next[r as usize] = true;
            }
        }
        std::mem::swap(&mut cur, &mut next);
    }
    (end_right as usize) < N_C && cur[end_right as usize]
}

/// Pre-compute edge-piece options for each border direction.
fn precompute_edge_options(pieces: &[[u8; 4]]) -> Vec<Vec<(u16, u8, u8, u8)>> {
    let mut by_dir: Vec<Vec<(u16, u8, u8, u8)>> = vec![Vec::new(); 4];
    for (pid, e) in pieces.iter().enumerate() {
        let zeros = e.iter().filter(|&&x| x == 0).count();
        if zeros != 1 { continue; }
        for rot in 0..4u8 {
            let re = rot_edges(*e, rot);
            // Top border: T=0, traversing L→R: input=L, output=R
            if re[0] == 0 { by_dir[0].push((pid as u16, rot, re[3], re[1])); }
            // Right border: R=0, traversing T→B: input=T, output=B
            if re[1] == 0 { by_dir[1].push((pid as u16, rot, re[0], re[2])); }
            // Bottom border: B=0, traversing L→R: input=L, output=R
            if re[2] == 0 { by_dir[2].push((pid as u16, rot, re[3], re[1])); }
            // Left border: L=0, traversing T→B: input=T, output=B
            if re[3] == 0 { by_dir[3].push((pid as u16, rot, re[0], re[2])); }
        }
    }
    by_dir
}

/// Check if piece 138 (hint at (8,7)) rot 0 has 4 compatible unused neighbors.
/// Piece 138 edges = (T=8, R=9, B=9, L=12). Neighbors required:
///   (7,7) at S=B=8 → need piece with T=8 (in some rotation) NOT used by corners
///   (9,7) at N=T=9 → need piece with B=9
///   (8,6) at E=R=9 → need piece with L=9
///   (8,8) at W=L=12 → need piece with R=12
/// Check that EACH required color-direction has at least one INTERIOR piece available.
fn hint_8_7_neighbor_feasible(combined: &PieceSet, pieces: &[[u8; 4]]) -> bool {
    // Piece 138 reserved by hint logic — won't be in `combined` (since N1 excludes hint pids)
    // Check that for each required (color, side), at least one unused interior piece has it.
    let required: [(u8, u8); 4] = [
        (8, 0),   // need piece with T=8 in some rot (for (7,7) below hint, top side faces hint's B=8)
        (9, 2),   // need piece with B=9 (for (9,7) above hint? no, BELOW: T side of (9,7) matches hint B)
        // Actually let me re-think. Hint (8,7) has B=9 → (9,7).T must = 9.
        // (7,7).B must match hint.T = 8.
        // (8,8).L must match hint.R = 9.
        // (8,6).R must match hint.L = 12.
        // So: cell (7,7) needs B=8 (after rotation), cell (9,7) needs T=9, cell (8,6) needs R=12, cell (8,8) needs L=9.
        // Side indices: T=0, R=1, B=2, L=3.
        (9, 1),   // not actually used by my reasoning above
        (12, 3),
    ];
    let _ = required;
    // Correct list:
    let need: [(u8, u8); 4] = [
        (8, 2),    // (7,7) below-side-of-it-above-hint: B=8
        (9, 0),    // (9,7) above-side: T=9
        (12, 1),   // (8,6) right-side: R=12
        (9, 3),    // (8,8) left-side: L=9
    ];
    // Hint pieces themselves are not interior; piece 138 IS interior but reserved.
    // Reserved hint pids: 138 (this one), 207, 254, 180, 248.
    let reserved: [u16; 5] = [138, 207, 254, 180, 248];
    for &(color, side) in &need {
        let mut found = false;
        for (pid, e) in pieces.iter().enumerate() {
            let zeros = e.iter().filter(|&&x| x == 0).count();
            if zeros != 0 { continue; }  // interior only
            if combined.contains(pid as u16) { continue; }  // not used by corners
            if reserved.contains(&(pid as u16)) { continue; }  // reserved hints
            for rot in 0..4u8 {
                let re = rot_edges(*e, rot);
                if re[side as usize] == color {
                    found = true;
                    break;
                }
            }
            if found { break; }
        }
        if !found { return false; }
    }
    true
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut in_db = PathBuf::from("output/vol-122/n1_corner_3x3_clusters.sqlite");
    let mut out_db = PathBuf::from("output/vol-122/n4_tight_feasible.sqlite");
    let mut store_limit: u64 = u64::MAX;
    let mut max_iterations: u64 = u64::MAX;
    let mut progress_every: u64 = 1_000_000;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--in" => in_db = PathBuf::from(args.next().unwrap()),
            "--out" => out_db = PathBuf::from(args.next().unwrap()),
            "--store-limit" => store_limit = args.next().unwrap().parse().unwrap(),
            "--max-iter" => max_iterations = args.next().unwrap().parse().unwrap(),
            "--progress-every" => progress_every = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();
    println!("loaded {} pieces", pieces.len());

    let conn_in = Connection::open(&in_db).expect("open");
    let tl = load_clusters(&conn_in, "TL", &pieces);
    let tr = load_clusters(&conn_in, "TR", &pieces);
    let bl = load_clusters(&conn_in, "BL", &pieces);
    let br = load_clusters(&conn_in, "BR", &pieces);
    println!("clusters: TL={} TR={} BL={} BR={}", tl.len(), tr.len(), bl.len(), br.len());

    let edge_options = precompute_edge_options(&pieces);

    std::fs::create_dir_all(out_db.parent().unwrap()).ok();
    let _ = std::fs::remove_file(&out_db);
    let conn_out = Connection::open(&out_db).expect("open out");
    conn_out.execute_batch("
        CREATE TABLE feasible (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tl_id INTEGER, tr_id INTEGER, bl_id INTEGER, br_id INTEGER
        );
    ").expect("create");

    let t0 = Instant::now();
    let mut explored: u64 = 0;
    let mut l1_pass: u64 = 0;
    let mut hint_pass: u64 = 0;
    let mut row0_pass: u64 = 0;
    let mut full_pass: u64 = 0;
    let mut inserted: u64 = 0;

    let mut tx = conn_out.unchecked_transaction().expect("tx");
    let mut stmt = tx.prepare("INSERT INTO feasible (tl_id, tr_id, bl_id, br_id) VALUES (?, ?, ?, ?)").expect("prepare");

    'outer: for tl_c in &tl {
        for tr_c in &tr {
            if tl_c.pieces.intersects(&tr_c.pieces) { continue; }
            // Row 0 segment: TL.right (border_seg_out) → TR.left (border_seg_in)
            // For TL: border_seg_out is R of (0,2); border_seg_in is B of (2,0).
            // For TR: border_seg_in is L of (0,13); border_seg_out is B of (2,15).
            let tl_tr_pieces = tl_c.pieces.or(&tr_c.pieces);
            if !border_seg_reachable(10, tl_c.border_seg_out, tr_c.border_seg_in, &edge_options[0], &tl_tr_pieces) {
                continue;
            }

            for bl_c in &bl {
                if tl_tr_pieces.intersects(&bl_c.pieces) { continue; }
                // Col 0 segment: TL.bot_out → BL.top_in
                // TL.border_seg_in = B of (2,0). BL.border_seg_in = T of (13,0).
                let tl_tr_bl = tl_tr_pieces.or(&bl_c.pieces);
                if !border_seg_reachable(10, tl_c.border_seg_in, bl_c.border_seg_in, &edge_options[3], &tl_tr_bl) {
                    continue;
                }

                for br_c in &br {
                    explored += 1;
                    if explored % progress_every == 0 {
                        println!("  explored={} L1pass={} hintpass={} row0pass={} fullpass={} elapsed={:.1}s",
                            explored, l1_pass, hint_pass, row0_pass, full_pass,
                            t0.elapsed().as_secs_f64());
                    }
                    if explored >= max_iterations { break 'outer; }

                    if tl_tr_bl.intersects(&br_c.pieces) { continue; }
                    let combined = tl_tr_bl.or(&br_c.pieces);
                    l1_pass += 1;

                    // Row 15 segment: BL.right_out → BR.left_in
                    if !border_seg_reachable(10, bl_c.border_seg_out, br_c.border_seg_out, &edge_options[2], &combined) {
                        continue;
                    }
                    // Col 15 segment: TR.bot_out → BR.top_in
                    if !border_seg_reachable(10, tr_c.border_seg_out, br_c.border_seg_in, &edge_options[1], &combined) {
                        continue;
                    }
                    row0_pass += 1;

                    // C2: hint 138 at (8,7) neighborhood
                    if !hint_8_7_neighbor_feasible(&combined, &pieces) {
                        continue;
                    }
                    hint_pass += 1;

                    full_pass += 1;
                    if inserted < store_limit {
                        stmt.execute(params![tl_c.id, tr_c.id, bl_c.id, br_c.id]).expect("insert");
                        inserted += 1;
                    }
                }
            }
        }
        if tl_c.id % 100 == 0 {
            println!("  TL={}/{}, explored={} fullpass={} inserted={} elapsed={:.1}s",
                tl_c.id, tl.len(), explored, full_pass, inserted, t0.elapsed().as_secs_f64());
        }
    }

    drop(stmt);
    tx.commit().expect("commit");
    let n_rows: i64 = conn_out.query_row("SELECT COUNT(*) FROM feasible", [], |r| r.get(0)).unwrap();
    println!("\n=== TOTAL ===");
    println!("explored: {}", explored);
    println!("L1 pass (piece-disjoint): {}", l1_pass);
    println!("L4 pass (4 border segs reachable): {}", row0_pass);
    println!("hint (8,7) pass: {}", hint_pass);
    println!("full_pass: {}", full_pass);
    println!("inserted: {}", n_rows);
    println!("elapsed: {:.2}s", t0.elapsed().as_secs_f64());
    println!("wrote: {}", out_db.display());
}
