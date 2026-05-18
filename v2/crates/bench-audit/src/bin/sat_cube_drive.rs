// Vol-125 T4c — single-process driver: enumerate cubes in-memory,
// pipe each to kissat via stdin, aggregate results. No millions of tiny
// files on disk.
//
// Cubes: K contiguous cells, top-K candidates per cell, filtered for
// piece-uniqueness AND adjacency-color match.

#![forbid(unsafe_code)]

use std::collections::BTreeMap;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_sat_encoder::{encode, EncodeOptions, VarMap};

#[derive(Clone)]
struct Args {
    puzzle_path: PathBuf,
    out_dir: PathBuf,
    decision_cells: Vec<u32>,
    timeout_s: u64,
    threads: usize,
}

fn parse_args() -> Args {
    let mut a = Args {
        puzzle_path: PathBuf::from("../data/puzzles/size_16_official_eternity.csv"),
        out_dir: PathBuf::from("output/vol-125/sat_cube_drive"),
        decision_cells: vec![0, 1, 2, 3, 4, 5],
        timeout_s: 60,
        threads: 4,
    };
    let mut args = std::env::args().skip(1);
    while let Some(x) = args.next() {
        match x.as_str() {
            "--puzzle" => a.puzzle_path = PathBuf::from(args.next().unwrap()),
            "--out-dir" => a.out_dir = PathBuf::from(args.next().unwrap()),
            "--decision-cells" => {
                a.decision_cells = args.next().unwrap().split(',').map(|s| s.parse().unwrap()).collect();
            }
            "--timeout-s" => a.timeout_s = args.next().unwrap().parse().unwrap(),
            "--threads" => a.threads = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    a
}

fn build_base_cnf(args: &Args) -> (String, BTreeMap<u32, Vec<(u32, u8, u32, [u8; 4])>>) {
    println!("Loading puzzle: {}", args.puzzle_path.display());
    let (puzzle, file_hints) = load_puzzle_with_hints(&args.puzzle_path).expect("load");
    let vmap = VarMap::build(&puzzle);
    let cnf = encode(&puzzle, &file_hints, &vmap, &EncodeOptions { soft_edge_match: false });
    println!("  n_vars = {}, n_clauses = {}", cnf.next_aux_var - 1, cnf.clauses.len());

    // Pre-render base CNF as a string (faster than re-rendering each cube).
    let n_vars_base = cnf.next_aux_var - 1;
    let mut base = String::with_capacity(140_000_000);
    base.push_str(&format!("p cnf {} {}\n", n_vars_base, cnf.clauses.len()));
    for cl in &cnf.clauses {
        for lit in cl { base.push_str(&format!("{lit} ")); }
        base.push_str("0\n");
    }
    println!("  base CNF rendered: {:.1} MB", base.len() as f64 / 1.0e6);

    // Collect decision-cell candidates with rotated edges.
    let cands: BTreeMap<u32, Vec<(u32, u8, u32, [u8; 4])>> = args.decision_cells.iter()
        .map(|c| {
            let v = &vmap.cell_to_pr[*c as usize];
            let mut vv: Vec<(u32, u8, u32, [u8; 4])> = v.iter().map(|(pidx, rot, var)| {
                let piece = &puzzle.pieces()[*pidx as usize];
                let edges = piece.edges.rotated(*rot);
                let nesw = [edges.top(), edges.right(), edges.bottom(), edges.left()];
                (*pidx, rot.as_u8(), *var, nesw)
            }).collect();
            vv.sort_by_key(|t| (t.0, t.1));
            (*c, vv)
        }).collect();
    (base, cands)
}

fn adjacent_sides(a: u32, b: u32, width: i64) -> Option<(usize, usize)> {
    let (a_r, a_c) = (a as i64 / width, a as i64 % width);
    let (b_r, b_c) = (b as i64 / width, b as i64 % width);
    if a_r == b_r && b_c == a_c + 1 { Some((1, 3)) }
    else if a_r == b_r && a_c == b_c + 1 { Some((3, 1)) }
    else if a_c == b_c && b_r == a_r + 1 { Some((2, 0)) }
    else if a_c == b_c && a_r == b_r + 1 { Some((0, 2)) }
    else { None }
}

fn enumerate_cubes(
    cells: &[u32],
    cands: &BTreeMap<u32, Vec<(u32, u8, u32, [u8; 4])>>,
    width: i64,
) -> Vec<Vec<i64>> {
    let mut out: Vec<Vec<i64>> = Vec::new();
    let mut chosen: Vec<(u32, u8, u32, [u8; 4])> = Vec::new();
    fn dfs(
        depth: usize,
        cells: &[u32],
        cands: &BTreeMap<u32, Vec<(u32, u8, u32, [u8; 4])>>,
        width: i64,
        chosen: &mut Vec<(u32, u8, u32, [u8; 4])>,
        out: &mut Vec<Vec<i64>>,
    ) {
        if depth == cells.len() {
            out.push(chosen.iter().map(|(_, _, v, _)| *v as i64).collect());
            return;
        }
        let cell = cells[depth];
        for cand in &cands[&cell] {
            if chosen.iter().any(|(p, _, _, _)| *p == cand.0) { continue; }
            let mut ok = true;
            for (i, prior) in chosen.iter().enumerate() {
                if let Some((sa, sb)) = adjacent_sides(cells[i], cell, width) {
                    if prior.3[sa] != cand.3[sb] { ok = false; break; }
                }
            }
            if !ok { continue; }
            chosen.push(*cand);
            dfs(depth + 1, cells, cands, width, chosen, out);
            chosen.pop();
        }
    }
    dfs(0, cells, cands, width, &mut chosen, &mut out);
    out
}

fn solve_one(base: &str, cube_lits: &[i64], timeout_s: u64) -> (String, f64) {
    let t0 = Instant::now();
    let mut child = Command::new("kissat")
        .arg("--relaxed")
        .arg(format!("--time={timeout_s}"))
        .arg("-q")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .expect("spawn kissat");
    {
        let stdin = child.stdin.as_mut().expect("stdin");
        stdin.write_all(base.as_bytes()).expect("write base");
        for lit in cube_lits {
            writeln!(stdin, "{lit} 0").expect("write lit");
        }
    }
    let out = child.wait_with_output().expect("wait");
    let stdout = String::from_utf8_lossy(&out.stdout);
    let status = stdout.lines().find(|l| l.starts_with("s "))
        .map(|l| l.split_whitespace().nth(1).unwrap_or("?").to_string())
        .unwrap_or("?".to_string());
    (status, t0.elapsed().as_secs_f64())
}

fn main() {
    let args = parse_args();
    std::fs::create_dir_all(&args.out_dir).expect("mkdir");

    let (base, cands) = build_base_cnf(&args);
    let width = 16i64; // canonical
    let cubes = enumerate_cubes(&args.decision_cells, &cands, width);
    println!("Total cubes: {}", cubes.len());

    let log_path = args.out_dir.join("results.tsv");
    let mut log = std::fs::File::create(&log_path).expect("log");
    writeln!(log, "cube_id\tstatus\tseconds\tvars").expect("hdr");
    let log = std::sync::Mutex::new(log);

    let found_sat = Arc::new(AtomicBool::new(false));
    let done_count = Arc::new(AtomicU64::new(0));
    let unsat_count = Arc::new(AtomicU64::new(0));
    let sat_count = Arc::new(AtomicU64::new(0));
    let unk_count = Arc::new(AtomicU64::new(0));

    let cubes_total = cubes.len();
    let next = Arc::new(AtomicU64::new(0));
    let base = Arc::new(base);

    let t_start = Instant::now();

    std::thread::scope(|s| {
        for _t in 0..args.threads {
            let base = base.clone();
            let cubes = &cubes;
            let log = &log;
            let found_sat = found_sat.clone();
            let done_count = done_count.clone();
            let unsat_count = unsat_count.clone();
            let sat_count = sat_count.clone();
            let unk_count = unk_count.clone();
            let next = next.clone();
            let timeout_s = args.timeout_s;
            let out_dir = args.out_dir.clone();
            s.spawn(move || {
                loop {
                    if found_sat.load(Ordering::Relaxed) { return; }
                    let id = next.fetch_add(1, Ordering::Relaxed);
                    if (id as usize) >= cubes.len() { return; }
                    let (status, elapsed) = solve_one(&base, &cubes[id as usize], timeout_s);
                    let cube_lits = &cubes[id as usize];
                    let var_str: String = cube_lits.iter().map(|v| v.to_string())
                        .collect::<Vec<_>>().join(",");
                    let mut log = log.lock().unwrap();
                    writeln!(log, "{id}\t{status}\t{elapsed:.3}\t{var_str}").ok();
                    drop(log);
                    let d = done_count.fetch_add(1, Ordering::Relaxed) + 1;
                    match status.as_str() {
                        "SATISFIABLE" => {
                            sat_count.fetch_add(1, Ordering::Relaxed);
                            found_sat.store(true, Ordering::Relaxed);
                            // Save SAT solution
                            let sat_log = out_dir.join(format!("SAT_cube_{id}.txt"));
                            let _ = std::fs::write(&sat_log,
                                format!("cube_id={id}\nvars={var_str}\n"));
                            eprintln!("!!! SAT on cube {id} (elapsed {elapsed:.2}s) !!!");
                        }
                        "UNSATISFIABLE" => { unsat_count.fetch_add(1, Ordering::Relaxed); }
                        _ => { unk_count.fetch_add(1, Ordering::Relaxed); }
                    }
                    if d % 50 == 0 || d == cubes_total as u64 {
                        let secs = t_start.elapsed().as_secs_f64();
                        let unsat = unsat_count.load(Ordering::Relaxed);
                        let unk = unk_count.load(Ordering::Relaxed);
                        let sat = sat_count.load(Ordering::Relaxed);
                        eprintln!("  [{:.0}s] done={}/{} (unsat={}, unk={}, sat={})",
                            secs, d, cubes_total, unsat, unk, sat);
                    }
                }
            });
        }
    });

    let total_done = done_count.load(Ordering::Relaxed);
    let total_sat = sat_count.load(Ordering::Relaxed);
    let total_unsat = unsat_count.load(Ordering::Relaxed);
    let total_unk = unk_count.load(Ordering::Relaxed);
    println!("\n=== FINAL ===");
    println!("Done: {}/{}", total_done, cubes_total);
    println!("SAT: {}", total_sat);
    println!("UNSAT: {}", total_unsat);
    println!("UNKNOWN/TIMEOUT: {}", total_unk);
    println!("Total wall: {:.1}s", t_start.elapsed().as_secs_f64());
    println!("Results: {}", log_path.display());
}
