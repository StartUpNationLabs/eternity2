// Parallel-Tempering experiment on the official Eternity II puzzle.
//
// Pipeline: CP phase produces a partial; PT polishes with N replicas at
// a geometric temperature ladder, with replica-exchange every K SA steps.
// Reports CP-only, PT (CP-seeded), and single-T SA (CP-seeded) for
// apples-to-apples comparison.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Hints, Piece, PieceId, Puzzle, BORDER};
use eternity2_events::BufferSink;
use eternity2_localsearch::{run_pt_from, run_sa_from, PtConfig, SaConfig};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

#[derive(Parser, Debug)]
#[command(name = "pt_e2", about = "Parallel Tempering on Eternity II")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// CP phase budget (seconds).
    #[arg(long, default_value_t = 60)]
    cp_seconds: u64,

    /// PT total wall-clock budget (seconds).
    #[arg(long, default_value_t = 240)]
    pt_seconds: u64,

    /// Number of parallel replicas (also the number of cores used).
    #[arg(long, default_value_t = 8)]
    n_replicas: usize,

    /// Inner iters per replica per round.
    #[arg(long, default_value_t = 100_000)]
    inner_iters: u64,

    /// Min temperature.
    #[arg(long, default_value_t = 0.05)]
    t_min: f64,

    /// Max temperature.
    #[arg(long, default_value_t = 2.0)]
    t_max: f64,

    /// Seed.
    #[arg(long, default_value_t = 0xE2_E2_E2_E2)]
    seed: u64,

    /// Skip the single-T SA comparison run.
    #[arg(long, default_value_t = false)]
    skip_sa_compare: bool,
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

fn pct(num: u32, denom: u32) -> f64 { 100.0 * (num as f64) / (denom as f64) }

fn main() {
    let args = Args::parse();
    eprintln!("=== PT (Parallel Tempering) ON ETERNITY II ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("cp_seconds={} pt_seconds={} replicas={} inner_iters={} t=[{:.2}..{:.2}] seed=0x{:x}",
        args.cp_seconds, args.pt_seconds, args.n_replicas, args.inner_iters,
        args.t_min, args.t_max, args.seed);

    let (puzzle, file_hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    eprintln!("loaded {}×{}, {} pieces, {} colors, {} hints",
        puzzle.width, puzzle.height, puzzle.pieces().len(),
        puzzle.color_count - 1, file_hints.hints.len());

    // ----- CP phase -----
    eprintln!("\n--- CP phase ({}s) ---", args.cp_seconds);
    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = args.cp_seconds * 1000;
    opts.hints = file_hints.clone();
    let t0 = Instant::now();
    let cp_out = solver.solve(&puzzle, &opts, &mut sink);
    let cp_elapsed = t0.elapsed();
    let cp_board: Board = match cp_out {
        SolveOutcome::Solved(b) | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        SolveOutcome::Exhausted => Board::empty(&puzzle),
        SolveOutcome::Error(e) => { eprintln!("CP err: {e}"); Board::empty(&puzzle) }
    };
    let (cp_score, total) = score_board(&puzzle, &cp_board);
    eprintln!("CP done in {:.1}s: placed={}/{}, edges={}/{} ({:.1}%)",
        cp_elapsed.as_secs_f64(), placed_count(&cp_board),
        puzzle.cell_count(), cp_score, total, pct(cp_score, total));

    // ----- PT phase -----
    eprintln!("\n--- PT phase ({}s, {} replicas) ---", args.pt_seconds, args.n_replicas);
    let pt_cfg = PtConfig {
        n_replicas: args.n_replicas,
        t_min: args.t_min,
        t_max: args.t_max,
        inner_iters: args.inner_iters,
        max_rounds: 0,
        time_budget_ms: args.pt_seconds * 1000,
        seed: args.seed,
        verbose: true,
        greedy_fill: true,
        diversify_fill: false,
    };
    let t1 = Instant::now();
    let (pt_out, pt_stats) = run_pt_from(&puzzle, &cp_board, &pt_cfg);
    let pt_elapsed = t1.elapsed();
    let swap_rate = if pt_stats.total_swap_proposals > 0 {
        100.0 * (pt_stats.total_swap_accepts as f64) / (pt_stats.total_swap_proposals as f64)
    } else { 0.0 };
    eprintln!("PT done in {:.1}s: rounds={} best={}/{} ({:.1}%) swap_accept_rate={:.1}%",
        pt_elapsed.as_secs_f64(), pt_stats.rounds,
        pt_out.best_score, pt_out.total_edges, pct(pt_out.best_score, pt_out.total_edges),
        swap_rate);
    eprintln!("per-pair swap accepts: {:?}", pt_stats.pair_accepts);
    eprintln!("per-pair swap proposals: {:?}", pt_stats.pair_proposals);
    let pair_rates: Vec<String> = pt_stats.pair_accepts.iter().zip(pt_stats.pair_proposals.iter())
        .map(|(a, p)| if *p == 0 { "—".to_string() } else { format!("{:.0}%", 100.0 * (*a as f64) / (*p as f64)) })
        .collect();
    eprintln!("per-pair accept rates: {:?}", pair_rates);
    eprintln!("final replica scores: {:?}", pt_stats.final_scores);

    // ----- Single-T SA control -----
    if !args.skip_sa_compare {
        eprintln!("\n--- Single-T SA control ({}s, same wall-clock) ---", args.pt_seconds);
        let sa_cfg = SaConfig {
            time_budget_ms: args.pt_seconds * 1000,
            seed: args.seed,
            ..Default::default()
        };
        let t2 = Instant::now();
        let sa_out = run_sa_from(&puzzle, &cp_board, &sa_cfg);
        let sa_elapsed = t2.elapsed();
        eprintln!("Single-T SA done in {:.1}s: iters={} best={}/{} ({:.1}%)",
            sa_elapsed.as_secs_f64(), sa_out.iterations,
            sa_out.best_score, sa_out.total_edges,
            pct(sa_out.best_score, sa_out.total_edges));
    }

    eprintln!("\n=== SUMMARY ===");
    eprintln!("CP:        {}/{} ({:.1}%)", cp_score, total, pct(cp_score, total));
    eprintln!("PT:        {}/{} ({:.1}%)", pt_out.best_score, total, pct(pt_out.best_score, total));
    eprintln!("Community: 467/480 (97.3%)");
    let _ = (file_hints, Hints::default());
}
