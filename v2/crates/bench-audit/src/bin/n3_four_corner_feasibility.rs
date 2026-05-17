// Vol-122 N3 — Fast feasibility test for 4-corner cluster combinations.
//
// Given a 4-tuple (TL, TR, BL, BR) of 3×3 clusters, check necessary conditions:
// L1 (~10 ns): piece-uniqueness across 36 cells.
// L2 (~1 µs): border-ring color consistency (border colors must form a closed loop).
// L3 (~10 µs): edge-piece supply (the 4 unfilled border segments need enough
//             matching edge pieces).
// L4 (~100 µs): per-row/per-col border segment reachability via 1D DP.
//
// Output: SQLite DB with feasibility annotations on each 4-tuple.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use rusqlite::{params, Connection};

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
}

fn load_clusters(conn: &Connection, corner: &str) -> Vec<Cluster> {
    let label_char = match corner {
        "TL" => 'L', "TR" => 'R', "BL" => 'l', "BR" => 'r', _ => panic!(),
    };
    let q = format!("SELECT id,
        p0_pid, p0_rot, p1_pid, p1_rot, p2_pid, p2_rot,
        p3_pid, p3_rot, p4_pid, p4_rot, p5_pid, p5_rot,
        p6_pid, p6_rot, p7_pid, p7_rot, p8_pid, p8_rot
        FROM clusters WHERE corner = '{}' ORDER BY id", corner);
    let mut stmt = conn.prepare(&q).expect("prepare");
    stmt.query_map([], |r| {
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
        Ok(Cluster { id, corner: label_char, pids, rots, pieces })
    }).expect("query").filter_map(Result::ok).collect()
}

/// For a cluster, return the FACING colors on the inward edges (the 6 colors
/// that face the rest of the board).
///
/// For TL 3×3 (board cells (0..2, 0..2)):
///   - Right edges: cells (0,2),(1,2),(2,2) emit their R-side colors → 3 colors.
///   - Bottom edges: cells (2,0),(2,1),(2,2) emit their B-side colors → 3 colors.
///   - Corner cell (2,2) appears in both, but its outward edges are the R-side
///     and the B-side (different colors). 6 outward edges total.
///
/// Returns: ([color_right_top, color_right_mid, color_right_bot],
///          [color_bot_left, color_bot_mid, color_bot_right])
/// where for TL, color_right_top = cell(0,2).R, color_right_mid = cell(1,2).R, etc.
/// Analogous for other corners (we ROTATE the meanings).
fn cluster_facing_edges(cluster: &Cluster, pieces: &[[u8; 4]]) -> ([u8; 3], [u8; 3]) {
    // For TL 3×3, "inward" edges are:
    //   - cells in column 2 (local idx 2, 5, 8) → their R-side faces col 3.
    //   - cells in row 2 (local idx 6, 7, 8) → their B-side faces row 3.
    // For TR, "inward" = cells in column 0 (idx 0, 3, 6) L-side, and row 2 (6,7,8) B-side.
    // For BL: row 0 (0,1,2) T-side and col 2 (2,5,8) R-side.
    // For BR: row 0 (0,1,2) T-side and col 0 (0,3,6) L-side.
    let (col_cells, col_side, row_cells, row_side) = match cluster.corner {
        'L' => ([2, 5, 8], 1u8, [6, 7, 8], 2u8),  // R-side of col 2, B-side of row 2
        'R' => ([0, 3, 6], 3u8, [6, 7, 8], 2u8),  // L-side of col 0, B-side of row 2
        'l' => ([2, 5, 8], 1u8, [0, 1, 2], 0u8),  // R-side of col 2, T-side of row 0
        'r' => ([0, 3, 6], 3u8, [0, 1, 2], 0u8),  // L-side of col 0, T-side of row 0
        _ => panic!(),
    };
    let mut col_colors = [0u8; 3];
    let mut row_colors = [0u8; 3];
    for (i, &c) in col_cells.iter().enumerate() {
        let e = rot_edges(pieces[cluster.pids[c] as usize], cluster.rots[c]);
        col_colors[i] = e[col_side as usize];
    }
    for (i, &c) in row_cells.iter().enumerate() {
        let e = rot_edges(pieces[cluster.pids[c] as usize], cluster.rots[c]);
        row_colors[i] = e[row_side as usize];
    }
    (col_colors, row_colors)
}

/// For an edge-piece, return all (rot, [T,R,B,L]) where the resulting orientation
/// is valid as a TOP-BORDER edge (T=0, both L and R non-zero, B non-zero).
/// We need similar for each border direction. Simpler: enumerate (pid, rot) with
/// piece having exactly 1 border-side (= edge piece), and use it on any border.
fn precompute_edge_options(pieces: &[[u8; 4]]) -> Vec<Vec<(u16, u8, u8, u8)>> {
    // Index by border_color = 0 in which side: 0=top (B-only border)... wait
    // For each edge piece, the BORDER side is fixed (one of T,R,B,L is 0).
    // We need to know: for each edge piece, which rotation puts the border on which
    // side. We'll precompute by output:
    // Returns: for each "border-side" (0=T, 1=R, 2=B, 3=L), list of (pid, rot, L_color, R_color)
    // for L/R interpretation matching the border-row's traversal direction.
    //
    // Simpler: for each piece, generate all (rot, edges) where exactly one of T/R/B/L = 0.
    // The 0-side is the BORDER. The "left" and "right" are the two NEIGHBORS along the border.
    //
    // For top-border traversal (going LEFT to RIGHT along row 0):
    //   - cell's TOP = 0 (border)
    //   - cell's LEFT must match previous cell's RIGHT
    //   - cell's RIGHT becomes next cell's required-LEFT
    //   - cell's BOTTOM faces interior (free to be anything non-0)
    //
    // For each row/col direction (4 total: top, right, bot, left border),
    // we'll precompute: piece-rotations that are valid + their (left_color, right_color).
    let mut by_border_dir: Vec<Vec<(u16, u8, u8, u8)>> = vec![Vec::new(); 4];
    for (pid, e) in pieces.iter().enumerate() {
        let zeros = e.iter().filter(|&&x| x == 0).count();
        if zeros != 1 { continue; }  // edge pieces only
        for rot in 0..4u8 {
            let re = rot_edges(*e, rot);
            // T=0 → top border, going L→R, neighbors are L (prev R) and R (next L)
            if re[0] == 0 {
                by_border_dir[0].push((pid as u16, rot, re[3], re[1]));
            }
            // R=0 → right border, going T→B, neighbors above/below
            if re[1] == 0 {
                by_border_dir[1].push((pid as u16, rot, re[0], re[2]));
            }
            // B=0 → bottom border, going L→R, neighbors L/R
            if re[2] == 0 {
                by_border_dir[2].push((pid as u16, rot, re[3], re[1]));
            }
            // L=0 → left border, going T→B
            if re[3] == 0 {
                by_border_dir[3].push((pid as u16, rot, re[0], re[2]));
            }
        }
    }
    by_border_dir
}

/// Test L2: border-segment reachability.
/// Between two corners along a border (e.g., TL's right edge and TR's left edge
/// on row 0), there are 10 unfilled cells. Check if there exists ANY sequence
/// of 10 edge-pieces from `start_color` to `end_color`, using only edge-pieces
/// NOT already in `used`.
///
/// 1D-DP: state = (cell_index, current_right_color_emitted). Returns true if
/// reachable from start_color to end_color in 10 steps.
fn border_segment_reachable(
    n_intermediate: usize,
    start_left_color: u8,
    end_right_color: u8,
    border_dir: usize,
    edge_options: &[Vec<(u16, u8, u8, u8)>],
    used: &PieceSet,
) -> bool {
    // Edge options for this border direction
    let opts = &edge_options[border_dir];
    // 1D DP: dp[step][output_color] = reachable from start_left_color through `step` cells
    // ending with this cell's output_color (= next cell's required-left).
    // Output: dp[n_intermediate][end_right_color] should be true.
    //
    // Index: 23 colors max (0..22). For canonical E2 with 22 interior colors + 0 border.
    const N_C: usize = 32;
    let mut cur = [false; N_C];
    let mut next = [false; N_C];
    cur[start_left_color as usize] = true;

    for _step in 0..n_intermediate {
        for c in 0..N_C { next[c] = false; }
        for &(pid, _rot, left, right) in opts {
            // Check if piece is already used in the 36-piece corner set
            let used_bit = if pid < 128 {
                (used.low >> pid) & 1
            } else {
                (used.high >> (pid - 128)) & 1
            };
            if used_bit == 1 { continue; }
            if (left as usize) < N_C && cur[left as usize] {
                next[right as usize] = true;
            }
        }
        std::mem::swap(&mut cur, &mut next);
    }
    if (end_right_color as usize) < N_C {
        cur[end_right_color as usize]
    } else {
        false
    }
}

fn check_feasibility(
    tl: &Cluster, tr: &Cluster, bl: &Cluster, br: &Cluster,
    pieces: &[[u8; 4]],
    edge_options: &[Vec<(u16, u8, u8, u8)>],
) -> (bool, &'static str) {
    // L1: piece uniqueness
    let combined = tl.pieces.or(&tr.pieces).or(&bl.pieces).or(&br.pieces);
    let total_bits = combined.low.count_ones() + combined.high.count_ones();
    if total_bits != 36 {
        return (false, "L1: piece collision");
    }

    // For all 4 border segments, get the END colors:
    //
    // TL inward = TL.right_col_colors (3 colors at (0,2), (1,2), (2,2)) and TL.bot_row_colors.
    // TR inward = TR.left_col_colors (at (0,13),(1,13),(2,13)) and TR.bot_row_colors.
    //
    // Row 0 border segment (cols 3..12, 10 cells) connects:
    //   - TL cell (0, 2).R-color → start (this is left-side of cell (0,3))
    //   - TR cell (0, 13).L-color → end
    //
    // The TL.col_colors[0] = R-side of cell (0,2) = TL's row-0 right-most cell.
    // The TR.col_colors[0] = L-side of cell (0,13) = TR's row-0 left-most cell.
    //
    // 10 unfilled cells must form a path from TL.col[0] → TR.col[0].
    // border_dir = 0 (top border).
    let (tl_col_colors, tl_row_colors) = cluster_facing_edges(tl, pieces);
    let (tr_col_colors, tr_row_colors) = cluster_facing_edges(tr, pieces);
    let (bl_col_colors, bl_row_colors) = cluster_facing_edges(bl, pieces);
    let (br_col_colors, br_row_colors) = cluster_facing_edges(br, pieces);

    let debug_mode = std::env::var("DEBUG_N3").is_ok();
    if debug_mode {
        eprintln!("DEBUG: testing TL={} TR={} BL={} BR={}", tl.id, tr.id, bl.id, br.id);
        eprintln!("  TL facing: col={:?} row={:?}", tl_col_colors, tl_row_colors);
        eprintln!("  TR facing: col={:?} row={:?}", tr_col_colors, tr_row_colors);
        eprintln!("  BL facing: col={:?} row={:?}", bl_col_colors, bl_row_colors);
        eprintln!("  BR facing: col={:?} row={:?}", br_col_colors, br_row_colors);
    }
    // Row 0 (top border): TL.right of (0,2) → TR.left of (0,13). 10 intermediate cells.
    let r0 = border_segment_reachable(10, tl_col_colors[0], tr_col_colors[0], 0, edge_options, &combined);
    if debug_mode {
        eprintln!("  row0 ({} -> {}): {}", tl_col_colors[0], tr_col_colors[0], r0);
    }
    if !r0 { return (false, "L4: row 0 segment not reachable"); }
    // Row 15 (bottom border): BL.right of (13,2) → BR.left of (13,13). 10 cells.
    // BL's facing row is top side of cells (15,0),(15,1),(15,2) — that's the BOTTOM border seg only.
    // BL.col_colors are R-side of (13,2),(14,2),(15,2) - inward going right.
    // For row 13 (which is internal at row 13), BL.col[0] = R-side of (13,2). It connects to (13,3) L-side.
    // But row 13 isn't border — it's an interior row.
    // The row 15 (bottom border) connects BL cell (15,2) to BR cell (15,13).
    // BL.row_colors[0] = T-side of (15,0)... wait that's not right for BL's "facing inward".
    //
    // Hmm, this needs re-thinking. For BL (cells 13..15, 0..2):
    //   - Inward-facing edges are:
    //     - col 2 cells (13,2)(14,2)(15,2): R-side faces col 3.
    //     - row 13 cells (13,0)(13,1)(13,2): T-side faces row 12.
    //   - So BL.col_colors = R-side of (13,2),(14,2),(15,2) (col is local-col 2, idx 2,5,8).
    //   - BL.row_colors = T-side of (13,0),(13,1),(13,2) (row is local-row 0, idx 0,1,2).
    //
    // Row 15 border doesn't go through the corners' inward edges! Row 15 is the BOTTOM border,
    // which goes through cells (15,0)(15,1)...(15,15) — all BORDER cells.
    // BL's row 15 cells: (15,0),(15,1),(15,2) — local idx 6,7,8.
    // BR's row 15 cells: (15,13),(15,14),(15,15) — local idx 6,7,8 in BR's frame.
    // The segment between them is row 15 cells (15,3) to (15,12) — 10 cells.
    //
    // BL's (15,2).R = output going east (into (15,3)). That's local idx 8 R-side.
    // BR's (15,13).L = input from west. That's local idx 6 L-side.
    //
    // My cluster_facing_edges() doesn't expose these. Need to recompute properly.
    let _ = (br_col_colors, bl_col_colors);

    // Let me get the actual border-row endpoints
    let tl_e = rot_edges(pieces[tl.pids[8] as usize], tl.rots[8]);  // (2,2) of TL
    let _ = tl_e;
    let bl_15_2_r = {
        let e = rot_edges(pieces[bl.pids[8] as usize], bl.rots[8]);  // (15,2) of BL = local idx 8
        e[1]  // R-side
    };
    let br_15_13_l = {
        let e = rot_edges(pieces[br.pids[6] as usize], br.rots[6]);  // (15,13) of BR = local idx 6
        e[3]  // L-side
    };
    if !border_segment_reachable(10, bl_15_2_r, br_15_13_l, 2, edge_options, &combined) {
        return (false, "L4: row 15 segment not reachable");
    }
    // Col 0 (left border): TL cell (2,0).B → BL cell (13,0).T. 10 cells.
    let tl_2_0_b = {
        let e = rot_edges(pieces[tl.pids[6] as usize], tl.rots[6]);  // (2,0) of TL = local idx 6
        e[2]  // B-side
    };
    let bl_13_0_t = {
        let e = rot_edges(pieces[bl.pids[0] as usize], bl.rots[0]);  // (13,0) of BL = local idx 0
        e[0]  // T-side
    };
    if !border_segment_reachable(10, tl_2_0_b, bl_13_0_t, 3, edge_options, &combined) {
        return (false, "L4: col 0 segment not reachable");
    }
    // Col 15 (right border): TR (2,15).B → BR (13,15).T. 10 cells.
    let tr_2_15_b = {
        let e = rot_edges(pieces[tr.pids[8] as usize], tr.rots[8]);  // (2,15) of TR = local idx 8
        e[2]  // B-side
    };
    let br_13_15_t = {
        let e = rot_edges(pieces[br.pids[2] as usize], br.rots[2]);  // (13,15) of BR = local idx 2
        e[0]  // T-side
    };
    if !border_segment_reachable(10, tr_2_15_b, br_13_15_t, 1, edge_options, &combined) {
        return (false, "L4: col 15 segment not reachable");
    }

    (true, "feasible-L1-L4")
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut in_db = PathBuf::from("output/vol-122/n1_corner_3x3_clusters.sqlite");
    let mut out_db = PathBuf::from("output/vol-122/n3_feasible_4tuples.sqlite");
    let mut sample_count: u64 = 100_000;  // sample N random 4-tuples
    let mut seed: u64 = 42;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--in" => in_db = PathBuf::from(args.next().unwrap()),
            "--out" => out_db = PathBuf::from(args.next().unwrap()),
            "--sample" => sample_count = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
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
    let tl = load_clusters(&conn_in, "TL");
    let tr = load_clusters(&conn_in, "TR");
    let bl = load_clusters(&conn_in, "BL");
    let br = load_clusters(&conn_in, "BR");
    println!("loaded clusters: TL={} TR={} BL={} BR={}",
        tl.len(), tr.len(), bl.len(), br.len());

    let edge_options = precompute_edge_options(&pieces);
    for (i, opts) in edge_options.iter().enumerate() {
        println!("  border-dir {}: {} edge-piece options", i, opts.len());
    }

    std::fs::create_dir_all(out_db.parent().unwrap()).ok();
    let _ = std::fs::remove_file(&out_db);
    let conn_out = Connection::open(&out_db).expect("open out");
    conn_out.execute_batch("
        CREATE TABLE feasible (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tl_id INTEGER NOT NULL,
            tr_id INTEGER NOT NULL,
            bl_id INTEGER NOT NULL,
            br_id INTEGER NOT NULL,
            reason TEXT NOT NULL
        );
    ").expect("create");

    // Sample N random 4-tuples
    let mut rng_state = seed.wrapping_mul(2654435761);
    let mut rand = || {
        rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        rng_state
    };

    let t0 = Instant::now();
    let mut l1_pass = 0u64;
    let mut l4_pass = 0u64;
    let mut feasible_kept = 0u64;
    let mut tx = conn_out.unchecked_transaction().expect("tx");
    {
        let mut stmt = tx.prepare(
            "INSERT INTO feasible (tl_id, tr_id, bl_id, br_id, reason) VALUES (?, ?, ?, ?, ?)"
        ).expect("prepare");
        for trial in 0..sample_count {
            let i_tl = (rand() as usize) % tl.len();
            let i_tr = (rand() as usize) % tr.len();
            let i_bl = (rand() as usize) % bl.len();
            let i_br = (rand() as usize) % br.len();
            let t = &tl[i_tl];
            let r = &tr[i_tr];
            let b = &bl[i_bl];
            let q = &br[i_br];
            let (ok, reason) = check_feasibility(t, r, b, q, &pieces, &edge_options);
            // Quick separate count of L1 pass
            let combined = t.pieces.or(&r.pieces).or(&b.pieces).or(&q.pieces);
            let bits = combined.low.count_ones() + combined.high.count_ones();
            if bits == 36 { l1_pass += 1; }
            if ok {
                l4_pass += 1;
                feasible_kept += 1;
                stmt.execute(params![t.id, r.id, b.id, q.id, reason])
                    .expect("insert");
            }
            if (trial + 1) % 10_000 == 0 {
                println!("  trial {}: L1-pass={} feasible-L4={} elapsed={:.1}s",
                    trial + 1, l1_pass, feasible_kept, t0.elapsed().as_secs_f64());
            }
        }
    }
    tx.commit().expect("commit");

    println!("\n=== TOTAL ===");
    println!("samples: {}", sample_count);
    println!("L1 pass (piece-disjoint): {} ({:.2}%)",
        l1_pass, l1_pass as f64 / sample_count as f64 * 100.0);
    println!("L4 pass (all 4 segments reachable): {} ({:.2}%)",
        l4_pass, l4_pass as f64 / sample_count as f64 * 100.0);
    println!("inserted: {}", feasible_kept);
    println!("elapsed: {:.2}s", t0.elapsed().as_secs_f64());
    println!("wrote: {}", out_db.display());
}
