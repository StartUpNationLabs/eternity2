// Vol-23 T1 — McGavin-style prune-restart driver.
//
// Vault concept: prune-restart (unbuilt since vol-14, 8 vols deferred).
//
// Algorithm:
//   1. Run Blackwood CP for time-budget T1 from the canonical hints.
//   2. Capture the best partial placement at its max-depth.
//   3. Convert all NEW placements (cells beyond canonical hints) into
//      additional hints.
//   4. Re-run Blackwood CP with the COMBINED hints (canonical + new).
//      The second run's AC-3/gacolor/multiset-equality propagators see
//      a richer initial state → tighter domains → potentially finds
//      a deeper / higher-score placement.
//   5. Iterate up to N rounds, stopping when no progress or when a
//      round finds 480 (solution).
//
// The key trick is exactly what McGavin/Joe describe: instead of
// backtracking past the depth wall, treat the partial as locked and
// re-prune with the locked pieces as constraint sources.
//
// CLI:
//   prune_restart [--start <board.json>] [--cp-budget-ms 60000]
//                 [--rounds 5] [--seed 1] [--engine joe_depth150_bp_par]
//                 [--out-dir output/v23_prune_restart]
//
// Output: one JSON per round + a summary CSV showing
//   round, depth_attained, score, n_pinned.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Hint, Hints, Puzzle, Rotation};
use eternity2_solver_engine::{
    blackwood_schedule_calibrated_v17a, EngineSolver,
};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn load_board(path: &std::path::Path, puzzle: &Puzzle) -> Board {
    let raw = std::fs::read_to_string(path).expect("read");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let mut b = Board::empty(puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for p in arr {
            if p.is_null() { continue; }
            let pos = p["pos"].as_u64().unwrap() as u32;
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot = Rotation::from_u8(p["rotation"].as_u64().unwrap() as u8).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

/// Build hints from a board's placed cells, EXCLUDING canonical hint
/// positions (which are already pinned).
///
/// Hints are emitted in BORDER-FIRST order (corners → edges → interior)
/// to match the engine's BORDER_FIRST_LCV variable ordering. Within
/// each tier, sort by position. This minimises mid-apply propagation
/// from removing options needed by later hints.
fn hints_from_board(board: &Board, puzzle: &Puzzle, canonical: &Hints) -> Hints {
    let canonical_positions: std::collections::BTreeSet<u32> =
        canonical.hints.iter().map(|h| h.position).collect();
    let mut hs: Vec<Hint> = canonical.hints.clone();
    let mut corners: Vec<Hint> = Vec::new();
    let mut edges: Vec<Hint> = Vec::new();
    let mut inner: Vec<Hint> = Vec::new();
    let w = puzzle.width;
    let h = puzzle.height;
    for pos in 0..puzzle.cell_count() {
        if canonical_positions.contains(&pos) { continue; }
        let Some((pid, rot)) = board.get(pos) else { continue; };
        let hint = Hint { position: pos, piece_id: pid, rotation: rot };
        let x = pos % w;
        let y = pos / w;
        let n_border = (if x == 0 {1} else {0}) + (if x == w - 1 {1} else {0})
            + (if y == 0 {1} else {0}) + (if y == h - 1 {1} else {0});
        match n_border {
            2 => corners.push(hint),
            1 => edges.push(hint),
            _ => inner.push(hint),
        }
    }
    corners.sort_by_key(|h| h.position);
    edges.sort_by_key(|h| h.position);
    inner.sort_by_key(|h| h.position);
    hs.extend(corners);
    hs.extend(edges);
    hs.extend(inner);
    Hints::new(hs)
}

fn save_board(path: &std::path::Path, puzzle: &Puzzle, board: &Board, score: u32, round: u32, n_pinned: usize) {
    let json = serde_json::json!({
        "round": round,
        "matched": score,
        "n_pinned": n_pinned,
        "placement": (0..puzzle.cell_count()).map(|p| {
            board.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    std::fs::write(path, serde_json::to_string_pretty(&json).unwrap()).expect("write");
}

fn main() {
    let mut start_board_path: Option<PathBuf> = None;
    let mut cp_budget_ms: u64 = 60_000;
    let mut rounds: u32 = 5;
    let mut seed: u64 = 1;
    let mut out_dir = PathBuf::from("output/v23_prune_restart");
    let mut min_depth_growth: u32 = 5;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--start" => start_board_path = Some(PathBuf::from(args.next().unwrap())),
            "--cp-budget-ms" => cp_budget_ms = args.next().unwrap().parse().unwrap(),
            "--rounds" => rounds = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--out-dir" => out_dir = PathBuf::from(args.next().unwrap()),
            "--min-depth-growth" => min_depth_growth = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    let _ = std::fs::create_dir_all(&out_dir);

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, canonical_hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let canonical_count = canonical_hints.hints.len();
    eprintln!(
        "prune_restart: canonical_hints={canonical_count}, cp_budget={cp_budget_ms}ms, rounds={rounds}, seed={seed}"
    );

    // Build the v17a Blackwood schedule once and reuse across rounds.
    let schedule = match blackwood_schedule_calibrated_v17a(&puzzle, &canonical_hints) {
        Some(s) => Arc::new(s),
        None => {
            eprintln!("FATAL: could not build v17a schedule (need >= 3 heuristic colors)");
            std::process::exit(1);
        }
    };
    eprintln!("schedule built (max_index={})", schedule.max_heuristic_index);

    // The "current best" board + its hints set (canonical at round 0, growing each round).
    let initial_board = if let Some(p) = start_board_path.as_ref() {
        let b = load_board(p, &puzzle);
        let (s, _) = score_board(&puzzle, &b);
        eprintln!("loaded start board: score={s}/480, placed={}/{}",
            placed_count(&b, &puzzle), puzzle.cell_count());
        Some(b)
    } else {
        None
    };

    // Use the initial board's placements as the seed hint set (round 1's inputs).
    // If no start board, round 1 just runs from canonical hints.
    let mut current_hints = if let Some(ref b) = initial_board {
        hints_from_board(b, &puzzle, &canonical_hints)
    } else {
        canonical_hints.clone()
    };
    let mut best_score: u32 = initial_board.as_ref()
        .map(|b| score_board(&puzzle, b).0)
        .unwrap_or(0);
    let mut best_depth: u32 = 0;

    eprintln!("\n=== prune-restart loop ===");
    let mut summary: Vec<String> = vec!["round,n_pinned,depth,score,time_s".to_string()];

    for round in 1..=rounds {
        let mut opts = SolveOpts::default();
        opts.time_budget_ms = cp_budget_ms;
        opts.seed = seed;
        opts.hints = current_hints.clone();

        let n_pinned = current_hints.hints.len();
        eprintln!("\n=== ROUND {round}: pinned={n_pinned} (canonical={canonical_count} + {} extra) ===",
            n_pinned - canonical_count);

        // Round 1: rich propagators (joe_depth150_bp_par) for the initial CP.
        // Rounds 2+: border_first_lcv — bare minimum propagation. The point
        // of prune-restart is the RE-PROPAGATION with hints fixed; we let the
        // engine's standard propagation chain (edge-color matching, piece
        // uniqueness) re-run from a richer state. Heavier propagators
        // (gacolor, multiset_equality) over-prune when many hints are pinned.
        let mut solver: Box<EngineSolver> = if round == 1 {
            Box::new(EngineSolver::joe_depth150_bp_par().with_blackwood_schedule(schedule.clone()))
        } else {
            Box::new(EngineSolver::border_first_lcv_par())
        };
        let log_path = out_dir.join(format!("round_{round}.log"));
        let mut sink = ProgressSink::new(&log_path, 5_000).expect("open log");
        sink.write_line(&format!(
            "=== prune_restart round {round}, pinned={n_pinned}, seed={seed} ==="
        ));
        let t0 = Instant::now();
        let outcome = solver.solve(&puzzle, &opts, &mut sink);
        let elapsed = t0.elapsed();
        let stats = sink.final_stats.clone();

        let cp_board: Board = match outcome {
            SolveOutcome::Solved(b) => b,
            SolveOutcome::TimedOut { best_partial, .. } => best_partial,
            SolveOutcome::Cancelled { best_partial, .. } => best_partial,
            SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
            SolveOutcome::Error(e) => {
                eprintln!("  ENGINE ERROR (hints rejected?): {e}");
                Board::empty(&puzzle)
            }
            SolveOutcome::Exhausted => {
                eprintln!("  EXHAUSTED — no extension of hints found in budget");
                Board::empty(&puzzle)
            }
        };
        let (score, _) = score_board(&puzzle, &cp_board);
        let n_placed = placed_count(&cp_board, &puzzle);
        let depth = stats.as_ref().map(|s| s.max_depth_seen).unwrap_or(sink.best_depth);
        let nodes = stats.as_ref().map(|s| s.nodes).unwrap_or(0);

        eprintln!(
            "ROUND {round}: depth={depth}, placed={n_placed}/{}, score={score}/480, nodes={nodes}, elapsed={:.1}s",
            puzzle.cell_count(), elapsed.as_secs_f64()
        );

        let board_path = out_dir.join(format!("round_{round}_board.json"));
        save_board(&board_path, &puzzle, &cp_board, score, round, n_pinned);
        eprintln!("  saved {}", board_path.display());

        summary.push(format!(
            "{round},{n_pinned},{depth},{score},{:.1}",
            elapsed.as_secs_f64()
        ));

        // Decide whether to proceed.
        if score > best_score {
            eprintln!("  ** ROUND IMPROVED: score {} -> {} (Δ +{})", best_score, score, score - best_score);
            best_score = score;
            best_depth = depth;
            // Update hints for next round: pin everything currently placed.
            current_hints = hints_from_board(&cp_board, &puzzle, &canonical_hints);
        } else if depth > best_depth + min_depth_growth {
            // No score improvement but the CP went deeper — still useful;
            // pin its placements for the next round.
            eprintln!("  depth grew {}→{} (no score lift); still pinning for next round", best_depth, depth);
            best_depth = depth;
            current_hints = hints_from_board(&cp_board, &puzzle, &canonical_hints);
        } else {
            eprintln!("  STAGNATED (no score lift, depth growth < {}); stopping early", min_depth_growth);
            break;
        }
    }

    let summary_path = out_dir.join("summary.csv");
    let _ = std::fs::write(&summary_path, summary.join("\n"));
    eprintln!("\n=== Final ===");
    eprintln!("best score: {best_score}/480 across {} rounds", rounds);
    eprintln!("summary: {}", summary_path.display());
}
