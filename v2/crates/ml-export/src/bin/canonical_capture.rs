// Vol-29 T1a — capture canonical-E2 cold-start expert trajectories for
// ML training. Runs `joe_depth150_bp` for N seeds with a per-seed time
// budget; emits one JSONL record per seed with:
//   - seed
//   - max_depth, nodes, backtracks, solved (final stats from the run)
//   - placements: [{depth, position, piece_id, rotation}]  (the winning
//     prefix the engine committed to, depth 0..max_depth)
//
// Vol-28 lesson: training distribution must match inference distribution.
// We capture from the SAME engine profile we'll later deploy Learned in,
// so the partial-board distribution matches.

#![forbid(unsafe_code)]

use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_events::{EventBody, EventSink, SolverEvent};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineConfig, EngineSolver, Parallelism, ValueOrder, VariableOrder};
use eternity2_solver_trait::{SolveMode, SolveOpts, Solver};
use serde::Serialize;

#[derive(Serialize)]
struct TrajectoryStep {
    depth: u32,
    position: u32,
    piece_id: u16,
    rotation: u8,
}

#[derive(Serialize)]
struct SeedRecord {
    seed: u64,
    max_depth: u32,
    nodes: u64,
    backtracks: u64,
    solved: bool,
    placements: Vec<TrajectoryStep>,
}

struct CaptureSink {
    stack: Vec<Option<(u32, u16, u8)>>,
    nodes: u64,
    backtracks: u64,
    max_depth: u32,
    solved: bool,
    deadline: Instant,
}

impl EventSink for CaptureSink {
    fn emit(&mut self, e: SolverEvent) {
        match e.body {
            EventBody::ValueTried { position, piece_id, rotation } => {
                let d = e.depth as usize;
                if d < self.stack.len() {
                    self.stack[d] = Some((position, piece_id, rotation.as_u8()));
                }
                if e.depth > self.max_depth {
                    self.max_depth = e.depth;
                }
            }
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
    fn should_continue(&self) -> bool {
        Instant::now() < self.deadline
    }
}

fn main() {
    let mut out = PathBuf::from("ml/data/canonical_trajectories.jsonl");
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");
    let mut seed_start: u64 = 1;
    let mut seed_end: u64 = 21;  // exclusive
    let mut budget_ms: u64 = 30_000;
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--out" => { out = PathBuf::from(&raw[i + 1]); i += 2; }
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--bp-path" => { bp_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--seeds" => {
                let s = &raw[i + 1];
                let (lo, hi) = s.split_once("..").expect("--seeds expects lo..hi");
                seed_start = lo.parse().expect("seed_start");
                seed_end = hi.parse().expect("seed_end");
                i += 2;
            }
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget"); i += 2; }
            other => panic!("unknown arg: {other}"),
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let n_cells = puzzle.cell_count() as usize;
    eprintln!(
        "loaded {}x{} canonical E2; seeds {}..{} budget {} ms; out={}",
        puzzle.width, puzzle.height, seed_start, seed_end, budget_ms, out.display(),
    );

    let bp = match load_edge_bp_marginals(&bp_path) {
        Ok(b) => Some(b),
        Err(e) => {
            eprintln!("warning: bp_path missing ({e}); joe_depth150_bp will fall back to InsertionOrder");
            None
        }
    };

    if let Some(parent) = out.parent() {
        std::fs::create_dir_all(parent).expect("mkdir");
    }
    let f = File::create(&out).expect("open out");
    let mut w = BufWriter::new(f);

    for seed in seed_start..seed_end {
        let mut cfg = EngineConfig::JOE_DEPTH150_BP;
        cfg.parallelism = Parallelism::SingleThread;
        cfg.value_order = ValueOrder::EdgeBpMarginals;
        // Vol-29 — keep BorderFirstMrv (deep partials reach depth 165 in
        // 60s). Seeds give nearly-identical trajectories so the training
        // data has limited diversity, but each seed contributes ~165
        // distinct partial-board states. Diversity from MRV tie-breaks
        // + small AC-3 nondeterminism is enough for ~3300 unique
        // samples per capture. If overfitting is observed, switch to
        // BorderFirstRandom for diversity at the cost of trajectory
        // depth (50 vs 165).

        let mut solver = EngineSolver::new(cfg, "engine", "canonical_capture");
        let opts = SolveOpts {
            mode: SolveMode::FirstSolution,
            hints: hints.clone(),
            seed,
            time_budget_ms: budget_ms,
            edge_bp_marginals: bp.clone(),
            ..SolveOpts::default()
        };
        let t0 = Instant::now();
        let deadline = t0 + std::time::Duration::from_millis(budget_ms + 1_000);
        let mut sink = CaptureSink {
            stack: vec![None; n_cells],
            nodes: 0, backtracks: 0, max_depth: 0, solved: false,
            deadline,
        };
        let _ = solver.solve(&puzzle, &opts, &mut sink);
        let elapsed = t0.elapsed().as_millis() as u64;

        // Extract the winning prefix: the stack indexed 0..max_depth (the
        // last commit at each depth before the time budget expired). On
        // backtrack the engine overwrites stack[d]; the final values are
        // the deepest committed lineage.
        let mut placements = Vec::with_capacity(sink.max_depth as usize);
        for (d, slot) in sink.stack.iter().enumerate() {
            if (d as u32) >= sink.max_depth { break; }
            if let Some((pos, pid, rot)) = *slot {
                placements.push(TrajectoryStep {
                    depth: d as u32, position: pos, piece_id: pid, rotation: rot,
                });
            }
        }

        let rec = SeedRecord {
            seed,
            max_depth: sink.max_depth,
            nodes: sink.nodes,
            backtracks: sink.backtracks,
            solved: sink.solved,
            placements,
        };
        serde_json::to_writer(&mut w, &rec).expect("write");
        w.write_all(b"\n").expect("nl");
        w.flush().expect("flush per-seed");
        eprintln!(
            "[capture] seed={seed} elapsed_ms={elapsed} max_depth={} nodes={} backtracks={}",
            sink.max_depth, sink.nodes, sink.backtracks,
        );
    }
    w.flush().expect("flush");
    eprintln!("[capture] done -> {}", out.display());
}
