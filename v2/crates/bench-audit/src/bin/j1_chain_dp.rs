// Vol-122 J1 v6 — Rust chain over all bands.
//
// Sequential band processing: band 0, then band 1 (with top fixed from
// band 0's bottom), etc. Saves the full board.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use serde_json::json;
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug)]
struct PieceRot {
    pid: u16,
    rot: u8,
    edges: [u8; 4],
}

#[derive(Clone, Copy, Default, Debug, PartialEq, Eq, Hash)]
struct PieceSet {
    low: u128,
    high: u128,
}

impl PieceSet {
    fn new() -> Self { Self { low: 0, high: 0 } }
    #[inline]
    fn set(&mut self, pid: u16) {
        if pid < 128 { self.low |= 1u128 << pid; }
        else { self.high |= 1u128 << (pid - 128); }
    }
    #[inline]
    fn contains(&self, pid: u16) -> bool {
        if pid < 128 { (self.low >> pid) & 1 == 1 }
        else { (self.high >> (pid - 128)) & 1 == 1 }
    }
    fn with(&self, pid: u16) -> Self {
        let mut s = *self;
        s.set(pid);
        s
    }
}

#[derive(Clone, Debug)]
struct State {
    top: PieceRot,
    bot: PieceRot,
    used: PieceSet,
    score: u32,
    parent_idx: i32,
}

/// Solve a single band, allowing fixed top row (per column).
fn solve_band(
    pieces: &[[u8; 4]],
    side: usize,
    top_row: usize,
    bot_row: usize,
    fixed_top: Option<&BTreeMap<usize, PieceRot>>,
    initial_used: PieceSet,
    beam: usize,
    time_limit: std::time::Duration,
) -> Option<(u32, Vec<(u16, u8)>, Vec<(u16, u8)>)> {
    let n_pieces = pieces.len();

    let mut all_options: Vec<PieceRot> = Vec::with_capacity(n_pieces * 4);
    for pid in 0..n_pieces {
        for rot in 0..4u8 {
            let e = pieces[pid];
            let rotated: [u8; 4] = match rot {
                0 => e,
                1 => [e[3], e[0], e[1], e[2]],
                2 => [e[2], e[3], e[0], e[1]],
                _ => [e[1], e[2], e[3], e[0]],
            };
            all_options.push(PieceRot { pid: pid as u16, rot, edges: rotated });
        }
    }

    let valid_top_at = |opt: &PieceRot, col: usize| -> bool {
        let e = opt.edges;
        let is_top_border = top_row == 0;
        if is_top_border && e[0] != 0 { return false; }
        if !is_top_border && e[0] == 0 { return false; }
        if col == 0 && e[3] != 0 { return false; }
        if col != 0 && e[3] == 0 { return false; }
        if col == side - 1 && e[1] != 0 { return false; }
        if col != side - 1 && e[1] == 0 { return false; }
        true
    };
    let valid_bot_at = |opt: &PieceRot, col: usize| -> bool {
        let e = opt.edges;
        let is_bot_border = bot_row == side - 1;
        if is_bot_border && e[2] != 0 { return false; }
        if !is_bot_border && e[2] == 0 { return false; }
        if col == 0 && e[3] != 0 { return false; }
        if col != 0 && e[3] == 0 { return false; }
        if col == side - 1 && e[1] != 0 { return false; }
        if col != side - 1 && e[1] == 0 { return false; }
        true
    };

    let max_color = pieces.iter().flat_map(|p| p.iter()).max().copied().unwrap_or(22) as usize;
    let mut top_by_l: Vec<Vec<Vec<PieceRot>>> = (0..side)
        .map(|_| (0..=max_color).map(|_| Vec::new()).collect())
        .collect();
    let mut bot_by_l: Vec<Vec<Vec<PieceRot>>> = (0..side)
        .map(|_| (0..=max_color).map(|_| Vec::new()).collect())
        .collect();
    for col in 0..side {
        if let Some(ft) = fixed_top {
            if let Some(p) = ft.get(&col) {
                top_by_l[col][p.edges[3] as usize].push(*p);
                // No alternatives; top is fixed.
                for opt in &all_options {
                    if valid_bot_at(opt, col) {
                        bot_by_l[col][opt.edges[3] as usize].push(*opt);
                    }
                }
                continue;
            }
        }
        for opt in &all_options {
            if valid_top_at(opt, col) {
                top_by_l[col][opt.edges[3] as usize].push(*opt);
            }
            if valid_bot_at(opt, col) {
                bot_by_l[col][opt.edges[3] as usize].push(*opt);
            }
        }
    }

    // Col 0 setup
    let top_col0: Vec<PieceRot> = if let Some(ft) = fixed_top {
        if let Some(p) = ft.get(&0) { vec![*p] } else { all_options.iter().filter(|o| valid_top_at(o, 0)).cloned().collect() }
    } else {
        all_options.iter().filter(|o| valid_top_at(o, 0)).cloned().collect()
    };
    let bot_col0: Vec<PieceRot> = all_options.iter().filter(|o| valid_bot_at(o, 0)).cloned().collect();

    let mut states_per_col: Vec<Vec<State>> = Vec::with_capacity(side);
    let mut col0_states: Vec<State> = Vec::new();
    for ot in &top_col0 {
        if initial_used.contains(ot.pid) { continue; }
        for ob in &bot_col0 {
            if ob.pid == ot.pid { continue; }
            if initial_used.contains(ob.pid) { continue; }
            let mut score = 0u32;
            if ot.edges[2] == ob.edges[0] && ot.edges[2] != 0 {
                score += 1;
            }
            let used = initial_used.with(ot.pid).with(ob.pid);
            col0_states.push(State {
                top: *ot, bot: *ob, used, score, parent_idx: -1,
            });
        }
    }
    col0_states.sort_unstable_by_key(|s| std::cmp::Reverse(s.score));
    col0_states.truncate(beam);
    if col0_states.is_empty() { return None; }
    states_per_col.push(col0_states);

    let t_start = Instant::now();
    for j in 1..side {
        if t_start.elapsed() > time_limit {
            eprintln!("  TIME LIMIT at col {}", j);
            return None;
        }
        let prev_idx = j - 1;
        let prev_len = states_per_col[prev_idx].len();
        let mut new_states: Vec<State> = Vec::new();
        new_states.reserve(prev_len * 20);
        for parent_idx in 0..prev_len {
            let s = &states_per_col[prev_idx][parent_idx];
            let req_top_l = s.top.edges[1] as usize;
            let req_bot_l = s.bot.edges[1] as usize;
            let s_used = s.used;
            let s_score = s.score;
            for ot in &top_by_l[j][req_top_l] {
                if s_used.contains(ot.pid) { continue; }
                for ob in &bot_by_l[j][req_bot_l] {
                    if ob.pid == ot.pid { continue; }
                    if s_used.contains(ob.pid) { continue; }
                    let mut new_sc = s_score;
                    if req_top_l != 0 { new_sc += 1; }
                    if req_bot_l != 0 { new_sc += 1; }
                    if ot.edges[2] == ob.edges[0] && ot.edges[2] != 0 {
                        new_sc += 1;
                    }
                    let new_used = s_used.with(ot.pid).with(ob.pid);
                    new_states.push(State {
                        top: *ot, bot: *ob, used: new_used, score: new_sc,
                        parent_idx: parent_idx as i32,
                    });
                }
            }
        }
        new_states.sort_unstable_by_key(|s| std::cmp::Reverse(s.score));
        new_states.truncate(beam);
        if new_states.is_empty() {
            eprintln!("  col {}: NO STATES", j);
            return None;
        }
        states_per_col.push(new_states);
    }

    let last = &states_per_col[side - 1];
    let best = &last[0];
    let final_score = best.score;
    let mut top_row_assign = vec![(0u16, 0u8); side];
    let mut bot_row_assign = vec![(0u16, 0u8); side];
    let mut cur = best.clone();
    let mut cur_col = side - 1;
    loop {
        top_row_assign[cur_col] = (cur.top.pid, cur.top.rot);
        bot_row_assign[cur_col] = (cur.bot.pid, cur.bot.rot);
        if cur_col == 0 { break; }
        cur = states_per_col[cur_col - 1][cur.parent_idx as usize].clone();
        cur_col -= 1;
    }
    Some((final_score, top_row_assign, bot_row_assign))
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut beam: usize = 5000;
    let mut time_per_band_secs: u64 = 60;
    let mut out_path = PathBuf::from("output/vol-122/j1_rust_chain.json");

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--beam" => beam = args.next().unwrap().parse().unwrap(),
            "--time-per-band" => time_per_band_secs = args.next().unwrap().parse().unwrap(),
            "--out" => out_path = PathBuf::from(args.next().unwrap()),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let side = puzzle.width as usize;
    println!("puzzle: {} side={} beam={} time/band={}s",
        puzzle_path.display(), side, beam, time_per_band_secs);

    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::from_u8(0).unwrap()).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    let mut full_board: BTreeMap<(usize, usize), (u16, u8)> = BTreeMap::new();
    let mut used = PieceSet::new();
    let mut fixed_top: Option<BTreeMap<usize, PieceRot>> = None;
    let mut total_score: u32 = 0;
    let t_total = Instant::now();

    for band_idx in 0..(side - 1) {
        let top_row = band_idx;
        let bot_row = band_idx + 1;
        println!("\n=== BAND {} (rows {}, {}) ===", band_idx, top_row, bot_row);
        let t0 = Instant::now();
        // When fixed_top set, those pieces are NOT in "initial_used" because they're being re-placed
        // in this band. Remove them.
        let mut initial_used = used;
        if let Some(ft) = &fixed_top {
            for (_, p) in ft.iter() {
                if initial_used.contains(p.pid) {
                    // can't unset bit in our PieceSet easily; just track separately
                }
            }
        }
        // Simpler: rebuild from full_board excluding the row being re-placed (= row top_row).
        let mut initial_used = PieceSet::new();
        for ((r, _), (pid, _)) in full_board.iter() {
            if *r != top_row {
                initial_used.set(*pid);
            }
        }

        let result = solve_band(&pieces, side, top_row, bot_row,
            fixed_top.as_ref(), initial_used, beam,
            std::time::Duration::from_secs(time_per_band_secs));
        let elapsed = t0.elapsed();
        let max_band = 3 * side - 2;
        match result {
            Some((score, top_assign, bot_assign)) => {
                println!("  score: {} / {}  elapsed: {:.2}s", score, max_band, elapsed.as_secs_f64());
                for c in 0..side {
                    if !full_board.contains_key(&(top_row, c)) {
                        full_board.insert((top_row, c), top_assign[c]);
                        used.set(top_assign[c].0);
                    }
                    full_board.insert((bot_row, c), bot_assign[c]);
                    used.set(bot_assign[c].0);
                }
                total_score += score;
                // Build fixed_top for next band: this band's bottom row
                let mut next_ft = BTreeMap::new();
                for c in 0..side {
                    let (pid, rot) = bot_assign[c];
                    let e = pieces[pid as usize];
                    let rotated: [u8; 4] = match rot {
                        0 => e,
                        1 => [e[3], e[0], e[1], e[2]],
                        2 => [e[2], e[3], e[0], e[1]],
                        _ => [e[1], e[2], e[3], e[0]],
                    };
                    next_ft.insert(c, PieceRot { pid, rot, edges: rotated });
                }
                fixed_top = Some(next_ft);
            }
            None => {
                println!("  BAND FAILED. Stopping.");
                break;
            }
        }
    }

    println!("\n=== TOTAL ===");
    println!("total band scores: {}", total_score);
    println!("full board placements: {}", full_board.len());
    println!("total elapsed: {:.2}s", t_total.elapsed().as_secs_f64());

    let placement: Vec<_> = full_board.iter().map(|((r, c), (pid, rot))| {
        json!({"pos": r * side + c, "piece_id": *pid as u32, "rotation": *rot as u32})
    }).collect();
    let out = json!({
        "source": "vol122_j1_rust_chain",
        "n_placed": full_board.len(),
        "total_band_score": total_score,
        "placement": placement,
    });
    std::fs::create_dir_all(out_path.parent().unwrap()).ok();
    std::fs::write(&out_path, serde_json::to_string_pretty(&out).unwrap()).unwrap();
    println!("wrote: {}", out_path.display());
}
