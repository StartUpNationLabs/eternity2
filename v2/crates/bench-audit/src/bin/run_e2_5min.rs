// Vol-12 closeout — raw run on canonical Eternity II with the best v12
// combination: joe_depth150_par. 5-minute time budget.
//
// Vol-16 Cat-3 — migrated to the shared `bench_audit::{ProgressSink,
// score_board, render_board, placed_count}` helpers. Local duplicates
// dropped (was 260 lines, now ~100).

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, render_board, score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let log_path = PathBuf::from("output/v12_run/run_e2_5min.log");
    let board_path = PathBuf::from("output/v12_run/run_e2_5min_board.json");
    std::fs::create_dir_all("output/v12_run").expect("mkdir");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let mut sink = ProgressSink::new(&log_path, 5_000).expect("open log");
    let header = format!(
        "=== vol-12 raw run on canonical Eternity II ===\n\
         puzzle: {}\n\
         size: {}x{} colors={} hints={}\n\
         profile: joe_depth150_par (gacolor + AC-3 + NS-1 + depth-150 gate + multi-core)\n\
         budget: 300_000 ms (5 min)\n",
        puzzle_path.display(),
        puzzle.width,
        puzzle.height,
        puzzle.color_count - 1,
        hints.hints.len()
    );
    sink.write_line(&header);
    eprintln!("{header}");

    let mut solver = EngineSolver::joe_depth150_par();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = 300_000;
    opts.seed = 1;
    opts.hints = hints;

    let t0 = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();

    let final_stats = sink.final_stats.clone();

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

    let mut summary = String::new();
    summary.push_str("\n=== FINAL RESULT ===\n");
    summary.push_str(&format!("verdict: {verdict}\n"));
    summary.push_str(&format!("wall_clock: {:.2} s\n", elapsed.as_secs_f64()));
    if let Some(s) = final_stats.as_ref() {
        summary.push_str(&format!(
            "nodes: {}\nbacktracks: {}\npropagations: {}\ndomain_wipeouts: {}\nmax_depth_seen: {}\nsolutions_found: {}\nnodes_per_sec: {:.0}\n",
            s.nodes,
            s.backtracks,
            s.propagations,
            s.domain_wipeouts,
            s.max_depth_seen,
            s.solutions_found,
            s.nodes as f64 / elapsed.as_secs_f64().max(1e-6)
        ));
    }
    if let Some(b) = board.as_ref() {
        let (matched, total) = score_board(&puzzle, b);
        let placed = placed_count(b, &puzzle);
        let internal_total = 2 * puzzle.width * puzzle.height - puzzle.width - puzzle.height;
        summary.push_str(&format!(
            "pieces_placed: {}/{}\nedge_matches: {}/{} (counting only placed-placed joins)\ninternal_total_edges: {}\n",
            placed,
            puzzle.cell_count(),
            matched,
            total,
            internal_total
        ));
        summary.push_str("\nBoard (piece_id:rotation):\n");
        summary.push_str(&render_board(&puzzle, b));
        let stats_json = final_stats.as_ref().map(|s| serde_json::json!({
            "time_ms": s.time_ms,
            "nodes": s.nodes,
            "backtracks": s.backtracks,
            "propagations": s.propagations,
            "domain_wipeouts": s.domain_wipeouts,
            "current_depth": s.current_depth,
            "max_depth_seen": s.max_depth_seen,
            "solutions_found": s.solutions_found,
        }));
        let bucas = bucas_url(&puzzle, b, "vol12_5min");
        summary.push_str(&format!("\nbucas: {bucas}\n"));
        let json = serde_json::json!({
            "schema_version": 1,
            "verdict": verdict,
            "elapsed_s": elapsed.as_secs_f64(),
            "pieces_placed": placed,
            "edge_matches": matched,
            "edge_total": total,
            "internal_total_edges": internal_total,
            "bucas_url": bucas,
            "placement": (0..puzzle.cell_count()).map(|pos| {
                b.get(pos).map(|(pid, rot)| serde_json::json!({
                    "pos": pos,
                    "piece_id": u32::from(pid),
                    "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
            "final_stats": stats_json,
        });
        std::fs::write(&board_path, serde_json::to_string_pretty(&json).unwrap()).expect("write json");
    }
    sink.write_line(&summary);
    eprintln!("{summary}");
    eprintln!("log:   {}", log_path.display());
    eprintln!("board: {}", board_path.display());
}
