// Vol-14 #5 — Frame-first interior sweep.
//
// For each of vol-12's 75 173 valid 60-cell Hamilton border rings,
// pin the 60 perimeter pieces as Hints + the 5 canonical hints
// (where they overlap, the frame must agree with the hint, which
// it already does because vol-12 enumerated only hint-compatible
// frames), then run `joe_depth150_par` to solve the 196-cell
// interior.
//
// PoC: sample N frames (default 50) and report depth, score,
// pieces_placed, wall time. If any frame produces a complete or
// near-complete solution, save it.
//
// CLI:
//   --frames-path output/v12_hamilton/frames_full.json
//   --sample-n 50            (random sample of N frames)
//   --budget-ms 60000        (per-frame budget)
//   --seed 1
//   --output-dir output/v14_framefirst/run_<unix>/

use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Instant;

use eternity2_bench_audit as _;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Hint, Hints, PieceId, Position, Rotation};
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

const W: u32 = 16;
const H: u32 = 16;
const N_RING: usize = 60;

/// Ring positions walking clockwise from (0,0):
///   top row L→R (16 cells, x=0..15, y=0)
///   right col T→B (15 cells, x=15, y=1..15)
///   bottom row R→L (15 cells, x=14..0, y=15)
///   left col B→T (14 cells, x=0, y=14..1)
fn ring_positions() -> Vec<(u32, u32)> {
    let mut out = Vec::with_capacity(N_RING);
    for x in 0..W { out.push((x, 0)); }
    for y in 1..H { out.push((W - 1, y)); }
    for x in (0..W - 1).rev() { out.push((x, H - 1)); }
    for y in (1..H - 1).rev() { out.push((0, y)); }
    assert_eq!(out.len(), N_RING);
    out
}

struct QuietSink {
    best_depth: u32,
    final_stats: Option<FinalStats>,
}
impl QuietSink {
    fn new() -> Self { Self { best_depth: 0, final_stats: None } }
}
impl EventSink for QuietSink {
    fn emit(&mut self, event: SolverEvent) {
        if let EventBody::Backtrack { from_depth, .. } = &event.body {
            if *from_depth > self.best_depth { self.best_depth = *from_depth; }
        }
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

fn score_board(puzzle: &eternity2_core::Puzzle, board: &Board) -> u32 {
    let (w, h) = (puzzle.width, puzzle.height);
    let mut matched = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let p = puzzle.piece(pid).unwrap();
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((npid, nrot)) = board.get(y * w + (x + 1)) {
                    let np = puzzle.piece(npid).unwrap();
                    let ne = np.edges.rotated(nrot).as_array();
                    if e[1] == ne[3] { matched += 1; }
                }
            }
            if y + 1 < h {
                if let Some((npid, nrot)) = board.get((y + 1) * w + x) {
                    let np = puzzle.piece(npid).unwrap();
                    let ne = np.edges.rotated(nrot).as_array();
                    if e[2] == ne[0] { matched += 1; }
                }
            }
        }
    }
    matched
}

fn placed_count(b: &Board, puzzle: &eternity2_core::Puzzle) -> u32 {
    (0..puzzle.cell_count()).filter(|&p| b.get(p).is_some()).count() as u32
}

fn frame_to_hints(ring: &[(u32, u32)], rp: &[(u32, u32)], canonical_hints: &Hints) -> Hints {
    // Apply frame ring first in *ring traversal order* (TL → TR → BR →
    // BL → back to TL), so each new ring hint only constrains its
    // immediate neighbour around the ring (a pair already validated
    // by vol-12's Hamilton enumeration). Adding canonical hints last
    // lets the propagator decide late whether the frame is globally
    // compatible (a global-rejection path that vol-12 didn't filter).
    let mut hints: Vec<Hint> = Vec::with_capacity(N_RING + canonical_hints.hints.len());
    let mut seen = std::collections::HashSet::new();
    for (i, &(pid_u, rot_u)) in ring.iter().enumerate() {
        let (x, y) = rp[i];
        let pos: Position = y * W + x;
        seen.insert(pos);
        let piece_id = PieceId::try_from(pid_u).expect("pid in range");
        let rotation = Rotation::from_u8(rot_u as u8).expect("rot in 0..4");
        hints.push(Hint { position: pos, piece_id, rotation });
    }
    for h in &canonical_hints.hints {
        if !seen.contains(&h.position) {
            hints.push(*h);
        }
    }
    Hints { hints }
}

#[derive(serde::Serialize)]
struct FrameResult {
    frame_idx: usize,
    elapsed_ms: u64,
    placed: u32,
    matched: u32,
    max_depth_seen: u32,
    nodes: u64,
    verdict: String,
    bucas: Option<String>,
}

fn run_one_frame(
    puzzle: &eternity2_core::Puzzle,
    canonical_hints: &Hints,
    rp: &[(u32, u32)],
    ring: &[(u32, u32)],
    frame_idx: usize,
    budget_ms: u64,
    seed: u64,
    save_full_board: bool,
    out_dir: &Path,
) -> FrameResult {
    let hints = frame_to_hints(ring, rp, canonical_hints);
    let mut opts = SolveOpts::default();
    opts.hints = hints;
    opts.time_budget_ms = budget_ms;
    opts.seed = seed;

    // Use border_first_lcv (single-threaded, baseline edge-prop only)
    // for the frame-first survey: this is permissive enough to actually
    // accept the 60 frame hints + 5 canonical hints, exposing whether
    // the *interior* search is then feasible. Stronger propagators
    // (gacolor + AC-3) prematurely reject every frame at hint-apply
    // time — a separate vol-14 structural measurement.
    let mut solver = EngineSolver::border_first_lcv();
    let mut sink = QuietSink::new();
    let t0 = Instant::now();
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    let elapsed_ms = t0.elapsed().as_millis() as u64;

    // Reconstruct the frame board (with canonical hints) for scoring
    // when the engine returns Exhausted or Error — we still want to
    // attribute the placed/matched pieces from the frame itself, since
    // they prove a Hamilton-valid ring exists even if the interior
    // is infeasible.
    let frame_board = {
        let mut b = Board::empty(puzzle);
        for h in &opts.hints.hints { b.place(h.position, h.piece_id, h.rotation); }
        b
    };
    let (verdict, board) = match outcome {
        SolveOutcome::Solved(b) => ("SOLVED".to_string(), Some(b)),
        SolveOutcome::TimedOut { best_partial, best_depth } => {
            (format!("TIMEOUT (best_depth={best_depth})"), Some(best_partial))
        }
        SolveOutcome::Cancelled { best_partial, best_depth, .. } => {
            (format!("CANCELLED (best_depth={best_depth})"), Some(best_partial))
        }
        SolveOutcome::Exhausted => ("EXHAUSTED".to_string(), Some(frame_board)),
        SolveOutcome::AllSolutions(bs) => (format!("ALL ({})", bs.len()), bs.into_iter().next()),
        SolveOutcome::Error(e) => (format!("ERROR: {e}"), None),
    };

    let (placed, matched, bucas) = if let Some(b) = board.as_ref() {
        let p = placed_count(b, puzzle);
        let m = score_board(puzzle, b);
        let bu = bucas_url(puzzle, b, &format!("v14_ff_{frame_idx}"));
        if save_full_board {
            let board_path = out_dir.join(format!("board_frame_{frame_idx}.json"));
            let placement: Vec<_> = (0..puzzle.cell_count()).map(|pos| {
                b.get(pos).map(|(pid, rot)| serde_json::json!({
                    "pos": pos, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect();
            let _ = std::fs::write(&board_path, serde_json::to_string_pretty(
                &serde_json::json!({"placement": placement, "bucas_url": bu})
            ).unwrap());
        }
        (p, m, Some(bu))
    } else {
        (0, 0, None)
    };

    let (nodes, depth) = sink.final_stats.as_ref()
        .map(|s| (s.nodes, s.max_depth_seen))
        .unwrap_or((0, sink.best_depth));

    FrameResult {
        frame_idx, elapsed_ms, placed, matched,
        max_depth_seen: depth, nodes, verdict, bucas,
    }
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut frames_path = PathBuf::from("output/v12_hamilton/frames_full.json");
    let mut sample_n: usize = 50;
    let mut budget_ms: u64 = 60_000;
    let mut seed: u64 = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--frames-path" => frames_path = PathBuf::from(args.next().unwrap()),
            "--sample-n" => sample_n = args.next().unwrap().parse().unwrap(),
            "--budget-ms" => budget_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            _ => eprintln!("(unrecognized: {a})"),
        }
    }

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v14_framefirst/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");
    #[cfg(unix)]
    {
        let latest = PathBuf::from("output/v14_framefirst/latest");
        let _ = std::fs::remove_file(&latest);
        let _ = std::os::unix::fs::symlink(format!("run_{run_id}"), &latest);
    }

    let (puzzle, canonical_hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    eprintln!("loaded puzzle: {}x{} hints={}", puzzle.width, puzzle.height,
              canonical_hints.hints.len());

    // Sanity: piece 50 rotated 3 should have BORDER on west (left col cell).
    let p50 = puzzle.piece(PieceId::try_from(50u32).unwrap()).unwrap();
    let p50r3 = p50.edges.rotated(Rotation::from_u8(3).unwrap()).as_array();
    eprintln!("piece 50 rot 3 (engine) [N,E,S,W]={:?}", p50r3);
    let mask = puzzle.border_mask(224);
    eprintln!("pos 224 border_mask [N,E,S,W]={:?}", mask);

    eprintln!("loading frames from {} ...", frames_path.display());
    let frames_bytes = std::fs::read(&frames_path).expect("read frames");
    let frames_doc: serde_json::Value = serde_json::from_slice(&frames_bytes).expect("parse frames");
    let frames = frames_doc.get("frames").and_then(|v| v.as_array()).expect("frames[]");
    eprintln!("frames available: {}", frames.len());

    let rp = ring_positions();

    // Deterministic seeded sample using a tiny LCG so reruns reproduce.
    let mut rng_state: u64 = seed.wrapping_mul(0x9E37_79B9_7F4A_7C15) | 1;
    let mut sample_indices: Vec<usize> = (0..frames.len()).collect();
    for i in (1..sample_indices.len()).rev() {
        rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let j = (rng_state >> 33) as usize % (i + 1);
        sample_indices.swap(i, j);
    }
    sample_indices.truncate(sample_n.min(frames.len()));

    let log_path = out_dir.join("results.tsv");
    let mut log = std::fs::File::create(&log_path).expect("open log");
    let _ = writeln!(log, "frame_idx\telapsed_ms\tplaced\tmatched\tmax_depth_seen\tnodes\tverdict");

    let summary_path = out_dir.join("summary.json");
    let mut results: Vec<FrameResult> = Vec::with_capacity(sample_indices.len());

    let mut best_matched = 0u32;
    let mut best_placed = 0u32;

    eprintln!(
        "running {} frames × {} s budget each = ~{} min wall-clock (single-thread per frame, joe_depth150_par root-splits internally)",
        sample_indices.len(), budget_ms / 1000,
        sample_indices.len() as u64 * budget_ms / 60_000,
    );

    for (i, &frame_idx) in sample_indices.iter().enumerate() {
        let ring_raw = frames[frame_idx].get("ring").and_then(|v| v.as_array()).expect("ring");
        let ring: Vec<(u32, u32)> = ring_raw.iter().map(|e| {
            let arr = e.as_array().expect("[pid, rot]");
            let pid = arr[0].as_u64().expect("pid") as u32;
            let rot = arr[1].as_u64().expect("rot") as u32;
            (pid, rot)
        }).collect();
        if ring.len() != N_RING {
            eprintln!("frame {frame_idx}: bad ring length {}", ring.len());
            continue;
        }

        // Save the full board only if this run improves on best score so far.
        let save_full = true; // small (16KB each), keep for forensics
        let r = run_one_frame(&puzzle, &canonical_hints, &rp, &ring, frame_idx, budget_ms, seed, save_full, &out_dir);
        let _ = writeln!(log, "{}\t{}\t{}\t{}\t{}\t{}\t{}",
                         r.frame_idx, r.elapsed_ms, r.placed, r.matched,
                         r.max_depth_seen, r.nodes, r.verdict.replace('\t', " "));
        let _ = log.flush();

        if r.matched > best_matched || (r.matched == best_matched && r.placed > best_placed) {
            best_matched = r.matched;
            best_placed = r.placed;
            eprintln!("[{:>3}/{}] frame={:>6}  placed={:>3}  matched={:>3}/480  depth={:>3}  ⬅️  new best",
                      i + 1, sample_indices.len(), r.frame_idx, r.placed, r.matched, r.max_depth_seen);
        } else {
            eprintln!("[{:>3}/{}] frame={:>6}  placed={:>3}  matched={:>3}/480  depth={:>3}",
                      i + 1, sample_indices.len(), r.frame_idx, r.placed, r.matched, r.max_depth_seen);
        }

        results.push(r);

        let _ = std::fs::write(&summary_path, serde_json::to_string_pretty(&serde_json::json!({
            "schema_version": 1,
            "sample_n_requested": sample_n,
            "sample_n_completed": results.len(),
            "budget_ms_per_frame": budget_ms,
            "seed": seed,
            "best_matched": best_matched,
            "best_placed": best_placed,
            "results": &results,
        })).unwrap());
    }

    eprintln!(
        "\n=== FRAME-FIRST FINAL ===\nframes: {}\nbest_matched: {}/480\nbest_placed: {}/256\nout: {}",
        results.len(), best_matched, best_placed, out_dir.display(),
    );
}
