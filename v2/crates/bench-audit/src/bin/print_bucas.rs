// print_bucas — print the bucas URL for a board JSON.
// Useful for inspecting partial boards visually.
// Vol-118 T9: migrated to canonical eternity2_export::load_board.

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_export::{bucas_url, load_board};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: print_bucas <board.json>");
        std::process::exit(1);
    }
    let path = PathBuf::from(&args[1]);
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let board = load_board(&path, &puzzle).expect("load board");
    let url = bucas_url(&puzzle, &board, "vol118_partial");
    println!("{}", url);
}
