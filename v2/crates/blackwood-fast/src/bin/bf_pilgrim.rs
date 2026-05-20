// V195 PILGRIM — long-run hybrid DFS.
//
// Architecture:
//   - 5 canonical hints pinned.
//   - Row-major DFS with hard edge match.
//   - Periodic restarts (when no max-depth progress in K nodes OR
//     scheduled budget).
//   - Each restart: shuffle entries with new seed (different value-order).
//   - Track all-time best max_depth and best board.
//   - Periodic checkpoint to disk (every N restarts or M minutes).
//
// Usage:
//   bf_pilgrim --budget-ms 43200000 \
//              --restart-after-nodes 100000000 \
//              --checkpoint-every-restart 50 \
//              --out output/vol-195/best.json

use eternity2_blackwood_fast::{
    score_board, solve_raw_with_initial_board, PieceRot, RowMajorIndex,
};
use eternity2_puzzle_io::load_puzzle_with_hints;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Instant;

const WH: usize = 256;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut puzzle_path = PathBuf::from(
        "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv",
    );
    let mut budget_ms: u64 = 60_000;
    let mut restart_after_nodes: u64 = 50_000_000;
    let mut restart_after_ms_per_run: u64 = 30_000;
    let mut out_path: Option<PathBuf> = None;
    let mut log_path: Option<PathBuf> = None;
    let mut threads: usize = 1;
    let mut seed_start: u64 = 0;
    let mut starting_partial: Option<PathBuf> = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&args[i + 1]); i += 2; }
            "--budget-ms" => { budget_ms = args[i + 1].parse().expect("budget"); i += 2; }
            "--restart-after-nodes" => { restart_after_nodes = args[i + 1].parse().expect("nodes"); i += 2; }
            "--restart-after-ms" => { restart_after_ms_per_run = args[i + 1].parse().expect("ms"); i += 2; }
            "--out" => { out_path = Some(PathBuf::from(&args[i + 1])); i += 2; }
            "--log" => { log_path = Some(PathBuf::from(&args[i + 1])); i += 2; }
            "--threads" => { threads = args[i + 1].parse().expect("threads"); i += 2; }
            "--seed-start" => { seed_start = args[i + 1].parse().expect("seed"); i += 2; }
            "--starting-partial" => { starting_partial = Some(PathBuf::from(&args[i + 1])); i += 2; }
            _ => { eprintln!("unknown arg: {}", args[i]); std::process::exit(1); }
        }
    }

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    assert_eq!(puzzle.width as usize, 16);
    assert_eq!(puzzle.height as usize, 16);

    let base_index = RowMajorIndex::build(&puzzle);
    let n_pieces = base_index.n_pieces;
    assert_eq!(n_pieces, 256);

    // Map PieceId -> piece_idx
    let mut pid_to_idx: std::collections::HashMap<u16, u16> = std::collections::HashMap::new();
    for (idx, &pid) in base_index.piece_ids.iter().enumerate() {
        pid_to_idx.insert(pid, idx as u16);
    }

    // Build initial board + pinning mask:
    //   - Start from 5 canonical hints.
    //   - Optionally pre-load a starting partial (everything in it is pinned).
    let mut initial_board: [PieceRot; WH] = [PieceRot::NONE; WH];
    let mut is_pinned: [bool; WH] = [false; WH];
    let mut pieces_used: [u64; 4] = [0; 4];

    for h in &hints.hints {
        let pi = pid_to_idx[&h.piece_id];
        initial_board[h.position as usize] = PieceRot::new(pi, h.rotation.as_u8());
        is_pinned[h.position as usize] = true;
        pieces_used[(pi as usize) >> 6] |= 1u64 << (pi & 63);
    }
    let n_hint_pins = hints.hints.len();
    let mut starting_label = format!("5/5 hints only ({} cells pinned)", n_hint_pins);

    // V195-T3: save every restart's deepest state if it crosses a threshold.
    // For 12h-blank-canvas mode, we want to harvest variance not just global best.
    let save_threshold: u32 = std::env::var("PILGRIM_SAVE_THRESHOLD")
        .ok().and_then(|s| s.parse().ok()).unwrap_or(200);
    let save_corpus_dir: Option<PathBuf> = std::env::var("PILGRIM_CORPUS_DIR")
        .ok().map(PathBuf::from);
    if let Some(d) = &save_corpus_dir {
        std::fs::create_dir_all(d).ok();
        eprintln!("[pilgrim] saving restart corpus to {} (threshold depth >= {})",
                  d.display(), save_threshold);
    }

    if let Some(sp) = &starting_partial {
        // Load JSON and pin all its placements.
        let raw = std::fs::read_to_string(sp).expect("read starting partial");
        let json: serde_json::Value = serde_json::from_str(&raw).expect("parse");
        let placement = json.get("placement").and_then(|v| v.as_array()).expect("placement array");
        let mut n_loaded = 0;
        for ent in placement {
            let pos = ent.get("pos").and_then(|v| v.as_u64()).expect("pos") as usize;
            let pid = ent.get("piece_id").and_then(|v| v.as_u64()).expect("piece_id") as u16;
            let rot = ent.get("rotation").and_then(|v| v.as_u64()).unwrap_or(0) as u8;
            if let Some(&pi) = pid_to_idx.get(&pid) {
                if !is_pinned[pos] {
                    initial_board[pos] = PieceRot::new(pi, rot);
                    is_pinned[pos] = true;
                    pieces_used[(pi as usize) >> 6] |= 1u64 << (pi & 63);
                    n_loaded += 1;
                }
            }
        }
        starting_label = format!("starting partial ({} extra cells pinned + {} hints)",
                                  n_loaded, n_hint_pins);
    }

    let n_initial_placed: usize = initial_board.iter().filter(|p| p.0 != PieceRot::NONE.0).count();
    eprintln!("[pilgrim] start: {}", starting_label);
    eprintln!("[pilgrim] initial_placed={} threads={} budget_ms={}",
              n_initial_placed, threads, budget_ms);

    let deadline = Instant::now() + std::time::Duration::from_millis(budget_ms);
    let best_depth = Arc::new(AtomicU32::new(n_initial_placed as u32));
    let total_restarts = Arc::new(AtomicU64::new(0));
    let total_nodes = Arc::new(AtomicU64::new(0));
    let best_board: Arc<std::sync::Mutex<Vec<(eternity2_core::PieceId, eternity2_core::Rotation)>>> =
        Arc::new(std::sync::Mutex::new(Vec::new()));

    let log_out: Arc<std::sync::Mutex<Option<std::io::BufWriter<std::fs::File>>>> = Arc::new(
        std::sync::Mutex::new(log_path.as_ref().map(|p| {
            std::io::BufWriter::new(std::fs::File::create(p).expect("create log"))
        })),
    );

    let thread_handles: Vec<_> = (0..threads).map(|tid| {
        let base_index = base_index.clone();
        let initial_board = initial_board;
        let is_pinned = is_pinned;
        let pieces_used = pieces_used;
        let best_depth = Arc::clone(&best_depth);
        let total_restarts = Arc::clone(&total_restarts);
        let total_nodes = Arc::clone(&total_nodes);
        let best_board = Arc::clone(&best_board);
        let log_out = Arc::clone(&log_out);
        let puzzle = puzzle.clone();
        let out_path_clone = out_path.clone();
        let save_corpus_dir_clone = save_corpus_dir.clone();
        std::thread::spawn(move || {
            let thread_seed_base = seed_start + (tid as u64) * 1_000_000;
            let mut local_seed = thread_seed_base;
            loop {
                let now = Instant::now();
                if now >= deadline { break; }
                let remaining_ms = (deadline - now).as_millis() as u64;
                let this_run_ms = remaining_ms.min(restart_after_ms_per_run);
                let this_run_us = this_run_ms * 1000;

                let mut index = base_index.clone();
                if local_seed > 0 {
                    index.permute_entries_seeded(local_seed);
                }

                let (stats, board) = solve_raw_with_initial_board(
                    &index,
                    initial_board,
                    is_pinned,
                    pieces_used,
                    this_run_us,
                );

                let restart_idx = total_restarts.fetch_add(1, Ordering::Relaxed);
                total_nodes.fetch_add(stats.nodes, Ordering::Relaxed);

                // V195-T3: save this restart's deepest board to corpus dir if it crossed threshold.
                if stats.max_depth >= save_threshold {
                    if let Some(corpus_dir) = &save_corpus_dir_clone {
                        let score = score_board(&puzzle, &board);
                        let mut placements: Vec<serde_json::Value> = Vec::new();
                        for (pos, &(pid, rot)) in board.iter().enumerate() {
                            if pid == u16::MAX { continue; }
                            placements.push(serde_json::json!({
                                "pos": pos as u32,
                                "piece_id": pid,
                                "rotation": rot.as_u8(),
                            }));
                        }
                        let outj = serde_json::json!({
                            "placement": placements,
                            "source": "bf_pilgrim_restart",
                            "max_depth": stats.max_depth,
                            "score": score,
                            "matched": score,
                            "placed": placements.len(),
                            "seed": local_seed,
                            "thread": tid,
                            "restart": restart_idx,
                        });
                        let fname = corpus_dir.join(format!("r{:06}_tid{}_seed{}_d{}.json",
                                                              restart_idx, tid, local_seed, stats.max_depth));
                        let _ = std::fs::write(&fname, serde_json::to_string(&outj).unwrap());
                    }
                }

                let prev_best = best_depth.load(Ordering::Relaxed);
                if stats.max_depth > prev_best {
                    if best_depth.compare_exchange(prev_best, stats.max_depth,
                                                    Ordering::Relaxed, Ordering::Relaxed).is_ok() {
                        // We won the race; save the board.
                        let score = score_board(&puzzle, &board);
                        eprintln!("[pilgrim] tid={} seed={} NEW BEST depth={} score={}/{} nodes={} restart#{}",
                                  tid, local_seed, stats.max_depth, score, 480,
                                  stats.nodes, total_restarts.load(Ordering::Relaxed));
                        {
                            let mut lock = log_out.lock().unwrap();
                            if let Some(f) = lock.as_mut() {
                                use std::io::Write;
                                let elapsed_s = (Instant::now() - (deadline - std::time::Duration::from_millis(budget_ms))).as_secs();
                                let _ = writeln!(f, "t+{}s tid={} seed={} depth={} score={}/480 nodes={} restart={}",
                                                   elapsed_s,
                                                   tid, local_seed, stats.max_depth, score, stats.nodes,
                                                   total_restarts.load(Ordering::Relaxed));
                                let _ = f.flush();
                            }
                        }
                        {
                            let mut bb = best_board.lock().unwrap();
                            *bb = board.clone();
                        }
                        // Write to disk too.
                        if let Some(out) = &out_path_clone {
                            let mut placements: Vec<serde_json::Value> = Vec::new();
                            for (pos, &(pid, rot)) in board.iter().enumerate() {
                                if pid == u16::MAX { continue; }
                                placements.push(serde_json::json!({
                                    "pos": pos as u32,
                                    "piece_id": pid,
                                    "rotation": rot.as_u8(),
                                }));
                            }
                            let outj = serde_json::json!({
                                "placement": placements,
                                "source": "bf_pilgrim",
                                "max_depth": stats.max_depth,
                                "score": score,
                                "matched": score,
                                "placed": placements.len(),
                                "seed": local_seed,
                                "thread": tid,
                                "restart": total_restarts.load(Ordering::Relaxed),
                            });
                            std::fs::create_dir_all(out.parent().unwrap_or(std::path::Path::new("."))).ok();
                            let _ = std::fs::write(out, serde_json::to_string(&outj).unwrap());
                        }
                    }
                }

                local_seed += 1;
            }
        })
    }).collect();

    for h in thread_handles {
        let _ = h.join();
    }

    let final_best = best_depth.load(Ordering::Relaxed);
    let final_restarts = total_restarts.load(Ordering::Relaxed);
    let final_nodes = total_nodes.load(Ordering::Relaxed);
    eprintln!("[pilgrim] done: best_depth={} restarts={} total_nodes={}",
              final_best, final_restarts, final_nodes);
    println!(
        "{{\"profile\":\"bf_pilgrim\",\"budget_ms\":{},\"best_depth\":{},\"restarts\":{},\"total_nodes\":{}}}",
        budget_ms, final_best, final_restarts, final_nodes
    );
}
