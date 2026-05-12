// Vol-14 — 8x8 / 8-color generated puzzle benchmark.
//
// Generates an 8x8 puzzle with 8 interior colors via
// `eternity2_generator::generate`. Solves with the vol-14 stack
// (joe_depth150_par + edge-BP marginals would require regenerating
// BP for the new puzzle; instead use joe_depth150_par or the
// strongest non-BP profile). Reports wall-clock to first solution.
//
// Compares to v1-stack historical performance which (per user) had
// trouble with this puzzle size.
//
// CLI:
//   --seed <u64>          seed for puzzle generation (default 1)
//   --solve-budget-ms <ms> per-profile budget (default 60_000)
//   --profile <name>      one of: joe_par, joe_ns1_par, gacolor_ac3_par,
//                                  border_first_lcv_par, border_first_lcv (single-thread)
//   --all-profiles        run all configured profiles sequentially

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit as _;
use eternity2_core::Board;
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

struct QuietSink {
    depth: u32,
    final_stats: Option<FinalStats>,
}
impl QuietSink {
    fn new() -> Self { Self { depth: 0, final_stats: None } }
}
impl EventSink for QuietSink {
    fn emit(&mut self, event: SolverEvent) {
        if event.depth > self.depth { self.depth = event.depth; }
        match event.body {
            EventBody::Solved { final_stats, .. }
            | EventBody::Exhausted { final_stats, .. }
            | EventBody::TimedOut { final_stats, .. }
            | EventBody::Cancelled { final_stats, .. } => {
                self.final_stats = Some(final_stats);
            }
            _ => {}
        }
    }
}

fn score_board(puzzle: &eternity2_core::Puzzle, board: &Board) -> (u32, u32) {
    let (w, h) = (puzzle.width, puzzle.height);
    let total = (w - 1) * h + w * (h - 1);
    let mut matched = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let p = puzzle.piece(pid).unwrap();
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((npid, nrot)) = board.get(pos + 1) {
                    let np = puzzle.piece(npid).unwrap();
                    if e[1] == np.edges.rotated(nrot).as_array()[3] { matched += 1; }
                }
            }
            if y + 1 < h {
                if let Some((npid, nrot)) = board.get(pos + w) {
                    let np = puzzle.piece(npid).unwrap();
                    if e[2] == np.edges.rotated(nrot).as_array()[0] { matched += 1; }
                }
            }
        }
    }
    (matched, total)
}

fn placed_count(b: &Board, puzzle: &eternity2_core::Puzzle) -> u32 {
    (0..puzzle.cell_count()).filter(|&p| b.get(p).is_some()).count() as u32
}

fn run_profile(label: &str, solver: &mut EngineSolver,
               puzzle: &eternity2_core::Puzzle, budget_ms: u64, seed: u64)
{
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = seed;
    // No canonical hints for a generated puzzle.

    let mut sink = QuietSink::new();
    let t0 = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();

    let stats = sink.final_stats.unwrap_or(FinalStats::default());
    let (verdict, board) = match outcome {
        SolveOutcome::Solved(b) => ("SOLVED".to_string(), Some(b)),
        SolveOutcome::TimedOut { best_partial, best_depth } => {
            (format!("TIMEOUT (best_depth={best_depth})"), Some(best_partial))
        }
        SolveOutcome::Cancelled { best_partial, best_depth, .. } => {
            (format!("CANCELLED (best_depth={best_depth})"), Some(best_partial))
        }
        SolveOutcome::Exhausted => ("EXHAUSTED".to_string(), None),
        SolveOutcome::AllSolutions(bs) => (format!("ALL ({})", bs.len()), bs.into_iter().next()),
        SolveOutcome::Error(e) => (format!("ERROR: {e}"), None),
    };

    let (placed, matched, total) = if let Some(b) = board.as_ref() {
        let (m, t) = score_board(puzzle, b);
        (placed_count(b, puzzle), m, t)
    } else {
        (0, 0, (puzzle.width - 1) * puzzle.height + puzzle.width * (puzzle.height - 1))
    };
    let nps = stats.nodes as f64 / elapsed.as_secs_f64().max(1e-6);

    eprintln!("{label:>26}: {verdict:<28} elapsed={:.3}s  nodes={:>10}  nps={nps:>8.0}  depth={:>3}  placed={:>3}/{}  matched={matched:>3}/{total}",
        elapsed.as_secs_f64(), stats.nodes, stats.max_depth_seen, placed, puzzle.cell_count());
}

fn main() {
    let mut seed: u64 = 1;
    let mut budget_ms: u64 = 60_000;
    let mut all = false;
    let mut profile = "joe_par".to_string();
    let mut size: u32 = 8;
    let mut colors: u32 = 8;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--solve-budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--profile" => profile = args.next().unwrap(),
            "--all-profiles" => all = true,
            "--size" => size = args.next().unwrap().parse().unwrap(),
            "--colors" => colors = args.next().unwrap().parse().unwrap(),
            _ => eprintln!("(unrecognized: {a})"),
        }
    }

    let cfg = GeneratorConfig { size, interior_colors: colors, seed };
    let puzzle = generate(cfg).expect("generate");
    eprintln!("Generated puzzle: {}x{}, {} interior colors, seed={}",
        puzzle.width, puzzle.height, puzzle.color_count - 1, seed);
    let internal_total = (puzzle.width - 1) * puzzle.height + puzzle.width * (puzzle.height - 1);
    eprintln!("Total internal edges = {internal_total}");
    eprintln!("Budget per profile = {budget_ms} ms\n");

    if all {
        // Mix of single-thread and multi-core, with and without strong props.
        run_profile("border_first_lcv (1-thr)", &mut EngineSolver::border_first_lcv(), &puzzle, budget_ms, seed);
        run_profile("border_first_lcv_par",     &mut EngineSolver::border_first_lcv_par(), &puzzle, budget_ms, seed);
        run_profile("gacolor_ac3 (1-thr)",      &mut EngineSolver::gacolor_ac3(), &puzzle, budget_ms, seed);
        run_profile("gacolor_ac3_par",          &mut EngineSolver::gacolor_ac3_par(), &puzzle, budget_ms, seed);
        run_profile("gacolor_ac3_ns1_par",      &mut EngineSolver::gacolor_ac3_ns1_par(), &puzzle, budget_ms, seed);
        run_profile("joe_depth150_par",         &mut EngineSolver::joe_depth150_par(), &puzzle, budget_ms, seed);
    } else {
        let mut s = match profile.as_str() {
            "joe_par"               => EngineSolver::joe_depth150_par(),
            "joe_ns1_par"           => EngineSolver::gacolor_ac3_ns1_par(),
            "gacolor_ac3_par"       => EngineSolver::gacolor_ac3_par(),
            "border_first_lcv_par"  => EngineSolver::border_first_lcv_par(),
            "border_first_lcv"      => EngineSolver::border_first_lcv(),
            _ => panic!("unknown profile {profile}"),
        };
        run_profile(&profile, &mut s, &puzzle, budget_ms, seed);
    }
}
