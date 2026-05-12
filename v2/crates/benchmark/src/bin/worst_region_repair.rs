// Find the worst k×k region (lowest internal-edge-match score) on a dump
// and try to repair it via CP. This is the previous "directed bad-cell"
// hypothesis applied via CP instead of SA.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::board_io::read_dump;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::{bucas_url, puzzle_name_from_path, write_report};
use eternity2_core::{Board, Piece, PieceId, Puzzle, BORDER};
use eternity2_localsearch::repair::{repair_region, worst_region};

#[derive(Parser, Debug)]
#[command(name = "worst_region_repair", about = "CP repair of the worst k×k region on a plateau dump")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long)]
    dump: PathBuf,

    /// Side length k of the region to consider (default 6).
    #[arg(long, default_value_t = 6)]
    k: u32,

    /// CP time budget in seconds.
    #[arg(long, default_value_t = 60)]
    budget_seconds: u64,

    /// Instead of the single worst region, sweep over the top-N
    /// worst non-overlapping regions and repair each. 0 = just one.
    #[arg(long, default_value_t = 0)]
    top_n: u32,
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
    eprintln!("=== worst_region_repair ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("dump:   {}", args.dump.display());

    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    let dump = read_dump(&args.dump).expect("read dump");
    let mut board = dump.to_board(&puzzle);
    let (before, total) = score_board(&puzzle, &board);
    eprintln!("before: {}/{} ({:.2}%)", before, total, 100.0 * (before as f64) / (total as f64));

    // For top-N variant, repeatedly find worst region, try to repair, accept improvement.
    let n_iters = if args.top_n == 0 { 1 } else { args.top_n };
    for iter in 0..n_iters {
        let (x0, y0) = match worst_region(&puzzle, &board, args.k) {
            Some(p) => p,
            None => { eprintln!("no worst region found, stopping"); break; }
        };
        let (before_iter, _) = score_board(&puzzle, &board);
        eprintln!("\n--- iter {}/{}: worst region at ({}, {}), k={} ---",
            iter + 1, n_iters, x0, y0, args.k);

        let t = Instant::now();
        let result = repair_region(&puzzle, &board, x0, y0, args.k, args.budget_seconds * 1000);
        let elapsed = t.elapsed().as_secs_f64();
        match result {
            Some(new_board) => {
                let (after, _) = score_board(&puzzle, &new_board);
                let delta = (after as i64) - (before_iter as i64);
                eprintln!("  CP repaired in {:.1}s: {} -> {} (delta={:+})",
                    elapsed, before_iter, after, delta);
                if delta > 0 {
                    board = new_board;
                } else {
                    eprintln!("  no improvement; keeping original");
                }
            }
            None => {
                eprintln!("  CP wipeout/timeout in {:.1}s", elapsed);
            }
        }
    }

    let (after_final, _) = score_board(&puzzle, &board);
    eprintln!("\n=== DONE ===");
    eprintln!("final: {}/{} ({:.2}%)  delta={:+}",
        after_final, total, 100.0 * (after_final as f64) / (total as f64),
        (after_final as i64) - (before as i64));

    let url = bucas_url(&puzzle, &board, "worst_region_repair");
    eprintln!("\nBucas: {}", url);

    let puzzle_name = puzzle_name_from_path(&args.puzzle);
    let output_dir = PathBuf::from("output");
    let extra = serde_json::json!({
        "before_score": before,
        "after_score": after_final,
        "k": args.k,
        "top_n": args.top_n,
        "budget_seconds": args.budget_seconds,
        "dump": args.dump.display().to_string(),
    });
    let _ = write_report(&output_dir, "worst_region_repair", &puzzle, &puzzle_name, &board, extra);
}
