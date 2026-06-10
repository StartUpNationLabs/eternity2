// cloister_border — vol-211: exact border attach for a standalone interior.
//
// Given an interior board (196 interior cells placed, border empty), find the
// assignment of the 60 border pieces to the 60 ring positions (rotations
// forced grey-outward) maximizing BB (ring-ring matches, max 60) + IB
// (inward color vs fixed interior rim, max 56). Exact via HiGHS MIP.
//
// Usage: cloister_border <interior.json> [--time-limit-secs N] [--out-dir D]
// Output: assembled 256-cell board JSON + url + totals; appends history CSV.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::io::Write as _;
use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Piece, Puzzle, Rotation, BORDER};
use good_lp::{
    constraint,
    solvers::highs::highs,
    Expression, ProblemVariables, Solution, SolverModel, Variable, variable,
};

const W: usize = 16;

/// ring positions in cycle order starting top-left corner, clockwise
fn ring_positions() -> Vec<usize> {
    let mut v = Vec::with_capacity(60);
    for x in 0..W {
        v.push(x);
    }
    for y in 1..W {
        v.push(y * W + (W - 1));
    }
    for x in (0..W - 1).rev() {
        v.push((W - 1) * W + x);
    }
    for y in (1..W - 1).rev() {
        v.push(y * W);
    }
    v
}

fn is_corner(pos: usize) -> bool {
    pos == 0 || pos == W - 1 || pos == W * (W - 1) || pos == W * W - 1
}

/// for a ring position, the rotation that puts a piece's grey side(s)
/// outward; returns rotated edge array given base edges
fn forced_rotation(pos: usize, base: [u8; 4]) -> Option<[u8; 4]> {
    // sides: 0=N,1=E,2=S,3=W must be grey
    let (y, x) = (pos / W, pos % W);
    let mut need_grey = Vec::new();
    if y == 0 {
        need_grey.push(0);
    }
    if y == W - 1 {
        need_grey.push(2);
    }
    if x == 0 {
        need_grey.push(3);
    }
    if x == W - 1 {
        need_grey.push(1);
    }
    for r in 0..4u8 {
        let e: [u8; 4] = core::array::from_fn(|s| base[(s + 4 - r as usize) % 4]);
        if need_grey.iter().all(|&s| e[s] == BORDER)
            && e.iter().filter(|&&c| c == BORDER).count() == need_grey.len()
        {
            return Some(e);
        }
    }
    None
}

#[allow(clippy::too_many_lines)]
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let get = |flag: &str| -> Option<String> {
        args.iter()
            .position(|a| a == flag)
            .and_then(|i| args.get(i + 1).cloned())
    };
    let path = args
        .first()
        .filter(|a| !a.starts_with("--"))
        .expect("usage: cloister_border <interior.json>")
        .clone();
    let time_limit: f64 = get("--time-limit-secs").and_then(|s| s.parse().ok()).unwrap_or(120.0);

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");

    // interior board: pos -> (global pid, rot)
    let txt = std::fs::read_to_string(&path).expect("read interior board");
    let v: serde_json::Value = serde_json::from_str(&txt).expect("parse");
    let mut interior_place: HashMap<usize, (u16, u8)> = HashMap::new();
    for e in v["placement"].as_array().expect("placement") {
        let pos = e["pos"].as_u64().expect("pos") as usize;
        interior_place.insert(
            pos,
            (
                e["piece_id"].as_u64().expect("pid") as u16,
                e["rotation"].as_u64().expect("rot") as u8,
            ),
        );
    }
    assert_eq!(interior_place.len(), 196, "need full 196-cell interior");

    let edges_of = |pid: u16, rot: u8| -> [u8; 4] {
        let p: &Piece = puzzle.piece(pid).expect("piece");
        p.edges
            .rotated(Rotation::from_u8(rot).expect("rot"))
            .as_array()
    };

    // rim demand: for each ring SIDE position, the required inward color =
    // adjacent interior cell's facing edge
    let ring = ring_positions();
    let mut rim_color: HashMap<usize, u8> = HashMap::new();
    for &pos in &ring {
        if is_corner(pos) {
            continue;
        }
        let (y, x) = (pos / W, pos % W);
        // (interior neighbor, my inward side, their facing side)
        let (npos, their_side) = if y == 0 {
            (pos + W, 0)
        } else if y == W - 1 {
            (pos - W, 2)
        } else if x == 0 {
            (pos + 1, 3)
        } else {
            (pos - 1, 1)
        };
        let (pid, rot) = interior_place[&npos];
        rim_color.insert(pos, edges_of(pid, rot)[their_side]);
    }

    // border pieces: classify + forced-rotation edge arrays per position class
    let mut corner_pieces: Vec<u16> = Vec::new();
    let mut edge_pieces: Vec<u16> = Vec::new();
    for pid in 0..256u16 {
        let e = puzzle.piece(pid).expect("piece").edges.as_array();
        match e.iter().filter(|&&c| c == BORDER).count() {
            2 => corner_pieces.push(pid),
            1 => edge_pieces.push(pid),
            _ => {}
        }
    }
    assert_eq!(corner_pieces.len(), 4);
    assert_eq!(edge_pieces.len(), 56);

    let corner_positions: Vec<usize> = ring.iter().copied().filter(|&p| is_corner(p)).collect();
    let side_positions: Vec<usize> = ring.iter().copied().filter(|&p| !is_corner(p)).collect();

    // oriented edges of piece p at position q (forced rotation)
    let oriented = |pid: u16, pos: usize| -> Option<[u8; 4]> {
        forced_rotation(pos, puzzle.piece(pid).expect("piece").edges.as_array())
    };

    // ---- MIP ----
    let mut prob = ProblemVariables::new();
    // x[(p, q)] for legal (corner pieces at corner positions, edge at side)
    let mut x: HashMap<(u16, usize), Variable> = HashMap::new();
    for &p in &corner_pieces {
        for &q in &corner_positions {
            if oriented(p, q).is_some() {
                x.insert((p, q), prob.add(variable().binary()));
            }
        }
    }
    for &p in &edge_pieces {
        for &q in &side_positions {
            if oriented(p, q).is_some() {
                x.insert((p, q), prob.add(variable().binary()));
            }
        }
    }
    // ring adjacency pairs (i -> next), with the side each presents
    // ring order is clockwise; piece at ring[i] touches ring[i+1]
    let n_ring = ring.len();
    // lateral side toward the NEXT ring cell, per position
    let side_toward = |from: usize, to: usize| -> usize {
        let (fy, fx) = (from / W, from % W);
        let (ty, tx) = (to / W, to % W);
        if ty == fy {
            if tx == fx + 1 { 1 } else { 3 }
        } else if ty == fy + 1 {
            2
        } else {
            0
        }
    };
    // collect colors that can appear laterally (for z vars)
    let mut z_vars: Vec<(usize, Vec<(u8, Variable)>)> = Vec::new();
    let mut all_pieces_at = |q: usize| -> Vec<u16> {
        if is_corner(q) {
            corner_pieces.clone()
        } else {
            edge_pieces.clone()
        }
    };
    let mut constraints: Vec<good_lp::Constraint> = Vec::new();
    for i in 0..n_ring {
        let a = ring[i];
        let b = ring[(i + 1) % n_ring];
        let sa = side_toward(a, b);
        let sb = side_toward(b, a);
        let mut colors: Vec<u8> = Vec::new();
        for &p in &all_pieces_at(a) {
            if let Some(e) = oriented(p, a) {
                if !colors.contains(&e[sa]) {
                    colors.push(e[sa]);
                }
            }
        }
        let mut zc = Vec::new();
        for c in colors {
            let z = prob.add(variable().binary());
            zc.push((c, z));
        }
        z_vars.push((i, zc));
    }

    // objective: sum z + sum ib coeff * x
    let mut obj = Expression::from(0.0);
    for (_, zc) in &z_vars {
        for &(_, z) in zc {
            obj += z;
        }
    }
    for (&(p, q), &xv) in &x {
        if !is_corner(q) {
            let e = oriented(p, q).expect("legal");
            // inward side: opposite the grey side
            let (y, xx) = (q / W, q % W);
            let inward = if y == 0 {
                2
            } else if y == W - 1 {
                0
            } else if xx == 0 {
                1
            } else {
                3
            };
            if rim_color[&q] == e[inward] {
                obj += xv;
            }
        }
    }

    // assignment constraints
    for &p in corner_pieces.iter().chain(edge_pieces.iter()) {
        let mut s = Expression::from(0.0);
        for ((pp, q), &xv) in &x {
            if *pp == p {
                let _ = q;
                s += xv;
            }
        }
        constraints.push(constraint!(s == 1.0));
    }
    for &q in corner_positions.iter().chain(side_positions.iter()) {
        let mut s = Expression::from(0.0);
        for ((p, qq), &xv) in &x {
            if *qq == q {
                let _ = p;
                s += xv;
            }
        }
        constraints.push(constraint!(s == 1.0));
    }
    // optional: force a PERFECT ring (all 60 BB edges matched)
    if args.iter().any(|a| a == "--require-bb60") {
        let mut all_z = Expression::from(0.0);
        for (_, zc) in &z_vars {
            for &(_, z) in zc {
                all_z += z;
            }
        }
        constraints.push(constraint!(all_z == 60.0));
    }
    // z linking
    for (i, zc) in &z_vars {
        let a = ring[*i];
        let b = ring[(*i + 1) % n_ring];
        let sa = side_toward(a, b);
        let sb = side_toward(b, a);
        let mut z_sum = Expression::from(0.0);
        for &(c, z) in zc {
            let mut sup_a = Expression::from(0.0);
            for &p in &all_pieces_at(a) {
                if let Some(e) = oriented(p, a) {
                    if e[sa] == c {
                        if let Some(&xv) = x.get(&(p, a)) {
                            sup_a += xv;
                        }
                    }
                }
            }
            let mut sup_b = Expression::from(0.0);
            for &p in &all_pieces_at(b) {
                if let Some(e) = oriented(p, b) {
                    if e[sb] == c {
                        if let Some(&xv) = x.get(&(p, b)) {
                            sup_b += xv;
                        }
                    }
                }
            }
            constraints.push(constraint!(z - sup_a <= 0.0));
            constraints.push(constraint!(z - sup_b <= 0.0));
            z_sum += z;
        }
        constraints.push(constraint!(z_sum <= 1.0));
    }

    let mut model = prob.maximise(obj.clone()).using(highs);
    model = model.set_time_limit(time_limit);
    model = model.set_parallel(good_lp::solvers::highs::HighsParallelType::On);
    for c in constraints {
        model = model.with(c);
    }
    eprintln!("solving border-attach MIP (time limit {time_limit}s)...");
    let sol = model.solve().expect("MIP solve");
    let obj_val = sol.eval(&obj);

    // extract assignment
    let mut border_place: HashMap<usize, (u16, u8)> = HashMap::new();
    for (&(p, q), &xv) in &x {
        if sol.value(xv) > 0.5 {
            // recover the forced rotation index
            let base = puzzle.piece(p).expect("piece").edges.as_array();
            let target = oriented(p, q).expect("legal");
            for r in 0..4u8 {
                let e: [u8; 4] = core::array::from_fn(|s| base[(s + 4 - r as usize) % 4]);
                if e == target {
                    border_place.insert(q, (p, r));
                    break;
                }
            }
        }
    }
    assert_eq!(border_place.len(), 60, "full border assignment");

    // assemble + score
    let mut full: Vec<(usize, u16, u8)> = Vec::new();
    for (&pos, &(p, r)) in interior_place.iter().chain(border_place.iter()) {
        full.push((pos, p, r));
    }
    full.sort_unstable();
    let edge_at = |pos: usize, full: &[(usize, u16, u8)]| -> [u8; 4] {
        let i = full.binary_search_by_key(&pos, |&(p, _, _)| p).expect("pos");
        edges_of(full[i].1, full[i].2)
    };
    let (mut ii, mut ib, mut bb) = (0u32, 0u32, 0u32);
    for y in 0..W {
        for x_ in 0..W {
            let pos = y * W + x_;
            let e = edge_at(pos, &full);
            if x_ + 1 < W {
                let ne = edge_at(pos + 1, &full);
                if e[1] == ne[3] && e[1] != BORDER {
                    let per = |p: usize| p / W == 0 || p / W == W - 1 || p % W == 0 || p % W == W - 1;
                    match (per(pos), per(pos + 1)) {
                        (true, true) => bb += 1,
                        (false, false) => ii += 1,
                        _ => ib += 1,
                    }
                }
            }
            if y + 1 < W {
                let ne = edge_at(pos + W, &full);
                if e[2] == ne[0] && e[2] != BORDER {
                    let per = |p: usize| p / W == 0 || p / W == W - 1 || p % W == 0 || p % W == W - 1;
                    match (per(pos), per(pos + W)) {
                        (true, true) => bb += 1,
                        (false, false) => ii += 1,
                        _ => ib += 1,
                    }
                }
            }
        }
    }
    let total = ii + ib + bb;
    println!(
        "border-attach: obj={obj_val:.1}  ->  II={ii}/364  IB={ib}/56  BB={bb}/60  TOTAL={total}/480"
    );

    // save assembled board
    let ts = {
        use std::time::{SystemTime, UNIX_EPOCH};
        SystemTime::now().duration_since(UNIX_EPOCH).expect("clock").as_secs()
    };
    let out_dir = PathBuf::from(
        get("--out-dir").unwrap_or_else(|| format!("output/vol-211/border_attach_{ts}")),
    );
    std::fs::create_dir_all(&out_dir).expect("mkdir");
    let stem = PathBuf::from(&path)
        .file_stem()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| "interior".into());
    let mut placement = Vec::new();
    let mut url_edges = String::new();
    for &(pos, p, r) in &full {
        placement.push(format!(
            "{{\"pos\":{pos},\"piece_id\":{p},\"rotation\":{r}}}"
        ));
        let e = edges_of(p, r);
        for c in e {
            url_edges.push((b'a' + c) as char);
        }
    }
    let url = format!(
        "https://e2.bucas.name/#puzzle=Eternity2&board_w=16&board_h=16&board_edges={url_edges}"
    );
    let json = format!(
        "{{\"matched\":{total},\"ii\":{ii},\"ib\":{ib},\"bb\":{bb},\"source\":\"cloister_border:{path}\",\"bucas_url\":\"{url}\",\"placement\":[{}]}}",
        placement.join(",")
    );
    let out = out_dir.join(format!("ATTACHED_{total}_{stem}.json"));
    std::fs::write(&out, json).expect("write");
    std::fs::write(out.with_extension("url.txt"), format!("{url}\n")).expect("url");
    println!("saved {}", out.display());

    // history
    let hist = PathBuf::from("output/vol-211/cloister_history.csv");
    let new = !hist.exists();
    let mut f = std::fs::OpenOptions::new().create(true).append(true).open(&hist).expect("hist");
    if new {
        writeln!(f, "timestamp,mode,seed,interior_ii,params,run_dir,board,bucas_url").expect("hdr");
    }
    writeln!(
        f,
        "{ts},border_attach,0,{ii},total={total};ib={ib};bb={bb},{},{},{url}",
        out_dir.display(),
        out.display()
    )
    .expect("row");
}
