// Vol-17 NOVEL — iterated ALNS + cluster_repair multi-pass.
//
// Alternates short ALNS phases with dedicated cluster CP repair:
//   board = initial
//   for pass in 1..n_passes:
//       board = ALNS(board, alns_ms)
//       board = cluster_repair(board, cluster_ms)
//   return best
//
// Motivation: ALNS converges in ~30s (iter 33 typically) per E4 logs;
// continuing ALNS past that is wasted compute. cluster_repair on the
// frozen-cluster gives a fresh perspective via long CP search.
// Combining them in multi-pass might compound (ALNS → cluster → ALNS).
//
// CLI:
//   alns_cluster_loop --cp-board PATH --n-passes 3 --alns-ms 60000
//                     --cluster-ms 30000 --halo 1 --ops winning5
//                     --seed 1

#![forbid(unsafe_code)]

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board, ProgressSink};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Hint, Hints, Rotation};
use eternity2_localsearch::{
    find_mismatches, piece_swap_hillclimb, polish_rotations, run_alns, Acceptance,
    AlnsConfig, ConflictDriven, DestroyOp, MwpmDefectPair, RandomRegion, RepairKind,
    WorstBand, WorstWindow,
};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

fn build_winning5() -> Vec<Box<dyn DestroyOp>> {
    vec![
        Box::new(RandomRegion { k: 4 }),
        Box::new(WorstWindow { k: 5 }),
        Box::new(ConflictDriven { max_size: 30 }),
        Box::new(ConflictDriven { max_size: 80 }),
        Box::new(MwpmDefectPair { max_pairs: 12 }),
        Box::new(WorstBand { k_rows: 4 }),
    ]
}

fn load_board(path: &std::path::Path) -> Board {
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

/// Run dedicated cluster CP repair on `board`. Returns the repaired board.
fn cluster_repair_step(
    puzzle: &eternity2_core::Puzzle,
    canonical_hints: &Hints,
    board: &Board,
    cp_budget_ms: u64,
    halo: u32,
    log_idx: u64,
) -> Board {
    let w = puzzle.width;
    let h = puzzle.height;
    let mismatches = find_mismatches(puzzle, board);
    let mut mismatch_cells: BTreeSet<u32> = BTreeSet::new();
    for m in &mismatches {
        mismatch_cells.insert(m.cell_a);
        mismatch_cells.insert(m.cell_b);
    }
    let mut free: BTreeSet<u32> = mismatch_cells.clone();
    for _ in 0..halo {
        let snapshot: Vec<u32> = free.iter().copied().collect();
        for p in snapshot {
            let x = p % w; let y = p / w;
            if x + 1 < w { free.insert(p + 1); }
            if x > 0 { free.insert(p - 1); }
            if y + 1 < h { free.insert(p + w); }
            if y > 0 { free.insert(p - w); }
        }
    }
    // Canonical hints never freed.
    for h in &canonical_hints.hints {
        free.remove(&h.position);
    }
    if free.is_empty() {
        return board.clone(); // No cluster to repair.
    }
    eprintln!("  cluster_repair: {} cells free", free.len());

    let mut hints_vec: Vec<Hint> = Vec::new();
    for pos in 0..puzzle.cell_count() {
        if free.contains(&pos) { continue; }
        if let Some((pid, rot)) = board.get(pos) {
            hints_vec.push(Hint { position: pos, piece_id: pid, rotation: rot });
        }
    }
    let hints = Hints::new(hints_vec);
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = cp_budget_ms;
    opts.seed = 1 + log_idx;
    opts.hints = hints;

    let mut solver: Box<EngineSolver> = Box::new(EngineSolver::gacolor_ac3_par());
    let log_dir = PathBuf::from("output/v17_alns_cluster");
    let _ = std::fs::create_dir_all(&log_dir);
    let log_path = log_dir.join(format!("cluster_pass{log_idx}.log"));
    let mut sink = ProgressSink::new(&log_path, 5_000).expect("log");
    let outcome = solver.solve(puzzle, &opts, &mut sink);
    match outcome {
        SolveOutcome::Solved(b)
        | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| board.clone()),
        _ => board.clone(),
    }
}

fn main() {
    let mut cp_board_path = PathBuf::new();
    let mut n_passes: u32 = 3;
    let mut alns_ms: u64 = 60_000;
    let mut cluster_ms: u64 = 30_000;
    let mut halo: u32 = 1;
    let mut seed: u64 = 1;
    let mut t: f64 = 1.0;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--cp-board" => cp_board_path = PathBuf::from(args.next().unwrap()),
            "--n-passes" => n_passes = args.next().unwrap().parse().unwrap(),
            "--alns-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--cluster-ms" => cluster_ms = args.next().unwrap().parse().unwrap(),
            "--halo" => halo = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--t" => t = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if cp_board_path.as_os_str().is_empty() {
        eprintln!("--cp-board required");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let cp_board = load_board(&cp_board_path);
    let (m0, _) = score_board(&puzzle, &cp_board);
    let p0 = placed_count(&cp_board, &puzzle);
    eprintln!("loaded CP board: {p0} placed, {m0}/480 matched");
    eprintln!(
        "alns_cluster_loop: n_passes={n_passes} alns_ms={alns_ms} cluster_ms={cluster_ms} halo={halo} t={t}"
    );

    let pinned_set: BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();
    let t0 = Instant::now();
    let mut current = cp_board.clone();
    let mut best = current.clone();
    let mut best_score = score_board(&puzzle, &best).0;

    for pass in 1..=n_passes {
        eprintln!("\n=== Pass {pass}/{n_passes} ===");
        // Stage A: ALNS.
        let mut ops = build_winning5();
        let cfg = AlnsConfig {
            time_budget_ms: alns_ms,
            repair_budget_ms: 1500,
            acceptance: Acceptance::SimulatedAnnealing { t },
            segment_iters: 50,
            seed: seed.wrapping_add(pass as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15),
            verbose: false,
            repair: RepairKind::Sa,
            cp_fallback_to_sa: true,
            pinned_positions: hints.hints.iter().map(|h| h.position).collect(),
            iter_budget: 0,
            lex_break_isoscore: false,
        checkpoint_path: None,
        checkpoint_every_ms: 60_000,
        };
        let alns_t = Instant::now();
        let (alns_board, alns_stats) = run_alns(&puzzle, &current, ops.as_mut_slice(), &cfg);
        let (alns_board, _) = polish_rotations(&puzzle, &alns_board, &pinned_set);
        let (alns_board, _) = piece_swap_hillclimb(&puzzle, &alns_board, &pinned_set);
        let (am, _) = score_board(&puzzle, &alns_board);
        eprintln!(
            "  ALNS pass {pass}: {:.1}s iters={} matched={am}/480",
            alns_t.elapsed().as_secs_f64(), alns_stats.iters
        );
        if am > best_score {
            best = alns_board.clone();
            best_score = am;
        }
        current = alns_board;

        // Stage B: cluster repair.
        let cr_t = Instant::now();
        let cluster_board = cluster_repair_step(&puzzle, &hints, &current, cluster_ms, halo, pass as u64);
        let (cluster_board, _) = polish_rotations(&puzzle, &cluster_board, &pinned_set);
        let (cluster_board, _) = piece_swap_hillclimb(&puzzle, &cluster_board, &pinned_set);
        let (cm, _) = score_board(&puzzle, &cluster_board);
        eprintln!(
            "  cluster pass {pass}: {:.1}s matched={cm}/480",
            cr_t.elapsed().as_secs_f64()
        );
        if cm > best_score {
            best = cluster_board.clone();
            best_score = cm;
        }
        current = cluster_board;
    }

    let elapsed = t0.elapsed();
    let (m_best, _) = score_board(&puzzle, &best);
    let p_best = placed_count(&best, &puzzle);
    let url = bucas_url(&puzzle, &best, "v17_alns_cluster_loop");
    eprintln!(
        "\n=== alns_cluster_loop summary ===\nbest: matched={m_best}/480 placed={p_best}/256 elapsed={:.1}s",
        elapsed.as_secs_f64()
    );
    eprintln!("bucas: {url}");

    let log_dir = PathBuf::from("output/v17_alns_cluster");
    let _ = std::fs::create_dir_all(&log_dir);
    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let json = serde_json::json!({
        "matched_best": m_best, "placed_best": p_best,
        "elapsed_s": elapsed.as_secs_f64(),
        "n_passes": n_passes, "alns_ms": alns_ms, "cluster_ms": cluster_ms,
        "bucas_url": url,
        "placement": (0..puzzle.cell_count()).map(|p| {
            best.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    let _ = std::fs::write(log_dir.join(format!("final_{run_id}.json")), serde_json::to_string_pretty(&json).unwrap());
    eprintln!("saved: output/v17_alns_cluster/final_{run_id}.json");
}
