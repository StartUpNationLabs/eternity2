// Central-region CP repair experiment.
//
// Topology diagnostic told us the plateau variance concentrates in
// rows 4-9, cols 6-10 (the central ~6x6). All 20 unpinned and all 6
// pinned plateau states share the same border colors 1-5 perfectly;
// 60-70% of the per-(color,row|col) histogram cells are invariant
// across plateau states. Border is solved; the action is in the centre.
//
// Earlier generic mini-CP repair failed (~99% wipeout) because pinning
// an arbitrary region's boundary created unsatisfiable sub-problems.
// But the CENTRAL region's boundary is precisely the perfectly-matched
// middle rings, which should admit feasible inner assignments.
//
// This binary takes a plateau dump, frees a (k×k) central window,
// pins everything else, and runs CP for a fixed time budget. Reports
// the new score and whether CP completed the region.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::board_io::read_dump;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::{bucas_url, puzzle_name_from_path, write_report};
use eternity2_core::{Board, Piece, PieceId, Puzzle, BORDER};
use eternity2_localsearch::repair::repair_region;

#[derive(Parser, Debug)]
#[command(name = "central_repair", about = "Central-region CP repair on a plateau dump")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// Path to a sample_XXX.json dump from harvest_plateau.
    #[arg(long)]
    dump: PathBuf,

    /// Top-left x of the region to free (default 5 = column 5).
    #[arg(long, default_value_t = 5)]
    x0: u32,

    /// Top-left y of the region to free (default 5 = row 5).
    #[arg(long, default_value_t = 5)]
    y0: u32,

    /// Side length k of the freed region (default 6 = 6×6).
    #[arg(long, default_value_t = 6)]
    k: u32,

    /// CP time budget in seconds.
    #[arg(long, default_value_t = 60)]
    budget_seconds: u64,
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
    eprintln!("=== central_repair ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("dump:   {}", args.dump.display());
    eprintln!("region: x0={} y0={} k={} (frees cells [{}..{}) × [{}..{}))",
        args.x0, args.y0, args.k,
        args.x0, args.x0 + args.k, args.y0, args.y0 + args.k);
    eprintln!("budget: {}s", args.budget_seconds);

    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    let dump = read_dump(&args.dump).expect("read dump");
    let board = dump.to_board(&puzzle);
    let (before, total) = score_board(&puzzle, &board);
    eprintln!("\nbefore: {}/{} ({:.2}%)",
        before, total, 100.0 * (before as f64) / (total as f64));

    let t0 = Instant::now();
    let result = repair_region(&puzzle, &board, args.x0, args.y0, args.k, args.budget_seconds * 1000);
    let elapsed = t0.elapsed().as_secs_f64();

    match result {
        Some(new_board) => {
            let (after, _) = score_board(&puzzle, &new_board);
            let delta = (after as i64) - (before as i64);
            eprintln!("\nafter:  {}/{} ({:.2}%)  delta={:+}  elapsed={:.1}s",
                after, total, 100.0 * (after as f64) / (total as f64), delta, elapsed);
            let url = bucas_url(&puzzle, &new_board, "central_repair");
            eprintln!("\nBucas: {}", url);

            // Write a full report for posterity.
            let puzzle_name = puzzle_name_from_path(&args.puzzle);
            let output_dir = PathBuf::from("output");
            let extra = serde_json::json!({
                "before_score": before,
                "after_score": after,
                "delta": delta,
                "region": { "x0": args.x0, "y0": args.y0, "k": args.k },
                "budget_seconds": args.budget_seconds,
                "elapsed_seconds": elapsed,
                "dump": args.dump.display().to_string(),
            });
            match write_report(&output_dir, "central_repair", &puzzle, &puzzle_name, &new_board, extra) {
                Ok(r) => eprintln!("Report: {}", r.json_path.display()),
                Err(e) => eprintln!("warning: failed to write report: {e}"),
            }
        }
        None => {
            eprintln!("\nCP could not complete the freed region in {:.1}s (wipeout or timeout).",
                elapsed);
            eprintln!("This is the 'unsatisfiable sub-problem' failure mode the earlier");
            eprintln!("repair experiments hit. Try a different (x0, y0, k) or longer budget.");
        }
    }
}
