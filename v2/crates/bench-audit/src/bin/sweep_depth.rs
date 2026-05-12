// Vol-12 depth-threshold sweep on canonical E2.
//
// For each depth-threshold T in a configurable set (default {0, 100, 150, 180}),
// runs EngineConfig::JOE_DEPTH150 with `depth_threshold_for_propagators = Some(T)`
// (or None at T=0 → propagators always run) on canonical E2 (16×16, 5 hints) for
// `--budget-ms` milliseconds and records nodes/sec + max_depth.
//
// Output: JSON with one record per (threshold, seed) pair.

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit as _;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_solver_engine::{EngineConfig, EngineSolver};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
struct SweepCell {
    threshold: i64, // -1 == None (always run)
    multiset_equality: bool,
    seed: u64,
    elapsed_ms: u64,
    nodes: u64,
    propagations: u64,
    backtracks: u64,
    max_depth_seen: u32,
    best_depth: u32,
    nodes_per_sec: f64,
    propagations_per_node: f64,
    solved: bool,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct SweepReport {
    label: String,
    puzzle: String,
    budget_ms: u64,
    cells: Vec<SweepCell>,
}

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

fn parse_args() -> (PathBuf, PathBuf, String, u64, Vec<i64>, Vec<u64>, bool, bool) {
    let mut args = std::env::args().skip(1);
    let mut puzzle = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut out = PathBuf::from("output/v12_bench/sweep.json");
    let mut label = "sweep".to_string();
    let mut budget_ms: u64 = 60_000;
    let mut thresholds: Vec<i64> = vec![-1, 100, 150, 180];
    let mut seeds: Vec<u64> = vec![1];
    let mut use_hints = true;
    let mut parallel = false;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle = PathBuf::from(args.next().expect("--puzzle PATH")),
            "--out" => out = PathBuf::from(args.next().expect("--out PATH")),
            "--label" => label = args.next().expect("--label NAME"),
            "--budget-ms" => budget_ms = args.next().expect("--budget-ms MS").parse().expect("int"),
            "--thresholds" => {
                thresholds = args.next().expect("--thresholds csv").split(',')
                    .map(|s| s.parse::<i64>().expect("int")).collect();
            }
            "--seeds" => {
                seeds = args.next().expect("--seeds csv").split(',')
                    .map(|s| s.parse::<u64>().expect("u64")).collect();
            }
            "--no-hints" => use_hints = false,
            "--parallel" => parallel = true,
            other => panic!("unknown arg: {other}"),
        }
    }
    (puzzle, out, label, budget_ms, thresholds, seeds, use_hints, parallel)
}

fn run_cell(
    puzzle: &eternity2_core::Puzzle,
    hints: eternity2_core::Hints,
    threshold: i64,
    multiset_equality: bool,
    seed: u64,
    budget_ms: u64,
    parallel: bool,
) -> SweepCell {
    let mut cfg = if parallel {
        EngineConfig::GACOLOR_AC3_PAR
    } else {
        EngineConfig::GACOLOR_AC3
    };
    cfg.propagators.multiset_equality = multiset_equality;
    cfg.propagators.depth_threshold = if threshold < 0 { None } else { Some(threshold as u32) };
    let mut solver = EngineSolver::new(cfg, "engine", "sweep_depth");
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = seed;
    opts.hints = hints;
    let mut sink = StatsOnlySink { final_stats: None };
    let started = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let elapsed_ms = started.elapsed().as_millis() as u64;
    let stats = sink.final_stats.unwrap_or_default();
    let (solved, best_depth) = match &outcome {
        SolveOutcome::Solved(_) => (true, puzzle.cell_count()),
        SolveOutcome::Exhausted => (false, stats.max_depth_seen),
        SolveOutcome::TimedOut { best_depth, .. } => (false, *best_depth),
        SolveOutcome::Cancelled { best_depth, .. } => (false, *best_depth),
        SolveOutcome::AllSolutions(b) => (!b.is_empty(), puzzle.cell_count()),
        SolveOutcome::Error(_) => (false, 0),
    };
    let nps = if elapsed_ms > 0 { (stats.nodes as f64) * 1000.0 / (elapsed_ms as f64) } else { 0.0 };
    let ppn = if stats.nodes > 0 { stats.propagations as f64 / stats.nodes as f64 } else { 0.0 };
    SweepCell {
        threshold,
        multiset_equality,
        seed,
        elapsed_ms,
        nodes: stats.nodes,
        propagations: stats.propagations,
        backtracks: stats.backtracks,
        max_depth_seen: stats.max_depth_seen,
        best_depth,
        nodes_per_sec: nps,
        propagations_per_node: ppn,
        solved,
    }
}

fn main() {
    let (puzzle_path, out, label, budget_ms, thresholds, seeds, use_hints, parallel) = parse_args();
    eprintln!("== vol-12 depth-threshold sweep ==");
    eprintln!("label: {label}");
    eprintln!("puzzle: {}", puzzle_path.display());
    eprintln!("budget: {budget_ms} ms / cell");
    eprintln!("thresholds: {:?}", thresholds);
    eprintln!("seeds: {:?}", seeds);
    eprintln!("hints: {}  parallel: {}", use_hints, parallel);

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let used_hints = if use_hints { hints } else { eternity2_core::Hints::new(vec![]) };
    eprintln!(
        "loaded: {}x{} colors={} hints={}",
        puzzle.width, puzzle.height, puzzle.color_count - 1, used_hints.hints.len()
    );

    let mut cells: Vec<SweepCell> = Vec::new();
    for &t in &thresholds {
        for me in [false, true] {
            for &seed in &seeds {
                eprint!("[t={t} me={me} seed={seed}] ");
                let cell = run_cell(&puzzle, used_hints.clone(), t, me, seed, budget_ms, parallel);
                eprintln!(
                    "depth={} nodes={} nps={:.0} ppn={:.1} bt={} solved={}",
                    cell.best_depth, cell.nodes, cell.nodes_per_sec,
                    cell.propagations_per_node, cell.backtracks, cell.solved,
                );
                cells.push(cell);
            }
        }
    }

    let report = SweepReport {
        label,
        puzzle: puzzle_path.display().to_string(),
        budget_ms,
        cells,
    };
    if let Some(parent) = out.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let json = serde_json::to_string_pretty(&report).expect("serialize");
    std::fs::write(&out, &json).expect("write json");
    eprintln!("wrote {}", out.display());
}
