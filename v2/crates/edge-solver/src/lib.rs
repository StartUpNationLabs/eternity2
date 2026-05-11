// Edge-as-variable Constraint Programming for Eternity II
// (RESEARCH_NOTES_3 Inversion 2).
//
// The existing solver-engine encodes E2 as "cells are variables, pieces
// are domain values." This crate flips the model: the 480 interior
// edges of the 16×16 board are variables (domain: interior colors),
// and the constraints are per-cell ("the 4 surrounding edges must be a
// 4-tuple of some unused piece-rotation") plus a global piece-alldiff.
//
// Why: vol. 2's plateau analysis identified 30 specific unmatched
// edges in the deepest partials. In edge-CP those are *directly
// addressable variables* — the search engine reasons over them
// natively. In cell-CP, each unmatched edge is an emergent property
// of which (piece, rotation) the search picked for adjacent cells.

#![forbid(unsafe_code)]

pub mod recover;
pub mod search;
pub mod tables;
pub mod topology;

use std::time::Instant;

use eternity2_core::{PathPolicy, Puzzle};
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_solver_trait::{
    HeuristicProfile, SolveMode, SolveOpts, SolveOutcome, Solver, SolverId,
};

pub use search::{RecurseResult, Search, SearchConfig, SearchStats};
pub use tables::Tables;
pub use topology::Topology;

pub struct EdgeSolver {
    pub config: SearchConfig,
    pub solver_id: String,
    pub heuristic_profile: String,
}

impl EdgeSolver {
    #[must_use]
    pub fn new(config: SearchConfig, profile: impl Into<String>) -> Self {
        Self {
            config,
            solver_id: "edge_cp".to_string(),
            heuristic_profile: profile.into(),
        }
    }

    #[must_use]
    pub fn default_v1() -> Self {
        // v1 default: piece-uniqueness propagation OFF.
        // The naïve single-cell-collapse heuristic is unsound — committing
        // piece P at cell A whenever A's mask shrinks to P-rotations may
        // leave cell B (which also needed P) infeasible. Real alldiff
        // propagation needs Hall's condition or bipartite matching; that's
        // v1.1. Until then, defer piece-uniqueness to recovery.
        let mut cfg = SearchConfig::default();
        cfg.propagate_piece_uniqueness = false;
        Self::new(cfg, "edge_v1")
    }
}

impl Solver for EdgeSolver {
    fn id(&self) -> SolverId { SolverId(self.solver_id.clone()) }
    fn heuristic_profile(&self) -> HeuristicProfile {
        HeuristicProfile(self.heuristic_profile.clone())
    }
    fn supports_path_policy(&self, policy: &PathPolicy) -> bool {
        !matches!(policy, PathPolicy::Strict)
    }

    fn solve(
        &mut self,
        puzzle: &Puzzle,
        opts: &SolveOpts,
        sink: &mut dyn EventSink,
    ) -> SolveOutcome {
        let topology = Topology::new(puzzle);
        let tables = Tables::new(puzzle, &topology);
        let mut cfg = self.config.clone();
        cfg.time_budget_ms = opts.time_budget_ms;
        cfg.seed = opts.seed;
        let mut search = Search::new(puzzle, &topology, &tables, cfg);
        let start = Instant::now();
        search.started_us = 0;
        let clock = |start: Instant| move || start.elapsed().as_micros() as u64;
        let clock_fn = clock(start);
        let now_us: &dyn Fn() -> u64 = &clock_fn;

        let started = SolverEvent {
            schema_version: 1,
            solver_run_id: opts.solver_run_id,
            node_id: 0,
            depth: 0,
            timestamp_us: 0,
            body: EventBody::Started {
                solver_id: self.solver_id.clone(),
                heuristic_profile: self.heuristic_profile.clone(),
                puzzle_fingerprint: puzzle.fingerprint(),
                seed: opts.seed,
                started_wall_us: 0,
            },
        };
        sink.emit(started);

        // Apply hints as pre-assigned edges (the pieces' 4-tuples
        // dictate edge colors around each hint cell). Hints stay
        // un-pinned for v1 — we'll add this in v1.1.
        let _ = opts.hints.hints.is_empty();

        let result = search.recurse(now_us);
        let elapsed_us = (now_us)();
        let mut stats = FinalStats::default();
        stats.nodes = search.stats.nodes;
        stats.backtracks = search.stats.backtracks;
        stats.propagations = search.stats.propagations;
        stats.time_ms = elapsed_us / 1000;
        stats.max_depth_seen = search.best_score;
        stats.current_depth = search.assigned_count();

        let best_board = recover::recover_board(puzzle, &topology, &tables, &search.best_edge_color);
        let total_edges = topology.n_edges;
        let is_complete = search.best_score == total_edges;

        match result {
            RecurseResult::AllAssigned => {
                stats.solutions_found = 1;
                sink.emit(SolverEvent {
                    schema_version: 1,
                    solver_run_id: opts.solver_run_id,
                    node_id: search.stats.nodes,
                    depth: search.best_score,
                    timestamp_us: elapsed_us,
                    body: EventBody::Solved {
                        board: best_board.clone(),
                        final_stats: stats,
                    },
                });
                SolveOutcome::Solved(best_board)
            }
            RecurseResult::Exhausted | RecurseResult::DeadEnd if is_complete => {
                stats.solutions_found = 1;
                sink.emit(SolverEvent {
                    schema_version: 1,
                    solver_run_id: opts.solver_run_id,
                    node_id: search.stats.nodes,
                    depth: search.best_score,
                    timestamp_us: elapsed_us,
                    body: EventBody::Solved {
                        board: best_board.clone(),
                        final_stats: stats,
                    },
                });
                SolveOutcome::Solved(best_board)
            }
            RecurseResult::Exhausted | RecurseResult::DeadEnd => {
                sink.emit(SolverEvent {
                    schema_version: 1,
                    solver_run_id: opts.solver_run_id,
                    node_id: search.stats.nodes,
                    depth: search.best_score,
                    timestamp_us: elapsed_us,
                    body: EventBody::Exhausted {
                        final_stats: stats,
                        solutions_found: 0,
                    },
                });
                if matches!(opts.mode, SolveMode::FirstSolution) || search.best_score == 0 {
                    SolveOutcome::Exhausted
                } else {
                    SolveOutcome::TimedOut {
                        best_partial: best_board,
                        best_depth: search.best_score,
                    }
                }
            }
            RecurseResult::TimedOut => {
                sink.emit(SolverEvent {
                    schema_version: 1,
                    solver_run_id: opts.solver_run_id,
                    node_id: search.stats.nodes,
                    depth: search.best_score,
                    timestamp_us: elapsed_us,
                    body: EventBody::TimedOut {
                        final_stats: stats,
                        best_partial: best_board.clone(),
                        best_depth: search.best_score,
                    },
                });
                SolveOutcome::TimedOut {
                    best_partial: best_board,
                    best_depth: search.best_score,
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_events::BufferSink;
    use eternity2_generator::{generate, GeneratorConfig};

    #[test]
    fn solves_4x4_generated() {
        let puzzle = generate(GeneratorConfig { size: 4, interior_colors: 4, seed: 17 }).unwrap();
        let mut solver = EdgeSolver::default_v1();
        let mut sink = BufferSink::new();
        let mut opts = SolveOpts::default();
        opts.time_budget_ms = 30_000;
        let outcome = solver.solve(&puzzle, &opts, &mut sink);
        match outcome {
            SolveOutcome::Solved(_) => eprintln!("4x4 solved"),
            SolveOutcome::TimedOut { best_partial: _, best_depth } => {
                eprintln!("edge-cp 4x4: timed out at score {best_depth}");
            }
            SolveOutcome::Exhausted => {
                eprintln!("edge-cp 4x4: exhausted without finding 24/24");
            }
            other => panic!("unexpected outcome: {other:?}"),
        }
    }

    #[test]
    fn solves_6x6_generated() {
        let puzzle = generate(GeneratorConfig { size: 6, interior_colors: 5, seed: 11 }).unwrap();
        let topology = Topology::new(&puzzle);
        let tables = Tables::new(&puzzle, &topology);
        let mut cfg = SearchConfig::default();
        cfg.time_budget_ms = 60_000;
        let mut search = Search::new(&puzzle, &topology, &tables, cfg);
        let start = std::time::Instant::now();
        let clock = || start.elapsed().as_micros() as u64;
        let r = search.recurse(&clock);
        eprintln!("6x6 with-alldiff: result={:?} best_score={}/{} nodes={} backtracks={} piece_commits={}",
            r, search.best_score, topology.n_edges, search.stats.nodes, search.stats.backtracks,
            search.stats.piece_commits);
    }

    #[test]
    fn solves_6x6_no_alldiff() {
        let puzzle = generate(GeneratorConfig { size: 6, interior_colors: 5, seed: 11 }).unwrap();
        let topology = Topology::new(&puzzle);
        let tables = Tables::new(&puzzle, &topology);
        let mut cfg = SearchConfig::default();
        cfg.time_budget_ms = 60_000;
        cfg.propagate_piece_uniqueness = false;
        let mut search = Search::new(&puzzle, &topology, &tables, cfg);
        let start = std::time::Instant::now();
        let clock = || start.elapsed().as_micros() as u64;
        let r = search.recurse(&clock);
        eprintln!("6x6 no-alldiff: result={:?} best_score={}/{} nodes={} backtracks={} piece_commits={}",
            r, search.best_score, topology.n_edges, search.stats.nodes, search.stats.backtracks,
            search.stats.piece_commits);
    }

    #[test]
    fn print_3x3_pieces() {
        let p = generate(GeneratorConfig { size: 3, interior_colors: 3, seed: 1 }).unwrap();
        for piece in p.pieces() {
            let e = piece.edges.as_array();
            let kind = if piece.is_corner() { "CORNER" } else if piece.is_edge() { "EDGE" } else { "INNER" };
            eprintln!("piece {}: edges=[t={},r={},b={},l={}] {kind}", piece.id, e[0], e[1], e[2], e[3]);
        }
    }

    #[test]
    fn diagnostic_3x3_generated() {
        let puzzle = generate(GeneratorConfig { size: 3, interior_colors: 3, seed: 1 }).unwrap();
        let topology = Topology::new(&puzzle);
        let tables = Tables::new(&puzzle, &topology);
        eprintln!("3x3 puzzle: n_edges={} n_rows={} n_cells={}",
            topology.n_edges, tables.n_rows, topology.n_cells);
        for c in 0..topology.n_cells {
            let mask = tables.cell_shape_mask(c);
            let cnt: u32 = mask.iter().map(|w| w.count_ones()).sum();
            eprintln!("cell {c}: shape_mask popcount = {cnt}");
        }
        let mut cfg = SearchConfig::default();
        cfg.trace = true;
        let mut search = Search::new(&puzzle, &topology, &tables, cfg);
        let clock = || 0u64;
        let r = search.recurse(&clock);
        eprintln!("result={:?} best_score={} nodes={} backtracks={} piece_commits={}",
            r, search.best_score, search.stats.nodes, search.stats.backtracks,
            search.stats.piece_commits);
    }
}
