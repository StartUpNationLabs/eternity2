// Run the CP-with-LP-UB-pruning search on canonical-E2.
//
// Usage: cp_search [--time-limit-secs N] [--threshold N] [--save-dir DIR]

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_cp_lp_search::{run_cp_lp_search, CpLpSearchOpts};
use eternity2_puzzle_io::load_puzzle_with_hints;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut time_limit_secs: f64 = 60.0;
    let mut threshold: f64 = 478.0;
    let mut save_dir = PathBuf::from("output/vol-46_cp_search");
    let mut iter = args.iter();
    while let Some(a) = iter.next() {
        match a.as_str() {
            "--time-limit-secs" => time_limit_secs = iter.next().unwrap().parse().unwrap(),
            "--threshold" => threshold = iter.next().unwrap().parse().unwrap(),
            "--save-dir" => save_dir = PathBuf::from(iter.next().unwrap()),
            other => eprintln!("unrecognized: {other}"),
        }
    }

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let opts = CpLpSearchOpts {
        threshold_ub: threshold,
        phase1_depth_max: 30,
        phase2_depth_max: 55,
        time_budget_secs: time_limit_secs,
        threads: 1,  // single-threaded driver for now
        save_dir,
        leaf_min_bb: 60,
    };
    println!("Starting CP search: threshold={threshold} budget={time_limit_secs}s save_dir={:?}", opts.save_dir);

    let r = run_cp_lp_search(&puzzle, &hints, &opts).expect("search");
    println!();
    println!("==== RESULT ====");
    println!("explored:           {}", r.n_explored);
    println!("pruned (cheap):     {}", r.n_pruned_cheap);
    println!("leaves kept:        {}", r.n_leaves_kept);
    println!("elapsed:            {:.2}s", r.elapsed_secs);
}
