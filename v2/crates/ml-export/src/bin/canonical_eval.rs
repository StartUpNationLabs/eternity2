// Vol-28 — measure cold-start depth/nodes on canonical 5-clue 16x16
// Eternity II using the requested ValueOrder, with the canonical 5 hints.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_events::{EventBody, EventSink, SolverEvent};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineConfig, EngineSolver, ValueOrder};
use eternity2_solver_trait::{SolveMode, SolveOpts, Solver};

struct Sink {
    nodes: u64,
    backtracks: u64,
    max_depth: u32,
    solved: bool,
}

impl EventSink for Sink {
    fn emit(&mut self, e: SolverEvent) {
        match e.body {
            EventBody::Solved { final_stats, .. } => {
                self.nodes = final_stats.nodes;
                self.backtracks = final_stats.backtracks;
                self.max_depth = final_stats.max_depth_seen;
                self.solved = true;
            }
            EventBody::Exhausted { final_stats, .. }
            | EventBody::TimedOut { final_stats, .. }
            | EventBody::Cancelled { final_stats, .. } => {
                self.nodes = final_stats.nodes;
                self.backtracks = final_stats.backtracks;
                self.max_depth = final_stats.max_depth_seen;
            }
            _ => {}
        }
    }
}

fn main() {
    let mut mode = "mrv".to_string();
    let mut profile = "border_first_lcv".to_string();
    let mut budget_ms: u64 = 30_000;
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--mode" => { mode = raw[i + 1].clone(); i += 2; }
            "--profile" => { profile = raw[i + 1].clone(); i += 2; }
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget parse"); i += 2; }
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--bp-path" => { bp_path = PathBuf::from(&raw[i + 1]); i += 2; }
            other => panic!("unknown arg: {other}"),
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eprintln!("loaded {}x{} canonical E2, profile={}, mode={}, budget_ms={}",
        puzzle.width, puzzle.height, profile, mode, budget_ms);

    // Pick the base profile.
    let mut cfg = match profile.as_str() {
        "border_first_lcv" => EngineConfig::BORDER_FIRST_LCV,
        "joe_depth150_bp" => EngineConfig::JOE_DEPTH150_BP,
        other => panic!("unknown profile: {other}. valid: border_first_lcv, joe_depth150_bp"),
    };

    // Override value-order with the mode setting. Note that some profiles
    // (e.g. joe_depth150_bp) bake EdgeBpMarginals in; switching to
    // `learned` overrides that. mode=default keeps the profile's order.
    let value_order = match mode.as_str() {
        "default" => cfg.value_order,
        "mrv" => ValueOrder::LeastConstraining,
        "insertion" => ValueOrder::InsertionOrder,
        "learned" => ValueOrder::Learned,
        "edge_bp" => ValueOrder::EdgeBpMarginals,
        other => panic!("unknown mode: {other}"),
    };
    cfg.value_order = value_order;
    // Force single-thread for clean A/B (some profiles default to RootSplit).
    cfg.parallelism = eternity2_solver_engine::Parallelism::SingleThread;

    let mut solver = EngineSolver::new(cfg, "engine", "canonical_eval");
    let mut opts = SolveOpts {
        mode: SolveMode::FirstSolution,
        hints,
        seed: 1,
        time_budget_ms: budget_ms,
        ..SolveOpts::default()
    };
    // If using EdgeBpMarginals load the BP file.
    if matches!(value_order, ValueOrder::EdgeBpMarginals) {
        if let Ok(bp) = load_edge_bp_marginals(&bp_path) {
            opts.edge_bp_marginals = Some(bp);
        } else {
            eprintln!("warning: --bp-path {} not found; EdgeBpMarginals will fall back to InsertionOrder", bp_path.display());
        }
    }

    let mut sink = Sink { nodes: 0, backtracks: 0, max_depth: 0, solved: false };
    let t0 = Instant::now();
    let _ = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed().as_millis() as u64;

    println!(
        "{{\"profile\":\"{}\",\"mode\":\"{}\",\"budget_ms\":{},\"elapsed_ms\":{},\"solved\":{},\"nodes\":{},\"backtracks\":{},\"max_depth\":{}}}",
        profile, mode, budget_ms, elapsed, sink.solved, sink.nodes, sink.backtracks, sink.max_depth,
    );
}
