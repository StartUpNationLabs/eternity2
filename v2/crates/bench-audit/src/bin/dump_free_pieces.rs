#![forbid(unsafe_code)]
use std::path::PathBuf;
use std::collections::HashSet;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use serde_json::Value;

fn rot_edges_canonical(e: [u8; 4], r: u8) -> [u8; 4] {
    // Matches Rotation::rotated on Edges:
    // r=0: [t,r,b,l]
    // r=1: [l,t,r,b]
    // r=2: [b,l,t,r]
    // r=3: [r,b,l,t]
    match r {
        0 => e,
        1 => [e[3], e[0], e[1], e[2]],
        2 => [e[2], e[3], e[0], e[1]],
        _ => [e[1], e[2], e[3], e[0]],
    }
}

fn main() {
    let mut input = PathBuf::from("output/vol-122/j1_chain_hinted_v2_b100k.json");
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--input" => input = PathBuf::from(args.next().unwrap()),
            _ => {}
        }
    }
    let pp = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&pp).expect("load puzzle");
    let side = puzzle.width as usize;
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    let txt = std::fs::read_to_string(&input).expect("read input");
    let v: Value = serde_json::from_str(&txt).expect("parse");
    let placement = v["placement"].as_array().unwrap();
    let mut used: HashSet<u16> = HashSet::new();
    let mut placed_by_pos: std::collections::BTreeMap<usize, (u16, u8)> = std::collections::BTreeMap::new();
    for p in placement {
        let pos = p["pos"].as_u64().unwrap() as usize;
        let pid = p["piece_id"].as_u64().unwrap() as u16;
        let rot = p["rotation"].as_u64().unwrap() as u8;
        used.insert(pid);
        placed_by_pos.insert(pos, (pid, rot));
    }
    let free: Vec<u16> = (0..256).filter(|p| !used.contains(p)).collect();
    println!("Used: {}, free: {}", used.len(), free.len());
    println!("\nFree piece edges (orig T,R,B,L):");
    for &pid in &free {
        let e = pieces[pid as usize];
        let zeros = e.iter().filter(|&&x| x == 0).count();
        let kind = match zeros { 2 => "CORNER", 1 => "edge  ", _ => "INTER " };
        println!("  pid={:3} [{}] orig=({},{},{},{})", pid, kind, e[0], e[1], e[2], e[3]);
    }

    // Row 14 bottom colors (= row 15 needed tops)
    println!("\nRow 14 bottom edges (what row 15 tops must match):");
    for c in 0..side {
        let pos = 14 * side + c;
        if let Some(&(pid, rot)) = placed_by_pos.get(&pos) {
            let e = rot_edges_canonical(pieces[pid as usize], rot);
            println!("  col {}: pid={} rot={} -> edges=(T={},R={},B={},L={}) → BOT={}",
                c, pid, rot, e[0], e[1], e[2], e[3], e[2]);
        } else {
            println!("  col {}: EMPTY", c);
        }
    }

    // For each row-15 col, find feasible free pieces:
    println!("\nRow 15 cell feasibility (free pieces with bot=0, top matches row-14-bot, side constraints):");
    for c in 0..side {
        let pos15 = 15 * side + c;
        if placed_by_pos.contains_key(&pos15) {
            println!("  col {}: already placed", c); continue;
        }
        let r14_pos = 14 * side + c;
        let (r14pid, r14rot) = placed_by_pos[&r14_pos];
        let r14_e = rot_edges_canonical(pieces[r14pid as usize], r14rot);
        let need_top = r14_e[2];
        let need_left_zero = c == 0;
        let need_right_zero = c == side - 1;
        let mut candidates = vec![];
        for &pid in &free {
            for rot in 0u8..4 {
                let e = rot_edges_canonical(pieces[pid as usize], rot);
                if e[2] != 0 { continue; } // need bottom = border
                if e[0] != need_top { continue; }
                if need_left_zero && e[3] != 0 { continue; }
                if !need_left_zero && e[3] == 0 { continue; }
                if need_right_zero && e[1] != 0 { continue; }
                if !need_right_zero && e[1] == 0 { continue; }
                candidates.push((pid, rot, e));
            }
        }
        println!("  col {} need top={}: {} candidate(s)", c, need_top, candidates.len());
        for (pid, rot, e) in candidates.iter().take(5) {
            println!("    pid={} rot={} edges=({},{},{},{})", pid, rot, e[0], e[1], e[2], e[3]);
        }
    }
}
