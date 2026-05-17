// K5: Multiset-Deterministic Filling (MDF) propagator.
//
// Given a partial board, iteratively fill cells whose 4-color multiset
// constraint uniquely determines a piece. 192/196 interior pieces have
// unique color multisets → many positions are forced.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::collections::{HashMap, BTreeMap};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use serde_json::{json, Value};

fn rot_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    match r {
        0 => e,
        1 => [e[3], e[0], e[1], e[2]],
        2 => [e[2], e[3], e[0], e[1]],
        _ => [e[1], e[2], e[3], e[0]],
    }
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut input = PathBuf::from("output/vol-122/j1_chain_hinted_v2_b100k.json");
    let mut out_path = PathBuf::from("output/vol-122/mdf_filled.json");

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--input" => input = PathBuf::from(args.next().unwrap()),
            "--out" => out_path = PathBuf::from(args.next().unwrap()),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let side = puzzle.width as usize;
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    // Load input partial
    let txt = std::fs::read_to_string(&input).expect("read");
    let v: Value = serde_json::from_str(&txt).expect("parse");
    let mut board: BTreeMap<(usize, usize), (u16, u8)> = BTreeMap::new();
    let mut used: std::collections::HashSet<u16> = std::collections::HashSet::new();
    for p in v["placement"].as_array().unwrap() {
        let pos = p["pos"].as_u64().unwrap() as usize;
        let pid = p["piece_id"].as_u64().unwrap() as u16;
        let rot = p["rotation"].as_u64().unwrap() as u8;
        board.insert((pos / side, pos % side), (pid, rot));
        used.insert(pid);
    }
    println!("Loaded partial: {} cells", board.len());

    // Build multiset → list of (pid, edges) map for free pieces
    let mut multiset_to_pids: HashMap<[u8; 4], Vec<u16>> = HashMap::new();
    for (pid, e) in pieces.iter().enumerate() {
        if used.contains(&(pid as u16)) { continue; }
        let mut sorted = *e;
        sorted.sort();
        multiset_to_pids.entry(sorted).or_default().push(pid as u16);
    }
    println!("Free pieces: {}, multiset classes: {}", 256 - used.len(), multiset_to_pids.len());

    // MDF iteration
    let mut total_filled = 0;
    loop {
        let mut filled_this_iter = 0;
        let mut to_fill = Vec::new();
        for r in 0..side {
            for c in 0..side {
                if board.contains_key(&(r, c)) { continue; }
                // Gather required colors from filled neighbors
                let mut required: Vec<Option<u8>> = vec![None; 4]; // [T, R, B, L]
                // Top (row r-1's bottom)
                if r == 0 { required[0] = Some(0); }
                else if let Some(&(npid, nrot)) = board.get(&(r-1, c)) {
                    let ne = rot_edges(pieces[npid as usize], nrot);
                    required[0] = Some(ne[2]);
                }
                // Right (col c+1's left)
                if c == side - 1 { required[1] = Some(0); }
                else if let Some(&(npid, nrot)) = board.get(&(r, c+1)) {
                    let ne = rot_edges(pieces[npid as usize], nrot);
                    required[1] = Some(ne[3]);
                }
                // Bottom (row r+1's top)
                if r == side - 1 { required[2] = Some(0); }
                else if let Some(&(npid, nrot)) = board.get(&(r+1, c)) {
                    let ne = rot_edges(pieces[npid as usize], nrot);
                    required[2] = Some(ne[0]);
                }
                // Left (col c-1's right)
                if c == 0 { required[3] = Some(0); }
                else if let Some(&(npid, nrot)) = board.get(&(r, c-1)) {
                    let ne = rot_edges(pieces[npid as usize], nrot);
                    required[3] = Some(ne[1]);
                }

                // Count known constraints
                let n_known = required.iter().filter(|x| x.is_some()).count();
                if n_known < 4 { continue; }

                // All 4 known: find piece+rotation matching
                let known_colors: [u8; 4] = [
                    required[0].unwrap(),
                    required[1].unwrap(),
                    required[2].unwrap(),
                    required[3].unwrap(),
                ];
                let mut sorted = known_colors;
                sorted.sort();

                // Find candidate pieces by multiset
                if let Some(pids) = multiset_to_pids.get(&sorted) {
                    // For each candidate piece, find a rotation where edges == known_colors
                    let mut candidates: Vec<(u16, u8)> = Vec::new();
                    for &pid in pids {
                        for rot in 0..4u8 {
                            let pe = rot_edges(pieces[pid as usize], rot);
                            if pe == known_colors {
                                candidates.push((pid, rot));
                            }
                        }
                    }
                    if candidates.len() == 1 {
                        to_fill.push(((r, c), candidates[0]));
                    } else if candidates.is_empty() {
                        // Constraint infeasibility — but maybe board has an interior cell
                        // that simply isn't fillable. Note and skip.
                    }
                    // Multiple candidates: leave for MRV.
                }
            }
        }

        for ((r, c), (pid, rot)) in &to_fill {
            // Race: another fill in this iter could have claimed the piece
            if used.contains(pid) { continue; }
            if board.contains_key(&(*r, *c)) { continue; }
            board.insert((*r, *c), (*pid, *rot));
            used.insert(*pid);
            filled_this_iter += 1;
        }
        total_filled += filled_this_iter;
        if filled_this_iter == 0 { break; }
        println!("  iter: +{} filled (total filled by MDF: {})", filled_this_iter, total_filled);
    }
    println!("Total cells after MDF: {}", board.len());

    // Score the board
    let mut matched = 0u32;
    for r in 0..side {
        for c in 0..side {
            if let Some(&(pid, rot)) = board.get(&(r, c)) {
                let e = rot_edges(pieces[pid as usize], rot);
                if c + 1 < side {
                    if let Some(&(npid, nrot)) = board.get(&(r, c+1)) {
                        let ne = rot_edges(pieces[npid as usize], nrot);
                        if e[1] == ne[3] && e[1] != 0 { matched += 1; }
                    }
                }
                if r + 1 < side {
                    if let Some(&(npid, nrot)) = board.get(&(r+1, c)) {
                        let ne = rot_edges(pieces[npid as usize], nrot);
                        if e[2] == ne[0] && e[2] != 0 { matched += 1; }
                    }
                }
            }
        }
    }
    println!("Matched: {}/480", matched);

    let placement: Vec<_> = board.iter().map(|((r, c), (pid, rot))| {
        json!({"pos": r * side + c, "piece_id": *pid as u32, "rotation": *rot as u32})
    }).collect();
    let out = json!({
        "source": "k5_mdf",
        "input": input.display().to_string(),
        "n_placed": board.len(),
        "matched_edges": matched,
        "placement": placement,
    });
    std::fs::create_dir_all(out_path.parent().unwrap()).ok();
    std::fs::write(&out_path, serde_json::to_string_pretty(&out).unwrap()).unwrap();
    println!("Wrote: {}", out_path.display());
}
