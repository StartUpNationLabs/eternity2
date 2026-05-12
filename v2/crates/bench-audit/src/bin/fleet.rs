// Before/after fleet harness for the audit.
//
// Two workloads, each timestamped + nodes-counted so we can compare a
// "baseline" run against an "after" run done with identical args.
//
//   ENGINE workload — generate puzzles of size in {8,9,10,11,12}, two
//     seeds each, run EngineSolver::gacolor_ac3() with a per-puzzle
//     budget. Record: solved (bool), elapsed_ms, nodes, nodes/sec,
//     best_depth.
//
//   PT workload — generate a 10×10 puzzle, run PT for the same budget
//     starting from an empty board. Record: best score, total_edges,
//     iterations/sec (rounds × inner_iters / elapsed_s).
//
// Output: a single JSON to a user-supplied path. Compare two runs with
// the `--compare base.json after.json` mode (see compare_fleet.rs).

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit as _; // ensure the crate is linked
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_localsearch::{run_pt, PtConfig};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
struct EngineResult {
    size: u32,
    colors: u32,
    seed: u64,
    profile: String,
    elapsed_ms: u64,
    nodes: u64,
    propagations: u64,
    backtracks: u64,
    best_depth: u32,
    solved: bool,
    nodes_per_sec: f64,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct PtResult {
    size: u32,
    colors: u32,
    seed: u64,
    elapsed_ms: u64,
    rounds: u64,
    inner_iters_per_round: u64,
    n_replicas: usize,
    best_score: u32,
    total_edges: u32,
    iters_per_sec: f64,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct FleetReport {
    label: String,
    cpu_brand: String,
    rustflags: String,
    profile: String, // cargo profile: release / bench
    budget_ms: u64,
    engine: Vec<EngineResult>,
    pt: Vec<PtResult>,
}

fn parse_args() -> (PathBuf, String, u64, bool) {
    let mut args = std::env::args().skip(1);
    let mut out = PathBuf::from("/tmp/fleet.json");
    let mut label = "baseline".to_string();
    let mut budget_ms: u64 = 60_000;
    let mut quick = false;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--out" => out = PathBuf::from(args.next().expect("--out PATH")),
            "--label" => label = args.next().expect("--label NAME"),
            "--budget-ms" => budget_ms = args.next().expect("--budget-ms MS").parse().expect("integer"),
            "--quick" => quick = true,
            other => panic!("unknown arg: {other}"),
        }
    }
    (out, label, budget_ms, quick)
}

fn cpu_brand() -> String {
    // macOS-only: sysctl machdep.cpu.brand_string
    if let Ok(out) = std::process::Command::new("sysctl")
        .args(["-n", "machdep.cpu.brand_string"])
        .output()
    {
        if out.status.success() {
            return String::from_utf8_lossy(&out.stdout).trim().to_string();
        }
    }
    "unknown".to_string()
}

fn rustflags_at_build() -> String {
    option_env!("RUSTFLAGS").unwrap_or("(unset)").to_string()
}

fn cargo_profile_at_build() -> String {
    if cfg!(debug_assertions) { "dev".into() } else { "release-or-bench".into() }
}

/// Listens only for terminal events (Solved/TimedOut/Exhausted/Cancelled) and
/// captures their embedded `FinalStats`. Every other event is dropped on the
/// floor with a single store — keeps the engine at full speed.
struct StatsOnlySink {
    final_stats: Option<FinalStats>,
}

impl EventSink for StatsOnlySink {
    fn emit(&mut self, event: SolverEvent) {
        match event.body {
            EventBody::Solved { final_stats, .. }
            | EventBody::Exhausted { final_stats, .. }
            | EventBody::TimedOut { final_stats, .. }
            | EventBody::Cancelled { final_stats, .. } => {
                self.final_stats = Some(final_stats);
            }
            _ => {}
        }
    }
}

fn run_engine_cell(size: u32, colors: u32, seed: u64, budget_ms: u64) -> EngineResult {
    let puzzle = generate(GeneratorConfig { size, interior_colors: colors, seed })
        .expect("generator must succeed");
    let mut solver = EngineSolver::gacolor_ac3();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = seed;
    let mut sink = StatsOnlySink { final_stats: None };
    let started = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed_ms = started.elapsed().as_millis() as u64;
    let stats = sink.final_stats.unwrap_or_default();
    let (solved, best_depth) = match &outcome {
        SolveOutcome::Solved(_) => (true, size * size),
        SolveOutcome::Exhausted => (false, stats.max_depth_seen),
        SolveOutcome::TimedOut { best_depth, .. } => (false, *best_depth),
        SolveOutcome::Cancelled { best_depth, .. } => (false, *best_depth),
        SolveOutcome::AllSolutions(b) => (!b.is_empty(), size * size),
        SolveOutcome::Error(_) => (false, 0),
    };
    let nps = if elapsed_ms > 0 { (stats.nodes as f64) * 1000.0 / (elapsed_ms as f64) } else { 0.0 };
    EngineResult {
        size, colors, seed,
        profile: "gacolor_ac3".into(),
        elapsed_ms,
        nodes: stats.nodes,
        propagations: stats.propagations,
        backtracks: stats.backtracks,
        best_depth, solved,
        nodes_per_sec: nps,
    }
}

fn run_pt_cell(size: u32, colors: u32, seed: u64, budget_ms: u64) -> PtResult {
    let puzzle = generate(GeneratorConfig { size, interior_colors: colors, seed })
        .expect("generator must succeed");
    let cfg = PtConfig {
        n_replicas: 8,
        t_min: 0.05,
        t_max: 2.0,
        inner_iters: 5_000,
        max_rounds: 0,
        time_budget_ms: budget_ms,
        seed,
        verbose: false,
        greedy_fill: false,
        ..PtConfig::default()
    };
    let started = Instant::now();
    let (outcome, stats) = run_pt(&puzzle, &cfg);
    let elapsed_ms = started.elapsed().as_millis() as u64;
    let total_iters = stats.rounds * cfg.inner_iters * (cfg.n_replicas as u64);
    let ips = if elapsed_ms > 0 { (total_iters as f64) * 1000.0 / (elapsed_ms as f64) } else { 0.0 };
    PtResult {
        size, colors, seed,
        elapsed_ms,
        rounds: stats.rounds,
        inner_iters_per_round: cfg.inner_iters,
        n_replicas: cfg.n_replicas,
        best_score: outcome.best_score,
        total_edges: outcome.total_edges,
        iters_per_sec: ips,
    }
}

fn main() {
    let (out, label, budget_ms, quick) = parse_args();
    eprintln!("== fleet harness ==");
    eprintln!("label: {label}");
    eprintln!("budget: {budget_ms} ms / cell");
    eprintln!("cpu: {}", cpu_brand());
    eprintln!("RUSTFLAGS at build: {}", rustflags_at_build());

    // Workload definition: (size, colors, seed)
    //   8x8  → 5 colors  (Mariner et al. generator difficulty band)
    //   9x9  → 5 colors
    //  10x10 → 6 colors
    //  11x11 → 6 colors
    //  12x12 → 7 colors
    // Two seeds per size keep the matrix small while showing seed variance.
    let cells: &[(u32, u32, u64)] = if quick {
        &[(8, 5, 1), (10, 6, 1)]
    } else {
        &[
            (8, 5, 1), (8, 5, 2),
            (9, 5, 1), (9, 5, 2),
            (10, 6, 1), (10, 6, 2),
            (11, 6, 1), (11, 6, 2),
            (12, 7, 1), (12, 7, 2),
        ]
    };

    let mut engine_results = Vec::with_capacity(cells.len());
    for &(size, colors, seed) in cells {
        eprint!("[engine] {size}x{size} c={colors} seed={seed} … ");
        let r = run_engine_cell(size, colors, seed, budget_ms);
        eprintln!("{} in {:>5} ms (depth {})",
            if r.solved { "SOLVED" } else { "to/exh" }, r.elapsed_ms, r.best_depth);
        engine_results.push(r);
    }

    // PT: just one cell at 10x10 (representative). Reuse seeds 1.
    let mut pt_results = Vec::new();
    eprint!("[pt]    10x10 c=6 seed=1 … ");
    let r = run_pt_cell(10, 6, 1, budget_ms);
    eprintln!("score {}/{} in {} ms ({:.0} iters/s)",
        r.best_score, r.total_edges, r.elapsed_ms, r.iters_per_sec);
    pt_results.push(r);

    let report = FleetReport {
        label,
        cpu_brand: cpu_brand(),
        rustflags: rustflags_at_build(),
        profile: cargo_profile_at_build(),
        budget_ms,
        engine: engine_results,
        pt: pt_results,
    };
    let json = serde_json::to_string_pretty(&report).expect("serialize");
    std::fs::write(&out, &json).expect("write json");
    eprintln!("wrote {}", out.display());
}
