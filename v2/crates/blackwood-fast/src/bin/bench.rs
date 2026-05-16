// bf_bench — benchmark the blackwood-fast core engine.
//
// Modes:
//   bf_bench gen [size] [interior_colors] [seed] [budget_ms]
//   bf_bench csv <path> [budget_ms]
//
// Defaults: gen 16 22 42 5000
//
// Reports nps and max_depth. This is the vol-106 T1 measurement.

use eternity2_blackwood_fast::solve_raw;
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_puzzle_io::load_puzzle;

fn parse_arg<T: std::str::FromStr>(args: &[String], i: usize, default: T) -> T {
    args.get(i).and_then(|s| s.parse().ok()).unwrap_or(default)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    let (puzzle, label) = match args.get(1).map(|s| s.as_str()) {
        Some("csv") => {
            let path = args.get(2).expect("usage: bf_bench csv <path> [budget_ms]");
            let p = load_puzzle(path).expect("load puzzle");
            (p, format!("csv:{path}"))
        }
        _ => {
            // gen mode (default).
            let off = if args.get(1).map(|s| s.as_str()) == Some("gen") { 2 } else { 1 };
            let size: u32 = parse_arg(&args, off, 16);
            let interior_colors: u32 = parse_arg(&args, off + 1, 22);
            let seed: u64 = parse_arg(&args, off + 2, 42);
            let cfg = GeneratorConfig { size, interior_colors, seed };
            let p = generate(cfg).expect("generator");
            (p, format!("gen:{}x{}/c={}/seed={}", size, size, interior_colors, seed))
        }
    };

    // budget_ms is the last numeric arg in either mode.
    let budget_ms: u64 = match args.get(1).map(|s| s.as_str()) {
        Some("csv") => parse_arg(&args, 3, 5000),
        _ => {
            let off = if args.get(1).map(|s| s.as_str()) == Some("gen") { 2 } else { 1 };
            parse_arg(&args, off + 3, 5000)
        }
    };

    eprintln!("bf_bench: {label} budget_ms={budget_ms}");

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
