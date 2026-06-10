// framegen — vol-213 hint-compatible frame generator.
//
// The vol-213 500-frame census measured 1/500 (0.2%) of random BB=60
// frames hint-compatible, and pinpointed the killers: interior (0,1)
// must satisfy frame-N + the (0,0)-chain + hint15-S simultaneously
// (311/500 jam at depth 1); interior (0,13) needs N+E rims + W-chain
// (89/500 jam at depth 13). This bin enumerates BB=60 rings by
// randomized cycle-DFS with the four chain-feasibility constraints
// checked DURING ring construction:
//   1. top-left:  ∃ distinct interior p0@(0,0), p1@(0,1), p2@(1,0)
//      with p1.S = hint15.N and p2.E = hint15.W
//   2. top-right: ∃ distinct p12@(0,12), p13@(0,13), p15@(1,13)
//      with p12.S = hint26.N and p15.W = hint26.E
//   3. deep-left:  ∃ p@(12,0) with W = ring(13,0) inward, E = deep-left-hint.W
//   4. deep-right: ∃ p@(12,13) with E = ring(13,15) inward, W = deep-right-hint.E
// The ring path order front-loads the check sites: (2,0),(1,0),(0,0),
// (0,1)..(0,15),(1,15)..(15,15),(15,14)..(15,0),(14,0)..(3,0).
//
// --no-chains generates without the checks (census control: measures
// the chains' precision against the 6 s probe).
// Output: ring placement JSONs loadable by frame::load, timestamped dir.

#![forbid(unsafe_code)]

use std::collections::HashSet;
use std::hash::{Hash, Hasher};
use std::io::Write as _;
use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_cloister::frame::{from_ring, W};
use eternity2_cloister::io as cio;
use eternity2_cloister::model::InteriorModel;
use eternity2_cloister::rng::Rng;
use eternity2_core::{Rotation, BORDER};

fn ring_path() -> Vec<usize> {
    let mut p = vec![2 * W, W, 0];
    p.extend(1..W);
    p.extend((1..W).map(|y| y * W + W - 1));
    p.extend((0..W - 1).rev().map(|x| (W - 1) * W + x));
    p.extend((3..W - 1).rev().map(|y| y * W));
    assert_eq!(p.len(), 60);
    p
}

/// sides that must be grey at a ring position
fn grey_pattern(pos: usize) -> [bool; 4] {
    let (y, x) = (pos / W, pos % W);
    [y == 0, x == W - 1, y == W - 1, x == 0]
}

/// my side facing the cell at `other` (must be grid-adjacent)
fn facing(pos: usize, other: usize) -> u8 {
    match other as isize - pos as isize {
        d if d == -(W as isize) => 0,
        1 => 1,
        d if d == W as isize => 2,
        -1 => 3,
        _ => unreachable!("non-adjacent ring cells"),
    }
}

#[allow(clippy::too_many_lines)]
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let get = |flag: &str| -> Option<String> {
        args.iter()
            .position(|a| a == flag)
            .and_then(|i| args.get(i + 1).cloned())
    };
    let count: usize = get("--count").and_then(|s| s.parse().ok()).unwrap_or(300);
    let seed0: u64 = get("--seed0").and_then(|s| s.parse().ok()).unwrap_or(1);
    let no_chains = args.iter().any(|a| a == "--no-chains");
    let node_cap: u64 = get("--node-cap").and_then(|s| s.parse().ok()).unwrap_or(500_000);
    let out_root = get("--out-root").unwrap_or_else(|| "output/vol-213".into());
    let puzzle_path = PathBuf::from(
        get("--puzzle").unwrap_or_else(|| "../data/puzzles/size_16_official_eternity.csv".into()),
    );
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let model = InteriorModel::from_puzzle(&puzzle, &hints);
    let n = model.n;

    // hint edge colors by hint geometry (row 1 left/right, row 12 left/right)
    let hint_edges = |row: usize, left: bool| -> [u8; 4] {
        let &(_, pid, rot) = model
            .hints
            .iter()
            .find(|&&(cell, _, _)| cell / n == row && (cell % n < n / 2) == left)
            .expect("hint");
        model.edges(pid as u16, rot)
    };
    let h15 = hint_edges(1, true);
    let h26 = hint_edges(1, false);
    let hdl = hint_edges(12, true);
    let hdr = hint_edges(12, false);

    // interior candidate pieces (local ids), hint pieces excluded
    let hint_pids: Vec<usize> = model.hints.iter().map(|&(_, pid, _)| pid).collect();
    let ints: Vec<u16> = (0..model.np as u16)
        .filter(|&p| !hint_pids.contains(&(p as usize)))
        .collect();
    let iedges = |p: u16, r: u8| model.edges(p, r);

    // border pieces: forced rotation + edges per ring cell
    let path = ring_path();
    let border_pids: Vec<u16> = (0..256u16)
        .filter(|&pid| {
            let e = puzzle.piece(pid).expect("piece").edges.as_array();
            e.iter().filter(|&&c| c == BORDER).count() >= 1
        })
        .collect();
    assert_eq!(border_pids.len(), 60);
    // fit[cell_idx][k] = (border piece local k, rot, edges) if the piece's
    // grey sides exactly match the cell's outward sides
    let fit: Vec<Vec<(u16, u8, [u8; 4])>> = path
        .iter()
        .map(|&pos| {
            let want = grey_pattern(pos);
            border_pids
                .iter()
                .enumerate()
                .filter_map(|(k, &pid)| {
                    (0..4u8).find_map(|rot| {
                        let e = puzzle
                            .piece(pid)
                            .expect("piece")
                            .edges
                            .rotated(Rotation::from_u8(rot).expect("rot"))
                            .as_array();
                        let ok = (0..4).all(|s| (e[s] == BORDER) == want[s]);
                        ok.then_some((k as u16, rot, e))
                    })
                })
                .collect()
        })
        .collect();

    // chain feasibility -------------------------------------------------
    let pids_with = |f: &dyn Fn([u8; 4]) -> bool| -> Vec<u16> {
        let mut v: Vec<u16> = Vec::new();
        for &p in &ints {
            if (0..4u8).any(|r| f(iedges(p, r))) {
                v.push(p);
            }
        }
        v
    };
    let top_left = |a: u8, b: u8, c: u8, w2: u8| -> bool {
        for &p0 in &ints {
            for r0 in 0..4u8 {
                let e0 = iedges(p0, r0);
                if e0[0] != b || e0[3] != a {
                    continue;
                }
                let s1 = pids_with(&|e: [u8; 4]| e[0] == c && e[3] == e0[1] && e[2] == h15[0]);
                let s2 = pids_with(&|e: [u8; 4]| e[3] == w2 && e[0] == e0[2] && e[1] == h15[3]);
                let s1: Vec<u16> = s1.into_iter().filter(|&p| p != p0).collect();
                let s2: Vec<u16> = s2.into_iter().filter(|&p| p != p0).collect();
                if !s1.is_empty()
                    && !s2.is_empty()
                    && !(s1.len() == 1 && s2.len() == 1 && s1[0] == s2[0])
                {
                    return true;
                }
            }
        }
        false
    };
    let top_right = |d: u8, f: u8, g: u8, e2: u8| -> bool {
        for &p12 in &ints {
            for r12 in 0..4u8 {
                let e12 = iedges(p12, r12);
                if e12[0] != d || e12[2] != h26[0] {
                    continue;
                }
                for &p13 in &ints {
                    if p13 == p12 {
                        continue;
                    }
                    for r13 in 0..4u8 {
                        let e13 = iedges(p13, r13);
                        if e13[0] != f || e13[1] != g || e13[3] != e12[1] {
                            continue;
                        }
                        let ok = ints.iter().any(|&p15| {
                            p15 != p12
                                && p15 != p13
                                && (0..4u8).any(|r15| {
                                    let e15 = iedges(p15, r15);
                                    e15[0] == e13[2] && e15[1] == e2 && e15[3] == h26[1]
                                })
                        });
                        if ok {
                            return true;
                        }
                    }
                }
            }
        }
        false
    };
    let deep_left = |inward_e: u8| -> bool {
        ints.iter().any(|&p| {
            (0..4u8).any(|r| {
                let e = iedges(p, r);
                e[3] == inward_e && e[1] == hdl[3]
            })
        })
    };
    let deep_right = |inward_w: u8| -> bool {
        ints.iter().any(|&p| {
            (0..4u8).any(|r| {
                let e = iedges(p, r);
                e[1] == inward_w && e[3] == hdr[1]
            })
        })
    };

    // trigger path indices
    let idx_of = |pos: usize| path.iter().position(|&p| p == pos).expect("on path");
    let trig_tl = idx_of(2); // (0,2)
    let trig_tr = idx_of(2 * W + W - 1); // (2,15)
    let trig_dr = idx_of(13 * W + W - 1); // (13,15)
    let trig_dl = idx_of(13 * W); // (13,0)

    // generation ---------------------------------------------------------
    let ts = cio::timestamp();
    let tag = if no_chains { "nochains" } else { "chains" };
    let dir = PathBuf::from(format!("{out_root}/framegen_{tag}_{ts}"));
    std::fs::create_dir_all(&dir).expect("mkdir");
    eprintln!(
        "framegen: target {count} frames ({tag}), trig idx tl={trig_tl} tr={trig_tr} dr={trig_dr} dl={trig_dl}"
    );

    let mut seen: HashSet<u64> = HashSet::new();
    let mut emitted = 0usize;
    let mut restarts = 0u64;
    let mut chain_prunes = [0u64; 4];
    let mut seed = seed0;
    while emitted < count {
        restarts += 1;
        let mut rng = Rng::new(seed);
        seed += 1;
        // per-restart shuffled candidate order per cell
        let mut order: Vec<Vec<u16>> = fit
            .iter()
            .map(|cands| (0..cands.len() as u16).collect())
            .collect();
        for o in &mut order {
            for i in (1..o.len()).rev() {
                let j = rng.below(i + 1);
                o.swap(i, j);
            }
        }
        let mut used = [false; 60];
        let mut asn: Vec<(u16, u8, [u8; 4])> = Vec::with_capacity(60);
        let mut cursor = vec![0usize; 61];
        let mut nodes = 0u64;
        let mut depth = 0usize;
        let complete = 'dfs: loop {
            nodes += 1;
            if nodes > node_cap {
                break 'dfs false;
            }
            if depth == 60 {
                break 'dfs true;
            }
            let mut placed = false;
            while cursor[depth] < order[depth].len() {
                let ci = order[depth][cursor[depth]] as usize;
                cursor[depth] += 1;
                let (k, rot, e) = fit[depth][ci];
                if used[k as usize] {
                    continue;
                }
                if depth > 0 {
                    let my_side = facing(path[depth], path[depth - 1]) as usize;
                    let their = asn[depth - 1].2[(my_side + 2) % 4];
                    if e[my_side] != their {
                        continue;
                    }
                }
                if depth == 59 {
                    let my_side = facing(path[59], path[0]) as usize;
                    if e[my_side] != asn[0].2[(my_side + 2) % 4] {
                        continue;
                    }
                }
                // chain checks fire when their last ring dependency lands
                if !no_chains {
                    let feasible = if depth == trig_tl {
                        // a = E of (1,0)=idx1; b = S of (0,1)=idx3; c = S of me
                        // w2 = E of (2,0)=idx0
                        let ok = top_left(asn[1].2[1], asn[3].2[2], e[2], asn[0].2[1]);
                        if !ok {
                            chain_prunes[0] += 1;
                        }
                        ok
                    } else if depth == trig_tr {
                        // d = S of (0,13); f = S of (0,14); g = W of (1,15); e2 = W of me
                        let i013 = idx_of(13);
                        let i014 = idx_of(14);
                        let i115 = idx_of(W + W - 1);
                        let ok = top_right(
                            asn[i013].2[2],
                            asn[i014].2[2],
                            asn[i115].2[3],
                            e[3],
                        );
                        if !ok {
                            chain_prunes[1] += 1;
                        }
                        ok
                    } else if depth == trig_dr {
                        let ok = deep_right(e[3]);
                        if !ok {
                            chain_prunes[2] += 1;
                        }
                        ok
                    } else if depth == trig_dl {
                        let ok = deep_left(e[1]);
                        if !ok {
                            chain_prunes[3] += 1;
                        }
                        ok
                    } else {
                        true
                    };
                    if !feasible {
                        continue;
                    }
                }
                used[k as usize] = true;
                asn.push((k, rot, e));
                placed = true;
                break;
            }
            if placed {
                depth += 1;
                cursor[depth] = 0;
            } else {
                if depth == 0 {
                    break 'dfs false;
                }
                cursor[depth] = 0;
                depth -= 1;
                let (k, _, _) = asn.pop().expect("asn");
                used[k as usize] = false;
            }
        };
        if !complete {
            continue;
        }
        // dedup + verify + emit
        let ring: std::collections::HashMap<usize, (u16, u8)> = path
            .iter()
            .zip(&asn)
            .map(|(&pos, &(k, rot, _))| (pos, (border_pids[k as usize], rot)))
            .collect();
        let mut placement: Vec<(usize, u16, u8)> =
            ring.iter().map(|(&p, &(pid, r))| (p, pid, r)).collect();
        placement.sort_unstable();
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        placement.hash(&mut hasher);
        if !seen.insert(hasher.finish()) {
            continue;
        }
        let fr = from_ring(&ring, &puzzle, format!("gen{emitted:04}")).expect("legal ring");
        assert_eq!(fr.bb, 60, "cycle DFS must produce BB=60");
        let body: Vec<String> = placement
            .iter()
            .map(|&(pos, pid, rot)| {
                format!("{{\"pos\":{pos},\"piece_id\":{pid},\"rotation\":{rot}}}")
            })
            .collect();
        let json = format!(
            "{{\"generator\":\"framegen_{tag}\",\"seed\":{},\"bb\":60,\"placement\":[{}]}}",
            seed - 1,
            body.join(",")
        );
        let mut f =
            std::fs::File::create(dir.join(format!("gen{emitted:04}.json"))).expect("create");
        f.write_all(json.as_bytes()).expect("write");
        emitted += 1;
        if emitted % 50 == 0 {
            eprintln!(
                "  {emitted}/{count} (restarts {restarts}, prunes tl={} tr={} dr={} dl={})",
                chain_prunes[0], chain_prunes[1], chain_prunes[2], chain_prunes[3]
            );
        }
    }
    println!(
        "framegen done: {emitted} frames in {} | restarts {restarts} | chain prunes tl={} tr={} dr={} dl={}",
        dir.display(),
        chain_prunes[0],
        chain_prunes[1],
        chain_prunes[2],
        chain_prunes[3]
    );
}
