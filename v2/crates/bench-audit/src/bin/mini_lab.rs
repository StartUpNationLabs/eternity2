// Vol-218: BANDSAW 10×10 measurement driver (prereg M1-M4).
//
//   mini_lab --mode m1  --seed 101 --entries E.jsonl [--grid-n 20]
//   mini_lab --mode m23 --seed 101 --entries E.jsonl [--grid-n 20]
//   mini_lab --mode m4  --seed 101 --entries E.jsonl
//
// All modes emit TSV to stdout (one row per measurement unit) and
// loud per-entry progress to stderr. Single-threaded by design —
// instances are parallelized at the shell level (8 cores max).
//
// m1 : relax vs exact band counts, depth k=1..4, budgets b=0..3.
// m23: per-entry exact min-break — BANDSAW vs independent exhaustive
//      B&B (escalating break ceiling), plus join-size stats and the
//      relaxation gap at b* (counts at the achievable frontier).
// m4 : per-entry instrument values — relaxed floor, greedy label
//      (100 ms B&B), exact min-break (BANDSAW).

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::io::Write as _;
use std::path::PathBuf;

use eternity2_bench_audit::mini::{
    bandsaw, bb_min_break, endgame_band, exact_count, exact_count_pruned, hint_cells,
    relax_floor, relax_profile, tropical_suffix, Band, Mini,
};



fn load_entries(path: &PathBuf, n: usize) -> Vec<Vec<Option<(u16, u8)>>> {
    let raw = std::fs::read_to_string(path).expect("read entries");
    raw.lines()
        .filter(|l| !l.trim().is_empty())
        .map(|line| {
            let v: serde_json::Value = serde_json::from_str(line).expect("parse entry");
            let mut grid: Vec<Option<(u16, u8)>> = vec![None; n * n];
            for e in v["placement"].as_array().expect("placement") {
                let pos = e["pos"].as_u64().unwrap() as usize;
                grid[pos] = Some((
                    e["piece_id"].as_u64().unwrap() as u16,
                    e["rotation"].as_u64().unwrap() as u8,
                ));
            }
            grid
        })
        .collect()
}

fn sub_band<'a>(full: &Band<'a>, k: usize) -> Band<'a> {
    Band {
        mini: full.mini,
        r0: full.r0,
        k,
        frontier: full.frontier.clone(),
        pool: full.pool.clone(),
        forced: full
            .forced
            .iter()
            .filter(|&(&pos, _)| pos < (full.r0 + k) * full.mini.n)
            .map(|(&pos, &v)| (pos, v))
            .collect::<HashMap<_, _>>(),
    }
}

/// Independent exhaustive ground truth: iterative deepening on the
/// break ceiling, +1 from the admissible floor (a slack ceiling makes
/// the pre-completion tree explode — measured 600 s+ at 10×10 even
/// for near-canonical entries). Never seeded by BANDSAW's answer.
/// budget_ms bounds the TOTAL across rounds.
fn bb_ground_truth(
    band: &Band,
    start: u32,
    budget_ms: u64,
    node_cap: u64,
    suffix: &[Vec<u32>],
) -> (Option<u32>, u64, u128, bool) {
    let mut ceil = start;
    let mut nodes = 0u64;
    let mut ms = 0u128;
    loop {
        let remaining = budget_ms.saturating_sub(u64::try_from(ms).unwrap_or(u64::MAX));
        if remaining == 0 {
            return (None, nodes, ms, true);
        }
        let r = bb_min_break(band, ceil, remaining, node_cap, Some(suffix));
        nodes += r.nodes;
        ms += r.elapsed_ms;
        if r.capped {
            return (r.best, nodes, ms, true);
        }
        if let Some(b) = r.best {
            return (Some(b), nodes, ms, false);
        }
        if ceil >= 64 {
            return (None, nodes, ms, false);
        }
        ceil += 1;
    }
}

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut size = 10usize;
    let mut colors = 8u32;
    let mut seed = 101u64;
    let mut rows = 6usize;
    let mut mode = String::from("m23");
    let mut entries_path = PathBuf::new();
    let mut grid_n = 20usize;
    let mut bb_budget_ms = 600_000u64;
    let mut node_cap: u64 = 4_000_000_000;
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--size" => { size = raw[i + 1].parse().unwrap(); i += 2; }
            "--colors" => { colors = raw[i + 1].parse().unwrap(); i += 2; }
            "--seed" => { seed = raw[i + 1].parse().unwrap(); i += 2; }
            "--rows" => { rows = raw[i + 1].parse().unwrap(); i += 2; }
            "--mode" => { mode = raw[i + 1].clone(); i += 2; }
            "--entries" => { entries_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--grid-n" => { grid_n = raw[i + 1].parse().unwrap(); i += 2; }
            "--bb-budget-ms" => { bb_budget_ms = raw[i + 1].parse().unwrap(); i += 2; }
            "--node-cap" => { node_cap = raw[i + 1].parse().unwrap(); i += 2; }
            other => panic!("unknown arg {other}"),
        }
    }
    let m = Mini::from_seed(size, colors, seed, &hint_cells(size));
    let entries = if mode == "m2ladder" {
        Vec::new()
    } else {
        load_entries(&entries_path, m.n)
    };
    eprintln!("[mini_lab] seed={seed} mode={mode} entries={}", entries.len());

    match mode.as_str() {
        "m2ladder" => {
            // M2 exactness gate on a CONTROLLED b*-graded family:
            // canonical prefix with j frontier columns corrupted
            // (j = 0..6) — bandsaw must equal the independent
            // iterative-deepening B&B on every rung, every instance.
            const COLS: [usize; 6] = [1, 4, 7, 2, 5, 8];
            println!("seed\tncorrupt\tfloor\tsaw_best\tbb_best\tmatch\tsaw_ms\tbb_ms\tsaw_capped\tbb_capped");
            for ncorrupt in 0..=6usize {
                let n = m.n;
                let mut grid: Vec<Option<(u16, u8)>> = vec![None; n * n];
                for pos in 0..rows * n {
                    grid[pos] = Some(m.solution[pos]);
                }
                let mut band = endgame_band(&m, &grid, rows);
                let mut f = band.frontier.clone().unwrap();
                for &col in COLS.iter().take(ncorrupt) {
                    f[col] = if f[col] == 1 { 2 } else { 1 };
                }
                band.frontier = Some(f);
                let sfx = tropical_suffix(&band);
                let floor = relax_floor(&band, 8);
                let saw = bandsaw(&band, floor, node_cap);
                let (bb_best, _bn, bb_ms2, bb_capped) =
                    bb_ground_truth(&band, floor, bb_budget_ms, node_cap, &sfx);
                let matched = match (saw.best, bb_best) {
                    (Some(a), Some(b)) => u8::from(a == b),
                    _ => 0,
                };
                println!(
                    "{seed}\t{ncorrupt}\t{floor}\t{}\t{}\t{matched}\t{}\t{bb_ms2}\t{}\t{}",
                    saw.best.map_or(-1, |x| i64::from(x)),
                    bb_best.map_or(-1, |x| i64::from(x)),
                    saw.elapsed_ms,
                    u8::from(saw.capped),
                    u8::from(bb_capped),
                );
                std::io::stdout().flush().unwrap();
                eprintln!(
                    "[m2ladder] ncorrupt {ncorrupt}: floor {floor} saw {:?} bb {bb_best:?}",
                    saw.best
                );
            }
        }
        "m1" => {
            println!("seed\tidx\tk\tb\trelax_cum\texact_cum\texact_capped");
            for (idx, grid) in entries.iter().take(grid_n).enumerate() {
                let full = endgame_band(&m, grid, rows);
                for k in 1..=full.k {
                    let band = sub_band(&full, k);
                    let bmax = 3u32;
                    let relax = relax_profile(&band, bmax);
                    let exact = exact_count(&band, bmax, node_cap);
                    let mut rc = 0.0f64;
                    let mut ec = 0u64;
                    for b in 0..=bmax as usize {
                        rc += relax[b];
                        ec += exact.by_b[b];
                        println!(
                            "{seed}\t{idx}\t{k}\t{b}\t{rc:.6e}\t{ec}\t{}",
                            u8::from(exact.capped)
                        );
                    }
                }
                eprintln!("[m1] idx {idx} done");
            }
        }
        "m23" => {
            println!("seed\tidx\tfloor\tsaw_best\tsaw_ub\tsaw_lb\tsaw_budget\tsaw_capped\tbb_best\tbb_capped\tmatch\ttop_raw\tbottom_raw\ttop_keys\tbottom_keys\tmask_groups\tjoin_pairs\tsaw_ms\tbb_nodes\tbb_ms\texact_at_bstar\texact_capped\trelax_at_bstar");
            for (idx, grid) in entries.iter().take(grid_n).enumerate() {
                let band = endgame_band(&m, grid, rows);
                let sfx = tropical_suffix(&band);
                let floor = relax_floor(&band, 8);
                assert_eq!(*sfx[0].iter().min().unwrap(), floor, "suffix floor != relax floor");
                eprintln!("[m23] idx {idx}: floor {floor}, saw...");
                let saw = bandsaw(&band, floor, node_cap);
                eprintln!(
                    "[m23] idx {idx}: saw {:?} (B={}, {} ms), bb...",
                    saw.best, saw.final_budget, saw.elapsed_ms
                );
                let (bb_best, bb_nodes, bb_ms, bb_capped) =
                    bb_ground_truth(&band, floor, bb_budget_ms, node_cap, &sfx);
                let matched = match (saw.best, bb_best) {
                    (Some(a), Some(b)) => u8::from(a == b),
                    _ => 0,
                };
                // relaxation gap at the achievable frontier b*
                let (mut exact_b, mut exact_capped, mut relax_b) = (0u64, 0u8, 0.0f64);
                if let Some(bstar) = saw.best {
                    let ec = exact_count_pruned(&band, bstar, node_cap, Some(&sfx));
                    exact_b = ec.by_b.iter().sum();
                    exact_capped = u8::from(ec.capped);
                    relax_b = relax_profile(&band, bstar).iter().sum();
                }
                println!(
                    "{seed}\t{idx}\t{floor}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{matched}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{bb_nodes}\t{bb_ms}\t{exact_b}\t{exact_capped}\t{relax_b:.6e}",
                    saw.best.map_or(-1, |x| i64::from(x)),
                    saw.upper.map_or(-1, |x| i64::from(x)),
                    saw.lb,
                    saw.final_budget,
                    u8::from(saw.capped),
                    bb_best.map_or(-1, |x| i64::from(x)),
                    u8::from(bb_capped),
                    saw.top_raw,
                    saw.bottom_raw,
                    saw.top_keys,
                    saw.bottom_keys,
                    saw.bottom_mask_groups,
                    saw.join_pairs,
                    saw.elapsed_ms,
                );
                std::io::stdout().flush().unwrap();
                eprintln!(
                    "[m23] idx {idx}: floor {floor} saw {:?} bb {:?} match {matched}",
                    saw.best, bb_best
                );
            }
        }
        "m4" => {
            println!("seed\tidx\tfloor\tgreedy\texact\tsaw_ub\tsaw_lb\tsaw_capped");
            for (idx, grid) in entries.iter().enumerate() {
                let band = endgame_band(&m, grid, rows);
                let sfx = tropical_suffix(&band);
                let floor = relax_floor(&band, 8);
                let greedy = bb_min_break(&band, 64, 100, node_cap, Some(&sfx));
                let saw = bandsaw(&band, floor, node_cap);
                println!(
                    "{seed}\t{idx}\t{floor}\t{}\t{}\t{}\t{}\t{}",
                    greedy.best.map_or(-1, |x| i64::from(x)),
                    saw.best.map_or(-1, |x| i64::from(x)),
                    saw.upper.map_or(-1, |x| i64::from(x)),
                    saw.lb,
                    u8::from(saw.capped)
                );
                std::io::stdout().flush().unwrap();
                if idx % 20 == 0 {
                    eprintln!("[m4] idx {idx} done");
                }
            }
        }
        other => panic!("unknown mode {other}"),
    }
}
