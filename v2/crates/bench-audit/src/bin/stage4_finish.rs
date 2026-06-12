// Vol-217: stage-4 finisher — branch-and-bound min-break completion of
// rows 12-15 (64 cells) from a perfect rows-0-11 full-board state.
// The reality-side instrument for the "<10 errors in the last 4 rows"
// check: measures what a given stage-4 entry ACTUALLY finishes at.
//
//   stage4_finish --board S3_STATE.json --max-breaks 12 \
//     --budget-ms 60000 [--node-cap N] [--save-best OUT.json]
//
// Anytime B&B: budget tightens to (best-1) after each completion.
// Candidate costs: each cell pays its N edge (vs row above) and its
// W edge (vs cell left); board-edge sides are structural (candidate
// orientation), so all 124 stage-4 edges are counted exactly once.
// Clue cells (13,2)/(13,13) forced. Loud node-cap / deadline report.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;

const N: usize = 16;

fn rotate_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    let mut out = [0u8; 4];
    for i in 0..4 {
        out[i] = e[(i + 4 - r as usize) % 4];
    }
    out
}

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut board_path: Option<PathBuf> = None;
    let mut max_breaks: i32 = 12;
    let mut budget_ms: u64 = 60_000;
    let mut node_cap: u64 = u64::MAX;
    let mut save_best: Option<PathBuf> = None;
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--puzzle" => { puzzle_path = PathBuf::from(&raw[i + 1]); i += 2; }
            "--board" => { board_path = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            "--max-breaks" => { max_breaks = raw[i + 1].parse().unwrap(); i += 2; }
            "--budget-ms" => { budget_ms = raw[i + 1].parse().unwrap(); i += 2; }
            "--node-cap" => { node_cap = raw[i + 1].parse().unwrap(); i += 2; }
            "--save-best" => { save_best = Some(PathBuf::from(&raw[i + 1])); i += 2; }
            other => panic!("unknown arg {other}"),
        }
    }
    let board_path = board_path.expect("--board required");

    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("puzzle");
    let mut rot: Vec<[[u8; 4]; 4]> = Vec::with_capacity(256);
    let mut kind: Vec<u8> = Vec::with_capacity(256); // 0 corner 1 edge 2 interior
    for p in puzzle.pieces() {
        let e = [p.edges.top(), p.edges.right(), p.edges.bottom(), p.edges.left()];
        let mut rr = [[0u8; 4]; 4];
        for r in 0..4 {
            rr[r] = rotate_edges(e, r as u8);
        }
        rot.push(rr);
        kind.push(match e.iter().filter(|&&c| c == 0).count() {
            2 => 0,
            1 => 1,
            _ => 2,
        });
    }

    // load rows 0-11
    let v: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&board_path).expect("read board"))
            .expect("parse");
    let mut placed: HashMap<usize, (u16, u8)> = HashMap::new();
    for (idx, e) in v["placement"].as_array().expect("placement").iter().enumerate() {
        if e.is_null() {
            continue;
        }
        let pos = e.get("pos").and_then(|p| p.as_u64()).unwrap_or(idx as u64) as usize;
        if pos < 12 * N {
            placed.insert(pos, (
                e["piece_id"].as_u64().unwrap() as u16,
                e["rotation"].as_u64().unwrap() as u8,
            ));
        }
    }
    assert_eq!(placed.len(), 12 * N, "rows 0-11 incomplete");
    let mut used = [false; 256];
    for &(p, _) in placed.values() {
        assert!(!used[p as usize], "dup piece");
        used[p as usize] = true;
    }
    // forced clue cells in stage 4
    let mut forced: HashMap<usize, (u16, u8)> = HashMap::new();
    for h in hints.hints.iter() {
        let pos = h.position as usize;
        if pos >= 12 * N {
            forced.insert(pos, (h.piece_id, h.rotation.as_u8()));
        }
    }

    // candidate lists per cell: (piece, rot, n, e, s, w) packed
    #[derive(Clone, Copy)]
    struct Cand {
        pid: u16,
        rotc: u8,
        n: u8,
        e: u8,
        s: u8,
    }
    let mut cands: Vec<Vec<Cand>> = vec![Vec::new(); 64];
    let pool: Vec<u16> = (0..256u16).filter(|&p| !used[p as usize]).collect();
    assert_eq!(pool.len(), 64);
    for cell in 0..64 {
        let pos = 12 * N + cell;
        let (r, c) = (pos / N, pos % N);
        let list = &mut cands[cell];
        if let Some(&(pid, rotc)) = forced.get(&pos) {
            let o = rot[pid as usize][rotc as usize];
            list.push(Cand { pid, rotc, n: o[0], e: o[1], s: o[2] });
            continue;
        }
        for &p in &pool {
            for rc in 0..4u8 {
                let o = rot[p as usize][rc as usize];
                let ok = if r == 15 && c == 0 {
                    o[2] == 0 && o[3] == 0
                } else if r == 15 && c == 15 {
                    o[2] == 0 && o[1] == 0
                } else if r == 15 {
                    kind[p as usize] == 1 && o[2] == 0
                } else if c == 0 {
                    kind[p as usize] == 1 && o[3] == 0
                } else if c == 15 {
                    kind[p as usize] == 1 && o[1] == 0
                } else {
                    kind[p as usize] == 2
                };
                if ok {
                    list.push(Cand { pid: p, rotc: rc, n: o[0], e: o[1], s: o[2] });
                }
            }
        }
    }

    // north targets for row 12 from placed row 11
    let mut tn12 = [0u8; N];
    for c in 0..N {
        let &(p, rc) = placed.get(&(11 * N + c)).unwrap();
        tn12[c] = rot[p as usize][rc as usize][2];
    }

    // DFS state
    let mut chosen: Vec<usize> = vec![usize::MAX; 64]; // index into cands[cell]
    let mut spent: Vec<i32> = vec![0; 65];
    let mut south: Vec<[u8; N]> = vec![[0; N]; 5]; // souths per stage-4 row built
    let mut east: [u8; 64] = [0; 64];
    let mut used4 = [false; 256];
    let mut best = i32::MAX;
    let mut best_board: Vec<(u16, u8)> = Vec::new();
    let mut nodes: u64 = 0;
    let t0 = Instant::now();
    let deadline = t0 + std::time::Duration::from_millis(budget_ms);
    let mut capped = false;

    // iterative DFS over cells 0..64 (stage-4 local index)
    let mut cursor: Vec<usize> = vec![0; 65];
    let mut depth: usize = 0;
    loop {
        if (nodes & 0xFFFF) == 0 && (Instant::now() >= deadline || nodes >= node_cap) {
            capped = true;
            break;
        }
        if depth == 64 {
            let total = spent[64];
            if total < best {
                best = total;
                best_board = chosen
                    .iter()
                    .enumerate()
                    .map(|(cell, &ci)| {
                        let cd = cands[cell][ci];
                        (cd.pid, cd.rotc)
                    })
                    .collect();
                eprintln!(
                    "[best] breaks={best} total={} nodes={nodes} t={}ms",
                    480 - best,
                    t0.elapsed().as_millis()
                );
                if best == 0 {
                    break;
                }
            }
            // force backtrack
            depth -= 1;
            let cd = cands[depth][chosen[depth]];
            used4[cd.pid as usize] = false;
            cursor[depth] = chosen[depth] + 1;
            continue;
        }
        let (r, c) = ((12 * N + depth) / N, depth % N);
        let rrow = r - 12;
        let budget = best.min(max_breaks + 1) - 1; // strictly better than best
        let mut advanced = false;
        let mut ci = cursor[depth];
        while ci < cands[depth].len() {
            let cd = cands[depth][ci];
            if used4[cd.pid as usize] {
                ci += 1;
                continue;
            }
            let tn = if rrow == 0 { tn12[c] } else { south[rrow - 1][c] };
            let mut cost = i32::from(cd.n != tn);
            if c > 0 {
                cost += i32::from(east[depth - 1] != {
                    // west side of candidate
                    let o = rot[cd.pid as usize][cd.rotc as usize];
                    o[3]
                });
            }
            let ns = spent[depth] + cost;
            if ns <= budget {
                nodes += 1;
                chosen[depth] = ci;
                used4[cd.pid as usize] = true;
                spent[depth + 1] = ns;
                south[rrow][c] = cd.s;
                east[depth] = cd.e;
                cursor[depth] = ci; // resume point on backtrack
                depth += 1;
                cursor[depth] = 0;
                advanced = true;
                break;
            }
            ci += 1;
        }
        if !advanced {
            if depth == 0 {
                break;
            }
            depth -= 1;
            let cd = cands[depth][chosen[depth]];
            used4[cd.pid as usize] = false;
            cursor[depth] = chosen[depth] + 1;
        }
    }

    let status = if capped { "CAPPED" } else { "exhausted-or-solved" };
    println!(
        "{{\"board\":\"{}\",\"best_breaks\":{},\"best_total\":{},\"nodes\":{},\"elapsed_ms\":{},\"status\":\"{}\"}}",
        board_path.file_stem().unwrap().to_string_lossy(),
        if best == i32::MAX { -1 } else { best },
        if best == i32::MAX { -1 } else { 480 - best },
        nodes,
        t0.elapsed().as_millis(),
        status
    );
    if capped {
        eprintln!("WARN stage4_finish: search CAPPED — best may be non-optimal");
    }
    if let (Some(out), false) = (save_best, best_board.is_empty()) {
        let mut entries: Vec<String> = Vec::new();
        let mut full: Vec<Option<(u16, u8)>> = vec![None; 256];
        for (pos, &pr) in &placed {
            full[*pos] = Some(pr);
        }
        for (cell, &(pid, rc)) in best_board.iter().enumerate() {
            full[12 * N + cell] = Some((pid, rc));
        }
        for (pos, slot) in full.iter().enumerate() {
            if let Some((pid, rc)) = slot {
                entries.push(format!(
                    "{{\"pos\":{pos},\"piece_id\":{pid},\"rotation\":{rc}}}"
                ));
            }
        }
        std::fs::write(out, format!("{{\"placement\": [{}]}}", entries.join(",")))
            .expect("write best");
    }
}
