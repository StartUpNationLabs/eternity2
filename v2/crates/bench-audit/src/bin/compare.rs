// Compare two fleet JSON reports and print a markdown table.
//
// Usage: compare BASE.json AFTER.json

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Serialize, Deserialize, Debug, Clone)]
struct EngineResult {
    size: u32,
    colors: u32,
    seed: u64,
    profile: String,
    elapsed_ms: u64,
    nodes: u64,
    propagations: u64,
    backtracks: u64,
    best_depth: u32,
    solved: bool,
    nodes_per_sec: f64,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct PtResult {
    size: u32,
    colors: u32,
    seed: u64,
    elapsed_ms: u64,
    rounds: u64,
    inner_iters_per_round: u64,
    n_replicas: usize,
    best_score: u32,
    total_edges: u32,
    iters_per_sec: f64,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct FleetReport {
    label: String,
    cpu_brand: String,
    rustflags: String,
    profile: String,
    budget_ms: u64,
    engine: Vec<EngineResult>,
    pt: Vec<PtResult>,
}

fn load(p: &PathBuf) -> FleetReport {
    let s = std::fs::read_to_string(p).expect("read");
    serde_json::from_str(&s).expect("parse")
}

fn pct_change(base: f64, after: f64) -> f64 {
    if base == 0.0 { return 0.0; }
    (after - base) / base * 100.0
}

fn fmt_pct(p: f64) -> String {
    let arrow = if p > 0.5 { "↑" } else if p < -0.5 { "↓" } else { "·" };
    format!("{arrow}{:+.1}%", p)
}

fn main() {
    let mut args = std::env::args().skip(1);
    let base_p = PathBuf::from(args.next().expect("BASE.json"));
    let after_p = PathBuf::from(args.next().expect("AFTER.json"));
    let base = load(&base_p);
    let after = load(&after_p);

    println!("# Fleet benchmark — {} vs {}", base.label, after.label);
    println!();
    println!("- CPU: {}", base.cpu_brand);
    println!("- Budget: {} ms/cell", base.budget_ms);
    println!("- Base profile: `{}`  After profile: `{}`", base.profile, after.profile);
    println!();

    println!("## Engine (gacolor_ac3, FirstSolution)");
    println!();
    println!("| Size | Colors | Seed | Base time | After time | Δ time | Base nodes/s | After nodes/s | Δ nps | Base depth | After depth |");
    println!("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|");
    let mut total_base_ms: u64 = 0;
    let mut total_after_ms: u64 = 0;
    let mut sum_base_nps = 0.0;
    let mut sum_after_nps = 0.0;
    let mut nps_count = 0;
    for (b, a) in base.engine.iter().zip(after.engine.iter()) {
        let dt = pct_change(b.elapsed_ms as f64, a.elapsed_ms as f64);
        let dnps = pct_change(b.nodes_per_sec, a.nodes_per_sec);
        let label = |r: &EngineResult| if r.solved {
            format!("{} ms", r.elapsed_ms)
        } else {
            format!("{} ms (to/exh)", r.elapsed_ms)
        };
        println!(
            "| {}×{} | {} | {} | {} | {} | {} | {:.0} | {:.0} | {} | {} | {} |",
            b.size, b.size, b.colors, b.seed,
            label(b), label(a), fmt_pct(dt),
            b.nodes_per_sec, a.nodes_per_sec, fmt_pct(dnps),
            b.best_depth, a.best_depth,
        );
        total_base_ms += b.elapsed_ms;
        total_after_ms += a.elapsed_ms;
        sum_base_nps += b.nodes_per_sec;
        sum_after_nps += a.nodes_per_sec;
        nps_count += 1;
    }
    println!();
    println!("**Engine totals:** base {} ms, after {} ms ({})",
        total_base_ms, total_after_ms,
        fmt_pct(pct_change(total_base_ms as f64, total_after_ms as f64)));
    if nps_count > 0 {
        println!("**Engine mean nodes/s:** base {:.0}, after {:.0} ({})",
            sum_base_nps / nps_count as f64,
            sum_after_nps / nps_count as f64,
            fmt_pct(pct_change(sum_base_nps / nps_count as f64, sum_after_nps / nps_count as f64)));
    }
    println!();

    println!("## Parallel Tempering");
    println!();
    println!("| Size | Seed | Base score | After score | Base iters/s | After iters/s | Δ iters/s |");
    println!("|---:|---:|---:|---:|---:|---:|---:|");
    for (b, a) in base.pt.iter().zip(after.pt.iter()) {
        let dips = pct_change(b.iters_per_sec, a.iters_per_sec);
        println!(
            "| {}×{} | {} | {}/{} | {}/{} | {:.0} | {:.0} | {} |",
            b.size, b.size, b.seed,
            b.best_score, b.total_edges,
            a.best_score, a.total_edges,
            b.iters_per_sec, a.iters_per_sec, fmt_pct(dips),
        );
    }
}
