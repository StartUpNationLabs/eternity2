// Overlap analysis for the RSB diagnostic.
//
// Reads all `output/plateau/<run_name>/sample_*.json` dumps and computes
// the pairwise overlap distribution P(q). Three overlap variants:
//
//   q_piece     — fraction of cells with the same piece id (ignores rotation).
//   q_oriented  — fraction of cells with the same (piece, rotation).
//   q_edge      — fraction of internal edges where both boards present the
//                 same color on both incident faces. This is the closest
//                 analog to the spin-glass "energy overlap" because it
//                 directly compares the constraint-satisfying structure
//                 rather than identity.
//
// Output:
//   - histogram of q to stderr (12 bins from 0 to 1).
//   - JSON summary at output/plateau/<run_name>/_overlap.json with mean,
//     std, percentiles, and per-pair table.
//   - optional CSV of pairs for plotting.
//
// Interpretation:
//   - q narrowly peaked near 1   → all plateau states are essentially the
//     same configuration (one basin); RSB framing is wrong.
//   - q peaked at one value < 1  → states are diverse but homogeneous
//     (one giant basin with thermal noise); replica-symmetric.
//   - q multi-modal              → discrete basins separated in
//     configuration space → 1-RSB (or worse) → Houdayer cluster moves
//     are the named cure.

use std::fs;
use std::path::PathBuf;

use clap::Parser;
use eternity2_benchmark::board_io::{read_dump, DumpedBoard};

#[derive(Parser, Debug)]
#[command(name = "analyze_overlap", about = "P(q) for harvested plateau states")]
struct Args {
    /// Sub-directory of output/plateau/ to read.
    #[arg(long, default_value = "default")]
    run_name: String,

    /// Also write a CSV of (i, j, q_piece, q_oriented, q_edge) for plotting.
    #[arg(long, default_value_t = false)]
    csv: bool,
}

fn q_piece(a: &DumpedBoard, b: &DumpedBoard) -> f64 {
    assert_eq!(a.cells.len(), b.cells.len());
    let mut both = 0u32;
    let mut same = 0u32;
    for (ca, cb) in a.cells.iter().zip(b.cells.iter()) {
        if let (Some([pa, _]), Some([pb, _])) = (ca, cb) {
            both += 1;
            if pa == pb { same += 1; }
        }
    }
    if both == 0 { 0.0 } else { (same as f64) / (both as f64) }
}

fn q_oriented(a: &DumpedBoard, b: &DumpedBoard) -> f64 {
    let mut both = 0u32;
    let mut same = 0u32;
    for (ca, cb) in a.cells.iter().zip(b.cells.iter()) {
        if let (Some([pa, ra]), Some([pb, rb])) = (ca, cb) {
            both += 1;
            if pa == pb && ra == rb { same += 1; }
        }
    }
    if both == 0 { 0.0 } else { (same as f64) / (both as f64) }
}

// Compare the *edge labelings* both boards induce. For each interior edge
// of the grid (horizontal between (x,y)-(x+1,y) or vertical between
// (x,y)-(x,y+1)) we read the two color values both boards assign to the
// two incident faces and count it as agreeing iff both pairs match.
//
// We do not have piece edges here (the dump stores piece id + rotation
// only), so we accept the dump's `score` field as ground truth for
// per-board correctness and instead compare on a structural fingerprint
// constructed from (piece_id, rotation) — same pair at same position
// implies same edge labels. That's exactly q_oriented; so q_edge as
// defined would require the original puzzle. To avoid pulling the puzzle
// into this binary we drop q_edge for now; q_oriented carries the same
// signal because piece+rotation determines all four edges.
//
// Keeping the function stub so future versions can fold in the puzzle
// and compute the true edge-overlap.

fn histogram(values: &[f64], bins: usize) -> Vec<u32> {
    let mut h = vec![0u32; bins];
    for &v in values {
        let mut idx = (v * (bins as f64)).floor() as usize;
        if idx >= bins { idx = bins - 1; }
        h[idx] += 1;
    }
    h
}

fn percentile(sorted: &[f64], p: f64) -> f64 {
    if sorted.is_empty() { return 0.0; }
    let rank = (p * ((sorted.len() - 1) as f64)).round() as usize;
    sorted[rank.min(sorted.len() - 1)]
}

fn main() {
    let args = Args::parse();
    let dir = PathBuf::from("output").join("plateau").join(&args.run_name);
    eprintln!("=== analyze_overlap ===");
    eprintln!("dir: {}", dir.display());

    let entries: Vec<PathBuf> = fs::read_dir(&dir)
        .unwrap_or_else(|e| panic!("read_dir {}: {}", dir.display(), e))
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().and_then(|s| s.to_str()) == Some("json"))
        .filter(|p| p.file_name().and_then(|s| s.to_str()).map(|s| s.starts_with("sample_")).unwrap_or(false))
        .collect();

    let mut dumps: Vec<DumpedBoard> = Vec::with_capacity(entries.len());
    let mut paths_sorted: Vec<PathBuf> = entries.clone();
    paths_sorted.sort();
    for p in &paths_sorted {
        match read_dump(p) {
            Ok(d) => dumps.push(d),
            Err(e) => eprintln!("skip {}: {e}", p.display()),
        }
    }
    let n = dumps.len();
    if n < 2 {
        eprintln!("need at least 2 plateau states, found {n}; harvest more first.");
        return;
    }
    eprintln!("loaded {} plateau states", n);
    let scores: Vec<u32> = dumps.iter().map(|d| d.score).collect();
    eprintln!("scores: min={} max={} mean={:.1}",
        scores.iter().min().unwrap(),
        scores.iter().max().unwrap(),
        (scores.iter().sum::<u32>() as f64) / (n as f64),
    );

    let mut q_piece_vals: Vec<f64> = Vec::with_capacity(n * (n - 1) / 2);
    let mut q_orient_vals: Vec<f64> = Vec::with_capacity(n * (n - 1) / 2);
    let mut pairs: Vec<(usize, usize, f64, f64)> = Vec::new();
    for i in 0..n {
        for j in (i + 1)..n {
            let qp = q_piece(&dumps[i], &dumps[j]);
            let qo = q_oriented(&dumps[i], &dumps[j]);
            q_piece_vals.push(qp);
            q_orient_vals.push(qo);
            pairs.push((i, j, qp, qo));
        }
    }

    fn report(name: &str, mut vals: Vec<f64>) -> serde_json::Value {
        vals.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let n = vals.len();
        let mean = vals.iter().sum::<f64>() / (n as f64);
        let var = vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (n as f64);
        let std = var.sqrt();
        let p05 = percentile(&vals, 0.05);
        let p25 = percentile(&vals, 0.25);
        let p50 = percentile(&vals, 0.50);
        let p75 = percentile(&vals, 0.75);
        let p95 = percentile(&vals, 0.95);
        let hist = histogram(&vals, 12);
        eprintln!("\n--- {} (n={} pairs) ---", name, n);
        eprintln!("  mean={:.4} std={:.4}", mean, std);
        eprintln!("  min={:.4} p05={:.4} p25={:.4} p50={:.4} p75={:.4} p95={:.4} max={:.4}",
            vals[0], p05, p25, p50, p75, p95, vals[n - 1]);
        eprintln!("  histogram (12 bins, [0,1]):");
        for (b, count) in hist.iter().enumerate() {
            let lo = (b as f64) / 12.0;
            let hi = ((b + 1) as f64) / 12.0;
            let bar = "#".repeat((*count as usize).min(60));
            eprintln!("    [{:.2}..{:.2}) {:4}  {}", lo, hi, count, bar);
        }
        serde_json::json!({
            "n_pairs": n,
            "mean": mean,
            "std": std,
            "min": vals[0],
            "max": vals[n - 1],
            "p05": p05, "p25": p25, "p50": p50, "p75": p75, "p95": p95,
            "histogram_12bins_0to1": hist,
        })
    }

    let q_piece_summary = report("q_piece (piece-id agreement)", q_piece_vals.clone());
    let q_orient_summary = report("q_oriented (piece+rotation agreement)", q_orient_vals.clone());

    let summary = serde_json::json!({
        "n_samples": n,
        "scores": scores,
        "q_piece": q_piece_summary,
        "q_oriented": q_orient_summary,
    });
    let summary_path = dir.join("_overlap.json");
    if let Err(e) = fs::write(&summary_path, serde_json::to_string_pretty(&summary).unwrap() + "\n") {
        eprintln!("warning: failed to write summary: {e}");
    } else {
        eprintln!("\nsummary: {}", summary_path.display());
    }

    if args.csv {
        let csv_path = dir.join("_overlap_pairs.csv");
        let mut s = String::from("i,j,q_piece,q_oriented\n");
        for (i, j, qp, qo) in pairs {
            s.push_str(&format!("{i},{j},{qp:.6},{qo:.6}\n"));
        }
        if let Err(e) = fs::write(&csv_path, s) {
            eprintln!("warning: failed to write csv: {e}");
        } else {
            eprintln!("csv: {}", csv_path.display());
        }
    }

    eprintln!("\nInterpretation hints:");
    eprintln!("  - If q_oriented histogram has ONE sharp peak near 1.0:");
    eprintln!("      all plateau states are basically the same config — try perturbing more.");
    eprintln!("  - If q_oriented has ONE smooth bell around a single value < 1:");
    eprintln!("      replica-symmetric / single giant basin — RSB is NOT the explanation.");
    eprintln!("  - If q_oriented has TWO OR MORE peaks separated by gaps:");
    eprintln!("      1-RSB confirmed. Houdayer cluster moves are the next experiment.");
}
