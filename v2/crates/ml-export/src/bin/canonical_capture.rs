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
use std::sync::Mutex;
use std::time::Instant;

use rayon::iter::{IntoParallelIterator, ParallelIterator};

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
    let mut parallel: usize = 1;
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
            "--parallel" => { parallel = raw[i + 1].parse().expect("parallel"); i += 2; }
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
    let writer = Mutex::new(BufWriter::new(File::create(&out).expect("open out")));

    let run_seed = |seed: u64| -> SeedRecord {
        let mut cfg = EngineConfig::JOE_DEPTH150_BP;
        cfg.parallelism = Parallelism::SingleThread;
        cfg.value_order = ValueOrder::EdgeBpMarginals;
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

        let mut placements = Vec::with_capacity(sink.max_depth as usize);
        for (d, slot) in sink.stack.iter().enumerate() {
            if (d as u32) >= sink.max_depth { break; }
            if let Some((pos, pid, rot)) = *slot {
                placements.push(TrajectoryStep {
                    depth: d as u32, position: pos, piece_id: pid, rotation: rot,
                });
            }
        }
        eprintln!(
            "[capture] seed={seed} elapsed_ms={elapsed} max_depth={} nodes={} backtracks={}",
            sink.max_depth, sink.nodes, sink.backtracks,
        );
        SeedRecord {
            seed,
            max_depth: sink.max_depth,
            nodes: sink.nodes,
            backtracks: sink.backtracks,
            solved: sink.solved,
            placements,
        }
    };

    let seeds: Vec<u64> = (seed_start..seed_end).collect();
    if parallel <= 1 {
        for seed in seeds {
            let rec = run_seed(seed);
            let mut w = writer.lock().unwrap();
            serde_json::to_writer(&mut *w, &rec).expect("write");
            w.write_all(b"\n").expect("nl");
            w.flush().expect("flush per-seed");
        }
    } else {
        // Rayon pool sized to `parallel`. Engines are single-thread, so
        // each worker pegs one core; expect near-linear speedup until
        // we hit the M1's 4 performance cores. Beyond that, gains
        // taper (efficiency cores are slower).
        rayon::ThreadPoolBuilder::new()
            .num_threads(parallel)
            .build()
            .expect("rayon pool")
            .install(|| {
                seeds.into_par_iter().for_each(|seed| {
                    let rec = run_seed(seed);
                    let mut w = writer.lock().unwrap();
                    serde_json::to_writer(&mut *w, &rec).expect("write");
                    w.write_all(b"\n").expect("nl");
                    w.flush().expect("flush per-seed");
                });
            });
    }
    writer.lock().unwrap().flush().expect("flush");
    eprintln!("[capture] done -> {}", out.display());
}
