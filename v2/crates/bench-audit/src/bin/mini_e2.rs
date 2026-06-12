// Vol-218: tropical-suffix + ID-B&B portability smoke on the REAL
// 16×16 stage-4 endgame (rows 12-15, 64-piece pool, row-13 hints).
// Per entry: relax floor (k=4), suffix floor (must agree), certified
// LB ladder (ID-bb, per-rung wall budget), and a 1.5 s greedy label
// (column-major + suffix; comparable to stage4_finish's 1.5 s label).
//
//   mini_e2 --entry BOARD.json [--rung-ms 15000] [--label-ms 1500]

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_bench_audit::mini::{
    bb_min_break, endgame_band, relax_floor, tropical_suffix, Mini,
};
use eternity2_benchmark::loader::load_puzzle_with_hints;

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut entry_path = PathBuf::new();
    let mut rung_ms = 15_000u64;
    let mut label_ms = 1_500u64;
    let mut max_lb_rungs = 40u32;
    let mut profile_check = false;
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--entry" => { entry_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--rung-ms" => { rung_ms = raw[i + 1].parse().unwrap(); i += 2; }
            "--label-ms" => { label_ms = raw[i + 1].parse().unwrap(); i += 2; }
            "--max-lb-rungs" => { max_lb_rungs = raw[i + 1].parse().unwrap(); i += 2; }
            // counting-profile floor cross-check (30 s at 16×16; the
            // suffix floor is the same number in ~1.7 s)
            "--profile-check" => { profile_check = true; i += 1; }
            other => panic!("unknown arg {other}"),
        }
    }
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("puzzle");
    let hv: Vec<(usize, u16, u8)> = hints
        .hints
        .iter()
        .map(|h| (h.position as usize, h.piece_id, h.rotation.as_u8()))
        .collect();
    let m = Mini::from_puzzle(&puzzle, hv);
    let n = m.n;

    let v: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&entry_path).expect("read entry"))
            .expect("parse entry");
    let mut grid: Vec<Option<(u16, u8)>> = vec![None; n * n];
    for (idx, e) in v["placement"].as_array().expect("placement").iter().enumerate() {
        if e.is_null() {
            continue;
        }
        let pos = e.get("pos").and_then(|p| p.as_u64()).unwrap_or(idx as u64) as usize;
        if pos < 12 * n {
            grid[pos] = Some((
                e["piece_id"].as_u64().unwrap() as u16,
                e["rotation"].as_u64().unwrap() as u8,
            ));
        }
    }
    let band = endgame_band(&m, &grid, 12);

    let t0 = Instant::now();
    let sfx = tropical_suffix(&band);
    let sfx_ms = t0.elapsed().as_millis();
    let sfx_floor = *sfx[0].iter().min().unwrap();
    let rfloor = if profile_check {
        let t1 = Instant::now();
        let rf = relax_floor(&band, 8);
        assert_eq!(sfx_floor, rf, "suffix floor != relax floor on E2");
        eprintln!("[e2] profile cross-check OK ({} ms)", t1.elapsed().as_millis());
        rf
    } else {
        sfx_floor
    };
    eprintln!("[e2] floor {rfloor} (suffix {sfx_ms} ms)");

    // greedy label: anytime bb at label_ms, generous ceiling
    let label = bb_min_break(&band, 64, label_ms, u64::MAX, Some(&sfx));
    eprintln!(
        "[e2] greedy label {:?} ({} nodes, {} ms)",
        label.best, label.nodes, label.elapsed_ms
    );

    // certified LB ladder: ID rounds, each must EXHAUST within rung_ms
    let mut lb = rfloor; // b* >= floor certified by the relaxation
    let mut ub: Option<u32> = label.best;
    let mut rung = rfloor;
    let mut rung_results: Vec<String> = Vec::new();
    for _ in 0..max_lb_rungs {
        let r = bb_min_break(&band, rung, rung_ms, u64::MAX, Some(&sfx));
        if r.capped {
            rung_results.push(format!("rung {rung}: CAPPED ({} nodes, {} ms)", r.nodes, r.elapsed_ms));
            break;
        }
        match r.best {
            Some(b) => {
                // exhausted with a completion: b* == b proven
                lb = b;
                ub = Some(ub.map_or(b, |u| u.min(b)));
                rung_results.push(format!("rung {rung}: SOLVED b*={b} ({} ms)", r.elapsed_ms));
                break;
            }
            None => {
                // exhausted, no completion <= rung: b* > rung
                lb = rung + 1;
                rung_results.push(format!("rung {rung}: certified b*>{rung} ({} nodes, {} ms)", r.nodes, r.elapsed_ms));
                rung += 1;
            }
        }
    }
    for s in &rung_results {
        eprintln!("[e2] {s}");
    }
    println!(
        "{{\"entry\":\"{}\",\"relax_floor\":{rfloor},\"certified_lb\":{lb},\"greedy_label\":{},\"bracket\":\"[{lb},{}]\"}}",
        entry_path.file_stem().unwrap().to_string_lossy(),
        ub.map_or(-1, |x| i64::from(x)),
        ub.map_or(-1, |x| i64::from(x)),
    );
}
