// Joins a v2 benchmark JSON with the legacy data/generated/results.csv
// and prints a Markdown comparison table.
//
// Usage:
//   cargo run --release -p eternity2-benchmark --bin compare_legacy -- \
//     --v2 v2/data/bench_legacy.json \
//     --legacy data/generated/results.csv

use std::collections::HashMap;
use std::path::PathBuf;

use clap::Parser;
use serde::Deserialize;

#[derive(Parser, Debug)]
struct Args {
    #[arg(long)] v2: PathBuf,
    #[arg(long)] legacy: PathBuf,
}

#[derive(Deserialize)]
struct V2Report {
    cpu_brand: String,
    n_cores_logical: usize,
    rayon_threads: usize,
    time_budget_ms: u64,
    runs_per_cell: u32,
    puzzles: Vec<V2Puzzle>,
}

#[derive(Deserialize)]
struct V2Puzzle {
    puzzle: V2PuzzleSpec,
    profiles: Vec<V2ProfileResult>,
}

#[derive(Deserialize)]
struct V2PuzzleSpec { file: String, size: u32, colors: u32 }

#[derive(Deserialize)]
#[allow(dead_code)]
struct V2ProfileResult {
    solver_id: String,
    heuristic_profile: String,
    median_time_us: u128,
    solved_count: u32,
}

struct LegacyRow {
    v1_solved: bool,    v1_time_ms: f64,
    v2_std_solved: bool, v2_std_time_ms: f64,
    v2_bf_solved: bool,  v2_bf_time_ms: f64,
    v2_par_solved: bool, v2_par_time_ms: f64,
    v2_par_bf_solved: bool, v2_par_bf_time_ms: f64,
    v3_solved: bool,     v3_time_ms: f64,
    v3_par_solved: bool, v3_par_time_ms: f64,
}

fn parse_bool(s: &str) -> bool { s.trim().eq_ignore_ascii_case("true") }
fn parse_f64(s: &str) -> f64 { s.trim().parse().unwrap_or(0.0) }

fn load_legacy(path: &PathBuf) -> HashMap<String, LegacyRow> {
    let raw = std::fs::read_to_string(path).expect("read legacy");
    let mut lines = raw.lines();
    let _header = lines.next();
    let mut out = HashMap::new();
    for line in lines {
        if line.trim().is_empty() { continue; }
        let cols: Vec<&str> = line.split(',').collect();
        if cols.len() < 36 { continue; }
        let file_path = cols[0].trim_matches('"');
        let fname = file_path.rsplit('/').next().unwrap_or(file_path).to_string();
        out.insert(fname, LegacyRow {
            v1_solved: parse_bool(cols[2]),    v1_time_ms: parse_f64(cols[3]),
            v2_std_solved: parse_bool(cols[6]),  v2_std_time_ms: parse_f64(cols[7]),
            v2_bf_solved: parse_bool(cols[11]),  v2_bf_time_ms: parse_f64(cols[12]),
            v2_par_solved: parse_bool(cols[16]), v2_par_time_ms: parse_f64(cols[17]),
            v2_par_bf_solved: parse_bool(cols[21]), v2_par_bf_time_ms: parse_f64(cols[22]),
            v3_solved: parse_bool(cols[26]),    v3_time_ms: parse_f64(cols[27]),
            v3_par_solved: parse_bool(cols[31]),v3_par_time_ms: parse_f64(cols[32]),
        });
    }
    out
}

fn fmt_legacy(solved: bool, t: f64) -> String {
    if !solved { format!("**{:.0}**(×)", t) }
    else if t < 1.0 { format!("{:.3}", t) }
    else { format!("{:.1}", t) }
}

fn fmt_v2(p: &V2ProfileResult) -> String {
    let ms = (p.median_time_us as f64) / 1000.0;
    if p.solved_count == 0 { format!("**{:.0}**(×)", ms) }
    else if ms < 1.0 { format!("{:.3}", ms) }
    else { format!("{:.1}", ms) }
}

fn main() {
    let args = Args::parse();
    let v2: V2Report = serde_json::from_str(&std::fs::read_to_string(&args.v2).expect("read v2 json")).expect("parse v2");
    let legacy = load_legacy(&args.legacy);

    println!("## Legacy vs v2 comparison\n");
    println!("**v2 system:** {} ({} logical cores, rayon = {} threads)", v2.cpu_brand, v2.n_cores_logical, v2.rayon_threads);
    println!("**v2 budget:** {} ms × {} run(s) (median ms reported)", v2.time_budget_ms, v2.runs_per_cell);
    println!("**Legacy:** times from `data/generated/results.csv` (provenance: original C++ run)\n");

    // Pick a representative v2 profile per category for the table.
    let interesting_v2 = [
        "row_by_row", "border_first_lcv", "border_first_full",
        "border_first_lcv_par", "border_first_full_par",
    ];

    print!("| Puzzle | sz | col | v1 | v2_std | v2_bf | v2_par | v2_par_bf | v3 | v3_par");
    for p in &interesting_v2 { print!(" | v2/{}", p); }
    println!(" |");
    print!("|---|---|---|---|---|---|---|---|---|---");
    for _ in &interesting_v2 { print!("|---"); }
    println!("|");

    let mut total_v3 = 0.0f64;
    let mut total_v2_engine = 0.0f64;
    let mut total_v3_par = 0.0f64;
    let mut total_v2_par = 0.0f64;
    let mut wins_v2_vs_v3 = 0u32;
    let mut losses_v2_vs_v3 = 0u32;
    let mut wins_v2par_vs_v3par = 0u32;
    let mut losses_v2par_vs_v3par = 0u32;

    for puz in &v2.puzzles {
        let leg = legacy.get(&puz.puzzle.file);
        let leg_str = if let Some(l) = leg {
            format!(
                "{} | {} | {} | {} | {} | {} | {}",
                fmt_legacy(l.v1_solved, l.v1_time_ms),
                fmt_legacy(l.v2_std_solved, l.v2_std_time_ms),
                fmt_legacy(l.v2_bf_solved, l.v2_bf_time_ms),
                fmt_legacy(l.v2_par_solved, l.v2_par_time_ms),
                fmt_legacy(l.v2_par_bf_solved, l.v2_par_bf_time_ms),
                fmt_legacy(l.v3_solved, l.v3_time_ms),
                fmt_legacy(l.v3_par_solved, l.v3_par_time_ms),
            )
        } else {
            "- | - | - | - | - | - | -".into()
        };
        print!("| {} | {} | {} | {}", puz.puzzle.file, puz.puzzle.size, puz.puzzle.colors, leg_str);
        for name in &interesting_v2 {
            if let Some(p) = puz.profiles.iter().find(|p| p.heuristic_profile == *name) {
                print!(" | {}", fmt_v2(p));
            } else {
                print!(" | -");
            }
        }
        println!(" |");

        // Aggregate.
        if let Some(l) = leg {
            if let Some(v3_v2) = puz.profiles.iter().find(|p| p.heuristic_profile == "border_first_full") {
                if l.v3_solved && v3_v2.solved_count > 0 {
                    let v2_ms = (v3_v2.median_time_us as f64) / 1000.0;
                    total_v3 += l.v3_time_ms;
                    total_v2_engine += v2_ms;
                    if v2_ms < l.v3_time_ms { wins_v2_vs_v3 += 1; }
                    else if v2_ms > l.v3_time_ms * 1.1 { losses_v2_vs_v3 += 1; }
                }
            }
            if let Some(v2_par_full) = puz.profiles.iter().find(|p| p.heuristic_profile == "border_first_full_par") {
                if l.v3_par_solved && v2_par_full.solved_count > 0 {
                    let v2_ms = (v2_par_full.median_time_us as f64) / 1000.0;
                    total_v3_par += l.v3_par_time_ms;
                    total_v2_par += v2_ms;
                    if v2_ms < l.v3_par_time_ms { wins_v2par_vs_v3par += 1; }
                    else if v2_ms > l.v3_par_time_ms * 1.1 { losses_v2par_vs_v3par += 1; }
                }
            }
        }
    }

    println!("\n## Aggregates (puzzles where both solved)\n");
    println!("- **v2 engine/border_first_full vs legacy v3:** {} wins, {} losses (>10% slower). Sum medians: v2 {:.1} ms, legacy v3 {:.1} ms — v2/v3 ratio = {:.2}×",
        wins_v2_vs_v3, losses_v2_vs_v3, total_v2_engine, total_v3,
        if total_v3 > 0.0 { total_v2_engine / total_v3 } else { 0.0 });
    println!("- **v2 border_first_full_par vs legacy v3_par:** {} wins, {} losses. Sum medians: v2_par {:.1} ms, legacy v3_par {:.1} ms — ratio = {:.2}×",
        wins_v2par_vs_v3par, losses_v2par_vs_v3par, total_v2_par, total_v3_par,
        if total_v3_par > 0.0 { total_v2_par / total_v3_par } else { 0.0 });
}
