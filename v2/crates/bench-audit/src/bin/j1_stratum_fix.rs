// Vol-122 J1 stratum-fix: rebuild rows `freeze_row+1..side-1` with the upper
// frozen, attempting to improve the lower-stratum internal score.
//
// From j1-loss-localization-math: J1 boards have perfect inner-row horizontals
// AND perfect V_0..V_7. The 36 missing edges are concentrated in V_8..V_14.
// This binary surgically rebuilds the lower stratum using J1 column-DP with
// fixed interface row.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;
use serde_json::{json, Value};
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

fn rotate_edges(e: [u8; 4], rot: u8) -> [u8; 4] {
    match rot {
        0 => e,
        1 => [e[3], e[0], e[1], e[2]],
        2 => [e[2], e[3], e[0], e[1]],
        _ => [e[1], e[2], e[3], e[0]],
    }
}

fn solve_band(
    pieces: &[[u8; 4]],
    side: usize,
    top_row: usize,
    bot_row: usize,
    fixed_top: Option<&BTreeMap<usize, PieceRot>>,
    initial_used: PieceSet,
    beam: usize,
    time_limit: std::time::Duration,
    use_flh: bool,
    flh_consider: usize,
    flh_score_weight: i64,
    flh_compat_weight: i64,
) -> Option<(u32, Vec<(u16, u8)>, Vec<(u16, u8)>)> {
    let n_pieces = pieces.len();

    let mut all_options: Vec<PieceRot> = Vec::with_capacity(n_pieces * 4);
    for pid in 0..n_pieces {
        for rot in 0..4u8 {
            let rotated = rotate_edges(pieces[pid], rot);
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
        eprintln!("  col {}: {} kept, max score {}", j, new_states.len(), new_states[0].score);
        states_per_col.push(new_states);
    }

    let last = &states_per_col[side - 1];

    // FLH: pick best state from top-K by combined (100*score + future_compat).
    let mut color_top_supply: Vec<u32> = vec![0; max_color + 1];
    for pid in 0..n_pieces {
        if initial_used.contains(pid as u16) { continue; }
        for rot in 0..4u8 {
            let rotated_top = match rot {
                0 => pieces[pid][0],
                1 => pieces[pid][3],
                2 => pieces[pid][2],
                _ => pieces[pid][1],
            };
            if rotated_top != 0 {
                color_top_supply[rotated_top as usize] += 1;
            }
        }
    }
    let n_consider = if use_flh { flh_consider.min(last.len()) } else { 1 };
    let mut best_idx = 0;
    let mut best_combined = i64::MIN;
    for k in 0..n_consider {
        let s = &last[k];
        let mut bot_colors = vec![0u8; side];
        let mut cur = s.clone();
        let mut cur_col = side - 1;
        loop {
            bot_colors[cur_col] = cur.bot.edges[2];
            if cur_col == 0 { break; }
            cur = states_per_col[cur_col - 1][cur.parent_idx as usize].clone();
            cur_col -= 1;
        }
        let mut supply = color_top_supply.clone();
        for pid in 0..n_pieces {
            if s.used.contains(pid as u16) && !initial_used.contains(pid as u16) {
                for rot in 0..4u8 {
                    let rotated_top = match rot {
                        0 => pieces[pid][0],
                        1 => pieces[pid][3],
                        2 => pieces[pid][2],
                        _ => pieces[pid][1],
                    };
                    if rotated_top != 0 && supply[rotated_top as usize] > 0 {
                        supply[rotated_top as usize] -= 1;
                    }
                }
            }
        }
        let mut compat = 0i64;
        for c in 0..side {
            let needed = bot_colors[c];
            if needed != 0 && supply[needed as usize] > 0 { compat += 1; }
        }
        let combined = flh_score_weight * s.score as i64 + flh_compat_weight * compat;
        if combined > best_combined {
            best_combined = combined;
            best_idx = k;
        }
    }
    let best = &last[best_idx];
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
    let mut input_board = PathBuf::from("output/vol-122/j1_rust_flh.json");
    let mut freeze_through_row: usize = 7; // freeze rows 0..=7, rebuild 8..=15
    let mut beam: usize = 100_000;
    let mut time_per_band_secs: u64 = 120;
    let mut out_path = PathBuf::from("output/vol-122/j1_stratum_fix.json");
    let mut flh_consider: usize = 1; // 1 = no FLH; default to ablated for sanity
    let mut flh_score_weight: i64 = 100;
    let mut flh_compat_weight: i64 = 1;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--input" => input_board = PathBuf::from(args.next().unwrap()),
            "--freeze-through" => freeze_through_row = args.next().unwrap().parse().unwrap(),
            "--beam" => beam = args.next().unwrap().parse().unwrap(),
            "--time-per-band" => time_per_band_secs = args.next().unwrap().parse().unwrap(),
            "--out" => out_path = PathBuf::from(args.next().unwrap()),
            "--flh-consider" => flh_consider = args.next().unwrap().parse().unwrap(),
            "--flh-score-weight" => flh_score_weight = args.next().unwrap().parse().unwrap(),
            "--flh-compat-weight" => flh_compat_weight = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let side = puzzle.width as usize;
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::from_u8(0).unwrap()).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    // Load the input J1 board.
    let json_str = std::fs::read_to_string(&input_board).expect("read input board");
    let v: Value = serde_json::from_str(&json_str).expect("parse json");
    let placement = v.get("placement").expect("placement").as_array().expect("array");

    let mut frozen_board: BTreeMap<(usize, usize), (u16, u8)> = BTreeMap::new();
    for item in placement {
        let pos = item.get("pos").unwrap().as_u64().unwrap() as usize;
        let pid = item.get("piece_id").unwrap().as_u64().unwrap() as u16;
        let rot = item.get("rotation").unwrap().as_u64().unwrap() as u8;
        let r = pos / side;
        let c = pos % side;
        frozen_board.insert((r, c), (pid, rot));
    }
    println!("loaded board: {} cells", frozen_board.len());

    // Frozen pieces (rows 0..=freeze_through_row).
    let mut frozen_used = PieceSet::new();
    for ((r, _c), (pid, _rot)) in frozen_board.iter() {
        if *r <= freeze_through_row {
            frozen_used.set(*pid);
        }
    }

    // Interface row: bottom edges of row `freeze_through_row` are the top
    // colors for row `freeze_through_row + 1`. We use that as fixed_top for
    // the first new band.
    let interface_row = freeze_through_row;
    let new_top_row_initial = freeze_through_row + 1;

    println!("freeze rows 0..={} ({} pieces), rebuild rows {}..={}",
        freeze_through_row,
        frozen_used.low.count_ones() + frozen_used.high.count_ones(),
        new_top_row_initial, side - 1);
    println!("beam={} time/band={}s", beam, time_per_band_secs);

    // The first band of new search has top_row = freeze_through_row (the
    // frozen interface row), bot_row = freeze_through_row + 1. We need to
    // pass fixed_top from the interface row.
    let mut interface_fixed_top: BTreeMap<usize, PieceRot> = BTreeMap::new();
    for c in 0..side {
        let (pid, rot) = frozen_board[&(interface_row, c)];
        let edges = rotate_edges(pieces[pid as usize], rot);
        interface_fixed_top.insert(c, PieceRot { pid, rot, edges });
    }

    let mut new_board: BTreeMap<(usize, usize), (u16, u8)> = BTreeMap::new();
    for ((r, c), v) in frozen_board.iter() {
        if *r <= freeze_through_row {
            new_board.insert((*r, *c), *v);
        }
    }

    let mut used_running = frozen_used;
    let mut fixed_top: Option<BTreeMap<usize, PieceRot>> = Some(interface_fixed_top);
    let mut total_band_score: u32 = 0;
    let t0 = Instant::now();

    for band_idx in 0..(side - 1 - freeze_through_row) {
        let top_row = freeze_through_row + band_idx;
        let bot_row = top_row + 1;
        println!("\n=== BAND {} (rows {}, {}) ===", band_idx, top_row, bot_row);
        let t_band = Instant::now();

        // initial_used is what's BEFORE row top_row (which is the interface row
        // for the first iteration, and is in the frozen set, so it's already
        // in used_running... but actually the chain logic re-places top row.
        // We use: initial_used = used_running minus the pieces in row top_row
        // (because they're being re-placed = "fixed" via fixed_top).
        let mut initial_used = PieceSet::new();
        for ((r, _), (pid, _)) in new_board.iter() {
            if *r != top_row {
                initial_used.set(*pid);
            }
        }

        let result = solve_band(
            &pieces, side, top_row, bot_row,
            fixed_top.as_ref(),
            initial_used,
            beam,
            std::time::Duration::from_secs(time_per_band_secs),
            flh_consider > 1,
            flh_consider,
            flh_score_weight,
            flh_compat_weight,
        );

        match result {
            Some((score, top_assign, bot_assign)) => {
                let max_band = 3 * side - 2;
                println!("  score: {} / {}  elapsed: {:.2}s",
                    score, max_band, t_band.elapsed().as_secs_f64());
                // Top row should equal current fixed_top
                for c in 0..side {
                    if !new_board.contains_key(&(top_row, c)) {
                        new_board.insert((top_row, c), top_assign[c]);
                        used_running.set(top_assign[c].0);
                    }
                    new_board.insert((bot_row, c), bot_assign[c]);
                    used_running.set(bot_assign[c].0);
                }
                total_band_score += score;

                let mut next_ft = BTreeMap::new();
                for c in 0..side {
                    let (pid, rot) = bot_assign[c];
                    let edges = rotate_edges(pieces[pid as usize], rot);
                    next_ft.insert(c, PieceRot { pid, rot, edges });
                }
                fixed_top = Some(next_ft);
            }
            None => {
                println!("  BAND FAILED. Stopping at band {}.", band_idx);
                break;
            }
        }
    }

    // Score the resulting board (verify-style)
    let mut full_matched = 0u32;
    for r in 0..side {
        for c in 0..side {
            let (pid, rot) = match new_board.get(&(r, c)) {
                Some(v) => *v,
                None => continue,
            };
            let edges = rotate_edges(pieces[pid as usize], rot);
            // Match to right neighbor
            if c + 1 < side {
                if let Some(&(rpid, rrot)) = new_board.get(&(r, c + 1)) {
                    let re = rotate_edges(pieces[rpid as usize], rrot);
                    if edges[1] == re[3] && edges[1] != 0 {
                        full_matched += 1;
                    }
                }
            }
            // Match to bottom neighbor
            if r + 1 < side {
                if let Some(&(bpid, brot)) = new_board.get(&(r + 1, c)) {
                    let be = rotate_edges(pieces[bpid as usize], brot);
                    if edges[2] == be[0] && edges[2] != 0 {
                        full_matched += 1;
                    }
                }
            }
        }
    }

    println!("\n=== STRATUM-FIX RESULT ===");
    println!("placed: {} / {}", new_board.len(), side * side);
    println!("matched edges: {} / 480", full_matched);
    println!("total band scores (lower stratum, including interface): {}", total_band_score);
    println!("elapsed: {:.2}s", t0.elapsed().as_secs_f64());

    let placement_out: Vec<_> = new_board.iter().map(|((r, c), (pid, rot))| {
        json!({"pos": r * side + c, "piece_id": *pid as u32, "rotation": *rot as u32})
    }).collect();
    let out = json!({
        "source": "vol122_j1_stratum_fix",
        "input_board": input_board.display().to_string(),
        "freeze_through_row": freeze_through_row,
        "n_placed": new_board.len(),
        "matched_edges": full_matched,
        "placement": placement_out,
    });
    std::fs::create_dir_all(out_path.parent().unwrap()).ok();
    std::fs::write(&out_path, serde_json::to_string_pretty(&out).unwrap()).unwrap();
    println!("wrote: {}", out_path.display());
}
