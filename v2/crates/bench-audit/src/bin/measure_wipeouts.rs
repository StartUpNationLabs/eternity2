// Vol-56 T3 — measure AC-3 wipeout frequency and depth distribution
// on canonical-E2, to bound the EV of no-good learning.
//
// Hypothesis: if many wipeouts occur at depth >= D for some D >> 20,
// AND if the "wipeout depth" distribution is multi-modal (many at
// similar depths), no-good learning would prune effectively because
// the same sub-assignments are reached and fail.
//
// Counter-hypothesis: if wipeouts are predominantly at small depths
// or singularly-deep with no repetition, no-good learning offers
// little structural benefit beyond what AC-3 already does on-the-fly.
//
// What we record: depth at each domain wipeout event during a 60s
// canonical solve. Aggregate distribution + counts.

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_events::{BufferSink, EventBody};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineSolver};
use eternity2_solver_trait::{SolveOpts, Solver};

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");

    let mut solver = EngineSolver::joe_depth150_bp();
    let budget_ms: u64 = std::env::var("E2_PROFILE_MS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(60_000);
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = budget_ms;
    opts.seed = 1;
    opts.hints = hints;
    let bp_path = PathBuf::from("output/v12_bp/edge_bp_60i.json");
    if bp_path.exists() {
        if let Ok(bp) = load_edge_bp_marginals(&bp_path) {
            opts.edge_bp_marginals = Some(bp);
        }
    }

    let mut sink = BufferSink::default();
    let t = std::time::Instant::now();
    let _outcome = solver.solve(&puzzle, &opts, &mut sink);
    let elapsed_ms = t.elapsed().as_millis() as u64;

    let mut depth_hist: std::collections::HashMap<u32, u64> = std::collections::HashMap::new();
    let mut wipe_count: u64 = 0;
    let mut node_count: u64 = 0;
    let mut bt_count: u64 = 0;
    let mut max_depth: u32 = 0;
    let mut final_wipeouts: u64 = 0;
    for ev in &sink.events {
        match &ev.body {
            EventBody::DomainWipeout { .. } => {
                wipe_count += 1;
                *depth_hist.entry(ev.depth).or_insert(0) += 1;
                if ev.depth > max_depth { max_depth = ev.depth; }
            }
            EventBody::ValueTried { .. } => { node_count += 1; }
            EventBody::Backtrack { .. } => { bt_count += 1; }
            EventBody::TimedOut { final_stats, .. }
            | EventBody::Exhausted { final_stats, .. }
            | EventBody::Solved { final_stats, .. }
            | EventBody::Cancelled { final_stats, .. } => { final_wipeouts = final_stats.domain_wipeouts; }
            _ => {}
        }
    }
    eprintln!("elapsed_ms = {}, max_depth = {}", elapsed_ms, max_depth);
    eprintln!("counted in event stream: nodes={node_count}, backtracks={bt_count}, wipeouts={wipe_count}");
    eprintln!("final_stats.domain_wipeouts = {}", final_wipeouts);
    eprintln!();
    eprintln!("Note: Stats events are throttled, so event-stream wipeouts undercount;");
    eprintln!("`final_stats.domain_wipeouts` is the truth.");
    eprintln!();
    eprintln!("Depth histogram (event-stream wipeouts, observed):");
    let mut depths: Vec<&u32> = depth_hist.keys().collect();
    depths.sort();
    for d in depths {
        eprintln!("  depth {:3}: {:>7}", d, depth_hist[d]);
    }
    eprintln!();
    eprintln!("Observed wipeouts span depth range [{}, {}]",
        depth_hist.keys().min().copied().unwrap_or(0),
        max_depth);
    let total: u64 = depth_hist.values().sum();
    let deep: u64 = depth_hist.iter().filter(|(d, _)| **d >= 50).map(|(_, c)| c).sum();
    let very_deep: u64 = depth_hist.iter().filter(|(d, _)| **d >= 100).map(|(_, c)| c).sum();
    let truly_deep: u64 = depth_hist.iter().filter(|(d, _)| **d >= 150).map(|(_, c)| c).sum();
    eprintln!("of {} observed wipeouts: depth >= 50 = {} ({:.1}%), >= 100 = {} ({:.1}%), >= 150 = {} ({:.1}%)",
        total, deep, 100.0 * deep as f64 / total.max(1) as f64,
        very_deep, 100.0 * very_deep as f64 / total.max(1) as f64,
        truly_deep, 100.0 * truly_deep as f64 / total.max(1) as f64);

    // EV-of-no-good signal:
    // - If wipeouts predominantly at depth 50-100: many small no-goods to learn.
    // - If wipeouts predominantly at depth 150+: each no-good is huge; learning expensive.
    // - If # wipeouts >> # backtracks * 10: lots of internal AC-3 failures per backtrack.
    let bt_to_wipe = if bt_count > 0 { final_wipeouts as f64 / bt_count as f64 } else { 0.0 };
    eprintln!();
    eprintln!("wipeouts / backtracks = {:.2}", bt_to_wipe);
    eprintln!("(high = each backtrack involves multiple AC-3 failures; potential no-good source)");
}
