// Vol-122 N1 — Enumerate all valid 3×3 corner clusters with canonical hint.
//
// For each of the 4 board corners (TL, TR, BL, BR), enumerate all 3×3 cluster
// placements where:
// - The cell diagonal-opposite the board corner holds the canonical hint
//   piece + rotation (e.g., for TL 3×3, cell (2,2) holds piece 207 rot 1).
// - All 5 border-touching cells respect the board's outer border.
// - All 12 internal edges of the 3×3 are perfectly matched.
// - No piece is used twice.
// - Corner piece slot only allows actual corner pieces; edge slots only allow
//   actual edge pieces; interior slots only allow interior pieces.
//
// Output: SQLite database with one row per valid 3×3 cluster.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;
use std::sync::atomic::{AtomicU64, Ordering};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use rusqlite::{params, Connection};

const SIDE: usize = 16;

#[derive(Clone, Copy, Debug)]
struct PieceRot {
    pid: u16,
    rot: u8,
    edges: [u8; 4],  // T, R, B, L
}

fn rot_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    match r {
        0 => e,
        1 => [e[3], e[0], e[1], e[2]],
        2 => [e[2], e[3], e[0], e[1]],
        _ => [e[1], e[2], e[3], e[0]],
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum PieceClass { Corner, Edge, Interior }

fn classify(e: [u8; 4]) -> PieceClass {
    let zeros = e.iter().filter(|&&x| x == 0).count();
    match zeros {
        2 => PieceClass::Corner,
        1 => PieceClass::Edge,
        _ => PieceClass::Interior,
    }
}

/// For each (row 0..2, col 0..2) cell of the 3×3, the four cardinal directions
/// (T, R, B, L) where each is one of:
///  - Border: must be color 0
///  - Match-to(other_cell, other_side): must equal that cell's side
///  - Free: no constraint other than piece type
#[derive(Clone, Copy, Debug)]
enum SideConstraint {
    Border,
    Match(u8, u8),  // (other_cell_idx 0..8, other_side 0..3)
}

fn cell_idx(r: usize, c: usize) -> u8 { (r * 3 + c) as u8 }

/// Determine border-side mask for a 3×3 anchored at (anchor_r, anchor_c)
/// where anchor is the top-left of the 3×3 (in board coords).
fn border_constraints(corner: char) -> [[bool; 4]; 9] {
    // corner ∈ {'T'L, 'TR', 'BL', 'BR'}.
    // Returns per-cell [T_border, R_border, B_border, L_border].
    let mut out = [[false; 4]; 9];
    match corner {
        'L' => {
            // TL: 3×3 at (0..2, 0..2). Top border on row 0, left border on col 0.
            for r in 0..3 {
                for c in 0..3 {
                    let idx = r * 3 + c;
                    out[idx][0] = r == 0;  // top border
                    out[idx][3] = c == 0;  // left border
                }
            }
        }
        'R' => {
            // TR: 3×3 at (0..2, 13..15). Top border on row 0, right border on col 15.
            for r in 0..3 {
                for c in 0..3 {
                    let idx = r * 3 + c;
                    out[idx][0] = r == 0;
                    out[idx][1] = c == 2;  // right border (board col 15 = local col 2)
                }
            }
        }
        'l' => {
            // BL: 3×3 at (13..15, 0..2). Bottom border on row 15, left border on col 0.
            for r in 0..3 {
                for c in 0..3 {
                    let idx = r * 3 + c;
                    out[idx][2] = r == 2;  // bottom border
                    out[idx][3] = c == 0;
                }
            }
        }
        'r' => {
            // BR: 3×3 at (13..15, 13..15). Bottom border on row 15, right border on col 15.
            for r in 0..3 {
                for c in 0..3 {
                    let idx = r * 3 + c;
                    out[idx][2] = r == 2;
                    out[idx][1] = c == 2;
                }
            }
        }
        _ => panic!("bad corner"),
    }
    out
}

/// Required piece class per cell, given border mask.
fn cell_class(border: [bool; 4]) -> PieceClass {
    let n_borders = border.iter().filter(|&&b| b).count();
    match n_borders {
        2 => PieceClass::Corner,
        1 => PieceClass::Edge,
        _ => PieceClass::Interior,
    }
}

/// Within a 3×3, for each cell, where the hint goes for each corner.
/// Returns the local cell index (0..8 = 3*r + c) AND the canonical (pid, rot).
fn hint_for_corner(corner: char) -> (usize, u16, u8) {
    // Canonical hints (board): pos 34 (2,2)=207r1, pos 45 (2,13)=254r1,
    //                         pos 210 (13,2)=180r1, pos 221 (13,13)=248r2.
    // For each 3×3, the hint is at the diagonal-opposite-board-corner cell:
    match corner {
        'L' => (3 * 2 + 2, 207, 1),  // (2, 2) in TL 3×3 → local (2,2)
        'R' => (3 * 2 + 0, 254, 1),  // (2, 13) in TR 3×3 → local (2, 0) since TR is (0..2, 13..15) → col 0 is board col 13
        'l' => (3 * 0 + 2, 180, 1),  // (13, 2) in BL 3×3 → local (0, 2)
        'r' => (3 * 0 + 0, 248, 2),  // (13, 13) in BR 3×3 → local (0, 0)
        _ => panic!("bad corner"),
    }
}

/// Cell-fill ORDER for enumeration. Place most-constrained cells first.
/// For TL: hint at (2,2), corner at (0,0). Best order: corner first, then
/// border-adjacent, then interior, end at hint (which is fixed last so we
/// just validate).
/// Actually since the hint is fixed, we should place IT first, then constrain
/// neighbors. So order: hint, corner, border-cells, interior.
fn fill_order(corner: char, hint_idx: usize, corner_idx: usize) -> Vec<usize> {
    // Generic order: hint first (it's fixed), then board-corner cell, then
    // remaining cells. Within remaining, do border cells before interiors.
    let mut order = vec![hint_idx, corner_idx];
    let _ = corner;
    let mut visited = vec![false; 9];
    visited[hint_idx] = true;
    visited[corner_idx] = true;
    // Add border cells (cells touching one or two borders), then interior.
    // For now, just add cells in fixed numeric order.
    for i in 0..9 {
        if !visited[i] {
            order.push(i);
            visited[i] = true;
        }
    }
    order
}

/// Adjacent-cell constraints WITHIN a 3×3.
/// For cell i = (r, c) at local 3×3 position, returns the list of
/// (neighbor_idx, side_on_this_cell, side_on_neighbor) for cells that are
/// ADJACENT within the 3×3 (top/right/bot/left neighbors that exist in the 3×3).
fn internal_neighbors(i: usize) -> Vec<(usize, u8, u8)> {
    let r = i / 3;
    let c = i % 3;
    let mut out = Vec::new();
    // Top neighbor (r-1, c)
    if r > 0 {
        out.push(((r - 1) * 3 + c, 0u8, 2u8));  // this top = neighbor bot
    }
    // Right (r, c+1)
    if c < 2 {
        out.push((r * 3 + (c + 1), 1u8, 3u8));  // this right = neighbor left
    }
    // Bot (r+1, c)
    if r < 2 {
        out.push(((r + 1) * 3 + c, 2u8, 0u8));  // this bot = neighbor top
    }
    // Left (r, c-1)
    if c > 0 {
        out.push((r * 3 + (c - 1), 3u8, 1u8));  // this left = neighbor right
    }
    out
}

#[derive(Clone, Copy, Debug)]
struct Placed {
    pid: u16,
    rot: u8,
    edges: [u8; 4],
}

fn validate_placement(
    cell_idx: usize,
    pr: PieceRot,
    placement: &[Option<Placed>; 9],
    borders: &[[bool; 4]; 9],
) -> bool {
    // Check borders
    for side in 0..4 {
        if borders[cell_idx][side] {
            if pr.edges[side] != 0 { return false; }
        } else {
            if pr.edges[side] == 0 { return false; }
        }
    }
    // Check matches with already-placed neighbors
    for (nb, this_side, nb_side) in internal_neighbors(cell_idx) {
        if let Some(p) = placement[nb] {
            if pr.edges[this_side as usize] != p.edges[nb_side as usize] {
                return false;
            }
            // Note: 0=0 match would mean both are border, but borders are checked
            // separately. Internal edges should never be 0 here.
            if pr.edges[this_side as usize] == 0 {
                return false;  // can't have border color on internal edge
            }
        }
    }
    true
}

fn recurse(
    order: &[usize],
    order_pos: usize,
    placement: &mut [Option<Placed>; 9],
    used_pids: &mut [bool; 256],
    borders: &[[bool; 4]; 9],
    pieces_by_class: &[Vec<u16>; 3],
    pieces: &[[u8; 4]],
    hint_pids_to_reserve: &[u16],
    callback: &mut impl FnMut(&[Option<Placed>; 9]),
    counter: &AtomicU64,
) {
    if order_pos == order.len() {
        callback(placement);
        return;
    }
    let cell = order[order_pos];
    let class = cell_class(borders[cell]);
    let candidates = match class {
        PieceClass::Corner => &pieces_by_class[0],
        PieceClass::Edge => &pieces_by_class[1],
        PieceClass::Interior => &pieces_by_class[2],
    };
    for &pid in candidates {
        if used_pids[pid as usize] { continue; }
        // Skip canonical hint pieces UNLESS this cell is supposed to be a hint cell
        // (the hint cell is already placed at order_pos=0, so any other slot must
        // skip the 5 hint pieces).
        if hint_pids_to_reserve.contains(&pid) { continue; }

        for rot in 0..4u8 {
            let edges = rot_edges(pieces[pid as usize], rot);
            let pr = PieceRot { pid, rot, edges };
            if !validate_placement(cell, pr, placement, borders) { continue; }

            placement[cell] = Some(Placed { pid, rot, edges });
            used_pids[pid as usize] = true;
            counter.fetch_add(1, Ordering::Relaxed);

            recurse(order, order_pos + 1, placement, used_pids, borders,
                pieces_by_class, pieces, hint_pids_to_reserve, callback, counter);

            placement[cell] = None;
            used_pids[pid as usize] = false;
        }
    }
}

fn enumerate_corner(
    corner: char,
    pieces: &[[u8; 4]],
    pieces_by_class: &[Vec<u16>; 3],
    canonical_hints: &[(usize, u16, u8)],  // (local_cell_idx, pid, rot)
    callback: &mut impl FnMut(&[Option<Placed>; 9]),
) -> u64 {
    let borders = border_constraints(corner);
    let (hint_idx, hint_pid, hint_rot) = hint_for_corner(corner);

    // Determine the BOARD-CORNER cell (the actual corner of the 3×3 that's at
    // the board border-corner). For TL: (0,0) = local idx 0. For TR: (0,2) = 2.
    // For BL: (2,0) = 6. For BR: (2,2) = 8.
    let corner_idx = match corner {
        'L' => 0,
        'R' => 2,
        'l' => 6,
        'r' => 8,
        _ => panic!(),
    };

    let order = fill_order(corner, hint_idx, corner_idx);

    let mut placement: [Option<Placed>; 9] = [None; 9];
    let mut used: [bool; 256] = [false; 256];

    // Place the hint piece first (if its border constraints permit)
    let hint_edges = rot_edges(pieces[hint_pid as usize], hint_rot);
    let hint_pr = PieceRot { pid: hint_pid, rot: hint_rot, edges: hint_edges };
    if !validate_placement(hint_idx, hint_pr, &placement, &borders) {
        eprintln!("WARN: hint piece at corner {} cell {} doesn't validate", corner, hint_idx);
        return 0;
    }
    placement[hint_idx] = Some(Placed { pid: hint_pid, rot: hint_rot, edges: hint_edges });
    used[hint_pid as usize] = true;

    // We want OTHER hint pieces to not be used in this 3×3 either (they're
    // reserved for their corner). The 5 canonical hint pids must be excluded.
    let hint_pids_to_reserve: Vec<u16> = canonical_hints.iter()
        .map(|(_, pid, _)| *pid)
        .filter(|p| *p != hint_pid)
        .collect();

    let counter = AtomicU64::new(0);
    recurse(&order, 1, &mut placement, &mut used, &borders, pieces_by_class,
        pieces, &hint_pids_to_reserve, callback, &counter);
    counter.load(Ordering::Relaxed)
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut out_db = PathBuf::from("output/vol-122/n1_corner_3x3_clusters.sqlite");
    let mut limit: u64 = u64::MAX;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--out" => out_db = PathBuf::from(args.next().unwrap()),
            "--limit" => limit = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();
    println!("loaded {} pieces from {}", pieces.len(), puzzle_path.display());

    // Pre-classify
    let mut by_class: [Vec<u16>; 3] = Default::default();
    for (i, e) in pieces.iter().enumerate() {
        let c = classify(*e);
        let bucket = match c {
            PieceClass::Corner => 0,
            PieceClass::Edge => 1,
            PieceClass::Interior => 2,
        };
        by_class[bucket].push(i as u16);
    }
    println!("corners: {}, edges: {}, interior: {}",
        by_class[0].len(), by_class[1].len(), by_class[2].len());

    // Canonical hints
    let canonical_hints = vec![
        (34, 207u16, 1u8),
        (45, 254u16, 1u8),
        (135, 138u16, 0u8),
        (210, 180u16, 1u8),
        (221, 248u16, 2u8),
    ];

    // Open SQLite
    std::fs::create_dir_all(out_db.parent().unwrap()).ok();
    let _ = std::fs::remove_file(&out_db);
    let conn = Connection::open(&out_db).expect("open sqlite");
    conn.execute_batch("
        CREATE TABLE clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corner TEXT NOT NULL,
            -- 9 pieces with rotations, in local cell order (idx 0..8 = 3*r + c)
            p0_pid INTEGER, p0_rot INTEGER,
            p1_pid INTEGER, p1_rot INTEGER,
            p2_pid INTEGER, p2_rot INTEGER,
            p3_pid INTEGER, p3_rot INTEGER,
            p4_pid INTEGER, p4_rot INTEGER,
            p5_pid INTEGER, p5_rot INTEGER,
            p6_pid INTEGER, p6_rot INTEGER,
            p7_pid INTEGER, p7_rot INTEGER,
            p8_pid INTEGER, p8_rot INTEGER
        );
        CREATE INDEX idx_corner ON clusters(corner);
    ").expect("create");

    let total_count = std::sync::Arc::new(AtomicU64::new(0));
    let inserted = std::sync::Arc::new(AtomicU64::new(0));

    let t0 = Instant::now();

    for corner in ['L', 'R', 'l', 'r'] {
        let label = match corner {
            'L' => "TL", 'R' => "TR", 'l' => "BL", 'r' => "BR", _ => "?",
        };
        println!("\n=== ENUMERATING {} ===", label);
        let t_corner = Instant::now();
        let mut local_count: u64 = 0;
        let mut tx = conn.unchecked_transaction().expect("tx");
        {
            let mut stmt = tx.prepare("INSERT INTO clusters (corner,
                p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot,
                p3_pid, p3_rot, p4_pid, p4_rot, p5_pid, p5_rot,
                p6_pid, p6_rot, p7_pid, p7_rot, p8_pid, p8_rot)
                VALUES (?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").expect("prepare");
            let ti = inserted.clone();
            let _explored = enumerate_corner(corner, &pieces, &by_class, &canonical_hints, &mut |pl| {
                local_count += 1;
                if ti.load(Ordering::Relaxed) >= limit { return; }
                let mut row: [i64; 18] = [0; 18];
                for i in 0..9 {
                    let p = pl[i].expect("all cells filled");
                    row[i * 2] = p.pid as i64;
                    row[i * 2 + 1] = p.rot as i64;
                }
                stmt.execute(params![label,
                    row[0], row[1], row[2], row[3], row[4], row[5],
                    row[6], row[7], row[8], row[9], row[10], row[11],
                    row[12], row[13], row[14], row[15], row[16], row[17]
                ]).expect("insert");
                ti.fetch_add(1, Ordering::Relaxed);
            });
        }
        tx.commit().expect("commit");
        total_count.fetch_add(local_count, Ordering::Relaxed);
        println!("  found {} valid 3×3 for {} in {:.2}s",
            local_count, label, t_corner.elapsed().as_secs_f64());
    }

    let n_rows: i64 = conn.query_row("SELECT COUNT(*) FROM clusters", [], |r| r.get(0)).unwrap();
    println!("\n=== TOTAL ===");
    println!("inserted: {}", n_rows);
    println!("elapsed: {:.2}s", t0.elapsed().as_secs_f64());
    println!("wrote: {}", out_db.display());
}
