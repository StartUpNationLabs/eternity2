// RTCP — Region-Tear with CP. A novel hybrid for hard edge-matching puzzles.
//
// Standard CP→LS hybrids feed a single CP partial into local search and
// hope SA can polish it. On Eternity II this saturates ~65% because SA
// can't coordinate the multi-piece swaps needed to fix bad regions.
//
// RTCP's bet: use CP itself as the repair operator.
//   1. Run CP → best_partial (we already get ~62% on E2 in 60s).
//   2. Compute the "matched-edge consistency graph" of placed cells.
//   3. Find the largest connected component of cells whose internal
//      edges all match — the "good anchor".
//   4. Pin every cell in the anchor as a hint, leave the rest free.
//   5. Re-run CP. Now CP only needs to solve N - |anchor| cells, with
//      the anchor's outer boundary providing strong color constraints
//      on the freed cells' domains.
//   6. Iterate: a successful repair becomes the new partial, find the
//      next anchor, etc. If CP can't repair (timeout / wipeout), grow
//      the tear (drop the smallest matched components from the anchor).
//
// To my knowledge this is not in the literature. Community hybrids use
// LS (Wauters 5-operator, Verhaard piece-pairing) for repair; nobody
// uses CP recursively as the repair engine.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::{puzzle_name_from_path, write_report};
use eternity2_core::{Board, Hint, Hints, Piece, PieceId, Position, Puzzle, BORDER};
use eternity2_events::BufferSink;
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

#[derive(Parser, Debug)]
#[command(name = "rtcp", about = "Region-Tear with CP — iterative CP-based repair")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// Initial CP phase budget in seconds.
    #[arg(long, default_value_t = 60)]
    cp_seconds: u64,

    /// Per-repair CP budget in seconds.
    #[arg(long, default_value_t = 30)]
    repair_seconds: u64,

    /// Maximum number of repair iterations.
    #[arg(long, default_value_t = 40)]
    max_iterations: u32,

    /// Total wall-clock cap for the whole RTCP loop in seconds.
    #[arg(long, default_value_t = 600)]
    total_seconds: u64,

    /// Hint cells must be in a matched component of at least this size to
    /// be considered an "anchor". Smaller = more tearing per round.
    #[arg(long, default_value_t = 8)]
    min_component_size: u32,

    /// If a repair fails (no improvement), shrink the anchor by this fraction.
    /// 0.10 = drop 10% of anchor cells (the worst-matched 10%) and retry.
    #[arg(long, default_value_t = 0.10)]
    shrink_factor: f64,

    /// Honour hints from the puzzle file.
    #[arg(long, default_value_t = true)]
    use_hints: bool,
}

// ---------- scoring ----------

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.piece(id)
}

// Count matched non-border edges on the board. Also return the set of
// (pos, neighbor_pos) pairs that are matched, for component analysis.
fn score_and_match_set(puzzle: &Puzzle, board: &Board) -> (u32, u32, Vec<(Position, Position)>) {
    let w = puzzle.width;
    let h = puzzle.height;
    let total = (w - 1) * h + w * (h - 1);
    let mut matches = 0u32;
    let mut pairs = Vec::new();
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let Some(piece) = lookup_piece(puzzle, pid) else { continue; };
            let e = piece.edges.rotated(rot).as_array();
            if x + 1 < w {
                let rpos = y * w + (x + 1);
                if let Some((rpid, rrot)) = board.get(rpos) {
                    if let Some(rp) = lookup_piece(puzzle, rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        if e[1] == re[3] && e[1] != BORDER && e[1] != 0 {
                            matches += 1;
                            pairs.push((pos, rpos));
                        }
                    }
                }
            }
            if y + 1 < h {
                let bpos = (y + 1) * w + x;
                if let Some((bpid, brot)) = board.get(bpos) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        if e[2] == be[0] && e[2] != BORDER && e[2] != 0 {
                            matches += 1;
                            pairs.push((pos, bpos));
                        }
                    }
                }
            }
        }
    }
    (matches, total, pairs)
}

fn placed_count(board: &Board) -> u32 {
    board.cells().iter().filter(|c| c.is_some()).count() as u32
}

// ---------- consistency components ----------
//
// Union-find over placed cells, joined when their shared edge matches.
// A "good anchor" = a connected component of placed cells where every
// internal edge matches. Equivalently: union along matched-edge pairs.
struct DSU { parent: Vec<u32>, size: Vec<u32> }

impl DSU {
    fn new(n: u32) -> Self {
        Self { parent: (0..n).collect(), size: vec![1; n as usize] }
    }
    fn find(&mut self, x: u32) -> u32 {
        let mut r = x;
        while self.parent[r as usize] != r { r = self.parent[r as usize]; }
        let mut cur = x;
        while self.parent[cur as usize] != r {
            let next = self.parent[cur as usize];
            self.parent[cur as usize] = r;
            cur = next;
        }
        r
    }
    fn union(&mut self, a: u32, b: u32) {
        let ra = self.find(a);
        let rb = self.find(b);
        if ra == rb { return; }
        let (small, big) = if self.size[ra as usize] < self.size[rb as usize] { (ra, rb) } else { (rb, ra) };
        self.parent[small as usize] = big;
        self.size[big as usize] += self.size[small as usize];
    }
}

// Build matched components. Returns vec[pos] -> Option<component_root>.
// Cells with no placement get None. Cells in a singleton "matched"
// component (no matched edges to any neighbor) get their own root.
fn matched_components(puzzle: &Puzzle, board: &Board, pairs: &[(Position, Position)])
    -> (Vec<Option<u32>>, Vec<u32>)
{
    let n = puzzle.cell_count();
    let mut dsu = DSU::new(n);
    for &(a, b) in pairs { dsu.union(a, b); }
    let mut roots: Vec<Option<u32>> = vec![None; n as usize];
    let mut size_by_root = vec![0u32; n as usize];
    for pos in 0..n {
        if board.get(pos).is_some() {
            let r = dsu.find(pos);
            roots[pos as usize] = Some(r);
            size_by_root[r as usize] += 1;
        }
    }
    (roots, size_by_root)
}

// ---------- anchor selection ----------
//
// Strategy B (revised): anchor = placed cells whose ALL edges to placed
// neighbors are matched. These are "locally perfect" cells. Then we
// also drop cells whose containing matched-component is smaller than
// `min_component_size` — singletons/dust isn't worth pinning.
fn select_anchor(
    puzzle: &Puzzle,
    board: &Board,
    pairs: &[(Position, Position)],
    min_component_size: u32,
) -> (Vec<bool>, u32) {
    let n = puzzle.cell_count() as usize;
    let w = puzzle.width;
    let h = puzzle.height;

    // matched_count[pos] = # of edges to placed neighbors that match.
    let mut matched = vec![0u32; n];
    let mut placed_neighbors = vec![0u32; n];
    for pos in 0..n as u32 {
        if board.get(pos).is_none() { continue; }
        let (x, y) = puzzle.xy(pos);
        for (dx, dy) in [(1i32, 0i32), (-1, 0), (0, 1), (0, -1)] {
            let nx = x as i32 + dx;
            let ny = y as i32 + dy;
            if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 { continue; }
            let np = (ny as u32) * w + nx as u32;
            if board.get(np).is_some() {
                placed_neighbors[pos as usize] += 1;
            }
        }
    }
    for &(a, b) in pairs {
        matched[a as usize] += 1;
        matched[b as usize] += 1;
    }

    let (roots, sizes) = matched_components(puzzle, board, pairs);

    let mut anchor = vec![false; n];
    let mut count = 0u32;
    for pos in 0..n {
        if board.get(pos as Position).is_none() { continue; }
        // Locally perfect: every placed-neighbor edge matches.
        if matched[pos] != placed_neighbors[pos] { continue; }
        // Big-enough component.
        if let Some(r) = roots[pos] {
            if sizes[r as usize] >= min_component_size {
                anchor[pos] = true;
                count += 1;
            }
        }
    }
    (anchor, count)
}

// Shrink anchor: drop the smallest matched-component still in the anchor
// (fallback) OR drop the boundary cells with the fewest matched neighbors.
fn shrink_anchor(
    puzzle: &Puzzle,
    board: &Board,
    pairs: &[(Position, Position)],
    anchor: &mut Vec<bool>,
    fraction: f64,
) -> u32 {
    let (roots, sizes) = matched_components(puzzle, board, pairs);
    // Per-cell matched-neighbor count (within anchor).
    let n = puzzle.cell_count() as usize;
    let w = puzzle.width as i32;
    let h = puzzle.height as i32;
    let mut score = vec![0i32; n];
    for &(a, b) in pairs {
        if anchor[a as usize] && anchor[b as usize] {
            score[a as usize] += 1;
            score[b as usize] += 1;
        }
    }
    // Take the bottom-`fraction` of anchor cells by score, drop them.
    let mut indexed: Vec<(usize, i32)> = anchor.iter().enumerate()
        .filter_map(|(i, &a)| if a { Some((i, score[i])) } else { None })
        .collect();
    indexed.sort_by_key(|&(_, s)| s);
    let drop_n = ((indexed.len() as f64) * fraction).ceil() as usize;
    let drop_n = drop_n.max(1);
    let mut dropped = 0u32;
    for &(i, _) in indexed.iter().take(drop_n) {
        anchor[i] = false;
        dropped += 1;
    }
    let _ = (roots, sizes, w, h);
    dropped
}

// Convert (anchor mask + board) into Hints for the CP solver.
fn anchor_to_hints(board: &Board, anchor: &[bool]) -> Hints {
    let mut hs = Vec::new();
    for (i, &is_anchor) in anchor.iter().enumerate() {
        if !is_anchor { continue; }
        if let Some((pid, rot)) = board.get(i as Position) {
            hs.push(Hint { position: i as Position, piece_id: pid, rotation: rot });
        }
    }
    Hints::new(hs)
}

fn run_cp_with_hints(puzzle: &Puzzle, hints: Hints, budget_ms: u64) -> Board {
    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.hints = hints;
    match solver.solve(puzzle, &opts, &mut sink) {
        SolveOutcome::Solved(b) => b,
        SolveOutcome::TimedOut { best_partial, .. } => best_partial,
        SolveOutcome::Cancelled { best_partial, .. } => best_partial,
        SolveOutcome::Exhausted => Board::empty(puzzle),
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(puzzle)),
        SolveOutcome::Error(_) => Board::empty(puzzle),
    }
}

// Returns the board from the (possibly partial) CP outcome; surfaces Error.
fn run_cp_with_hints_strict(puzzle: &Puzzle, hints: Hints, budget_ms: u64) -> Result<Board, String> {
    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.hints = hints;
    match solver.solve(puzzle, &opts, &mut sink) {
        SolveOutcome::Solved(b) => Ok(b),
        SolveOutcome::TimedOut { best_partial, .. } => Ok(best_partial),
        SolveOutcome::Cancelled { best_partial, .. } => Ok(best_partial),
        SolveOutcome::Exhausted => Ok(Board::empty(puzzle)),
        SolveOutcome::AllSolutions(bs) => Ok(bs.into_iter().next().unwrap_or_else(|| Board::empty(puzzle))),
        SolveOutcome::Error(e) => Err(e),
    }
}

fn main() {
    let args = Args::parse();
    eprintln!("=== RTCP — Region-Tear with CP ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("cp_seconds: {}  repair_seconds: {}  max_iter: {}  total: {}s",
        args.cp_seconds, args.repair_seconds, args.max_iterations, args.total_seconds);
    eprintln!("min_component_size: {}  shrink_factor: {}", args.min_component_size, args.shrink_factor);

    let (puzzle, file_hints) = load_puzzle_with_hints(&args.puzzle).expect("load puzzle");
    eprintln!("loaded {}×{}, {} pieces, {} colors, {} file-hints",
        puzzle.width, puzzle.height, puzzle.pieces().len(), puzzle.color_count - 1, file_hints.hints.len());

    let global_start = Instant::now();

    // ------- Phase 0: initial CP -------
    eprintln!("\n--- Phase 0: initial CP ({}s) ---", args.cp_seconds);
    let initial_hints = if args.use_hints { file_hints.clone() } else { Hints::default() };
    let t = Instant::now();
    let mut best_board = run_cp_with_hints(&puzzle, initial_hints, args.cp_seconds * 1000);
    let (mut best_score, total, mut pairs) = score_and_match_set(&puzzle, &best_board);
    eprintln!("phase 0: {:.1}s, placed={}/{}, edges={}/{} ({}%)",
        t.elapsed().as_secs_f64(),
        placed_count(&best_board), puzzle.cell_count(),
        best_score, total, (best_score * 100) / total);

    // ------- Repair loop -------
    let mut iter = 0u32;
    let mut consecutive_failures = 0u32;
    while iter < args.max_iterations
        && global_start.elapsed().as_secs() < args.total_seconds
    {
        iter += 1;
        let (mut anchor, anchor_size) = select_anchor(&puzzle, &best_board, &pairs, args.min_component_size);
        if anchor_size == 0 {
            eprintln!("  [iter {}] no anchor found (no matched components ≥ {}). Done.",
                iter, args.min_component_size);
            break;
        }
        // Always keep file_hints in the anchor (they're known-correct).
        if args.use_hints {
            for h in &file_hints.hints {
                anchor[h.position as usize] = true;
            }
        }
        let free_cells = (puzzle.cell_count() - anchor.iter().filter(|&&a| a).count() as u32) as i32;

        // If consecutive_failures > 0, shrink the anchor before solving.
        for _ in 0..consecutive_failures {
            let _ = shrink_anchor(&puzzle, &best_board, &pairs, &mut anchor, args.shrink_factor);
        }
        let pinned = anchor.iter().filter(|&&a| a).count() as u32;
        let freed = puzzle.cell_count() - pinned;

        let hints = anchor_to_hints(&best_board, &anchor);
        eprintln!("\n--- iter {}: anchor={} pinned, {} free (consec_fail={}) ---",
            iter, pinned, freed, consecutive_failures);

        // Diagnostic: count anchor cells with no piece in best_board.
        let mut anchor_unplaced = 0u32;
        for (i, &is_a) in anchor.iter().enumerate() {
            if is_a && best_board.get(i as Position).is_none() { anchor_unplaced += 1; }
        }
        eprintln!("  diag: anchor={}, anchor_with_piece={}, anchor_empty_in_partial={}",
            anchor.iter().filter(|&&a| a).count(),
            anchor.iter().filter(|&&a| a).count() - anchor_unplaced as usize,
            anchor_unplaced);

        let t = Instant::now();
        let result = run_cp_with_hints_strict(&puzzle, hints, args.repair_seconds * 1000);
        match result {
            Err(e) => {
                eprintln!("  CP error: {e}");
                eprintln!("  → anchor inconsistent (matched-edge graph said clean but solver disagreed?).");
                consecutive_failures += 1;
                if consecutive_failures > 5 {
                    eprintln!("  → too many consecutive failures, stopping.");
                    break;
                }
                continue;
            }
            Ok(new_board) => {
                let (new_score, _, new_pairs) = score_and_match_set(&puzzle, &new_board);
                let new_placed = placed_count(&new_board);
                eprintln!("  CP repair done in {:.1}s: placed={}/{} edges={}/{} ({}%)",
                    t.elapsed().as_secs_f64(),
                    new_placed, puzzle.cell_count(),
                    new_score, total, (new_score * 100) / total);

                if new_score > best_score {
                    let delta = new_score - best_score;
                    eprintln!("  ✓ improvement: +{} edges (was {}, now {})", delta, best_score, new_score);
                    best_board = new_board;
                    best_score = new_score;
                    pairs = new_pairs;
                    consecutive_failures = 0;
                } else {
                    eprintln!("  ✗ no improvement ({} ≤ {}).", new_score, best_score);
                    consecutive_failures += 1;
                    if consecutive_failures > 5 {
                        eprintln!("  → stopping after 5 consecutive non-improvements.");
                        break;
                    }
                }
            }
        }
        let _ = free_cells;
    }

    eprintln!("\n=== RTCP DONE ===");
    eprintln!("total wall-clock: {:.1}s   iterations: {}",
        global_start.elapsed().as_secs_f64(), iter);
    eprintln!("final score: {}/{} ({}%)", best_score, total, (best_score * 100) / total);

    let output_dir = std::path::PathBuf::from("output");
    let puzzle_name = puzzle_name_from_path(&args.puzzle);
    let extra = serde_json::json!({
        "rtcp": {
            "iterations": iter,
            "wall_clock_s": global_start.elapsed().as_secs_f64(),
            "cp_seconds": args.cp_seconds,
            "repair_seconds": args.repair_seconds,
            "max_iterations": args.max_iterations,
            "total_seconds": args.total_seconds,
            "min_component_size": args.min_component_size,
            "shrink_factor": args.shrink_factor,
        },
    });
    match write_report(&output_dir, "rtcp", &puzzle, &puzzle_name, &best_board, extra) {
        Ok(r) => { eprintln!("\nReport: {}", r.json_path.display()); eprintln!("Bucas:  {}", r.url); }
        Err(e) => eprintln!("warning: failed to write report: {e}"),
    }
    let _ = pairs;
}
