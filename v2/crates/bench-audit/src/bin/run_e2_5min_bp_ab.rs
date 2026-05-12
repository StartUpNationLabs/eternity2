// Vol-14 #1 A/B — same canonical Eternity II run, same seed, two
// profiles back-to-back:
//   A) joe_depth150_par                          (vol-12 baseline)
//   B) joe_depth150_bp_par + edge-BP marginals   (vol-14 #1)
//
// 5-minute budget each. Records max_depth_seen, nodes, edge_matches,
// and bucas URL for both arms. Output saved under output/v14_bp/.
//
// Run sequentially (not in parallel) so they don't fight over cores.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Instant;

use eternity2_bench_audit as _;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::Board;
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineSolver};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

struct ProgressSink {
    log: std::fs::File,
    started: Instant,
    last_log_ms: u64,
    period_ms: u64,
    best_depth: u32,
    final_stats: Option<FinalStats>,
}

impl ProgressSink {
    fn new(path: &Path, period_ms: u64) -> std::io::Result<Self> {
        let file = std::fs::File::create(path)?;
        Ok(Self {
            log: file,
            started: Instant::now(),
            last_log_ms: 0,
            period_ms,
            best_depth: 0,
            final_stats: None,
        })
    }
    fn write_line(&mut self, line: &str) {
        let _ = writeln!(self.log, "{line}");
        let _ = self.log.flush();
    }
}

impl EventSink for ProgressSink {
    fn emit(&mut self, event: SolverEvent) {
        let elapsed_ms = self.started.elapsed().as_millis() as u64;
        if let EventBody::Backtrack { from_depth, .. } = &event.body {
            if *from_depth > self.best_depth { self.best_depth = *from_depth; }
        }
        if event.depth > self.best_depth { self.best_depth = event.depth; }
        let should_tick = elapsed_ms.saturating_sub(self.last_log_ms) >= self.period_ms;
        if should_tick {
            self.last_log_ms = elapsed_ms;
            let bd = self.best_depth;
            let line = format!(
                "[{:>7} ms]  current_depth={:>4}  best_depth_seen={:>4}  node_id={}",
                elapsed_ms, event.depth, bd, event.node_id
            );
            self.write_line(&line);
        }
        match event.body {
            EventBody::Solved { final_stats, .. }
            | EventBody::Exhausted { final_stats, .. }
            | EventBody::TimedOut { final_stats, .. }
            | EventBody::Cancelled { final_stats, .. } => {
                self.final_stats = Some(final_stats);
                self.write_line("=== terminal event received ===");
            }
            _ => {}
        }
    }
}

fn score_board(puzzle: &eternity2_core::Puzzle, board: &Board) -> (u32, u32) {
    let mut matched = 0u32;
    let mut total = 0u32;
    let w = puzzle.width;
    let h = puzzle.height;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let p = puzzle.piece(pid).unwrap();
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((npid, nrot)) = board.get(y * w + (x + 1)) {
                    total += 1;
                    let np = puzzle.piece(npid).unwrap();
                    let ne = np.edges.rotated(nrot).as_array();
                    if e[1] == ne[3] { matched += 1; }
                }
            }
            if y + 1 < h {
                if let Some((npid, nrot)) = board.get((y + 1) * w + x) {
                    total += 1;
                    let np = puzzle.piece(npid).unwrap();
                    let ne = np.edges.rotated(nrot).as_array();
                    if e[2] == ne[0] { matched += 1; }
                }
            }
        }
    }
    (matched, total)
}

fn placed_count(b: &Board, puzzle: &eternity2_core::Puzzle) -> u32 {
    let mut n = 0;
    for pos in 0..puzzle.cell_count() {
        if b.get(pos).is_some() { n += 1; }
    }
    n
}

struct ArmResult {
    label: String,
    verdict: String,
    elapsed_s: f64,
    nodes: u64,
    nodes_per_sec: f64,
    max_depth_seen: u32,
    edge_matches: u32,
    edge_total: u32,
    pieces_placed: u32,
    bucas: String,
    board_json: serde_json::Value,
}

fn run_arm(
    label: &str,
    mut solver: EngineSolver,
    puzzle: &eternity2_core::Puzzle,
    hints: &eternity2_core::Hints,
    edge_bp: Option<std::sync::Arc<Vec<f32>>>,
    log_path: &Path,
    board_path: &Path,
    budget_ms: u64,
    seed: u64,
) -> ArmResult {
    let mut sink = ProgressSink::new(log_path, 5_000).expect("open log");
    sink.write_line(&format!(
        "=== {label} ===\nbudget_ms: {budget_ms}\nseed: {seed}\n",
    ));
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = seed;
    opts.hints = hints.clone();
    opts.edge_bp_marginals = edge_bp;

    let t0 = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed();
    let final_stats = sink.final_stats.clone();

    let (verdict, board) = match outcome {
        SolveOutcome::Solved(b) => ("SOLVED".to_string(), Some(b)),
        SolveOutcome::TimedOut { best_partial, best_depth } => {
            (format!("TIMEOUT (best_depth={best_depth})"), Some(best_partial))
        }
        SolveOutcome::Cancelled { best_partial, best_depth, .. } => {
            (format!("CANCELLED (best_depth={best_depth})"), Some(best_partial))
        }
        SolveOutcome::Exhausted => ("EXHAUSTED".to_string(), None),
        SolveOutcome::AllSolutions(bs) => (format!("ALL ({})", bs.len()), bs.into_iter().next()),
        SolveOutcome::Error(e) => (format!("ERROR: {e}"), None),
    };

    let (matched, total, placed, bucas, board_json) = if let Some(b) = board.as_ref() {
        let (m, t) = score_board(puzzle, b);
        let p = placed_count(b, puzzle);
        let bu = bucas_url(puzzle, b, &format!("v14_{label}"));
        let j = serde_json::json!({
            "placement": (0..puzzle.cell_count()).map(|pos| {
                b.get(pos).map(|(pid, rot)| serde_json::json!({
                    "pos": pos,
                    "piece_id": u32::from(pid),
                    "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
        });
        std::fs::write(board_path, serde_json::to_string_pretty(&j).unwrap()).expect("write board");
        (m, t, p, bu, j)
    } else {
        (0, 0, 0, "(no board)".to_string(), serde_json::json!({}))
    };

    let (nodes, max_depth) = final_stats
        .as_ref()
        .map(|s| (s.nodes, s.max_depth_seen))
        .unwrap_or((0, 0));
    let nps = nodes as f64 / elapsed.as_secs_f64().max(1e-6);

    let summary = format!(
        "\n=== {label} FINAL ===\nverdict: {verdict}\nwall_clock_s: {:.2}\nnodes: {nodes}\nnps: {:.0}\nmax_depth_seen: {max_depth}\npieces_placed: {placed}/{}\nedge_matches: {matched}/{total}\nbucas: {bucas}\n",
        elapsed.as_secs_f64(),
        nps,
        puzzle.cell_count(),
    );
    sink.write_line(&summary);
    eprintln!("{summary}");

    ArmResult {
        label: label.to_string(),
        verdict,
        elapsed_s: elapsed.as_secs_f64(),
        nodes,
        nodes_per_sec: nps,
        max_depth_seen: max_depth,
        edge_matches: matched,
        edge_total: total,
        pieces_placed: placed,
        bucas,
        board_json,
    }
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");
    let out_dir = PathBuf::from("output/v14_bp");
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eprintln!(
        "loaded canonical E2: {}x{} colors={} hints={}",
        puzzle.width, puzzle.height, puzzle.color_count - 1, hints.hints.len()
    );

    let edge_bp = load_edge_bp_marginals(&bp_path).expect("load edge_bp_60i.json");
    eprintln!("loaded edge-BP marginals: {} floats ({} edges × 23)", edge_bp.len(), edge_bp.len() / 23);

    // Honour optional CLI: budget_ms (default 300_000) and seed (default 1).
    let mut budget_ms: u64 = 300_000;
    let mut seed: u64 = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            _ => eprintln!("(unrecognized arg: {a})"),
        }
    }

    // Arm A — baseline.
    let a = run_arm(
        "joe_depth150_par",
        EngineSolver::joe_depth150_par(),
        &puzzle,
        &hints,
        None,
        &out_dir.join("A_baseline.log"),
        &out_dir.join("A_baseline_board.json"),
        budget_ms,
        seed,
    );
    // Arm B — edge-BP.
    let b = run_arm(
        "joe_depth150_bp_par",
        EngineSolver::joe_depth150_bp_par(),
        &puzzle,
        &hints,
        Some(edge_bp.clone()),
        &out_dir.join("B_bp.log"),
        &out_dir.join("B_bp_board.json"),
        budget_ms,
        seed,
    );

    let report = serde_json::json!({
        "schema_version": 1,
        "puzzle": "canonical E2 (size_16_official_eternity.csv)",
        "budget_ms": budget_ms,
        "seed": seed,
        "edge_bp_source": "output/v12_bp/edge_bp_60i.json",
        "arms": [
            {
                "label": a.label, "verdict": a.verdict, "elapsed_s": a.elapsed_s,
                "nodes": a.nodes, "nodes_per_sec": a.nodes_per_sec,
                "max_depth_seen": a.max_depth_seen, "edge_matches": a.edge_matches,
                "edge_total": a.edge_total, "pieces_placed": a.pieces_placed,
                "bucas": a.bucas, "board": a.board_json,
            },
            {
                "label": b.label, "verdict": b.verdict, "elapsed_s": b.elapsed_s,
                "nodes": b.nodes, "nodes_per_sec": b.nodes_per_sec,
                "max_depth_seen": b.max_depth_seen, "edge_matches": b.edge_matches,
                "edge_total": b.edge_total, "pieces_placed": b.pieces_placed,
                "bucas": b.bucas, "board": b.board_json,
            },
        ],
        "delta_max_depth": b.max_depth_seen as i64 - a.max_depth_seen as i64,
        "delta_edge_matches": b.edge_matches as i64 - a.edge_matches as i64,
        "delta_pieces_placed": b.pieces_placed as i64 - a.pieces_placed as i64,
    });
    let report_path = out_dir.join("ab_report.json");
    std::fs::write(&report_path, serde_json::to_string_pretty(&report).unwrap()).expect("write report");
    eprintln!("\nReport: {}", report_path.display());
    eprintln!(
        "Δ max_depth_seen  = {:+}\nΔ edge_matches    = {:+}\nΔ pieces_placed   = {:+}",
        b.max_depth_seen as i64 - a.max_depth_seen as i64,
        b.edge_matches as i64 - a.edge_matches as i64,
        b.pieces_placed as i64 - a.pieces_placed as i64,
    );
}
