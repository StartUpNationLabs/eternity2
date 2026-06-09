// CRUCIBLE — exact-repair LNS with global piece rebalance (vol-207).
//
// New search operator class: dissolve a region, re-solve it EXACTLY (MaxScore
// DFS+B&B) against its fixed boundary, optionally pulling DONOR pieces from
// mismatched cells elsewhere (global rebalance) so pieces FLOW between regions.
// This attacks the sigma-lock that heuristic-repair ALNS and fixed-region
// cluster-repair both hit: exact repair + cross-region piece flow.
//
// Usage:
//   crucible --board IN.json [--win 4] [--iters N] [--rebalance K] [--seed S]
//            [--out DIR] [--time-ms MS]

use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Color, Puzzle, Rotation, BORDER};
use eternity2_export::{bucas_url, load_board, save_board, BoardMetadata};

const N_: usize = 0;
const E_: usize = 1;
const S_: usize = 2;
const W_: usize = 3;

#[inline]
fn rot_edges(base: [Color; 4], r: u8) -> [Color; 4] {
    let r = r as usize;
    [base[(N_ + 4 - r) % 4], base[(E_ + 4 - r) % 4], base[(S_ + 4 - r) % 4], base[(W_ + 4 - r) % 4]]
}

struct Inst { size: usize, np: usize, base: Vec<[Color; 4]>, border_sides: Vec<Vec<usize>> }

impl Inst {
    fn new(puzzle: &Puzzle) -> Self {
        let size = puzzle.width as usize;
        let np = puzzle.pieces().len();
        let base: Vec<[Color; 4]> = puzzle.pieces().iter().map(|p| p.edges.as_array()).collect();
        let border_sides = (0..np).map(|p| (0..4).filter(|&s| base[p][s] == BORDER).collect()).collect();
        Inst { size, np, base, border_sides }
    }
    fn must_border(&self, cell: usize) -> Vec<usize> {
        let (x, y) = (cell % self.size, cell / self.size);
        let mut s = Vec::new();
        if y == 0 { s.push(N_); }
        if y == self.size - 1 { s.push(S_); }
        if x == 0 { s.push(W_); }
        if x == self.size - 1 { s.push(E_); }
        s.sort_unstable();
        s
    }
}

#[derive(Clone, Copy)]
struct Cand { p: usize, r: u8, e: [Color; 4] }

// Exact MaxScore solve of `cells` given a fixed surrounding board `place` and a
// pool of usable pieces. Boundary = edges to placed cells OUTSIDE `cells` (HARD
// scored: we maximize internal + boundary matches). Returns (assignment, matched)
// where matched counts the edges incident to `cells` (internal + boundary).
#[allow(clippy::too_many_arguments)]
fn solve_region(
    inst: &Inst,
    cells: &[usize],
    pool: &[bool],
    place: &[Option<(usize, u8)>],
    pe: &[Option<[Color; 4]>],
    seed: u64,
    node_cap: u64,
) -> Option<Vec<(usize, usize, u8)>> {
    let n = cells.len();
    let cellset: std::collections::HashSet<usize> = cells.iter().copied().collect();
    let mix = |mut z: u64| -> u64 {
        z = z.wrapping_add(0x9E37_79B9_7F4A_7C15);
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    };
    let mut cand: Vec<Vec<Cand>> = Vec::with_capacity(n);
    for &c in cells {
        let mb = inst.must_border(c);
        let mut lst = Vec::new();
        for p in 0..inst.np {
            if !pool[p] { continue; }
            if inst.border_sides[p].len() != mb.len() { continue; }
            for r in 0..4u8 {
                let e = rot_edges(inst.base[p], r);
                let bs: Vec<usize> = (0..4).filter(|&s| e[s] == BORDER).collect();
                if bs != mb { continue; }
                lst.push(Cand { p, r, e });
            }
        }
        if lst.is_empty() { return None; }
        if seed != 0 {
            lst.sort_by_key(|cd| mix(seed ^ ((c as u64) << 20) ^ ((cd.p as u64) << 2) ^ cd.r as u64));
        }
        cand.push(lst);
    }
    // boundary demands: for each region cell, the (side -> color) of placed
    // OUTSIDE neighbors. Scored as matches.
    let mut bnd: Vec<Vec<(usize, Color)>> = vec![Vec::new(); n];
    for (i, &c) in cells.iter().enumerate() {
        let (x, y) = (c % inst.size, c / inst.size);
        let mut v = Vec::new();
        if y > 0 && !cellset.contains(&(c - inst.size)) { if let Some(e) = pe[c - inst.size] { v.push((N_, e[S_])); } }
        if y + 1 < inst.size && !cellset.contains(&(c + inst.size)) { if let Some(e) = pe[c + inst.size] { v.push((S_, e[N_])); } }
        if x > 0 && !cellset.contains(&(c - 1)) { if let Some(e) = pe[c - 1] { v.push((W_, e[E_])); } }
        if x + 1 < inst.size && !cellset.contains(&(c + 1)) { if let Some(e) = pe[c + 1] { v.push((E_, e[W_])); } }
        bnd[i] = v;
    }
    // internal edges among region cells
    let pos_of: HashMap<usize, usize> = cells.iter().enumerate().map(|(i, &c)| (c, i)).collect();
    let mut edges_closing_at: Vec<Vec<(usize, usize, usize, usize)>> = vec![Vec::new(); n];
    let mut total_int = 0usize;
    for (i, &c) in cells.iter().enumerate() {
        let (x, y) = (c % inst.size, c / inst.size);
        if x + 1 < inst.size && cellset.contains(&(c + 1)) {
            let j = pos_of[&(c + 1)]; edges_closing_at[i.max(j)].push((i, E_, j, W_)); total_int += 1;
        }
        if y + 1 < inst.size && cellset.contains(&(c + inst.size)) {
            let j = pos_of[&(c + inst.size)]; edges_closing_at[i.max(j)].push((i, S_, j, N_)); total_int += 1;
        }
    }
    let total_bnd: usize = bnd.iter().map(|v| v.len()).sum();
    let max_possible = (total_int + total_bnd) as i32;
    let mut used_local = vec![false; inst.np];
    let mut chosen = vec![usize::MAX; n];
    let mut best = -1i32;
    let mut best_choice = vec![0usize; n];
    let mut nodes = 0u64;

    #[allow(clippy::too_many_arguments)]
    fn dfs(idx: usize, n: usize, cand: &Vec<Vec<Cand>>, bnd: &Vec<Vec<(usize, Color)>>,
           eca: &Vec<Vec<(usize, usize, usize, usize)>>, chosen: &mut Vec<usize>,
           used_local: &mut Vec<bool>, matched: i32, rem: i32, best: &mut i32,
           best_choice: &mut Vec<usize>, nodes: &mut u64, cap: u64) {
        if *nodes >= cap { return; }
        if matched + rem <= *best { return; }
        if idx == n { if matched > *best { *best = matched; best_choice.copy_from_slice(&chosen[..n]); } return; }
        let cl = &eca[idx];
        let child_rem = rem - cl.len() as i32 - bnd[idx].len() as i32;
        for ci in 0..cand[idx].len() {
            let c = cand[idx][ci];
            if used_local[c.p] { continue; }
            let mut gain = 0i32;
            for &(side, col) in &bnd[idx] { if c.e[side] == col { gain += 1; } }
            for &(a, sa, b, sb) in cl {
                let (ms, oi, os) = if a == idx { (sa, b, sb) } else { (sb, a, sa) };
                if c.e[ms] == cand[oi][chosen[oi]].e[os] { gain += 1; }
            }
            *nodes += 1;
            chosen[idx] = ci; used_local[c.p] = true;
            dfs(idx + 1, n, cand, bnd, eca, chosen, used_local, matched + gain, child_rem, best, best_choice, nodes, cap);
            used_local[c.p] = false;
            if *nodes >= cap { break; }
        }
        chosen[idx] = usize::MAX;
    }
    dfs(0, n, &cand, &bnd, &edges_closing_at, &mut chosen, &mut used_local, 0, max_possible, &mut best, &mut best_choice, &mut nodes, node_cap);
    if best < 0 { return None; }
    Some((0..n).map(|i| { let c = cand[i][best_choice[i]]; (cells[i], c.p, c.r) }).collect())
}

fn score(inst: &Inst, pe: &[Option<[Color; 4]>]) -> i32 {
    let size = inst.size;
    let mut m = 0;
    for c in 0..size * size {
        let (x, y) = (c % size, c / size);
        if x + 1 < size { if let (Some(a), Some(b)) = (pe[c], pe[c + 1]) { if a[E_] == b[W_] { m += 1; } } }
        if y + 1 < size { if let (Some(a), Some(b)) = (pe[c], pe[c + size]) { if a[S_] == b[N_] { m += 1; } } }
    }
    m
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut board_path = String::new();
    let mut win = 4usize;
    let mut iters = 100000usize;
    let mut time_ms = 120000u128;
    let mut seed = 1u64;
    let mut rebalance = 0usize;
    let mut out = String::new();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--board" => { board_path = args[i + 1].clone(); i += 2; }
            "--win" => { win = args[i + 1].parse().unwrap(); i += 2; }
            "--iters" => { iters = args[i + 1].parse().unwrap(); i += 2; }
            "--time-ms" => { time_ms = args[i + 1].parse().unwrap(); i += 2; }
            "--seed" => { seed = args[i + 1].parse().unwrap(); i += 2; }
            "--rebalance" => { rebalance = args[i + 1].parse().unwrap(); i += 2; }
            "--out" => { out = args[i + 1].clone(); i += 2; }
            other => { eprintln!("unknown arg {other}"); i += 1; }
        }
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _h) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let inst = Inst::new(&puzzle);
    let size = inst.size;
    let board0 = load_board(&PathBuf::from(&board_path), &puzzle).expect("load board");
    let mut place: Vec<Option<(usize, u8)>> = vec![None; size * size];
    let mut pe: Vec<Option<[Color; 4]>> = vec![None; size * size];
    for c in 0..size * size {
        if let Some((pid, rot)) = board0.get(c as u32) {
            place[c] = Some((pid as usize, rot.as_u8()));
            pe[c] = Some(rot_edges(inst.base[pid as usize], rot.as_u8()));
        }
    }
    let start_score = score(&inst, &pe);
    eprintln!("CRUCIBLE win={win} start_score={start_score}/480 board={board_path}");
    let node_cap: u64 = std::env::var("CRUCIBLE_NODECAP").ok().and_then(|s| s.parse().ok()).unwrap_or(20_000_000);
    let t0 = Instant::now();
    let mut cur = start_score;
    let mut rng = seed;
    let mix = |z: u64| { let mut z = z.wrapping_add(0x9E37_79B9_7F4A_7C15); z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9); z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB); z ^ (z >> 31) };
    let mut it = 0usize;
    let mut improvements = 0usize;
    let mut lateral_moves = 0usize;
    while it < iters && t0.elapsed().as_millis() < time_ms {
        it += 1;
        rng = mix(rng);
        // pick a random win×win window top-left
        let wy = (rng as usize) % (size - win + 1);
        rng = mix(rng);
        let wx = (rng as usize) % (size - win + 1);
        let mut cells: Vec<usize> = (0..win).flat_map(|dy| (0..win).map(move |dx| (dy, dx)))
            .map(|(dy, dx)| (wy + dy) * size + (wx + dx)).collect();
        // GLOBAL REBALANCE: add `rebalance` donor cells from mismatched cells
        // ELSEWHERE on the board. Their pieces enter the pool, so the exact solve
        // can pull them into the region (and a leftover region piece flows to the
        // donor cell). This is the cross-region piece flow that fixed-region repair
        // cannot do — the key to escaping the local optimum.
        if rebalance > 0 {
            let inset: std::collections::HashSet<usize> = cells.iter().copied().collect();
            // collect mismatched cells outside the window
            let mut mis: Vec<usize> = Vec::new();
            for c in 0..size * size {
                if inset.contains(&c) { continue; }
                let (x, y) = (c % size, c / size);
                let mut bad = false;
                if x + 1 < size { if let (Some(a), Some(b)) = (pe[c], pe[c + 1]) { if a[E_] != b[W_] { bad = true; } } }
                if x > 0 { if let (Some(a), Some(b)) = (pe[c], pe[c - 1]) { if a[W_] != b[E_] { bad = true; } } }
                if y + 1 < size { if let (Some(a), Some(b)) = (pe[c], pe[c + size]) { if a[S_] != b[N_] { bad = true; } } }
                if y > 0 { if let (Some(a), Some(b)) = (pe[c], pe[c - size]) { if a[N_] != b[S_] { bad = true; } } }
                if bad { mis.push(c); }
            }
            // pick `rebalance` random donor cells from mismatched ones
            for _ in 0..rebalance {
                if mis.is_empty() { break; }
                rng = mix(rng);
                let idx = (rng as usize) % mis.len();
                let dc = mis.swap_remove(idx);
                if !cells.contains(&dc) { cells.push(dc); }
            }
        }
        // pool = current pieces of ALL cells being re-solved (region + donors)
        let mut pool = vec![false; inst.np];
        for &c in &cells { if let Some((p, _)) = place[c] { pool[p] = true; } }
        // snapshot region for rollback / improvement test
        let before: Vec<(usize, Option<(usize, u8)>, Option<[Color; 4]>)> =
            cells.iter().map(|&c| (c, place[c], pe[c])).collect();
        rng = mix(rng);
        if let Some(assign) = solve_region(&inst, &cells, &pool, &place, &pe, rng, node_cap) {
            // count how many cells actually CHANGED piece (proves rebalance/flow active)
            let mut changed = 0;
            for &(c, p, _r) in &assign { if before.iter().find(|x| x.0 == c).and_then(|x| x.1).map(|pr| pr.0) != Some(p) { changed += 1; } }
            for &(c, p, r) in &assign { place[c] = Some((p, r)); pe[c] = Some(rot_edges(inst.base[p], r)); }
            let ns = score(&inst, &pe);
            if ns > cur {
                cur = ns; improvements += 1;
            } else if ns < cur {
                for (c, pl, e) in &before { place[*c] = *pl; pe[*c] = *e; }
            } else {
                // equal: keep (lateral walk). count lateral moves that changed pieces.
                if changed > 0 { lateral_moves += 1; }
            }
        }
    }
    let final_score = score(&inst, &pe);
    eprintln!("CRUCIBLE done: {start_score} -> {final_score} ({improvements} improving, {lateral_moves} lateral-piece-moves, {it} iters, {:.0}s)", t0.elapsed().as_secs_f64());
    let mut board = Board::empty(&puzzle);
    for c in 0..size * size { if let Some((p, r)) = place[c] { board.place(c as u32, p as u16, Rotation::from_u8(r).unwrap()); } }
    println!("matched={final_score}/480");
    let url = bucas_url(&puzzle, &board, "crucible");
    println!("bucas: {url}");
    if !out.is_empty() {
        let dir = PathBuf::from(&out); std::fs::create_dir_all(&dir).ok();
        let path = dir.join(format!("crucible_win{win}_s{seed}_m{final_score}.json"));
        let md = BoardMetadata { source: Some(format!("crucible win={win} from {board_path}")), ..Default::default() };
        save_board(&path, &puzzle, &board, &md).expect("save");
        println!("saved -> {}", path.display());
    }
}
