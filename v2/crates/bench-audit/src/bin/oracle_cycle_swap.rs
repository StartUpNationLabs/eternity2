// Vol-18 — OracleCycleSwap proof-of-concept.
//
// Load current board + oracle board, compute σ-cycles, apply them one
// at a time and report the score trajectory. Validates the Python R5e
// finding in Rust and gives us a baseline for integrating into ALNS.
//
// CLI:
//   oracle_cycle_swap --current <path> --oracle <path>

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_bench_audit::{placed_count, score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::bucas_url;
use eternity2_core::{Board, Rotation};
use eternity2_localsearch::oracle_swap::{apply_all_cycles, apply_cycle, apply_rotation_fixups, compute_sigma_cycles, rotation_fixups};

// Vol-118 T9: migrated to canonical eternity2_export::load_board.
fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> eternity2_core::Board {
    eternity2_export::load_board(path, puzzle).expect("load_board")
}

fn main() {
    let mut current_path = PathBuf::new();
    let mut oracle_path = PathBuf::new();
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--current" => current_path = PathBuf::from(args.next().unwrap()),
            "--oracle" => oracle_path = PathBuf::from(args.next().unwrap()),
            other => panic!("unknown arg {other}"),
        }
    }
    if current_path.as_os_str().is_empty() || oracle_path.as_os_str().is_empty() {
        eprintln!("usage: oracle_cycle_swap --current <path> --oracle <path>");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let current = load_board(&current_path, &puzzle);
    let oracle = load_board(&oracle_path, &puzzle);
    let cell_count = puzzle.cell_count() as usize;

    let (cm, _) = score_board(&puzzle, &current);
    let (om, _) = score_board(&puzzle, &oracle);
    eprintln!(
        "current: {}/480 ({} placed)  oracle: {}/480 ({} placed)",
        cm, placed_count(&current, &puzzle), om, placed_count(&oracle, &puzzle)
    );

    let cycles = compute_sigma_cycles(&current, &oracle, cell_count);
    eprintln!("# σ-cycles (length >= 2): {}", cycles.len());
    for (i, c) in cycles.iter().enumerate() {
        let board_after = apply_cycle(&current, c);
        let (m, _) = score_board(&puzzle, &board_after);
        let delta = m as i32 - cm as i32;
        let rows: std::collections::BTreeSet<u32> = c.positions.iter().map(|&p| p / puzzle.width).collect();
        let rows_str = rows.iter().map(|r| r.to_string()).collect::<Vec<_>>().join(",");
        eprintln!(
            "  cycle {:>2} (len {:>3}, rows {}): Δ = {:+}",
            i, c.positions.len(), rows_str, delta
        );
    }

    let board_all = apply_all_cycles(&current, &cycles);
    let (mall, _) = score_board(&puzzle, &board_all);
    eprintln!();
    eprintln!("apply ALL cycles: {}/480  (delta = {:+}, oracle = {})", mall, mall as i32 - cm as i32, om);

    let fixups = rotation_fixups(&current, &oracle, cell_count);
    eprintln!("# rotation fixups (same piece, wrong rot): {}", fixups.len());
    let board_full = apply_rotation_fixups(&board_all, &fixups);
    let (mfull, _) = score_board(&puzzle, &board_full);
    eprintln!("apply cycles + rotation fixups: {}/480  (delta = {:+}, oracle = {})", mfull, mfull as i32 - cm as i32, om);
    let board_all = board_full; // shadow so saved JSON has the full result

    let bucas = bucas_url(&puzzle, &board_all, "oracle_cycle_swap_result");
    eprintln!("bucas: {bucas}");

    let json = serde_json::json!({
        "matched": mall,
        "placed": placed_count(&board_all, &puzzle),
        "oracle_score": om,
        "current_score": cm,
        "n_cycles": cycles.len(),
        "bucas_url": bucas,
        "placement": (0..puzzle.cell_count()).map(|p| {
            board_all.get(p).map(|(pid, rot)| serde_json::json!({
                "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
            }))
        }).collect::<Vec<_>>(),
    });
    let out_dir = PathBuf::from("output/v18_oracle");
    let _ = std::fs::create_dir_all(&out_dir);
    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let p = out_dir.join(format!("ocs_{}.json", run_id));
    let _ = std::fs::write(&p, serde_json::to_string_pretty(&json).unwrap());
    eprintln!("saved: {}", p.display());
}
