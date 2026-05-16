// Vol-17 NOVEL — dedicated long-budget CP repair on the mismatch cluster.
//
// After ALNS produces a board with a 25-50 cell mismatch cluster, run a
// dedicated 60s+ CP-search on JUST the cluster (rest pinned as hints).
// With gacolor_ac3_par and 60s budget, CP can enumerate cluster
// completions far more thoroughly than the 1500ms cp_repair inside ALNS.
//
// CLI:
//   cluster_repair --board PATH --cp-budget-ms MS [--halo N] [--ops PRESET]
//
// --halo N: include N-cell halo around mismatches in the freed region.
// 0 = just mismatched cells, 1 = +4 neighbors, 2 = +12, etc.

#![forbid(unsafe_code)]

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Hint, Hints, Rotation};
use eternity2_localsearch::{
    find_mismatches, piece_swap_hillclimb, polish_rotations,
};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};
use eternity2_bench_audit::ProgressSink;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path) -> eternity2_core::Board {
    let puzzle_path = std::path::PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = eternity2_benchmark::loader::load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eternity2_export::load_board(path, &puzzle).expect("load_board")
}

fn main() {
    let mut board_path = PathBuf::new();
    let mut cp_budget_ms: u64 = 60_000;
    let mut halo: u32 = 1;
    let mut solver_kind = "gacolor_ac3_par".to_string();
    let mut seed: u64 = 1;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--cp-budget-ms" => cp_budget_ms = args.next().unwrap().parse().unwrap(),
            "--halo" => halo = args.next().unwrap().parse().unwrap(),
            "--solver" => solver_kind = args.next().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("--board required");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, canonical_hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let board = load_board(&board_path);
    let (m0, _) = score_board(&puzzle, &board);
    let p0 = placed_count(&board, &puzzle);
    eprintln!("loaded board: {p0} placed, {m0}/480 matched");

    // Find mismatched cells.
    let mismatches = find_mismatches(&puzzle, &board);
    let w = puzzle.width;
    let h = puzzle.height;
    let mut mismatch_cells: BTreeSet<u32> = BTreeSet::new();
    for m in &mismatches {
        mismatch_cells.insert(m.cell_a);
        mismatch_cells.insert(m.cell_b);
    }
    eprintln!("mismatches: {} edges, {} touched cells", mismatches.len(), mismatch_cells.len());

    // Expand with halo.
    let mut free: BTreeSet<u32> = mismatch_cells.clone();
    for _ in 0..halo {
        let snapshot: Vec<u32> = free.iter().copied().collect();
        for p in snapshot {
            let x = p % w; let y = p / w;
            if x + 1 < w { free.insert(p + 1); }
            if x > 0 { free.insert(p - 1); }
            if y + 1 < h { free.insert(p + w); }
            if y > 0 { free.insert(p - w); }
        }
    }
    // Canonical hints are NEVER freed.
    let canonical_pinned: BTreeSet<u32> = canonical_hints.hints.iter().map(|h| h.position).collect();
    for &c in &canonical_pinned {
        free.remove(&c);
    }
    eprintln!("free region size: {} cells (mismatch+halo, minus canonical hints)", free.len());

    // Build hint list = everything NOT free.
    let mut hints_vec: Vec<Hint> = Vec::new();
    for pos in 0..puzzle.cell_count() {
        if free.contains(&pos) { continue; }
        if let Some((pid, rot)) = board.get(pos) {
            hints_vec.push(Hint { position: pos, piece_id: pid, rotation: rot });
        }
    }
    let hints = Hints::new(hints_vec);
    eprintln!("hint count (pinned): {}", hints.hints.len());

    // Run CP on the free region.
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = cp_budget_ms;
    opts.seed = seed;
    opts.hints = hints;
    let mut solver: Box<EngineSolver> = match solver_kind.as_str() {
        "gacolor_ac3_par" => Box::new(EngineSolver::gacolor_ac3_par()),
        "joe_depth150_par" => Box::new(EngineSolver::joe_depth150_par()),
        "joe_depth150_bp_par" => Box::new(EngineSolver::joe_depth150_bp_par()),
        other => panic!("unknown --solver {other}"),
    };

    let log_dir = PathBuf::from("output/v17_cluster_repair");
    let _ = std::fs::create_dir_all(&log_dir);
    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let log_path = log_dir.join(format!("run_{run_id}.log"));
    let mut sink = ProgressSink::new(&log_path, 5_000).expect("log");
    eprintln!("CP repair: solver={solver_kind} budget={cp_budget_ms}ms log={}", log_path.display());

    let t0 = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();
    let new_board = match outcome {
        SolveOutcome::Solved(b)
        | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        SolveOutcome::Exhausted => {
            eprintln!("CP EXHAUSTED — no feasible completion within budget. Returning original.");
            board.clone()
        }
        SolveOutcome::Error(e) => {
            eprintln!("CP ERROR: {e}");
            board.clone()
        }
    };

    // Polish.
    let pinned_set: BTreeSet<u32> = canonical_pinned.clone();
    let (new_board, rg) = polish_rotations(&puzzle, &new_board, &pinned_set);
    let (new_board, sg) = piece_swap_hillclimb(&puzzle, &new_board, &pinned_set);

    let (m_new, _) = score_board(&puzzle, &new_board);
    let p_new = placed_count(&new_board, &puzzle);
    let url = bucas_url(&puzzle, &new_board, "v17_cluster_repair");
    eprintln!(
        "\nResult: matched={m_new}/480 (was {m0}, Δ={:+}) placed={p_new}/256 elapsed={:.1}s polish_rot=+{rg} polish_swap=+{sg}",
        m_new as i32 - m0 as i32, elapsed.as_secs_f64()
    );
    eprintln!("bucas: {url}");

    let json_path = log_dir.join(format!("board_{run_id}.json"));
    let json = serde_json::json!({
        "matched_in": m0, "matched_out": m_new, "delta": m_new as i32 - m0 as i32,
        "elapsed_s": elapsed.as_secs_f64(),
        "free_size": free.len(),
        "halo": halo,
        "solver_kind": solver_kind,
        "polish_rot_gain": rg, "polish_swap_gain": sg,
        "bucas_url": url,
        "placement": (0..puzzle.cell_count()).map(|p| {
            new_board.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    let _ = std::fs::write(&json_path, serde_json::to_string_pretty(&json).unwrap());
    eprintln!("saved: {}", json_path.display());
}
