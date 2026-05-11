// Eternity II v2 benchmark runner.
//
// Loads legacy CSV puzzles from a directory, runs each (puzzle, profile)
// triple `runs` times with a per-run time budget, writes structured JSON
// output, and prints a Markdown comparison table.
//
// Parallelism strategy:
//   - parallel profiles (border_first_*_par) saturate cores internally
//   - non-parallel profiles run one at a time per puzzle, but multiple
//     puzzles run concurrently via rayon to keep all cores busy
//
// Use --release with RUSTFLAGS="-C target-cpu=native" for max perf.

use eternity2_benchmark::{loader, runner};

use std::path::PathBuf;
use std::sync::Mutex;

use clap::Parser;
use rayon::prelude::*;

#[derive(Parser, Debug)]
#[command(name = "eternity2-benchmark")]
struct Args {
    /// Directory containing the legacy CSV puzzle corpus.
    #[arg(long, default_value = "../data/benchmark")]
    corpus: PathBuf,

    /// Output JSON path.
    #[arg(long, default_value = "../data/v2_bench_results.json")]
    output: PathBuf,

    /// Per-run time budget in milliseconds.
    #[arg(long, default_value_t = 300_000)]
    time_budget_ms: u64,

    /// Number of runs per (puzzle, profile) for median reporting.
    #[arg(long, default_value_t = 3)]
    runs: u32,

    /// Only include puzzles with size <= this. 0 = all.
    #[arg(long, default_value_t = 0)]
    max_size: u32,

    /// Only include puzzles with size >= this.
    #[arg(long, default_value_t = 0)]
    min_size: u32,

    /// Skip these profiles (comma-separated heuristic_profile names).
    #[arg(long, default_value = "")]
    skip: String,

    /// Number of puzzles to run concurrently. 0 = rayon default.
    #[arg(long, default_value_t = 1)]
    parallel_puzzles: usize,
}

fn main() {
    let args = Args::parse();
    let skip_set: Vec<&str> = args.skip.split(',').filter(|s| !s.is_empty()).collect();
    let active_profiles: Vec<runner::ProfileSpec> = runner::PROFILES.iter()
        .filter(|p| !skip_set.contains(&p.heuristic_profile))
        .copied()
        .collect();

    let mut puzzle_paths = runner::list_puzzles(&args.corpus);
    if args.max_size > 0 || args.min_size > 0 {
        puzzle_paths.retain(|p| {
            let fname = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
            let Some((size, _)) = runner::parse_size_colors(fname) else { return false; };
            (args.max_size == 0 || size <= args.max_size)
                && (args.min_size == 0 || size >= args.min_size)
        });
    }

    let (cpu_brand, physical, logical) = runner::cpu_info();
    let rayon_threads = rayon::current_num_threads();
    eprintln!("== benchmark ==");
    eprintln!("cpu: {cpu_brand} ({physical} physical / {logical} logical cores)");
    eprintln!("rayon threads: {rayon_threads}");
    eprintln!("time budget: {} ms per run, {} runs per cell", args.time_budget_ms, args.runs);
    eprintln!("active profiles: {}", active_profiles.iter().map(|p| p.heuristic_profile).collect::<Vec<_>>().join(", "));
    eprintln!("puzzles to run: {}", puzzle_paths.len());

    let total_cells = puzzle_paths.len() * active_profiles.len();
    let progress = Mutex::new(0usize);
    let collected: Mutex<Vec<runner::PuzzleReport>> = Mutex::new(Vec::new());
    let bench_start = std::time::Instant::now();

    // Header for the running JSON. After each puzzle we rewrite the file
    // atomically so an interrupt never loses already-completed work.
    let write_progress = |collected: &Mutex<Vec<runner::PuzzleReport>>| {
        let snap = collected.lock().unwrap().clone();
        let report = runner::BenchReport {
            cpu_brand: cpu_brand.clone(),
            n_cores_physical: physical,
            n_cores_logical: logical,
            rayon_threads,
            time_budget_ms: args.time_budget_ms,
            runs_per_cell: args.runs,
            git_branch: runner::git_branch(),
            puzzles: snap,
        };
        let json = serde_json::to_string_pretty(&report).expect("json");
        let tmp = args.output.with_extension("json.tmp");
        if let Some(parent) = args.output.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        std::fs::write(&tmp, &json).expect("write tmp json");
        std::fs::rename(&tmp, &args.output).expect("rename json");
    };

    let run_puzzle = |path: &PathBuf| -> Option<runner::PuzzleReport> {
        let puzzle = match loader::load_puzzle(path) {
            Ok(p) => p,
            Err(e) => {
                eprintln!("[skip] {}: {e}", path.display());
                return None;
            }
        };
        let spec = runner::puzzle_spec(path, &puzzle);
        let mut profile_reports = Vec::with_capacity(active_profiles.len());
        for prof in &active_profiles {
            let cell_start = std::time::Instant::now();
            let report = runner::run_profile(&puzzle, prof, args.time_budget_ms, args.runs);
            let cell_secs = cell_start.elapsed().as_secs_f64();
            let bench_elapsed_s = bench_start.elapsed().as_secs();
            let bench_h = bench_elapsed_s / 3600;
            let bench_m = (bench_elapsed_s / 60) % 60;
            let bench_s = bench_elapsed_s % 60;
            {
                let mut p = progress.lock().unwrap();
                *p += 1;
                let outcome = if report.solved_count > 0 { "✓" } else { "✗" };
                eprintln!(
                    "[{}/{}] +{:02}:{:02}:{:02} cell={:.1}s {} {:>22} {} median {:.3}ms (solved {}/{})",
                    *p, total_cells,
                    bench_h, bench_m, bench_s,
                    cell_secs,
                    spec.file, prof.heuristic_profile, outcome,
                    (report.median_time_us as f64) / 1000.0,
                    report.solved_count, args.runs,
                );
            }
            profile_reports.push(report);
        }
        let puzzle_report = runner::PuzzleReport { puzzle: spec, profiles: profile_reports };
        collected.lock().unwrap().push(puzzle_report.clone());
        write_progress(&collected);
        Some(puzzle_report)
    };

    let puzzle_reports: Vec<runner::PuzzleReport> = if args.parallel_puzzles <= 1 {
        puzzle_paths.iter().filter_map(run_puzzle).collect()
    } else {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(args.parallel_puzzles)
            .build()
            .expect("rayon");
        pool.install(|| puzzle_paths.par_iter().filter_map(run_puzzle).collect())
    };

    let report = runner::BenchReport {
        cpu_brand,
        n_cores_physical: physical,
        n_cores_logical: logical,
        rayon_threads,
        time_budget_ms: args.time_budget_ms,
        runs_per_cell: args.runs,
        git_branch: runner::git_branch(),
        puzzles: puzzle_reports,
    };

    let json = serde_json::to_string_pretty(&report).expect("json");
    std::fs::write(&args.output, &json).expect("write json");
    eprintln!("\nwrote {}", args.output.display());

    print_summary(&report);
}

fn print_summary(report: &runner::BenchReport) {
    use std::collections::BTreeMap;

    println!("\n## Benchmark summary");
    println!("**CPU:** {}", report.cpu_brand);
    println!("**Cores:** {} physical / {} logical, rayon = {} threads", report.n_cores_physical, report.n_cores_logical, report.rayon_threads);
    println!("**Budget:** {} ms × {} runs (median reported)\n", report.time_budget_ms, report.runs_per_cell);

    // Per-profile rollup.
    let mut by_profile: BTreeMap<String, (u32, u32, u128)> = BTreeMap::new();
    let total = report.puzzles.len() as u32;
    for p in &report.puzzles {
        for pr in &p.profiles {
            let key = format!("{}/{}", pr.solver_id, pr.heuristic_profile);
            let entry = by_profile.entry(key).or_insert((0, 0, 0));
            entry.0 += if pr.solved_count > 0 { 1 } else { 0 };
            entry.1 += 1;
            entry.2 += pr.median_time_us;
        }
    }
    println!("### Rollup: solved-of-total and sum of median wall times\n");
    println!("| Profile | Solved / Puzzles | Sum of medians (ms) |");
    println!("|---|---|---|");
    for (profile, (solved, count, sum)) in &by_profile {
        println!("| {profile} | {solved} / {count} | {:.3} |", (*sum as f64) / 1000.0);
    }

    // Per-puzzle table.
    println!("\n### Per-puzzle median times (ms)\n");
    let profiles: Vec<String> = by_profile.keys().cloned().collect();
    print!("| Puzzle | size | colors");
    for p in &profiles { print!(" | {}", p.split('/').next_back().unwrap_or(p)); }
    println!(" |");
    print!("|---|---|---");
    for _ in &profiles { print!("|---"); }
    println!("|");
    for p in &report.puzzles {
        print!("| {} | {} | {}", p.puzzle.file, p.puzzle.size, p.puzzle.colors);
        for pr in &p.profiles {
            let ms = (pr.median_time_us as f64) / 1000.0;
            let cell = if pr.solved_count > 0 {
                if ms < 1.0 { format!("{:.3}", ms) } else { format!("{:.1}", ms) }
            } else {
                format!("**{:.0}** (×)", ms)
            };
            print!(" | {cell}");
        }
        println!(" |");
    }
    let _ = total;
}
