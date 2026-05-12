// Vol-14: dump the per-cell domain size AFTER applying canonical
// hints + initial propagation (gacolor + AC-3), BEFORE search starts.
//
// Answers: "If we placed each cell first, how many candidates would
// we face?" — the *intrinsic* per-cell difficulty given only the
// puzzle structure + hints, decoupled from search order.
//
// This is what the user is implicitly asking about: is the deep
// center actually easy on the empty board (with hints), or only
// easy AFTER the search has already filled in the surrounding cells?

use std::path::PathBuf;

use eternity2_bench_audit as _;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveMode, Solver};

const W: u32 = 16;
const H: u32 = 16;

fn cell_layer(pos: u32) -> u32 {
    let x = pos % W;
    let y = pos / W;
    let dx = std::cmp::min(x, W - 1 - x);
    let dy = std::cmp::min(y, H - 1 - y);
    std::cmp::min(dx, dy)
}

fn cell_class(pos: u32) -> &'static str {
    let x = pos % W;
    let y = pos / W;
    let is_corner = (x == 0 || x == W-1) && (y == 0 || y == H-1);
    let is_border = x == 0 || x == W-1 || y == 0 || y == H-1;
    if is_corner { "corner" }
    else if is_border { "border" }
    else { "interior" }
}

struct CaptureSink {
    captured_initial_domains: Vec<u32>,
    final_stats: Option<FinalStats>,
}
impl CaptureSink {
    fn new() -> Self { Self { captured_initial_domains: Vec::new(), final_stats: None } }
}
impl EventSink for CaptureSink {
    fn emit(&mut self, event: SolverEvent) {
        if let EventBody::Started { .. } = &event.body {
            // engine hasn't computed domains yet
        }
        if let EventBody::VariableSelected { domain_size, .. } = &event.body {
            // The FIRST VariableSelected event is at depth 0 — captures
            // the actually-selected cell's domain, not all cells.
            // We can't get all cells from sink directly, so the capture
            // is limited; we want per-cell domain. Workaround: use
            // mode=AllSolutions but never recurse — but that's what
            // we'll do via a hack.
            self.captured_initial_domains.push(*domain_size);
        }
        match event.body {
            EventBody::Solved { final_stats, .. }
            | EventBody::Exhausted { final_stats, .. }
            | EventBody::TimedOut { final_stats, .. }
            | EventBody::Cancelled { final_stats, .. } => {
                self.final_stats = Some(final_stats);
            }
            _ => {}
        }
    }
}

fn main() {
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    eprintln!("loaded {}x{} puzzle, {} hints", puzzle.width, puzzle.height, hints.hints.len());

    // Strategy: use AllSolutions mode with a 1-second budget.
    // The engine will explore extensively; the VariableSelected events
    // emitted at depth 0 across many backtracks will collectively reveal
    // the domain sizes at depth 0 for every cell that gets picked.
    // BUT we need ONE specific cell's domain at root — across all sibling
    // branches the same cell at depth 0 is always the same.
    //
    // Better: instrument the engine directly to dump initial domains.
    // For now, simpler: run a 100-ms search to many depths and we'll
    // collect the depth-0 domain sizes (always for whichever cell MRV
    // picks at root). Then we'll INFER the others by analytic argument.
    //
    // Actually the cleanest experiment: for each of the 256 cells,
    // explicitly force the engine to pick that cell first via path-prefix.
    // Then read the domain size from the first VariableSelected event.

    let mut report_rows: Vec<(u32, u32, &'static str, u32)> = Vec::new();

    for pos in 0..puzzle.cell_count() {
        // Skip hint cells: they're forced to domain 1.
        if hints.hints.iter().any(|h| h.position == pos) {
            report_rows.push((pos, cell_layer(pos), cell_class(pos), 1));
            continue;
        }
        // Build a path that picks `pos` first.
        let mut opts = SolveOpts::default();
        opts.mode = SolveMode::AllSolutions;  // doesn't matter, we'll time out
        opts.time_budget_ms = 50;  // very short, just need the first event
        opts.seed = 1;
        opts.hints = hints.clone();
        opts.path = vec![pos];
        opts.path_policy = eternity2_core::PathPolicy::PrefixConstraint { k: 1 };

        // Use the simplest single-thread profile with full propagation.
        let mut solver = EngineSolver::gacolor_ac3();
        let mut sink = CaptureSink::new();
        let _ = solver.solve(&puzzle, &opts, &mut sink);
        // The first VariableSelected event is the domain at this cell
        // (with only canonical hints applied + their propagation).
        let d = sink.captured_initial_domains.first().copied().unwrap_or(0);
        report_rows.push((pos, cell_layer(pos), cell_class(pos), d));
    }

    // Aggregate
    use std::collections::BTreeMap;
    let mut by_layer: BTreeMap<u32, Vec<u32>> = BTreeMap::new();
    let mut by_class: BTreeMap<&'static str, Vec<u32>> = BTreeMap::new();
    for (_pos, layer, class, d) in &report_rows {
        by_layer.entry(*layer).or_default().push(*d);
        by_class.entry(class).or_default().push(*d);
    }

    println!("=== Initial domain sizes (after hints + propagation, no search) ===\n");
    println!("By layer (Chebyshev distance from edge):");
    println!("{:>5} {:>6} {:>10} {:>10} {:>10} {:>10} {:>10}",
        "layer", "cells", "min", "median", "mean", "max", "total");
    for (layer, ds) in &by_layer {
        let mut ds = ds.clone();
        ds.sort();
        let min = *ds.first().unwrap();
        let max = *ds.last().unwrap();
        let median = ds[ds.len()/2];
        let sum: u64 = ds.iter().map(|&x| x as u64).sum();
        let mean = sum as f64 / ds.len() as f64;
        println!("{:>5} {:>6} {:>10} {:>10} {:>10.1} {:>10} {:>10}",
            layer, ds.len(), min, median, mean, max, sum);
    }
    println!("\nBy cell class:");
    println!("{:>10} {:>6} {:>10} {:>10} {:>10} {:>10} {:>10}",
        "class", "cells", "min", "median", "mean", "max", "total");
    for (class, ds) in &by_class {
        let mut ds = ds.clone();
        ds.sort();
        let min = *ds.first().unwrap();
        let max = *ds.last().unwrap();
        let median = ds[ds.len()/2];
        let sum: u64 = ds.iter().map(|&x| x as u64).sum();
        let mean = sum as f64 / ds.len() as f64;
        println!("{:>10} {:>6} {:>10} {:>10} {:>10.1} {:>10} {:>10}",
            class, ds.len(), min, median, mean, max, sum);
    }

    // Visualize as a 16x16 grid
    println!("\n=== Domain-size map (16x16) ===");
    for y in 0..H {
        let mut row = String::new();
        for x in 0..W {
            let pos = y*W + x;
            let entry = report_rows.iter().find(|(p, _, _, _)| *p == pos).unwrap();
            row.push_str(&format!("{:>4} ", entry.3));
        }
        println!("{}", row);
    }

    // Save
    let run_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let out_dir = PathBuf::from(format!("output/v14_initial_domains/run_{run_id}"));
    std::fs::create_dir_all(&out_dir).expect("mkdir");
    let report = serde_json::json!({
        "rows": report_rows.iter().map(|(p, l, c, d)| serde_json::json!({
            "pos": p, "x": p % W, "y": p / W, "layer": l, "class": c, "domain": d
        })).collect::<Vec<_>>(),
    });
    let path = out_dir.join("report.json");
    std::fs::write(&path, serde_json::to_string_pretty(&report).unwrap()).expect("write");
    eprintln!("\nfull report: {}", path.display());
}
