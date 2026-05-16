// Blackwood-schedule factories. Ported from solver-engine/src/schedule_builders.rs
// (verified by vol-15..17 calibration work). See [[blackwood-algorithm]] +
// [[blackwood-schedule-calibration]] in vault.

use eternity2_core::{Color, Hints, Puzzle, BORDER};

use crate::BlackwoodSchedule;

/// Vol-107 T1 — const tables for the v17a schedule pre-evaluated at every
/// depth ∈ 0..256 (canonical 16×16). Used by the unrolled engine variant
/// to fold per-D schedule lookups into immediate values, eliminating one
/// L1 load per node.
///
/// `TARGETS_V17A_CANONICAL[D]` = required cumulative heuristic-edge count
/// at depth D, computed from the v17a exhaustion_targets curve.
/// `CONFLICTS_V17A_CANONICAL[D]` = cumulative break-budget at depth D,
/// computed from the canonical break-index set [201, 206, ..., 255].
///
/// Both are evaluated by const fns at compile time. Values match what
/// `blackwood_schedule_calibrated_v17a(&canonical_puzzle, &canonical_hints)`
/// produces at runtime, modulo `pool_size.min(150)` which we approximate
/// as 150 (canonical pool_size on Selby-Riordan is >150).
pub const TARGETS_V17A_CANONICAL: [u32; 256] = compute_targets_v17a_canonical();
pub const CONFLICTS_V17A_CANONICAL: [u32; 256] = compute_conflicts_v17a_canonical();

const fn compute_targets_v17a_canonical() -> [u32; 256] {
    // From schedule.rs blackwood_schedule_calibrated_v17a:
    //   (0, 0), (60, 21), (80, 32), (100, 41), (120, 48),
    //   (140, 58), (160, 82), (200, 112), (255, 150).
    const CONTROL: [(u32, u32); 9] = [
        (0, 0),
        (60, 21),
        (80, 32),
        (100, 41),
        (120, 48),
        (140, 58),
        (160, 82),
        (200, 112),
        (255, 150),
    ];
    let mut out = [0u32; 256];
    let mut d = 0u32;
    while d < 256 {
        // Find the control-point interval [c0, c1] containing d.
        let mut i = 0;
        while i + 1 < CONTROL.len() && CONTROL[i + 1].0 < d {
            i += 1;
        }
        // Interpolate.
        if d >= CONTROL[CONTROL.len() - 1].0 {
            out[d as usize] = CONTROL[CONTROL.len() - 1].1;
        } else if d <= CONTROL[0].0 {
            out[d as usize] = CONTROL[0].1;
        } else {
            let (d0, c0) = CONTROL[i];
            let (d1, c1) = CONTROL[i + 1];
            if d1 == d0 {
                out[d as usize] = c1;
            } else {
                let span = (d1 - d0) as i64;
                let dc = c1 as i64 - c0 as i64;
                let off = (d - d0) as i64;
                let interp = c0 as i64 + (dc * off) / span;
                out[d as usize] = if interp < 0 { 0 } else { interp as u32 };
            }
        }
        d += 1;
    }
    out
}

const fn compute_conflicts_v17a_canonical() -> [u32; 256] {
    // Canonical break-indexes (n_pos=256 so the proportional scale is identity):
    const BREAKS: [u32; 12] = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 255];
    let mut out = [0u32; 256];
    let mut d: u32 = 0;
    let mut budget: u32 = 0;
    while d < 256 {
        // Increment budget if d is in BREAKS.
        let mut i = 0;
        while i < BREAKS.len() {
            if BREAKS[i] == d {
                budget += 1;
            }
            i += 1;
        }
        out[d as usize] = budget;
        d += 1;
    }
    out
}

/// Pick Blackwood's 3 "heuristic colors" by (a) high piece-edge occurrence
/// count, (b) not on any corner piece, (c) not on the centre/start hint
/// piece. Matches `solver-engine::compute_heuristic_sides`.
pub fn compute_heuristic_sides(puzzle: &Puzzle, hints: &Hints) -> Vec<Color> {
    if let Ok(s) = std::env::var("E2_HEURISTIC_SIDES_OVERRIDE") {
        let parsed: Vec<Color> = s
            .split(',')
            .filter_map(|t| t.trim().parse::<Color>().ok())
            .collect();
        if parsed.len() == 3 {
            eprintln!("[heuristic-sides] OVERRIDE active: {:?}", parsed);
            return parsed;
        }
    }
    let pieces = puzzle.pieces();

    let mut corner_colors: std::collections::HashSet<Color> = Default::default();
    for p in pieces {
        let e = p.edges.as_array();
        let n_border = e.iter().filter(|&&c| c == BORDER).count();
        if n_border == 2 {
            for &c in &e {
                if c != BORDER {
                    corner_colors.insert(c);
                }
            }
        }
    }

    let n_pos = puzzle.cell_count();
    let centre_pos = n_pos / 2;
    let start_piece = hints
        .hints
        .iter()
        .find(|h| h.position == centre_pos)
        .or_else(|| {
            let w = puzzle.width;
            let h_ = puzzle.height;
            hints.hints.iter().find(|hh| {
                let (x, y) = (hh.position % w, hh.position / w);
                x > 0 && x + 1 < w && y > 0 && y + 1 < h_
            })
        })
        .and_then(|h| puzzle.piece(h.piece_id));

    let mut start_colors: std::collections::HashSet<Color> = Default::default();
    if let Some(p) = start_piece {
        for &c in &p.edges.as_array() {
            if c != BORDER {
                start_colors.insert(c);
            }
        }
    }

    let forbidden: std::collections::HashSet<Color> =
        corner_colors.union(&start_colors).copied().collect();

    let mut counts: std::collections::HashMap<Color, u32> = Default::default();
    for p in pieces {
        for &c in &p.edges.as_array() {
            if c != BORDER {
                *counts.entry(c).or_insert(0) += 1;
            }
        }
    }

    let mut candidates: Vec<(Color, u32)> = counts
        .into_iter()
        .filter(|(c, _)| !forbidden.contains(c))
        .collect();
    candidates.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    candidates.into_iter().take(3).map(|(c, _)| c).collect()
}

pub fn count_color_occurrences(puzzle: &Puzzle, colors: &[Color]) -> u32 {
    let set: std::collections::HashSet<Color> = colors.iter().copied().collect();
    let mut n = 0u32;
    for p in puzzle.pieces() {
        for &c in &p.edges.as_array() {
            if c != BORDER && set.contains(&c) {
                n += 1;
            }
        }
    }
    n
}

/// Vol-15 — Blackwood's 469-recipe schedule, affine-remapped into our
/// post-border depth range. See solver-engine::blackwood_schedule_469
/// for full history.
pub fn blackwood_schedule_469(puzzle: &Puzzle, hints: &Hints) -> Option<BlackwoodSchedule> {
    let colors = compute_heuristic_sides(puzzle, hints);
    if colors.len() < 3 {
        return None;
    }
    let pool_size = count_color_occurrences(puzzle, &colors);
    let n_pos = puzzle.cell_count();
    let w = puzzle.width;
    let h = puzzle.height;
    let border_ring = 2 * w + 2 * h - 4;

    let bw_pool = 122u32;
    let scale_c = |c: u32| ((c as u64 * pool_size as u64) / bw_pool as u64) as u32;

    let post_border = border_ring + 1;
    let target_max = ((160u64 * n_pos as u64) / 256) as u32;
    if target_max <= post_border {
        return None;
    }

    let bw_depths: [u32; 6] = [16, 26, 56, 76, 102, 160];
    let bw_counts: [u32; 6] = [0, 28, 71, 89, 106, 119];
    let remap = |d: u32| -> u32 {
        let num = (d - 16) as u64 * (target_max - post_border) as u64;
        let den = (160 - 16) as u64;
        post_border + (num / den) as u32
    };

    let mut targets: Vec<(u32, u32)> = Vec::with_capacity(bw_depths.len() + 1);
    targets.push((0, 0));
    for (&d, &c) in bw_depths.iter().zip(bw_counts.iter()) {
        targets.push((remap(d), scale_c(c)));
    }

    // Blackwood's canonical break-index set, scaled proportionally.
    let bw_breaks: [u32; 12] = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256];
    let breaks: Vec<u32> = bw_breaks
        .iter()
        .map(|&b| {
            let scaled = ((b as u64 * n_pos as u64) / 256u64) as u32;
            scaled.min(n_pos.saturating_sub(1))
        })
        .collect();

    Some(BlackwoodSchedule {
        heuristic_sides: colors,
        exhaustion_targets: targets,
        max_heuristic_index: target_max,
        break_indexes_allowed: breaks,
    })
}

/// Vol-17 idea A — empirically calibrated schedule derived from McGavin's
/// 469 community board (N=1 corpus). Less aggressive than the
/// affine-remapped vol-15 schedule. From `output/v17_calibration.json`.
pub fn blackwood_schedule_calibrated_v17a(puzzle: &Puzzle, hints: &Hints) -> Option<BlackwoodSchedule> {
    let colors = compute_heuristic_sides(puzzle, hints);
    if colors.len() < 3 {
        return None;
    }
    let pool_size = count_color_occurrences(puzzle, &colors);
    let n_pos = puzzle.cell_count();
    let last_idx = n_pos.saturating_sub(1);

    let targets: Vec<(u32, u32)> = vec![
        (0, 0),
        (60, 21),
        (80, 32),
        (100, 41),
        (120, 48),
        (140, 58),
        (160, 82),
        (200, 112),
        (last_idx, pool_size.min(150)),
    ];

    let bw_breaks: [u32; 12] = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256];
    let breaks: Vec<u32> = bw_breaks
        .iter()
        .map(|&b| {
            let scaled = ((b as u64 * n_pos as u64) / 256u64) as u32;
            scaled.min(n_pos.saturating_sub(1))
        })
        .collect();

    let target_max = targets.last().map(|&(d, _)| d).unwrap_or(last_idx);
    Some(BlackwoodSchedule {
        heuristic_sides: colors,
        exhaustion_targets: targets,
        max_heuristic_index: target_max,
        break_indexes_allowed: breaks,
    })
}
