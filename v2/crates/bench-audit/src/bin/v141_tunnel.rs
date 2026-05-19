// V141-T1 — TUNNEL: PT with destroy-aggressiveness ladder per chain.

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Rotation};
use eternity2_localsearch::alns::score_board;
use eternity2_localsearch::{
    run_alns_pt, ConflictDriven, DestroyOp, MwpmDefectPair, PtAlnsConfig,
    RandomRegion, RepairKind, WorstBand, WorstWindow,
    polish_rotations, piece_swap_hillclimb,
};

fn load_cp_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Board {
    let raw = std::fs::read_to_string(path).expect("read board");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let mut b = Board::empty(puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for (idx, p) in arr.iter().enumerate() {
            if p.is_null() { continue; }
            let pos = match p.get("pos").and_then(|x| x.as_u64()) {
                Some(v) => v as u32, None => idx as u32,
            };
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot_u = p["rotation"].as_u64().unwrap() as u8;
            let rot = Rotation::from_u8(rot_u).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn ladder_ops(chain_idx: usize) -> Vec<Box<dyn DestroyOp>> {
    match chain_idx {
        0 => vec![
            Box::new(RandomRegion { k: 2 }),
            Box::new(WorstWindow { k: 3 }),
            Box::new(MwpmDefectPair { max_pairs: 6 }),
        ],
        1 => vec![
            Box::new(RandomRegion { k: 3 }),
            Box::new(WorstWindow { k: 4 }),
            Box::new(ConflictDriven { max_size: 20 }),
            Box::new(MwpmDefectPair { max_pairs: 8 }),
        ],
        2 => vec![
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
            Box::new(WorstBand { k_rows: 4 }),
        ],
        3 => vec![
            Box::new(RandomRegion { k: 6 }),
            Box::new(WorstWindow { k: 7 }),
            Box::new(ConflictDriven { max_size: 50 }),
            Box::new(MwpmDefectPair { max_pairs: 16 }),
            Box::new(WorstBand { k_rows: 6 }),
        ],
        _ => vec![
            Box::new(RandomRegion { k: 8 }),
            Box::new(WorstWindow { k: 9 }),
            Box::new(ConflictDriven { max_size: 80 }),
            Box::new(MwpmDefectPair { max_pairs: 24 }),
            Box::new(WorstBand { k_rows: 8 }),
        ],
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut seconds: u64 = 300;
    let mut chains: usize = 5;
    let mut seed: u64 = 42;
    let mut seed_board: Option<PathBuf> = None;
    let mut it = args.iter().skip(1);
    while let Some(arg) = it.next() {
        match arg.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(it.next().expect("--puzzle path")),
            "--seconds" => seconds = it.next().unwrap().parse().unwrap(),
            "--chains" => chains = it.next().unwrap().parse().unwrap(),
            "--seed" => seed = it.next().unwrap().parse().unwrap(),
            "--seed-board" => seed_board = Some(PathBuf::from(it.next().expect("--seed-board path"))),
            other => panic!("unknown arg: {}", other),
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let initial = if let Some(p) = &seed_board {
        load_cp_board(p, &puzzle)
    } else {
        let mut b = Board::empty(&puzzle);
        for i in 0..(puzzle.width * puzzle.height) {
            let pid = (i as u16) as eternity2_core::PieceId;
            b.place(i, pid, Rotation::R0);
        }
        b
    };
    let init_s = score_board(&puzzle, &initial);
    let total = (puzzle.width - 1) * puzzle.height + puzzle.width * (puzzle.height - 1);
    eprintln!("V141 TUNNEL — chains={} seconds={} seed={}", chains, seconds, seed);
    eprintln!("Initial: {}/{}", init_s, total);

    let cfg = PtAlnsConfig {
        n_chains: chains,
        t_min: 0.5,
        t_max: 4.0,
        geometric_ladder: true,
        inner_iters_per_round: 20,
        time_budget_ms: seconds * 1000,
        repair_budget_ms: 500,
        segment_iters: 50,
        seed,
        verbose: false,
        repair: RepairKind::Sa,
        cp_fallback_to_sa: true,
        pinned_positions: hints.hints.iter().map(|h| h.position).collect(),
    };

    let t0 = Instant::now();
    let (best, stats) = run_alns_pt(&puzzle, &initial, ladder_ops, &cfg);
    let elapsed = t0.elapsed();

    let pinned: std::collections::BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();
    let (best, _) = polish_rotations(&puzzle, &best, &pinned);
    let (best, _) = piece_swap_hillclimb(&puzzle, &best, &pinned);
    let best_s = score_board(&puzzle, &best);

    eprintln!("\n=== TUNNEL RESULT ===");
    eprintln!("elapsed: {:.1}s   rounds: {}", elapsed.as_secs_f64(), stats.rounds);
    eprintln!("best:    {}/{} ({:.1}%)   Δ = {:+}",
              best_s, total,
              (best_s as f64 / total as f64) * 100.0,
              best_s as i32 - init_s as i32);
    eprintln!("exchanges: {}/{} accepted",
              stats.exchange_accepts, stats.exchange_proposals);
    eprintln!("per-chain scores: {:?}", stats.per_chain_scores);
}
