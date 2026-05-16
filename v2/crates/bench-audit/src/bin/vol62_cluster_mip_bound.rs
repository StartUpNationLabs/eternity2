// Vol-62 — sound integer upper bound on local-repair score
// reachable from the 459 basin.
//
// For each connected component of defect cells, build a halo of radius r
// around the component's cells, then run the MIP-based cluster repairer.
// The MIP returns the maximum number of matched edges achievable by
// permuting+rotating the pieces in the cluster, holding everything outside
// FIXED.
//
// Output: per-component delta over the current 459 score, with the
// halo-radius dependency. If max delta ≤ 0 across all components at every
// reasonable radius, the 459 basin is locally MIP-optimal and any
// local-only operator (ComponentClusterDestroy included) cannot break it.
//
// This is a SOUND bound — not a heuristic. Cheap (~10-60s per cluster).
// Usage:
//   vol62_cluster_mip_bound BOARD.json [--radius R] [--time-limit-secs T]
//                                       [--all-radii]
//
// If --all-radii: sweeps r ∈ {0, 1, 2}; else uses single --radius (default 1).
//
// Does NOT use vault/concepts/relaxed_bound — uses the proper MIP.

#![forbid(unsafe_code)]

use std::collections::{BTreeSet, VecDeque};
use std::path::{Path, PathBuf};

use eternity2_bench_audit::cluster_repair::{repair_cluster, ClusterOptions};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation};
use eternity2_export::score_board;
use serde_json::Value;

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Result<eternity2_core::Board, String> {
    eternity2_export::load_board(path, puzzle).map_err(|e| format!("{e}"))
}

/// Find defect cells: cells incident on at least one mismatched edge.
fn defect_cells(puzzle: &Puzzle, board: &Board) -> BTreeSet<Position> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut out = BTreeSet::new();
    for y in 0..h {
        for x in 0..w {
            let c = y * w + x;
            let (pid_c, rot_c) = match board.get(c) {
                Some(v) => v,
                None => continue,
            };
            let edges_c = puzzle.piece(pid_c).unwrap().edges.rotated(rot_c).as_array();
            // right neighbour
            if x + 1 < w {
                let n = c + 1;
                if let Some((pid_n, rot_n)) = board.get(n) {
                    let edges_n = puzzle.piece(pid_n).unwrap().edges.rotated(rot_n).as_array();
                    // c's right (side 1) vs n's left (side 3)
                    if edges_c[1] != edges_n[3] {
                        out.insert(c);
                        out.insert(n);
                    }
                }
            }
            // below neighbour
            if y + 1 < h {
                let n = c + w;
                if let Some((pid_n, rot_n)) = board.get(n) {
                    let edges_n = puzzle.piece(pid_n).unwrap().edges.rotated(rot_n).as_array();
                    // c's bottom (side 2) vs n's top (side 0)
                    if edges_c[2] != edges_n[0] {
                        out.insert(c);
                        out.insert(n);
                    }
                }
            }
        }
    }
    out
}

/// 4-neighbour-adjacency components of defect cells.
fn defect_components(puzzle: &Puzzle, defects: &BTreeSet<Position>) -> Vec<Vec<Position>> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut visited = BTreeSet::new();
    let mut comps = Vec::new();
    for &s in defects {
        if visited.contains(&s) { continue; }
        let mut comp = Vec::new();
        let mut q = VecDeque::new();
        q.push_back(s);
        visited.insert(s);
        while let Some(p) = q.pop_front() {
            comp.push(p);
            let x = p % w;
            let y = p / w;
            let mut nbrs: Vec<Position> = Vec::with_capacity(4);
            if x + 1 < w { nbrs.push(p + 1); }
            if x > 0 { nbrs.push(p - 1); }
            if y + 1 < h { nbrs.push(p + w); }
            if y > 0 { nbrs.push(p - w); }
            for n in nbrs {
                if defects.contains(&n) && !visited.contains(&n) {
                    visited.insert(n);
                    q.push_back(n);
                }
            }
        }
        comps.push(comp);
    }
    comps
}

/// Expand cluster by `radius` 4-neighbour steps. Stay inside the board;
/// skip true perimeter cells (border-ring) to avoid disturbing fixed
/// frame structure (border-only repair can have huge regions that
/// blow up MIP time without real promise of improvement).
fn expand_with_halo(puzzle: &Puzzle, core: &[Position], radius: u32) -> Vec<Position> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut set: BTreeSet<Position> = core.iter().copied().collect();
    for _ in 0..radius {
        let snap: Vec<Position> = set.iter().copied().collect();
        for c in snap {
            let x = c % w;
            let y = c / w;
            // 4-neighbours
            let mut nbrs: Vec<Position> = Vec::with_capacity(4);
            if y > 0 { nbrs.push(c - w); }
            if x + 1 < w { nbrs.push(c + 1); }
            if y + 1 < h { nbrs.push(c + w); }
            if x > 0 { nbrs.push(c - 1); }
            for n in nbrs {
                let nx = n % w;
                let ny = n / w;
                // skip perimeter (border-ring) cells
                if nx == 0 || nx == w - 1 || ny == 0 || ny == h - 1 {
                    continue;
                }
                set.insert(n);
            }
        }
    }
    set.into_iter().collect()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut board_path = String::new();
    let mut radius: u32 = 1;
    let mut time_limit_secs: f64 = 30.0;
    let mut all_radii = false;
    let mut max_region_size: usize = 40;
    let mut joint_mip = false;
    let mut joint_halo: u32 = 1;
    let mut iter = args.iter().peekable();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--radius" => radius = iter.next().unwrap().parse().unwrap(),
            "--time-limit-secs" => time_limit_secs = iter.next().unwrap().parse().unwrap(),
            "--all-radii" => all_radii = true,
            "--max-region-size" => max_region_size = iter.next().unwrap().parse().unwrap(),
            "--joint-mip" => joint_mip = true,
            "--joint-halo" => joint_halo = iter.next().unwrap().parse().unwrap(),
            other => {
                if !other.starts_with("--") {
                    board_path = other.to_string();
                } else {
                    eprintln!("(unrecognized arg: {other})");
                }
            }
        }
    }
    if board_path.is_empty() {
        eprintln!("usage: vol62_cluster_mip_bound BOARD.json [--radius R] [--time-limit-secs T] [--all-radii]");
        std::process::exit(2);
    }

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let board = load_board(&PathBuf::from(&board_path), &puzzle).expect("load board");
    let (matched_0, total_0) = score_board(&puzzle, &board);
    println!("Board: {board_path}");
    println!("Score: {matched_0}/{total_0}");

    let defects = defect_cells(&puzzle, &board);
    let comps = defect_components(&puzzle, &defects);
    let mut comps_sorted: Vec<Vec<Position>> = comps.into_iter().collect();
    comps_sorted.sort_by_key(|c| std::cmp::Reverse(c.len()));
    println!("Defect cells: {}, components: {}", defects.len(), comps_sorted.len());
    println!("Component sizes: {:?}", comps_sorted.iter().map(|c| c.len()).collect::<Vec<_>>());

    let radii: Vec<u32> = if all_radii { vec![0, 1, 2] } else { vec![radius] };
    let opts_template = ClusterOptions { time_limit_secs, threads: 4, verbose: false };

    println!("\n{:-^110}", " per-component MIP-optimum local-repair scores ");
    println!("{:>4} | {:>5} | {:>5} | {:>5} | {:>6} | {:>6} | {:>5}",
             "comp", "core", "r", "size", "delta", "obj", "time(s)");
    println!("{}", "-".repeat(110));

    let mut best_overall_delta: i32 = 0;
    let mut total_jobs = 0;
    for (i, comp) in comps_sorted.iter().enumerate() {
        for &r in &radii {
            let region = expand_with_halo(&puzzle, comp, r);
            // Bail out if region is too large for MIP (configurable cap).
            if region.len() > max_region_size {
                println!("{:>4} | {:>5} | {:>5} | {:>5} | {:>6} | {:>6} | {:>5}",
                         i, comp.len(), r, region.len(), "skip", format!("(>{max_region_size})"), "");
                continue;
            }
            match repair_cluster(&puzzle, &board, &region, opts_template.clone()) {
                Ok(rep) => {
                    println!("{:>4} | {:>5} | {:>5} | {:>5} | {:>+6} | {:>6.1} | {:>5.2}",
                             i, comp.len(), r, region.len(), rep.delta, rep.obj_value, rep.solve_secs);
                    if rep.delta > best_overall_delta {
                        best_overall_delta = rep.delta;
                    }
                    total_jobs += 1;
                }
                Err(e) => {
                    println!("{:>4} | {:>5} | {:>5} | {:>5} | {:>6} | {:>6} | {} ERR: {e}",
                             i, comp.len(), r, region.len(), "?", "?", "");
                }
            }
        }
    }

    println!("\n{}", "=".repeat(70));
    println!("Best local-repair delta: {best_overall_delta:+}");
    println!("MIP-bound ceiling from this basin: {} (= score {matched_0} {:+})",
             matched_0 as i32 + best_overall_delta, best_overall_delta);
    println!("Total MIP jobs solved: {total_jobs}");

    if joint_mip {
        println!("\n{:-^110}", " JOINT MIP across ALL defect cells + halo ");
        let all_defects: Vec<Position> = defects.iter().copied().collect();
        let joint_region = expand_with_halo(&puzzle, &all_defects, joint_halo);
        println!("Joint region size: {} ({} defect cells + halo r={joint_halo})",
                 joint_region.len(), defects.len());
        if joint_region.len() > max_region_size * 3 {
            println!("Joint region too large ({} > {}), skipping",
                     joint_region.len(), max_region_size * 3);
        } else {
            let big_opts = ClusterOptions {
                time_limit_secs: time_limit_secs * 3.0,
                threads: opts_template.threads,
                verbose: false,
            };
            match repair_cluster(&puzzle, &board, &joint_region, big_opts) {
                Ok(rep) => {
                    println!("Joint MIP: delta={:+}, obj={:.1}, time={:.2}s",
                             rep.delta, rep.obj_value, rep.solve_secs);
                    if rep.delta > best_overall_delta {
                        best_overall_delta = rep.delta;
                    }
                }
                Err(e) => println!("Joint MIP ERROR: {e}"),
            }
        }
    }

    if best_overall_delta == 0 {
        println!("\n** This basin is MIP-locally optimal at every tested radius. **");
        println!("** ComponentClusterDestroy and similar local ops cannot break the basin **");
        println!("** without going board-spanning. Vol-62 must use BIGGER or NON-LOCAL ops. **");
    } else {
        println!("\n** Improvement found: delta={best_overall_delta:+}. **");
        println!("** New score: {}. **", matched_0 as i32 + best_overall_delta);
    }
}
