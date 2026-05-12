// Vol-14 — same rectangle-path experiment but on a 12x12/12-color
// generated puzzle with synthetic hints placed in canonical-E2-style
// geometry: 4 corner-area hints + 1 center hint.
//
// Method:
//   1. Generate 12x12/12 puzzle from --seed.
//   2. Solve to get the true solution (vol-14 stack can solve a 12x12
//      with strong propagation given enough budget — but generation
//      includes the solution by construction, so we just sample it).
//      Actually: the generator produces a puzzle from a known-good
//      placement. We don't have access to that placement via the
//      public API, so instead we solve once with a long budget and
//      use whatever it finds.
//   3. From the solution, extract (piece, rotation) at 5 positions
//      in canonical-style geometry: (2,2), (9,2), (2,9), (9,9), (5,5).
//   4. Re-launch CP with those 5 hints + the rectangle-skeleton path.
//   5. A/B vs the same hints without the rectangle path.
//
// CLI: --seed --solve-budget-ms (for initial solve) --bench-budget-ms (A/B)

use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_core::{Board, Hint, Hints, PathPolicy, Position};
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

const W: u32 = 12;

fn pos(x: u32, y: u32) -> Position { y * W + x }

fn build_rectangle_path(corner_hints: &[(u32, u32)], center: (u32, u32)) -> Vec<Position> {
    // corner_hints[0..4] = TL, TR, BR, BL (clockwise from top-left).
    // Walk TL→TR along TL.y row, TR→BR along TR.x col, BR→BL along BR.y row, BL→(BL.y-1) up col.
    let (tlx, tly) = corner_hints[0];
    let (trx, _try) = corner_hints[1];
    let (_brx, bry) = corner_hints[2];
    let mut path = Vec::new();
    let mut seen = std::collections::HashSet::new();
    let push = |p: Position, path: &mut Vec<Position>, seen: &mut std::collections::HashSet<Position>| {
        if seen.insert(p) { path.push(p); }
    };
    // Top row
    for x in tlx..=trx { push(pos(x, tly), &mut path, &mut seen); }
    // Right col
    for y in (tly+1)..=bry { push(pos(trx, y), &mut path, &mut seen); }
    // Bottom row, right-to-left
    for x in (tlx..=trx-1).rev() { push(pos(x, bry), &mut path, &mut seen); }
    // Left col, bottom-to-top, stop one short of TL
    for y in ((tly+1)..bry).rev() { push(pos(tlx, y), &mut path, &mut seen); }
    // Path to center along center.y row
    let (cx, cy) = center;
    for x in tlx..=cx { push(pos(x, cy), &mut path, &mut seen); }
    path
}

struct QuietSink {
    final_stats: Option<FinalStats>,
    best_depth: u32,
}
impl QuietSink { fn new() -> Self { Self { final_stats: None, best_depth: 0 } } }
impl EventSink for QuietSink {
    fn emit(&mut self, event: SolverEvent) {
        if event.depth > self.best_depth { self.best_depth = event.depth; }
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


fn main() {
    let mut seed: u64 = 1;
    let mut solve_budget: u64 = 90_000;
    let mut bench_budget: u64 = 60_000;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--solve-budget-ms" => solve_budget = args.next().unwrap().parse().unwrap(),
            "--bench-budget-ms" => bench_budget = args.next().unwrap().parse().unwrap(),
            _ => {}
        }
    }

    let puzzle = generate(GeneratorConfig {
        size: W, interior_colors: 12, seed
    }).expect("generate");
    eprintln!("Generated 12x12/12 puzzle, seed={seed}");

    // Stage 1: solve to (near-)completion to learn the "true" piece
    // placements at our chosen hint positions.
    eprintln!("\n--- Stage 1: solve to learn hint pieces (CP + ALNS) ---");
    let corner_hints = [(2, 2), (9, 2), (9, 9), (2, 9)]; // TL, TR, BR, BL
    let center = (5, 5);
    let hint_positions: Vec<Position> = corner_hints.iter()
        .map(|&(x, y)| pos(x, y))
        .chain(std::iter::once(pos(center.0, center.1)))
        .collect();

    let mut s = EngineSolver::gacolor_ac3_par();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = solve_budget;
    opts.seed = seed;
    let mut sink = QuietSink::new();
    let t0 = Instant::now();
    let outcome = s.solve(&puzzle, &opts, &mut sink);
    let solve_elapsed = t0.elapsed();
    let board0: Board = match outcome {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::TimedOut { best_partial, .. } => best_partial,
        SolveOutcome::Cancelled { best_partial, .. } => best_partial,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        _ => Board::empty(&puzzle),
    };
    let (m0, t0_e) = score_board(&puzzle, &board0);
    eprintln!("Stage 1 ({:.1}s): matched={m0}/{t0_e}, placed={}/{}",
        solve_elapsed.as_secs_f64(),
        placed_count(&board0, &puzzle), puzzle.cell_count());

    // Build hints from board0 at our chosen positions.
    let mut hints_vec = Vec::new();
    for &p in &hint_positions {
        if let Some((pid, rot)) = board0.get(p) {
            hints_vec.push(Hint { position: p, piece_id: pid, rotation: rot });
        } else {
            eprintln!("WARNING: pos {} not placed in stage-1 solution, skipping hint", p);
        }
    }
    eprintln!("Hints derived: {} of {} target positions",
        hints_vec.len(), hint_positions.len());
    let hints = Hints { hints: hints_vec.clone() };

    // Stage 2: A/B with these hints, with and without rectangle path.
    let path = build_rectangle_path(&corner_hints, center);
    eprintln!("\n--- Stage 2: A/B (default_mrv vs rectangle_path), budget={bench_budget}ms ---");
    eprintln!("Rectangle path length: {}", path.len());

    for (label, use_path) in [("default_mrv", false), ("rectangle_path", true)] {
        let mut opts = SolveOpts::default();
        opts.time_budget_ms = bench_budget;
        opts.seed = seed;
        opts.hints = hints.clone();
        if use_path {
            opts.path = path.clone();
            opts.path_policy = PathPolicy::PrefixConstraint { k: path.len() as u32 };
        }
        let mut s = EngineSolver::border_first_lcv();
        let mut sink = QuietSink::new();
        let t = Instant::now();
        let oc = s.solve(&puzzle, &opts, &mut sink);
        let elapsed = t.elapsed();
        let board = match oc {
            SolveOutcome::Solved(b) => Some(b),
            SolveOutcome::TimedOut { best_partial, .. } => Some(best_partial),
            SolveOutcome::Cancelled { best_partial, .. } => Some(best_partial),
            _ => None,
        };
        let (placed, matched, total) = if let Some(b) = board.as_ref() {
            let (m, t) = score_board(&puzzle, b);
            (placed_count(b, &puzzle), m, t)
        } else { (0, 0, 264) };
        let stats = sink.final_stats.clone();
        let (nodes, depth, nps) = stats.as_ref().map(|s| (
            s.nodes, s.max_depth_seen,
            s.nodes as f64 / elapsed.as_secs_f64().max(1e-6)
        )).unwrap_or((0, sink.best_depth, 0.0));
        eprintln!("{label:>20}: elapsed={:.1}s  depth={depth:>3}  placed={placed:>3}/{}  matched={matched:>3}/{total}  nodes={nodes}  nps={nps:.0}",
            elapsed.as_secs_f64(), puzzle.cell_count());
    }
}
