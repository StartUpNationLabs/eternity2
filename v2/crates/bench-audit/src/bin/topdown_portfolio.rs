// Vol-20 — top-down CP portfolio for N6 cross-scan-order backbone.
//
// All Blackwood-based CP profiles in our stack use RowMajorBottomUp,
// which produces boards with the bottom-left 4x4 universally agreed
// (algorithmic artefact). To get cross-scan-order backbone signal, run
// the SAME puzzle with a TOP-DOWN scan-order CP profile across several
// seeds. The cells where both bottom-up and top-down runs agree are
// real structural backbone.
//
// Uses `gacolor_ac3_par` (no Blackwood scan-order override, defaults
// to engine's historic RowMajorTopDown indexing).
//
// CLI:
//   topdown_portfolio --seeds 5 --budget-ms 60000
//
// Output: one JSON per seed in output/n6_topdown/.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn main() {
    let mut n_seeds: u64 = 5;
    let mut budget_ms: u64 = 60_000;
    let mut profile = String::from("gacolor_ac3_par");
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--seeds" => n_seeds = args.next().unwrap().parse().unwrap(),
            "--budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--profile" => profile = args.next().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let out_dir = PathBuf::from("output/n6_topdown");
    let _ = std::fs::create_dir_all(&out_dir);

    eprintln!(
        "topdown_portfolio: profile={profile} seeds={n_seeds} budget={budget_ms}ms hints={}",
        hints.hints.len()
    );

    for seed in 1..=n_seeds {
        let mut solver = match profile.as_str() {
            "gacolor_ac3_par" => EngineSolver::gacolor_ac3_par(),
            "gacolor_ac3_random_par" => EngineSolver::gacolor_ac3_random_par(),
            "joe_depth150_par" => EngineSolver::joe_depth150_par(),
            "border_first_full_par" => EngineSolver::border_first_full_par(),
            other => panic!("unknown profile {other}"),
        };
        let mut opts = SolveOpts::default();
        opts.time_budget_ms = budget_ms;
        opts.seed = seed;
        opts.hints = hints.clone();

        let log_path = out_dir.join(format!("seed_{seed}.log"));
        let mut sink = ProgressSink::new(&log_path, 5_000).expect("open log");
        let header = format!(
            "=== top-down CP seed {} ({} ms, profile={}) ===\n",
            seed, budget_ms, profile
        );
        sink.write_line(&header);
        eprintln!("seed={seed} starting ({budget_ms}ms)");

        let t0 = Instant::now();
        let outcome = solver.solve(&puzzle, &opts, &mut sink);
        let elapsed = t0.elapsed();

        let (matched_str, placed, board_opt, depth) = match outcome {
            SolveOutcome::Solved(b) => {
                let (m, _) = score_board(&puzzle, &b);
                let p = placed_count(&b, &puzzle);
                ("SOLVED".to_string(), p, Some(b), 0u32)
            }
            SolveOutcome::TimedOut { best_partial, best_depth } => {
                let (m, _) = score_board(&puzzle, &best_partial);
                let p = placed_count(&best_partial, &puzzle);
                (format!("TIMEOUT(matched={m})"), p, Some(best_partial), best_depth)
            }
            SolveOutcome::Cancelled { best_partial, best_depth, .. } => {
                let (m, _) = score_board(&puzzle, &best_partial);
                let p = placed_count(&best_partial, &puzzle);
                (format!("CANCELLED(matched={m})"), p, Some(best_partial), best_depth)
            }
            SolveOutcome::Exhausted => ("EXHAUSTED".to_string(), 0, None, 0),
            SolveOutcome::AllSolutions(bs) => (
                format!("ALL({} sols)", bs.len()),
                bs.first().map(|b| placed_count(b, &puzzle)).unwrap_or(0),
                bs.into_iter().next(),
                0,
            ),
            SolveOutcome::Error(e) => (format!("ERROR: {e}"), 0, None, 0),
        };

        if let Some(b) = board_opt.as_ref() {
            let (matched, _) = score_board(&puzzle, b);
            let url = bucas_url(&puzzle, b, "n6_topdown");
            eprintln!(
                "seed={seed} done in {:.1}s — {} placed={placed} matched={matched} depth={depth}",
                elapsed.as_secs_f64(), matched_str
            );
            let json = serde_json::json!({
                "seed": seed,
                "profile": profile,
                "elapsed_ms": elapsed.as_millis() as u64,
                "matched": matched,
                "placed": placed,
                "max_depth_seen": depth,
                "bucas_url": url,
                "placement": (0..puzzle.cell_count()).map(|p| {
                    b.get(p).map(|(pid, rot)| serde_json::json!({
                        "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                    }))
                }).collect::<Vec<_>>(),
            });
            let p = out_dir.join(format!("topdown_{profile}_seed{seed}.json"));
            let _ = std::fs::write(&p, serde_json::to_string_pretty(&json).unwrap());
            eprintln!("  saved: {}", p.display());
        }
    }
    eprintln!("topdown_portfolio: all seeds done.");
}
