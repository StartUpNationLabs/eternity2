// Vol-125 T4 — Cube-and-conquer driver for canonical E2 SAT.
//
// Generates the canonical SAT CNF once + the variable index, then writes
// many "cubed" CNF files, each obtained by appending unit clauses for a
// specific assignment of structural decision variables.
//
// Decision variables (priority order):
//   1. Top-row first 4 cells (after corner 0): pos 1, 2, 3, 4. Each
//      cell has ~10-15 candidates. We pick TOP-K cube branches per cell.
//   2. Left-col first 4 cells: pos 16, 32, 48, 64.
//
// For each cube: write the original CNF prefix + unit clauses for the
// cube's decisions + 0-terminator. Save with a deterministic filename
// so the driver script can solve each in parallel.

#![forbid(unsafe_code)]

use std::collections::BTreeMap;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_sat_encoder::{encode, EncodeOptions, VarMap};
use eternity2_core::Hints;

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut out_dir = PathBuf::from("output/vol-125/sat_cubes");
    let mut decision_cells: Vec<u32> = vec![1, 2, 3, 4, 16, 32, 48, 64];
    let mut top_k: usize = 2;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--out-dir" => out_dir = PathBuf::from(args.next().unwrap()),
            "--decision-cells" => {
                let s = args.next().unwrap();
                decision_cells = s.split(',').map(|x| x.parse().unwrap()).collect();
            }
            "--top-k" => top_k = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    std::fs::create_dir_all(&out_dir).expect("mkdir");

    println!("Loading puzzle: {}", puzzle_path.display());
    let (puzzle, file_hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let n_cells = puzzle.cell_count();
    println!("Puzzle {}×{}, n_cells={}, n_pieces={}",
             puzzle.width, puzzle.height, n_cells, puzzle.pieces().len());

    println!("Building VarMap...");
    let vmap = VarMap::build(&puzzle);
    println!("  n_vars = {}", vmap.n_vars);

    println!("Encoding CNF...");
    let opts = EncodeOptions { soft_edge_match: false };
    let cnf = encode(&puzzle, &file_hints, &vmap, &opts);
    println!("  hard clauses = {}, soft = {}, next_aux = {}",
             cnf.clauses.len(), cnf.soft_clauses.len(), cnf.next_aux_var);

    // For each decision cell, list candidate (piece_idx, rot, var_id), sorted
    // by some heuristic. We use plain enumeration order; the top-K cubes are
    // simply the first K candidates per cell.
    let mut cell_candidates: BTreeMap<u32, Vec<(u32, u8, u32)>> = BTreeMap::new();
    for &cell in &decision_cells {
        let cands = &vmap.cell_to_pr[cell as usize];
        let mut v: Vec<(u32, u8, u32)> = cands.iter()
            .map(|(pidx, rot, var)| (*pidx, rot.as_u8(), *var))
            .collect();
        v.sort_by_key(|t| (t.0, t.1));
        cell_candidates.insert(cell, v);
    }

    println!("Decision cells and candidate counts:");
    for (cell, cands) in &cell_candidates {
        println!("  cell {}: {} candidates", cell, cands.len());
    }

    // Cartesian product over decisions, taking top_k per cell.
    let cells: Vec<u32> = decision_cells.clone();
    // per-cell list of (piece_idx, var_id). We take ALL candidates per cell;
    // dedup-by-piece happens in the Cartesian-product enumeration below.
    let per_cell_pcvar: Vec<Vec<(u32, i64)>> = cells.iter().map(|c| {
        let cands = &cell_candidates[c];
        cands.iter().take(top_k).map(|(pidx, _rot, v)| (*pidx, *v as i64)).collect()
    }).collect();

    let n_raw_cubes: u128 = per_cell_pcvar.iter().map(|v| v.len() as u128).product();
    println!("Raw cubes (before piece-uniqueness filter): {}", n_raw_cubes);
    if n_raw_cubes > 1_000_000 {
        println!("WARNING: > 1M raw cubes — consider smaller top_k or fewer cells");
    }

    // Write the BASE CNF once. Each cube is a tiny file with just the
    // assumption unit clauses; the runner cats base + cube → kissat.
    let base_path = out_dir.join("base.cnf");
    println!("Writing base CNF to {}...", base_path.display());
    {
        let mut f = BufWriter::new(File::create(&base_path).expect("base cnf"));
        // n_vars matches cnf.next_aux_var - 1.
        let n_vars_base = cnf.next_aux_var - 1;
        writeln!(f, "p cnf {} {}", n_vars_base, cnf.clauses.len()).unwrap();
        for cl in &cnf.clauses {
            for lit in cl { write!(f, "{lit} ").unwrap(); }
            writeln!(f, "0").unwrap();
        }
    }
    let base_size = std::fs::metadata(&base_path).map(|m| m.len()).unwrap_or(0);
    println!("  base.cnf size: {:.1} MB", base_size as f64 / 1.0e6);

    // Index for cube selections.
    let index_path = out_dir.join("index.tsv");
    let mut idx_file = BufWriter::new(File::create(&index_path).expect("idx"));
    writeln!(idx_file, "cube_id\tfilename\t{}", cells.iter().map(|c| format!("cell{c}")).collect::<Vec<_>>().join("\t")).unwrap();

    // Iterate Cartesian product, FILTER for piece-uniqueness
    let mut cube_id: u64 = 0;
    let mut idxs: Vec<usize> = vec![0; cells.len()];
    let mut n_skipped: u64 = 0;
    'outer: loop {
        let cube_pcs: Vec<(u32, i64)> = idxs.iter().zip(per_cell_pcvar.iter())
            .map(|(i, lits)| lits[*i])
            .collect();
        // Piece-uniqueness: skip if any two cells pick the same piece.
        let mut pieces_seen = std::collections::HashSet::new();
        let mut conflict = false;
        for (pidx, _) in &cube_pcs {
            if !pieces_seen.insert(*pidx) { conflict = true; break; }
        }
        if conflict {
            n_skipped += 1;
            // Advance odometer (duplicate of the advance block below)
            let mut i = idxs.len();
            loop {
                if i == 0 { break 'outer; }
                i -= 1;
                idxs[i] += 1;
                if idxs[i] < per_cell_pcvar[i].len() { break; }
                idxs[i] = 0;
                if i == 0 { break 'outer; }
            }
            continue;
        }
        let cube_lits: Vec<i64> = cube_pcs.iter().map(|(_, v)| *v).collect();
        // Tiny per-cube file: just the assumption unit clauses (no header).
        // Runner cat's base + this together. ~30 bytes per file.
        let fname = format!("cube_{:06}.assume", cube_id);
        let path = out_dir.join(&fname);
        let mut f = BufWriter::new(File::create(&path).expect("cube"));
        for lit in &cube_lits {
            writeln!(f, "{lit} 0").unwrap();
        }
        write!(idx_file, "{}\t{}", cube_id, fname).unwrap();
        for lit in &cube_lits {
            write!(idx_file, "\t{lit}").unwrap();
        }
        writeln!(idx_file).unwrap();
        cube_id += 1;
        if cube_id % 50 == 0 {
            println!("  wrote {cube_id} cubes...");
        }

        // Advance odometer
        let mut i = idxs.len();
        loop {
            if i == 0 { break 'outer; }
            i -= 1;
            idxs[i] += 1;
            if idxs[i] < per_cell_pcvar[i].len() { break; }
            idxs[i] = 0;
            if i == 0 { break 'outer; }
        }
    }
    println!("DONE: wrote {} cubes ({} skipped for piece-dup) to {}",
             cube_id, n_skipped, out_dir.display());

    drop(file_hints);
    let _: Hints = Hints::new(Vec::new());

    println!("\nNext step:");
    println!("  for f in {}/cube_*.cnf; do kissat --time=600 $f; done", out_dir.display());
    println!("  Or use scripts/vol125_run_cubes.sh");
}
