// Run our SOTA pipeline on the official 16×16 Eternity II puzzle.
//
// Strategy:
//   1. CP search (`gacolor_ac3_par`) with hints honoured, time-bounded.
//   2. If CP didn't fully solve (almost certain), feed its best_partial
//      into local search (`eternity2-localsearch`) for further polish.
//   3. Report best edge-match score and the BUCAS URL of the placement.
//
// The published community record is 467/480 by Verhaard 2008. Our
// realistic v0 target is to put a number on the board honestly.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::{puzzle_name_from_path, write_report};
use eternity2_core::{Board, Puzzle, BORDER};
use eternity2_events::BufferSink;
use eternity2_localsearch::{run_sa_from, SaConfig};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

#[derive(Parser, Debug)]
#[command(name = "official_e2", about = "Run solver on official Eternity II puzzle")]
struct Args {
    /// Path to the official puzzle CSV.
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// CP phase wall-clock budget in seconds.
    #[arg(long, default_value_t = 120)]
    cp_seconds: u64,

    /// LS phase wall-clock budget in seconds. 0 to skip.
    #[arg(long, default_value_t = 120)]
    ls_seconds: u64,

    /// Seed for the LS phase PRNG.
    #[arg(long, default_value_t = 0xE2_E2_E2_E2)]
    seed: u64,

    /// Use hints from the puzzle file (default true).
    #[arg(long, default_value_t = true)]
    use_hints: bool,
}

fn score_board(puzzle: &Puzzle, board: &Board) -> (u32, u32) {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut matches = 0u32;
    let total = (w - 1) * h + w * (h - 1);
    let pieces = puzzle.pieces();
    let lookup = |id: eternity2_core::PieceId| -> Option<&eternity2_core::Piece> {
        pieces.iter().find(|p| p.id == id)
    };
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let Some(piece) = lookup(pid) else { continue; };
            let e = piece.edges.rotated(rot).as_array();
            // Right neighbour
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup(rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        if e[1] == re[3] && e[1] != BORDER && e[1] != 0 { matches += 1; }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup(bpid) {
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

fn main() {
    let args = Args::parse();
    eprintln!("=== OFFICIAL ETERNITY II EXPERIMENT ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("cp_budget: {}s   ls_budget: {}s   seed: 0x{:x}", args.cp_seconds, args.ls_seconds, args.seed);

    let (puzzle, hints) = load_puzzle_with_hints(&args.puzzle).expect("load puzzle");
    eprintln!(
        "loaded: size={}x{}, pieces={}, colors={}, hints={}",
        puzzle.width, puzzle.height, puzzle.pieces().len(), puzzle.color_count - 1, hints.hints.len()
    );
    for h in &hints.hints {
        let (x, y) = puzzle.xy(h.position);
        eprintln!("  hint: piece {} at ({},{}) rot {}", u32::from(h.piece_id), x, y, h.rotation.as_u8());
    }

    // -------- CP phase --------
    eprintln!();
    eprintln!("--- CP phase ({}s) ---", args.cp_seconds);
    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = args.cp_seconds * 1000;
    if args.use_hints {
        opts.hints = hints;
    }
    let t0 = Instant::now();
    let cp_outcome = solver.solve(&puzzle, &opts, &mut sink);
    let cp_elapsed = t0.elapsed();
    let cp_board: Board = match &cp_outcome {
        SolveOutcome::Solved(b) => b.clone(),
        SolveOutcome::TimedOut { best_partial, .. } => best_partial.clone(),
        SolveOutcome::Cancelled { best_partial, .. } => best_partial.clone(),
        SolveOutcome::Exhausted => Board::empty(&puzzle),
        SolveOutcome::AllSolutions(bs) => bs.first().cloned().unwrap_or_else(|| Board::empty(&puzzle)),
        SolveOutcome::Error(e) => { eprintln!("CP error: {e}"); Board::empty(&puzzle) }
    };
    let (cp_score, total) = score_board(&puzzle, &cp_board);
    let cp_placed = placed_count(&cp_board);
    eprintln!(
        "CP done in {:.2}s: outcome={:?}  pieces_placed={}/{}  edges={}/{} ({}%)",
        cp_elapsed.as_secs_f64(),
        std::mem::discriminant(&cp_outcome),
        cp_placed, puzzle.cell_count(),
        cp_score, total,
        if total > 0 { (cp_score * 100) / total } else { 0 },
    );

    let output_dir = std::path::PathBuf::from("output");
    let puzzle_name = puzzle_name_from_path(&args.puzzle);

    // -------- LS phase --------
    if args.ls_seconds == 0 {
        eprintln!("(LS phase skipped)");
        let extra = serde_json::json!({
            "cp": { "score": cp_score, "elapsed_s": cp_elapsed.as_secs_f64(), "budget_s": args.cp_seconds },
            "ls": null,
            "seed": args.seed,
        });
        match write_report(&output_dir, "official_e2", &puzzle, &puzzle_name, &cp_board, extra) {
            Ok(r) => { eprintln!("\nReport: {}", r.json_path.display()); eprintln!("Bucas:  {}", r.url); }
            Err(e) => eprintln!("warning: failed to write report: {e}"),
        }
        return;
    }
    eprintln!();
    eprintln!("--- LS phase ({}s, seeded from CP partial) ---", args.ls_seconds);
    let ls_cfg = SaConfig {
        time_budget_ms: args.ls_seconds * 1000,
        seed: args.seed,
        ..Default::default()
    };
    let t1 = Instant::now();
    let ls_out = run_sa_from(&puzzle, &cp_board, &ls_cfg);
    let ls_elapsed = t1.elapsed();
    eprintln!(
        "LS done in {:.2}s: iters={}  best_edges={}/{} ({}%)",
        ls_elapsed.as_secs_f64(),
        ls_out.iterations,
        ls_out.best_score, ls_out.total_edges,
        (ls_out.best_score * 100) / ls_out.total_edges,
    );

    eprintln!();
    eprintln!("=== SUMMARY ===");
    eprintln!("CP phase:  {}/{} edges ({}%)", cp_score, total, if total > 0 { (cp_score * 100) / total } else { 0 });
    eprintln!("LS phase:  {}/{} edges ({}%)", ls_out.best_score, ls_out.total_edges, (ls_out.best_score * 100) / ls_out.total_edges);

    let extra = serde_json::json!({
        "cp": { "score": cp_score, "elapsed_s": cp_elapsed.as_secs_f64(), "budget_s": args.cp_seconds },
        "ls": { "score": ls_out.best_score, "elapsed_s": ls_elapsed.as_secs_f64(), "iters": ls_out.iterations, "budget_s": args.ls_seconds },
        "seed": args.seed,
    });
    match write_report(&output_dir, "official_e2", &puzzle, &puzzle_name, &ls_out.best_board, extra) {
        Ok(r) => { eprintln!("\nReport: {}", r.json_path.display()); eprintln!("Bucas:  {}", r.url); }
        Err(e) => eprintln!("warning: failed to write report: {e}"),
    }
}
