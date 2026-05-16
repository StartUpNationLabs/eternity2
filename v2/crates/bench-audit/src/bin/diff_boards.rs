// Vol-60 — diff_boards: direct piece-id comparison between two boards.
//
// Per CLAUDE.md rules #2 and #11: when asking "are two boards the same?",
// the FIRST action is to compare placement piece-ids cell-by-cell. Color
// labelings (Bucas's Joshua coloring vs our pt coloring) can σ-permute,
// but piece-ids 0..255 are unambiguous.
//
// Usage: diff_boards <a.json> <b.json>
//
// Output: per-cell diff summary, then category-level overlap stats.

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_export::load_board;
use eternity2_solver_trait as _;

fn cell_class(x: u32, y: u32, w: u32, h: u32) -> &'static str {
    let is_corner = (x == 0 || x + 1 == w) && (y == 0 || y + 1 == h);
    let is_border = x == 0 || x + 1 == w || y == 0 || y + 1 == h;
    if is_corner { "corner" } else if is_border { "border" } else { "interior" }
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 2 {
        eprintln!("usage: diff_boards <a.json> <b.json>");
        std::process::exit(2);
    }
    let a = load_board(&PathBuf::from(&args[0]), &puzzle).expect("load A");
    let b = load_board(&PathBuf::from(&args[1]), &puzzle).expect("load B");
    let w = puzzle.width;
    let h = puzzle.height;
    let n_cells = puzzle.cell_count();

    let mut same_pid_rot = 0u32;     // exact match
    let mut same_pid_diff_rot = 0u32; // same piece, different rotation
    let mut diff_pid = 0u32;          // different piece
    let mut one_empty = 0u32;         // exactly one has a placement
    let mut both_empty = 0u32;        // neither has a placement

    let mut by_class: std::collections::HashMap<&'static str, (u32, u32, u32)> =
        std::collections::HashMap::new(); // class -> (match, diff, total)

    let mut corner_diff = false;
    for pos in 0..n_cells {
        let x = pos % w; let y = pos / w;
        let class = cell_class(x, y, w, h);
        let entry = by_class.entry(class).or_insert((0, 0, 0));
        entry.2 += 1;
        match (a.get(pos), b.get(pos)) {
            (Some((p1, r1)), Some((p2, r2))) => {
                if p1 == p2 && r1 == r2 {
                    same_pid_rot += 1;
                    entry.0 += 1;
                } else if p1 == p2 {
                    same_pid_diff_rot += 1;
                    entry.1 += 1;
                } else {
                    diff_pid += 1;
                    entry.1 += 1;
                    if class == "corner" { corner_diff = true; }
                }
            }
            (None, None) => { both_empty += 1; }
            _ => { one_empty += 1; entry.1 += 1; }
        }
    }

    println!("Diff between:");
    println!("  A: {}", args[0]);
    println!("  B: {}", args[1]);
    println!("");
    println!("Cell-by-cell summary ({} cells):", n_cells);
    println!("  same (pid, rot):           {:>4}  ({:.1}%)", same_pid_rot, 100.0 * same_pid_rot as f64 / n_cells as f64);
    println!("  same piece, diff rotation: {:>4}", same_pid_diff_rot);
    println!("  different piece:           {:>4}", diff_pid);
    println!("  exactly one empty:         {:>4}", one_empty);
    println!("  both empty:                {:>4}", both_empty);
    println!("");
    println!("By cell class:");
    let mut classes: Vec<&&str> = by_class.keys().collect();
    classes.sort();
    for c in classes {
        let (m, d, t) = by_class[*c];
        println!("  {:<10}: match={} diff={} total={}", c, m, d, t);
    }
    println!("");

    // Verdict
    if same_pid_rot == n_cells {
        println!("VERDICT: Boards are IDENTICAL (all cells match piece+rotation).");
    } else if same_pid_rot + both_empty == n_cells {
        println!("VERDICT: Boards have IDENTICAL placements (where placed).");
    } else if diff_pid == 0 && same_pid_diff_rot > 0 {
        println!("VERDICT: Same pieces, some rotated differently. Likely related basin.");
    } else if corner_diff {
        println!("VERDICT: DISTINCT BOARDS — corners differ. Different basin families.");
    } else if diff_pid > 0 {
        println!("VERDICT: DISTINCT BOARDS — pieces differ at non-corner cells.");
    } else {
        println!("VERDICT: Partial overlap.");
    }
}
