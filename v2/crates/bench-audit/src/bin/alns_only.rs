// Vol-17 — replay ALNS on a saved Blackwood CP board.
//
// Saves the 5 minutes of CP each experiment, lets us iterate ALNS
// configs at 2× throughput. Loads a CP-board JSON (the existing
// `blackwood_raw_cp_board.json` format) and runs the same ops set
// as run_e2_blackwood.
//
// CLI:
//   alns_only --cp-board <path> --alns-budget-ms <N> --seed <N> [--ops <preset>]
//
// Ops presets:
//   --ops minimal   = RandomRegion{4}, WorstWindow{5}, ConflictDriven{30}, MwpmDefectPair{12}
//   --ops basic     = + WorstBand{4} (the 455-record set)
//   --ops full      = + ConflictDriven{80}, WorstBand{6}, ComponentDestroy,
//                       ComponentPlusHaloDestroy, WorstRow, HingeDestroy
//   --ops wbonly    = WorstBand{4} only
//   --ops cdonly    = ConflictDriven{80} only

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Rotation};
use eternity2_localsearch::{
    piece_swap_hillclimb, polish_rotations, run_alns, Acceptance, AlnsConfig,
    BottomBandDestroy, ComponentDestroy, ComponentPlusHaloDestroy, ConflictDriven, DestroyOp,
    HalfBoardDestroy, HingeDestroy, MegaBand, MwpmDefectPair, RandomRegion, RandomScatter,
    RepairKind, WorstBand, WorstColumn, WorstColumnBand, WorstRow, WorstWindow,
};

fn build_ops(preset: &str) -> Vec<Box<dyn DestroyOp>> {
    match preset {
        "minimal" => vec![
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
        ],
        "basic" => vec![
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
            Box::new(WorstBand { k_rows: 4 }),
        ],
        "winning5" => vec![
            // The 5-op set with ConflictDriven{80} added + WB — this is
            // the configuration that hit 455 on seed 1 with SA-primary.
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(ConflictDriven { max_size: 80 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
            Box::new(WorstBand { k_rows: 4 }),
        ],
        "diverse" => vec![
            // Vol-17 — winning5 + BottomBandDestroy to inject diversity in
            // the perfect zone. Tests H15: forcing bottom-row disturbance
            // breaks past 455 local optimum.
            Box::new(RandomRegion { k: 4 }),
            Box::new(WorstWindow { k: 5 }),
            Box::new(ConflictDriven { max_size: 30 }),
            Box::new(ConflictDriven { max_size: 80 }),
            Box::new(MwpmDefectPair { max_pairs: 12 }),
            Box::new(WorstBand { k_rows: 4 }),
            Box::new(BottomBandDestroy { k_rows: 3, first_row: 8 }),
            Box::new(BottomBandDestroy { k_rows: 4, first_row: 8 }),
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
        "wbonly" => vec![Box::new(WorstBand { k_rows: 4 })],
        "cdonly" => vec![Box::new(ConflictDriven { max_size: 80 })],
        "componentonly" => vec![Box::new(ComponentDestroy { max_size: 100, min_size: 4 })],
        "hingeonly" => vec![Box::new(HingeDestroy { halo: 1 })],
        // Vol-18 — escape 457 operator-lock with fundamentally different
        // proposals. MegaBand{8,10,12} destroys 128-192 cells; WorstColumn
        // and column-band sample orthogonal to row-bands; HalfBoardDestroy
        // is brutal; RandomScatter explores non-contiguous patterns.
        "mega" => vec![
            Box::new(MegaBand { k_rows: 8 }),
            Box::new(MegaBand { k_rows: 10 }),
            Box::new(MegaBand { k_rows: 12 }),
            Box::new(WorstColumn),
            Box::new(WorstColumnBand { k_cols: 4 }),
            Box::new(RandomScatter { k: 60 }),
        ],
        "mega_mix" => vec![
            // Vol-18 — combine winning5's reliable ops with mega-escape ops.
            // Gives ALNS adaptive weights the choice: small ops for
            // refinement, big ops for basin-escape.
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
        "halfboard" => vec![
            Box::new(HalfBoardDestroy { which: 0 }),
            Box::new(HalfBoardDestroy { which: 1 }),
            Box::new(HalfBoardDestroy { which: 2 }),
            Box::new(HalfBoardDestroy { which: 3 }),
        ],
        other => panic!("unknown --ops preset {other}; want minimal|basic|winning5|full|mega|mega_mix|halfboard|wbonly|cdonly|componentonly|hingeonly"),
    }
}

fn load_cp_board(path: &std::path::Path) -> Board {
    let raw = std::fs::read_to_string(path).expect("read cp board");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse cp board");
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let mut b = Board::empty(&puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for p in arr {
            if p.is_null() { continue; }
            let pos = p["pos"].as_u64().unwrap() as u32;
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot_u = p["rotation"].as_u64().unwrap() as u8;
            let rot = Rotation::from_u8(rot_u).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn main() {
    let mut cp_board_path = PathBuf::new();
    let mut alns_ms: u64 = 300_000;
    let mut seed: u64 = 1;
    let mut ops_preset = "winning5".to_string();
    let mut repair_budget_ms: u64 = 1500;
    let mut repair_kind = "sa".to_string();
    let mut t: f64 = 1.0;
    let mut lex = false;
    let mut repair_step_budget: u64 = 0;
    let mut cp_repair_parallel = true;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--cp-board" => cp_board_path = PathBuf::from(args.next().unwrap()),
            "--alns-budget-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--ops" => ops_preset = args.next().unwrap(),
            "--repair-budget-ms" => repair_budget_ms = args.next().unwrap().parse().unwrap(),
            "--repair-kind" => repair_kind = args.next().unwrap(),
            "--t" => t = args.next().unwrap().parse().unwrap(),
            "--lex" => lex = true,
            // Vol-17 OPTIMIZATION_REPORT phase 0 — determinism knobs.
            "--repair-step-budget" => repair_step_budget = args.next().unwrap().parse().unwrap(),
            "--cp-repair-single" => cp_repair_parallel = false,
            other => panic!("unknown arg {other}"),
        }
    }
    if cp_board_path.as_os_str().is_empty() {
        eprintln!("--cp-board PATH required");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let cp_board = load_cp_board(&cp_board_path);
    let (cp_m, _) = score_board(&puzzle, &cp_board);
    let cp_p = placed_count(&cp_board, &puzzle);
    eprintln!(
        "loaded CP board: {} placed, {}/480 matched",
        cp_p, cp_m
    );
    eprintln!(
        "ALNS config: ops={ops_preset} repair_kind={repair_kind} repair_budget_ms={repair_budget_ms} t={t} budget={alns_ms}ms seed={seed}"
    );

    let mut ops = build_ops(&ops_preset);
    let cfg = AlnsConfig {
        time_budget_ms: alns_ms,
        repair_budget_ms,
        acceptance: Acceptance::SimulatedAnnealing { t },
        segment_iters: 50,
        seed,
        verbose: false,
        repair: match repair_kind.as_str() {
            "sa" => RepairKind::Sa,
            "cp" => RepairKind::Cp,
            "ot" => RepairKind::IterativeOt,
            other => panic!("--repair-kind want sa|cp|ot, got {other}"),
        },
        cp_fallback_to_sa: true,
        pinned_positions: hints.hints.iter().map(|h| h.position).collect(),
        iter_budget: 0,
        lex_break_isoscore: lex,
        checkpoint_path: None,
        checkpoint_every_ms: 60_000,
        repair_step_budget,
        cp_repair_parallel,
    };

    let t0 = Instant::now();
    let (alns_board, stats) = run_alns(&puzzle, &cp_board, ops.as_mut_slice(), &cfg);
    let elapsed = t0.elapsed();
    let pinned_set: std::collections::BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();
    let (alns_board, rg) = polish_rotations(&puzzle, &alns_board, &pinned_set);
    let (alns_board, sg) = piece_swap_hillclimb(&puzzle, &alns_board, &pinned_set);

    let (am, _) = score_board(&puzzle, &alns_board);
    let ap = placed_count(&alns_board, &puzzle);
    let url = bucas_url(&puzzle, &alns_board, "v17_alns_only");

    eprintln!(
        "ALNS: elapsed={:.1}s iters={} placed={ap}/256 matched={am}/480 polish_rot=+{rg} polish_swap=+{sg}",
        elapsed.as_secs_f64(), stats.iters
    );
    // Vol-17 — show when new bests were found.
    if !stats.best_score_history.is_empty() {
        eprintln!("  best_score_history: {} entries", stats.best_score_history.len());
        for (iter, score) in &stats.best_score_history {
            eprintln!("    iter={iter:>4}  new_best={score}");
        }
    }
    for (i, name) in stats.op_names.iter().enumerate() {
        let inv = stats.per_op_invocations[i];
        let acc = stats.per_op_accepts[i];
        let rate = if inv > 0 { 100.0 * acc as f64 / inv as f64 } else { 0.0 };
        eprintln!("  {name:<24}  inv={inv:>4}  acc={acc:>4}  rate={rate:>5.1}%");
    }
    eprintln!("bucas: {url}");
    let json = serde_json::json!({
        "matched": am, "placed": ap,
        "ops_preset": ops_preset, "repair_kind": repair_kind,
        "repair_budget_ms": repair_budget_ms, "t": t, "alns_ms": alns_ms,
        "polish_rot_gain": rg, "polish_swap_gain": sg,
        "bucas_url": url,
        "placement": (0..puzzle.cell_count()).map(|p| {
            alns_board.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from("output/v17_alns_only");
    let _ = std::fs::create_dir_all(&out_dir);
    let p = out_dir.join(format!("{ops_preset}_{repair_kind}_t{t}_s{seed}_{run_id}.json"));
    let _ = std::fs::write(&p, serde_json::to_string_pretty(&json).unwrap());
    eprintln!("saved: {}", p.display());
}
