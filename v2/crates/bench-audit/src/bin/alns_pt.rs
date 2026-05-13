// Vol-17 NOVEL — Parallel Tempering on ALNS from a saved CP board.
//
// Runs N chains at fixed temperatures in a geometric (or linear) ladder.
// Each chain does inner_iters_per_round ALNS iterations in parallel, then
// adjacent pairs propose exchange of board states via Metropolis criterion.
// Repeat until time budget. Return global best.
//
// CLI:
//   alns_pt --cp-board PATH --n-chains N
//           --t-min F --t-max F [--linear-ladder]
//           --inner-iters K --time-budget-ms MS
//           --ops PRESET --seed BASE [--verbose]

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Rotation};
use eternity2_localsearch::{
    piece_swap_hillclimb, polish_rotations, run_alns_pt_multi_init, ComponentDestroy,
    ComponentPlusHaloDestroy, ConflictDriven, DestroyOp, HalfBoardDestroy, HingeDestroy,
    MegaBand, MwpmDefectPair, PtAlnsConfig, RandomRegion, RandomScatter, RepairKind, WorstBand,
    WorstColumn, WorstColumnBand, WorstRow, WorstWindow,
};

fn build_ops(preset: &str) -> Vec<Box<dyn DestroyOp>> {
    match preset {
        "minimal" => vec![
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
        ],
        "winning5" => vec![
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(ConflictDriven { max_size: 80 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
            Box::new(WorstBand { k_rows: 4 }),
        ],
        "full" => vec![
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(ConflictDriven { max_size: 80 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
            Box::new(WorstBand { k_rows: 4 }),
            Box::new(WorstBand { k_rows: 6 }),
            Box::new(ComponentDestroy { max_size: 100, min_size: 6 }),
            Box::new(ComponentPlusHaloDestroy { max_size: 100, min_size: 6 }),
            Box::new(WorstRow),
            Box::new(HingeDestroy { halo: 1 }),
        ],
        // Vol-18 — combine winning5 reliable ops with mega-escape ops to
        // bust through operator-locked basins (e.g., 457).
        "mega_mix" => vec![
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(ConflictDriven { max_size: 80 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
            Box::new(WorstBand { k_rows: 4 }),
            Box::new(MegaBand { k_rows: 8 }),
            Box::new(MegaBand { k_rows: 12 }),
            Box::new(WorstColumn),
            Box::new(WorstColumnBand { k_cols: 4 }),
            Box::new(RandomScatter { k: 60 }),
            Box::new(HalfBoardDestroy { which: 0 }),
        ],
        other => panic!("unknown --ops {other}"),
    }
}

fn load_cp_board(path: &std::path::Path) -> Board {
    let raw = std::fs::read_to_string(path).expect("read");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let mut b = Board::empty(&puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for p in arr {
            if p.is_null() { continue; }
            let pos = p["pos"].as_u64().unwrap() as u32;
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot = Rotation::from_u8(p["rotation"].as_u64().unwrap() as u8).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn main() {
    let mut cp_board_path = PathBuf::new();
    let mut cp_boards_paths: Vec<PathBuf> = Vec::new();
    let mut n_chains: usize = 4;
    let mut t_min: f64 = 0.5;
    let mut t_max: f64 = 2.0;
    let mut inner_iters: u32 = 25;
    let mut time_budget_ms: u64 = 300_000;
    let mut seed: u64 = 1;
    let mut ops_preset = "winning5".to_string();
    let mut repair_budget_ms: u64 = 1500;
    let mut linear_ladder = false;
    let mut verbose = false;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--cp-board" => cp_board_path = PathBuf::from(args.next().unwrap()),
            "--cp-boards" => {
                let v = args.next().unwrap();
                cp_boards_paths = v.split(',').map(PathBuf::from).collect();
            }
            "--n-chains" => n_chains = args.next().unwrap().parse().unwrap(),
            "--t-min" => t_min = args.next().unwrap().parse().unwrap(),
            "--t-max" => t_max = args.next().unwrap().parse().unwrap(),
            "--inner-iters" => inner_iters = args.next().unwrap().parse().unwrap(),
            "--time-budget-ms" => time_budget_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--ops" => ops_preset = args.next().unwrap(),
            "--repair-budget-ms" => repair_budget_ms = args.next().unwrap().parse().unwrap(),
            "--linear-ladder" => linear_ladder = true,
            "--verbose" => verbose = true,
            other => panic!("unknown arg {other}"),
        }
    }
    if cp_board_path.as_os_str().is_empty() && cp_boards_paths.is_empty() {
        eprintln!("--cp-board or --cp-boards required");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");

    // Multi-init mode: load N different CP boards (one per chain).
    let initials: Vec<Board> = if !cp_boards_paths.is_empty() {
        if cp_boards_paths.len() != n_chains {
            eprintln!("--cp-boards must have exactly n_chains entries; got {} for n_chains={}",
                cp_boards_paths.len(), n_chains);
            std::process::exit(1);
        }
        cp_boards_paths.iter().map(|p| load_cp_board(p)).collect()
    } else {
        // Single board, replicated across chains.
        let b = load_cp_board(&cp_board_path);
        vec![b; n_chains]
    };

    let cp_scores: Vec<u32> = initials.iter().map(|b| score_board(&puzzle, b).0).collect();
    eprintln!(
        "loaded {} CP boards: scores={:?}",
        initials.len(), cp_scores
    );
    eprintln!(
        "PT-ALNS config: n_chains={n_chains} t=[{t_min},{t_max}] geometric={} inner_iters={inner_iters} time_budget_ms={time_budget_ms} ops={ops_preset} repair_budget_ms={repair_budget_ms} seed={seed}",
        !linear_ladder
    );

    let cfg = PtAlnsConfig {
        n_chains,
        t_min,
        t_max,
        geometric_ladder: !linear_ladder,
        inner_iters_per_round: inner_iters,
        time_budget_ms,
        repair_budget_ms,
        segment_iters: inner_iters.max(50),
        seed,
        verbose,
        repair: RepairKind::Sa,
        cp_fallback_to_sa: true,
        pinned_positions: hints.hints.iter().map(|h| h.position).collect(),
    };
    let preset = ops_preset.clone();
    let ops_factory = move |_chain_idx: usize| build_ops(&preset);

    let t0 = Instant::now();
    let (best, pt_stats) = run_alns_pt_multi_init(&puzzle, &initials, ops_factory, &cfg);
    let elapsed = t0.elapsed();

    let pinned_set: std::collections::BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();
    let (best, rg) = polish_rotations(&puzzle, &best, &pinned_set);
    let (best, sg) = piece_swap_hillclimb(&puzzle, &best, &pinned_set);

    let (am, _) = score_board(&puzzle, &best);
    let ap = placed_count(&best, &puzzle);
    let url = bucas_url(&puzzle, &best, "v17_alns_pt");

    eprintln!("\n=== PT-ALNS summary ===");
    eprintln!("Rounds: {}", pt_stats.rounds);
    eprintln!(
        "Exchange: {}/{} accepted ({:.1}%)",
        pt_stats.exchange_accepts, pt_stats.exchange_proposals,
        100.0 * pt_stats.exchange_accepts as f64 / pt_stats.exchange_proposals.max(1) as f64,
    );
    for (i, (s, iters)) in pt_stats.per_chain_scores.iter().zip(pt_stats.per_chain_iters.iter()).enumerate() {
        eprintln!("  chain {i}: matched={s}/480  total_iters={iters}");
    }
    eprintln!(
        "\nGlobal best: matched={}/480 (chain {} at round {})",
        pt_stats.global_best_score, pt_stats.global_best_seen_at_chain, pt_stats.global_best_seen_at_round
    );
    eprintln!(
        "After polish: matched={am}/480 placed={ap}/256 elapsed={:.1}s (polish: rot=+{rg} swap=+{sg})",
        elapsed.as_secs_f64()
    );
    eprintln!("bucas: {url}");

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from("output/v17_alns_pt");
    let _ = std::fs::create_dir_all(&out_dir);
    let p = out_dir.join(format!("pt_{ops_preset}_n{n_chains}_t{t_min}_{t_max}_s{seed}_{run_id}.json"));
    let json = serde_json::json!({
        "matched_best": am, "placed_best": ap,
        "n_chains": n_chains, "t_min": t_min, "t_max": t_max,
        "rounds": pt_stats.rounds,
        "exchange_accepts": pt_stats.exchange_accepts,
        "exchange_proposals": pt_stats.exchange_proposals,
        "per_chain_scores": pt_stats.per_chain_scores,
        "per_chain_iters": pt_stats.per_chain_iters,
        "global_best_seen_at_round": pt_stats.global_best_seen_at_round,
        "global_best_seen_at_chain": pt_stats.global_best_seen_at_chain,
        "polish_rot_gain": rg, "polish_swap_gain": sg,
        "bucas_url": url,
        "placement": (0..puzzle.cell_count()).map(|p| {
            best.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    let _ = std::fs::write(&p, serde_json::to_string_pretty(&json).unwrap());
    eprintln!("saved: {}", p.display());
}
