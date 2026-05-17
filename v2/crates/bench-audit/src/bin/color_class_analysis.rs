// Color-class analysis for canonical E2.
//
// For each interior piece (4 non-border edges), compute its color multiset
// (sorted tuple of edge colors). Group pieces by color multiset.
//
// Hypothesis: rare color multisets must go in specific board positions,
// providing strong placement constraints.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::collections::HashMap;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;

fn main() {
    let pp = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&pp).expect("load");
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    // Classify each piece by # zero edges
    let mut interior = Vec::new();
    let mut edge_pieces = Vec::new();
    let mut corners = Vec::new();
    for (i, e) in pieces.iter().enumerate() {
        let zeros = e.iter().filter(|&&x| x == 0).count();
        match zeros {
            0 => interior.push((i, *e)),
            1 => edge_pieces.push((i, *e)),
            2 => corners.push((i, *e)),
            _ => panic!("unexpected"),
        }
    }
    println!("Corners: {}, edges: {}, interior: {}",
        corners.len(), edge_pieces.len(), interior.len());

    // For each interior piece, sorted color multiset
    let mut interior_classes: HashMap<[u8; 4], Vec<usize>> = HashMap::new();
    for (pid, e) in &interior {
        let mut sorted = *e;
        sorted.sort();
        interior_classes.entry(sorted).or_default().push(*pid);
    }
    let mut classes: Vec<_> = interior_classes.iter().collect();
    classes.sort_by_key(|(k, _v)| (k[0], k[1], k[2], k[3]));
    println!("\nInterior color-multiset classes: {} distinct", classes.len());

    let mut singletons = 0;
    let mut total_pieces_in_small = 0;
    for (multiset, pids) in &classes {
        if pids.len() == 1 {
            singletons += 1;
            total_pieces_in_small += 1;
        } else if pids.len() <= 3 {
            total_pieces_in_small += pids.len();
        }
    }
    println!("  Singletons (unique multiset): {}", singletons);
    println!("  In classes of size <= 3: {}", total_pieces_in_small);

    // Histogram of class sizes
    let mut size_hist: HashMap<usize, usize> = HashMap::new();
    for (_, pids) in &classes {
        *size_hist.entry(pids.len()).or_insert(0) += 1;
    }
    let mut size_vec: Vec<_> = size_hist.iter().collect();
    size_vec.sort_by_key(|(k, _)| **k);
    println!("\nClass size histogram (size: #classes):");
    for (size, count) in size_vec {
        println!("  size={}: {} classes", size, count);
    }

    // Show top-10 largest classes
    let mut classes_by_size = classes.clone();
    classes_by_size.sort_by_key(|(_, pids)| std::cmp::Reverse(pids.len()));
    println!("\nLargest classes:");
    for (multiset, pids) in classes_by_size.iter().take(5) {
        println!("  multiset={:?}: {} pieces (e.g., pid={})", multiset, pids.len(), pids[0]);
    }

    // Color frequency in interior pieces' edges
    let mut color_freq: HashMap<u8, usize> = HashMap::new();
    for (_, e) in &interior {
        for &c in e {
            *color_freq.entry(c).or_insert(0) += 1;
        }
    }
    let mut cf: Vec<_> = color_freq.iter().collect();
    cf.sort_by_key(|(_, v)| std::cmp::Reverse(**v));
    println!("\nInterior-edge color frequency (top 5):");
    for (c, n) in cf.iter().take(5) {
        println!("  color {}: {} occurrences (avg {:.2}/piece)", c, n, **n as f64 / interior.len() as f64);
    }
}
