// Vol-60 T6 — test ISOLATED scheduled-relaxation (break_indexes_allowed only).
//
// Vol-15 tried full Blackwood (heuristic curve + break indexes) and hit
// depth-wall 80. Vol-60 isolates pruner #3 (break indexes) without the
// curve, to see if scheduled relaxations alone improve depth on canonical.
//
// Schedule: no-op exhaustion curve (target=0 everywhere) + McGavin's
// 10 specific break depths. Applied to BLACKWOOD_RAW profile.

use std::path::PathBuf;
use std::sync::Arc;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_events::BufferSink;
use eternity2_solver_engine::{BlackwoodSchedule, EngineSolver};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");

    let budget_ms: u64 = std::env::var("BUDGET_MS")
        .ok().and_then(|s| s.parse().ok()).unwrap_or(60_000);

    // McGavin's 10 break-depth indexes (per blackwood_decoded memory).
    // These are scan-order INDEXES (which in BLACKWOOD_RAW = bottom-up
    // row-major). Map them appropriately.
    let break_indexes_mcgavin: Vec<u32> = vec![197, 203, 210, 216, 221, 225, 229, 233, 236, 238];

    // No-op curve: target=0 for all depths (heuristic count never fails).
    let schedule = Arc::new(BlackwoodSchedule {
        heuristic_sides: vec![],
        exhaustion_targets: vec![(0, 0), (256, 0)],
        heuristic_pool_size: 0,
        max_heuristic_index: 0,  // disable curve at depth 0+
        break_indexes_allowed: break_indexes_mcgavin.clone(),
    });
    if let Err(e) = schedule.validate() {
        panic!("invalid schedule: {e}");
    }

    eprintln!("Vol-60 T6: BREAK_INDEXES_ONLY (no-curve)");
    eprintln!("  break_indexes_allowed: {:?}", break_indexes_mcgavin);
    eprintln!("  budget_ms: {}", budget_ms);

    let mut solver = EngineSolver::blackwood_raw(schedule);

    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = 1;
    opts.hints = hints;

    let mut sink = BufferSink::default();
    let t0 = std::time::Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();

    let (best_partial, best_depth) = match outcome {
        SolveOutcome::TimedOut { best_partial, best_depth } =>
            (Some(best_partial), best_depth),
        SolveOutcome::Cancelled { best_partial, best_depth, .. } =>
            (Some(best_partial), best_depth),
        SolveOutcome::Solved(b) => (Some(b), 256),
        _ => (None, 0),
    };

    eprintln!("Elapsed: {:.1}s", elapsed.as_secs_f64());
    // Extract stats from sink events
    use eternity2_events::EventBody;
    for ev in sink.events.iter().rev() {
        if let EventBody::TimedOut { final_stats, .. } | EventBody::Solved { final_stats, .. } | EventBody::Cancelled { final_stats, .. } | EventBody::Exhausted { final_stats, .. } = &ev.body {
            eprintln!("Stats: nodes={} backtracks={} wipeouts={} max_depth={}",
                final_stats.nodes, final_stats.backtracks, final_stats.domain_wipeouts, final_stats.max_depth_seen);
            break;
        }
    }
    eprintln!("Best depth: {}", best_depth);

    if let Some(b) = best_partial {
        let (matched, total) = eternity2_bench_audit::score_board_dense(&puzzle, &b);
        eprintln!("Best partial score: {}/{}", matched, total);
    }
}
