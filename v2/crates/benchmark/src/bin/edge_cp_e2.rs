// Edge-CP experiment on the official Eternity II puzzle.
//
// Inversion 2 from RESEARCH_NOTES_3: 480 interior edges as the search
// variables (instead of 256 cells). Runs the new eternity2-edge-solver
// alongside the existing solver-engine for side-by-side comparison.
//
// Pipeline (v1):
//   1. Load the official 5-clue E2 puzzle.
//   2. Run edge-CP with a configurable time budget.
//   3. Recover a Board from the edge assignment via greedy alldiff.
//   4. Score the recovered board using the same metric as pt_e2 (matched
//      edges between adjacent placed pieces).
//
// Hints are not yet applied — pinning hint pieces requires translating
// each pinned (piece, rotation, position) into pinned edge-color values
// along that cell's 4 sides. v1.1 work.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::{puzzle_name_from_path, write_report};
use eternity2_core::{Board, Piece, PieceId, Puzzle, BORDER};
use eternity2_edge_solver::{recover, Search, SearchConfig, Tables, Topology};

#[derive(Parser, Debug)]
#[command(name = "edge_cp_e2", about = "Edge-as-variable CP on Eternity II")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long, default_value_t = 60)]
    seconds: u64,

    /// Enable the (currently unsound) single-cell piece-uniqueness propagator.
    /// Off by default — see Inversion 2 design notes.
    #[arg(long, default_value_t = false)]
    propagate_alldiff: bool,
}

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.pieces().iter().find(|p| p.id == id)
}

fn score_board(puzzle: &Puzzle, board: &Board) -> (u32, u32) {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut matches = 0u32;
    let total = (w - 1) * h + w * (h - 1);
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let Some(piece) = lookup_piece(puzzle, pid) else { continue; };
            let e = piece.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup_piece(puzzle, rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        if e[1] == re[3] && e[1] != BORDER && e[1] != 0 { matches += 1; }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        if e[2] == be[0] && e[2] != BORDER && e[2] != 0 { matches += 1; }
                    }
                }
            }
        }
    }
    (matches, total)
}

fn placed_count(board: &Board) -> u32 {
    board.cells().iter().filter(|c| c.is_some()).count() as u32
}

fn pct(num: u32, denom: u32) -> f64 {
    if denom == 0 { 0.0 } else { 100.0 * (num as f64) / (denom as f64) }
}

fn main() {
    let args = Args::parse();
    eprintln!("=== EDGE-CP (Inversion 2) ON ETERNITY II ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("seconds={} propagate_alldiff={}", args.seconds, args.propagate_alldiff);

    let (puzzle, file_hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    eprintln!("loaded {}×{}, {} pieces, {} colors, {} hints",
        puzzle.width, puzzle.height, puzzle.pieces().len(),
        puzzle.color_count - 1, file_hints.hints.len());

    let topology = Topology::new(&puzzle);
    let tables = Tables::new(&puzzle, &topology);
    eprintln!("topology: n_edges={} n_cells={} n_rows={}",
        topology.n_edges, topology.n_cells, tables.n_rows);

    let mut cfg = SearchConfig::default();
    cfg.time_budget_ms = args.seconds * 1000;
    cfg.propagate_piece_uniqueness = args.propagate_alldiff;
    cfg.stop_on_first = true;

    let start = Instant::now();
    let mut search = Search::new(&puzzle, &topology, &tables, cfg);
    search.started_us = 0;
    let clock = || start.elapsed().as_micros() as u64;
    let result = search.recurse(&clock);
    let elapsed = start.elapsed();

    eprintln!("\n--- edge-CP result ---");
    eprintln!("outcome: {:?}", result);
    eprintln!("best edge-score: {}/{}", search.best_score, topology.n_edges);
    eprintln!("nodes={} backtracks={} propagations={} piece_commits={}",
        search.stats.nodes, search.stats.backtracks,
        search.stats.propagations, search.stats.piece_commits);
    eprintln!("elapsed: {:.1}s", elapsed.as_secs_f64());

    let (board, rstats) = recover::recover_board_with_stats(&puzzle, &topology, &tables, &search.best_edge_color);
    let placed = placed_count(&board);
    let (matched, total) = score_board(&puzzle, &board);
    eprintln!("\n--- recovered board ---");
    eprintln!("placed: {}/{} cells ({:.1}%)", placed, puzzle.cell_count(), pct(placed, puzzle.cell_count()));
    eprintln!("matched edges: {}/{} ({:.1}%)", matched, total, pct(matched, total));
    eprintln!("recovery diagnostics:");
    eprintln!("  cells fully determined: {}/{}", rstats.cells_fully_determined, puzzle.cell_count());
    eprintln!("  cells with ≥1 piece candidate: {}", rstats.cells_with_any_candidates);
    eprintln!("  cells with 0 candidates (unrealizable 4-tuple): {}", rstats.cells_with_zero_candidates);
    if rstats.cells_with_any_candidates > 0 {
        let mean_cand = (rstats.total_candidate_count as f64) / (rstats.cells_with_any_candidates as f64);
        eprintln!("  mean candidates / cell: {mean_cand:.2}  max: {}", rstats.max_candidate_count);
    }
    eprintln!("  cells placed by matching: {}", rstats.cells_placed);

    eprintln!("\n=== SUMMARY ===");
    eprintln!("edge-CP best edge-score (search): {}/{}", search.best_score, topology.n_edges);
    eprintln!("recovered board score: {}/{} matched edges, {}/{} cells placed",
        matched, total, placed, puzzle.cell_count());
    eprintln!("(cell-CP baseline on this puzzle: 449-450/480)");

    let output_dir = std::path::PathBuf::from("output");
    let puzzle_name = puzzle_name_from_path(&args.puzzle);
    let extra = serde_json::json!({
        "edge_cp": {
            "edge_score": search.best_score,
            "n_edges": topology.n_edges,
            "elapsed_s": elapsed.as_secs_f64(),
            "budget_s": args.seconds,
            "nodes": search.stats.nodes,
            "backtracks": search.stats.backtracks,
            "propagations": search.stats.propagations,
            "piece_commits": search.stats.piece_commits,
            "outcome": format!("{:?}", result),
            "propagate_alldiff": args.propagate_alldiff,
        },
        "recovered": {
            "matched_edges": matched,
            "total_edges": total,
            "placed_cells": placed,
            "total_cells": puzzle.cell_count(),
        },
    });
    match write_report(&output_dir, "edge_cp_e2", &puzzle, &puzzle_name, &board, extra) {
        Ok(r) => {
            eprintln!("\nReport: {}", r.json_path.display());
            eprintln!("Bucas:  {}", r.url);
        }
        Err(e) => eprintln!("warning: failed to write report: {e}"),
    }
}
