// Harvest plateau states for RSB diagnostic.
//
// Runs the CP→PT pipeline N times with distinct seeds (CP itself is
// deterministic; the seed varies PT only). Each final PT board is dumped
// to JSON in `output/plateau/<run_name>/`. The pairwise overlap analysis
// (see `analyze_overlap`) consumes those dumps.
//
// Why this matters: if plateau states cluster into discrete basins with
// large gaps between them, the energy landscape is 1-RSB and PT cannot
// cross — explaining the 446-449 plateau and motivating Houdayer cluster
// moves. If they form one continuous distribution, the cause is elsewhere.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::board_io::{write_dump, DumpedBoard};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::puzzle_name_from_path;
use eternity2_core::{Board, Piece, PieceId, Puzzle, BORDER};
use eternity2_events::BufferSink;
use eternity2_localsearch::{run_pt_from, PtConfig};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

#[derive(Parser, Debug)]
#[command(name = "harvest_plateau", about = "Sample plateau states for RSB diagnostic")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// Number of plateau states to harvest.
    #[arg(long, default_value_t = 20)]
    n_samples: u32,

    /// CP budget (seconds) per sample. CP is deterministic so this stays small;
    /// the per-sample work is dominated by PT.
    #[arg(long, default_value_t = 30)]
    cp_seconds: u64,

    /// PT budget (seconds) per sample.
    #[arg(long, default_value_t = 90)]
    pt_seconds: u64,

    /// Number of PT replicas per sample.
    #[arg(long, default_value_t = 8)]
    n_replicas: usize,

    #[arg(long, default_value_t = 100_000)]
    inner_iters: u64,

    #[arg(long, default_value_t = 0.05)]
    t_min: f64,

    #[arg(long, default_value_t = 2.0)]
    t_max: f64,

    /// Base seed; per-sample seed = base ^ (sample_idx * 0x9E37_79B9_7F4A_7C15).
    #[arg(long, default_value_t = 0xE2_E2_E2_E2)]
    seed: u64,

    /// Sub-directory under output/plateau/ to write dumps into.
    #[arg(long, default_value = "default")]
    run_name: String,

    /// Re-run CP per sample instead of reusing one CP partial. By default we
    /// reuse a single CP partial (CP is deterministic with the same opts so
    /// re-running gives identical results unless --random-cp is set).
    /// Use `--no-reuse-cp` (or equivalently set this to false) when you
    /// want CP itself to vary between samples.
    #[arg(long, default_value_t = true, action = clap::ArgAction::Set)]
    reuse_cp: bool,

    /// Pin the official-E2 hint positions during PT.
    #[arg(long, default_value_t = true, action = clap::ArgAction::Set)]
    pin_hints: bool,

    /// Use `gacolor_ac3_random_par` (seeded random variable-order tiebreaker)
    /// instead of the deterministic `gacolor_ac3_par`. Combined with
    /// `--reuse-cp=false`, this produces a different CP partial per sample,
    /// diversifying the canonical prefix that PT seeds from.
    #[arg(long, default_value_t = false)]
    random_cp: bool,
}

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.pieces().iter().find(|p| p.id == id)
}

fn score_board(puzzle: &Puzzle, board: &Board) -> (u32, u32) {
    let w = puzzle.width;
    let h = puzzle.height;
    let total = (w - 1) * h + w * (h - 1);
    let mut matches = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue };
            let Some(piece) = lookup_piece(puzzle, pid) else { continue };
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

fn run_cp(
    puzzle: &Puzzle,
    hints: eternity2_core::Hints,
    budget_ms: u64,
    random_cp: bool,
    seed: u64,
) -> Board {
    let mut solver = if random_cp {
        EngineSolver::gacolor_ac3_random_par()
    } else {
        EngineSolver::gacolor_ac3_par()
    };
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.hints = hints;
    opts.seed = seed;
    match solver.solve(puzzle, &opts, &mut sink) {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::TimedOut { best_partial, .. } => best_partial,
        SolveOutcome::Cancelled { best_partial, .. } => best_partial,
        SolveOutcome::Exhausted | SolveOutcome::Error(_) => Board::empty(puzzle),
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(puzzle)),
    }
}

fn main() {
    let args = Args::parse();
    eprintln!("=== HARVEST_PLATEAU (RSB diagnostic) ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("n_samples={} cp={}s pt={}s replicas={} reuse_cp={}",
        args.n_samples, args.cp_seconds, args.pt_seconds, args.n_replicas, args.reuse_cp);

    let (puzzle, file_hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    eprintln!("loaded {}×{}, {} pieces, {} colors",
        puzzle.width, puzzle.height, puzzle.pieces().len(), puzzle.color_count - 1);

    let puzzle_name = puzzle_name_from_path(&args.puzzle);
    let out_dir = PathBuf::from("output").join("plateau").join(&args.run_name);
    eprintln!("dump dir: {}", out_dir.display());

    // -- Initial CP partial (reused across samples by default).
    let cp_board_shared: Option<Board> = if args.reuse_cp {
        eprintln!("\n--- CP phase (shared, {}s, random_cp={}) ---",
            args.cp_seconds, args.random_cp);
        let t = Instant::now();
        let b = run_cp(&puzzle, file_hints.clone(), args.cp_seconds * 1000, args.random_cp, args.seed);
        let (s, total) = score_board(&puzzle, &b);
        eprintln!("CP: {}/{} ({:.1}%) in {:.1}s", s, total, 100.0 * (s as f64) / (total as f64), t.elapsed().as_secs_f64());
        Some(b)
    } else {
        None
    };

    let global_start = Instant::now();
    let mut all_scores: Vec<u32> = Vec::with_capacity(args.n_samples as usize);

    for idx in 0..args.n_samples {
        // Mix the base seed with the index using a golden-ratio multiplier
        // so adjacent samples don't correlate even if base seed is simple.
        let sample_seed = args.seed.wrapping_add((idx as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15));

        eprintln!("\n--- sample {}/{} (seed=0x{:x}) ---", idx + 1, args.n_samples, sample_seed);

        let cp_board = if let Some(ref shared) = cp_board_shared {
            shared.clone()
        } else {
            let t = Instant::now();
            // Per-sample CP gets the per-sample seed; with random_cp=true
            // this means each sample's CP partial is different.
            let b = run_cp(&puzzle, file_hints.clone(), args.cp_seconds * 1000, args.random_cp, sample_seed);
            let (cp_s, _) = score_board(&puzzle, &b);
            eprintln!("  CP {:.1}s, score {}", t.elapsed().as_secs_f64(), cp_s);
            b
        };

        let pinned: Vec<u32> = if args.pin_hints {
            file_hints.hints.iter().map(|h| h.position).collect()
        } else { Vec::new() };
        let pt_cfg = PtConfig {
            n_replicas: args.n_replicas,
            t_min: args.t_min,
            t_max: args.t_max,
            inner_iters: args.inner_iters,
            max_rounds: 0,
            time_budget_ms: args.pt_seconds * 1000,
            seed: sample_seed,
            verbose: false,
            greedy_fill: true,
            diversify_fill: false,
            repair_every: 0,
            repair_k: 4,
            repair_budget_ms: 200,
            kick_every: 0,
            kick_n_swaps: 6,
            pinned_positions: pinned,
            houdayer_every: 0,
            houdayer_max_component: 20,
            houdayer_min_component: 4,
        forbidden_edges: Vec::new(),
        forbidden_penalty_k: 0,
        };
        let t = Instant::now();
        let (pt_out, _stats) = run_pt_from(&puzzle, &cp_board, &pt_cfg);
        let elapsed = t.elapsed().as_secs_f64();
        let (score, total) = score_board(&puzzle, &pt_out.best_board);
        all_scores.push(score);
        eprintln!("  PT {:.1}s: {}/{} ({:.1}%)", elapsed, score, total, 100.0 * (score as f64) / (total as f64));

        let dump = DumpedBoard::from_board(&pt_out.best_board, sample_seed, score, total);
        let path = out_dir.join(format!("sample_{:03}_seed_{:016x}_score_{}.json", idx, sample_seed, score));
        if let Err(e) = write_dump(&path, &dump) {
            eprintln!("  warning: failed to dump: {e}");
        } else {
            eprintln!("  → {}", path.display());
        }
    }

    let wall = global_start.elapsed().as_secs_f64();
    let mean = all_scores.iter().map(|s| *s as f64).sum::<f64>() / (all_scores.len() as f64);
    let min = *all_scores.iter().min().unwrap_or(&0);
    let max = *all_scores.iter().max().unwrap_or(&0);
    eprintln!("\n=== HARVEST DONE ===");
    eprintln!("samples: {}   wall_clock: {:.1}s   per_sample: {:.1}s",
        args.n_samples, wall, wall / (args.n_samples as f64));
    eprintln!("scores: min={} max={} mean={:.1}", min, max, mean);
    eprintln!("scores: {:?}", all_scores);
    eprintln!("dumps in: {}", out_dir.display());
    let _ = puzzle_name;
}
