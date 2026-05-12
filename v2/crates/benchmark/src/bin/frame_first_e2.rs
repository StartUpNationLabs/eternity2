// Frame-first decomposition for Eternity II.
//
// Per RESEARCH_NOTES_4 SESSION 2: ALNS confirms the pinned-boundary
// obstruction is universal — local search holding the border fixed
// cannot break 449. The Phase-C diagnostic showed the outer ring is
// trivially 100% feasible across all PT runs, and the hard region
// is the 10×10 center.
//
// Hypothesis: PT converges to the SAME border across all runs
// (vol. 2 observation: "all 6 plateau states share the SAME border").
// This means we've been exploring a single border-fixed basin. With
// a DIFFERENT border, PT may reach a different interior basin —
// possibly past 449.
//
// Pipeline:
//   1. Generate diverse border candidates via gacolor_ac3_random_par
//      with different seeds. Each seed produces a different CP
//      partial; we extract the border cells of each.
//   2. Deduplicate by (border-cell -> piece-rotation) signature.
//   3. For each unique border: run cell-CP→PT on the interior with
//      the border pinned. Report score.
//   4. Keep the best (border, full_score) pair.
//
// Schaus-Deville 2008 reached 458 with a similar idea. Wauters 2012
// reached 461. Our session-2 baseline is 449. The gap is what
// frame-first is designed to close.

use std::collections::BTreeMap;
use std::io::Write;
use std::path::PathBuf;
use std::time::Instant;

fn flush_err() {
    let _ = std::io::stderr().flush();
}

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::{puzzle_name_from_path, write_report};
use eternity2_core::{Board, Hint, Hints, Piece, PieceId, Position, Puzzle, BORDER};
use eternity2_events::BufferSink;
use eternity2_localsearch::{run_pt_from, PtConfig};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

#[derive(Parser, Debug)]
#[command(name = "frame_first_e2", about = "Frame-first decomposition for E2")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// Number of border candidates to generate via diverse-seed CP.
    #[arg(long, default_value_t = 16)]
    n_borders: u32,

    /// Per-candidate CP-on-interior budget (seconds).
    #[arg(long, default_value_t = 30)]
    cp_seconds: u64,

    /// Per-candidate PT-on-interior budget (seconds). Set 0 to skip PT.
    #[arg(long, default_value_t = 60)]
    pt_seconds: u64,

    /// Border-generation CP budget per seed (seconds).
    #[arg(long, default_value_t = 10)]
    border_gen_seconds: u64,

    /// Base seed; per-candidate seed = base + i.
    #[arg(long, default_value_t = 0xFA_FE_F0_F1)]
    base_seed: u64,

    /// Total wall-clock budget (seconds); 0 = no global limit.
    #[arg(long, default_value_t = 0)]
    total_seconds: u64,

    /// Explicit comma-separated list of u64 seeds to use, overriding
    /// `base_seed` + `n_borders`. Used by stage-2/3 of the overnight
    /// funnel to focus on borders that performed well in stage 1.
    #[arg(long)]
    seeds_list: Option<String>,

    /// PT seed offset relative to the border seed. Default 0 means
    /// (border_seed, pt_seed) = (s, s). Set to non-zero to use a
    /// different PT trajectory for the same border.
    #[arg(long, default_value_t = 0)]
    pt_seed_offset: u64,

    /// Path to a per-candidate checkpoint JSON. Updated after every
    /// candidate so an aborted run still preserves intermediate
    /// results. Default: output/frame_first_e2_checkpoint.json.
    #[arg(long, default_value = "output/frame_first_e2_checkpoint.json")]
    checkpoint_path: PathBuf,

    /// Label to embed in the checkpoint JSON (e.g., "stage1").
    #[arg(long, default_value = "default")]
    run_label: String,
}

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.pieces().iter().find(|p| p.id == id)
}

fn score_board(puzzle: &Puzzle, board: &Board) -> (u32, u32) {
    let w = puzzle.width;
    let h = puzzle.height;
    let total = (w - 1) * h + w * (h - 1);
    let mut matches = 0u32;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue };
            let Some(p) = lookup_piece(puzzle, pid) else { continue };
            let e = p.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup_piece(puzzle, rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        if e[1] == re[3] && e[1] != BORDER && e[1] != 0 { matches += 1; }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        if e[2] == be[0] && e[2] != BORDER && e[2] != 0 { matches += 1; }
                    }
                }
            }
        }
    }
    (matches, total)
}

fn pct(n: u32, d: u32) -> f64 { 100.0 * (n as f64) / (d as f64) }

fn is_border_cell(puzzle: &Puzzle, pos: Position) -> bool {
    let m = puzzle.border_mask(pos);
    m.iter().any(|&b| b)
}

/// Extract border-cell placements from a (possibly partial) board.
/// Returns a Vec<Hint> covering ONLY the border cells that have a
/// piece placed. Empty if the board has no border placements.
fn extract_border_hints(puzzle: &Puzzle, board: &Board) -> Vec<Hint> {
    let mut out = Vec::new();
    for pos in 0..puzzle.cell_count() {
        if is_border_cell(puzzle, pos) {
            if let Some((pid, rot)) = board.get(pos) {
                out.push(Hint { position: pos, piece_id: pid, rotation: rot });
            }
        }
    }
    out
}

/// A border "signature" — the sorted list of (position, piece_id, rotation)
/// for all border cells. Used to deduplicate borders across seeds.
type BorderSig = Vec<(Position, PieceId, u8)>;

fn signature(hints: &[Hint]) -> BorderSig {
    let mut s: Vec<(Position, PieceId, u8)> = hints.iter()
        .map(|h| (h.position, h.piece_id, h.rotation.as_u8()))
        .collect();
    s.sort();
    s
}

fn solve_with_seed(
    puzzle: &Puzzle,
    base_hints: &Hints,
    seed: u64,
    budget_s: u64,
) -> Option<Board> {
    let mut solver = EngineSolver::gacolor_ac3_random_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_s * 1000;
    opts.hints = base_hints.clone();
    opts.seed = seed;
    let out = solver.solve(puzzle, &opts, &mut sink);
    match out {
        SolveOutcome::Solved(b) => Some(b),
        SolveOutcome::TimedOut { best_partial, .. } | SolveOutcome::Cancelled { best_partial, .. } => Some(best_partial),
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next(),
        _ => None,
    }
}

fn solve_interior_with_border(
    puzzle: &Puzzle,
    base_hints: &Hints,
    border_hints: &[Hint],
    budget_s: u64,
    seed: u64,
) -> Option<Board> {
    // Merge: official hints + border hints. Dedupe by position.
    let mut hs: Vec<Hint> = Vec::new();
    let mut seen_pos = std::collections::BTreeSet::new();
    for h in &base_hints.hints { if seen_pos.insert(h.position) { hs.push(h.clone()); } }
    for h in border_hints { if seen_pos.insert(h.position) { hs.push(h.clone()); } }

    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_s * 1000;
    opts.hints = Hints::new(hs);
    opts.seed = seed;
    let out = solver.solve(puzzle, &opts, &mut sink);
    match out {
        SolveOutcome::Solved(b) => Some(b),
        SolveOutcome::TimedOut { best_partial, .. } | SolveOutcome::Cancelled { best_partial, .. } => Some(best_partial),
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next(),
        _ => None,
    }
}

fn run_pt_on(
    puzzle: &Puzzle,
    seed_board: &Board,
    pinned: Vec<Position>,
    pt_seconds: u64,
    seed: u64,
) -> Board {
    let pt_cfg = PtConfig {
        n_replicas: 8,
        t_min: 0.05, t_max: 2.0,
        inner_iters: 100_000,
        max_rounds: 0,
        time_budget_ms: pt_seconds * 1000,
        seed,
        verbose: false,
        greedy_fill: true,
        diversify_fill: false,
        repair_every: 0, repair_k: 4, repair_budget_ms: 200,
        kick_every: 0, kick_n_swaps: 20,
        pinned_positions: pinned,
        houdayer_every: 0, houdayer_max_component: 20, houdayer_min_component: 4,
        houdayer_accept_zero_delta: false,
    forbidden_edges: Vec::new(),
    forbidden_penalty_k: 0,
    };
    let (out, _stats) = run_pt_from(puzzle, seed_board, &pt_cfg);
    out.best_board
}

fn main() {
    let args = Args::parse();
    eprintln!("=== FRAME-FIRST DECOMPOSITION ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("n_borders={} border_gen_s={} cp_s={} pt_s={} total_s={} run_label={}",
        args.n_borders, args.border_gen_seconds, args.cp_seconds, args.pt_seconds,
        args.total_seconds, args.run_label);
    flush_err();

    let (puzzle, file_hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    eprintln!("loaded {}×{}, {} pieces, {} colors, {} official hints",
        puzzle.width, puzzle.height, puzzle.pieces().len(),
        puzzle.color_count - 1, file_hints.hints.len());

    let n_border_cells: u32 = (0..puzzle.cell_count()).filter(|&p| is_border_cell(&puzzle, p)).count() as u32;
    eprintln!("expected border cells: {}", n_border_cells);
    flush_err();

    // Build seed iterator: either explicit list (stage 2/3) or
    // base_seed + 0..n_borders (stage 1 / default).
    let seeds: Vec<u64> = if let Some(list) = &args.seeds_list {
        let parsed: Vec<u64> = list.split(',')
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .map(|s| {
                if let Some(hex) = s.strip_prefix("0x") {
                    u64::from_str_radix(hex, 16).expect("seeds_list: bad hex u64")
                } else {
                    s.parse::<u64>().expect("seeds_list: bad u64")
                }
            })
            .collect();
        eprintln!("using explicit seeds_list: {} seeds", parsed.len());
        parsed
    } else {
        (0..args.n_borders).map(|i| args.base_seed.wrapping_add(i as u64)).collect()
    };
    eprintln!("seeds to process: {}", seeds.len());
    flush_err();

    // Ensure checkpoint parent exists.
    if let Some(parent) = args.checkpoint_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    let t_global = Instant::now();
    let mut seen: BTreeMap<BorderSig, u32> = BTreeMap::new();
    let mut best: (u32, u32, Option<Board>, u64) = (0, 0, None, 0); // (score, total, board, seed_used)
    // (seed, border_filled, cp_score, pt_score, bucas_url_of_final_board).
    // Adding the bucas URL is what enables downstream filtering (e.g. by
    // top-6 universal-mismatch matches). The URL is the canonical
    // serialisation we use everywhere; it's 1 KB per board so the
    // checkpoint stays small even for 100 candidates.
    let mut interior_stats: Vec<(u64, u32, u32, u32, String)> = Vec::new();

    // Helper to (re)write the checkpoint. Called after every successful
    // candidate AND once before the loop so jq always has a parseable
    // file even if every candidate fails.
    let write_checkpoint = |interior_stats: &Vec<(u64, u32, u32, u32, String)>,
                            best: &(u32, u32, Option<Board>, u64),
                            t_global: &Instant| {
        let best_url = best.2.as_ref().map(|b| {
            eternity2_benchmark::report::bucas_url(
                &puzzle, b, &puzzle_name_from_path(&args.puzzle),
            )
        });
        let checkpoint = serde_json::json!({
            "run_label": args.run_label,
            "n_candidates_done": interior_stats.len(),
            "n_seeds_planned": seeds.len(),
            "elapsed_s": t_global.elapsed().as_secs_f64(),
            "border_gen_seconds": args.border_gen_seconds,
            "cp_seconds": args.cp_seconds,
            "pt_seconds": args.pt_seconds,
            "pt_seed_offset": args.pt_seed_offset,
            "best": {
                "score": best.0,
                "total": best.1,
                "seed": best.3,
                "seed_hex": format!("0x{:x}", best.3),
                "bucas_url": best_url,
            },
            "per_border": interior_stats.iter().map(|(s, b, c, p, url)| serde_json::json!({
                "seed": s, "seed_hex": format!("0x{:x}", s),
                "border_filled": b, "cp_score": c, "pt_score": p,
                "bucas_url": url,
            })).collect::<Vec<_>>(),
        });
        let tmp = args.checkpoint_path.with_extension("json.tmp");
        if let Ok(s) = serde_json::to_string_pretty(&checkpoint) {
            if std::fs::write(&tmp, &s).is_ok() {
                let _ = std::fs::rename(&tmp, &args.checkpoint_path);
            }
        }
    };
    // Write an initial empty checkpoint so jq always has a parseable file.
    write_checkpoint(&interior_stats, &best, &t_global);

    for (i, &seed) in seeds.iter().enumerate() {
        if args.total_seconds > 0 && t_global.elapsed().as_secs() >= args.total_seconds {
            eprintln!("\n[budget reached at i={i}, stopping]");
            flush_err();
            break;
        }
        eprintln!("\n--- Border candidate {} (seed=0x{:x}) ---", i + 1, seed);
        flush_err();

        // Phase 1: generate a candidate via random-tiebreaker CP.
        let t1 = Instant::now();
        let cand = match solve_with_seed(&puzzle, &file_hints, seed, args.border_gen_seconds) {
            Some(b) => b,
            None => { eprintln!("  border-gen failed"); continue; }
        };
        let border_hints = extract_border_hints(&puzzle, &cand);
        let n_filled = border_hints.len() as u32;
        eprintln!("  border-gen elapsed: {:.1}s, border cells filled: {}/{}",
            t1.elapsed().as_secs_f64(), n_filled, n_border_cells);
        flush_err();

        if n_filled < n_border_cells {
            eprintln!("  partial border (not all {} cells filled); using anyway", n_border_cells);
        }

        let sig = signature(&border_hints);
        if let Some(prev) = seen.get(&sig) {
            eprintln!("  duplicate border (also seen at i={}); skipping interior solve", prev);
            continue;
        }
        seen.insert(sig.clone(), i as u32);

        // Phase 2: interior CP conditioned on this border.
        let t2 = Instant::now();
        let cp_board = match solve_interior_with_border(&puzzle, &file_hints, &border_hints, args.cp_seconds, seed) {
            Some(b) => b,
            None => { eprintln!("  interior CP failed"); continue; }
        };
        let (cp_s, cp_t) = score_board(&puzzle, &cp_board);
        eprintln!("  interior CP elapsed: {:.1}s, score: {}/{} ({:.1}%)",
            t2.elapsed().as_secs_f64(), cp_s, cp_t, pct(cp_s, cp_t));
        flush_err();

        // Phase 3: PT on the interior result (if budget > 0).
        let final_board = if args.pt_seconds > 0 {
            let t3 = Instant::now();
            // Pin: official hints AND the border. Interior remains free.
            let mut pinned: Vec<Position> = file_hints.hints.iter().map(|h| h.position).collect();
            for h in &border_hints { if !pinned.contains(&h.position) { pinned.push(h.position); } }
            let pt_seed = seed.wrapping_add(args.pt_seed_offset);
            let pt_board = run_pt_on(&puzzle, &cp_board, pinned, args.pt_seconds, pt_seed);
            let (pt_s, pt_t) = score_board(&puzzle, &pt_board);
            eprintln!("  PT elapsed: {:.1}s, score: {}/{} ({:.1}%)",
                t3.elapsed().as_secs_f64(), pt_s, pt_t, pct(pt_s, pt_t));
            flush_err();
            let url = eternity2_benchmark::report::bucas_url(
                &puzzle, &pt_board, &puzzle_name_from_path(&args.puzzle));
            interior_stats.push((seed, n_filled, cp_s, pt_s, url));
            pt_board
        } else {
            let url = eternity2_benchmark::report::bucas_url(
                &puzzle, &cp_board, &puzzle_name_from_path(&args.puzzle));
            interior_stats.push((seed, n_filled, cp_s, cp_s, url));
            cp_board
        };

        let (s, t) = score_board(&puzzle, &final_board);
        if s > best.0 {
            eprintln!("  *** NEW BEST: {}/{} (was {}) ***", s, t, best.0);
            best = (s, t, Some(final_board.clone()), seed);
        }
        flush_err();
        write_checkpoint(&interior_stats, &best, &t_global);
    }

    eprintln!("\n=== SUMMARY ===");
    eprintln!("borders tried: {} unique out of {} attempts", seen.len(), args.n_borders);
    eprintln!("best overall: {}/{} ({:.1}%) at seed=0x{:x}",
        best.0, best.1, pct(best.0, best.1), best.3);
    eprintln!("per-border (seed, border_filled, cp_score, pt_score):");
    for (s, b, c, p, _url) in &interior_stats {
        eprintln!("  seed=0x{:x} border={} cp={} pt={}", s, b, c, p);
    }

    if let Some(board) = best.2 {
        let output_dir = std::path::PathBuf::from("output");
        let puzzle_name = puzzle_name_from_path(&args.puzzle);
        let extra = serde_json::json!({
            "frame_first": {
                "n_borders_attempted": args.n_borders,
                "unique_borders": seen.len(),
                "border_gen_seconds": args.border_gen_seconds,
                "cp_seconds": args.cp_seconds,
                "pt_seconds": args.pt_seconds,
                "best_seed": best.3,
                "per_border": interior_stats.iter().map(|(s, b, c, p, url)| {
                    serde_json::json!({"seed": s, "border_filled": b, "cp_score": c, "pt_score": p, "bucas_url": url})
                }).collect::<Vec<_>>(),
            },
            "base_seed": args.base_seed,
        });
        if let Ok(r) = write_report(&output_dir, "frame_first_e2", &puzzle, &puzzle_name, &board, extra) {
            eprintln!("\nReport: {}", r.json_path.display());
            eprintln!("Bucas:  {}", r.url);
        }
    }
}
