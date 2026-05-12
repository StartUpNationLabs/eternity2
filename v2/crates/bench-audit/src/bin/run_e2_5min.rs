// Vol-12 closeout — raw run on canonical Eternity II with the best v12
// combination: joe_depth150_par (gacolor + AC-3 + NS-1 multiset-equality
// + depth-150 gate + multi-core root-split + bitset-only domain rep).
//
// 5-minute time budget. Streams progress to a log file every 5 seconds:
// elapsed_ms, current_depth, max_depth_seen, nodes, propagations,
// backtracks. Final stats + best partial board dumped to the same file.

use std::io::Write;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit as _;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Board;
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_solver_engine::EngineSolver;
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
    fn new(path: &std::path::Path, period_ms: u64) -> std::io::Result<Self> {
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

        // Track max depth seen.
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

fn render_board(puzzle: &eternity2_core::Puzzle, board: &Board) -> String {
    // Compact ASCII board: one line per row, cell = piece_id:rot or "----:-".
    let mut out = String::new();
    for y in 0..puzzle.height {
        let mut row = String::new();
        for x in 0..puzzle.width {
            let pos = y * puzzle.width + x;
            match board.get(pos) {
                Some((pid, rot)) => row.push_str(&format!("{:>4}:{} ", u32::from(pid), rot.as_u8())),
                None => row.push_str("----:- "),
            }
        }
        out.push_str(&row);
        out.push('\n');
    }
    out
}

fn score_board(puzzle: &eternity2_core::Puzzle, board: &Board) -> (u32, u32) {
    use eternity2_core::Rotation;
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
            // East
            if x + 1 < w {
                if let Some((npid, nrot)) = board.get(y * w + (x + 1)) {
                    total += 1;
                    let np = puzzle.piece(npid).unwrap();
                    let ne = np.edges.rotated(nrot).as_array();
                    if e[1] == ne[3] { matched += 1; }
                }
            }
            // South
            if y + 1 < h {
                if let Some((npid, nrot)) = board.get((y + 1) * w + x) {
                    total += 1;
                    let np = puzzle.piece(npid).unwrap();
                    let ne = np.edges.rotated(nrot).as_array();
                    if e[2] == ne[0] { matched += 1; }
                }
            }
            let _ = Rotation::R0;
        }
    }
    (matched, total)
}

fn placed_count(b: &Board, puzzle: &eternity2_core::Puzzle) -> u32 {
    let mut n = 0;
    for pos in 0..puzzle.cell_count() { if b.get(pos).is_some() { n += 1; } }
    n
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let log_path = PathBuf::from("output/v12_run/run_e2_5min.log");
    let board_path = PathBuf::from("output/v12_run/run_e2_5min_board.json");
    std::fs::create_dir_all("output/v12_run").expect("mkdir");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let mut sink = ProgressSink::new(&log_path, 5_000).expect("open log");
    let header = format!(
        "=== vol-12 raw run on canonical Eternity II ===\n\
         puzzle: {}\n\
         size: {}x{} colors={} hints={}\n\
         profile: joe_depth150_par (gacolor + AC-3 + NS-1 + depth-150 gate + multi-core)\n\
         budget: 300_000 ms (5 min)\n\
         started: {}\n",
        puzzle_path.display(), puzzle.width, puzzle.height,
        puzzle.color_count - 1, hints.hints.len(),
        chrono_now()
    );
    sink.write_line(&header);
    eprintln!("{header}");

    let mut solver = EngineSolver::joe_depth150_par();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = 300_000;
    opts.seed = 1;
    opts.hints = hints;

    let t0 = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
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

    let mut summary = String::new();
    summary.push_str("\n=== FINAL RESULT ===\n");
    summary.push_str(&format!("verdict: {verdict}\n"));
    summary.push_str(&format!("wall_clock: {:.2} s\n", elapsed.as_secs_f64()));
    if let Some(s) = final_stats.as_ref() {
        summary.push_str(&format!(
            "nodes: {}\nbacktracks: {}\npropagations: {}\ndomain_wipeouts: {}\nmax_depth_seen: {}\nsolutions_found: {}\nnodes_per_sec: {:.0}\n",
            s.nodes, s.backtracks, s.propagations, s.domain_wipeouts,
            s.max_depth_seen, s.solutions_found,
            s.nodes as f64 / elapsed.as_secs_f64().max(1e-6)
        ));
    }
    if let Some(b) = board.as_ref() {
        let (matched, total) = score_board(&puzzle, b);
        let placed = placed_count(b, &puzzle);
        let internal_total = 2 * puzzle.width * puzzle.height - puzzle.width - puzzle.height;
        summary.push_str(&format!(
            "pieces_placed: {}/{}\nedge_matches: {}/{} (counting only placed-placed joins)\ninternal_total_edges: {}\n",
            placed, puzzle.cell_count(), matched, total, internal_total
        ));
        summary.push_str("\nBoard (piece_id:rotation):\n");
        summary.push_str(&render_board(&puzzle, b));
        // Dump board JSON too. FinalStats isn't serde-serializable in the
        // default events build, so unpack its fields manually.
        let stats_json = final_stats.as_ref().map(|s| serde_json::json!({
            "time_ms": s.time_ms,
            "nodes": s.nodes,
            "backtracks": s.backtracks,
            "propagations": s.propagations,
            "domain_wipeouts": s.domain_wipeouts,
            "current_depth": s.current_depth,
            "max_depth_seen": s.max_depth_seen,
            "solutions_found": s.solutions_found,
        }));
        let json = serde_json::json!({
            "schema_version": 1,
            "verdict": verdict,
            "elapsed_s": elapsed.as_secs_f64(),
            "pieces_placed": placed,
            "edge_matches": matched,
            "edge_total": total,
            "internal_total_edges": internal_total,
            "placement": (0..puzzle.cell_count()).map(|pos| {
                b.get(pos).map(|(pid, rot)| serde_json::json!({
                    "pos": pos,
                    "piece_id": u32::from(pid),
                    "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
            "final_stats": stats_json,
        });
        std::fs::write(&board_path, serde_json::to_string_pretty(&json).unwrap()).expect("write json");
    }
    sink.write_line(&summary);
    eprintln!("{summary}");
    eprintln!("log:   {}", log_path.display());
    eprintln!("board: {}", board_path.display());
}

fn chrono_now() -> String {
    // Minimal "yyyy-mm-dd HH:MM:SS" without chrono dep — use std::time + format.
    let now = std::time::SystemTime::now();
    let secs = now.duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    // We just stamp the unix seconds and let `date -d @sec` make sense of it
    // externally if needed.
    format!("(unix={secs})")
}
