#![forbid(unsafe_code)]
use std::path::PathBuf;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
fn main() {
    let ids: Vec<u32> = std::env::args().skip(1).map(|s| s.parse().unwrap()).collect();
    let pp = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&pp).expect("load");
    for pid in ids {
        let p = &puzzle.pieces()[pid as usize];
        let e = p.edges.rotated(Rotation::R0).as_array();
        let zeros = e.iter().filter(|&&x| x == 0).count();
        let kind = match zeros { 2 => "CORNER", 1 => "EDGE", _ => "INTERIOR" };
        println!("pid={} [{}] orig=({}, {}, {}, {})", pid, kind, e[0], e[1], e[2], e[3]);
    }
}
