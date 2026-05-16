// Blackwood-schedule factories. Ported from solver-engine/src/schedule_builders.rs
// (verified by vol-15..17 calibration work). See [[blackwood-algorithm]] +
// [[blackwood-schedule-calibration]] in vault.

use eternity2_core::{Color, Hints, Puzzle, BORDER};

use crate::BlackwoodSchedule;

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

    Some(BlackwoodSchedule {
        heuristic_sides: colors,
        exhaustion_targets: targets,
        max_heuristic_index: target_max,
    })
}
