// V130-T1 — Apply FILAMENT chain to a given board, report improvements.

use std::path::PathBuf;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle, Rotation};
use eternity2_localsearch::alns::{score_board, AlnsRng};
use eternity2_localsearch::filament::{run_filament_full, FilamentConfig};

fn load_cp_board(path: &std::path::Path, puzzle: &Puzzle) -> Board {
    let raw = std::fs::read_to_string(path).expect("read cp board");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse cp board");
    let mut b = Board::empty(puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for (idx, p) in arr.iter().enumerate() {
            if p.is_null() { continue; }
            let pos = match p.get("pos").and_then(|x| x.as_u64()) {
                Some(v) => v as u32,
                None => idx as u32,
            };
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot_u = p["rotation"].as_u64().unwrap() as u8;
            let rot = Rotation::from_u8(rot_u).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let board_path = args.get(1).expect("usage: v130_filament_apply <board.json> [n_seeds] [max_depth] [max_loss] [trials]").clone();
    let n_seeds: u32 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(16);
    let max_depth: u32 = args.get(3).and_then(|s| s.parse().ok()).unwrap_or(16);
    let max_loss: i32 = args.get(4).and_then(|s| s.parse().ok()).unwrap_or(4);
    let trials: u32 = args.get(5).and_then(|s| s.parse().ok()).unwrap_or(10);

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let board = load_cp_board(std::path::Path::new(&board_path), &puzzle);
    let initial = score_board(&puzzle, &board);
    let total_edges = (puzzle.width - 1) * puzzle.height + puzzle.width * (puzzle.height - 1);
    println!("Initial score: {}/{}", initial, total_edges);
    println!("Config: n_seeds={} max_depth={} max_loss={} trials={}",
             n_seeds, max_depth, max_loss, trials);

    let cfg = FilamentConfig {
        max_depth, max_loss, seed_worst: true, try_rotations: true, allow_revisit: false,
    };

    let mut best_board = board.clone();
    let mut best_score = initial;
    for trial in 0..trials {
        let mut rng = AlnsRng::new(42 + trial as u64);
        let (b, gain) = run_filament_full(&puzzle, &best_board, n_seeds, &cfg, &mut rng);
        let new_score = score_board(&puzzle, &b);
        if new_score > best_score {
            best_score = new_score;
            best_board = b;
            println!("Trial {:>3}: score → {} (gain {})", trial, new_score, gain);
        } else if trial % 3 == 0 {
            println!("Trial {:>3}: score → {} (no improvement)", trial, new_score);
        }
    }
    println!("Final: {}/{}", best_score, total_edges);
}
