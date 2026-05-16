// Hall-condition analysis on canonical E2 with vol-32 458 border.
//
// For each color k, count:
//   demand_k(side s) = # interior (cell, side) slots that MUST present
//     color k on side s in order for the adjacent fixed neighbor to match.
//   supply_k(side s) = # (interior_piece, rotation) pairs with color k
//     on side s.
//
// If any demand > supply, the configuration is infeasible.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::{
    is_perimeter_pos, perimeter_positions, strip_interior_except_hints,
};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, BORDER, PieceId, Position, Puzzle, Rotation};
use serde_json::Value;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let board_path = args.first().cloned()
        .unwrap_or_else(|| "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json".to_string());

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let hint_positions: Vec<Position> = hints.hints.iter().map(|h| h.position).collect();

    let board = load_board(&PathBuf::from(&board_path), &puzzle).expect("load board");
    let border_board = strip_interior_except_hints(&puzzle, &board, &hint_positions);

    let w = puzzle.width;
    let h = puzzle.height;
    let max_color = puzzle.color_count.saturating_sub(1) as u8;

    // For each (cell, side), is it a B-I demand slot? if yes, what color?
    // For each (cell, side) inside interior, what color is required from outside?
    // bi_demand[(cell, side)] = required_color
    let mut bi_demand: HashMap<(Position, u8), u8> = HashMap::new();
    for pos in perimeter_positions(&puzzle) {
        let (x, y) = puzzle.xy(pos);
        let Some((pid, rot)) = border_board.get(pos) else { continue; };
        let Some(p) = puzzle.piece(pid) else { continue; };
        let edges = p.edges.rotated(rot).as_array();
        // for each direction, if neighbor is interior, record demand
        if y > 0 {
            let n = (y - 1) * w + x;
            if !is_perimeter_pos(&puzzle, n) {
                bi_demand.insert((n, 2u8), edges[0]); // interior cell's bottom side = our top
            }
        }
        if x + 1 < w {
            let n = y * w + (x + 1);
            if !is_perimeter_pos(&puzzle, n) {
                bi_demand.insert((n, 3u8), edges[1]);
            }
        }
        if y + 1 < h {
            let n = (y + 1) * w + x;
            if !is_perimeter_pos(&puzzle, n) {
                bi_demand.insert((n, 0u8), edges[2]);
            }
        }
        if x > 0 {
            let n = y * w + (x - 1);
            if !is_perimeter_pos(&puzzle, n) {
                bi_demand.insert((n, 1u8), edges[3]);
            }
        }
    }

    // Hints also demand specific sides at hint cells. But the hint piece is fixed,
    // so it imposes its own colors on all 4 sides (used as demand at the OTHER side of each adjacency).
    // For now, let's just look at the border B-I demand.

    // Per-color, per-side demand (over interior cells that demand it).
    let mut demand_by_side_color: HashMap<(u8, u8), u32> = HashMap::new();
    for (&(_cell, side), &color) in &bi_demand {
        *demand_by_side_color.entry((side, color)).or_default() += 1;
    }

    // Supply: for each (color, side), count (piece, rotation) combos where piece
    // is an INTERIOR piece (i.e., currently has BORDER==0 on no side).
    // For each interior piece, for each of 4 rotations, check edge[side] for each side.
    let mut supply_by_side_color: HashMap<(u8, u8), u32> = HashMap::new();
    // Track which pieces are pinned (placed in border + hints). These cannot move.
    let mut pinned: std::collections::BTreeSet<PieceId> = std::collections::BTreeSet::new();
    for pos in 0..puzzle.cell_count() {
        if is_perimeter_pos(&puzzle, pos) || hint_positions.contains(&pos) {
            if let Some((pid, _)) = border_board.get(pos) {
                pinned.insert(pid);
            }
        }
    }

    for piece in puzzle.pieces() {
        if !piece.is_inner() { continue; }
        if pinned.contains(&piece.id) { continue; }
        for &r in &Rotation::ALL {
            let e = piece.edges.rotated(r).as_array();
            for s in 0u8..4 {
                if e[s as usize] != BORDER {
                    *supply_by_side_color.entry((s, e[s as usize])).or_default() += 1;
                }
            }
        }
    }

    println!("Hall-condition: B-I demand vs interior-piece supply (per (side, color))");
    println!("side\tcolor\tdemand\tsupply\tslack");
    let mut total_demand = 0u32;
    let mut any_violation = false;
    for s in 0u8..4 {
        for k in 1..=max_color {
            let d = *demand_by_side_color.get(&(s, k)).unwrap_or(&0);
            let sup = *supply_by_side_color.get(&(s, k)).unwrap_or(&0);
            if d > 0 || sup > 0 {
                let slack = sup as i64 - d as i64;
                let marker = if slack < 0 { " VIOLATION" } else { "" };
                if slack < 0 { any_violation = true; }
                println!("{s}\t{k}\t{d}\t{sup}\t{slack}{marker}");
                total_demand += d;
            }
        }
    }
    println!("---");
    println!("Total B-I demand slots: {total_demand}");
    println!("Any violation: {any_violation}");
}
