// Vol-17 NOVEL — embarrassingly parallel best-of-K ALNS portfolio
// from a saved CP board. Runs N chains in parallel via rayon, each
// with different seed (and optionally different temperature).
//
// CLI:
//   alns_portfolio --cp-board PATH --n-chains N --alns-budget-ms MS
//                  --ops PRESET --seed BASE [--temperature-ladder]
//
// --temperature-ladder: chains use t = 0.5, 1.0, 1.5, 2.0, ...
//                       Otherwise all chains use t=1.0.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Rotation};
use eternity2_localsearch::{
    piece_swap_hillclimb, polish_rotations, run_alns_portfolio, Acceptance, AlnsConfig,
    ComponentDestroy, ComponentPlusHaloDestroy, ConflictDriven, DestroyOp, HingeDestroy,
    MwpmDefectPair, RandomRegion, RepairKind, WorstBand, WorstRow, WorstWindow,
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
    let mut n_chains: usize = 4;
    let mut alns_ms: u64 = 300_000;
    let mut seed: u64 = 1;
    let mut ops_preset = "winning5".to_string();
    let mut repair_budget_ms: u64 = 1500;
    let mut temperature_ladder = false;
    let mut t_min: f64 = 0.5;
    let mut t_max: f64 = 2.0;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--cp-board" => cp_board_path = PathBuf::from(args.next().unwrap()),
            "--n-chains" => n_chains = args.next().unwrap().parse().unwrap(),
            "--alns-budget-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--ops" => ops_preset = args.next().unwrap(),
            "--repair-budget-ms" => repair_budget_ms = args.next().unwrap().parse().unwrap(),
            "--temperature-ladder" => temperature_ladder = true,
            "--t-min" => t_min = args.next().unwrap().parse().unwrap(),
            "--t-max" => t_max = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if cp_board_path.as_os_str().is_empty() {
        eprintln!("--cp-board required");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let cp_board = load_cp_board(&cp_board_path);
    let (cp_m, _) = score_board(&puzzle, &cp_board);
    eprintln!(
        "loaded CP board: {} placed, {}/480 matched",
        placed_count(&cp_board, &puzzle), cp_m
    );
    eprintln!(
        "Portfolio config: n_chains={n_chains} ops={ops_preset} repair_budget_ms={repair_budget_ms} alns_ms={alns_ms} seed={seed} temperature_ladder={temperature_ladder}"
    );

    let base_cfg = AlnsConfig {
        time_budget_ms: alns_ms,
        repair_budget_ms,
        acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
        segment_iters: 50,
        seed,
        verbose: false,
        repair: RepairKind::Sa,
        cp_fallback_to_sa: true,
        pinned_positions: hints.hints.iter().map(|h| h.position).collect(),
        iter_budget: 0,
            lex_break_isoscore: false,
    };
    let preset = ops_preset.clone();
    let ops_factory = move |_chain_idx: usize| build_ops(&preset);

    let n_chains_clone = n_chains;
    let acceptance_for_chain = move |i: usize| -> Acceptance {
        if temperature_ladder {
            // Linear ladder from t_min to t_max.
            let denom = (n_chains_clone.saturating_sub(1)).max(1) as f64;
            let t = t_min + (t_max - t_min) * (i as f64) / denom;
            Acceptance::SimulatedAnnealing { t }
        } else {
            Acceptance::SimulatedAnnealing { t: 1.0 }
        }
    };

    let t0 = Instant::now();
    let (best, per_chain) = run_alns_portfolio(
        &puzzle, &cp_board, ops_factory, &base_cfg, n_chains, acceptance_for_chain,
    );
    let elapsed = t0.elapsed();

    let pinned_set: std::collections::BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();
    let (best, rg) = polish_rotations(&puzzle, &best, &pinned_set);
    let (best, sg) = piece_swap_hillclimb(&puzzle, &best, &pinned_set);

    let (am, _) = score_board(&puzzle, &best);
    let ap = placed_count(&best, &puzzle);
    let url = bucas_url(&puzzle, &best, "v17_alns_portfolio");

    eprintln!("\n=== ALNS portfolio summary ===");
    for (i, (score, stats)) in per_chain.iter().enumerate() {
        eprintln!(
            "  chain {i}: matched={score}/480  iters={}  acc_imp={}  acc_worse={}  rej={}  rep_fail={}",
            stats.iters, stats.accepted_improving, stats.accepted_worse,
            stats.rejected, stats.repair_failures
        );
    }
    eprintln!(
        "\nBest across {n_chains} chains: matched={am}/480 placed={ap}/256 elapsed={:.1}s (polish: rot=+{rg} swap=+{sg})",
        elapsed.as_secs_f64()
    );
    eprintln!("bucas: {url}");

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from("output/v17_alns_portfolio");
    let _ = std::fs::create_dir_all(&out_dir);
    let p = out_dir.join(format!("portfolio_{ops_preset}_n{n_chains}_s{seed}_{run_id}.json"));
    let json = serde_json::json!({
        "matched_best": am, "placed_best": ap, "elapsed_s": elapsed.as_secs_f64(),
        "n_chains": n_chains, "ops_preset": ops_preset,
        "per_chain_scores": per_chain.iter().map(|(s, _)| *s).collect::<Vec<_>>(),
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
