// Vol-26 — invoke the engine on each puzzle in a JSONL test set under
// either the MRV baseline (`--mode mrv`) or the learned value-order
// (`--mode learned`), then emit one JSON result per puzzle to stdout.
//
// Used by `ml/evaluate.py`. The Python evaluator parses these results
// and computes the three gate conditions.

#![forbid(unsafe_code)]

use std::fs::File;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::time::Instant;

use eternity2_core::{Edges, Piece, Puzzle};
use eternity2_events::{EventBody, EventSink, SolverEvent};
use eternity2_solver_engine::{EngineConfig, EngineSolver, ValueOrder};
use eternity2_solver_trait::{SolveMode, SolveOpts, Solver};
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
struct PuzzleRecord {
    seed: u64,
    size: u32,
    color_count: u32,
    pieces: Vec<PieceWire>,
    // canonical_solution + expert_trajectory are present in the JSONL but
    // we don't need them here — serde quietly drops unknown fields.
    #[serde(default)]
    #[allow(dead_code)]
    canonical_solution: serde_json::Value,
    #[serde(default)]
    #[allow(dead_code)]
    expert_trajectory: serde_json::Value,
}

#[derive(Deserialize)]
struct PieceWire {
    id: u16,
    edges: [u8; 4],
}

#[derive(Serialize)]
struct Result {
    seed: u64,
    solved: bool,
    nodes: u64,
    backtracks: u64,
    elapsed_ms: u64,
}

struct StatsSink {
    nodes: u64,
    backtracks: u64,
    solved: bool,
}

impl EventSink for StatsSink {
    fn emit(&mut self, e: SolverEvent) {
        match e.body {
            EventBody::Solved { final_stats, .. } => {
                self.nodes = final_stats.nodes;
                self.backtracks = final_stats.backtracks;
                self.solved = true;
            }
            EventBody::Exhausted { final_stats, .. }
            | EventBody::TimedOut { final_stats, .. }
            | EventBody::Cancelled { final_stats, .. } => {
                self.nodes = final_stats.nodes;
                self.backtracks = final_stats.backtracks;
            }
            _ => {}
        }
    }
}

fn build_puzzle(rec: &PuzzleRecord) -> Puzzle {
    let pieces: Vec<Piece> = rec.pieces.iter().map(|p| {
        Piece::new(p.id, Edges::new(p.edges[0], p.edges[1], p.edges[2], p.edges[3]))
    }).collect();
    Puzzle::new(rec.size, rec.size, rec.color_count, pieces).expect("puzzle from wire")
}

fn run_one(rec: &PuzzleRecord, value_order: ValueOrder, budget_ms: u64) -> Result {
    let puz = build_puzzle(rec);
    let mut cfg = EngineConfig::BORDER_FIRST_LCV;
    cfg.value_order = value_order;
    let mut solver = EngineSolver::new(cfg, "engine", "bench_eval");
    let opts = SolveOpts {
        mode: SolveMode::FirstSolution,
        seed: rec.seed,
        time_budget_ms: budget_ms,
        ..SolveOpts::default()
    };
    let mut sink = StatsSink { nodes: 0, backtracks: 0, solved: false };
    let t0 = Instant::now();
    let _ = solver.solve(&puz, &opts, &mut sink);
    let elapsed_ms = t0.elapsed().as_millis() as u64;
    Result { seed: rec.seed, solved: sink.solved, nodes: sink.nodes, backtracks: sink.backtracks, elapsed_ms }
}

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut mode = "mrv".to_string();
    let mut in_path = PathBuf::from("ml/data/test_6x6_5c.jsonl");
    let mut budget_ms: u64 = 5_000;
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--mode" => { mode = raw[i + 1].clone(); i += 2; }
            "--in" => { in_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--budget-ms" => { budget_ms = raw[i + 1].parse().expect("budget parse"); i += 2; }
            other => panic!("unknown arg: {other}"),
        }
    }
    let value_order = match mode.as_str() {
        "mrv" => ValueOrder::LeastConstraining,
        "insertion" => ValueOrder::InsertionOrder,
        "learned" => ValueOrder::Learned,
        other => panic!("unknown mode: {other}"),
    };

    let f = File::open(&in_path).expect("open in");
    let mut stdout = std::io::stdout().lock();
    for line in BufReader::new(f).lines() {
        let line = line.expect("readline");
        if line.trim().is_empty() { continue; }
        let rec: PuzzleRecord = serde_json::from_str(&line).expect("parse puzzle");
        let r = run_one(&rec, value_order, budget_ms);
        serde_json::to_writer(&mut stdout, &r).expect("write result");
        writeln!(stdout).expect("nl");
    }
}
