// Map the mismatched edges in a canonical-E2 board, classify them by
// type (B-I, I-I), and analyse the I-I cluster structure.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use eternity2_bench_audit::border_ub::is_perimeter_pos;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use serde_json::Value;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}

/// Returns Vec of (pos_a, pos_b, type) for each mismatched adjacency.
/// type: 0=B-B, 1=B-I, 2=I-I.
fn mismatched_edges(puzzle: &Puzzle, board: &Board) -> Vec<(Position, Position, u8)> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut out = Vec::new();
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            let pos_per = is_perimeter_pos(puzzle, pos);
            let Some((pid, rot)) = board.get(pos) else { continue; };
            let Some(p) = puzzle.piece(pid) else { continue; };
            let e = p.edges.rotated(rot).as_array();
            // right
            if x + 1 < w {
                let n = y * w + (x + 1);
                let n_per = is_perimeter_pos(puzzle, n);
                if let Some((npid, nrot)) = board.get(n) {
                    if let Some(np) = puzzle.piece(npid) {
                        let ne = np.edges.rotated(nrot).as_array();
                        if e[1] != ne[3] {
                            let typ = match (pos_per, n_per) {
                                (true, true) => 0,
                                (true, false) | (false, true) => 1,
                                (false, false) => 2,
                            };
                            out.push((pos, n, typ));
                        }
                    }
                }
            }
            // bottom
            if y + 1 < h {
                let n = (y + 1) * w + x;
                let n_per = is_perimeter_pos(puzzle, n);
                if let Some((npid, nrot)) = board.get(n) {
                    if let Some(np) = puzzle.piece(npid) {
                        let ne = np.edges.rotated(nrot).as_array();
                        if e[2] != ne[0] {
                            let typ = match (pos_per, n_per) {
                                (true, true) => 0,
                                (true, false) | (false, true) => 1,
                                (false, false) => 2,
                            };
                            out.push((pos, n, typ));
                        }
                    }
                }
            }
        }
    }
    out
}

/// Union-find for cluster detection among I-I mismatched edges.
struct UnionFind {
    parent: HashMap<Position, Position>,
}
impl UnionFind {
    fn new() -> Self { UnionFind { parent: HashMap::new() } }
    fn find(&mut self, x: Position) -> Position {
        let p = *self.parent.entry(x).or_insert(x);
        if p == x { x } else {
            let root = self.find(p);
            self.parent.insert(x, root);
            root
        }
    }
    fn union(&mut self, a: Position, b: Position) {
        let ra = self.find(a);
        let rb = self.find(b);
        if ra != rb { self.parent.insert(ra, rb); }
    }
}

fn cluster_ii_mismatches(edges: &[(Position, Position, u8)]) -> Vec<Vec<Position>> {
    let mut uf = UnionFind::new();
    let mut all_cells = std::collections::BTreeSet::new();
    for &(a, b, t) in edges {
        if t == 2 {
            uf.union(a, b);
            all_cells.insert(a);
            all_cells.insert(b);
        }
    }
    let mut clusters: HashMap<Position, Vec<Position>> = HashMap::new();
    for cell in all_cells {
        let root = uf.find(cell);
        clusters.entry(root).or_default().push(cell);
    }
    let mut v: Vec<_> = clusters.into_values().collect();
    v.sort_by_key(|c| std::cmp::Reverse(c.len()));
    v
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: mismatch_map <board.json> [...]");
        std::process::exit(2);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    for arg in &args {
        let path = PathBuf::from(arg);
        match load_board(&path, &puzzle) {
            Ok(b) => {
                let edges = mismatched_edges(&puzzle, &b);
                let n_bb = edges.iter().filter(|(_, _, t)| *t == 0).count();
                let n_bi = edges.iter().filter(|(_, _, t)| *t == 1).count();
                let n_ii = edges.iter().filter(|(_, _, t)| *t == 2).count();
                println!("--- {} ---", arg);
                println!("Mismatches: BB={n_bb}  BI={n_bi}  II={n_ii}  total={}", edges.len());

                let bi_edges: Vec<_> = edges.iter().filter(|(_, _, t)| *t == 1).collect();
                println!("B-I mismatched edges:");
                for (a, b, _) in &bi_edges {
                    let (ax, ay) = puzzle.xy(*a);
                    let (bx, by) = puzzle.xy(*b);
                    let a_per = eternity2_bench_audit::border_ub::is_perimeter_pos(&puzzle, *a);
                    let b_per = eternity2_bench_audit::border_ub::is_perimeter_pos(&puzzle, *b);
                    let perim_pos = if a_per { *a } else { *b };
                    let int_pos = if a_per { *b } else { *a };
                    let (px, py) = puzzle.xy(perim_pos);
                    let (ix, iy) = puzzle.xy(int_pos);
                    println!("  perim {perim_pos}=({px},{py}) — interior {int_pos}=({ix},{iy})");
                }

                // I-I edges by (row, col)
                let ii_edges: Vec<_> = edges.iter().filter(|(_, _, t)| *t == 2).collect();
                println!("I-I mismatched edges (x,y of each endpoint):");
                for (a, b, _) in &ii_edges {
                    let (ax, ay) = puzzle.xy(*a);
                    let (bx, by) = puzzle.xy(*b);
                    println!("  {a:>3}=({ax},{ay}) — {b:>3}=({bx},{by})");
                }

                let clusters = cluster_ii_mismatches(&edges);
                println!("I-I mismatch clusters (cells touching ≥1 mismatch):");
                for (i, c) in clusters.iter().enumerate() {
                    let coords: Vec<String> = c.iter().map(|p| {
                        let (x, y) = puzzle.xy(*p);
                        format!("({x},{y})")
                    }).collect();
                    println!("  cluster #{i} size={} cells={:?}", c.len(), coords);
                }
            }
            Err(e) => eprintln!("{arg}\tERROR: {e}"),
        }
    }
}
