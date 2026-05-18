// Vol-125 T4b — smarter cube generator with adjacency pre-checking.
//
// Cubes a contiguous BLOCK of cells (e.g., 2x2 top-left region or a top
// row segment), enforcing both piece-uniqueness AND adjacency-color
// matching between cube cells. This avoids the vol-125-initial issue
// where 576 cubes were all trivially UNSAT due to top-row cells not
// edge-matching.
//
// Cube structure: pick K contiguous cells (e.g., positions 0..K on top
// row, or a 2x2 block). For each cell, enumerate all (piece, rot)
// candidates. Filter pairs/triples for both adjacency and uniqueness.

#![forbid(unsafe_code)]

use std::collections::BTreeMap;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_sat_encoder::{encode, EncodeOptions, VarMap};

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut out_dir = PathBuf::from("output/vol-125/sat_cubes_smart");
    // Default: top-row first 6 cells (positions 0-5) — a contiguous block.
    let mut decision_cells: Vec<u32> = vec![0, 1, 2, 3, 4, 5];

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--out-dir" => out_dir = PathBuf::from(args.next().unwrap()),
            "--decision-cells" => {
                let s = args.next().unwrap();
                decision_cells = s.split(',').map(|x| x.parse().unwrap()).collect();
            }
            other => panic!("unknown arg {other}"),
        }
    }
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    println!("Loading puzzle: {}", puzzle_path.display());
    let (puzzle, file_hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let width = puzzle.width as i64;
    let _height = puzzle.height as i64;

    println!("Building VarMap...");
    let vmap = VarMap::build(&puzzle);
    println!("  n_vars = {}", vmap.n_vars);

    println!("Encoding CNF...");
    let cnf = encode(&puzzle, &file_hints, &vmap, &EncodeOptions { soft_edge_match: false });
    println!("  hard clauses = {}", cnf.clauses.len());

    // Write base CNF once.
    let base_path = out_dir.join("base.cnf");
    {
        let mut f = BufWriter::new(File::create(&base_path).expect("base cnf"));
        let n_vars_base = cnf.next_aux_var - 1;
        writeln!(f, "p cnf {} {}", n_vars_base, cnf.clauses.len()).unwrap();
        for cl in &cnf.clauses {
            for lit in cl { write!(f, "{lit} ").unwrap(); }
            writeln!(f, "0").unwrap();
        }
    }
    println!("Wrote base.cnf");

    // For each decision cell, collect (piece_idx, rot, var_id, edge_colors) for all candidates.
    let cell_to_cands: BTreeMap<u32, Vec<(u32, u8, u32, [u8; 4])>> = decision_cells.iter()
        .map(|c| {
            let cands = &vmap.cell_to_pr[*c as usize];
            let mut v: Vec<(u32, u8, u32, [u8; 4])> = cands.iter().map(|(pidx, rot, var)| {
                let piece = &puzzle.pieces()[*pidx as usize];
                let edges = piece.edges.rotated(*rot);
                let nesw = [edges.top(), edges.right(), edges.bottom(), edges.left()];
                (*pidx, rot.as_u8(), *var, nesw)
            }).collect();
            v.sort_by_key(|t| (t.0, t.1));
            (*c, v)
        }).collect();

    for (cell, cands) in &cell_to_cands {
        println!("  cell {}: {} candidates", cell, cands.len());
    }

    // Adjacency helper: returns the (side_of_a, side_of_b) for adjacent cells a, b.
    // a, b must differ by 1 in row or 1 in column.
    fn adjacent_sides(a: u32, b: u32, width: i64) -> Option<(usize, usize)> {
        let (a_r, a_c) = (a as i64 / width, a as i64 % width);
        let (b_r, b_c) = (b as i64 / width, b as i64 % width);
        if a_r == b_r && b_c == a_c + 1 { Some((1, 3)) } // a's E, b's W
        else if a_r == b_r && a_c == b_c + 1 { Some((3, 1)) }
        else if a_c == b_c && b_r == a_r + 1 { Some((2, 0)) } // a's S, b's N
        else if a_c == b_c && a_r == b_r + 1 { Some((0, 2)) }
        else { None }
    }

    // Cartesian DFS with on-the-fly adjacency + piece-uniqueness filtering.
    let cells: Vec<u32> = decision_cells.clone();

    // Index file: each line = cube_id, var-list, piece-list.
    let index_path = out_dir.join("index.tsv");
    let mut idx_file = BufWriter::new(File::create(&index_path).expect("idx"));
    writeln!(idx_file, "cube_id\tfilename\tvars\tpieces").unwrap();

    let mut cube_id: u64 = 0;
    let mut chosen: Vec<(u32, u8, u32, [u8; 4])> = Vec::new();

    fn dfs(
        depth: usize,
        cells: &[u32],
        cands: &BTreeMap<u32, Vec<(u32, u8, u32, [u8; 4])>>,
        width: i64,
        chosen: &mut Vec<(u32, u8, u32, [u8; 4])>,
        out_dir: &PathBuf,
        cube_id: &mut u64,
        idx_file: &mut BufWriter<File>,
        n_skipped: &mut u64,
    ) {
        if depth == cells.len() {
            // Emit cube
            let lits: Vec<i64> = chosen.iter().map(|(_, _, v, _)| *v as i64).collect();
            let pieces: Vec<u32> = chosen.iter().map(|(p, _, _, _)| *p).collect();
            let fname = format!("cube_{:08}.assume", *cube_id);
            let path = out_dir.join(&fname);
            let mut f = BufWriter::new(File::create(&path).expect("cube"));
            for lit in &lits { writeln!(f, "{lit} 0").unwrap(); }
            // index entry
            let v_str: String = lits.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(",");
            let p_str: String = pieces.iter().map(|p| p.to_string()).collect::<Vec<_>>().join(",");
            writeln!(idx_file, "{}\t{}\t{}\t{}", cube_id, fname, v_str, p_str).unwrap();
            *cube_id += 1;
            if *cube_id % 1000 == 0 {
                println!("  emitted {} cubes (skipped {})", cube_id, n_skipped);
            }
            return;
        }
        let cell = cells[depth];
        let pool = &cands[&cell];
        for cand in pool {
            let (pidx, _rot, _var, edges) = *cand;
            // piece-uniqueness check
            if chosen.iter().any(|(p, _, _, _)| *p == pidx) {
                *n_skipped += 1;
                continue;
            }
            // adjacency check vs each prior chosen cell
            let mut ok = true;
            for (i, prior) in chosen.iter().enumerate() {
                let prior_cell = cells[i];
                if let Some((side_a, side_b)) = adjacent_sides(prior_cell, cell, width) {
                    if prior.3[side_a] != edges[side_b] {
                        ok = false; break;
                    }
                }
            }
            if !ok { *n_skipped += 1; continue; }
            chosen.push(*cand);
            dfs(depth + 1, cells, cands, width, chosen, out_dir, cube_id, idx_file, n_skipped);
            chosen.pop();
        }
    }

    let mut n_skipped: u64 = 0;
    dfs(0, &cells, &cell_to_cands, width, &mut chosen, &out_dir, &mut cube_id,
        &mut idx_file, &mut n_skipped);
    println!("DONE: emitted {} cubes ({} pruned by adjacency/uniqueness) to {}",
             cube_id, n_skipped, out_dir.display());
}
