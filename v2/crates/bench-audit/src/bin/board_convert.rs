// board_convert — convert any board JSON to the canonical format (JSON or CSV).
// Vol-118 T14: canonical format converter using eternity2_export::save_board.
//
// Usage:
//   board_convert <input.json> [--out <output.json>] [--csv]
//   board_convert <input.json> --inplace          # rewrite in place
//   board_convert --batch <pattern>                # batch-convert (preserves filename)
//
// Examples:
//   board_convert mcgavin.json --out mcgavin_canonical.json
//   board_convert old_dump.json --csv --out old.csv
//   board_convert mcgavin.json --inplace            # rewrites mcgavin.json

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_export::{load_board, save_board, save_board_csv, BoardMetadata};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: board_convert <input.json> [--out <path>] [--csv] [--inplace]");
        eprintln!("       board_convert --batch <input.json> [<input.json> ...]");
        std::process::exit(2);
    }

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    let mut input: Option<PathBuf> = None;
    let mut output: Option<PathBuf> = None;
    let mut csv_mode = false;
    let mut inplace = false;
    let mut batch_paths: Vec<PathBuf> = Vec::new();

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--out" => { output = Some(PathBuf::from(&args[i + 1])); i += 2; }
            "--csv" => { csv_mode = true; i += 1; }
            "--inplace" => { inplace = true; i += 1; }
            "--batch" => {
                i += 1;
                while i < args.len() {
                    batch_paths.push(PathBuf::from(&args[i]));
                    i += 1;
                }
            }
            other => {
                if input.is_none() && !other.starts_with("--") {
                    input = Some(PathBuf::from(other));
                    i += 1;
                } else {
                    eprintln!("unknown arg: {}", other);
                    std::process::exit(1);
                }
            }
        }
    }

    let meta = BoardMetadata {
        source: Some("board_convert".to_string()),
        note: Some("vol-118 T14 canonical-format conversion".to_string()),
        ..Default::default()
    };

    let do_convert = |path: &PathBuf, out_path: &PathBuf, csv: bool| -> Result<(), String> {
        let board = load_board(path, &puzzle).map_err(|e| format!("load: {e}"))?;
        if csv {
            save_board_csv(out_path, &puzzle, &board).map_err(|e| format!("save csv: {e}"))?;
        } else {
            save_board(out_path, &puzzle, &board, &meta).map_err(|e| format!("save json: {e}"))?;
        }
        Ok(())
    };

    if !batch_paths.is_empty() {
        let mut ok = 0;
        let mut errors = 0;
        for p in &batch_paths {
            let out = if csv_mode { p.with_extension("csv") } else { p.clone() };
            match do_convert(p, &out, csv_mode) {
                Ok(()) => { ok += 1; println!("OK  {} -> {}", p.display(), out.display()); }
                Err(e) => { errors += 1; eprintln!("ERR {}: {}", p.display(), e); }
            }
        }
        println!("\nBatch: {} ok, {} errors", ok, errors);
        std::process::exit(if errors == 0 { 0 } else { 1 });
    }

    let inp = input.expect("input path required");
    let out = if inplace {
        inp.clone()
    } else if let Some(o) = output {
        o
    } else {
        // Default: same dir, suffix _canonical.{json|csv}
        let stem = inp.file_stem().expect("filename stem").to_string_lossy().into_owned();
        let ext = if csv_mode { "csv" } else { "json" };
        inp.with_file_name(format!("{}_canonical.{}", stem, ext))
    };

    match do_convert(&inp, &out, csv_mode) {
        Ok(()) => {
            println!("Converted: {} -> {}", inp.display(), out.display());
            // Print a one-line summary (reload from the SOURCE since the
            // canonical CSV reader is load_board_csv, not load_board).
            let board = load_board(&inp, &puzzle).expect("reload source for summary");
            let (matched, total) = eternity2_export::score_board(&puzzle, &board);
            let placed = eternity2_export::placed_count(&board, &puzzle);
            println!("  placed={}/{}  matched={}/{}", placed, puzzle.cell_count(), matched, total);
        }
        Err(e) => {
            eprintln!("ERROR: {}", e);
            std::process::exit(1);
        }
    }
}
