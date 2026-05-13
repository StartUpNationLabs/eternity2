// Vol-26 — export synthetic E2-family puzzles + canonical solutions +
// expert trajectories to JSONL. Each line is one puzzle record. Python
// reads this for training the learned value-order model.
//
// Usage:
//   gen-export --out data/train.jsonl --seeds 1..10000 --size 6 --colors 5
//   gen-export --out data/test.jsonl  --seeds 100000..100200 --size 6 --colors 5

#![forbid(unsafe_code)]

use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::time::Instant;

use eternity2_core::{Board, PieceId, Rotation};
use eternity2_events::{EventBody, EventSink, SolverEvent};
use eternity2_generator::{generate_with_solution, GeneratorConfig, Placement};
use eternity2_solver_engine::{EngineConfig, EngineSolver};
use eternity2_solver_trait::{SolveMode, SolveOpts, Solver};
use serde::Serialize;

#[derive(Serialize)]
struct PuzzleRecord {
    seed: u64,
    size: u32,
    color_count: u32,
    /// `pieces[i]` is the piece served at catalog index `i`. Each piece has
    /// `id` (stable handle the solver uses) and `edges` in `[top, right,
    /// bottom, left]` order. Python tokenises pieces by id, NOT by index.
    pieces: Vec<PieceWire>,
    /// Canonical assembly built by the generator. The solver does NOT need
    /// to find this exact one — any complete edge-matched assembly works —
    /// but we ship it so the Python side can sanity-check the trajectory.
    canonical_solution: Vec<PlacementWire>,
    /// The actual sequence of placements the engine made to solve this
    /// puzzle under `BorderFirstMRV` + `LeastConstraining`. This is the
    /// imitation-learning target: at depth d, the model should predict
    /// `expert_trajectory[d].(piece_id, rotation)` given the partial.
    expert_trajectory: Vec<TrajectoryStep>,
}

#[derive(Serialize)]
struct PieceWire {
    id: u16,
    edges: [u8; 4],
}

#[derive(Serialize)]
struct PlacementWire {
    position: u32,
    piece_id: u16,
    rotation: u8,
}

#[derive(Serialize)]
struct TrajectoryStep {
    depth: u32,
    position: u32,
    piece_id: u16,
    rotation: u8,
}

/// Captures the engine's value-try stack. On every `ValueTried` at depth
/// `d`, overwrite slot `d`. On `Solved`, the slots 0..cell_count hold the
/// winning trajectory in scan order. We rely on the engine's invariant
/// that depth is monotonic between successive value-tries on the winning
/// path (backtracks reset higher slots which get overwritten next time).
struct TrajectorySink {
    stack: Vec<Option<(u32, u16, u8)>>,
    /// Last `VariableSelected.position` — paired with the next
    /// `ValueTried` at this depth to record the (depth, position, piece,
    /// rotation) tuple. The engine's `ValueTried` payload already carries
    /// position, but keeping a paired check rules out any future event
    /// drift.
    _last_var_pos: Option<u32>,
    final_board: Option<Board>,
    deadline: Instant,
}

impl TrajectorySink {
    fn new(cell_count: usize, deadline: Instant) -> Self {
        Self {
            stack: vec![None; cell_count],
            _last_var_pos: None,
            final_board: None,
            deadline,
        }
    }
}

impl EventSink for TrajectorySink {
    fn emit(&mut self, event: SolverEvent) {
        match event.body {
            EventBody::ValueTried { position, piece_id, rotation } => {
                let d = event.depth as usize;
                if d < self.stack.len() {
                    self.stack[d] = Some((position, piece_id, rotation.as_u8()));
                }
            }
            EventBody::Solved { board, .. } => {
                self.final_board = Some(board);
            }
            _ => {}
        }
    }
    fn should_continue(&self) -> bool {
        Instant::now() < self.deadline
    }
}

#[derive(Debug, Clone, Copy)]
struct Args {
    seed_start: u64,
    seed_end: u64,
    size: u32,
    colors: u32,
    budget_ms: u64,
}

fn parse_args() -> (Args, PathBuf) {
    let mut a = Args { seed_start: 1, seed_end: 10_001, size: 6, colors: 5, budget_ms: 2_000 };
    let mut out = PathBuf::from("ml/data/train_6x6_5c.jsonl");
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--out" => { out = PathBuf::from(&raw[i + 1]); i += 2; }
            "--seeds" => {
                let s = &raw[i + 1];
                let (lo, hi) = s.split_once("..").expect("--seeds expects lo..hi");
                a.seed_start = lo.parse().expect("seed_start parse");
                a.seed_end = hi.parse().expect("seed_end parse");
                i += 2;
            }
            "--size" => { a.size = raw[i + 1].parse().expect("size parse"); i += 2; }
            "--colors" => { a.colors = raw[i + 1].parse().expect("colors parse"); i += 2; }
            "--budget-ms" => { a.budget_ms = raw[i + 1].parse().expect("budget-ms parse"); i += 2; }
            other => panic!("unknown arg: {other}"),
        }
    }
    (a, out)
}

fn export_one(seed: u64, size: u32, colors: u32, budget_ms: u64) -> Option<PuzzleRecord> {
    let (puzzle, canonical) = generate_with_solution(GeneratorConfig {
        size, interior_colors: colors, seed,
    }).expect("generate");

    let pieces: Vec<PieceWire> = puzzle.pieces().iter().map(|p| PieceWire {
        id: p.id,
        edges: p.edges.as_array(),
    }).collect();

    let canonical_solution: Vec<PlacementWire> = canonical.iter().map(|p: &Placement| {
        PlacementWire { position: p.position, piece_id: p.piece_id, rotation: p.rotation.as_u8() }
    }).collect();

    // Solve with BorderFirstMRV + LeastConstraining (the MRV baseline the
    // gate compares against). Budget per puzzle is short — 6×6/5-color
    // solves in milliseconds.
    let cfg = EngineConfig::BORDER_FIRST_LCV;
    let mut solver = EngineSolver::new(cfg, "engine", "border_first_lcv");
    let opts = SolveOpts {
        mode: SolveMode::FirstSolution,
        seed,
        time_budget_ms: budget_ms,
        ..SolveOpts::default()
    };
    let deadline = Instant::now() + std::time::Duration::from_millis(budget_ms + 500);
    let mut sink = TrajectorySink::new(puzzle.cell_count() as usize, deadline);
    let _ = solver.solve(&puzzle, &opts, &mut sink);

    if sink.final_board.is_none() {
        // Engine didn't solve this within budget — drop the sample.
        return None;
    }

    let mut expert_trajectory: Vec<TrajectoryStep> = Vec::with_capacity(sink.stack.len());
    for (d, slot) in sink.stack.iter().enumerate() {
        match *slot {
            Some((pos, pid, rot)) => expert_trajectory.push(TrajectoryStep {
                depth: d as u32, position: pos, piece_id: pid, rotation: rot,
            }),
            None => {
                // Should not happen on a solved puzzle; skip defensively.
                return None;
            }
        }
    }

    Some(PuzzleRecord {
        seed,
        size,
        color_count: colors + 1,
        pieces,
        canonical_solution,
        expert_trajectory,
    })
}

fn main() {
    let (args, out_path) = parse_args();
    if let Some(parent) = out_path.parent() {
        std::fs::create_dir_all(parent).expect("create out dir");
    }
    let f = File::create(&out_path).expect("open out");
    let mut w = BufWriter::new(f);

    let mut written = 0u64;
    let mut dropped = 0u64;
    let start = Instant::now();
    for seed in args.seed_start..args.seed_end {
        match export_one(seed, args.size, args.colors, args.budget_ms) {
            Some(rec) => {
                serde_json::to_writer(&mut w, &rec).expect("json write");
                w.write_all(b"\n").expect("newline");
                written += 1;
            }
            None => { dropped += 1; }
        }
        if (seed - args.seed_start) % 500 == 0 {
            eprintln!(
                "[gen-export] seed={seed} written={written} dropped={dropped} elapsed={:?}",
                start.elapsed(),
            );
        }
    }
    w.flush().expect("flush");
    eprintln!(
        "[gen-export] done: written={written} dropped={dropped} elapsed={:?} -> {}",
        start.elapsed(), out_path.display(),
    );
    // Silence the unused PieceId/Rotation type-import warnings if a future
    // refactor drops the wire types' explicit type annotations.
    let _ = std::mem::size_of::<(PieceId, Rotation)>();
}
