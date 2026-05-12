// Vol-17 idea A — Blackwood schedule calibration from community boards.
//
// Recipe (from project_e2_vol15_blackwood_results.md):
//   1. Load each high-score community board on canonical Eternity2.
//   2. Re-order the 256 placements into bottom-up row-major scan
//      (idx = (H-1-y)*W + x), matching ScanOrder::RowMajorBottomUp.
//   3. For each prefix length k in 0..=256, compute the cumulative
//      count of "heuristic-color" edges (per compute_heuristic_sides)
//      that appear on the k placed pieces.
//      Each piece contributes 1 per heuristic-colored edge slot
//      (Blackwood's heuristic_pool_size = total occurrence count of
//      heuristic colors across all piece edges).
//   4. Fit a piecewise-linear schedule whose target_at(k) is the
//      median (or 25th-percentile, conservative) cumulative count
//      across loaded boards.
//   5. Emit the schedule as JSON + Rust source so it can be wired
//      into solver-engine.
//
// On canonical Eternity2 the corpus only has 1 board at score 469 +
// 1 saturator at 480, so "median across boards" reduces to the curve
// from those two boards. With N=2 the fitted curve is still strictly
// better than vol-15's `blackwood_schedule_469`, which used Blackwood's
// OWN puzzle's curve scaled by a flat factor.
//
// CLI:
//   calibrate_blackwood --puzzle PATH --corpus DIR \
//                       [--min-score 469] [--out PATH]
//
// Output: JSON to --out, with fields:
//   { heuristic_sides: [u8;3],
//     heuristic_pool_size: u32,
//     boards: [{file, score, cumulative_counts: [u32; 257]}],
//     median_curve: [(depth, count); ~10],
//     p25_curve:    [(depth, count); ~10],
//     mean_curve:   [(depth, count); ~10],
//     rust_snippet: "fn blackwood_schedule_calibrated(...) -> ..."
//   }
//
// Notes:
// - Heuristic-color edges are counted on the PIECE, not on actual
//   placed adjacency — matches Blackwood's algorithm (his schedule
//   counts heuristic colors that have been COMMITTED to the board).
// - The break_indexes_allowed list is NOT calibrated here. Vol-15's
//   bw_breaks were proportional to Blackwood's reported recipe; we
//   keep the same proportional break schedule for now. A separate
//   calibration step could mine mismatches from the 469 board's
//   placements to derive empirical break depths.

#![forbid(unsafe_code)]

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Hints, Puzzle, Rotation};
use eternity2_solver_engine::{
    compute_heuristic_sides, count_color_occurrences,
};

fn die(msg: &str) -> ! {
    eprintln!("ERROR: {msg}");
    std::process::exit(1);
}

struct Args {
    puzzle: PathBuf,
    corpus: PathBuf,
    min_score: u32,
    out: PathBuf,
    verbose: bool,
}

fn parse_args() -> Args {
    let mut puzzle = PathBuf::from("../../data/puzzles/size_16_official_eternity.csv");
    let mut corpus = PathBuf::from("output/community_corpus");
    let mut min_score = 469u32;
    let mut out = PathBuf::from("output/v17_calibration.json");
    let mut verbose = false;
    let argv: Vec<String> = std::env::args().collect();
    let mut i = 1;
    while i < argv.len() {
        match argv[i].as_str() {
            "--puzzle" => { puzzle = PathBuf::from(&argv[i + 1]); i += 2; }
            "--corpus" => { corpus = PathBuf::from(&argv[i + 1]); i += 2; }
            "--min-score" => { min_score = argv[i + 1].parse().expect("u32"); i += 2; }
            "--out" => { out = PathBuf::from(&argv[i + 1]); i += 2; }
            "-v" | "--verbose" => { verbose = true; i += 1; }
            "-h" | "--help" => {
                println!("usage: calibrate_blackwood [--puzzle PATH] [--corpus DIR] [--min-score N] [--out PATH] [-v]");
                std::process::exit(0);
            }
            other => die(&format!("unknown arg: {other}")),
        }
    }
    Args { puzzle, corpus, min_score, out, verbose }
}

#[derive(Debug, Clone)]
struct CorpusEntry {
    file: String,
    score: u32,
    placed_pieces: Box<[Option<(u16, Rotation)>; 256]>,
    // Cumulative heuristic-color piece-edge count, one entry per
    // prefix length 0..=256.
    cumulative: Vec<u32>,
}

fn decode_board_from_bucas(puzzle: &Puzzle, url: &str) -> Option<Board> {
    let mut b = Board::empty(puzzle);
    let idx = url.find("board_edges=")?;
    let blob = &url[idx + "board_edges=".len()..];
    let blob = blob.split('&').next()?;
    let bytes = blob.as_bytes();
    let n_cells = puzzle.cell_count() as usize;
    if bytes.len() < n_cells * 4 { return None; }
    for pos in 0..n_cells {
        let q: [u8; 4] = std::array::from_fn(|i| bytes[pos * 4 + i] - b'a');
        if q.iter().all(|&c| c == 0) { continue; }
        let mut found = false;
        for piece in puzzle.pieces() {
            for rot in Rotation::ALL {
                if piece.edges.rotated(rot).as_array() == q {
                    b.place(pos as u32, piece.id, rot);
                    found = true;
                    break;
                }
            }
            if found { break; }
        }
    }
    Some(b)
}

fn extract_score_from_json(text: &str) -> Option<u32> {
    // Cheap inline parse: look for "interior_matched": <N>
    let key = "\"interior_matched\":";
    let idx = text.find(key)?;
    let tail = &text[idx + key.len()..];
    let tail = tail.trim_start();
    let end = tail.find(|c: char| !c.is_ascii_digit()).unwrap_or(tail.len());
    tail[..end].parse().ok()
}

fn extract_url_from_json(text: &str) -> Option<String> {
    let key = "\"url\":";
    let idx = text.find(key)?;
    let tail = &text[idx + key.len()..];
    let tail = tail.trim_start();
    if !tail.starts_with('"') { return None; }
    let body = &tail[1..];
    let end = body.find('"')?;
    Some(body[..end].to_string())
}

fn extract_puzzle_name(text: &str) -> Option<String> {
    let key = "\"puzzle\":";
    let idx = text.find(key)?;
    let tail = &text[idx + key.len()..];
    let tail = tail.trim_start();
    if !tail.starts_with('"') { return None; }
    let body = &tail[1..];
    let end = body.find('"')?;
    Some(body[..end].to_string())
}

fn load_corpus(puzzle: &Puzzle, corpus_dir: &Path, min_score: u32) -> Vec<CorpusEntry> {
    let mut out = Vec::new();
    let read = match fs::read_dir(corpus_dir) {
        Ok(r) => r,
        Err(e) => die(&format!("can't read corpus dir {corpus_dir:?}: {e}")),
    };
    let mut skipped_wrong_puzzle = 0u32;
    let mut skipped_low_score = 0u32;
    let mut skipped_decode = 0u32;
    for entry in read.flatten() {
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) != Some("json") { continue; }
        let text = match fs::read_to_string(&path) {
            Ok(s) => s,
            Err(_) => continue,
        };
        // Filter on canonical Eternity2 only (others have different
        // piece sets — schedule wouldn't transfer).
        if extract_puzzle_name(&text).as_deref() != Some("Eternity2") {
            skipped_wrong_puzzle += 1;
            continue;
        }
        let Some(score) = extract_score_from_json(&text) else { continue; };
        if score < min_score { skipped_low_score += 1; continue; }
        let Some(url) = extract_url_from_json(&text) else { continue; };
        let Some(board) = decode_board_from_bucas(puzzle, &url) else { continue; };
        // Build placed_pieces array.
        let mut placed: Box<[Option<(u16, Rotation)>; 256]> = Box::new([None; 256]);
        let mut decoded = 0u32;
        for pos in 0..puzzle.cell_count() {
            if let Some((pid, rot)) = board.get(pos) {
                placed[pos as usize] = Some((u16::from(pid), rot));
                decoded += 1;
            }
        }
        if decoded != puzzle.cell_count() {
            eprintln!("WARNING: {:?} decoded {decoded}/{} cells — skipping",
                path.file_name().unwrap(), puzzle.cell_count());
            skipped_decode += 1;
            continue;
        }
        out.push(CorpusEntry {
            file: path.file_name().and_then(|s| s.to_str()).unwrap_or("?").to_string(),
            score,
            placed_pieces: placed,
            cumulative: Vec::new(),
        });
    }
    eprintln!(
        "corpus scan: kept {}, skipped (wrong_puzzle={}, low_score={}, decode={})",
        out.len(), skipped_wrong_puzzle, skipped_low_score, skipped_decode
    );
    out
}

/// For one board, compute cumulative count of heuristic-color piece-
/// edges placed in bottom-up row-major scan order. Each piece
/// contributes the number of its 4 edges whose color ∈ heuristic_sides.
/// Border edges (color 0) never contribute.
fn cumulative_heuristic_count(
    puzzle: &Puzzle,
    placed: &[Option<(u16, Rotation)>; 256],
    heuristic_sides: &[u8],
) -> Vec<u32> {
    let hset: HashSet<u8> = heuristic_sides.iter().copied().collect();
    let w = puzzle.width as usize;
    let h = puzzle.height as usize;
    let n = w * h;
    let mut cum = Vec::with_capacity(n + 1);
    cum.push(0u32);
    let mut running = 0u32;
    // Bottom-up row-major: y goes from (H-1) down to 0. The scan
    // order index is (H-1-y)*W + x.
    for k in 0..n {
        let x = k % w;
        let y_from_bottom = k / w;
        let y = h - 1 - y_from_bottom;
        let pos = y * w + x;
        if let Some((pid, rot)) = placed[pos] {
            if let Some(piece) = puzzle.piece(pid) {
                let e = piece.edges.rotated(rot).as_array();
                for &c in &e {
                    if c != 0 && hset.contains(&c) { running += 1; }
                }
            }
        }
        cum.push(running);
    }
    cum
}

fn quantile(values: &mut [u32], q: f64) -> u32 {
    if values.is_empty() { return 0; }
    values.sort_unstable();
    let idx = ((values.len() as f64 - 1.0) * q).round() as usize;
    values[idx.min(values.len() - 1)]
}

fn fit_curve(
    entries: &[CorpusEntry],
    quantile_q: f64,
    control_depths: &[u32],
    n_pos: u32,
) -> Vec<(u32, u32)> {
    if entries.is_empty() { return vec![(0, 0)]; }
    let mut out = Vec::with_capacity(control_depths.len() + 1);
    out.push((0u32, 0u32));
    let mut prev_count = 0u32;
    for &d in control_depths {
        let d_clamped = d.min(n_pos);
        let mut col: Vec<u32> = entries.iter()
            .map(|e| e.cumulative[d_clamped as usize])
            .collect();
        let mut c = quantile(&mut col, quantile_q);
        // Enforce strict-monotonic non-decreasing across control
        // points so BlackwoodSchedule::validate() passes.
        if c < prev_count { c = prev_count; }
        out.push((d_clamped, c));
        prev_count = c;
    }
    // De-duplicate equal-depth points (validate requires strict
    // increase in depth).
    let mut deduped = Vec::with_capacity(out.len());
    let mut last_d: Option<u32> = None;
    for (d, c) in out {
        if Some(d) == last_d { continue; }
        deduped.push((d, c));
        last_d = Some(d);
    }
    deduped
}

fn main() {
    let args = parse_args();
    eprintln!("=== vol-17 Blackwood schedule calibration ===");
    eprintln!("puzzle={:?} corpus={:?} min_score={} out={:?}",
        args.puzzle, args.corpus, args.min_score, args.out);

    let (puzzle, hints): (Puzzle, Hints) = match load_puzzle_with_hints(&args.puzzle) {
        Ok(x) => x,
        Err(e) => die(&format!("loading puzzle: {e}")),
    };
    let n_pos = puzzle.cell_count();
    eprintln!("loaded puzzle {}×{}, {} pieces, hints={}",
        puzzle.width, puzzle.height, puzzle.pieces().len(), hints.hints.len());

    let heuristic_sides = compute_heuristic_sides(&puzzle, &hints);
    let pool_size = count_color_occurrences(&puzzle, &heuristic_sides);
    eprintln!("heuristic_sides = {:?}, pool_size = {}", heuristic_sides, pool_size);

    let mut entries = load_corpus(&puzzle, &args.corpus, args.min_score);
    eprintln!("loaded {} corpus entries on canonical E2 with score ≥ {}",
        entries.len(), args.min_score);
    if entries.is_empty() {
        die("no corpus entries to calibrate from");
    }

    // Compute cumulative curves per board.
    for e in &mut entries {
        e.cumulative = cumulative_heuristic_count(&puzzle, &e.placed_pieces, &heuristic_sides);
    }

    if args.verbose {
        for e in &entries {
            eprintln!("  {} score={} cum[0..16]={:?} cum[60]={} cum[80]={} cum[120]={} cum[160]={} cum[256]={}",
                e.file, e.score,
                &e.cumulative[..16],
                e.cumulative[60], e.cumulative[80],
                e.cumulative[120], e.cumulative[160], e.cumulative[256]);
        }
    }

    // Choose control depths. Vol-15's `blackwood_schedule_469`
    // affine-remap used [16, 26, 56, 76, 102, 160] in Blackwood's
    // scan-relative space. For OUR scan we want to sample the
    // curve at meaningful inflection points:
    //   - 0: schedule entry
    //   - border_ring (60): just-finished border phase
    //   - +20: enter shoulder
    //   - +40: deep interior
    //   - +60: 3/4 of board
    //   - n_pos-1: saturation
    let w = puzzle.width;
    let h = puzzle.height;
    let border_ring = 2 * w + 2 * h - 4;
    let control_depths: Vec<u32> = vec![
        border_ring,
        border_ring + 20,
        border_ring + 40,
        border_ring + 60,
        border_ring + 80,
        border_ring + 100,
        border_ring + 140,
        n_pos - 1,
    ];
    eprintln!("control depths = {:?}", control_depths);

    let median_curve = fit_curve(&entries, 0.50, &control_depths, n_pos);
    let p25_curve    = fit_curve(&entries, 0.25, &control_depths, n_pos);
    let p10_curve    = fit_curve(&entries, 0.10, &control_depths, n_pos);

    eprintln!("median curve: {:?}", median_curve);
    eprintln!("p25    curve: {:?}", p25_curve);
    eprintln!("p10    curve: {:?}", p10_curve);

    // Per-corpus mean for context (not used as schedule, but informative).
    let mut mean_curve: Vec<(u32, u32)> = Vec::new();
    mean_curve.push((0, 0));
    for &d in &control_depths {
        let mean: u32 = (entries.iter()
            .map(|e| e.cumulative[d as usize] as u64).sum::<u64>()
            / entries.len() as u64) as u32;
        mean_curve.push((d.min(n_pos), mean));
    }
    eprintln!("mean   curve: {:?}", mean_curve);

    // Print full cumulative-count tables for inspection.
    if args.verbose {
        eprintln!("\n--- cumulative_counts per board (sparse sample) ---");
        for e in &entries {
            let samples = (0..=16).map(|i| {
                let k = i * 16usize;
                (k as u32, e.cumulative[k])
            }).collect::<Vec<_>>();
            eprintln!("{} ({}): {:?}", e.file, e.score, samples);
        }
    }

    // Emit JSON.
    let json = format!(
        "{{\n\
        \"heuristic_sides\": {:?},\n\
        \"heuristic_pool_size\": {},\n\
        \"control_depths\": {:?},\n\
        \"median_curve\": {:?},\n\
        \"p25_curve\": {:?},\n\
        \"p10_curve\": {:?},\n\
        \"mean_curve\": {:?},\n\
        \"n_boards\": {},\n\
        \"boards\": [\n{}\n  ],\n\
        \"break_indexes_allowed_scaled\": {:?}\n\
        }}\n",
        heuristic_sides,
        pool_size,
        control_depths,
        median_curve,
        p25_curve,
        p10_curve,
        mean_curve,
        entries.len(),
        entries.iter().map(|e| format!(
            "    {{\"file\": \"{}\", \"score\": {}, \"cum_at_60\": {}, \"cum_at_80\": {}, \"cum_at_120\": {}, \"cum_at_160\": {}, \"cum_at_256\": {} }}",
            e.file, e.score,
            e.cumulative[60], e.cumulative[80], e.cumulative[120], e.cumulative[160], e.cumulative[256]
        )).collect::<Vec<_>>().join(",\n"),
        // Blackwood-scaled break indices, kept for reference. Real
        // calibration of breaks needs mismatch detection on community
        // boards — left for a follow-up.
        {
            let bw_breaks: [u32; 12] = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256];
            bw_breaks.iter()
                .map(|&b| ((b as u64 * n_pos as u64) / 256u64) as u32)
                .map(|b| b.min(n_pos.saturating_sub(1)))
                .collect::<Vec<u32>>()
        },
    );

    if let Some(parent) = args.out.parent() {
        let _ = fs::create_dir_all(parent);
    }
    fs::write(&args.out, json).expect("write json");
    eprintln!("\nwrote calibration to {:?}", args.out);

    // Print a Rust snippet the user can drop into solver-engine.
    println!("\n// === drop into solver-engine/src/lib.rs ===");
    println!("/// Vol-17 — calibrated Blackwood schedule, fitted at the");
    println!("/// MEDIAN cumulative heuristic-color count over canonical-E2");
    println!("/// community boards with score ≥ {}. N_boards = {}.", args.min_score, entries.len());
    println!("pub fn blackwood_schedule_calibrated_median(");
    println!("    puzzle: &Puzzle,");
    println!("    hints: &eternity2_core::Hints,");
    println!(") -> Option<BlackwoodSchedule> {{");
    println!("    let colors = compute_heuristic_sides(puzzle, hints);");
    println!("    if colors.len() < 3 {{ return None; }}");
    println!("    let pool_size = count_color_occurrences(puzzle, &colors);");
    println!("    let n_pos = puzzle.cell_count();");
    println!("    let targets: Vec<(u32, u32)> = vec!{:?};", median_curve);
    println!("    let bw_breaks: [u32; 12] = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256];");
    println!("    let breaks: Vec<u32> = bw_breaks.iter().map(|&b| {{");
    println!("        let scaled = ((b as u64 * n_pos as u64) / 256u64) as u32;");
    println!("        scaled.min(n_pos.saturating_sub(1))");
    println!("    }}).collect();");
    println!("    let target_max = targets.last().map(|&(d, _)| d).unwrap_or(n_pos - 1);");
    println!("    let s = BlackwoodSchedule {{");
    println!("        heuristic_sides: colors,");
    println!("        exhaustion_targets: targets,");
    println!("        heuristic_pool_size: pool_size,");
    println!("        max_heuristic_index: target_max,");
    println!("        break_indexes_allowed: breaks,");
    println!("    }};");
    println!("    s.validate().ok().map(|_| s)");
    println!("}}");
}
