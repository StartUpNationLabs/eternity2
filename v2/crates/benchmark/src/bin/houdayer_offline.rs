// Offline Houdayer post-mortem on harvested plateau states.
//
// For each pair (i, j) of harvested plateau states:
//   - enumerate disagreement components
//   - filter to those whose piece multisets match (swappable)
//   - score the joint-edge delta of swapping each
// Report: how often swappable components exist; the distribution of
// component sizes; the distribution of joint-edge deltas; and how
// many pairs admit at least one IMPROVING joint swap.
//
// This is the strongest single piece of evidence that Houdayer cluster
// moves would help inside PT: if pairs of plateau states routinely admit
// positive-delta swappable clusters, those moves are exactly what PT
// can't propose by itself.

use std::path::PathBuf;

use clap::Parser;
use eternity2_benchmark::board_io::read_dump;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_localsearch::houdayer::{
    component_is_swappable, delta_replace_with, disagreement_components,
};

#[derive(Parser, Debug)]
#[command(name = "houdayer_offline", about = "Houdayer post-mortem on harvested plateau states")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long, default_value = "default")]
    run_name: String,

    /// Cap on number of pairs scanned (0 = all).
    #[arg(long, default_value_t = 0)]
    max_pairs: usize,
}

fn main() {
    let args = Args::parse();
    let dir = PathBuf::from("output").join("plateau").join(&args.run_name);
    eprintln!("=== houdayer_offline ===");
    eprintln!("dir: {}", dir.display());

    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).expect("load");

    let mut entries: Vec<PathBuf> = std::fs::read_dir(&dir)
        .unwrap_or_else(|e| panic!("read_dir: {e}"))
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().and_then(|s| s.to_str()) == Some("json"))
        .filter(|p| p.file_name().and_then(|s| s.to_str()).map(|s| s.starts_with("sample_")).unwrap_or(false))
        .collect();
    entries.sort();
    if entries.len() < 2 {
        eprintln!("need ≥2 plateau states");
        return;
    }

    let boards: Vec<_> = entries.iter().map(|p| {
        let d = read_dump(p).unwrap();
        let b = d.to_board(&puzzle);
        (d.score, b)
    }).collect();
    eprintln!("loaded {} plateau states", boards.len());

    let mut all_component_sizes: Vec<usize> = Vec::new();
    let mut all_swappable_sizes: Vec<usize> = Vec::new();
    let mut all_joint_deltas: Vec<i32> = Vec::new();
    let mut all_a_deltas: Vec<i32> = Vec::new();
    let mut all_b_deltas: Vec<i32> = Vec::new();

    let mut pairs_with_swappable = 0usize;
    let mut pairs_with_improving = 0usize;
    let mut total_pairs = 0usize;
    let mut total_swappable_components = 0usize;
    let mut total_improving_components = 0usize;

    'outer: for i in 0..boards.len() {
        for j in (i + 1)..boards.len() {
            total_pairs += 1;
            let comps = disagreement_components(&puzzle, &boards[i].1, &boards[j].1);
            let mut had_swappable = false;
            let mut had_improving = false;
            for comp in comps {
                if comp.len() < 2 { continue; }
                all_component_sizes.push(comp.len());
                if component_is_swappable(&boards[i].1, &boards[j].1, &comp) {
                    had_swappable = true;
                    total_swappable_components += 1;
                    all_swappable_sizes.push(comp.len());
                    let a_d = delta_replace_with(&puzzle, &boards[i].1, &boards[j].1, &comp);
                    let b_d = delta_replace_with(&puzzle, &boards[j].1, &boards[i].1, &comp);
                    let joint = a_d + b_d;
                    all_a_deltas.push(a_d);
                    all_b_deltas.push(b_d);
                    all_joint_deltas.push(joint);
                    if joint > 0 {
                        had_improving = true;
                        total_improving_components += 1;
                    }
                }
            }
            if had_swappable { pairs_with_swappable += 1; }
            if had_improving { pairs_with_improving += 1; }
            if args.max_pairs > 0 && total_pairs >= args.max_pairs { break 'outer; }
        }
    }

    eprintln!("\n=== RESULTS ===");
    eprintln!("pairs scanned:                 {}", total_pairs);
    eprintln!("pairs with ≥1 swappable comp:  {} ({:.1}%)",
        pairs_with_swappable, 100.0 * (pairs_with_swappable as f64) / (total_pairs.max(1) as f64));
    eprintln!("pairs with ≥1 IMPROVING comp:  {} ({:.1}%)",
        pairs_with_improving, 100.0 * (pairs_with_improving as f64) / (total_pairs.max(1) as f64));
    eprintln!("total swappable components:    {}", total_swappable_components);
    eprintln!("total improving components:    {}", total_improving_components);

    let mean = |xs: &[usize]| if xs.is_empty() { 0.0 } else { xs.iter().sum::<usize>() as f64 / xs.len() as f64 };
    let mean_i = |xs: &[i32]| if xs.is_empty() { 0.0 } else { xs.iter().sum::<i32>() as f64 / xs.len() as f64 };

    eprintln!("\nall disagreement components (size ≥ 2):");
    eprintln!("  n={}  mean_size={:.1}", all_component_sizes.len(), mean(&all_component_sizes));
    if !all_component_sizes.is_empty() {
        let mut sorted = all_component_sizes.clone();
        sorted.sort_unstable();
        eprintln!("  size percentiles: p10={} p50={} p90={} max={}",
            sorted[(sorted.len() as f64 * 0.10) as usize],
            sorted[(sorted.len() as f64 * 0.50) as usize],
            sorted[(sorted.len() as f64 * 0.90) as usize],
            sorted.last().unwrap());
    }

    eprintln!("\nswappable components:");
    eprintln!("  n={}  mean_size={:.1}", all_swappable_sizes.len(), mean(&all_swappable_sizes));
    if !all_swappable_sizes.is_empty() {
        let mut sorted = all_swappable_sizes.clone();
        sorted.sort_unstable();
        eprintln!("  size percentiles: p10={} p50={} p90={} max={}",
            sorted[(sorted.len() as f64 * 0.10) as usize],
            sorted[(sorted.len() as f64 * 0.50) as usize],
            sorted[(sorted.len() as f64 * 0.90) as usize],
            sorted.last().unwrap());
    }

    eprintln!("\njoint score deltas of swappable components:");
    eprintln!("  n={}  mean={:.2}", all_joint_deltas.len(), mean_i(&all_joint_deltas));
    if !all_joint_deltas.is_empty() {
        let max_pos = *all_joint_deltas.iter().max().unwrap_or(&0);
        let min_neg = *all_joint_deltas.iter().min().unwrap_or(&0);
        let n_pos = all_joint_deltas.iter().filter(|&&d| d > 0).count();
        let n_zero = all_joint_deltas.iter().filter(|&&d| d == 0).count();
        let n_neg = all_joint_deltas.iter().filter(|&&d| d < 0).count();
        eprintln!("  positive: {} ({:.1}%)  zero: {} ({:.1}%)  negative: {} ({:.1}%)",
            n_pos, 100.0 * (n_pos as f64) / (all_joint_deltas.len() as f64),
            n_zero, 100.0 * (n_zero as f64) / (all_joint_deltas.len() as f64),
            n_neg, 100.0 * (n_neg as f64) / (all_joint_deltas.len() as f64));
        eprintln!("  max joint delta: {}   min joint delta: {}", max_pos, min_neg);
    }

    let summary = serde_json::json!({
        "n_states": boards.len(),
        "pairs_scanned": total_pairs,
        "pairs_with_swappable": pairs_with_swappable,
        "pairs_with_improving": pairs_with_improving,
        "swappable_components_total": total_swappable_components,
        "improving_components_total": total_improving_components,
        "swappable_component_sizes": all_swappable_sizes,
        "joint_deltas": all_joint_deltas,
        "a_deltas": all_a_deltas,
        "b_deltas": all_b_deltas,
    });
    let out = dir.join("_houdayer_offline.json");
    if let Err(e) = std::fs::write(&out, serde_json::to_string_pretty(&summary).unwrap() + "\n") {
        eprintln!("warning: failed to write summary: {e}");
    } else {
        eprintln!("\nsummary: {}", out.display());
    }

    eprintln!("\nInterpretation:");
    eprintln!("  - 0% pairs with swappable: piece-set matching is too restrictive; consider");
    eprintln!("      a relaxed cluster move (sub-multiset rearrangement).");
    eprintln!("  - >50% pairs with IMPROVING: Houdayer integrated in PT should beat 449.");
    eprintln!("  - swappable but never improving: cluster moves can mix replicas but cannot");
    eprintln!("      escape the plateau on their own; combine with PT exchanges.");
}
