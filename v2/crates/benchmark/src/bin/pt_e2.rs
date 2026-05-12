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
use eternity2_benchmark::report::{puzzle_name_from_path, write_report};
use eternity2_core::{Board, Hints, Piece, PieceId, Puzzle, Rotation, BORDER};
use eternity2_events::BufferSink;
use eternity2_localsearch::{run_pt_from, run_sa_from, parse_forbidden_json, PtConfig, SaConfig};
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

    /// Run mini-CP region repair every N PT rounds (0=disable).
    #[arg(long, default_value_t = 0)]
    repair_every: u64,

    /// Repair region size (k×k).
    #[arg(long, default_value_t = 4)]
    repair_k: u32,

    /// CP budget per repair attempt (milliseconds).
    #[arg(long, default_value_t = 200)]
    repair_budget_ms: u64,

    /// Basin-hop kick every N PT rounds (0=disable).
    #[arg(long, default_value_t = 0)]
    kick_every: u64,

    /// Number of unconditional random swaps per kick.
    #[arg(long, default_value_t = 20)]
    kick_n_swaps: u32,

    /// Pin the official-E2 hint positions during PT (default true). When
    /// false, PT may freely move the hint pieces — useful to compare to
    /// unconstrained scores but means our score isn't the official E2 score.
    #[arg(long, default_value_t = true)]
    pin_hints: bool,

    /// Apply Houdayer cluster moves between adjacent replica pairs every
    /// N PT rounds (0 = disable). Recommended starting point: 10.
    #[arg(long, default_value_t = 0)]
    houdayer_every: u64,

    /// Skip Houdayer components larger than this size (cells).
    #[arg(long, default_value_t = 20)]
    houdayer_max: usize,

    /// Skip Houdayer components smaller than this.
    #[arg(long, default_value_t = 4)]
    houdayer_min: usize,

    /// If true, accept Houdayer swaps with joint_delta == 0 (vol-3 buggy
    /// microcanonical behaviour — infinite toggling on plateau states).
    /// Default false: require strict positive joint_delta improvement.
    #[arg(long, default_value_t = false)]
    houdayer_accept_zero: bool,

    /// Path to JSON file with forbidden (universal-mismatch) edges:
    /// `[["h", pos], ["v", pos], ...]`. Empty/unset = unconstrained PT.
    #[arg(long)]
    forbidden_edges: Option<PathBuf>,

    /// Penalty weight K for forbidden mismatches in PT effective score.
    /// 0 = off.
    #[arg(long, default_value_t = 0)]
    forbidden_k: i64,

    /// Path to a prior pt_e2 / frame_first_e2 result JSON. When set,
    /// SKIP the CP phase entirely and start PT from this board. Useful
    /// for chaining PT runs: e.g. run a constrained PT to a fmm=0
    /// basin, then restart unconstrained PT from there to explore
    /// without the penalty. Reads the `placement` array; falls back
    /// to bucas_url decode if `placement` is missing.
    #[arg(long)]
    start_from: Option<PathBuf>,
}

/// Read a board from a pt_e2/frame_first_e2 result JSON's `placement`
/// array (the canonical per-cell {piece_id, rotation} | null format).
fn read_board_from_json(puzzle: &Puzzle, path: &std::path::Path) -> Result<Board, String> {
    let s = std::fs::read_to_string(path)
        .map_err(|e| format!("read {}: {e}", path.display()))?;
    let j: serde_json::Value = serde_json::from_str(&s)
        .map_err(|e| format!("parse JSON {}: {e}", path.display()))?;
    let placement = j.get("placement")
        .and_then(|p| p.as_array())
        .ok_or_else(|| format!("no `placement` array in {}", path.display()))?;
    if placement.len() != puzzle.cell_count() as usize {
        return Err(format!("placement len {} != puzzle cell_count {}",
            placement.len(), puzzle.cell_count()));
    }
    let mut board = Board::empty(puzzle);
    for (pos, cell) in placement.iter().enumerate() {
        if cell.is_null() { continue; }
        let pid = cell.get("piece_id").and_then(|v| v.as_u64())
            .ok_or_else(|| format!("cell {pos} missing piece_id"))? as PieceId;
        let rot_u8 = cell.get("rotation").and_then(|v| v.as_u64())
            .ok_or_else(|| format!("cell {pos} missing rotation"))? as u8;
        let rot = Rotation::from_u8(rot_u8)
            .ok_or_else(|| format!("cell {pos} bad rotation {rot_u8}"))?;
        board.place(pos as u32, pid, rot);
    }
    Ok(board)
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

    // ----- CP phase (or load prior board) -----
    let (cp_board, cp_elapsed_secs, cp_skipped) = if let Some(p) = args.start_from.as_ref() {
        eprintln!("\n--- LOADING prior board from {} (CP phase SKIPPED) ---", p.display());
        let b = read_board_from_json(&puzzle, p).expect("load --start-from board");
        (b, 0.0_f64, true)
    } else {
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
        (cp_board, cp_elapsed.as_secs_f64(), false)
    };
    let (cp_score, total) = score_board(&puzzle, &cp_board);
    if cp_skipped {
        eprintln!("loaded board: placed={}/{}, edges={}/{} ({:.1}%)",
            placed_count(&cp_board), puzzle.cell_count(), cp_score, total, pct(cp_score, total));
    } else {
        eprintln!("CP done in {:.1}s: placed={}/{}, edges={}/{} ({:.1}%)",
            cp_elapsed_secs, placed_count(&cp_board),
            puzzle.cell_count(), cp_score, total, pct(cp_score, total));
    }
    let cp_elapsed = std::time::Duration::from_secs_f64(cp_elapsed_secs);

    // ----- PT phase -----
    eprintln!("\n--- PT phase ({}s, {} replicas) ---", args.pt_seconds, args.n_replicas);
    let pinned: Vec<u32> = if args.pin_hints {
        file_hints.hints.iter().map(|h| h.position).collect()
    } else { Vec::new() };
    if args.pin_hints {
        eprintln!("pinning {} hint positions during PT: {:?}", pinned.len(), pinned);
    } else {
        eprintln!("pin_hints=false: PT may move hint pieces (UNOFFICIAL E2)");
    }
    let forbidden_edges = if let Some(p) = args.forbidden_edges.as_ref() {
        let s = std::fs::read_to_string(p).expect("read forbidden_edges JSON");
        let v = parse_forbidden_json(&s, puzzle.width)
            .expect("parse forbidden_edges JSON");
        eprintln!("forbidden-edge soft penalty: K={} on {} edges from {}",
            args.forbidden_k, v.len(), p.display());
        v
    } else { Vec::new() };
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
        repair_every: args.repair_every,
        repair_k: args.repair_k,
        repair_budget_ms: args.repair_budget_ms,
        kick_every: args.kick_every,
        kick_n_swaps: args.kick_n_swaps,
        pinned_positions: pinned,
        houdayer_every: args.houdayer_every,
        houdayer_max_component: args.houdayer_max,
        houdayer_min_component: args.houdayer_min,
        houdayer_accept_zero_delta: args.houdayer_accept_zero,
        forbidden_edges,
        forbidden_penalty_k: args.forbidden_k,
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
    if args.forbidden_k > 0 && args.forbidden_edges.is_some() {
        eprintln!("forbidden mismatches: best_board fmm={} (out of {}), final per-replica fmm={:?}",
            pt_stats.best_board_fmm, pt_cfg.forbidden_edges.len(), pt_stats.final_fmm);
    }

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

    let output_dir = std::path::PathBuf::from("output");
    let puzzle_name = puzzle_name_from_path(&args.puzzle);
    let extra = serde_json::json!({
        "cp": {
            "score": cp_score,
            "elapsed_s": cp_elapsed.as_secs_f64(),
            "budget_s": args.cp_seconds,
        },
        "pt": {
            "score": pt_out.best_score,
            "elapsed_s": pt_elapsed.as_secs_f64(),
            "budget_s": args.pt_seconds,
            "n_replicas": args.n_replicas,
            "inner_iters": args.inner_iters,
            "t_min": args.t_min,
            "t_max": args.t_max,
            "rounds": pt_stats.rounds,
            "swap_proposals": pt_stats.total_swap_proposals,
            "swap_accepts": pt_stats.total_swap_accepts,
            "pair_proposals": pt_stats.pair_proposals,
            "pair_accepts": pt_stats.pair_accepts,
            "final_replica_scores": pt_stats.final_scores,
            "repair_every": args.repair_every,
            "kick_every": args.kick_every,
            "forbidden_k": args.forbidden_k,
            "forbidden_count_configured": pt_cfg.forbidden_edges.len(),
            "best_board_fmm": pt_stats.best_board_fmm,
            "final_fmm": pt_stats.final_fmm,
        },
        "seed": args.seed,
    });
    match write_report(&output_dir, "pt_e2", &puzzle, &puzzle_name, &pt_out.best_board, extra) {
        Ok(r) => {
            eprintln!("\nReport: {}", r.json_path.display());
            eprintln!("Bucas:  {}", r.url);
        }
        Err(e) => eprintln!("warning: failed to write report: {e}"),
    }
    let _ = (file_hints, Hints::default());
}
