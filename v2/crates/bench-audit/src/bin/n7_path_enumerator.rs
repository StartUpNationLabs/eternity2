// Vol-122 N7 — Pre-enumerate all valid 10-cell border-segment paths.
//
// For each border direction (top/right/bot/left) and each (start_color, end_color)
// pair in {1..22}^2, enumerate ALL valid 10-cell paths of edge pieces with
// matching color transitions and piece-uniqueness WITHIN the path.
//
// Output: report counts per (dir, start, end) cell of the matrix.
// If counts are tractable, store path bitsets for downstream multi-segment
// disjoint-set lookup.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;

#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
struct PieceSet { low: u128, high: u128 }
impl PieceSet {
    fn new() -> Self { Self { low: 0, high: 0 } }
    fn set(&mut self, pid: u16) {
        if pid < 128 { self.low |= 1u128 << pid; }
        else { self.high |= 1u128 << (pid - 128); }
    }
    fn contains(&self, pid: u16) -> bool {
        if pid < 128 { (self.low >> pid) & 1 == 1 }
        else { (self.high >> (pid - 128)) & 1 == 1 }
    }
}

fn rot_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    match r {
        0 => e,
        1 => [e[3], e[0], e[1], e[2]],
        2 => [e[2], e[3], e[0], e[1]],
        _ => [e[1], e[2], e[3], e[0]],
    }
}

#[derive(Clone, Copy, Debug)]
struct EdgeOption { pid: u16, rot: u8, left: u8, right: u8 }

fn precompute_edge_options(pieces: &[[u8; 4]]) -> [Vec<EdgeOption>; 4] {
    let mut by_dir: [Vec<EdgeOption>; 4] = Default::default();
    for (pid, e) in pieces.iter().enumerate() {
        let zeros = e.iter().filter(|&&x| x == 0).count();
        if zeros != 1 { continue; }
        for rot in 0..4u8 {
            let re = rot_edges(*e, rot);
            if re[0] == 0 { by_dir[0].push(EdgeOption { pid: pid as u16, rot, left: re[3], right: re[1] }); }
            if re[1] == 0 { by_dir[1].push(EdgeOption { pid: pid as u16, rot, left: re[0], right: re[2] }); }
            if re[2] == 0 { by_dir[2].push(EdgeOption { pid: pid as u16, rot, left: re[3], right: re[1] }); }
            if re[3] == 0 { by_dir[3].push(EdgeOption { pid: pid as u16, rot, left: re[0], right: re[2] }); }
        }
    }
    by_dir
}

fn bucket_by_left(opts: &[EdgeOption]) -> [Vec<EdgeOption>; 32] {
    let mut b: [Vec<EdgeOption>; 32] = Default::default();
    for opt in opts { b[opt.left as usize].push(*opt); }
    b
}

fn enumerate_paths(
    n_cells: usize,
    start_color: u8,
    end_color: u8,
    buckets: &[Vec<EdgeOption>; 32],
) -> u64 {
    let mut count: u64 = 0;
    let mut used = PieceSet::new();
    let mut current = start_color;
    enumerate_recurse(0, n_cells, &mut current, end_color, buckets, &mut used, &mut count);
    count
}

fn enumerate_recurse(
    step: usize,
    n_cells: usize,
    current: &mut u8,
    end: u8,
    buckets: &[Vec<EdgeOption>; 32],
    used: &mut PieceSet,
    count: &mut u64,
) {
    if step == n_cells {
        if *current == end { *count += 1; }
        return;
    }
    for &opt in &buckets[*current as usize] {
        if used.contains(opt.pid) { continue; }
        used.set(opt.pid);
        let saved = *current;
        *current = opt.right;
        enumerate_recurse(step + 1, n_cells, current, end, buckets, used, count);
        *current = saved;
        // unset
        if opt.pid < 128 { used.low &= !(1u128 << opt.pid); }
        else { used.high &= !(1u128 << (opt.pid - 128)); }
    }
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut n_cells: usize = 10;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--n-cells" => n_cells = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    let edge_opts = precompute_edge_options(&pieces);

    let dir_names = ["TOP", "RIGHT", "BOTTOM", "LEFT"];
    for dir in 0..4 {
        let buckets = bucket_by_left(&edge_opts[dir]);
        // Find non-empty start colors
        let mut start_colors: Vec<u8> = (0..32u8).filter(|c| !buckets[*c as usize].is_empty()).collect();
        if start_colors.contains(&0) { start_colors.retain(|c| *c != 0); }
        println!("\n=== {} ({} non-zero start colors) ===", dir_names[dir], start_colors.len());

        let t0 = Instant::now();
        let mut total_paths: u64 = 0;
        let mut max_per_pair: u64 = 0;
        let mut nonzero_pairs: u64 = 0;
        for &start in &start_colors {
            for end in 1..=22u8 {
                let count = enumerate_paths(n_cells, start, end, &buckets);
                if count > 0 {
                    nonzero_pairs += 1;
                    max_per_pair = max_per_pair.max(count);
                }
                total_paths += count;
            }
        }
        println!("  total paths: {} | nonzero (start,end) pairs: {} | max per pair: {} | {:.2}s",
            total_paths, nonzero_pairs, max_per_pair, t0.elapsed().as_secs_f64());
    }
}
