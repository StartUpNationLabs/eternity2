// verhaard_e2 — full Verhaard pipeline on canonical E2 using
// solver-engine for the backtracker.
//
//   Phase-0: outer SA over piece-set composition. Picks 186 of 196
//             inner pieces; the 10 remaining are "deferred".
//             Metric: #2x2 sub-tilings exhausted on the set (Verhaard
//             2008, groups.io 105190116, R² = 0.65 with log #tilings).
//   Phase-1: solver-engine search with SolveOpts.excluded_pieces set
//             to the deferred 10. Reports best partial (depth/edges).
//   Phase-2 (TODO): release the deferred pieces and continue from
//             phase-1's best partial.
//
// Calibration metric: best_edges (matched edges) on a partial board.
// Community ceiling on canonical 5-clue is 469/480 (McGavin 2020).
// Vol-7 reached ~454 via PT-based search; Verhaard's *attested* 467
// ceiling came from this set-composition algorithm.

#![forbid(unsafe_code)]

use std::fs::{create_dir_all, File};
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Piece, PieceId};
use eternity2_events::EventSink;
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveMode, SolveOpts, SolveOutcome, Solver};
use eternity2_solver_verhaard::sa::{run_sa, SaConfig, SimpleRng};
use eternity2_solver_verhaard::tile2x2::Tile2x2Index;

#[derive(Parser, Debug)]
#[command(name = "verhaard_e2", about = "Verhaard pipeline on canonical E2")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long, default_value = "output/v9_verhaard/run.json")]
    out: PathBuf,

    /// Inner-set size — Verhaard used 180-190 of 196.
    #[arg(long, default_value_t = 186)]
    k_target: usize,

    /// SA iterations.
    #[arg(long, default_value_t = 10_000)]
    sa_iters: u64,

    #[arg(long, default_value_t = 30000.0)]
    sa_t_initial: f64,
    #[arg(long, default_value_t = 100.0)]
    sa_t_final: f64,
    #[arg(long, default_value_t = 0.9995)]
    sa_cooling: f64,

    /// Phase-1 search time budget per profile (seconds).
    #[arg(long, default_value_t = 60u64)]
    phase1_secs: u64,

    /// Skip random-set baseline?
    #[arg(long, default_value_t = false)]
    skip_baseline: bool,

    /// Skip full-set reference?
    #[arg(long, default_value_t = false)]
    skip_reference: bool,

    /// Engine profile to use for phase-1 / baseline / reference.
    /// Default "gacolor_ac3_par" matches vol-7's strongest single-profile.
    #[arg(long, default_value = "gacolor_ac3_par")]
    profile: String,

    /// Number of "worst performers" (in addition to the deferred 10)
    /// to mark as preferred-first in the Verhaard run.
    #[arg(long, default_value_t = 10)]
    n_worst_performers: usize,

    /// RNG seed.
    #[arg(long, default_value_t = 0xDEC0DEDADC0DEu64)]
    seed: u64,
}

/// EventSink that just discards everything but tracks best partial.
/// solver-engine emits `Started`/`Solved`/`Exhausted`/`TimedOut` plus
/// per-node events; we don't need any of them — the SolveOutcome
/// carries the partial board for us.
struct NullSink;
impl EventSink for NullSink {
    fn emit(&mut self, _e: eternity2_events::SolverEvent) {}
    fn should_continue(&self) -> bool { true }
}

fn make_solver(profile: &str) -> EngineSolver {
    match profile {
        "border_first_lcv" => EngineSolver::border_first_lcv(),
        "border_first_lcv_par" => EngineSolver::border_first_lcv_par(),
        "border_first_full_par" => EngineSolver::border_first_full_par(),
        "border_first_gacolor" => EngineSolver::border_first_gacolor(),
        "border_first_gacolor_par" => EngineSolver::border_first_gacolor_par(),
        "chess_gacolor_par" => EngineSolver::chess_gacolor_par(),
        "gacolor_symbreak_par" => EngineSolver::gacolor_symbreak_par(),
        "gacolor_ac3" => EngineSolver::gacolor_ac3(),
        "gacolor_ac3_par" => EngineSolver::gacolor_ac3_par(),
        "verhaard_preferred" => EngineSolver::verhaard_preferred(),
        "verhaard_preferred_par" => EngineSolver::verhaard_preferred_par(),
        _ => EngineSolver::border_first_gacolor_par(),
    }
}

#[derive(Debug, serde::Serialize)]
struct PhaseResult {
    name: String,
    best_depth: u32,
    best_edges: Option<u32>,
    outcome_kind: String,
    elapsed_s: f64,
    n_excluded: usize,
}

/// Count matched edges on a possibly-partial board. None for any cell
/// is treated as "no edge contribution".
fn count_partial_edges(puzzle: &eternity2_core::Puzzle, board: &eternity2_core::Board) -> u32 {
    let mut c = 0u32;
    let w = puzzle.width;
    let h = puzzle.height;
    let mut placed: Vec<Option<[eternity2_core::Color; 4]>> = vec![None; puzzle.cell_count() as usize];
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, rot)) = board.get(pos) {
            let piece = puzzle.piece(pid);
            if let Some(piece) = piece {
                placed[pos as usize] = Some(piece.edges.rotated(rot).as_array());
            }
        }
    }
    for y in 0..h {
        for x in 0..w {
            let pos = (y * w + x) as usize;
            let edges = match placed[pos] { Some(e) => e, None => continue };
            // Top neighbor
            if y > 0 {
                let n = ((y - 1) * w + x) as usize;
                if let Some(ne) = placed[n] {
                    if edges[0] == ne[2] { c += 1; }
                }
            }
            // Left neighbor
            if x > 0 {
                let n = (y * w + (x - 1)) as usize;
                if let Some(ne) = placed[n] {
                    if edges[3] == ne[1] { c += 1; }
                }
            }
        }
    }
    c
}

fn run_search(
    puzzle: &eternity2_core::Puzzle,
    profile: &str,
    excluded: Vec<PieceId>,
    preferred: Vec<PieceId>,
    time_budget_ms: u64,
    seed: u64,
    name: &str,
) -> PhaseResult {
    let mut solver = make_solver(profile);
    let opts = SolveOpts {
        mode: SolveMode::FirstSolution,
        path: Vec::new(),
        path_policy: eternity2_core::PathPolicy::Ignored,
        hints: eternity2_core::Hints::default(),
        seed,
        time_budget_ms,
        max_solutions: 0,
        solver_run_id: 0,
        excluded_pieces: excluded.clone(),
        preferred_pieces: preferred,
        edge_bp_marginals: None,
    };
    let mut sink = NullSink;
    let t0 = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();

    let (kind, depth, edges) = match outcome {
        SolveOutcome::Solved(board) => (
            "Solved".to_string(),
            puzzle.cell_count(),
            Some(count_partial_edges(puzzle, &board)),
        ),
        SolveOutcome::AllSolutions(boards) => (
            "AllSolutions".to_string(),
            puzzle.cell_count(),
            boards.first().map(|b| count_partial_edges(puzzle, b)),
        ),
        SolveOutcome::Exhausted => ("Exhausted".to_string(), 0, None),
        SolveOutcome::TimedOut { best_partial, best_depth } => (
            "TimedOut".to_string(),
            best_depth,
            Some(count_partial_edges(puzzle, &best_partial)),
        ),
        SolveOutcome::Cancelled { best_partial, best_depth, .. } => (
            "Cancelled".to_string(),
            best_depth,
            Some(count_partial_edges(puzzle, &best_partial)),
        ),
        SolveOutcome::Error(msg) => (format!("Error: {msg}"), 0, None),
    };

    PhaseResult {
        name: name.to_string(),
        best_depth: depth,
        best_edges: edges,
        outcome_kind: kind,
        elapsed_s: elapsed.as_secs_f64(),
        n_excluded: excluded.len(),
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).map_err(|e| format!("{e}"))?;
    eprintln!("puzzle: {}x{}, {} pieces", puzzle.width, puzzle.height, puzzle.pieces().len());

    let inner_pieces: Vec<Piece> = puzzle.pieces().iter().filter(|p| p.is_inner()).copied().collect();
    let inner_pids: Vec<PieceId> = inner_pieces.iter().map(|p| p.id).collect();
    eprintln!("inner pieces: {}", inner_pieces.len());

    let max_color = puzzle.color_count as usize;
    let idx = Tile2x2Index::build(&inner_pieces, max_color);

    // -- Phase-0: SA --
    eprintln!("\n== Phase-0: outer SA ==");
    let sa_cfg = SaConfig {
        k_target: args.k_target,
        max_iters: args.sa_iters,
        t_initial: args.sa_t_initial,
        t_final: args.sa_t_final,
        cooling: args.sa_cooling,
        seed: args.seed,
        log_every: args.sa_iters.max(10) / 10,
        sanity_every: 0,
    };
    let sa_t0 = Instant::now();
    let sa_result = run_sa(&inner_pieces, &idx, &sa_cfg);
    eprintln!(
        "  SA: best_metric={} final_metric={} accepts={} iters={} elapsed={:.1}s",
        sa_result.best_metric, sa_result.final_metric, sa_result.accepts, sa_result.iters,
        sa_t0.elapsed().as_secs_f64()
    );

    let chosen: Vec<PieceId> = sa_result.best_set.clone();
    let chosen_mask_set: std::collections::HashSet<PieceId> = chosen.iter().copied().collect();
    let deferred: Vec<PieceId> = inner_pids.iter().copied().filter(|p| !chosen_mask_set.contains(p)).collect();
    eprintln!("  chosen |good|={}, |deferred|={}", chosen.len(), deferred.len());

    // Worst performers among the chosen set: lowest participates() values.
    let mut chosen_mask_vec = vec![false; 256];
    for &p in &chosen { chosen_mask_vec[p as usize] = true; }
    let mut parts: Vec<(PieceId, u64)> = chosen
        .iter()
        .map(|&pid| (pid, idx.participates(pid, &chosen_mask_vec)))
        .collect();
    parts.sort_by_key(|(_, c)| *c);
    let worst_good: Vec<PieceId> = parts.iter().take(args.n_worst_performers).map(|(p, _)| *p).collect();

    // Verhaard's preferred-pieces list = deferred ∪ worst-good.
    let mut preferred: Vec<PieceId> = deferred.clone();
    preferred.extend(worst_good.iter().copied());
    eprintln!("  |preferred (deferred ∪ worst-good)| = {}", preferred.len());

    // -- Experiment A: verhaard_preferred profile with the preferred list --
    eprintln!("\n== A: verhaard_preferred (no exclusion, value-order biased) ==");
    let phase1_verhaard = run_search(
        &puzzle, "verhaard_preferred_par", Vec::new(), preferred.clone(),
        args.phase1_secs * 1000, args.seed, "verhaard_preferred",
    );
    eprintln!(
        "  verhaard_preferred: outcome={} depth={} edges={:?} elapsed={:.1}s",
        phase1_verhaard.outcome_kind, phase1_verhaard.best_depth, phase1_verhaard.best_edges, phase1_verhaard.elapsed_s
    );

    // -- Experiment B: same profile, RANDOM preferred list --
    let mut phase1_random_pref: Option<PhaseResult> = None;
    if !args.skip_baseline {
        eprintln!("\n== B: verhaard_preferred with RANDOM preferred list ==");
        let mut rng = SimpleRng::new(args.seed.wrapping_add(99));
        let mut shuffled = inner_pids.clone();
        for i in (1..shuffled.len()).rev() {
            let j = (rng.next_u64() as usize) % (i + 1);
            shuffled.swap(i, j);
        }
        let random_pref: Vec<PieceId> = shuffled.iter().take(preferred.len()).copied().collect();
        let r = run_search(
            &puzzle, "verhaard_preferred_par", Vec::new(), random_pref,
            args.phase1_secs * 1000, args.seed, "random_preferred",
        );
        eprintln!(
            "  random_preferred: outcome={} depth={} edges={:?} elapsed={:.1}s",
            r.outcome_kind, r.best_depth, r.best_edges, r.elapsed_s
        );
        phase1_random_pref = Some(r);
    }

    // -- Experiment C: reference — same profile, no preference --
    let mut reference: Option<PhaseResult> = None;
    if !args.skip_reference {
        eprintln!("\n== C: reference — {} with no preferred list ==", args.profile);
        let r = run_search(
            &puzzle, &args.profile, Vec::new(), Vec::new(),
            args.phase1_secs * 1000, args.seed, "reference",
        );
        eprintln!(
            "  reference: outcome={} depth={} edges={:?} elapsed={:.1}s",
            r.outcome_kind, r.best_depth, r.best_edges, r.elapsed_s
        );
        reference = Some(r);
    }

    // -- Experiment D: exclusion-mode (original Verhaard interpretation
    //    that we showed was wrong, for the record) --
    eprintln!("\n== D: exclusion-mode (deferred 10 forbidden) — known-wrong baseline ==");
    let phase1_excluded = run_search(
        &puzzle, &args.profile, deferred.clone(), Vec::new(),
        args.phase1_secs * 1000, args.seed, "exclusion_mode",
    );
    eprintln!(
        "  exclusion: outcome={} depth={} edges={:?} elapsed={:.1}s",
        phase1_excluded.outcome_kind, phase1_excluded.best_depth, phase1_excluded.best_edges, phase1_excluded.elapsed_s
    );

    // Serialize.
    if let Some(p) = args.out.parent() { create_dir_all(p)?; }
    let mut writer = BufWriter::new(File::create(&args.out)?);
    let summary = serde_json::json!({
        "puzzle": args.puzzle.display().to_string(),
        "profile": args.profile,
        "args": {
            "k_target": args.k_target,
            "sa_iters": args.sa_iters,
            "phase1_secs": args.phase1_secs,
            "seed": args.seed,
        },
        "sa": sa_result,
        "experiment_A_verhaard_preferred": phase1_verhaard,
        "experiment_B_random_preferred": phase1_random_pref,
        "experiment_C_reference": reference,
        "experiment_D_exclusion": phase1_excluded,
    });
    serde_json::to_writer_pretty(&mut writer, &summary)?;
    writeln!(writer)?;
    drop(writer);
    eprintln!("\nwrote {}", args.out.display());

    Ok(())
}
