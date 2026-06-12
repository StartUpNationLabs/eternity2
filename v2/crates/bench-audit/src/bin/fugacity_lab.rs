// Vol-218 side gate, validation leg: does the equal-case fugacity
// correction (vol-216) repair the measured 10×10 relaxation gap?
// Ground truth: exact distinct-piece counts at b* from the m23 grid.
//
//   fugacity_lab --seed 104 --entries E.jsonl --m23 m23_104.tsv \
//     [--max-entries 5]
//
// Emits per-entry: b*, exact ln N(<=b*), naive ln, corrected ln,
// saddle diagnostics. Only entries whose exact count was uncapped.

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_bench_audit::mini::{
    bb_min_break, endgame_band, exact_count_pruned, fugacity_corrected_lncount, hint_cells,
    tropical_suffix, Band, Mini,
};

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut size = 10usize;
    let mut colors = 8u32;
    let mut seed = 104u64;
    let mut rows = 6usize;
    let mut entries_path = PathBuf::new();
    let mut m23_path = PathBuf::new();
    let mut max_entries = 5usize;
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--size" => { size = raw[i + 1].parse().unwrap(); i += 2; }
            "--colors" => { colors = raw[i + 1].parse().unwrap(); i += 2; }
            "--seed" => { seed = raw[i + 1].parse().unwrap(); i += 2; }
            "--rows" => { rows = raw[i + 1].parse().unwrap(); i += 2; }
            "--entries" => { entries_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--m23" => { m23_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--max-entries" => { max_entries = raw[i + 1].parse().unwrap(); i += 2; }
            other => panic!("unknown arg {other}"),
        }
    }
    let m = Mini::from_seed(size, colors, seed, &hint_cells(size));

    if entries_path.as_os_str().is_empty() {
        // LADDER mode: canonical-prefix corruption family — b* known
        // exactly (suffix-pruned ID-B&B), exact counts cheap. The
        // equal-case fugacity validation set the blind entries can't
        // provide (vol-218 M3: no blind b* decidable).
        const COLS: [usize; 6] = [1, 4, 7, 2, 5, 8];
        println!("seed\tncorrupt\tbstar\texact_ln\tnaive_ln\tcorr_ln\titers\tusage_err");
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
            let floor = *sfx[0].iter().min().unwrap();
            let mut ceil = floor;
            let bstar = loop {
                let r = bb_min_break(&band, ceil, 600_000, u64::MAX, Some(&sfx));
                assert!(!r.capped, "ladder bb must exhaust");
                if let Some(b) = r.best {
                    break b;
                }
                ceil += 1;
            };
            let ec = exact_count_pruned(&band, bstar, u64::MAX, Some(&sfx));
            assert!(!ec.capped);
            let exact: u64 = ec.by_b.iter().sum();
            let t0 = std::time::Instant::now();
            let r = fugacity_corrected_lncount(&band, bstar, 0.02, 40);
            #[allow(clippy::cast_precision_loss)]
            let exact_ln = (exact as f64).ln();
            println!(
                "{seed}\t{ncorrupt}\t{bstar}\t{exact_ln:.4}\t{:.4}\t{:.4}\t{}\t{:.4}",
                r.ln_naive, r.ln_corrected, r.iters, r.max_usage_err
            );
            eprintln!(
                "[fug-ladder] ncorrupt {ncorrupt}: b*={bstar} exact_ln={exact_ln:.2} naive={:.2} corr={:.2} ({} iters, {:.0} s)",
                r.ln_naive, r.ln_corrected, r.iters, t0.elapsed().as_secs_f64()
            );
        }
        return;
    }

    // entries
    let raw_entries = std::fs::read_to_string(&entries_path).expect("entries");
    let grids: Vec<Vec<Option<(u16, u8)>>> = raw_entries
        .lines()
        .filter(|l| !l.trim().is_empty())
        .map(|line| {
            let v: serde_json::Value = serde_json::from_str(line).unwrap();
            let mut grid = vec![None; m.n * m.n];
            for e in v["placement"].as_array().unwrap() {
                let pos = e["pos"].as_u64().unwrap() as usize;
                grid[pos] = Some((
                    e["piece_id"].as_u64().unwrap() as u16,
                    e["rotation"].as_u64().unwrap() as u8,
                ));
            }
            grid
        })
        .collect();

    // m23 rows: idx -> (saw_best/bb_best as bstar, exact_at_bstar, exact_capped)
    let m23 = std::fs::read_to_string(&m23_path).expect("m23 tsv");
    let mut header: Vec<String> = Vec::new();
    println!("seed\tidx\tbstar\texact_ln\tnaive_ln\tcorr_ln\titers\tusage_err");
    let mut done = 0usize;
    for line in m23.lines() {
        let p: Vec<&str> = line.trim_end().split('\t').collect();
        if p.is_empty() {
            continue;
        }
        if p[0] == "seed" {
            header = p.iter().map(|s| (*s).to_string()).collect();
            continue;
        }
        let col = |name: &str| -> Option<usize> { header.iter().position(|h| h == name) };
        let idx: usize = p[col("idx").unwrap()].parse().unwrap();
        let saw_best: i64 = p[col("saw_best").unwrap()].parse().unwrap();
        let exact_at: u64 = p[col("exact_at_bstar").unwrap()].parse().unwrap();
        let exact_capped: u8 = p[col("exact_capped").unwrap()].parse().unwrap();
        if saw_best < 0 || exact_capped != 0 || exact_at == 0 {
            continue;
        }
        let bstar = u32::try_from(saw_best).unwrap();
        let band = endgame_band(&m, &grids[idx], rows);
        let t0 = std::time::Instant::now();
        let r = fugacity_corrected_lncount(&band, bstar, 0.02, 40);
        #[allow(clippy::cast_precision_loss)]
        let exact_ln = (exact_at as f64).ln();
        println!(
            "{seed}\t{idx}\t{bstar}\t{exact_ln:.4}\t{:.4}\t{:.4}\t{}\t{:.4}",
            r.ln_naive, r.ln_corrected, r.iters, r.max_usage_err
        );
        eprintln!(
            "[fug] idx {idx}: b*={bstar} exact_ln={exact_ln:.2} naive={:.2} corr={:.2} ({} iters, {:.0} s)",
            r.ln_naive,
            r.ln_corrected,
            r.iters,
            t0.elapsed().as_secs_f64()
        );
        done += 1;
        if done >= max_entries {
            break;
        }
    }
    eprintln!("[fug] scored {done} entries");
}
