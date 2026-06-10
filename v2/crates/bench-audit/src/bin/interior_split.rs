// interior_split — vol-211 Phase 0a: matched-edge split by adjacency class.
//
// For each board: matched counts split as II (interior-interior, /364),
// IB (border-interior, /56), BB (border-border, /60) on canonical 16x16.
// Establishes the implicit standalone-interior record (max II) across
// record boards, community corpus, and the 400-480 DB.
//
// Usage: interior_split <board.json | dir> [...]   (dirs walked recursively)
// Output: TSV to stdout: path placed uniq matched II IB BB hints status

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::is_perimeter_pos;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle};
use eternity2_export::{load_board, verify};

struct Split {
    ii: u32,
    ib: u32,
    bb: u32,
}

fn matched_split(puzzle: &Puzzle, board: &Board) -> Split {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut s = Split { ii: 0, ib: 0, bb: 0 };
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let Some((pid, rot)) = board.get(pos) else { continue };
            let Some(p) = puzzle.piece(pid) else { continue };
            let e = p.edges.rotated(rot).as_array();
            let pos_per = is_perimeter_pos(puzzle, pos);
            if x + 1 < w {
                let n = y * w + (x + 1);
                if let Some((npid, nrot)) = board.get(n) {
                    if let Some(np) = puzzle.piece(npid) {
                        let ne = np.edges.rotated(nrot).as_array();
                        // grey-grey (color 0) never counts: border color is
                        // not a legal interior match (matters on illegal boards)
                        if e[1] == ne[3] && e[1] != eternity2_core::Color::from(0u8) {
                            match (pos_per, is_perimeter_pos(puzzle, n)) {
                                (true, true) => s.bb += 1,
                                (false, false) => s.ii += 1,
                                _ => s.ib += 1,
                            }
                        }
                    }
                }
            }
            if y + 1 < h {
                let n = (y + 1) * w + x;
                if let Some((npid, nrot)) = board.get(n) {
                    if let Some(np) = puzzle.piece(npid) {
                        let ne = np.edges.rotated(nrot).as_array();
                        if e[2] == ne[0] && e[2] != eternity2_core::Color::from(0u8) {
                            match (pos_per, is_perimeter_pos(puzzle, n)) {
                                (true, true) => s.bb += 1,
                                (false, false) => s.ii += 1,
                                _ => s.ib += 1,
                            }
                        }
                    }
                }
            }
        }
    }
    s
}

fn collect_json(path: &Path, out: &mut Vec<PathBuf>) {
    if path.is_dir() {
        let Ok(rd) = std::fs::read_dir(path) else { return };
        let mut entries: Vec<_> = rd.flatten().map(|e| e.path()).collect();
        entries.sort();
        for e in entries {
            collect_json(&e, out);
        }
    } else if path.extension().is_some_and(|x| x == "json") {
        out.push(path.to_path_buf());
    }
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: interior_split <board.json | dir> [...]");
        std::process::exit(2);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, canonical_hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let mut files = Vec::new();
    for a in &args {
        collect_json(&PathBuf::from(a), &mut files);
    }

    println!("path\tplaced\tuniq\tmatched\tII\tIB\tBB\thints\tstatus");
    for f in &files {
        match load_board(f, &puzzle) {
            Ok(board) => {
                let r = verify(&puzzle, &canonical_hints, &board);
                let s = matched_split(&puzzle, &board);
                let status = if !r.duplicate_pieces.is_empty() {
                    "DUP"
                } else if !r.border_violations.is_empty() {
                    "BORDER_VIOL"
                } else {
                    "OK"
                };
                println!(
                    "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}/{}\t{}",
                    f.display(),
                    r.placed_count,
                    r.unique_pieces,
                    r.matched,
                    s.ii,
                    s.ib,
                    s.bb,
                    r.hint_compliance.matched,
                    r.hint_compliance.total,
                    status,
                );
            }
            Err(e) => eprintln!("{}\tLOAD_ERROR: {e}", f.display()),
        }
    }
}
