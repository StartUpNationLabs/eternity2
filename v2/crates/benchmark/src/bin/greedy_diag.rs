// Diagnostic: run CP on the official Eternity II, then test what
// `greedy_fill_initial` produces. We want to know:
//   1. CP partial score
//   2. Greedy-filled score per seed
//   3. Whether the greedy fill is reproducibly high

use std::path::PathBuf;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Piece, PieceId, Puzzle, BORDER};
use eternity2_events::BufferSink;
use eternity2_localsearch::{RngHandle, StateRef};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

#[derive(Parser, Debug)]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,
    #[arg(long, default_value_t = 30)]
    cp_seconds: u64,
    #[arg(long, default_value_t = 10)]
    n_seeds: u32,
}

fn lookup_piece(p: &Puzzle, id: PieceId) -> Option<&Piece> {
    p.pieces().iter().find(|q| q.id == id)
}
fn score_board(p: &Puzzle, b: &Board) -> (u32, u32) {
    let w = p.width; let h = p.height;
    let mut m = 0u32;
    let total = (w-1)*h + w*(h-1);
    for y in 0..h { for x in 0..w {
        let pos = y*w+x;
        let Some((pid, rot)) = b.get(pos) else { continue; };
        let Some(piece) = lookup_piece(p, pid) else { continue; };
        let e = piece.edges.rotated(rot).as_array();
        if x+1<w { if let Some((rpid, rrot)) = b.get(y*w+(x+1)) { if let Some(rp) = lookup_piece(p, rpid) {
            let re = rp.edges.rotated(rrot).as_array();
            if e[1]==re[3] && e[1]!=BORDER && e[1]!=0 { m += 1; }
        }}}
        if y+1<h { if let Some((bpid, brot)) = b.get((y+1)*w+x) { if let Some(bp) = lookup_piece(p, bpid) {
            let be = bp.edges.rotated(brot).as_array();
            if e[2]==be[0] && e[2]!=BORDER && e[2]!=0 { m += 1; }
        }}}
    }}
    (m, total)
}

fn main() {
    let args = Args::parse();
    let (puzzle, hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    eprintln!("loaded {}×{}, {} pieces", puzzle.width, puzzle.height, puzzle.pieces().len());

    // CP phase.
    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = args.cp_seconds * 1000;
    opts.hints = hints;
    let out = solver.solve(&puzzle, &opts, &mut sink);
    let cp_board: Board = match out {
        SolveOutcome::Solved(b) | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        SolveOutcome::Exhausted => Board::empty(&puzzle),
        SolveOutcome::Error(_) => Board::empty(&puzzle),
    };
    let (cp_score, total) = score_board(&puzzle, &cp_board);
    let placed = cp_board.cells().iter().filter(|c| c.is_some()).count();
    eprintln!("CP: placed={}/{}, score={}/{} ({:.1}%)",
        placed, puzzle.cell_count(), cp_score, total,
        100.0 * cp_score as f64 / total as f64);

    // Greedy fill with N seeds.
    let state = StateRef::new(&puzzle);
    eprintln!("\n=== greedy_fill scores across {} seeds ===", args.n_seeds);
    let mut all = Vec::new();
    for s in 0..args.n_seeds {
        let mut rng = RngHandle::new(0xE2_E2_E2u64.wrapping_mul(1 + s as u64));
        let filled = state.greedy_fill_initial(&cp_board, &mut rng);
        let (sc, _) = score_board(&puzzle, &filled);
        let true_sc = state.score(&filled);
        all.push(sc);
        eprintln!("  seed={}: greedy_fill score={} (true={}, agrees={}) total={}/{} ({:.1}%)",
            s, sc, true_sc, sc == true_sc, sc, total, 100.0 * sc as f64 / total as f64);
    }
    let max = *all.iter().max().unwrap();
    let min = *all.iter().min().unwrap();
    let mean = (all.iter().sum::<u32>() as f64) / (all.len() as f64);
    eprintln!("\nmin={}  mean={:.1}  max={}  range={}",
        min, mean, max, max - min);
}
