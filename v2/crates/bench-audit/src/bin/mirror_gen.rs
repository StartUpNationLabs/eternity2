// Vol-218 MIRROR: broken-top stage-1 generator for the official E2.
// DFS over rows 0..R (default 5) with DELIBERATE breaks: a mask of
// (cell -> required cost) pins damage geometry (SOTA-mirrored /
// dispersed); non-mask cells must place at cost 0. Row-2 clues forced,
// ALL hint pieces bucket-excluded elsewhere. Banks diverse tops at
// depth R*16, deduped by (row R-1 souths, pool mask).
//
//   mirror_gen --arm sota469 --k 56 --secs 120 --out DIR [--seed 1]
//
// Arms (break-paying cells, cell pays its N and W edges):
//   sota469   McGavin 469 map, 11 breaks ((4,14) pays 2)
//   sota470   Blackwood 470 map clipped to rows 0-4, 9 breaks ((2,10) pays 2)
//   dispersed 10 cost-1 cells staggered over rows 1-4 (MIDDEN-style)
//   free      budget 10 anywhere in rows 0-4 (realized count recorded)
//   control   0 breaks (perfect top)

#![forbid(unsafe_code)]

use std::collections::{HashMap, HashSet};
use std::io::Write;
use std::path::PathBuf;
use std::time::{Duration, Instant};

use eternity2_bench_audit::mini::Mini;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_generator::SplitMix64;

fn arm_mask(arm: &str) -> (HashMap<usize, u32>, u32, bool) {
    // (cell -> required cost, total budget, free placement?)
    let cells = |v: &[(usize, usize, u32)]| -> HashMap<usize, u32> {
        v.iter().map(|&(r, c, k)| (r * 16 + c, k)).collect()
    };
    match arm {
        "sota469" => (
            cells(&[
                (1, 9, 1), (2, 8, 1), (2, 9, 1), (3, 7, 1), (3, 8, 1), (3, 14, 1),
                (4, 10, 1), (4, 11, 1), (4, 12, 1), (4, 14, 2),
            ]),
            11,
            false,
        ),
        "sota470" => (
            cells(&[
                (1, 13, 1), (2, 5, 1), (2, 15, 1), (3, 13, 1), (3, 14, 1),
                (4, 6, 1), (4, 15, 1), (2, 10, 2),
            ]),
            9,
            false,
        ),
        "dispersed" => (
            cells(&[
                (1, 4, 1), (1, 10, 1), (1, 15, 1), (2, 7, 1), (2, 12, 1),
                (3, 4, 1), (3, 10, 1), (3, 15, 1), (4, 7, 1), (4, 13, 1),
            ]),
            10,
            false,
        ),
        "free" => (HashMap::new(), 10, true),
        "control" => (HashMap::new(), 0, false),
        other => panic!("unknown arm {other}"),
    }
}

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut rows = 5usize;
    let mut arm = String::from("control");
    let mut k = 56usize;
    let mut secs = 120u64;
    let mut per_restart = 4usize;
    let mut restart_ms = 100u64;
    let mut seed = 1u64;
    let mut out = PathBuf::from("output/vol-218/mirror_tops");
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--rows" => { rows = raw[i + 1].parse().unwrap(); i += 2; }
            "--arm" => { arm = raw[i + 1].clone(); i += 2; }
            "--k" => { k = raw[i + 1].parse().unwrap(); i += 2; }
            "--secs" => { secs = raw[i + 1].parse().unwrap(); i += 2; }
            "--per-restart" => { per_restart = raw[i + 1].parse().unwrap(); i += 2; }
            "--restart-ms" => { restart_ms = raw[i + 1].parse().unwrap(); i += 2; }
            "--seed" => { seed = raw[i + 1].parse().unwrap(); i += 2; }
            "--out" => { out = PathBuf::from(&raw[i + 1]); i += 2; }
            other => panic!("unknown arg {other}"),
        }
    }
    std::fs::create_dir_all(&out).expect("mkdir out");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("puzzle");
    let hv: Vec<(usize, u16, u8)> = hints
        .hints
        .iter()
        .map(|h| (h.position as usize, h.piece_id, h.rotation.as_u8()))
        .collect();
    let m = Mini::from_puzzle(&puzzle, hv);
    let n = m.n;
    let prefix_len = rows * n;
    let (mask, budget, free) = arm_mask(&arm);
    for &pos in mask.keys() {
        assert!(pos < prefix_len, "mask cell outside stage-1 rows");
        assert!(!m.hints.iter().any(|&(hp, _, _)| hp == pos), "mask on a clue cell");
    }

    let mut avail0 = vec![true; n * n];
    for &(_, p, _) in &m.hints {
        avail0[p as usize] = false;
    }
    // Clue-compat pre-filter: a cell directly N or W of a forced clue
    // must expose the matching color toward it (unless the clue cell
    // itself is allowed to pay — it isn't: clue cells are never in the
    // mask). Kills the deterministic clue wall (measured: d34 stall).
    let clue_s_demand: HashMap<usize, u8> = m
        .hints
        .iter()
        .filter(|&&(hp, _, _)| hp < prefix_len && hp >= n)
        .map(|&(hp, p, rt)| (hp - n, m.rot[p as usize][rt as usize][0]))
        .collect();
    let clue_e_demand: HashMap<usize, u8> = m
        .hints
        .iter()
        .filter(|&&(hp, _, _)| hp < prefix_len && hp % n > 0)
        .map(|&(hp, p, rt)| (hp - 1, m.rot[p as usize][rt as usize][3]))
        .collect();
    let base_cands: Vec<Vec<(u16, u8)>> = (0..prefix_len)
        .map(|pos| {
            let (r, c) = (pos / n, pos % n);
            match m.hints.iter().find(|&&(hp, _, _)| hp == pos) {
                Some(&(_, p, rt)) => vec![(p, rt)],
                None => m
                    .cands_at(r, c, &avail0)
                    .into_iter()
                    .filter(|&(p, rt)| {
                        let o = m.rot[p as usize][rt as usize];
                        clue_s_demand.get(&pos).is_none_or(|&d| o[2] == d)
                            && clue_e_demand.get(&pos).is_none_or(|&d| o[1] == d)
                    })
                    .collect(),
            }
        })
        .collect();

    let t0 = Instant::now();
    let deadline = t0 + Duration::from_secs(secs);
    let mut rng_seed = seed
        .wrapping_mul(0x9E37_79B9_7F4A_7C15)
        .wrapping_add(arm.bytes().map(u64::from).sum::<u64>());
    let mut seen: HashSet<(Vec<u8>, Vec<u16>)> = HashSet::new();
    let mut banked = 0usize;
    let mut restarts = 0u64;
    let mut meta_lines: Vec<String> = Vec::new();

    while Instant::now() < deadline && banked < k {
        restarts += 1;
        let mut banked_this_restart = 0usize;
        rng_seed = rng_seed.wrapping_add(0xA076_1D64_78BD_642F);
        let mut rng = SplitMix64::new(rng_seed);
        let mut cands = base_cands.clone();
        for list in &mut cands {
            rng.shuffle(list);
        }
        let restart_deadline =
            (t0 + Duration::from_millis(restart_ms * restarts)).min(deadline);

        let mut used = vec![false; n * n];
        let mut grid: Vec<Option<(u16, u8)>> = vec![None; n * n];
        let mut cursor = vec![0usize; prefix_len + 1];
        let mut spent = vec![0u32; prefix_len + 1];
        let mut depth = 0usize;
        let mut restart_max_depth = 0usize;
        let mut tick = 0u64;
        loop {
            tick += 1;
            if (tick & 0xFFF) == 0 && Instant::now() >= restart_deadline {
                break;
            }
            let mut advanced = false;
            while cursor[depth] < cands[depth].len() {
                let (p, rt) = cands[depth][cursor[depth]];
                cursor[depth] += 1;
                if used[p as usize] {
                    continue;
                }
                let o = m.rot[p as usize][rt as usize];
                let (r, c) = (depth / n, depth % n);
                let mut cost = 0u32;
                if r > 0 {
                    let (p2, rt2) = grid[depth - n].unwrap();
                    cost += u32::from(m.rot[p2 as usize][rt2 as usize][2] != o[0]);
                }
                if c > 0 {
                    let (p2, rt2) = grid[depth - 1].unwrap();
                    cost += u32::from(m.rot[p2 as usize][rt2 as usize][1] != o[3]);
                }
                let ok = if free {
                    spent[depth] + cost <= budget
                } else {
                    match mask.get(&depth) {
                        Some(&req) => cost == req,
                        None => cost == 0,
                    }
                };
                if !ok {
                    continue;
                }
                used[p as usize] = true;
                grid[depth] = Some((p, rt));
                spent[depth + 1] = spent[depth] + cost;
                depth += 1;
                restart_max_depth = restart_max_depth.max(depth);
                advanced = true;
                break;
            }
            if advanced {
                if depth == prefix_len {
                    let frontier: Vec<u8> = (0..n)
                        .map(|c| {
                            let (p, rt) = grid[(rows - 1) * n + c].unwrap();
                            m.rot[p as usize][rt as usize][2]
                        })
                        .collect();
                    let mut pool: Vec<u16> = (0..n * n)
                        .filter(|&pid| !used[pid])
                        .map(|pid| u16::try_from(pid).unwrap())
                        .collect();
                    pool.sort_unstable();
                    if seen.insert((frontier, pool)) {
                        let realized = m.breaks_of(&grid);
                        if free {
                            assert!(realized <= budget);
                        } else {
                            assert_eq!(realized, budget, "mask must realize its budget");
                        }
                        for &(hp, p, rt) in &m.hints {
                            if hp < prefix_len {
                                assert_eq!(grid[hp], Some((p, rt)), "hint violated");
                            } else {
                                assert!(!used[p as usize], "hint piece consumed");
                            }
                        }
                        let cells: Vec<String> = (0..prefix_len)
                            .map(|pos| {
                                let (p, rt) = grid[pos].unwrap();
                                format!("{{\"pos\":{pos},\"piece_id\":{p},\"rotation\":{rt}}}")
                            })
                            .collect();
                        let fname = format!("top_{arm}_{banked:03}.json");
                        std::fs::write(
                            out.join(&fname),
                            format!("{{\"placement\": [{}]}}", cells.join(",")),
                        )
                        .expect("write top");
                        meta_lines.push(format!("{fname}\t{arm}\t{realized}"));
                        banked += 1;
                        banked_this_restart += 1;
                        if banked >= k || banked_this_restart >= per_restart {
                            break;
                        }
                    }
                    depth -= 1;
                    let (p, _) = grid[depth].unwrap();
                    used[p as usize] = false;
                    grid[depth] = None;
                } else {
                    cursor[depth] = 0;
                }
            } else {
                if depth == 0 {
                    break;
                }
                cursor[depth] = 0;
                depth -= 1;
                let (p, _) = grid[depth].unwrap();
                used[p as usize] = false;
                grid[depth] = None;
            }
        }
        eprintln!("[restart {restarts}] max_depth {restart_max_depth}");
    }

    let mut f = std::fs::File::create(out.join(format!("tops_{arm}.tsv"))).expect("meta");
    writeln!(f, "file\tarm\trealized_breaks").unwrap();
    for l in &meta_lines {
        writeln!(f, "{l}").unwrap();
    }
    println!(
        "{{\"arm\":\"{arm}\",\"banked\":{banked},\"restarts\":{restarts},\"elapsed_s\":{:.1}}}",
        t0.elapsed().as_secs_f64()
    );
}
