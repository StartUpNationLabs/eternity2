// Vol-122 A1 — CSP-fill from a sparse border partial.
//
// Loads a board with N placed cells (e.g., the 60-cell border partials from
// vol-122 INVENTION 3 / inv3_border_to_partial.py). Treats all placed cells
// as hints, runs the engine to fill the remaining cells.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Hint, Hints};
use eternity2_export::{load_board, save_board, BoardMetadata};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn main() {
    let mut board_path = PathBuf::new();
    let mut budget_ms: u64 = 60_000;
    let mut solver_kind = "gacolor_ac3_par".to_string();
    let mut seed: u64 = 1;
    let mut out_path: Option<PathBuf> = None;
    let mut random_fill = false;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--solver" => solver_kind = args.next().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--out" => out_path = Some(PathBuf::from(args.next().unwrap())),
            "--random-fill-remaining" => random_fill = true,
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("--board PATH required");
        std::process::exit(1);
    }

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _canonical_hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let board = load_board(&board_path, &puzzle).expect("load_board");

    let placed_initial = placed_count(&board, &puzzle);
    let (matched_initial, _) = score_board(&puzzle, &board);
    eprintln!(
        "loaded board: {} placed, {} matched edges",
        placed_initial, matched_initial
    );

    let mut hints_vec: Vec<Hint> = Vec::new();
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, rot)) = board.get(pos) {
            hints_vec.push(Hint {
                position: pos,
                piece_id: pid,
                rotation: rot,
            });
        }
    }
    let hints = Hints::new(hints_vec);
    eprintln!("CSP starting hint count: {}", hints.hints.len());

    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = seed;
    opts.hints = hints;
    opts.batch_hint_application = true;

    let mut solver: Box<EngineSolver> = match solver_kind.as_str() {
        "gacolor_ac3_par" => Box::new(EngineSolver::gacolor_ac3_par()),
        "joe_depth150_par" => Box::new(EngineSolver::joe_depth150_par()),
        "joe_depth150_bp_par" => Box::new(EngineSolver::joe_depth150_bp_par()),
        other => panic!("unknown --solver {other}; try gacolor_ac3_par / joe_depth150_par / joe_depth150_bp_par"),
    };

    let log_dir = PathBuf::from("output/vol-122/csp_fill");
    let _ = std::fs::create_dir_all(&log_dir);
    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let log_path = log_dir.join(format!("run_{run_id}.log"));
    let mut sink = ProgressSink::new(&log_path, 5_000).expect("log");
    eprintln!(
        "CSP fill: solver={solver_kind} budget={budget_ms}ms log={}",
        log_path.display()
    );

    let t0 = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();

    let new_board: Board = match outcome {
        SolveOutcome::Solved(b)
        | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        SolveOutcome::Exhausted => {
            eprintln!("CSP EXHAUSTED — returning original board");
            board.clone()
        }
        SolveOutcome::Error(e) => {
            eprintln!("CSP ERROR: {e}");
            board.clone()
        }
    };

    let placed_final = placed_count(&new_board, &puzzle);

    // Optional random fill of empty cells using unused pieces (random rotation).
    let mut new_board = new_board;
    if random_fill && placed_final < puzzle.cell_count() {
        use eternity2_core::Rotation;
        let used_pids: std::collections::BTreeSet<u16> = (0..puzzle.cell_count())
            .filter_map(|p| new_board.get(p).map(|(pid, _)| pid as u16))
            .collect();
        let mut remaining: Vec<u16> = (0..puzzle.pieces().len() as u16)
            .filter(|p| !used_pids.contains(p))
            .collect();
        let empty: Vec<u32> = (0..puzzle.cell_count())
            .filter(|p| new_board.get(*p).is_none())
            .collect();
        // Fisher-Yates shuffle of remaining using a simple seeded PRNG.
        let mut prng = seed.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut next_u32 = || {
            prng ^= prng << 13;
            prng ^= prng >> 7;
            prng ^= prng << 17;
            (prng & 0xFFFF_FFFF) as u32
        };
        for i in (1..remaining.len()).rev() {
            let j = (next_u32() as usize) % (i + 1);
            remaining.swap(i, j);
        }
        let n_to_fill = empty.len().min(remaining.len());
        for i in 0..n_to_fill {
            let pos = empty[i];
            let pid = remaining[i];
            let rot_idx = (next_u32() as u8) & 0b11;
            let rot = Rotation::from_u8(rot_idx).unwrap();
            let _ = new_board.place(pos, pid, rot);
        }
        eprintln!("random-fill: placed {} more cells", n_to_fill);
    }
    let placed_final = placed_count(&new_board, &puzzle);
    let (matched_final, _) = score_board(&puzzle, &new_board);
    eprintln!(
        "\nCSP fill done. placed: {} -> {} (+{}). matched: {} -> {} (+{}). elapsed: {:.1}s",
        placed_initial,
        placed_final,
        placed_final as i64 - placed_initial as i64,
        matched_initial,
        matched_final,
        matched_final as i64 - matched_initial as i64,
        elapsed.as_secs_f64()
    );

    if let Some(out) = out_path {
        let meta = BoardMetadata {
            source: Some(format!("border_to_csp_fill_{solver_kind}_s{seed}")),
            seed: Some(seed),
            elapsed_ms: Some(elapsed.as_millis() as u64),
            note: Some(format!(
                "started from {} ({} placed, {} matched); CSP-filled to {} placed, {} matched",
                board_path.display(),
                placed_initial,
                matched_initial,
                placed_final,
                matched_final
            )),
        };
        save_board(&out, &puzzle, &new_board, &meta).expect("save");
        eprintln!("Wrote: {}", out.display());
    }
}
