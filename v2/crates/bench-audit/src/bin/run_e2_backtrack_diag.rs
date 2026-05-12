// Vol-14 — instrument per-position backtrack distribution on canonical E2.
// Runs a single-thread `gacolor_ac3_ns1` CP for N seconds, then reads
// `EngineSolver::take_pos_backtracks()` and bucket by cell class.
//
// Question being answered: is the search cost concentrated at the border
// (where the 75k+ Hamilton-ring ambiguity lives) or at the interior
// (where the canonical 5 hints anchor a 12x11 hard sub-region)?

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit as _;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Position;
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, Solver};

struct QuietSink {
    depth: u32,
    final_stats: Option<FinalStats>,
}
impl QuietSink {
    fn new() -> Self { Self { depth: 0, final_stats: None } }
}
impl EventSink for QuietSink {
    fn emit(&mut self, event: SolverEvent) {
        if event.depth > self.depth { self.depth = event.depth; }
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

const W: u32 = 16;
const H: u32 = 16;

fn cell_class(pos: Position) -> &'static str {
    let x = pos % W;
    let y = pos / W;
    let is_corner = (x == 0 || x == W-1) && (y == 0 || y == H-1);
    let is_border = x == 0 || x == W-1 || y == 0 || y == H-1;
    if is_corner { "corner" }
    else if is_border { "border" }
    else { "interior" }
}

fn cell_layer(pos: Position) -> u32 {
    // Distance from nearest edge of board.
    let x = pos % W;
    let y = pos / W;
    let dx = std::cmp::min(x, W - 1 - x);
    let dy = std::cmp::min(y, H - 1 - y);
    std::cmp::min(dx, dy)
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut budget_ms: u64 = 30_000;
    let mut profile = "gacolor_ac3_ns1".to_string();
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--profile" => profile = args.next().unwrap(),
            _ => eprintln!("(unrecognized: {a})"),
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    eprintln!("loaded canonical E2: {}x{}, {} hints; profile={}, budget={}ms (SINGLE-THREAD)",
        puzzle.width, puzzle.height, hints.hints.len(), profile, budget_ms);

    let mut solver = match profile.as_str() {
        "gacolor_ac3"     => EngineSolver::gacolor_ac3(),
        "gacolor_ac3_ns1" => EngineSolver::gacolor_ac3_ns1(),
        "joe_depth150"    => EngineSolver::joe_depth150(),
        _ => panic!("unsupported profile (single-thread variants only): {profile}"),
    };
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = 1;
    opts.hints = hints;

    let mut sink = QuietSink::new();
    let t0 = Instant::now();
    let _outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();

    let stats = sink.final_stats.expect("final stats");
    let pos_bt = solver.take_pos_backtracks();
    let total_pos_bt: u64 = pos_bt.iter().sum();

    eprintln!("\n=== RUN STATS ===");
    eprintln!("elapsed:        {:.1}s", elapsed.as_secs_f64());
    eprintln!("nodes:          {}", stats.nodes);
    eprintln!("backtracks:     {}", stats.backtracks);
    eprintln!("pos_bt_total:   {}  (should ≈ backtracks)", total_pos_bt);
    eprintln!("max_depth:      {}", stats.max_depth_seen);

    // Bucket 1: by cell class
    let mut by_class = std::collections::BTreeMap::new();
    let mut by_layer = std::collections::BTreeMap::new();
    for (pos_u, count) in pos_bt.iter().enumerate() {
        let pos = pos_u as Position;
        *by_class.entry(cell_class(pos)).or_insert(0u64) += *count;
        *by_layer.entry(cell_layer(pos)).or_insert(0u64) += *count;
    }
    eprintln!("\n=== Backtracks by cell class ===");
    let total = total_pos_bt.max(1);
    for (k, v) in &by_class {
        eprintln!("  {:>10}: {:>12}  ({:>5.1}%)", k, v, *v as f64 * 100.0 / total as f64);
    }
    eprintln!("\n=== Backtracks by layer (Chebyshev distance from board edge) ===");
    eprintln!("  layer 0 = perimeter; layer 1 = next ring inward; etc.");
    for (k, v) in &by_layer {
        // Cells in each layer:
        let cells_in_layer = if *k == 0 { 60u32 }
            else if *k == 7 { 4u32 }
            else { 4 * (W - 2 * *k) - 4 };
        eprintln!("  layer {}: {:>12}  ({:>5.1}%)   ({} cells; {:.1} bt/cell avg)",
            k, v, *v as f64 * 100.0 / total as f64,
            cells_in_layer, *v as f64 / cells_in_layer as f64);
    }

    // Top-10 hottest cells
    let mut top: Vec<(Position, u64)> = pos_bt.iter().enumerate()
        .map(|(i, &c)| (i as Position, c))
        .collect();
    top.sort_by(|a, b| b.1.cmp(&a.1));
    eprintln!("\n=== Top-10 hottest positions ===");
    for (i, (pos, count)) in top.iter().take(10).enumerate() {
        let x = pos % W;
        let y = pos / W;
        eprintln!("  #{} pos={:>3} (x={:>2},y={:>2}, {:>8}, layer={}): {} backtracks ({:.1}%)",
            i+1, pos, x, y, cell_class(*pos), cell_layer(*pos),
            count, *count as f64 * 100.0 / total as f64);
    }

    // Save the full distribution
    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v14_backtrack_diag/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");
    let report = serde_json::json!({
        "profile": profile,
        "budget_ms": budget_ms,
        "elapsed_s": elapsed.as_secs_f64(),
        "nodes": stats.nodes,
        "backtracks_total": stats.backtracks,
        "max_depth_seen": stats.max_depth_seen,
        "by_class": by_class,
        "by_layer": by_layer,
        "per_position": pos_bt,
        "top_10": top[..10].iter().map(|(p, c)| serde_json::json!({
            "pos": p, "x": p % W, "y": p / W,
            "class": cell_class(*p), "layer": cell_layer(*p), "count": c,
        })).collect::<Vec<_>>(),
    });
    let report_path = out_dir.join("report.json");
    std::fs::write(&report_path, serde_json::to_string_pretty(&report).unwrap()).expect("write");
    eprintln!("\nFull report: {}", report_path.display());
}
