// Vol-54 T1 — per-color INTEGER match count on a saved board.
//
// Classifies each of the 480 internal grid-edges by the cell-class pair
// (II / BI / BB) where:
//   - I: interior cell (not on outer ring)
//   - B: border cell (on outer ring; includes corners)
// Reports per-color matched count within each class, pairable with
// output/vol-44_border_lp_ub/per_color_458.log which gives per-color LP UBs.
//
// Usage: per_color_integer <board.json>

use std::path::{Path, PathBuf};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Rotation};
use eternity2_solver_trait as _;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}

fn is_border(x: u32, y: u32, w: u32, h: u32) -> bool {
    x == 0 || x + 1 == w || y == 0 || y + 1 == h
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: per_color_integer <board.json>");
        std::process::exit(2);
    }
    let path = PathBuf::from(&args[0]);
    let board = load_board(&path, &puzzle).expect("load board");

    let w = puzzle.width;
    let h = puzzle.height;
    let n_cells = puzzle.cell_count();

    let mut per_color_ii: Vec<u32> = vec![0; 24];
    let mut per_color_bi: Vec<u32> = vec![0; 24];
    let mut per_color_bb: Vec<u32> = vec![0; 24];
    let mut count_ii_edges: u32 = 0;
    let mut count_bi_edges: u32 = 0;
    let mut count_bb_edges: u32 = 0;
    let mut match_ii: u32 = 0;
    let mut match_bi: u32 = 0;
    let mut match_bb: u32 = 0;

    let get_edges = |b: &Board, p: u32| b.get(p).map(|(pid, rot)| {
        puzzle.piece(pid).expect("piece").edges.rotated(rot).as_array()
    });

    for pos in 0..n_cells {
        let x = pos % w;
        let y = pos / w;
        let me = match get_edges(&board, pos) { Some(e) => e, None => continue };

        // East edge: my[1] vs east[3]
        if x + 1 < w {
            let np = pos + 1;
            let nx = (np) % w;
            let ny = (np) / w;
            let is_b1 = is_border(x, y, w, h);
            let is_b2 = is_border(nx, ny, w, h);
            let cls = match (is_b1, is_b2) {
                (true, true) => 0,    // BB
                (false, false) => 2,  // II
                _ => 1,               // BI
            };
            if let Some(ne) = get_edges(&board, np) {
                let a = me[1];
                let b = ne[3];
                match cls {
                    0 => { count_bb_edges += 1; if a == b { match_bb += 1; per_color_bb[a as usize] += 1; } }
                    1 => { count_bi_edges += 1; if a == b { match_bi += 1; per_color_bi[a as usize] += 1; } }
                    _ => { count_ii_edges += 1; if a == b { match_ii += 1; per_color_ii[a as usize] += 1; } }
                }
            } else {
                match cls {
                    0 => count_bb_edges += 1,
                    1 => count_bi_edges += 1,
                    _ => count_ii_edges += 1,
                }
            }
        }
        // South edge: my[2] vs south[0]
        if y + 1 < h {
            let np = pos + w;
            let nx = (np) % w;
            let ny = (np) / w;
            let is_b1 = is_border(x, y, w, h);
            let is_b2 = is_border(nx, ny, w, h);
            let cls = match (is_b1, is_b2) {
                (true, true) => 0,
                (false, false) => 2,
                _ => 1,
            };
            if let Some(ne) = get_edges(&board, np) {
                let a = me[2];
                let b = ne[0];
                match cls {
                    0 => { count_bb_edges += 1; if a == b { match_bb += 1; per_color_bb[a as usize] += 1; } }
                    1 => { count_bi_edges += 1; if a == b { match_bi += 1; per_color_bi[a as usize] += 1; } }
                    _ => { count_ii_edges += 1; if a == b { match_ii += 1; per_color_ii[a as usize] += 1; } }
                }
            } else {
                match cls {
                    0 => count_bb_edges += 1,
                    1 => count_bi_edges += 1,
                    _ => count_ii_edges += 1,
                }
            }
        }
    }

    println!("# board: {}", args[0]);
    println!("# edge counts:  II={count_ii_edges}  BI={count_bi_edges}  BB={count_bb_edges}  total={}",
        count_ii_edges + count_bi_edges + count_bb_edges);
    println!("# matched:      II={match_ii}  BI={match_bi}  BB={match_bb}  total={}",
        match_ii + match_bi + match_bb);
    println!();
    println!("# per-color INTEGER matches:");
    println!("# color  k:   II_int    BI_int    BB_int     TOTAL");
    let mut sum_ii: u32 = 0;
    let mut sum_bi: u32 = 0;
    let mut sum_bb: u32 = 0;
    for c in 1..24u8 {
        let ii = per_color_ii[c as usize];
        let bi = per_color_bi[c as usize];
        let bb = per_color_bb[c as usize];
        sum_ii += ii;
        sum_bi += bi;
        sum_bb += bb;
        println!("#   color {:2}:   {:6}    {:6}    {:6}    {:6}", c, ii, bi, bb, ii + bi + bb);
    }
    println!("#  ---------");
    println!("#   SUM    :   {:6}    {:6}    {:6}    {:6}", sum_ii, sum_bi, sum_bb, sum_ii + sum_bi + sum_bb);
}
