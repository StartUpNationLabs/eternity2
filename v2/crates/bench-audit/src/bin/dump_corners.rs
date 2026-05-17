#![forbid(unsafe_code)]
use std::path::PathBuf;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
fn main() {
    let pp = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&pp).expect("load");
    println!("Total pieces: {}", puzzle.pieces().len());
    let mut corners = vec![];
    for (i, p) in puzzle.pieces().iter().enumerate() {
        let e = p.edges.rotated(Rotation::R0).as_array();
        let zeros = e.iter().filter(|&&x| x == 0).count();
        if zeros == 2 {
            corners.push((i, e));
        }
    }
    println!("Corner pieces ({}):", corners.len());
    for (pid, e) in &corners {
        println!("  pid={}: edges (T,R,B,L) = ({:?})", pid, e);
    }
}
