// Vol-20 — exhaustive cycle scan over the mismatch cells of a high-score
// board. For each cycle of length K (3..=N), evaluate the score delta when
// the pieces are rotated cyclically (piece(a)→b, piece(b)→c, …, piece(z)→a),
// each placed at its best rotation given current neighbours.
//
// Python N4b confirmed all 3-cycles and 4-cycles on the 38 mismatch cells
// have Δ < 0. This Rust scanner extends to K=5,6,7,8 efficiently and
// records the full Δ-distribution so we can pinpoint the cycle length at
// which the cooperative barrier is first crossable.
//
// CLI:
//   cycle_scan --board <path> --max-k 6
//
// Output: per-K Δ-histogram + (if any) cycles with Δ ≥ 0.

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_bench_audit::{score_board_dense as score_board};
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, BORDER, Rotation};

fn load_board(path: &std::path::Path, puzzle: &eternity2_core::Puzzle) -> Board {
    let raw = std::fs::read_to_string(path).expect("read");
    let v: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let mut b = Board::empty(puzzle);
    if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
        for p in arr {
            if p.is_null() { continue; }
            let pos = p["pos"].as_u64().unwrap() as u32;
            let pid = p["piece_id"].as_u64().unwrap() as u16;
            let rot = Rotation::from_u8(p["rotation"].as_u64().unwrap() as u8).unwrap();
            b.place(pos, pid, rot);
        }
    }
    b
}

fn cell_edges(puzzle: &eternity2_core::Puzzle, board: &Board, pos: u32) -> Option<[u8; 4]> {
    board.get(pos).map(|(pid, rot)| {
        let piece = puzzle.piece(pid).expect("piece");
        piece.edges.rotated(rot).as_array()
    })
}

fn count_mismatches(puzzle: &eternity2_core::Puzzle, board: &Board) -> Vec<u32> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut mm: Vec<u32> = Vec::new();
    for pos in 0..(w * h) {
        let Some(e) = cell_edges(puzzle, board, pos) else { continue };
        let x = pos % w;
        let y = pos / w;
        let mut bad = 0;
        if y > 0 {
            if let Some(ne) = cell_edges(puzzle, board, pos - w) {
                if e[0] != BORDER && ne[2] != BORDER && e[0] != ne[2] { bad += 1; }
            }
        }
        if x + 1 < w {
            if let Some(ne) = cell_edges(puzzle, board, pos + 1) {
                if e[1] != BORDER && ne[3] != BORDER && e[1] != ne[3] { bad += 1; }
            }
        }
        if y + 1 < h {
            if let Some(ne) = cell_edges(puzzle, board, pos + w) {
                if e[2] != BORDER && ne[0] != BORDER && e[2] != ne[0] { bad += 1; }
            }
        }
        if x > 0 {
            if let Some(ne) = cell_edges(puzzle, board, pos - 1) {
                if e[3] != BORDER && ne[1] != BORDER && e[3] != ne[1] { bad += 1; }
            }
        }
        if bad > 0 {
            mm.push(pos);
        }
    }
    mm
}

fn border_class_of_piece(puzzle: &eternity2_core::Puzzle, pid: u16) -> u8 {
    let piece = puzzle.piece(pid).expect("piece");
    let e = piece.edges.as_array();
    e.iter().filter(|&&c| c == BORDER).count() as u8
}

fn border_class_of_pos(w: u32, h: u32, pos: u32) -> u8 {
    let x = pos % w;
    let y = pos / w;
    let mut n = 0;
    if x == 0 { n += 1; }
    if x == w - 1 { n += 1; }
    if y == 0 { n += 1; }
    if y == h - 1 { n += 1; }
    n
}

fn best_rot_score_at(puzzle: &eternity2_core::Puzzle, board: &Board, pos: u32, pid: u16) -> Option<(u32, Rotation)> {
    let w = puzzle.width;
    let h = puzzle.height;
    let piece = puzzle.piece(pid)?;
    let x = pos % w;
    let y = pos / w;
    let mut best: Option<(u32, Rotation)> = None;
    for rot in Rotation::ALL {
        let e = piece.edges.rotated(rot).as_array();
        // border alignment
        let n_at_top = y == 0;
        let n_at_right = x == w - 1;
        let n_at_bot = y == h - 1;
        let n_at_left = x == 0;
        if (e[0] == BORDER) != n_at_top { continue; }
        if (e[1] == BORDER) != n_at_right { continue; }
        if (e[2] == BORDER) != n_at_bot { continue; }
        if (e[3] == BORDER) != n_at_left { continue; }
        let mut s = 0u32;
        if y > 0 {
            if let Some(ne) = cell_edges(puzzle, board, pos - w) {
                if e[0] != BORDER && ne[2] != BORDER && e[0] == ne[2] { s += 1; }
            }
        }
        if x + 1 < w {
            if let Some(ne) = cell_edges(puzzle, board, pos + 1) {
                if e[1] != BORDER && ne[3] != BORDER && e[1] == ne[3] { s += 1; }
            }
        }
        if y + 1 < h {
            if let Some(ne) = cell_edges(puzzle, board, pos + w) {
                if e[2] != BORDER && ne[0] != BORDER && e[2] == ne[0] { s += 1; }
            }
        }
        if x > 0 {
            if let Some(ne) = cell_edges(puzzle, board, pos - 1) {
                if e[3] != BORDER && ne[1] != BORDER && e[3] == ne[1] { s += 1; }
            }
        }
        if best.map(|(b, _)| s > b).unwrap_or(true) {
            best = Some((s, rot));
        }
    }
    best
}

/// Evaluate a cyclic permutation: place piece(cycle[i]) at cycle[(i+1) mod K]
/// with best rotation (against original board, two-pass).
/// Returns Δ = score_after - score_before across all edges incident to cycle cells.
fn evaluate_cycle(puzzle: &eternity2_core::Puzzle, board: &Board, cycle: &[u32]) -> Option<i32> {
    let k = cycle.len();
    let mut new_pids: Vec<u16> = Vec::with_capacity(k);
    for i in 0..k {
        let src = cycle[i];
        new_pids.push(board.get(src)?.0);
    }

    // Two-pass placement: pass 1 best rot vs original; pass 2 best rot vs tentative.
    let mut tentative = board.clone();
    for i in 0..k {
        let dst = cycle[(i + 1) % k];
        let pid = new_pids[i];
        let (_, rot) = best_rot_score_at(puzzle, board, dst, pid)?;
        tentative.place(dst, pid, rot);
    }
    for i in 0..k {
        let dst = cycle[(i + 1) % k];
        let pid = new_pids[i];
        let (_, rot) = best_rot_score_at(puzzle, &tentative, dst, pid)?;
        tentative.place(dst, pid, rot);
    }

    // Compute affected score: sum over edges incident to any cycle cell.
    // Use a HashSet keyed by horizontal/vertical edge (smaller endpoint).
    use std::collections::HashSet;
    let mut seen: HashSet<(u8, u32)> = HashSet::new();
    let w = puzzle.width;
    let cycle_set: HashSet<u32> = cycle.iter().copied().collect();

    let mut score_edges = |brd: &Board| -> i32 {
        let mut s: i32 = 0;
        let mut seen_local: HashSet<(u8, u32)> = HashSet::new();
        for &pos in cycle {
            let Some(e) = cell_edges(puzzle, brd, pos) else { continue };
            let x = pos % w;
            let y = pos / w;
            // East edge: between pos and pos+1; key ('h', pos)
            if x + 1 < w {
                let key = (0u8, pos);
                if !seen_local.contains(&key) {
                    seen_local.insert(key);
                    if let Some(ne) = cell_edges(puzzle, brd, pos + 1) {
                        if e[1] != BORDER && ne[3] != BORDER && e[1] == ne[3] { s += 1; }
                    }
                }
            }
            // South edge: between pos and pos+w; key ('v', pos)
            if y + 1 < puzzle.height {
                let key = (1u8, pos);
                if !seen_local.contains(&key) {
                    seen_local.insert(key);
                    if let Some(ne) = cell_edges(puzzle, brd, pos + w) {
                        if e[2] != BORDER && ne[0] != BORDER && e[2] == ne[0] { s += 1; }
                    }
                }
            }
            // West edge: between pos-1 and pos; key ('h', pos-1) — only if pos-1 not in cycle
            if x > 0 && !cycle_set.contains(&(pos - 1)) {
                let key = (0u8, pos - 1);
                if !seen_local.contains(&key) {
                    seen_local.insert(key);
                    if let Some(ne) = cell_edges(puzzle, brd, pos - 1) {
                        if e[3] != BORDER && ne[1] != BORDER && e[3] == ne[1] { s += 1; }
                    }
                }
            }
            if y > 0 && !cycle_set.contains(&(pos - w)) {
                let key = (1u8, pos - w);
                if !seen_local.contains(&key) {
                    seen_local.insert(key);
                    if let Some(ne) = cell_edges(puzzle, brd, pos - w) {
                        if e[0] != BORDER && ne[2] != BORDER && e[0] == ne[2] { s += 1; }
                    }
                }
            }
        }
        let _ = seen;
        s
    };

    let s_old = score_edges(board);
    let s_new = score_edges(&tentative);
    Some(s_new - s_old)
}

fn main() {
    let mut board_path = PathBuf::new();
    let mut max_k: usize = 5;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--max-k" => max_k = args.next().unwrap().parse().unwrap(),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("usage: cycle_scan --board <path> [--max-k 5]");
        std::process::exit(1);
    }

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let board = load_board(&board_path, &puzzle);
    let (score, _) = score_board(&puzzle, &board);
    eprintln!("loaded board: {}/480", score);

    let mismatches = count_mismatches(&puzzle, &board);
    eprintln!("mismatch cells: {}", mismatches.len());

    // Group by piece-border-class. Only cycles of cells of the same class
    // can be permuted (border-class assignment must hold).
    let mut by_class: std::collections::BTreeMap<u8, Vec<u32>> = Default::default();
    for &pos in &mismatches {
        let cls_pos = border_class_of_pos(puzzle.width, puzzle.height, pos);
        let cls_piece = board.get(pos).map(|(pid, _)| border_class_of_piece(&puzzle, pid)).unwrap_or(0);
        assert_eq!(cls_pos, cls_piece, "board at pos {} has piece-class != position-class", pos);
        by_class.entry(cls_pos).or_default().push(pos);
    }
    for (k, v) in &by_class {
        eprintln!("  border-class {}: {} cells", k, v.len());
    }

    // For each K=3..=max_k, enumerate K-cycles within each border class.
    use std::collections::HashMap;
    for k in 3..=max_k {
        let mut hist: HashMap<i32, u64> = HashMap::new();
        let mut improvers: Vec<(Vec<u32>, i32)> = Vec::new();
        let mut total: u64 = 0;
        let t0 = std::time::Instant::now();
        for cells in by_class.values() {
            if cells.len() < k { continue; }
            // For each combination of K cells, generate all (k-1)! cyclic permutations.
            // Implementation: pick indices i0<i1<…<i_{k-1}, then enumerate permutations with first element fixed.
            let n = cells.len();
            // K-combinations
            let mut idx = (0..k).collect::<Vec<_>>();
            'comb: loop {
                let combo: Vec<u32> = idx.iter().map(|&i| cells[i]).collect();
                // Permutations with combo[0] fixed; (k-1)! perms; for k=5 → 24.
                // Generate via Heap's algorithm on combo[1..].
                let mut perm = combo.clone();
                let mut c_state = vec![0usize; k];
                // initial
                if let Some(d) = evaluate_cycle(&puzzle, &board, &perm) {
                    *hist.entry(d).or_insert(0) += 1;
                    total += 1;
                    if d >= 0 { improvers.push((perm.clone(), d)); }
                }
                let mut i_state = 1;
                while i_state < k {
                    if c_state[i_state] < i_state {
                        let j = if i_state % 2 == 0 { 1 } else { c_state[i_state] + 1 };
                        if j != 0 && j < k {
                            perm.swap(j, i_state);
                        }
                        if let Some(d) = evaluate_cycle(&puzzle, &board, &perm) {
                            *hist.entry(d).or_insert(0) += 1;
                            total += 1;
                            if d >= 0 { improvers.push((perm.clone(), d)); }
                        }
                        c_state[i_state] += 1;
                        i_state = 1;
                    } else {
                        c_state[i_state] = 0;
                        i_state += 1;
                    }
                }
                // next combination
                let mut i = k;
                loop {
                    if i == 0 { break 'comb; }
                    i -= 1;
                    if idx[i] < n - (k - i) {
                        idx[i] += 1;
                        for j in (i + 1)..k {
                            idx[j] = idx[j - 1] + 1;
                        }
                        break;
                    }
                }
            }
        }
        let elapsed = t0.elapsed().as_secs_f64();
        eprintln!("\nK={k}: {total} cycles in {elapsed:.1}s");
        let mut keys: Vec<&i32> = hist.keys().collect();
        keys.sort();
        for d in keys {
            eprintln!("  Δ={d:+3}: {}", hist[d]);
        }
        if !improvers.is_empty() {
            improvers.sort_by_key(|x| -x.1);
            eprintln!("  ★ {} improvers (Δ≥0) — top 10:", improvers.len());
            for (cycle, d) in improvers.iter().take(10) {
                eprintln!("    Δ={d:+}: cycle {:?}", cycle);
            }
        }
    }
}
