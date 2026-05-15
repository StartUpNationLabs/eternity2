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
use eternity2_solver_trait::{Objective, SolveOpts, SolveOutcome, Solver};
use eternity2_core::BORDER;

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

/// Local cell score: how many of `pos`'s 4 edges match its current
/// neighbors. Used to drop mismatch cells.
fn cell_local_score(puzzle: &Puzzle, board: &Board, pos: u32) -> u32 {
    let Some((pid, rot)) = board.get(pos) else { return 0; };
    let e = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
    let w = puzzle.width;
    let h = puzzle.height;
    let x = pos % w;
    let y = pos / w;
    let mut s = 0u32;
    for (dx, dy, our, theirs) in [(0i32, -1, 0, 2), (1, 0, 1, 3), (0, 1, 2, 0), (-1, 0, 3, 1)] {
        let nx = x as i32 + dx;
        let ny = y as i32 + dy;
        if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 { continue; }
        let npos = ny as u32 * w + nx as u32;
        if let Some((npid, nrot)) = board.get(npos) {
            let ne = puzzle.piece(npid).unwrap().edges.rotated(nrot).as_array();
            if e[our] != BORDER && ne[theirs] != BORDER && e[our] == ne[theirs] {
                s += 1;
            }
        }
    }
    s
}

/// Maximum possible local score for a cell (= number of interior-facing sides).
fn cell_max_score(puzzle: &Puzzle, pos: u32) -> u32 {
    let w = puzzle.width;
    let h = puzzle.height;
    let x = pos % w;
    let y = pos / w;
    let mut s = 0u32;
    if y > 0 { s += 1; }
    if x + 1 < w { s += 1; }
    if y + 1 < h { s += 1; }
    if x > 0 { s += 1; }
    s
}

/// Build hints from a board's placed cells, EXCLUDING canonical hint
/// positions AND mismatch cells (cells whose current local score is
/// below their max possible). The mismatch cells are dropped so CP
/// can re-search them. Optionally further drop `n_drop_extra` cells
/// adjacent to mismatch cells (halo expansion).
fn hints_from_board_with_drops(
    board: &Board,
    puzzle: &Puzzle,
    canonical: &Hints,
    n_drop_extra: usize,
) -> Hints {
    let canonical_positions: std::collections::BTreeSet<u32> =
        canonical.hints.iter().map(|h| h.position).collect();
    let w = puzzle.width;
    // First pass: identify the mismatch cells (local < max).
    let mismatch: std::collections::BTreeSet<u32> = (0..puzzle.cell_count())
        .filter(|p| !canonical_positions.contains(p))
        .filter(|&p| {
            let cur = cell_local_score(puzzle, board, p);
            let max = cell_max_score(puzzle, p);
            cur < max
        })
        .collect();
    // Optionally extend by 1-hop neighbors of mismatch cells.
    let mut to_drop = mismatch.clone();
    if n_drop_extra > 0 {
        // Score each non-mismatch cell by how many mismatch neighbors it has.
        let mut neighbor_count: std::collections::BTreeMap<u32, u32> = std::collections::BTreeMap::new();
        for &m in &mismatch {
            let x = m % w;
            let y = m / w;
            for (dx, dy) in [(0i32, -1), (1, 0), (0, 1), (-1, 0)] {
                let nx = x as i32 + dx;
                let ny = y as i32 + dy;
                if nx < 0 || ny < 0 || nx >= w as i32 || ny >= puzzle.height as i32 { continue; }
                let np = ny as u32 * w + nx as u32;
                if !to_drop.contains(&np) && !canonical_positions.contains(&np) {
                    *neighbor_count.entry(np).or_insert(0) += 1;
                }
            }
        }
        let mut by_neighbors: Vec<(u32, u32)> = neighbor_count.into_iter().collect();
        by_neighbors.sort_by_key(|(p, c)| (std::cmp::Reverse(*c), *p));
        for (p, _) in by_neighbors.into_iter().take(n_drop_extra) {
            to_drop.insert(p);
        }
    }
    eprintln!("  dropping {} cells ({} mismatch + {} halo)",
        to_drop.len(), mismatch.len(), to_drop.len() - mismatch.len());

    let placed: Vec<u32> = (0..puzzle.cell_count())
        .filter(|p| !canonical_positions.contains(p))
        .filter(|p| board.get(*p).is_some())
        .filter(|p| !to_drop.contains(p))
        .collect();
    let kept: std::collections::BTreeSet<u32> = placed.into_iter().collect();

    let mut hs: Vec<Hint> = canonical.hints.clone();
    let mut corners: Vec<Hint> = Vec::new();
    let mut edges: Vec<Hint> = Vec::new();
    let mut inner: Vec<Hint> = Vec::new();
    let w = puzzle.width;
    let h = puzzle.height;
    for pos in 0..puzzle.cell_count() {
        if canonical_positions.contains(&pos) { continue; }
        if !kept.contains(&pos) { continue; }
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

/// Build hints from a board's placed cells, EXCLUDING canonical hint
/// positions (which are already pinned).
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
    let mut node_budget: u64 = 0;
    let mut rounds: u32 = 5;
    let mut seed: u64 = 1;
    let mut out_dir = PathBuf::from("output/v23_prune_restart");
    let mut min_depth_growth: u32 = 5;
    let mut drop_k: usize = 30;
    // Vol-24 — round 1 stays FirstSolution (a deepening pass); rounds
    // 2+ default to MaxScore so the CP filler optimises matched-edge
    // count instead of taking the first valid completion. Flip with
    // `--no-max-score` to reproduce vol-23's behaviour for A/B runs.
    let mut max_score: bool = true;
    // Vol-24 — `--pin-all-from-start` skips the mismatch-cell drop on
    // round 1 when `--start` is provided, so a `--drop-k 0` run truly
    // pins everything in the start board. Lets us measure MaxScore CP
    // fill from a fixed partial (the vol-23 round-2 board) without the
    // confounding mismatch-drop step.
    let mut pin_all_from_start: bool = false;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--start" => start_board_path = Some(PathBuf::from(args.next().unwrap())),
            "--cp-budget-ms" => cp_budget_ms = args.next().unwrap().parse().unwrap(),
            // Vol-50 — Joe-style node-count cap per round. 0 = unlimited.
            "--node-budget" => node_budget = args.next().unwrap().parse().unwrap(),
            "--rounds" => rounds = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--out-dir" => out_dir = PathBuf::from(args.next().unwrap()),
            "--min-depth-growth" => min_depth_growth = args.next().unwrap().parse().unwrap(),
            "--drop-k" => drop_k = args.next().unwrap().parse().unwrap(),
            "--no-max-score" => max_score = false,
            "--max-score" => max_score = true,
            "--pin-all-from-start" => pin_all_from_start = true,
            other => panic!("unknown arg {other}"),
        }
    }
    let _ = std::fs::create_dir_all(&out_dir);

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, canonical_hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let canonical_count = canonical_hints.hints.len();
    eprintln!(
        "prune_restart: canonical_hints={canonical_count}, cp_budget={cp_budget_ms}ms, node_budget={node_budget}, rounds={rounds}, seed={seed}"
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
    // When --start is provided AND --drop-k > 0, round 1 pins all-but-the-
    // lowest-scoring `drop_k` cells, then CP fills those unpinned cells.
    let mut current_hints = if let Some(ref b) = initial_board {
        if pin_all_from_start {
            eprintln!("pinning ALL placed cells from start board ({} cells)",
                placed_count(b, &puzzle));
            hints_from_board(b, &puzzle, &canonical_hints)
        } else {
            eprintln!("dropping {drop_k} lowest-scoring cells from start board");
            hints_from_board_with_drops(b, &puzzle, &canonical_hints, drop_k)
        }
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
        opts.node_budget = node_budget;
        opts.seed = seed;
        opts.hints = current_hints.clone();
        let n_pinned = current_hints.hints.len();
        // Vol-23 engine change — batch mode pins all hints before
        // propagation so a DFS-derived hint set doesn't reject itself.
        // Enable whenever the hint set exceeds the canonical count
        // (i.e. any round 2+, or round 1 if started from a partial board).
        opts.batch_hint_application = n_pinned > canonical_count;
        // Vol-24 — MaxScore objective on filler rounds (anything beyond
        // canonical-only hints). On the cold-start round 1 we still
        // want FirstSolution behaviour: the goal there is to dig deep,
        // and FirstSolution lets the engine return as soon as it hits
        // a complete consistent placement. MaxScore on round 1 would
        // chew through the whole search space without improvement,
        // because no completion is reachable in the budget anyway.
        let use_max_score = max_score && n_pinned > canonical_count;
        opts.objective = if use_max_score { Some(Objective::MaxScore) } else { None };

        eprintln!("\n=== ROUND {round}: pinned={n_pinned} (canonical={canonical_count} + {} extra), objective={} ===",
            n_pinned - canonical_count,
            if use_max_score { "MaxScore" } else { "FirstSolution" });

        // Vol-23 — engine selection:
        // - Round 1 from canonical-only hints: joe_depth150_bp_par + v17a
        //   schedule (strongest cold-start CP).
        // - Otherwise (round 1 from partial, or any round 2+):
        //   gacolor_ac3_par WITHOUT schedule. The schedule is calibrated
        //   for the 5-hint cold-start trajectory; running it with 30+
        //   extra hints distorts the heuristic-count vs target check.
        //   gacolor_ac3 provides decent propagation without the schedule.
        let cold_start = round == 1 && n_pinned == canonical_count;
        // For heavily-pinned starts (e.g. 226/256 cells), gacolor's
        // incremental color-pool tracking triggers false-positive wipeouts.
        // Use the bare-bones border_first_lcv_par profile (just class_balance
        // + edge-color matching) for these.
        let heavily_pinned = n_pinned > 100;
        let mut solver: Box<EngineSolver> = if cold_start {
            Box::new(EngineSolver::joe_depth150_bp_par().with_blackwood_schedule(schedule.clone()))
        } else if heavily_pinned {
            Box::new(EngineSolver::border_first_lcv_par())
        } else {
            Box::new(EngineSolver::gacolor_ac3_par())
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
