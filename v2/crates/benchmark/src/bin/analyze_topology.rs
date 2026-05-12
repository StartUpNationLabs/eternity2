// Topological / color-flow diagnostic for the RSB-vs-obstruction question.
//
// For each plateau state we compute, for every interior color c:
//   - total count of horizontal interior edges with color c (between same row)
//   - total count of vertical   interior edges with color c (between same col)
//   - per-row count of vertical edges (signature of "vertical strands")
//   - per-col count of horizontal edges (signature of "horizontal strands")
// We then ask: are these signatures *constant* across plateau states?
//
// If yes for any non-trivial signature, we have a global invariant local
// moves preserve — which explains why every cluster / swap variant we
// tried plateaus at the same score. The cure is a move that deliberately
// changes the invariant (color-strand surgery).
//
// If no, no obvious global topological obstruction; RSB framing remains
// the leading hypothesis.
//
// Requires the puzzle to read piece edges; loads the same official-E2
// CSV as the other binaries by default.

use std::collections::BTreeSet;
use std::fs;
use std::path::PathBuf;

use clap::Parser;
use eternity2_benchmark::board_io::read_dump;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Piece, PieceId, Puzzle, BORDER};

#[derive(Parser, Debug)]
#[command(name = "analyze_topology", about = "Color-flow invariants on plateau states")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long, default_value = "default")]
    run_name: String,
}

fn lookup_piece(puzzle: &Puzzle, id: PieceId) -> Option<&Piece> {
    puzzle.piece(id)
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct ColorSignature {
    width: u32,
    height: u32,
    max_color: u8,
    // [color] -> total H edges with that color (interior, both sides matched).
    h_total: Vec<u32>,
    v_total: Vec<u32>,
    // [color][row 0..height-1] -> count of vertical edges between row y and y+1 with that color.
    v_per_row: Vec<Vec<u32>>,
    // [color][col 0..width-1] -> count of horizontal edges between col x and x+1 with that color.
    h_per_col: Vec<Vec<u32>>,
    // For board-mismatch tolerance: include mismatched edges too, classifying
    // their color by the average of the two faces — but for unambiguous
    // invariants we ONLY count *matched* edges. Mismatched contributions go
    // into a separate "mismatched" tally per color.
    h_mismatched_per_col: Vec<Vec<u32>>,
    v_mismatched_per_row: Vec<Vec<u32>>,
}

fn signature(puzzle: &Puzzle, board: &Board) -> ColorSignature {
    let w = puzzle.width;
    let h = puzzle.height;
    let max_c = (puzzle.color_count as u8).saturating_sub(1).max(22);
    let n_colors = (max_c as usize) + 1;
    let mut h_total = vec![0u32; n_colors];
    let mut v_total = vec![0u32; n_colors];
    let mut v_per_row = vec![vec![0u32; (h.saturating_sub(1)) as usize]; n_colors];
    let mut h_per_col = vec![vec![0u32; (w.saturating_sub(1)) as usize]; n_colors];
    let mut h_mismatched_per_col = vec![vec![0u32; (w.saturating_sub(1)) as usize]; n_colors];
    let mut v_mismatched_per_row = vec![vec![0u32; (h.saturating_sub(1)) as usize]; n_colors];

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
                        let c_a = e[1] as usize;
                        let c_b = re[3] as usize;
                        if c_a != BORDER as usize && c_a == c_b && c_a < n_colors {
                            h_total[c_a] += 1;
                            h_per_col[c_a][x as usize] += 1;
                        } else if c_a != BORDER as usize && c_a < n_colors {
                            h_mismatched_per_col[c_a][x as usize] += 1;
                        }
                    }
                }
            }
            if y + 1 < h {
                if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                    if let Some(bp) = lookup_piece(puzzle, bpid) {
                        let be = bp.edges.rotated(brot).as_array();
                        let c_a = e[2] as usize;
                        let c_b = be[0] as usize;
                        if c_a != BORDER as usize && c_a == c_b && c_a < n_colors {
                            v_total[c_a] += 1;
                            v_per_row[c_a][y as usize] += 1;
                        } else if c_a != BORDER as usize && c_a < n_colors {
                            v_mismatched_per_row[c_a][y as usize] += 1;
                        }
                    }
                }
            }
        }
    }

    ColorSignature {
        width: w, height: h, max_color: max_c,
        h_total, v_total, v_per_row, h_per_col,
        h_mismatched_per_col, v_mismatched_per_row,
    }
}

fn main() {
    let args = Args::parse();
    let dir = PathBuf::from("output").join("plateau").join(&args.run_name);
    eprintln!("=== analyze_topology ===");
    eprintln!("dir: {}", dir.display());
    eprintln!("puzzle: {}", args.puzzle.display());

    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).expect("load");

    let mut entries: Vec<PathBuf> = fs::read_dir(&dir)
        .unwrap_or_else(|e| panic!("read_dir {}: {}", dir.display(), e))
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().and_then(|s| s.to_str()) == Some("json"))
        .filter(|p| p.file_name().and_then(|s| s.to_str()).map(|s| s.starts_with("sample_")).unwrap_or(false))
        .collect();
    entries.sort();

    let mut sigs: Vec<ColorSignature> = Vec::new();
    let mut scores: Vec<u32> = Vec::new();
    for p in &entries {
        match read_dump(p) {
            Ok(d) => {
                let board = d.to_board(&puzzle);
                sigs.push(signature(&puzzle, &board));
                scores.push(d.score);
            }
            Err(e) => eprintln!("skip {}: {e}", p.display()),
        }
    }
    let n = sigs.len();
    if n < 2 {
        eprintln!("need at least 2 states, found {n}");
        return;
    }
    eprintln!("loaded {n} plateau states; scores min={} max={}",
        scores.iter().min().unwrap(), scores.iter().max().unwrap());

    let n_colors = (sigs[0].max_color as usize) + 1;

    // Per-color: is h_total[c] / v_total[c] constant across plateau states?
    eprintln!("\n--- per-color matched-edge totals (looking for invariants) ---");
    eprintln!("color | h_total values across {n} states          | v_total values across {n} states");
    eprintln!("------+--------------------------------------------+----------------------------------");
    let mut invariant_total_colors: Vec<usize> = Vec::new();
    for c in 1..n_colors {
        let hs: Vec<u32> = sigs.iter().map(|s| s.h_total.get(c).copied().unwrap_or(0)).collect();
        let vs: Vec<u32> = sigs.iter().map(|s| s.v_total.get(c).copied().unwrap_or(0)).collect();
        let h_set: BTreeSet<u32> = hs.iter().copied().collect();
        let v_set: BTreeSet<u32> = vs.iter().copied().collect();
        let h_inv = h_set.len() == 1;
        let v_inv = v_set.len() == 1;
        if h_inv && v_inv { invariant_total_colors.push(c); }
        let h_min = hs.iter().min().unwrap_or(&0);
        let h_max = hs.iter().max().unwrap_or(&0);
        let v_min = vs.iter().min().unwrap_or(&0);
        let v_max = vs.iter().max().unwrap_or(&0);
        let marker = if h_inv && v_inv { "★" } else { " " };
        eprintln!(" {:>3}  | h: min={:>3} max={:>3} #distinct={:<2}      {}  | v: min={:>3} max={:>3} #distinct={:<2}",
            c, h_min, h_max, h_set.len(), marker, v_min, v_max, v_set.len());
    }
    eprintln!("\ncolors with BOTH h_total and v_total invariant across all {} states: {:?}",
        n, invariant_total_colors);

    // Per-color per-row / per-col: how many of the (color, row) / (color, col)
    // cells of the histogram are invariant across plateau states?
    let n_rows = sigs[0].v_per_row.first().map(|v| v.len()).unwrap_or(0);
    let n_cols = sigs[0].h_per_col.first().map(|v| v.len()).unwrap_or(0);
    let mut v_cell_total = 0usize;
    let mut v_cell_invariant = 0usize;
    let mut h_cell_total = 0usize;
    let mut h_cell_invariant = 0usize;
    for c in 1..n_colors {
        for y in 0..n_rows {
            let vs: BTreeSet<u32> = sigs.iter().map(|s| s.v_per_row[c][y]).collect();
            v_cell_total += 1;
            if vs.len() == 1 { v_cell_invariant += 1; }
        }
        for x in 0..n_cols {
            let hs: BTreeSet<u32> = sigs.iter().map(|s| s.h_per_col[c][x]).collect();
            h_cell_total += 1;
            if hs.len() == 1 { h_cell_invariant += 1; }
        }
    }
    eprintln!("\n--- per-color per-row / per-col matched-edge counts ---");
    eprintln!("v_per_row cells: {}/{} invariant ({:.1}%)",
        v_cell_invariant, v_cell_total, 100.0 * (v_cell_invariant as f64) / (v_cell_total as f64));
    eprintln!("h_per_col cells: {}/{} invariant ({:.1}%)",
        h_cell_invariant, h_cell_total, 100.0 * (h_cell_invariant as f64) / (h_cell_total as f64));

    // Where do plateau states differ MOST? Locate the (color, row|col) cells
    // with the highest variance. These are the candidate sites for color-
    // surgery moves.
    let mut row_var: Vec<(usize, usize, u32, u32)> = Vec::new();
    for c in 1..n_colors {
        for y in 0..n_rows {
            let vs: Vec<u32> = sigs.iter().map(|s| s.v_per_row[c][y]).collect();
            let lo = *vs.iter().min().unwrap_or(&0);
            let hi = *vs.iter().max().unwrap_or(&0);
            if hi > lo { row_var.push((c, y, lo, hi)); }
        }
    }
    row_var.sort_by_key(|(_, _, lo, hi)| std::cmp::Reverse(hi - lo));
    eprintln!("\ntop 10 (color, row) cells with largest range across plateau states (v_per_row):");
    for (c, y, lo, hi) in row_var.iter().take(10) {
        eprintln!("  color {} row {} range [{}..{}]", c, y, lo, hi);
    }
    let mut col_var: Vec<(usize, usize, u32, u32)> = Vec::new();
    for c in 1..n_colors {
        for x in 0..n_cols {
            let hs: Vec<u32> = sigs.iter().map(|s| s.h_per_col[c][x]).collect();
            let lo = *hs.iter().min().unwrap_or(&0);
            let hi = *hs.iter().max().unwrap_or(&0);
            if hi > lo { col_var.push((c, x, lo, hi)); }
        }
    }
    col_var.sort_by_key(|(_, _, lo, hi)| std::cmp::Reverse(hi - lo));
    eprintln!("\ntop 10 (color, col) cells with largest range across plateau states (h_per_col):");
    for (c, x, lo, hi) in col_var.iter().take(10) {
        eprintln!("  color {} col {} range [{}..{}]", c, x, lo, hi);
    }

    eprintln!("\nInterpretation:");
    eprintln!("  - 100% invariance ⇒ all plateau states share an exact color-strand");
    eprintln!("    signature; local moves CANNOT change it.  Cure: design moves");
    eprintln!("    that deliberately re-route a single color strand.");
    eprintln!("  - High but partial invariance (>90%) ⇒ moves change small regions");
    eprintln!("    but big-picture flows are conserved; the 'large-scale' surgery");
    eprintln!("    is still the right next move.");
    eprintln!("  - <50% invariance ⇒ no clear global obstruction at this granularity.");

    // Dump full signatures as JSON for offline analysis.
    let out = dir.join("_topology.json");
    let sigs_json: Vec<_> = sigs.iter().zip(scores.iter()).map(|(s, sc)| serde_json::json!({
        "score": sc,
        "h_total": s.h_total,
        "v_total": s.v_total,
        "v_per_row": s.v_per_row,
        "h_per_col": s.h_per_col,
        "h_mismatched_per_col": s.h_mismatched_per_col,
        "v_mismatched_per_row": s.v_mismatched_per_row,
    })).collect();
    let payload = serde_json::json!({
        "n_states": n,
        "max_color": sigs[0].max_color,
        "width": sigs[0].width,
        "height": sigs[0].height,
        "v_cell_invariant_pct": 100.0 * (v_cell_invariant as f64) / (v_cell_total as f64),
        "h_cell_invariant_pct": 100.0 * (h_cell_invariant as f64) / (h_cell_total as f64),
        "invariant_total_colors": invariant_total_colors,
        "signatures": sigs_json,
    });
    if let Err(e) = fs::write(&out, serde_json::to_string_pretty(&payload).unwrap() + "\n") {
        eprintln!("warning: failed to write topology summary: {e}");
    } else {
        eprintln!("\nsummary: {}", out.display());
    }
}
