// cloister2 — vol-212 CLOISTER-II driver.
//
// Free-rim (no --frame): the vol-211 standalone interior modes.
// Border-anchored (--frame <file|dir>): a fixed perfect ring turns the 56
// IB edges into real constraints from cell 1; the break-DFS anytime-
// minimizes total breaks over the 420 interior-touching edges.
// Record condition (perfect frame): total = 480 − breaks ≥ 461 with 5/5
// hints ⇒ strict-canonical record.
//
// Modes: dfs | sa | hybrid | tail2polish.
// Output: timestamped dir under --out-root (default output/vol-212),
// summary.tsv (one row per frame×seed), per-job board JSON + .url.txt,
// appended rows in the global cloister history CSV.

#![forbid(unsafe_code)]

use std::io::Write as _;
use std::path::{Path, PathBuf};

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_cloister::dfs::{dfs_run, DfsParams, Scan};
use eternity2_cloister::endgame::exact_tail2;
use eternity2_cloister::frame::Frame;
use eternity2_cloister::io as cio;
use eternity2_cloister::model::{InteriorModel, RimTargets, Tables};
use eternity2_cloister::sa::{greedy_complete, sa_run, SaParams};
use eternity2_cloister::verify;
use eternity2_cloister::frame;
use rayon::prelude::*;

struct JobOut {
    frame_label: String,
    frame_idx: usize,
    seed: u64,
    max_depth: usize,
    nodes: u64,
    epochs: u64,
    completes: u64,
    /// (canonical interior grid, breaks) if complete
    complete: Option<(Vec<(u16, u8)>, u32)>,
    sa_pair: Option<(u32, u32)>,
    ms_at_max: u128,
}

#[allow(clippy::too_many_lines)]
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let get = |flag: &str| -> Option<String> {
        args.iter()
            .position(|a| a == flag)
            .and_then(|i| args.get(i + 1).cloned())
    };
    let has = |flag: &str| args.iter().any(|a| a == flag);

    let mode = get("--mode").unwrap_or_else(|| "dfs".into());
    let seeds: u64 = get("--seeds").and_then(|s| s.parse().ok()).unwrap_or(8);
    let seed0: u64 = get("--seed0").and_then(|s| s.parse().ok()).unwrap_or(1);
    let budget_ms: u64 = get("--budget-ms").and_then(|s| s.parse().ok()).unwrap_or(30_000);
    let restart_ms: u64 = get("--restart-ms").and_then(|s| s.parse().ok()).unwrap_or(5_000);
    let hinted = has("--hints");
    let threads: usize = get("--threads").and_then(|s| s.parse().ok()).unwrap_or(8);
    let exact_tail_k: usize = get("--exact-tail").and_then(|s| s.parse().ok()).unwrap_or(8);
    let tail2 = has("--tail2");
    let tail2_cap: u64 = get("--tail2-cap").and_then(|s| s.parse().ok()).unwrap_or(30_000);
    let t0: f64 = get("--t0").and_then(|s| s.parse().ok()).unwrap_or(1.5);
    let max_disc: Option<u32> = get("--max-disc").and_then(|s| s.parse().ok());
    let scan = match get("--scan").as_deref() {
        Some("boustro") => Scan::Boustro,
        Some(s) if s.starts_with("seam:") => {
            Scan::Seam(s[5..].parse().expect("seam row"))
        }
        _ => Scan::RowMajor,
    };
    let dfs_ms: u64 = get("--dfs-ms")
        .and_then(|s| s.parse().ok())
        .unwrap_or_else(|| (budget_ms / 4).clamp(5_000, 60_000));
    let frame_limit: usize = get("--frame-limit").and_then(|s| s.parse().ok()).unwrap_or(usize::MAX);
    let frame_stride: usize = get("--frame-stride").and_then(|s| s.parse().ok()).unwrap_or(1);
    let out_root = get("--out-root").unwrap_or_else(|| "output/vol-212".into());
    let schedule: Vec<usize> = get("--break-schedule").map_or_else(
        || {
            let b: usize = get("--breaks").and_then(|s| s.parse().ok()).unwrap_or(0);
            (0..b)
                .map(|j| if b == 1 { 170 } else { 154 + j * 32 / (b - 1) })
                .collect()
        },
        |s| {
            let mut v: Vec<usize> = s
                .split(',')
                .map(|x| x.trim().parse().expect("schedule depth"))
                .collect();
            v.sort_unstable();
            v
        },
    );

    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .expect("rayon pool");

    let puzzle_path = PathBuf::from(
        get("--puzzle").unwrap_or_else(|| "../data/puzzles/size_16_official_eternity.csv".into()),
    );
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let model = InteriorModel::from_puzzle(&puzzle, &hints);

    // frames: none (free rim), a single file, or a directory to sweep
    let frames: Vec<Frame> = match get("--frame") {
        None => Vec::new(),
        Some(p) => {
            let path = PathBuf::from(&p);
            if path.is_dir() {
                let mut files: Vec<PathBuf> = std::fs::read_dir(&path)
                    .expect("frame dir")
                    .filter_map(|e| e.ok().map(|e| e.path()))
                    .filter(|p| p.extension().is_some_and(|e| e == "json"))
                    .collect();
                files.sort();
                files
                    .into_iter()
                    .step_by(frame_stride.max(1))
                    .take(frame_limit)
                    .filter_map(|f| match frame::load(&f, &puzzle) {
                        Ok(fr) => Some(fr),
                        Err(e) => {
                            eprintln!("skip frame {}: {e}", f.display());
                            None
                        }
                    })
                    .collect()
            } else {
                vec![frame::load(&path, &puzzle).expect("load frame")]
            }
        }
    };
    let bordered = !frames.is_empty();
    for f in &frames {
        if f.bb < 60 {
            eprintln!("WARN: frame {} has BB={} (<60)", f.label, f.bb);
        }
    }

    let ts = cio::timestamp();
    let dir = PathBuf::from(format!("{out_root}/cloister2_{mode}_{ts}"));
    std::fs::create_dir_all(&dir).expect("mkdir");
    let mut summary = std::fs::File::create(dir.join("summary.tsv")).expect("summary");
    writeln!(
        summary,
        "frame\tseed\tmode\tscan\tmax_depth\tnodes\tepochs\tcompletes\tbreaks\tii\tib\tbb\ttotal\thints_ok\tms_at_max\tboard"
    )
    .expect("hdr");
    let params_str = format!(
        "budget_ms={budget_ms};hinted={hinted};sched={schedule:?};et={exact_tail_k};tail2={tail2};restart={restart_ms};scan={};disc={max_disc:?};dfs_ms={dfs_ms}",
        scan.name()
    );
    eprintln!(
        "cloister2 mode={mode} frames={} seeds={seeds} {params_str}",
        if bordered { frames.len().to_string() } else { "free-rim".into() }
    );

    // job grid: (frame index or none) × seed
    let frame_ids: Vec<Option<usize>> = if bordered {
        (0..frames.len()).map(Some).collect()
    } else {
        vec![None]
    };
    let jobs: Vec<(Option<usize>, u64)> = frame_ids
        .iter()
        .flat_map(|&fi| (seed0..seed0 + seeds).map(move |s| (fi, s)))
        .collect();

    let run_job = |&(fi, seed): &(Option<usize>, u64)| -> JobOut {
        let (targets, label, fidx): (Option<&RimTargets>, String, usize) = match fi {
            Some(i) => (Some(&frames[i].targets), frames[i].label.clone(), i),
            None => (None, "free".into(), usize::MAX),
        };
        match mode.as_str() {
            "dfs" => {
                let p = DfsParams {
                    seed,
                    budget_ms,
                    restart_ms,
                    hinted,
                    schedule: schedule.clone(),
                    exact_tail_k,
                    tail2,
                    tail2_cap,
                    max_disc,
                    scan,
                };
                let r = dfs_run(&model, targets, &p);
                JobOut {
                    frame_label: label,
                    frame_idx: fidx,
                    seed,
                    max_depth: r.max_depth,
                    nodes: r.nodes,
                    epochs: r.epochs,
                    completes: r.completes_found,
                    complete: r.complete,
                    sa_pair: None,
                    ms_at_max: r.ms_at_max,
                }
            }
            "sa" | "hybrid" => {
                let init: Option<Vec<(u16, u8)>> = if mode == "hybrid" {
                    let p = DfsParams {
                        seed,
                        budget_ms: dfs_ms,
                        restart_ms,
                        hinted,
                        schedule: schedule.clone(),
                        exact_tail_k,
                        tail2,
                        tail2_cap,
                        max_disc,
                        scan,
                    };
                    let r = dfs_run(&model, targets, &p);
                    Some(r.complete.map_or_else(
                        || {
                            let so = scan.order(model.n);
                            let prefix: Vec<(usize, (u16, u8))> = r
                                .best_prefix
                                .iter()
                                .enumerate()
                                .map(|(j, &pr)| (so[j], pr))
                                .collect();
                            greedy_complete(&model, targets, &prefix)
                        },
                        |(g, _)| g,
                    ))
                } else {
                    get("--init-board").map(|p| load_interior_grid(&model, Path::new(&p)))
                };
                let p = SaParams {
                    seed,
                    budget_ms: budget_ms.saturating_sub(if mode == "hybrid" { dfs_ms } else { 0 }),
                    hinted,
                    t0,
                };
                let r = sa_run(&model, targets, init.as_deref(), &p);
                let breaks = model.count_breaks(&r.best_state, targets);
                JobOut {
                    frame_label: label,
                    frame_idx: fidx,
                    seed,
                    max_depth: model.cells,
                    nodes: r.moves,
                    epochs: 1,
                    completes: 1,
                    complete: Some((r.best_state, breaks)),
                    sa_pair: Some((r.best_ii, r.best_ib)),
                    ms_at_max: 0,
                }
            }
            m => panic!("unknown mode {m}"),
        }
    };

    let results: Vec<JobOut> = if mode == "tail2polish" {
        let path = get("--init-board").expect("tail2polish needs --init-board");
        let placement = cio::load_placement(Path::new(&path)).expect("init board");
        let mut g2l = vec![u16::MAX; 256];
        for (l, &g) in model.global_id.iter().enumerate() {
            g2l[g as usize] = l as u16;
        }
        let mut grid = vec![(u16::MAX, 0u8); model.cells];
        for &(pos, pid, rot) in &placement {
            if frame::is_ring(pos) {
                continue;
            }
            let (y, x) = (pos / 16, pos % 16);
            grid[(y - 1) * model.n + (x - 1)] = (g2l[pid as usize], rot);
        }
        assert!(grid.iter().all(|&(p, _)| p != u16::MAX), "incomplete interior");
        let targets = frames.first().map(|f| &f.targets);
        let tables = Tables::build(&model, hinted);
        let n = model.n;
        let start = (n - 2) * n;
        let cur = model.count_breaks(&grid, targets);
        // mismatches attributable to the 2-row tail
        let head: Vec<(u16, u8)> = grid.clone();
        let mut tail_mis = 0u32;
        for cell in start..model.cells {
            let e = model.edges(head[cell].0, head[cell].1);
            if cell % n > 0 {
                let l = model.edges(head[cell - 1].0, head[cell - 1].1);
                tail_mis += u32::from(l[1] != e[3]);
            }
            let u = model.edges(head[cell - n].0, head[cell - n].1);
            tail_mis += u32::from(u[2] != e[0]);
            if let Some(tg) = targets {
                for s in 0..4 {
                    if tg[cell][s].is_some_and(|c| c != e[s]) {
                        tail_mis += 1;
                    }
                }
            }
        }
        let pieces: Vec<u16> = grid[start..].iter().map(|&(p, _)| p).collect();
        let mut forced_by_cell: Vec<Option<(u16, u8)>> = vec![None; model.cells];
        if hinted {
            for &(cell, pid, rot) in &model.hints {
                forced_by_cell[cell] = Some((pid as u16, rot));
            }
        }
        let cap: u64 = get("--cap").and_then(|s| s.parse().ok()).unwrap_or(2_000_000_000);
        let t0i = std::time::Instant::now();
        let (mis, asn) = exact_tail2(
            &model, &tables, &grid, &pieces, &forced_by_cell, targets, tail_mis, cap,
        );
        println!(
            "tail2polish {path}: breaks {cur} (tail {tail_mis}) -> tail {mis} ({}s)",
            t0i.elapsed().as_secs()
        );
        let mut out = grid;
        if mis < tail_mis {
            for (j, &pr) in asn.iter().enumerate() {
                out[start + j] = pr;
            }
        }
        let breaks = model.count_breaks(&out, targets);
        vec![JobOut {
            frame_label: frames.first().map_or_else(|| "free".into(), |f| f.label.clone()),
            frame_idx: if bordered { 0 } else { usize::MAX },
            seed: 0,
            max_depth: model.cells,
            nodes: 0,
            epochs: 1,
            completes: 1,
            complete: Some((out, breaks)),
            sa_pair: None,
            ms_at_max: 0,
        }]
    } else {
        jobs.par_iter().map(run_job).collect()
    };

    // ---- report + save ----
    let mut totals: Vec<(String, Vec<i64>)> = Vec::new();
    for r in &results {
        let (breaks_s, ii, ib, bb, total, hints_ok, board_name) = if let Some((grid, breaks)) =
            &r.complete
        {
            let ii = model.ii_matches(grid);
            let (ib, bb, total, hints_ok, name) = if r.frame_idx != usize::MAX {
                let f = &frames[r.frame_idx];
                let ib = model.ib_matches(grid, &f.targets);
                let total = ii + ib + f.bb;
                // assemble + verify the full board
                let mut placement = cio::interior_to_placement(&model, grid);
                placement.extend_from_slice(&f.placement);
                let chk = verify::verify(&puzzle, &hints, &placement);
                assert!(chk.is_legal_complete(), "assembled board must be legal: {chk:?}");
                assert_eq!(chk.total(), total, "verify total");
                let name = format!(
                    "T{}_II{}_IB{}_{}_seed{}.json",
                    total, ii, ib, r.frame_label, r.seed
                );
                let meta = format!(
                    "\"matched\":{},\"ii\":{},\"ib\":{},\"bb\":{},\"hints_ok\":{},\"mode\":\"{}\",\"seed\":{},\"frame\":\"{}\",",
                    total, ii, ib, f.bb, chk.hints_ok, mode, r.seed, r.frame_label
                );
                let p = cio::save_board(&dir, &name, &puzzle, &placement, &meta);
                cio::append_history(
                    &dir,
                    &format!("cloister2_{mode}"),
                    r.seed,
                    ii,
                    &format!("total={total};ib={ib};bb={};frame={};{params_str}", f.bb, r.frame_label),
                    &p.display().to_string(),
                    &cio::bucas_url(&puzzle, &placement),
                );
                if chk.hints_ok == chk.hints_total && total >= 459 {
                    println!("*** STRICT-TRACK CANDIDATE: total {total} with 5/5 hints — {name}");
                }
                (ib, f.bb, total, chk.hints_ok, name)
            } else {
                let placement = cio::interior_to_placement(&model, grid);
                let name = format!("II{}_{}_seed{}.json", ii, r.frame_label, r.seed);
                let meta = format!(
                    "\"interior_ii\":{},\"ii_max\":{},\"mode\":\"{}\",\"seed\":{},\"hinted\":{},",
                    ii, model.ii_max, mode, r.seed, hinted
                );
                let p = cio::save_board(&dir, &name, &puzzle, &placement, &meta);
                cio::append_history(
                    &dir,
                    &format!("cloister2_{mode}"),
                    r.seed,
                    ii,
                    &params_str,
                    &p.display().to_string(),
                    &cio::bucas_url(&puzzle, &placement),
                );
                (0, 0, ii, 0, name)
            };
            (breaks.to_string(), ii, ib, bb, total, hints_ok, name)
        } else {
            ("-".into(), 0, 0, 0, 0, 0, "-".into())
        };
        writeln!(
            summary,
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            r.frame_label,
            r.seed,
            mode,
            scan.name(),
            r.max_depth,
            r.nodes,
            r.epochs,
            r.completes,
            breaks_s,
            ii,
            ib,
            bb,
            total,
            hints_ok,
            r.ms_at_max,
            board_name
        )
        .expect("row");
        let sa_s = r
            .sa_pair
            .map_or(String::new(), |(a, b)| format!("  sa_ii {a} sa_ib {b}"));
        println!(
            "frame {:>12} seed {:>3}: depth {:>3}/{}  completes {:>6}  breaks {:>3}  II {:>3} IB {:>2} total {:>3}{}",
            r.frame_label, r.seed, r.max_depth, model.cells, r.completes, breaks_s, ii, ib, total, sa_s
        );
        if r.complete.is_some() {
            totals
                .entry_or(&r.frame_label)
                .push(i64::from(total));
        } else {
            totals.entry_or(&r.frame_label).push(-(r.max_depth as i64));
        }
    }
    for (label, mut ts_) in totals {
        ts_.sort_unstable();
        println!(
            "frame {:>12}: n={} min={} median={} max={}",
            label,
            ts_.len(),
            ts_[0],
            ts_[ts_.len() / 2],
            ts_[ts_.len() - 1]
        );
    }
    println!("run dir: {}", dir.display());
}

trait EntryOr {
    fn entry_or(&mut self, label: &str) -> &mut Vec<i64>;
}
impl EntryOr for Vec<(String, Vec<i64>)> {
    fn entry_or(&mut self, label: &str) -> &mut Vec<i64> {
        if let Some(i) = self.iter().position(|(l, _)| l == label) {
            &mut self[i].1
        } else {
            self.push((label.to_string(), Vec::new()));
            &mut self.last_mut().expect("just pushed").1
        }
    }
}

/// load a board JSON's interior cells into a canonical-local-pid grid
fn load_interior_grid(
    model: &InteriorModel,
    path: &Path,
) -> Vec<(u16, u8)> {
    let placement = cio::load_placement(path).expect("init board");
    let mut g2l = vec![u16::MAX; 256];
    for (l, &g) in model.global_id.iter().enumerate() {
        g2l[g as usize] = l as u16;
    }
    let mut grid = vec![(u16::MAX, 0u8); model.cells];
    for &(pos, pid, rot) in &placement {
        if eternity2_cloister::frame::is_ring(pos) {
            continue;
        }
        let (y, x) = (pos / 16, pos % 16);
        grid[(y - 1) * model.n + (x - 1)] = (g2l[pid as usize], rot);
    }
    assert!(grid.iter().all(|&(p, _)| p != u16::MAX), "incomplete interior");
    grid
}
