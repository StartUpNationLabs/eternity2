// Vol-14 user-proposed experiment — "rectangle skeleton" path:
//   1. Start at hint at (2, 2).
//   2. Walk along row y=2 right to (13, 2) (hint).
//   3. Walk down col x=13 to (13, 13) (hint).
//   4. Walk left along row y=13 to (2, 13) (hint).
//   5. Walk up col x=2 partway, then jump to center hint (7, 8).
//   6. After the skeleton is placed, let border-first MRV handle the rest.
//
// Hypothesis: laying a skeleton that connects all 5 hints establishes
// shared-edge constraints across the board's 'gross structure' BEFORE
// the regular search begins. This may break the 764-plateau by
// constraining hot interior cells' domains via the skeleton.
//
// Method: SolveOpts.path = the skeleton sequence; PathPolicy =
// PrefixConstraint { k: skeleton_len }. After depth `k`, the engine
// uses its normal variable-ordering (border_first_lcv MRV).
//
// CLI: --budget-ms <ms> --seed <u64> --profile {joe_bp, joe_par,
//      lcv, gacolor_ac3} --close-loop (also close back to (2,2))

use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Instant;

use eternity2_bench_audit as _;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, PathPolicy, Position};
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineSolver};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

const W: u32 = 16;
const H: u32 = 16;

fn pos(x: u32, y: u32) -> Position { y * W + x }

/// User's "rectangle skeleton" path: trace a rectangle along rows
/// y=2 and y=13 + columns x=2 and x=13, visiting the 4 outer hints.
/// Then route to the center hint via (7, 8). Avoids duplicates.
fn build_rectangle_path(close_loop: bool) -> Vec<Position> {
    let mut path = Vec::new();
    let mut seen = std::collections::HashSet::new();
    let mut push = |p: Position, path: &mut Vec<Position>, seen: &mut std::collections::HashSet<Position>| {
        if seen.insert(p) {
            path.push(p);
        }
    };
    // Top row (y=2): from hint (2,2) to hint (13,2)
    for x in 2..=13 {
        push(pos(x, 2), &mut path, &mut seen);
    }
    // Right col (x=13): from (13,2) down to (13,13)
    for y in 3..=13 {
        push(pos(13, y), &mut path, &mut seen);
    }
    // Bottom row (y=13): from (13,13) left to (2,13)
    for x in (2..=12).rev() {
        push(pos(x, 13), &mut path, &mut seen);
    }
    // Left col (x=2): from (2,13) UP to (2,2). If close_loop=false,
    // stop one cell short of (2,2) so we don't loop back redundantly.
    let top_y = if close_loop { 2 } else { 3 };
    for y in (top_y..=12).rev() {
        push(pos(2, y), &mut path, &mut seen);
    }
    // Path to center hint (7, 8) — go right from (2,8), if (2,8) is
    // already in the rect that's fine.
    // Approach: a horizontal line at y=8 from x=2 to x=7.
    // (2,8) might already be on the rect (left col), so re-add skips.
    for x in 2..=7 {
        push(pos(x, 8), &mut path, &mut seen);
    }
    path
}

struct ProgressSink {
    log: std::fs::File,
    started: Instant,
    last_log_ms: u64,
    period_ms: u64,
    best_depth: u32,
    final_stats: Option<FinalStats>,
}
impl ProgressSink {
    fn new(p: &Path, period_ms: u64) -> std::io::Result<Self> {
        Ok(Self { log: std::fs::File::create(p)?, started: Instant::now(),
            last_log_ms: 0, period_ms, best_depth: 0, final_stats: None })
    }
}
impl EventSink for ProgressSink {
    fn emit(&mut self, event: SolverEvent) {
        let elapsed_ms = self.started.elapsed().as_millis() as u64;
        if let EventBody::Backtrack { from_depth, .. } = &event.body {
            if *from_depth > self.best_depth { self.best_depth = *from_depth; }
        }
        if event.depth > self.best_depth { self.best_depth = event.depth; }
        if elapsed_ms.saturating_sub(self.last_log_ms) >= self.period_ms {
            self.last_log_ms = elapsed_ms;
            let _ = writeln!(self.log,
                "[{:>7}ms]  depth={:>4}  best_depth={:>4}",
                elapsed_ms, event.depth, self.best_depth);
            let _ = self.log.flush();
        }
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

fn score_board(puzzle: &eternity2_core::Puzzle, board: &Board) -> u32 {
    let (w, h) = (puzzle.width, puzzle.height);
    let mut m = 0u32;
    for y in 0..h {
        for x in 0..w {
            let p = y*w+x;
            let Some((pid, rot)) = board.get(p) else { continue; };
            let pp = puzzle.piece(pid).unwrap();
            let e = pp.edges.rotated(rot).as_array();
            if x+1 < w {
                if let Some((np, nr)) = board.get(p+1) {
                    let npp = puzzle.piece(np).unwrap();
                    if e[1] == npp.edges.rotated(nr).as_array()[3] { m += 1; }
                }
            }
            if y+1 < h {
                if let Some((np, nr)) = board.get(p+w) {
                    let npp = puzzle.piece(np).unwrap();
                    if e[2] == npp.edges.rotated(nr).as_array()[0] { m += 1; }
                }
            }
        }
    }
    m
}

fn placed_count(b: &Board, puzzle: &eternity2_core::Puzzle) -> u32 {
    (0..puzzle.cell_count()).filter(|&p| b.get(p).is_some()).count() as u32
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v14_rectangle_path/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    let mut budget_ms: u64 = 60_000;
    let mut seed: u64 = 1;
    let mut profile = "lcv".to_string();
    let mut close_loop = false;
    let mut k_override: Option<u32> = None;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--profile" => profile = args.next().unwrap(),
            "--close-loop" => close_loop = true,
            "--k" => k_override = Some(args.next().unwrap().parse().unwrap()),
            _ => eprintln!("(unrecognized: {a})"),
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    eprintln!("loaded canonical E2");

    let path = build_rectangle_path(close_loop);
    let k = k_override.unwrap_or(path.len() as u32);
    eprintln!("Rectangle path (length {}):", path.len());
    for (i, p) in path.iter().enumerate() {
        if i < 5 || i >= path.len() - 5 { eprintln!("  [{}] pos={} ({},{})", i, p, p%W, p/W); }
        else if i == 5 { eprintln!("  ..."); }
    }
    eprintln!("PrefixConstraint k = {}", k);

    // Side-by-side: arm A = default (no path), arm B = rectangle path.
    let edge_bp = if profile == "joe_bp" {
        Some(load_edge_bp_marginals(&bp_path).expect("load bp"))
    } else { None };

    let mut summary = serde_json::json!({
        "schema_version": 1,
        "budget_ms": budget_ms,
        "seed": seed,
        "profile": profile,
        "rectangle_path_len": path.len(),
        "k": k,
        "close_loop": close_loop,
        "arms": [],
    });
    let arms = summary.as_object_mut().unwrap()
        .get_mut("arms").unwrap().as_array_mut().unwrap();

    for (label, use_path) in [("default_mrv", false), ("rectangle_path", true)] {
        eprintln!("\n=== arm: {label} ===");
        let log_path = out_dir.join(format!("{label}.log"));
        let mut sink = ProgressSink::new(&log_path, 5_000).expect("open log");
        let mut opts = SolveOpts::default();
        opts.time_budget_ms = budget_ms;
        opts.seed = seed;
        opts.hints = hints.clone();
        opts.edge_bp_marginals = edge_bp.clone();
        if use_path {
            opts.path = path.clone();
            opts.path_policy = PathPolicy::PrefixConstraint { k };
        }
        let mut solver = match profile.as_str() {
            "lcv"           => EngineSolver::border_first_lcv(),
            "lcv_par"       => EngineSolver::border_first_lcv_par(),
            "gacolor_ac3"   => EngineSolver::gacolor_ac3(),
            "joe_par"       => EngineSolver::joe_depth150_par(),
            "joe_bp"        => EngineSolver::joe_depth150_bp_par(),
            _ => panic!("unknown profile {profile}"),
        };
        let t0 = Instant::now();
        let outcome = solver.solve(&puzzle, &opts, &mut sink);
        let elapsed = t0.elapsed();
        let stats = sink.final_stats.clone();
        let board = match outcome {
            SolveOutcome::Solved(b) => Some(b),
            SolveOutcome::TimedOut { best_partial, .. } => Some(best_partial),
            SolveOutcome::Cancelled { best_partial, .. } => Some(best_partial),
            _ => None,
        };
        let (placed, matched, bucas) = if let Some(b) = board.as_ref() {
            let p = placed_count(b, &puzzle);
            let m = score_board(&puzzle, b);
            (p, m, Some(bucas_url(&puzzle, b, &format!("v14_rectangle_{label}"))))
        } else { (0, 0, None) };
        let (nodes, depth, nps) = stats.as_ref().map(|s| (
            s.nodes, s.max_depth_seen,
            s.nodes as f64 / elapsed.as_secs_f64().max(1e-6)
        )).unwrap_or((0, sink.best_depth, 0.0));
        eprintln!("{label:>20}: elapsed={:.1}s  depth={depth:>3}  placed={placed:>3}/256  matched={matched:>3}/480  nodes={nodes}  nps={nps:.0}",
            elapsed.as_secs_f64());
        arms.push(serde_json::json!({
            "label": label, "elapsed_s": elapsed.as_secs_f64(),
            "max_depth_seen": depth, "pieces_placed": placed,
            "matched_480": matched, "nodes": nodes, "nps": nps,
            "bucas": bucas,
        }));
    }

    let report_path = out_dir.join("ab_report.json");
    std::fs::write(&report_path, serde_json::to_string_pretty(&summary).unwrap()).unwrap();
    eprintln!("\nReport: {}", report_path.display());
}
