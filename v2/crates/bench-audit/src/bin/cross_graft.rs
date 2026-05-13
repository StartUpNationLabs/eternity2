// Vol-17 NOVEL — Cross-graft recombination of two ALNS-converged boards.
//
// Take board A and board B (both ALNS-converged, score ~455).
// Take rows [y_lo, y_hi] from board B, the rest from board A.
// Fix piece-uniqueness violations by swapping duplicated pieces with
// missing pieces (in any free cell). Repair via ALNS.
//
// This is a "block-crossover" — borrowing structure from GA. Different
// ALNS runs converge to DIFFERENT local optima despite same CP partial.
// Recombining their bottom rows might unlock a basin neither board
// reached individually.
//
// CLI:
//   cross_graft --board-a A.json --board-b B.json
//               --y-lo 12 --y-hi 15
//               --alns-ms 120000 --seed 1

#![forbid(unsafe_code)]

use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, PieceId, Rotation};
use eternity2_localsearch::{
    piece_swap_hillclimb, polish_rotations, run_alns, Acceptance, AlnsConfig,
    BottomBandDestroy, ComponentDestroy, ConflictDriven, DestroyOp, HingeDestroy,
    MwpmDefectPair, RandomRegion, RepairKind, WorstBand, WorstWindow,
};

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

fn main() {
    let mut board_a = PathBuf::new();
    let mut board_b = PathBuf::new();
    let mut y_lo: u32 = 12;
    let mut y_hi: u32 = 15;
    let mut alns_ms: u64 = 120_000;
    let mut seed: u64 = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board-a" => board_a = PathBuf::from(args.next().unwrap()),
            "--board-b" => board_b = PathBuf::from(args.next().unwrap()),
            "--y-lo" => y_lo = args.next().unwrap().parse().unwrap(),
            "--y-hi" => y_hi = args.next().unwrap().parse().unwrap(),
            "--alns-ms" => alns_ms = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_a.as_os_str().is_empty() || board_b.as_os_str().is_empty() {
        eprintln!("--board-a and --board-b required");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let a = load_board(&board_a);
    let b = load_board(&board_b);
    let (ma, _) = score_board(&puzzle, &a);
    let (mb, _) = score_board(&puzzle, &b);
    eprintln!("board A: {ma}/480 — {}", board_a.display());
    eprintln!("board B: {mb}/480 — {}", board_b.display());
    eprintln!("crossover region: rows {y_lo}..={y_hi}");

    let w = puzzle.width;
    let h = puzzle.height;
    assert!(y_hi < h);
    assert!(y_lo <= y_hi);

    // Build chimera: rows in [y_lo, y_hi] from B, rest from A.
    let mut chimera = Board::empty(&puzzle);
    let mut a_pieces: HashSet<PieceId> = HashSet::new();
    let mut b_pieces_in_region: HashSet<PieceId> = HashSet::new();
    for pos in 0..puzzle.cell_count() {
        let y = pos / w;
        if y >= y_lo && y <= y_hi {
            if let Some((pid, rot)) = b.get(pos) {
                chimera.place(pos, pid, rot);
                b_pieces_in_region.insert(pid);
            }
        } else {
            if let Some((pid, rot)) = a.get(pos) {
                chimera.place(pos, pid, rot);
                a_pieces.insert(pid);
            }
        }
    }
    eprintln!("chimera before fix: a pieces (outside region): {}, b pieces (inside region): {}",
        a_pieces.len(), b_pieces_in_region.len());

    // Find duplicates: pieces that are in BOTH a_pieces and b_pieces_in_region.
    let dup: Vec<PieceId> = a_pieces.intersection(&b_pieces_in_region).copied().collect();
    eprintln!("duplicate pieces: {}", dup.len());
    // Find missing: pieces that are in NEITHER set (= not in chimera).
    let all_pids: HashSet<PieceId> = puzzle.pieces().iter().map(|p| p.id).collect();
    let chimera_pids: HashSet<PieceId> = a_pieces.union(&b_pieces_in_region).copied().collect();
    let missing: Vec<PieceId> = all_pids.difference(&chimera_pids).copied().collect();
    eprintln!("missing pieces: {}", missing.len());
    assert_eq!(dup.len(), missing.len(), "chimera build invariant violated");

    // Fix duplicates: for each duplicate piece, REMOVE its instance in the
    // out-of-region (a) side and replace with a missing piece (any rotation
    // — ALNS will fix rotations).
    // Strategy: iterate cells outside region. If the cell's piece is a
    // duplicate, replace with a missing piece. Use cell_admits to pick
    // a valid (piece, rotation) for the cell.
    let mut dup_set: HashSet<PieceId> = dup.iter().copied().collect();
    let mut missing_queue: Vec<PieceId> = missing.clone();
    let mut n_fixed = 0u32;
    for pos in 0..puzzle.cell_count() {
        let y = pos / w;
        if y >= y_lo && y <= y_hi { continue; }
        let Some((pid, _rot)) = chimera.get(pos) else { continue };
        if dup_set.contains(&pid) {
            // Find a missing piece+rotation that cell_admits.
            let mut placed = false;
            let mut idx_to_use = None;
            for (qidx, &qpid) in missing_queue.iter().enumerate() {
                if let Some(piece) = puzzle.piece(qpid) {
                    for rot in Rotation::ALL {
                        if eternity2_sat_encoder::cell_admits(&puzzle, pos, piece, rot) {
                            chimera.place(pos, qpid, rot);
                            placed = true;
                            idx_to_use = Some(qidx);
                            break;
                        }
                    }
                }
                if placed { break; }
            }
            if placed {
                if let Some(idx) = idx_to_use {
                    missing_queue.remove(idx);
                }
                dup_set.remove(&pid);
                n_fixed += 1;
            }
        }
    }
    eprintln!("fixed {n_fixed} duplicates (remaining unfixed: {})", missing_queue.len());

    if !missing_queue.is_empty() {
        eprintln!("WARNING: {} pieces could not be placed (cell-class mismatch). Chimera incomplete.",
            missing_queue.len());
    }

    let (m_chim, _) = score_board(&puzzle, &chimera);
    eprintln!("chimera score: {m_chim}/480 (was A={ma}, B={mb})");

    // Now run ALNS on the chimera.
    eprintln!("\nRunning ALNS on chimera ({} ms)...", alns_ms);
    let mut ops: Vec<Box<dyn DestroyOp>> = vec![
        Box::new(RandomRegion { k: 4 }),
        Box::new(WorstWindow { k: 5 }),
        Box::new(ConflictDriven { max_size: 30 }),
        Box::new(ConflictDriven { max_size: 80 }),
        Box::new(MwpmDefectPair { max_pairs: 12 }),
        Box::new(WorstBand { k_rows: 4 }),
        Box::new(BottomBandDestroy { k_rows: 3, first_row: 8 }),
        Box::new(ComponentDestroy { max_size: 100, min_size: 6 }),
        Box::new(HingeDestroy { halo: 1 }),
    ];
    let pinned_set: std::collections::BTreeSet<u32> =
        hints.hints.iter().map(|h| h.position).collect();
    let cfg = AlnsConfig {
        time_budget_ms: alns_ms,
        repair_budget_ms: 1500,
        acceptance: Acceptance::SimulatedAnnealing { t: 1.0 },
        segment_iters: 50,
        seed,
        verbose: false,
        repair: RepairKind::Sa,
        cp_fallback_to_sa: true,
        pinned_positions: hints.hints.iter().map(|h| h.position).collect(),
        iter_budget: 0,
        lex_break_isoscore: false,
        checkpoint_path: None,
        checkpoint_every_ms: 60_000,
    };
    let t0 = Instant::now();
    let (alns_board, stats) = run_alns(&puzzle, &chimera, ops.as_mut_slice(), &cfg);
    let elapsed = t0.elapsed();
    let (alns_board, rg) = polish_rotations(&puzzle, &alns_board, &pinned_set);
    let (alns_board, sg) = piece_swap_hillclimb(&puzzle, &alns_board, &pinned_set);

    let (m_final, _) = score_board(&puzzle, &alns_board);
    let p_final = placed_count(&alns_board, &puzzle);
    let url = bucas_url(&puzzle, &alns_board, "v17_cross_graft");
    eprintln!(
        "\nResult: matched={m_final}/480 placed={p_final}/256 elapsed={:.1}s iters={} polish: rot=+{rg} swap=+{sg}",
        elapsed.as_secs_f64(), stats.iters
    );
    eprintln!("vs A={ma}, B={mb}, chimera_pre_alns={m_chim} — Δ from best parent = {:+}",
        m_final as i32 - (ma.max(mb)) as i32);
    eprintln!("bucas: {url}");

    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from("output/v17_cross_graft");
    let _ = std::fs::create_dir_all(&out_dir);
    let json = serde_json::json!({
        "board_a_score": ma, "board_b_score": mb,
        "chimera_pre_alns": m_chim, "matched_final": m_final,
        "y_lo": y_lo, "y_hi": y_hi, "alns_ms": alns_ms,
        "n_fixed_duplicates": n_fixed, "unfixed_missing": missing_queue.len(),
        "bucas_url": url,
        "placement": (0..puzzle.cell_count()).map(|p| {
            alns_board.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    let _ = std::fs::write(out_dir.join(format!("cross_graft_{run_id}.json")),
        serde_json::to_string_pretty(&json).unwrap());
    eprintln!("saved: output/v17_cross_graft/cross_graft_{run_id}.json");

    let _ = HashMap::<u32, u32>::new(); // suppress unused-import warning
}
