// Vol-122 J1 — Double-Row Column-DP with Beam Search (Rust port).
//
// Solves a 2-row band column-by-column with beam-pruning. Each band
// achieves perfect score (3*side - 2) on canonical 16×16 in ~70s in
// Python; Rust target: 10-100× faster.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;

#[derive(Clone, Copy, Debug)]
struct PieceRot {
    pid: u16,
    rot: u8,
    /// edges: [T, R, B, L]
    edges: [u8; 4],
}

/// Pair of u128 bitsets to track up to 256 pieces.
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

fn solve_band(
    pieces: &[[u8; 4]],
    side: usize,
    top_row: usize,
    bot_row: usize,
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
        for opt in &all_options {
            if valid_top_at(opt, col) {
                top_by_l[col][opt.edges[3] as usize].push(*opt);
            }
            if valid_bot_at(opt, col) {
                bot_by_l[col][opt.edges[3] as usize].push(*opt);
            }
        }
    }

    let top_col0: Vec<&PieceRot> = all_options.iter().filter(|o| valid_top_at(o, 0)).collect();
    let bot_col0: Vec<&PieceRot> = all_options.iter().filter(|o| valid_bot_at(o, 0)).collect();

    let mut states_per_col: Vec<Vec<State>> = Vec::with_capacity(side);
    let mut col0_states: Vec<State> = Vec::new();
    for ot in &top_col0 {
        for ob in &bot_col0 {
            if ot.pid == ob.pid { continue; }
            let mut score = 0u32;
            if ot.edges[2] == ob.edges[0] && ot.edges[2] != 0 {
                score += 1;
            }
            let mut used = PieceSet::new();
            used.set(ot.pid);
            used.set(ob.pid);
            col0_states.push(State {
                top: **ot, bot: **ob, used, score, parent_idx: -1,
            });
        }
    }
    col0_states.sort_unstable_by_key(|s| std::cmp::Reverse(s.score));
    col0_states.truncate(beam);
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
    let mut time_limit_secs: u64 = 300;
    let mut top_row: usize = 0;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--beam" => beam = args.next().unwrap().parse().unwrap(),
            "--time-secs" => time_limit_secs = args.next().unwrap().parse().unwrap(),
            "--top-row" => top_row = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let side = puzzle.width as usize;
    println!("puzzle: {} side={} pieces={} beam={} time={}s top_row={}",
        puzzle_path.display(), side, puzzle.pieces().len(), beam, time_limit_secs, top_row);

    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::from_u8(0).unwrap()).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();

    let bot_row = top_row + 1;
    let t0 = Instant::now();
    let result = solve_band(&pieces, side, top_row, bot_row, beam,
        std::time::Duration::from_secs(time_limit_secs));
    let elapsed = t0.elapsed();

    let max_possible = 3 * side - 2;
    if let Some((score, _, _)) = result {
        println!("\nband ({},{}) score: {} / {}  elapsed: {:.2}s",
            top_row, bot_row, score, max_possible, elapsed.as_secs_f64());
    } else {
        println!("\nband FAILED in {:.2}s", elapsed.as_secs_f64());
    }
}
