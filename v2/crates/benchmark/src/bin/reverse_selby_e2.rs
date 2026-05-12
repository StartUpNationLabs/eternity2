// Reverse-Selby strain-core CP attack.
//
// Idea: vol-6's PT saturates at 454/480 with 45 frozen-mismatched cells
// in a tight zone around the (7,8) hint. PT alone can't break this
// because its mobility zone is only 17 cells.
//
// Reverse-Selby: empty out a specified set of cells (the 45 frozen-
// mismatched cells, or any user-specified set), then run CP backtracking
// to fill them. The engine's existing rare-color + GAColor + AC3 +
// border-first-MRV variable ordering naturally prefers placing
// constrained cells first. Combined with edge-color propagation,
// backtracking can find configurations PT cannot.
//
// Selby's E1 method ordered pieces *worst-tilability first* (place bad
// pieces where they fit, save good pieces for endgame). On E2 the
// generator (Selby & Riordan themselves) flattened tilability so this
// no longer helps as a global ordering. The reverse on E2 is to attack
// the *spatial* hardness: pin everything outside the strain core, let
// CP find any configuration of the strain-core pieces that beats PT.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation, BORDER};
use eternity2_localsearch::repair_cells;

#[derive(Parser, Debug)]
#[command(name = "reverse_selby_e2", about = "Reverse-Selby strain-core CP attack on E2")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    /// Path to a JSON board (with `placement` array) to start from.
    /// All cells will be pinned EXCEPT those in `free_cells`.
    #[arg(long)]
    start_from: PathBuf,

    /// JSON array of 1D cell indices to free (e.g. "[68,76,84,...]").
    /// All other cells stay pinned. If omitted, we auto-compute the
    /// 45 frozen-mismatched cells from the 454 board.
    #[arg(long)]
    free_cells: Option<String>,

    /// Auto-detect cells: those with mismatched incident edges on the
    /// loaded board. Useful for arbitrary boards (not just the 454).
    /// Mutually exclusive with --free-cells.
    #[arg(long, default_value_t = false)]
    auto_mismatched: bool,

    /// CP budget in seconds.
    #[arg(long, default_value_t = 60)]
    cp_seconds: u64,

    /// Output JSON path. If omitted, prints stats only.
    #[arg(long)]
    out: Option<PathBuf>,
}

fn read_board_from_json(puzzle: &Puzzle, path: &std::path::Path) -> Result<Board, String> {
    let s = std::fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    let j: serde_json::Value =
        serde_json::from_str(&s).map_err(|e| format!("parse JSON {}: {e}", path.display()))?;
    let placement = j
        .get("placement")
        .and_then(|p| p.as_array())
        .ok_or_else(|| format!("no `placement` array in {}", path.display()))?;
    if placement.len() != puzzle.cell_count() as usize {
        return Err(format!(
            "placement len {} != puzzle cell_count {}",
            placement.len(),
            puzzle.cell_count()
        ));
    }
    let mut board = Board::empty(puzzle);
    for (pos, cell) in placement.iter().enumerate() {
        if cell.is_null() {
            continue;
        }
        let pid = cell
            .get("piece_id")
            .and_then(|v| v.as_u64())
            .ok_or_else(|| format!("cell {pos} missing piece_id"))? as PieceId;
        let rot_u8 = cell
            .get("rotation")
            .and_then(|v| v.as_u64())
            .ok_or_else(|| format!("cell {pos} missing rotation"))? as u8;
        let rot = Rotation::from_u8(rot_u8)
            .ok_or_else(|| format!("cell {pos} bad rotation {rot_u8}"))?;
        board.place(pos as u32, pid, rot);
    }
    Ok(board)
}

fn score_board(puzzle: &Puzzle, board: &Board) -> (u32, u32) {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut matches = 0u32;
    let total = (w - 1) * h + w * (h - 1);
    let lookup =
        |id: PieceId| puzzle.pieces().iter().find(|p| p.id == id);
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let Some(piece) = lookup(pid) else { continue; };
            let e = piece.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup(rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        if e[1] == re[3] && e[1] != BORDER && e[1] != 0 {
                            matches += 1;
                        }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup(bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        if e[2] == be[0] && e[2] != BORDER && e[2] != 0 {
                            matches += 1;
                        }
                    }
                }
            }
        }
    }
    (matches, total)
}

fn mismatched_cells(puzzle: &Puzzle, board: &Board) -> Vec<Position> {
    use std::collections::HashSet;
    let w = puzzle.width;
    let h = puzzle.height;
    let mut mm: HashSet<Position> = HashSet::new();
    let lookup =
        |id: PieceId| puzzle.pieces().iter().find(|p| p.id == id);
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let Some(piece) = lookup(pid) else { continue; };
            let e = piece.edges.rotated(rot).as_array();
            if x + 1 < w {
                if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                    if let Some(rp) = lookup(rpid) {
                        let re = rp.edges.rotated(rrot).as_array();
                        let m = e[1] == re[3] && e[1] != BORDER && e[1] != 0;
                        if !m {
                            mm.insert(pos);
                            mm.insert(y * w + (x + 1));
                        }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup(bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        let m = e[2] == be[0] && e[2] != BORDER && e[2] != 0;
                        if !m {
                            mm.insert(pos);
                            mm.insert((y + 1) * w + x);
                        }
                    }
                }
            }
        }
    }
    let mut v: Vec<Position> = mm.into_iter().collect();
    v.sort_unstable();
    v
}

fn main() {
    let args = Args::parse();
    eprintln!("=== reverse_selby_e2 ===");
    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).expect("load puzzle");
    eprintln!(
        "puzzle: {}×{}, {} pieces, {} colors",
        puzzle.width, puzzle.height, puzzle.pieces().len(), puzzle.color_count - 1
    );

    let board = read_board_from_json(&puzzle, &args.start_from).expect("load start_from board");
    let (score_in, total) = score_board(&puzzle, &board);
    eprintln!("starting board: {}/{} edges matched", score_in, total);

    let free_cells: Vec<Position> = if let Some(s) = args.free_cells.as_ref() {
        let v: Vec<u32> = serde_json::from_str(s).expect("parse --free-cells JSON");
        v
    } else if args.auto_mismatched {
        mismatched_cells(&puzzle, &board)
    } else {
        eprintln!("ERROR: must specify --free-cells or --auto-mismatched");
        std::process::exit(2);
    };

    eprintln!("free cells: {}", free_cells.len());
    eprintln!("free cell list: {:?}", free_cells);
    eprintln!("CP budget: {}s", args.cp_seconds);

    let t0 = Instant::now();
    let result = repair_cells(&puzzle, &board, &free_cells, args.cp_seconds * 1000);
    let elapsed = t0.elapsed();
    eprintln!("CP elapsed: {:.2}s", elapsed.as_secs_f64());

    match result {
        None => {
            eprintln!("CP could NOT fully fill the free cells in budget.");
        }
        Some(new_board) => {
            let (score_out, _) = score_board(&puzzle, &new_board);
            eprintln!(
                "CP filled all {} free cells. Final score: {}/{} edges (delta: {:+})",
                free_cells.len(),
                score_out,
                total,
                (score_out as i64) - (score_in as i64)
            );
            if let Some(out) = args.out.as_ref() {
                // Save as the same JSON format as pt_e2 output.
                let mut placement: Vec<serde_json::Value> = Vec::with_capacity(256);
                for pos in 0..puzzle.cell_count() {
                    if let Some((pid, rot)) = new_board.get(pos) {
                        placement.push(serde_json::json!({
                            "piece_id": pid,
                            "rotation": rot.as_u8(),
                        }));
                    } else {
                        placement.push(serde_json::Value::Null);
                    }
                }
                let j = serde_json::json!({
                    "puzzle": {"width": puzzle.width, "height": puzzle.height,
                              "color_count": puzzle.color_count, "piece_count": 256,
                              "name": "size_16_official_eternity"},
                    "placement": placement,
                    "score": {"matched_edges": score_out, "total_edges": total},
                    "run_name": "reverse_selby_e2",
                });
                std::fs::write(out, serde_json::to_string(&j).unwrap()).expect("write out");
                eprintln!("wrote {}", out.display());
            }
        }
    }
}
