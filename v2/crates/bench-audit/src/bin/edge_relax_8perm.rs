// Vol-21 — 8-piece exhaustive permutation over the relaxed-gap set.
//
// edge_relax discovered that under relaxed piece-uniqueness, the 457 board
// reaches 461 by placing pieces {82, 146, 205, 233} into the cells currently
// held by {207, 204, 245, 189} (their "duplicate" spots), and dropping
// {189, 204, 207, 245} entirely.
//
// THE BIG QUESTION: is there a permutation of these 8 pieces over their
// 8 current positions (and possibly more) that achieves the same +4 gain
// while keeping piece-uniqueness?
//
// 8! = 40,320 — trivially enumerable.

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_bench_audit::score_board_dense as score_board;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Board, Puzzle, Rotation, BORDER};

fn load_board(path: &std::path::Path, puzzle: &Puzzle) -> Board {
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

fn cell_edges(puzzle: &Puzzle, board: &Board, pos: u32) -> Option<[u8; 4]> {
    board.get(pos).map(|(pid, rot)| {
        let piece = puzzle.piece(pid).expect("piece");
        piece.edges.rotated(rot).as_array()
    })
}

fn cell_local_score(puzzle: &Puzzle, board: &Board, pos: u32, edges: [u8; 4]) -> u32 {
    let w = puzzle.width;
    let h = puzzle.height;
    let x = pos % w;
    let y = pos / w;
    let mut s = 0u32;
    if y > 0 {
        if let Some(ne) = cell_edges(puzzle, board, pos - w) {
            if edges[0] != BORDER && ne[2] != BORDER && edges[0] == ne[2] { s += 1; }
        }
    }
    if x + 1 < w {
        if let Some(ne) = cell_edges(puzzle, board, pos + 1) {
            if edges[1] != BORDER && ne[3] != BORDER && edges[1] == ne[3] { s += 1; }
        }
    }
    if y + 1 < h {
        if let Some(ne) = cell_edges(puzzle, board, pos + w) {
            if edges[2] != BORDER && ne[0] != BORDER && edges[2] == ne[0] { s += 1; }
        }
    }
    if x > 0 {
        if let Some(ne) = cell_edges(puzzle, board, pos - 1) {
            if edges[3] != BORDER && ne[1] != BORDER && edges[3] == ne[1] { s += 1; }
        }
    }
    s
}

fn border_class_of_pos(puzzle: &Puzzle, pos: u32) -> u8 {
    let x = pos % puzzle.width;
    let y = pos / puzzle.width;
    let mut n = 0u8;
    if x == 0 { n += 1; }
    if x == puzzle.width - 1 { n += 1; }
    if y == 0 { n += 1; }
    if y == puzzle.height - 1 { n += 1; }
    n
}

fn border_class_of_piece(puzzle: &Puzzle, pid: u16) -> u8 {
    let e = puzzle.piece(pid).unwrap().edges.as_array();
    e.iter().filter(|&&c| c == BORDER).count() as u8
}

fn best_rot_score(puzzle: &Puzzle, board: &Board, pos: u32, pid: u16) -> Option<(u32, Rotation, [u8; 4])> {
    let piece = puzzle.piece(pid)?;
    let w = puzzle.width;
    let h = puzzle.height;
    let x = pos % w;
    let y = pos / w;
    let mut best: Option<(u32, Rotation, [u8;4])> = None;
    for rot in Rotation::ALL {
        let e = piece.edges.rotated(rot).as_array();
        if (e[0] == BORDER) != (y == 0) { continue; }
        if (e[1] == BORDER) != (x + 1 == w) { continue; }
        if (e[2] == BORDER) != (y + 1 == h) { continue; }
        if (e[3] == BORDER) != (x == 0) { continue; }
        let s = cell_local_score(puzzle, board, pos, e);
        if best.map(|(b, _, _)| s > b).unwrap_or(true) {
            best = Some((s, rot, e));
        }
    }
    best
}

fn main() {
    let mut board_path = PathBuf::new();
    let mut extra_cells: Vec<u32> = Vec::new();
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--board" => board_path = PathBuf::from(args.next().unwrap()),
            "--extra-cell" => extra_cells.push(args.next().unwrap().parse().unwrap()),
            other => panic!("unknown arg {other}"),
        }
    }
    if board_path.as_os_str().is_empty() {
        eprintln!("usage: edge_relax_8perm --board <path> [--extra-cell POS]*");
        std::process::exit(1);
    }
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let board = load_board(&board_path, &puzzle);
    let (s_baseline, total) = score_board(&puzzle, &board);
    eprintln!("baseline: {}/{}", s_baseline, total);

    // The 8 cells with the relaxed-gap pieces.
    let core_cells: Vec<u32> = vec![
        2 * 16 + 1,   // (2,1) — 189
        2 * 16 + 2,   // (2,2) — 207
        2 * 16 + 3,   // (2,3) — 82
        3 * 16 + 7,   // (3,7) — 205
        3 * 16 + 8,   // (3,8) — 204
        3 * 16 + 13,  // (3,13) — 245
        7 * 16 + 3,   // (7,3) — 146
        10 * 16 + 10, // (10,10) — 233
    ];

    let mut cells: Vec<u32> = core_cells.clone();
    cells.extend(&extra_cells);
    cells.sort();
    cells.dedup();
    let n = cells.len();
    eprintln!("permuting over {} cells: {:?}", n,
        cells.iter().map(|p| (p/puzzle.width, p%puzzle.width)).collect::<Vec<_>>());

    // Get pieces at those cells, group by border class.
    let pids: Vec<u16> = cells.iter().map(|&pos| board.get(pos).unwrap().0).collect();
    eprintln!("pieces: {:?}", pids);

    let cls_cells: Vec<u8> = cells.iter().map(|&pos| border_class_of_pos(&puzzle, pos)).collect();
    let cls_pids: Vec<u8> = pids.iter().map(|&p| border_class_of_piece(&puzzle, p)).collect();
    for i in 0..n {
        eprintln!("  pos {:?} cls={} pid={} pid_cls={}", (cells[i]/puzzle.width, cells[i]%puzzle.width), cls_cells[i], pids[i], cls_pids[i]);
    }

    // All n! permutations σ where σ(i) is the destination index of piece i. Filter by class match.
    fn permute<F: FnMut(&[usize])>(arr: &mut [usize], k: usize, f: &mut F) {
        if k == 1 {
            f(arr);
            return;
        }
        for i in 0..k {
            permute(arr, k - 1, f);
            if k % 2 == 0 {
                arr.swap(i, k - 1);
            } else {
                arr.swap(0, k - 1);
            }
        }
    }

    let mut best_delta = 0i32;
    let mut best_perm: Vec<usize> = (0..n).collect();
    let mut hits: Vec<(Vec<usize>, i32)> = Vec::new();
    let mut tried: u64 = 0;
    let t0 = std::time::Instant::now();

    let mut arr: Vec<usize> = (0..n).collect();
    permute(&mut arr, n, &mut |perm: &[usize]| {
        tried += 1;
        // perm[i] = destination index for pids[i]
        // class check
        for i in 0..n {
            if cls_pids[i] != cls_cells[perm[i]] {
                return;
            }
        }
        // Place each piece at its destination with best rotation given current neighbors
        let mut tent = board.clone();
        for i in 0..n {
            let pid = pids[i];
            let dst = cells[perm[i]];
            if let Some((_, rot, _)) = best_rot_score(&puzzle, &board, dst, pid) {
                tent.place(dst, pid, rot);
            } else {
                return; // can't even place by border class
            }
        }
        // pass 2: refine
        let t2 = tent.clone();
        for i in 0..n {
            let pid = pids[i];
            let dst = cells[perm[i]];
            if let Some((_, rot, _)) = best_rot_score(&puzzle, &t2, dst, pid) {
                tent.place(dst, pid, rot);
            }
        }
        let (s_new, _) = score_board(&puzzle, &tent);
        let delta = s_new as i32 - s_baseline as i32;
        if delta > best_delta {
            best_delta = delta;
            best_perm = perm.to_vec();
        }
        if delta > 0 {
            hits.push((perm.to_vec(), delta));
        }
    });
    let dt = t0.elapsed().as_secs_f64();
    eprintln!("\n{} perms tried in {:.2}s; {} hits with Δ>0; best Δ = {:+}", tried, dt, hits.len(), best_delta);

    if best_delta > 0 {
        eprintln!("\nBest permutation:");
        for i in 0..n {
            let src = cells[i];
            let dst = cells[best_perm[i]];
            eprintln!("  pid {} from ({},{}) → ({},{})",
                pids[i],
                src/puzzle.width, src%puzzle.width,
                dst/puzzle.width, dst%puzzle.width,
            );
        }
        // Save best board
        let mut tent = board.clone();
        for i in 0..n {
            let pid = pids[i];
            let dst = cells[best_perm[i]];
            if let Some((_, rot, _)) = best_rot_score(&puzzle, &board, dst, pid) {
                tent.place(dst, pid, rot);
            }
        }
        let t2 = tent.clone();
        for i in 0..n {
            let pid = pids[i];
            let dst = cells[best_perm[i]];
            if let Some((_, rot, _)) = best_rot_score(&puzzle, &t2, dst, pid) {
                tent.place(dst, pid, rot);
            }
        }
        let (s_final, _) = score_board(&puzzle, &tent);
        eprintln!("\nFinal verified score: {}/480", s_final);
        let out_path = format!("output/v21_edge_relax_8perm_{}.json", s_final);
        let json = serde_json::json!({
            "matched_best": s_final,
            "placement": (0..puzzle.cell_count()).map(|p| {
                tent.get(p).map(|(pid, rot)| serde_json::json!({
                    "pos": p, "piece_id": u32::from(pid), "rotation": rot.as_u8(),
                }))
            }).collect::<Vec<_>>(),
        });
        std::fs::write(&out_path, serde_json::to_string_pretty(&json).unwrap()).expect("write");
        eprintln!("Saved to {}", out_path);
    }
}
