// Vol-56 T3b — measure REPETITION of sub-assignments at wipeout time.
//
// Goal: distinguish "46k unique deep partials all fail once" from
// "5k distinct partial prefixes each fail multiple times". The latter
// makes no-good learning powerful; the former makes it useless.
//
// Method: rebuild the current placement from ValueTried / Backtrack
// event stream. On each DomainWipeout, hash the current cell-set
// (positions only — we hypothesize that *which cells are filled*
// matters more than *which piece-rotation* fills each, for clause
// minimisation potential).
//
// Two hashes per wipeout:
//   H_pos: hash of the SET of currently-placed positions.
//   H_full: hash of the SORTED LIST of (pos, piece_id, rotation).
//
// Report top-K most common hashes by frequency.

use std::collections::HashMap;
use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_events::{BufferSink, EventBody};
use eternity2_solver_engine::{load_edge_bp_marginals, EngineSolver};
use eternity2_solver_trait::{SolveOpts, Solver};

fn hash_u64(slice: &[u64]) -> u64 {
    use std::hash::Hasher;
    let mut h = std::collections::hash_map::DefaultHasher::new();
    for v in slice { h.write_u64(*v); }
    use std::hash::Hash;
    slice.len().hash(&mut h);
    h.finish()
}

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

    // Replay event stream rebuilding placement state. Each ValueTried adds
    // to a stack; each Backtrack(to_depth) truncates the stack to that depth.
    // Each DomainWipeout sample the current stack.
    //
    // CAVEAT: ValueTried events emit only when the engine has *committed* to
    // a value (after AC-3 says ok). Wipeouts come during AC-3 of a tentative
    // ValueTried that's being checked. So the "placement state at wipeout"
    // is everything from previous ValueTrieds PLUS the current tentative
    // value that triggered the wipeout. The event sequence ordering is:
    // ValueTried -> (AC-3 propagates, hits wipeout) -> DomainWipeout.
    // So the stack at wipeout time includes the value that's about to be
    // rejected. That's actually the right thing — it's the failing sub-
    // assignment.

    let mut stack: Vec<(u32, u32, u8)> = Vec::new(); // (pos, piece_id, rot)
    let mut prev_depth: u32 = 0;
    let mut pos_hash_counts: HashMap<u64, u64> = HashMap::new();
    let mut full_hash_counts: HashMap<u64, u64> = HashMap::new();
    let mut wipe_count: u64 = 0;
    let mut size_at_wipeout: Vec<usize> = Vec::new();

    for ev in &sink.events {
        let d = ev.depth;
        match &ev.body {
            EventBody::ValueTried { position, piece_id, rotation } => {
                // truncate stack to depth d, then push
                if d == 0 {
                    stack.clear();
                } else if (d as usize) < stack.len() {
                    stack.truncate(d as usize);
                }
                stack.push((u32::from(*position), u32::from(*piece_id), rotation.as_u8()));
                prev_depth = d;
            }
            EventBody::Backtrack { to_depth, .. } => {
                if (*to_depth as usize) < stack.len() {
                    stack.truncate(*to_depth as usize);
                }
                prev_depth = *to_depth;
            }
            EventBody::DomainWipeout { .. } => {
                wipe_count += 1;
                // hash position-set (sorted)
                let mut positions: Vec<u32> = stack.iter().map(|t| t.0).collect();
                positions.sort();
                let pos_h = hash_u64(&positions.iter().map(|&x| x as u64).collect::<Vec<_>>());
                *pos_hash_counts.entry(pos_h).or_insert(0) += 1;
                // hash (pos, pid, rot) sorted
                let mut full: Vec<(u32, u32, u8)> = stack.clone();
                full.sort();
                let full_v: Vec<u64> = full.iter().flat_map(|(a, b, c)| {
                    vec![*a as u64, *b as u64, *c as u64]
                }).collect();
                let full_h = hash_u64(&full_v);
                *full_hash_counts.entry(full_h).or_insert(0) += 1;
                size_at_wipeout.push(stack.len());
            }
            _ => {}
        }
    }

    eprintln!("elapsed_ms = {}", elapsed_ms);
    eprintln!("wipeouts (event-stream) = {}", wipe_count);
    eprintln!("distinct position-set hashes  = {}", pos_hash_counts.len());
    eprintln!("distinct full (p,pid,rot) hashes = {}", full_hash_counts.len());
    eprintln!();
    // Repetition factor
    if pos_hash_counts.len() > 0 {
        let avg_per_pos = wipe_count as f64 / pos_hash_counts.len() as f64;
        eprintln!("avg wipeouts per pos-set hash = {:.2}", avg_per_pos);
    }
    if full_hash_counts.len() > 0 {
        let avg_per_full = wipe_count as f64 / full_hash_counts.len() as f64;
        eprintln!("avg wipeouts per full hash    = {:.2}", avg_per_full);
    }
    eprintln!();
    // Top 10 most repeated
    let mut by_count: Vec<(&u64, &u64)> = pos_hash_counts.iter().collect();
    by_count.sort_by(|a, b| b.1.cmp(a.1));
    eprintln!("Top 10 most-repeated position-set hashes:");
    for (h, c) in by_count.iter().take(10) {
        eprintln!("  {:016x}: {} wipeouts", h, c);
    }
    eprintln!();
    let mut by_count_full: Vec<(&u64, &u64)> = full_hash_counts.iter().collect();
    by_count_full.sort_by(|a, b| b.1.cmp(a.1));
    eprintln!("Top 10 most-repeated FULL hashes:");
    for (h, c) in by_count_full.iter().take(10) {
        eprintln!("  {:016x}: {} wipeouts", h, c);
    }

    // Histogram of repetition
    let mut rep_hist: HashMap<u64, u64> = HashMap::new();
    for c in pos_hash_counts.values() {
        *rep_hist.entry(*c).or_insert(0) += 1;
    }
    let mut rep_keys: Vec<&u64> = rep_hist.keys().collect();
    rep_keys.sort();
    eprintln!();
    eprintln!("Pos-set hash repetition distribution:");
    for k in rep_keys.iter().rev().take(20) {
        eprintln!("  {} repeats: {} unique hashes", k, rep_hist[k]);
    }

    // Distribution of stack size at wipeout
    if !size_at_wipeout.is_empty() {
        size_at_wipeout.sort();
        let n = size_at_wipeout.len();
        let median = size_at_wipeout[n / 2];
        let p10 = size_at_wipeout[n / 10];
        let p90 = size_at_wipeout[(9 * n) / 10];
        eprintln!();
        eprintln!("Stack-size at wipeout:  median={}, p10={}, p90={}, min={}, max={}",
            median, p10, p90, size_at_wipeout[0], size_at_wipeout[n-1]);
    }
}
