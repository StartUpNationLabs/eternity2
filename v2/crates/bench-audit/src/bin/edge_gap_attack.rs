// Vol-21 — Gap-guided ALNS attack.
//
// Strategy: compute the relaxed-edge target. Identify cells where the
// target uses a DIFFERENT (pid, rot) than the current board — these
// are the cells where pieces are "misplaced" relative to local optimum.
//
// Destroy those cells + their neighbors, then ALNS-repair under
// piece-uniqueness.
//
// Hypothesis: targeting the gap's specific cells (rather than random
// or worst-cell) gives ALNS-repair a strong local signal to follow.

#![forbid(unsafe_code)]

use std::collections::{BTreeSet, HashSet};
use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::score_board_dense as score_board;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle, Rotation, BORDER};
use eternity2_localsearch::{
    polish_rotations, piece_swap_hillclimb, run_alns, Acceptance, AlnsConfig, ConflictDriven,
    DestroyOp, MwpmDefectPair, RandomRegion, RepairKind, WorstBand, WorstWindow,
};

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> eternity2_core::Board {
    eternity2_export::load_board(path, puzzle).expect("load_board")
}

fn cell_edges(puzzle: &Puzzle, board: &Board, pos: u32) -> Option<[u8; 4]> {
    board.get(pos).map(|(pid, rot)| {
        let piece = puzzle.piece(pid).expect("piece");
        piece.edges.rotated(rot).as_array()
    })
}

fn cell_local_score(puzzle: &Puzzle, board: &Board, pos: u32, edges: [u8; 4]) -> u32 {
    let w = puzzle.width;
    let h = puzzle.height;
    let x = pos % w;
    let y = pos / w;
    let mut s = 0u32;
    if y > 0 {
        if let Some(ne) = cell_edges(puzzle, board, pos - w) {
            if edges[0] != BORDER && ne[2] != BORDER && edges[0] == ne[2] { s += 1; }
        }
    }
    if x + 1 < w {
        if let Some(ne) = cell_edges(puzzle, board, pos + 1) {
            if edges[1] != BORDER && ne[3] != BORDER && edges[1] == ne[3] { s += 1; }
        }
    }
    if y + 1 < h {
        if let Some(ne) = cell_edges(puzzle, board, pos + w) {
            if edges[2] != BORDER && ne[0] != BORDER && edges[2] == ne[0] { s += 1; }
        }
    }
    if x > 0 {
        if let Some(ne) = cell_edges(puzzle, board, pos - 1) {
            if edges[3] != BORDER && ne[1] != BORDER && edges[3] == ne[1] { s += 1; }
        }
    }
    s
}

fn relaxed_target(puzzle: &Puzzle, board: &Board) -> Board {
    let mut b = board.clone();
    let n_cells = puzzle.cell_count();
    for _ in 0..20 {
        let mut changes = 0u32;
        for pos in 0..n_cells {
            let cur_local = b.get(pos).map(|(pid, rot)| {
                let e = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
                cell_local_score(puzzle, &b, pos, e)
            }).unwrap_or(0);
            let mut best: Option<(u16, Rotation, u32)> = None;
            let w = puzzle.width;
            let h = puzzle.height;
            let x = pos % w;
            let y = pos / w;
            for piece in puzzle.pieces() {
                for rot in Rotation::ALL {
                    let e = piece.edges.rotated(rot).as_array();
                    if (e[0] == BORDER) != (y == 0) { continue; }
                    if (e[1] == BORDER) != (x + 1 == w) { continue; }
                    if (e[2] == BORDER) != (y + 1 == h) { continue; }
                    if (e[3] == BORDER) != (x == 0) { continue; }
                    let s = cell_local_score(puzzle, &b, pos, e);
                    if best.map(|(_, _, b_)| s > b_).unwrap_or(true) {
                        best = Some((piece.id, rot, s));
                    }
                }
            }
            if let Some((pid, rot, s)) = best {
                let cur = b.get(pos);
                let cur_pid = cur.map(|(p, _)| p).unwrap_or(0);
                let cur_rot = cur.map(|(_, r)| r).unwrap_or(Rotation::R0);
                if (pid, rot) != (cur_pid, cur_rot) && s > cur_local {
                    b.place(pos, pid, rot);
                    changes += 1;
                }
            }
        }
        if changes == 0 { break; }
    }
    b
}

/// GapAttack destroy op: free cells where the relaxed target disagrees
/// with the current board AT ANY ROTATION. Also free neighbors of those
/// cells (1-hop).
///
/// We can't add to the ALNS DestroyOp trait without modifying alns.rs.
/// Instead, this binary does the destroy + repair in a single PASS,
/// then runs standard ALNS on the residual.
pub struct GapAttack { puzzle_size: u32 }

impl GapAttack {
    /// Returns the set of cells to free, given the current board and relaxed target.
    fn cells_to_destroy(puzzle: &Puzzle, board: &Board, target: &Board) -> BTreeSet<u32> {
        let mut hot: BTreeSet<u32> = BTreeSet::new();
        for pos in 0..puzzle.cell_count() {
            let cur = board.get(pos);
            let tgt = target.get(pos);
            if cur != tgt {
                hot.insert(pos);
            }
        }
        // 1-hop neighbors
        let mut expanded = hot.clone();
        let w = puzzle.width;
        let h = puzzle.height;
        for &pos in &hot {
            let x = pos % w;
            let y = pos / w;
            if y > 0 { expanded.insert(pos - w); }
            if x + 1 < w { expanded.insert(pos + 1); }
            if y + 1 < h { expanded.insert(pos + w); }
            if x > 0 { expanded.insert(pos - 1); }
        }
        expanded
    }
}

fn main() {
    let mut board_path = PathBuf::new();
    let mut alns_budget_ms: u64 = 60_000;
    let mut n_attacks: u64 = 6;
    let mut seed: u64 = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--alns-budget-ms" => alns_budget_ms = args.next().unwrap().parse().unwrap(),
            "--n-attacks" => n_attacks = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("usage: edge_gap_attack --board <path> [--alns-budget-ms N] [--n-attacks N] [--seed N]");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let board = load_board(&board_path, &puzzle);
    let (s_baseline, total) = score_board(&puzzle, &board);
    eprintln!("baseline: {}/{}", s_baseline, total);

    let mut current = board.clone();
    let mut best = current.clone();
    let mut best_score = s_baseline;

    for attack in 0..n_attacks {
        eprintln!("\n=== Attack {} ===", attack);
        let target = relaxed_target(&puzzle, &current);
        let (s_target, _) = score_board(&puzzle, &target);
        let (s_now, _) = score_board(&puzzle, &current);
        let gap = s_target as i32 - s_now as i32;
        eprintln!("current: {}/{}, relaxed target: {}/{}, gap: {:+}", s_now, total, s_target, total, gap);
        let mut hot_cells = GapAttack::cells_to_destroy(&puzzle, &current, &target);
        eprintln!("Cells differing from target (1-hop expanded): {}", hot_cells.len());

        // Augment with random extra cells based on attack iteration:
        // attack 0: +0, attack 1: +10, attack 2: +20, ...
        let extra_radius = (attack as u32) * 10;
        if extra_radius > 0 {
            // Random pick from non-hot, non-hint cells
            let pinned_hints: BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();
            let candidates: Vec<u32> = (0..puzzle.cell_count())
                .filter(|p| !hot_cells.contains(p) && !pinned_hints.contains(p))
                .collect();
            let mut rng_state = seed.wrapping_add(attack as u64 * 0x9E3779B9) | 1;
            for _ in 0..extra_radius.min(candidates.len() as u32) {
                rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                let idx = (rng_state >> 32) as usize % candidates.len();
                hot_cells.insert(candidates[idx]);
            }
            eprintln!("After adding {} random cells: total destroy set {}", extra_radius, hot_cells.len());
        }

        if gap == 0 {
            eprintln!("Gap = 0: provable strict local maximum. Stopping.");
            break;
        }

        // Hint-pinned (non-destroyable) positions = canonical hints UNION (all cells - hot_cells).
        // The ALNS repair will fix the hot region; everything else stays.
        let pinned: BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();
        // We DO destroy hot_cells (except canonical hints). The ALNS pinned_positions
        // is everything OUTSIDE hot_cells UNION canonical hints.
        let mut pinned_for_alns: BTreeSet<u32> = pinned.clone();
        for pos in 0..puzzle.cell_count() {
            if !hot_cells.contains(&pos) {
                pinned_for_alns.insert(pos);
            }
        }
        // To create the destroyed state: clear non-pinned cells in `current`.
        let mut destroyed = current.clone();
        for &pos in &hot_cells {
            if !pinned.contains(&pos) {
                destroyed.clear(pos);
            }
        }
        let (s_destroyed, _) = score_board(&puzzle, &destroyed);
        eprintln!("After destroy: {}/{} (lost {} cells from gap region)",
            s_destroyed, total, hot_cells.len());

        // Run ALNS on the partial board.
        let cfg = AlnsConfig {
            time_budget_ms: alns_budget_ms,
            repair_budget_ms: 1500,
            acceptance: Acceptance::SimulatedAnnealing { t: 1.5 },
            segment_iters: 50,
            seed: seed.wrapping_add(attack * 17),
            verbose: false,
            repair: RepairKind::Sa,
            cp_fallback_to_sa: true,
            pinned_positions: pinned_for_alns.iter().copied().collect::<Vec<u32>>(),
            iter_budget: 0,
            lex_break_isoscore: false,
            checkpoint_path: None,
            checkpoint_every_ms: 60_000,
            repair_step_budget: 0,
            cp_repair_parallel: false,
        };
        let mut ops: Vec<Box<dyn DestroyOp>> = vec![
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(ConflictDriven { max_size: 80 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
            Box::new(WorstBand { k_rows: 4 }),
        ];
        let t0 = Instant::now();
        let (alns_board, _stats) = run_alns(&puzzle, &destroyed, ops.as_mut_slice(), &cfg);
        let (alns_board, _rg) = polish_rotations(&puzzle, &alns_board, &pinned);
        let (alns_board, _sg) = piece_swap_hillclimb(&puzzle, &alns_board, &pinned);
        let dt = t0.elapsed().as_secs_f64();
        let (s_alns, _) = score_board(&puzzle, &alns_board);
        eprintln!("ALNS: {}/{} (Δ from baseline {}: {:+}) in {:.1}s",
            s_alns, total, s_baseline, s_alns as i32 - s_baseline as i32, dt);

        if s_alns > best_score {
            best_score = s_alns;
            best = alns_board.clone();
            eprintln!("** NEW BEST: {}", best_score);
            let out_path = format!("output/v21_gap_attack_best_{}.json", best_score);
            let json = serde_json::json!({
                "matched_best": best_score,
                "placement": (0..puzzle.cell_count()).map(|p| {
                    best.get(p).map(|(pid, rot)| serde_json::json!({
                        "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                    }))
                }).collect::<Vec<_>>(),
            });
            std::fs::write(&out_path, serde_json::to_string_pretty(&json).unwrap()).expect("write");
            eprintln!("Saved to {}", out_path);
        }
        // For next attack, use the best so far as the current board.
        if s_alns >= s_baseline {
            current = alns_board;
        }
    }
    eprintln!("\n=== Final: {} → best {} (Δ {:+}) ===", s_baseline, best_score, best_score as i32 - s_baseline as i32);
}
