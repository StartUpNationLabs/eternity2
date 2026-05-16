// bf_bench — benchmark the blackwood-fast core engine on a generated puzzle.
//
// Usage: bf_bench [size] [interior_colors] [seed] [budget_ms]
// Defaults: 16 22 42 5000
//
// Reports nps and max_depth. This is the vol-106 T1 measurement.

use eternity2_blackwood_fast::solve_raw;
use eternity2_generator::{generate, GeneratorConfig};

fn parse_arg<T: std::str::FromStr>(args: &[String], i: usize, default: T) -> T {
    args.get(i).and_then(|s| s.parse().ok()).unwrap_or(default)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let size: u32 = parse_arg(&args, 1, 16);
    let interior_colors: u32 = parse_arg(&args, 2, 22);
    let seed: u64 = parse_arg(&args, 3, 42);
    let budget_ms: u64 = parse_arg(&args, 4, 5000);

    eprintln!(
        "bf_bench: size={} interior_colors={} seed={} budget_ms={}",
        size, interior_colors, seed, budget_ms
    );

    let cfg = GeneratorConfig { size, interior_colors, seed };
    let puzzle = generate(cfg).expect("generator");

    let t0 = std::time::Instant::now();
    let (stats, _board) = solve_raw(&puzzle, budget_ms * 1000);
    let elapsed = t0.elapsed();

    let nps = (stats.nodes as f64) / elapsed.as_secs_f64();
    println!(
        "nodes={} max_depth={} solved={} elapsed_ms={} nps={:.1}",
        stats.nodes,
        stats.max_depth,
        stats.solved,
        elapsed.as_millis(),
        nps
    );
}
