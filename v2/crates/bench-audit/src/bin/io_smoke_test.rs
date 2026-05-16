// io_smoke_test — vol-118 T8 smoke test the canonical load_board against
// our actual in-the-wild JSON formats.

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_export::{load_board, save_board, verify, BoardMetadata};

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let test_paths = vec![
        "output/vol-110/basins/bseed1_score459.json",
        "output/vol-65/mcgavin_469.json",
        "output/vol-118/v17a_par8_60s_FIXED.json",
    ];

    for p in test_paths {
        let path = PathBuf::from(p);
        match load_board(&path, &puzzle) {
            Ok(b) => {
                let r = verify(&puzzle, &hints, &b);
                println!(
                    "{}: placed={} matched={}/{} legal={}",
                    p, r.placed_count, r.matched, r.total_adjacencies, r.is_legal()
                );
            }
            Err(e) => println!("{}: ERROR {}", p, e),
        }
    }

    // Round-trip save: take the 452 board, save it via canonical, reload, verify.
    let path = PathBuf::from("output/v17_alns_only/winning5_sa_t1_s100_1778945478_858113000_p17748.json");
    let b = load_board(&path, &puzzle).expect("load 452");
    let out_path = PathBuf::from("/tmp/io_smoke_test_canonical.json");
    save_board(&out_path, &puzzle, &b, &BoardMetadata::default()).expect("save");
    let b2 = load_board(&out_path, &puzzle).expect("reload");
    let r = verify(&puzzle, &hints, &b2);
    println!("round-trip: placed={} matched={}/{} legal={}",
        r.placed_count, r.matched, r.total_adjacencies, r.is_legal());
    assert_eq!(r.matched, 452, "round-trip score preserved");
    println!("OK: canonical JSON round-trip preserves the 452 board exactly.");
}
