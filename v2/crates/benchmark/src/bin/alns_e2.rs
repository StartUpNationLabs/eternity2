// ALNS (Adaptive Large Neighborhood Search) on Eternity II.
//
// Starting board options:
//   - Run cell-CP then optionally PT, use that as the ALNS seed.
//   - Load a plateau JSON (preferred for vol. 4 — we already have a 449).
//
// Operator portfolio (default: all four):
//   - random_region (k)
//   - worst_window (k)
//   - conflict_driven (max_size)
//   - mwpm_defect_pair (max_pairs)
//
// Reports best score, full per-operator stats, and a JSON snapshot of
// the final board via the standard write_report helper.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::{puzzle_name_from_path, write_report};
use eternity2_core::{Board, Hint, Hints, Piece, PieceId, Puzzle, Rotation, BORDER};
use eternity2_events::BufferSink;
use eternity2_localsearch::{run_alns, run_pt_from, Acceptance, AlnsConfig, ConflictDriven,
                            DestroyOp, MwpmDefectPair, PtConfig, RandomRegion, RepairKind,
                            WorstWindow};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};
use serde_json::Value;

#[derive(Parser, Debug)]
#[command(name = "alns_e2", about = "ALNS on Eternity II")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// ALNS total wall-clock budget in seconds.
    #[arg(long, default_value_t = 600)]
    seconds: u64,

    /// CP repair time budget per ALNS iteration (milliseconds).
    #[arg(long, default_value_t = 500)]
    repair_ms: u64,

    /// SA temperature for acceptance (constant; future: cooling schedule).
    #[arg(long, default_value_t = 1.0)]
    t: f64,

    /// Random seed.
    #[arg(long, default_value_t = 0xA1A2A3A4)]
    seed: u64,

    /// Skip the CP+PT warm-up; start from an empty board (CP fills it).
    #[arg(long, default_value_t = false)]
    skip_warmup: bool,

    /// Load a starting board from a plateau JSON (preferred if available).
    #[arg(long)]
    seed_board: Option<PathBuf>,

    /// CP warm-up budget in seconds (used if --seed-board is not set).
    #[arg(long, default_value_t = 60)]
    cp_seconds: u64,

    /// PT warm-up budget in seconds (used if --seed-board is not set; 0 = skip PT).
    #[arg(long, default_value_t = 60)]
    pt_seconds: u64,

    /// Operators to use: subset of "rr,ww,cd,mwpm". Default: all four.
    #[arg(long, default_value = "rr,ww,cd,mwpm")]
    ops: String,

    /// Random-region k.
    #[arg(long, default_value_t = 4)]
    rr_k: u32,

    /// Worst-window k.
    #[arg(long, default_value_t = 5)]
    ww_k: u32,

    /// Conflict-driven max_size.
    #[arg(long, default_value_t = 30)]
    cd_max: u32,

    /// MWPM max_pairs.
    #[arg(long, default_value_t = 12)]
    mwpm_max: u32,

    /// Repair strategy: "sa" (SA-based, always succeeds; default) or
    /// "cp" (cell-CP; faster when feasible but AC3-wipes on plateau
    /// states — falls back to SA when --cp-fallback is set).
    #[arg(long, default_value = "sa")]
    repair: String,

    /// Fall back to SA when CP repair fails. Default true.
    #[arg(long, default_value_t = true)]
    cp_fallback: bool,

    /// Verbose progress every 2s.
    #[arg(long, default_value_t = true)]
    verbose: bool,

    /// V140 — enable INTAGLIO 2x2 forbidden-patch tiebreaker on iso-score moves.
    #[arg(long, default_value_t = false)]
    lex_break_intaglio: bool,
}

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.piece(id)
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

fn pct(n: u32, d: u32) -> f64 { 100.0 * (n as f64) / (d as f64) }

fn load_board_from_json(puzzle: &Puzzle, path: &PathBuf) -> Option<Board> {
    let s = std::fs::read_to_string(path).ok()?;
    let v: Value = serde_json::from_str(&s).ok()?;
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        if arr.len() != puzzle.cell_count() as usize { return None; }
        let mut b = Board::empty(puzzle);
        for (pos, entry) in arr.iter().enumerate() {
            if entry.is_null() { continue; }
            let pid = entry.get("piece_id")?.as_u64()? as PieceId;
            let rot_u = entry.get("rotation")?.as_u64()? as u8;
            b.place(pos as u32, pid, Rotation::from_u8(rot_u)?);
        }
        return Some(b);
    }
    if let Some(url) = v.get("bucas_url").and_then(|x| x.as_str()) {
        return Some(decode_from_bucas(puzzle, url));
    }
    None
}

fn decode_from_bucas(puzzle: &Puzzle, url: &str) -> Board {
    let mut b = Board::empty(puzzle);
    let Some(idx) = url.find("board_edges=") else { return b };
    let blob = &url[idx + "board_edges=".len()..];
    let blob = blob.split('&').next().unwrap_or(blob);
    let bytes = blob.as_bytes();
    let n_cells = puzzle.cell_count() as usize;
    if bytes.len() < n_cells * 4 { return b; }
    for pos in 0..n_cells {
        let q: [u8; 4] = std::array::from_fn(|i| bytes[pos * 4 + i] - b'a');
        if q.iter().all(|&c| c == 0) { continue; }
        for piece in puzzle.pieces() {
            for rot in Rotation::ALL {
                if piece.edges.rotated(rot).as_array() == q {
                    b.place(pos as u32, piece.id, rot);
                    break;
                }
            }
        }
    }
    b
}

fn parse_ops(spec: &str, args: &Args) -> Vec<Box<dyn DestroyOp>> {
    let mut out: Vec<Box<dyn DestroyOp>> = Vec::new();
    for tok in spec.split(',').map(|t| t.trim()) {
        match tok {
            "rr" => out.push(Box::new(RandomRegion { k: args.rr_k })),
            "ww" => out.push(Box::new(WorstWindow { k: args.ww_k })),
            "cd" => out.push(Box::new(ConflictDriven { max_size: args.cd_max })),
            "mwpm" => out.push(Box::new(MwpmDefectPair { max_pairs: args.mwpm_max })),
            "" => {}
            other => panic!("unknown op '{}' in --ops (use rr,ww,cd,mwpm)", other),
        }
    }
    out
}

fn main() {
    let args = Args::parse();
    eprintln!("=== ALNS ON ETERNITY II ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("budget={}s repair_ms={} t={} seed=0x{:x} ops={}",
        args.seconds, args.repair_ms, args.t, args.seed, args.ops);

    let (puzzle, file_hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    eprintln!("loaded {}×{}, {} pieces, {} colors, {} hints",
        puzzle.width, puzzle.height, puzzle.pieces().len(),
        puzzle.color_count - 1, file_hints.hints.len());

    // ----- Build starting board -----
    let initial: Board = if let Some(path) = &args.seed_board {
        let b = load_board_from_json(&puzzle, path)
            .expect("failed to load seed board from JSON");
        let (s, t) = score_board(&puzzle, &b);
        eprintln!("loaded seed board: {}/{} ({:.1}%)", s, t, pct(s, t));
        b
    } else if args.skip_warmup {
        eprintln!("--skip-warmup: starting from empty board");
        Board::empty(&puzzle)
    } else {
        // CP warm-up.
        eprintln!("\n--- CP warm-up ({}s) ---", args.cp_seconds);
        let mut solver = EngineSolver::gacolor_ac3_par();
        let mut sink = BufferSink::new();
        let mut opts = SolveOpts::default();
        opts.time_budget_ms = args.cp_seconds * 1000;
        opts.hints = file_hints.clone();
        let t0 = Instant::now();
        let out = solver.solve(&puzzle, &opts, &mut sink);
        let dt = t0.elapsed();
        let cp_board: Board = match out {
            SolveOutcome::Solved(b) | SolveOutcome::TimedOut { best_partial: b, .. }
            | SolveOutcome::Cancelled { best_partial: b, .. } => b,
            SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
            SolveOutcome::Exhausted => Board::empty(&puzzle),
            SolveOutcome::Error(e) => { eprintln!("CP err: {e}"); Board::empty(&puzzle) }
        };
        let (cp_s, cp_t) = score_board(&puzzle, &cp_board);
        eprintln!("CP done in {:.1}s: {}/{} ({:.1}%)",
            dt.as_secs_f64(), cp_s, cp_t, pct(cp_s, cp_t));

        if args.pt_seconds > 0 {
            eprintln!("\n--- PT warm-up ({}s) ---", args.pt_seconds);
            let pt_cfg = PtConfig {
                n_replicas: 8,
                t_min: 0.05, t_max: 2.0,
                inner_iters: 100_000,
                max_rounds: 0,
                time_budget_ms: args.pt_seconds * 1000,
                seed: args.seed,
                verbose: false,
                greedy_fill: true,
                diversify_fill: false,
                repair_every: 0, repair_k: 4, repair_budget_ms: 200,
                kick_every: 0, kick_n_swaps: 20,
                pinned_positions: file_hints.hints.iter().map(|h| h.position).collect(),
                houdayer_every: 0, houdayer_max_component: 20, houdayer_min_component: 4,
                houdayer_accept_zero_delta: false,
            forbidden_edges: Vec::new(),
            forbidden_penalty_k: 0,
            };
            let t1 = Instant::now();
            let (pt_out, _stats) = run_pt_from(&puzzle, &cp_board, &pt_cfg);
            let dt = t1.elapsed();
            let (pt_s, _) = score_board(&puzzle, &pt_out.best_board);
            eprintln!("PT done in {:.1}s: best={}/{} ({:.1}%)",
                dt.as_secs_f64(), pt_s, pt_out.total_edges, pct(pt_s, pt_out.total_edges));
            pt_out.best_board
        } else { cp_board }
    };

    let (init_s, init_t) = score_board(&puzzle, &initial);
    eprintln!("\nInitial board score: {}/{} ({:.1}%)", init_s, init_t, pct(init_s, init_t));

    // ----- ALNS -----
    eprintln!("\n--- ALNS ({}s) ---", args.seconds);
    let mut ops = parse_ops(&args.ops, &args);
    eprintln!("operators: {}", ops.iter().map(|o| o.name().to_string()).collect::<Vec<_>>().join(", "));

    let repair_kind = match args.repair.as_str() {
        "sa" => RepairKind::Sa,
        "cp" => RepairKind::Cp,
        "filament" => RepairKind::Filament,
        other => panic!("unknown --repair '{}' (use sa|cp|filament)", other),
    };
    let cfg = AlnsConfig {
        time_budget_ms: args.seconds * 1000,
        repair_budget_ms: args.repair_ms,
        acceptance: Acceptance::SimulatedAnnealing { t: args.t },
        segment_iters: 50,
        seed: args.seed,
        verbose: args.verbose,
        repair: repair_kind,
        cp_fallback_to_sa: args.cp_fallback,
        // Vol-14 fix: pin the canonical hint positions. Without this,
        // destroy operators happily free hint cells and the score is
        // for the wrong puzzle.
        pinned_positions: file_hints.hints.iter().map(|h| h.position).collect(),
        iter_budget: 0,
            lex_break_isoscore: false,
        lex_break_intaglio: args.lex_break_intaglio,
        checkpoint_path: None,
        checkpoint_every_ms: 60_000,
        repair_step_budget: 0,
        cp_repair_parallel: true,
    };
    let t_alns = Instant::now();
    let (best, stats) = run_alns(&puzzle, &initial, ops.as_mut_slice(), &cfg);
    let alns_elapsed = t_alns.elapsed();
    let (best_s, best_t) = score_board(&puzzle, &best);

    eprintln!("\n=== ALNS RESULT ===");
    eprintln!("elapsed: {:.1}s   iters: {}", alns_elapsed.as_secs_f64(), stats.iters);
    eprintln!("initial: {}/{} ({:.1}%)", init_s, init_t, pct(init_s, init_t));
    eprintln!("best:    {}/{} ({:.1}%)   Δ = {:+}",
        best_s, best_t, pct(best_s, best_t), best_s as i32 - init_s as i32);
    eprintln!("repair_failures: {}", stats.repair_failures);
    eprintln!("accepted: improving={} worse={} rejected={}",
        stats.accepted_improving, stats.accepted_worse, stats.rejected);
    eprintln!("per-operator:");
    for i in 0..stats.op_names.len() {
        let inv = stats.per_op_invocations[i];
        let acc = stats.per_op_accepts[i];
        let rate = if inv > 0 { 100.0 * (acc as f64) / (inv as f64) } else { 0.0 };
        eprintln!("  {:>18}: invocations={} accepts={} ({:.1}%)",
            stats.op_names[i], inv, acc, rate);
    }
    eprintln!("best-score history (first 30): {:?}",
        stats.best_score_history.iter().take(30).collect::<Vec<_>>());

    // ----- Report -----
    let output_dir = std::path::PathBuf::from("output");
    let puzzle_name = puzzle_name_from_path(&args.puzzle);
    let extra = serde_json::json!({
        "alns": {
            "elapsed_s": alns_elapsed.as_secs_f64(),
            "budget_s": args.seconds,
            "iters": stats.iters,
            "repair_failures": stats.repair_failures,
            "accepted_improving": stats.accepted_improving,
            "accepted_worse": stats.accepted_worse,
            "rejected": stats.rejected,
            "initial_score": init_s,
            "best_score": best_s,
            "per_op_invocations": stats.per_op_invocations,
            "per_op_accepts": stats.per_op_accepts,
            "op_names": stats.op_names,
            "best_history": stats.best_score_history,
            "operators_used": args.ops,
            "repair_budget_ms": args.repair_ms,
            "t": args.t,
        },
        "seed": args.seed,
    });
    match write_report(&output_dir, "alns_e2", &puzzle, &puzzle_name, &best, extra) {
        Ok(r) => {
            eprintln!("\nReport: {}", r.json_path.display());
            eprintln!("Bucas:  {}", r.url);
        }
        Err(e) => eprintln!("warning: failed to write report: {e}"),
    }
    let _ = (file_hints, Hints::default(), Hint { position: 0, piece_id: 0, rotation: Rotation::R0 });
}
