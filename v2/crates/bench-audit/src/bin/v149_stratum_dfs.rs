// V149 STRATUM v2 — color-class biased DFS.
//
// Cleanly redesigned 2026-05-19:
//   - Variable order: corners → border ring → interior spiral inward.
//     Identical structure to baseline DFS; no surgical changes to how
//     positions are visited.
//   - Value order: at each cell, candidates with the placed-neighbour
//     constraints satisfied are sorted by descending "color-class
//     constraint score":
//       score = 3*(rare-color sides) + 2*(medium-color sides) + 1*(common)
//     Rare = {1..5}; medium = {6..10}; common = {11..22}.
//     This puts the most-color-constrained pieces first, matching the
//     CSP MRV intuition without paying MRV's per-step computation cost.
//
// The DFS itself is a clean general backtracker, not the NW-bucket
// machinery of vanilla_fast — necessary because spiral-inward scan order
// breaks vanilla_fast's row-major NW-bucket assumption.
//
// Performance target: 5–15M placements/sec single-thread (≈1/6 of
// vanilla_fast 85M nps, the cost of the general neighbour check).
// Justification: a spiral interior visit places pieces among already-
// placed cells on 0-4 sides; on average we expect more constraints
// per cell than row-major, so pruning per node is stronger even if
// per-node throughput is lower.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_core::BORDER;
use eternity2_puzzle_io::load_puzzle_with_hints;

const N: usize = 16;
const N_POS: usize = N * N;
const N_PIECES: usize = 256;
const N_ROT: usize = 4;

// Color-class assignment. Border (0) is BORDER. The choice of 5/5/12
// reflects the canonical Selby-Riordan piece set: 5 rare colors with
// 24 occurrences each, 5 medium colors with 48, 12 common with 50.
#[inline]
fn color_class_weight(c: u8) -> u32 {
    match c {
        0 => 0,           // border doesn't bias
        1..=5 => 3,       // rare
        6..=10 => 2,      // medium
        _ => 1,           // common
    }
}

#[derive(Clone, Copy)]
struct PieceRot {
    piece_id: u16,
    rot: u8,
    n: u8, e: u8, s: u8, w: u8,
    /// Sort key: higher = more constrained = try first.
    color_weight: u32,
}

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    let mut out = [0u8; 4];
    for i in 0..4 {
        out[i] = e[(i + 4 - (r as usize)) % 4];
    }
    out
}

#[inline] fn need_n_border(pos: usize) -> bool { pos < N }
#[inline] fn need_w_border(pos: usize) -> bool { pos % N == 0 }
#[inline] fn need_s_border(pos: usize) -> bool { pos >= N_POS - N }
#[inline] fn need_e_border(pos: usize) -> bool { pos % N == N - 1 }

/// Generate corners → border CW → interior spiral inward scan order.
fn build_scan_order() -> Vec<usize> {
    let mut order = Vec::with_capacity(N_POS);
    // 4 corners (TL, TR, BL, BR).
    order.extend_from_slice(&[0, N - 1, N * (N - 1), N * N - 1]);
    // Border ring CW from (1, 0).
    for x in 1..N - 1 { order.push(x); }
    for y in 1..N - 1 { order.push(y * N + (N - 1)); }
    for x in (1..N - 1).rev() { order.push((N - 1) * N + x); }
    for y in (1..N - 1).rev() { order.push(y * N); }
    debug_assert_eq!(order.len(), 60);
    // Interior 14x14 spiral inward from (1, 1).
    for d in 0..7 {
        let top = 1 + d;
        let left = 1 + d;
        let size_ = 14 - 2 * d;
        if size_ <= 0 { continue; }
        if size_ == 1 {
            order.push(top * N + left);
            continue;
        }
        // top edge
        for x in left..left + size_ { order.push(top * N + x); }
        // right edge
        for y in top + 1..top + size_ { order.push(y * N + (left + size_ - 1)); }
        // bottom edge reversed
        for x in (left..left + size_ - 1).rev() { order.push((top + size_ - 1) * N + x); }
        // left edge reversed
        for y in (top + 1..top + size_ - 1).rev() { order.push(y * N + left); }
    }
    debug_assert_eq!(order.len(), N_POS);
    order
}

fn main() {
    let mut budget_ms: u64 = 60_000;
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut pin_hints = false;
    let mut verbose = false;
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget"); i += 2; }
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--pin-hints" => { pin_hints = true; i += 1; }
            "--verbose" => { verbose = true; i += 1; }
            other => { eprintln!("unknown arg {other}"); std::process::exit(2); }
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    assert_eq!(puzzle.width as usize, N);
    assert_eq!(puzzle.height as usize, N);

    // Build piece_rots with color_weight per rotation.
    let mut piece_rots: Vec<PieceRot> = Vec::with_capacity(N_PIECES * N_ROT);
    for pid in 0..N_PIECES as u16 {
        let p = puzzle.piece(pid).expect("piece");
        let base = p.edges.as_array();
        for r in 0..N_ROT as u8 {
            let rot = rotate_edges(base, r);
            let cw = rot.iter().map(|&c| color_class_weight(c)).sum::<u32>();
            piece_rots.push(PieceRot {
                piece_id: pid, rot: r,
                n: rot[0], e: rot[1], s: rot[2], w: rot[3],
                color_weight: cw,
            });
        }
    }

    let scan_order = build_scan_order();

    // Per-cell candidate list: indices into piece_rots, sorted by color_weight DESC.
    // We don't filter for layer; any piece can in principle go anywhere
    // (the structural neighbour check during DFS handles legality).
    let mut sorted_candidates: Vec<u32> = (0..piece_rots.len() as u32).collect();
    sorted_candidates.sort_by(|&a, &b| {
        piece_rots[b as usize].color_weight
            .cmp(&piece_rots[a as usize].color_weight)
            .then(a.cmp(&b))
    });

    // Neighbour topology.
    let mut pos_neighbours: Vec<[Option<usize>; 4]> = Vec::with_capacity(N_POS);
    for pos in 0..N_POS {
        let n_pos = if need_n_border(pos) { None } else { Some(pos - N) };
        let e_pos = if need_e_border(pos) { None } else { Some(pos + 1) };
        let s_pos = if need_s_border(pos) { None } else { Some(pos + N) };
        let w_pos = if need_w_border(pos) { None } else { Some(pos - 1) };
        pos_neighbours.push([n_pos, e_pos, s_pos, w_pos]);
    }

    // Hint table.
    let mut hint_pid_rot: Vec<Option<(u16, u8)>> = vec![None; N_POS];
    if pin_hints {
        for h in hints.hints.iter() {
            hint_pid_rot[h.position as usize] = Some((h.piece_id, h.rotation.as_u8()));
        }
    }

    // DFS state.
    let mut placed_at_pos: Vec<Option<usize>> = vec![None; N_POS];
    let mut used: Vec<bool> = vec![false; N_PIECES];
    let mut chosen_at_depth: Vec<u32> = vec![u32::MAX; N_POS];
    let mut cursor_at_depth: Vec<usize> = vec![0; N_POS];

    let t0 = Instant::now();
    let deadline = t0 + std::time::Duration::from_millis(budget_ms);

    let mut total_placements: u64 = 0;
    let mut total_backtracks: u64 = 0;
    let mut max_depth: u32 = 0;
    let mut depth_placements = vec![0u64; N_POS + 1];

    let mut depth: usize = 0;

    eprintln!("[init] scan_order: corners→border CW→interior spiral-in ({}-pos)", N_POS);
    eprintln!("[init] candidates sorted by color_weight (rare=3, medium=2, common=1) descending");
    eprintln!("[init] pin_hints={pin_hints}, budget={budget_ms}ms");

    'outer: loop {
        if (total_placements & 0xFFFF) == 0 && Instant::now() >= deadline {
            break;
        }
        let pos = scan_order[depth];

        // Constraint colors per side.
        let neighbours = pos_neighbours[pos];
        let mut side_constraint = [i16::MIN; 4]; // i16::MIN means OOB, must be BORDER
        let mut side_unplaced_neighbour = [false; 4]; // unplaced neighbour exists → side must NOT be BORDER
        for side in 0..4 {
            match neighbours[side] {
                None => side_constraint[side] = BORDER as i16,
                Some(np) => match placed_at_pos[np] {
                    Some(idx) => {
                        // Opposite side of neighbour faces us.
                        let pr = piece_rots[idx];
                        side_constraint[side] = match side {
                            0 => pr.s as i16,
                            1 => pr.w as i16,
                            2 => pr.n as i16,
                            3 => pr.e as i16,
                            _ => unreachable!(),
                        };
                    }
                    None => {
                        side_unplaced_neighbour[side] = true;
                    }
                },
            }
        }

        let hint = hint_pid_rot[pos];

        let cur_start = cursor_at_depth[depth];
        let mut cur = cur_start;
        let mut found = u32::MAX;
        while cur < sorted_candidates.len() {
            let pr_idx = sorted_candidates[cur] as usize;
            let pr = piece_rots[pr_idx];
            cur += 1;
            if used[pr.piece_id as usize] { continue; }
            let sides = [pr.n, pr.e, pr.s, pr.w];
            let mut ok = true;
            for s in 0..4 {
                if side_constraint[s] != i16::MIN {
                    if side_constraint[s] == BORDER as i16 {
                        if sides[s] != BORDER { ok = false; break; }
                    } else {
                        if sides[s] as i16 != side_constraint[s] { ok = false; break; }
                    }
                } else if side_unplaced_neighbour[s] {
                    if sides[s] == BORDER { ok = false; break; }
                }
                // else: OOB already encoded in side_constraint via i16::MIN sentinel above
            }
            if !ok { continue; }
            if let Some((hpid, hrot)) = hint {
                if pr.piece_id != hpid || pr.rot != hrot { continue; }
            }
            found = pr_idx as u32;
            break;
        }

        if found != u32::MAX {
            cursor_at_depth[depth] = cur;
            chosen_at_depth[depth] = found;
            let pr = piece_rots[found as usize];
            used[pr.piece_id as usize] = true;
            placed_at_pos[pos] = Some(found as usize);
            total_placements += 1;
            depth_placements[depth] += 1;
            depth += 1;
            if depth as u32 > max_depth {
                max_depth = depth as u32;
                if verbose {
                    eprintln!("[depth] new max d={} ({}ms)", max_depth, t0.elapsed().as_millis());
                }
            }
            if depth == N_POS {
                eprintln!("[solve] FOUND in {}ms", t0.elapsed().as_millis());
                break 'outer;
            }
            cursor_at_depth[depth] = 0;
        } else {
            // Backtrack.
            if depth == 0 { break 'outer; }
            depth -= 1;
            let prev = chosen_at_depth[depth];
            if prev != u32::MAX {
                let pr = piece_rots[prev as usize];
                used[pr.piece_id as usize] = false;
                placed_at_pos[scan_order[depth]] = None;
                chosen_at_depth[depth] = u32::MAX;
            }
            total_backtracks += 1;
        }
    }

    let elapsed = t0.elapsed();
    let pps = (total_placements as f64) / elapsed.as_secs_f64();
    let bps = (total_backtracks as f64) / elapsed.as_secs_f64();

    println!(
        "{{\"profile\":\"stratum_dfs_v149\",\"budget_ms\":{budget_ms},\"elapsed_ms\":{},\"placements\":{total_placements},\"backtracks\":{total_backtracks},\"max_depth\":{max_depth},\"placements_per_sec\":{:.0},\"backtracks_per_sec\":{:.0}}}",
        elapsed.as_millis(), pps, bps
    );

    eprintln!("[depth-dist] placements at depth-range:");
    for lo in (0..N_POS as u32).step_by(20) {
        let hi = (lo + 19).min(N_POS as u32 - 1);
        let sum: u64 = (lo..=hi).map(|d| depth_placements[d as usize]).sum();
        if sum > 0 {
            eprintln!(
                "  d={:>3}-{:>3}: {:>15} ({:>5.1}%)",
                lo, hi, sum,
                sum as f64 * 100.0 / total_placements.max(1) as f64
            );
        }
    }
}
