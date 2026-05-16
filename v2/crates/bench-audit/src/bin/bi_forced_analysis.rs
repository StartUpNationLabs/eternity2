// Identify which 2 of the 4 B-I mismatched edges in vol-32 458 are
// LP-forced (cannot be matched) vs fixable.
//
// For each subset of 2 from the 4 mismatched B-I edges, force the
// LP to match them. If LP feasible → those 2 are fixable. If LP
// infeasible → those 2 are forced.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::{lp_ub_with, strip_interior_except_hints, LpOptions};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use serde_json::Value;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let hint_positions: Vec<Position> = hints.hints.iter().map(|h| h.position).collect();

    let board_path = "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json";
    let board = load_board(&PathBuf::from(board_path), &puzzle).expect("load board");
    let border_board = strip_interior_except_hints(&puzzle, &board, &hint_positions);

    // From mismatch_map: the 4 B-I mismatches are between:
    //  perim 242=(2,15) — interior 226=(2,14)
    //  perim 243=(3,15) — interior 227=(3,14)
    //  perim 247=(7,15) — interior 231=(7,14)
    //  perim 254=(14,15) — interior 238=(14,14)
    //
    // In the LP, B-I demand is (interior_cell, interior_side_facing_perim, required_color).
    // The perim cells are on row y=15 (bottom edge), so interior cells y=14 face DOWN (side 2)
    // → wait. Let me re-derive: a cell at (x,14) with perim neighbor at (x,15) — the perim is
    // BELOW. So the interior cell's BOTTOM side (side 2) faces perim's TOP side (side 0).
    // The required color is perim_piece's TOP-side color.

    let mismatch_cells: [(u32, u32); 4] = [(2,14), (3,14), (7,14), (14,14)];
    let mut bi_edges: Vec<(Position, u8, u8)> = Vec::new();
    for &(x, y) in &mismatch_cells {
        let int_pos = y * puzzle.width + x;
        // perim cell directly below
        let perim_pos = (y + 1) * puzzle.width + x;
        let (ppid, prot) = board.get(perim_pos).expect("perim placed");
        let pp = puzzle.piece(ppid).unwrap();
        let pedges = pp.edges.rotated(prot).as_array();
        let required_color = pedges[0]; // perim's TOP side faces interior's BOTTOM
        bi_edges.push((int_pos, 2u8, required_color));
        eprintln!("B-I edge: interior {int_pos}=({x},{y}) side=BOTTOM(2) needs color {required_color}");
    }

    // First: force ALL 4 to match.
    {
        let force: Vec<_> = bi_edges.clone();
        let opts = LpOptions {
            verbose: false, threads: 8, time_limit_secs: 600.0,
            use_ipm: true, presolve: true, integer: false,
            force_bi_match: force,
        };
        eprintln!("Forcing ALL 4: {:?}", bi_edges);
        let t0 = std::time::Instant::now();
        match lp_ub_with(&puzzle, &border_board, opts) {
            Ok(r) => {
                println!("all_4\tFEASIBLE\ttotal_ub={:.4}\ttime={:.1}s", r.total_ub, t0.elapsed().as_secs_f64());
            }
            Err(e) => {
                println!("all_4\tINFEASIBLE\terror={e}\ttime={:.1}s", t0.elapsed().as_secs_f64());
            }
        }
    }

    // Also force each triple:
    for skip_i in 0..4 {
        let force: Vec<_> = bi_edges.iter().enumerate()
            .filter(|(i, _)| *i != skip_i).map(|(_, e)| *e).collect();
        let opts = LpOptions {
            verbose: false, threads: 8, time_limit_secs: 600.0,
            use_ipm: true, presolve: true, integer: false,
            force_bi_match: force,
        };
        eprintln!("Forcing 3 (skip {skip_i})");
        let t0 = std::time::Instant::now();
        match lp_ub_with(&puzzle, &border_board, opts) {
            Ok(r) => {
                println!("triple_skip_{skip_i}\tFEASIBLE\ttotal_ub={:.4}\ttime={:.1}s", r.total_ub, t0.elapsed().as_secs_f64());
            }
            Err(e) => {
                println!("triple_skip_{skip_i}\tINFEASIBLE\terror={e}\ttime={:.1}s", t0.elapsed().as_secs_f64());
            }
        }
    }

    return; // skip the pair tests (already done in earlier run)
    #[allow(unreachable_code)]
    let mut results: Vec<(usize, usize, f64, bool)> = Vec::new();
    #[allow(unreachable_code)]
    for i in 0..4 {
        for j in (i+1)..4 {
            let force = vec![bi_edges[i], bi_edges[j]];
            let opts = LpOptions {
                verbose: false,
                threads: 8,
                time_limit_secs: 600.0,
                use_ipm: true,
                presolve: true,
                integer: false,
                force_bi_match: force.clone(),
            };
            eprintln!("Forcing pair ({i},{j}): {:?} and {:?}", bi_edges[i], bi_edges[j]);
            let t0 = std::time::Instant::now();
            match lp_ub_with(&puzzle, &border_board, opts) {
                Ok(r) => {
                    let dt = t0.elapsed().as_secs_f64();
                    println!("pair_{i}_{j}\tFEASIBLE\ttotal_ub={:.4}\ttime={dt:.1}s", r.total_ub);
                    results.push((i, j, r.total_ub, true));
                }
                Err(e) => {
                    let dt = t0.elapsed().as_secs_f64();
                    println!("pair_{i}_{j}\tINFEASIBLE\terror={e}\ttime={dt:.1}s");
                    results.push((i, j, 0.0, false));
                }
            }
        }
    }
    println!("---SUMMARY---");
    let feasible: Vec<_> = results.iter().filter(|r| r.3).collect();
    let infeasible: Vec<_> = results.iter().filter(|r| !r.3).collect();
    println!("Feasible pairs: {}", feasible.len());
    for r in &feasible {
        println!("  pair ({}, {}) -> UB {:.4}", r.0, r.1, r.2);
    }
    println!("Infeasible pairs: {}", infeasible.len());
    for r in &infeasible {
        println!("  pair ({}, {})", r.0, r.1);
    }
}
