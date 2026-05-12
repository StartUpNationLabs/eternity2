// Compare our CP's piece commitments against Joshua Blackwood's 470/480
// solution. Strategy: run CP with ONLY the central hint pinned (matching
// Blackwood's setup), let it commit as many cells as possible in
// time_budget, then for every committed cell check whether our (piece, rot)
// matches Blackwood's at that cell.
//
// First-divergence cell is a candidate "where our CP makes a wrong choice
// that no downstream local search can fix."

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::board_io::read_dump;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Hints, Piece, PieceId, Puzzle, BORDER};
use eternity2_events::BufferSink;
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

#[derive(Parser, Debug)]
#[command(name = "prefix_compare", about = "Compare CP's placements to Blackwood's 470 solution")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// JSON file with Blackwood's decoded placement (cells = [pid, rot] or null).
    #[arg(long, default_value = "output/blackwood_decoded.json")]
    blackwood: PathBuf,

    /// Time budget (seconds) for CP.
    #[arg(long, default_value_t = 30)]
    budget_seconds: u64,

    /// Which hints to pin: "central" (only piece 138 at 7,8), "five" (all
    /// official), or "none". Default: central, matching Blackwood's setup.
    #[arg(long, default_value = "central")]
    hint_mode: String,
}

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.piece(id)
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
            let Some(piece) = lookup_piece(puzzle, pid) else { continue };
            let e = piece.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup_piece(puzzle, rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        if e[1] == re[3] && e[1] != BORDER { matches += 1; }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        if e[2] == be[0] && e[2] != BORDER { matches += 1; }
                    }
                }
            }
        }
    }
    (matches, total)
}

fn main() {
    let args = Args::parse();
    eprintln!("=== prefix_compare ===");
    eprintln!("puzzle:    {}", args.puzzle.display());
    eprintln!("blackwood: {}", args.blackwood.display());
    eprintln!("budget:    {}s", args.budget_seconds);
    eprintln!("hint_mode: {}", args.hint_mode);

    let (puzzle, file_hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    let blackwood = read_dump(&args.blackwood).expect("read blackwood");

    // Select hints
    let hints = match args.hint_mode.as_str() {
        "central" => {
            // central hint only — piece at (7,8) in our CSV is piece 138 rot 0
            let central = file_hints.hints.iter()
                .find(|h| h.position == 8 * 16 + 7)
                .cloned()
                .expect("central hint not found in CSV");
            Hints::new(vec![central])
        }
        "five" => file_hints,
        "none" => Hints::default(),
        _ => panic!("hint_mode must be central|five|none"),
    };
    eprintln!("hints used: {}", hints.hints.len());

    // Run CP
    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = args.budget_seconds * 1000;
    opts.hints = hints;
    let t0 = Instant::now();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed = t0.elapsed().as_secs_f64();
    let cp_board = match outcome {
        SolveOutcome::Solved(b) | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        SolveOutcome::Exhausted | SolveOutcome::Error(_) => Board::empty(&puzzle),
    };
    let placed = cp_board.cells().iter().filter(|c| c.is_some()).count();
    let (sc, _) = score_board(&puzzle, &cp_board);
    eprintln!("CP done in {:.1}s: placed={}/256, score={}/480",
        elapsed, placed, sc);

    // Compare cell by cell
    let mut matches_full = 0u32;
    let mut matches_pid_only = 0u32;
    let mut diverge_first: Option<u32> = None;
    let mut diverge_positions: Vec<u32> = Vec::new();
    eprintln!("\nCell-by-cell comparison (committed cells only):");
    eprintln!("pos (x, y)   cp_pid cp_rot   black_pid black_rot   status");
    for pos in 0..256u32 {
        let cp = cp_board.get(pos);
        let bl = blackwood.cells.get(pos as usize).copied().flatten();
        let (Some((cp_pid, cp_rot)), Some([b_pid, b_rot])) = (cp, bl) else { continue };
        let same_pid = u32::from(cp_pid) == b_pid;
        let same_rot = u32::from(cp_rot.as_u8()) == b_rot;
        if same_pid && same_rot {
            matches_full += 1;
        } else if same_pid {
            matches_pid_only += 1;
        } else {
            diverge_positions.push(pos);
            if diverge_first.is_none() {
                diverge_first = Some(pos);
            }
        }
    }
    let total_committed = matches_full + matches_pid_only + (diverge_positions.len() as u32);
    eprintln!("\nSummary across {} committed cells:", total_committed);
    eprintln!("  full match (pid + rot): {}", matches_full);
    eprintln!("  pid match, rot differs: {}", matches_pid_only);
    eprintln!("  diverge (different pid): {}", diverge_positions.len());
    if let Some(first) = diverge_first {
        let (x, y) = puzzle.xy(first);
        let (cp_pid, cp_rot) = cp_board.get(first).unwrap();
        let [b_pid, b_rot] = blackwood.cells[first as usize].unwrap();
        eprintln!("\nFirst divergence at cell {} (x={}, y={}):", first, x, y);
        eprintln!("  CP picked:        piece={} rot={}", u32::from(cp_pid), cp_rot.as_u8());
        eprintln!("  Blackwood placed: piece={} rot={}", b_pid, b_rot);
    } else {
        eprintln!("\nNO divergence: CP committed only cells that match Blackwood.");
    }

    if diverge_positions.len() <= 30 {
        eprintln!("\nAll diverging cells:");
        for pos in &diverge_positions {
            let (x, y) = puzzle.xy(*pos);
            let (cp_pid, cp_rot) = cp_board.get(*pos).unwrap();
            let [b_pid, b_rot] = blackwood.cells[*pos as usize].unwrap();
            eprintln!("  ({:>2}, {:>2}): CP=({:>3}, {}) Blackwood=({:>3}, {})",
                x, y, u32::from(cp_pid), cp_rot.as_u8(), b_pid, b_rot);
        }
    } else {
        eprintln!("\n({} diverging cells, showing first 30)", diverge_positions.len());
        for pos in diverge_positions.iter().take(30) {
            let (x, y) = puzzle.xy(*pos);
            let (cp_pid, cp_rot) = cp_board.get(*pos).unwrap();
            let [b_pid, b_rot] = blackwood.cells[*pos as usize].unwrap();
            eprintln!("  ({:>2}, {:>2}): CP=({:>3}, {}) Blackwood=({:>3}, {})",
                x, y, u32::from(cp_pid), cp_rot.as_u8(), b_pid, b_rot);
        }
    }
}
