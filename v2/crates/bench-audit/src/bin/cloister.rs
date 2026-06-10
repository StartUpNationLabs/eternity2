// cloister — vol-211: the standalone 14×14 interior puzzle (veteran
// milestone #3, never solved standalone).
//
// The 196 interior pieces on a 14×14 grid, rim outward sides FREE.
// Objective: maximize II (interior-interior matched edges, max 364).
//
// Modes:
//   --mode dfs     perfect-prefix DFS: measures the standalone interior's
//                  depth wall (max all-matched prefix in row-major scan),
//                  multi-seed. If depth 196 is reached the interior is
//                  PERFECT — dump and stop.
//   --mode sa      max-II annealer: rot / best-rot-swap / window-LNS moves,
//                  Metropolis acceptance, reheat on stagnation. Multi-seed
//                  parallel (rayon).
//   --mode hybrid  DFS-seeded repair: per seed, a short DFS probe builds a
//                  deep perfect prefix (wall ~174), greedy-fills the tail,
//                  then the SA loop (with exact B&B window repair + band
//                  destroys) repairs from there.
//
// Output: timestamped dir output/vol-211/cloister_<mode>_<ts>/ with
// per-seed summary TSV + best boards as sparse-pos 16×16 JSONs (border
// empty) + bucas URL (verified encoder convention: 'a'+color, empty=aaaa).

#![forbid(unsafe_code)]

use std::io::Write as _;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Piece, Puzzle, Rotation, BORDER};
use eternity2_localsearch::alns::AlnsRng;
use rayon::prelude::*;

const N: usize = 14;
const CELLS: usize = N * N;
const II_MAX: u32 = 364;

// ---------------------------------------------------------------- interior

struct Interior {
    /// rot_edges[pid][rot] = [N,E,S,W] colors, pid = local 0..195
    rot_edges: Vec<[[u8; 4]; 4]>,
    /// local pid -> canonical PieceId
    global_id: Vec<u16>,
    /// (cell, local pid, rot) for canonical hints that land in the interior
    hints: Vec<(usize, usize, u8)>,
    /// inward-color multiset of the 56 border edge pieces (for rim term)
    edge_inward_supply: [u32; 23],
}

fn extract_interior(puzzle: &Puzzle, hints: &eternity2_core::Hints) -> Interior {
    let mut rot_edges = Vec::new();
    let mut global_id = Vec::new();
    let mut g2l = vec![usize::MAX; 256];
    let mut edge_inward_supply = [0u32; 23];
    for pid in 0..256u16 {
        let p: &Piece = puzzle.piece(pid).expect("piece");
        let e = p.edges.as_array();
        let zeros = e.iter().filter(|&&c| c == BORDER).count();
        match zeros {
            0 => {
                g2l[pid as usize] = global_id.len();
                let mut re = [[0u8; 4]; 4];
                for r in 0..4u8 {
                    re[r as usize] = p
                        .edges
                        .rotated(Rotation::from_u8(r).expect("rot"))
                        .as_array();
                }
                rot_edges.push(re);
                global_id.push(pid);
            }
            1 => {
                // edge piece: inward color = side opposite the grey side
                let grey_side = e.iter().position(|&c| c == BORDER).expect("grey");
                let inward = e[(grey_side + 2) % 4];
                edge_inward_supply[inward as usize] += 1;
            }
            _ => {} // corner pieces have no interior-facing side
        }
    }
    assert_eq!(global_id.len(), 196, "interior piece count");

    let mut ih = Vec::new();
    for h in &hints.hints {
        let (x, y) = puzzle.xy(h.position);
        let (x, y) = (x as usize, y as usize);
        if (1..=N).contains(&x) && (1..=N).contains(&y) {
            let local = g2l[h.piece_id as usize];
            assert!(local != usize::MAX, "hint piece must be interior");
            ih.push(((y - 1) * N + (x - 1), local, h.rotation.as_u8()));
        } else {
            eprintln!("WARN: hint at non-interior position {}", h.position);
        }
    }
    Interior { rot_edges, global_id, hints: ih, edge_inward_supply }
}

// ------------------------------------------------------------------ output

fn shuffle<T>(v: &mut [T], rng: &mut AlnsRng) {
    for i in (1..v.len()).rev() {
        let j = (rng.next_u64() % (i as u64 + 1)) as usize;
        v.swap(i, j);
    }
}

fn bucas_url(interior: &Interior, state: &[(u16, u8)]) -> String {
    let mut edges = String::new();
    for full in 0..256usize {
        let (y, x) = (full / 16, full % 16);
        if (1..=N).contains(&x) && (1..=N).contains(&y) {
            let cell = (y - 1) * N + (x - 1);
            let (pid, rot) = state[cell];
            let e = interior.rot_edges[pid as usize][rot as usize];
            for c in e {
                edges.push((b'a' + c) as char);
            }
        } else {
            edges.push_str("aaaa");
        }
    }
    format!(
        "https://e2.bucas.name/#puzzle=Eternity2&board_w=16&board_h=16&board_edges={edges}"
    )
}

fn save_board(
    dir: &PathBuf,
    name: &str,
    interior: &Interior,
    state: &[(u16, u8)],
    ii: u32,
    extra: &str,
) {
    let mut placement = Vec::new();
    for cell in 0..CELLS {
        let (pid, rot) = state[cell];
        let full = (cell / N + 1) * 16 + (cell % N + 1);
        placement.push(format!(
            "{{\"pos\":{},\"piece_id\":{},\"rotation\":{}}}",
            full, interior.global_id[pid as usize], rot
        ));
    }
    let url = bucas_url(interior, state);
    let json = format!(
        "{{\"interior_ii\":{},\"ii_max\":{},{}\"bucas_url\":\"{}\",\"placement\":[{}]}}",
        ii,
        II_MAX,
        extra,
        url,
        placement.join(",")
    );
    let path = dir.join(name);
    std::fs::write(&path, json).expect("write board");
    std::fs::write(path.with_extension("url.txt"), format!("{url}\n")).expect("write url");
    println!("saved {} (II={}/364)", path.display(), ii);
}

/// append a row to the global cloister history CSV (created with header on
/// first use); one row per saved board so runs are auditable across sessions
fn append_history(dir: &PathBuf, mode: &str, seed: u64, ii: u32, params: &str, board: &str, url: &str) {
    let hist = PathBuf::from("output/vol-211/cloister_history.csv");
    let new = !hist.exists();
    let mut f = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&hist)
        .expect("open history");
    if new {
        writeln!(f, "timestamp,mode,seed,interior_ii,params,run_dir,board,bucas_url").expect("hdr");
    }
    writeln!(
        f,
        "{},{},{},{},{},{},{},{}",
        chrono_like_ts(),
        mode,
        seed,
        ii,
        params,
        dir.display(),
        board,
        url
    )
    .expect("append history");
}

// -------------------------------------------------------------------- DFS

struct DfsResult {
    seed: u64,
    max_depth: usize,
    nodes: u64,
    ms_at_max: u128,
    /// best complete assignment found (fewest breaks), with its break count
    complete: Option<(Vec<(u16, u8)>, u32)>,
    completes_found: u64,
    /// grid contents of cells 0..max_depth at the moment max_depth was hit
    best_prefix: Vec<(u16, u8)>,
}

/// count mismatched II edges of a complete assignment (independent recount)
fn count_breaks(interior: &Interior, grid: &[(u16, u8)]) -> u32 {
    let mut b = 0;
    for cell in 0..CELLS {
        let (pid, rot) = grid[cell];
        let e = interior.rot_edges[pid as usize][rot as usize];
        if cell % N > 0 {
            let (lp, lr) = grid[cell - 1];
            if interior.rot_edges[lp as usize][lr as usize][1] != e[3] {
                b += 1;
            }
        }
        if cell >= N {
            let (up, ur) = grid[cell - N];
            if interior.rot_edges[up as usize][ur as usize][2] != e[0] {
                b += 1;
            }
        }
    }
    b
}

/// Exact endgame: given the k remaining (unused) pieces and the k last
/// row-major cells (with all earlier cells placed in `grid`), find the
/// assignment minimizing total mismatches. B&B over cell order with an
/// admissible per-cell up-edge lower bound. Returns (min_mismatch,
/// assignment) — always returns some assignment. `abort_at`: stop refining
/// once proven >= abort_at (caller's interest threshold); node-capped.
/// `forced_tail[j]`: hint cells inside the tail (single allowed candidate).
/// Requires the tail to fit in the last row plus already-placed ups
/// (k <= N), so every cell's up neighbor is placed in `grid`.
fn exact_tail(
    interior: &Interior,
    grid: &[(u16, u8)],
    start: usize,
    pieces: &[u16],
    forced_tail: &[Option<(u16, u8)>],
    abort_at: u32,
) -> (u32, Vec<(u16, u8)>) {
    let k = CELLS - start;
    debug_assert_eq!(pieces.len(), k);
    debug_assert!(k <= N, "tail must not exceed one row");
    let forced_pi: Vec<Option<usize>> = forced_tail
        .iter()
        .map(|f| f.map(|(fp, _)| pieces.iter().position(|&p| p == fp).expect("forced in pool")))
        .collect();
    let mismatch_at = |g: &[(u16, u8)], cell: usize, e: &[u8; 4]| -> u32 {
        let mut m = 0;
        if cell % N > 0 {
            let (lp, lr) = g[cell - 1];
            if interior.rot_edges[lp as usize][lr as usize][1] != e[3] {
                m += 1;
            }
        }
        let (up, ur) = g[cell - N];
        if interior.rot_edges[up as usize][ur as usize][2] != e[0] {
            m += 1;
        }
        m
    };
    // greedy incumbent: per cell, best unused (piece, rot); forced respected
    let mut best_asn: Vec<(u16, u8)> = vec![(0, 0); k];
    let mut best_mis: u32 = 0;
    {
        let mut g = grid.to_vec();
        let mut used = vec![false; k];
        for j in 0..k {
            let cell = start + j;
            let mut bm = u32::MAX;
            let mut bpick = (0usize, 0u8);
            if let Some((_, fr)) = forced_tail[j] {
                let pi = forced_pi[j].expect("forced idx");
                let e = interior.rot_edges[pieces[pi] as usize][fr as usize];
                bm = mismatch_at(&g, cell, &e);
                bpick = (pi, fr);
            } else {
                for (pi, &pid) in pieces.iter().enumerate() {
                    if used[pi] || forced_pi.iter().flatten().any(|&fpi| fpi == pi) {
                        continue;
                    }
                    for rot in 0..4u8 {
                        let e = interior.rot_edges[pid as usize][rot as usize];
                        let m = mismatch_at(&g, cell, &e);
                        if m < bm {
                            bm = m;
                            bpick = (pi, rot);
                        }
                    }
                }
            }
            let (pi, rot) = bpick;
            used[pi] = true;
            g[cell] = (pieces[pi], rot);
            best_asn[j] = (pieces[pi], rot);
            best_mis += bm;
        }
    }
    if best_mis == 0 {
        return (best_mis, best_asn);
    }
    // B&B: assign cells left-to-right; per-cell admissible LB = min over
    // UNUSED pieces of up-edge mismatch (left edges ignored: >= 0).
    // up colors are fixed (row above fully placed; k <= N guarantees it).
    let up_color: Vec<u8> = (0..k)
        .map(|j| {
            let cell = start + j;
            let (up, ur) = grid[cell - N];
            interior.rot_edges[up as usize][ur as usize][2]
        })
        .collect();
    let up_ok: Vec<Vec<bool>> = (0..k)
        .map(|j| {
            pieces
                .iter()
                .map(|&pid| {
                    (0..4u8).any(|r| {
                        interior.rot_edges[pid as usize][r as usize][0] == up_color[j]
                    })
                })
                .collect()
        })
        .collect();
    let mut asn: Vec<(u16, u8)> = vec![(0, 0); k];
    let mut used = vec![false; k];
    let mut nodes: u64 = 0;
    const CAP: u64 = 2_000_000;

    fn lb_rest(
        j: usize,
        k: usize,
        up_ok: &[Vec<bool>],
        used: &[bool],
        forced_pi: &[Option<usize>],
    ) -> u32 {
        // for each remaining cell: forced -> its piece must match up;
        // free -> 1 if NO unused piece can match its up edge
        let mut lb = 0;
        for jj in j..k {
            if let Some(pi) = forced_pi[jj] {
                if !up_ok[jj][pi] {
                    lb += 1;
                }
                continue;
            }
            let mut any = false;
            for (pi, &u) in used.iter().enumerate() {
                if !u && up_ok[jj][pi] {
                    any = true;
                    break;
                }
            }
            if !any {
                lb += 1;
            }
        }
        lb
    }

    #[allow(clippy::too_many_arguments)]
    fn go(
        interior: &Interior,
        grid: &mut Vec<(u16, u8)>,
        start: usize,
        pieces: &[u16],
        forced_tail: &[Option<(u16, u8)>],
        forced_pi: &[Option<usize>],
        j: usize,
        mis: u32,
        used: &mut Vec<bool>,
        asn: &mut Vec<(u16, u8)>,
        best_mis: &mut u32,
        best_asn: &mut Vec<(u16, u8)>,
        up_ok: &[Vec<bool>],
        nodes: &mut u64,
        abort_at: u32,
    ) {
        let k = pieces.len();
        let cut = (*best_mis).min(abort_at);
        if mis >= cut || *nodes > CAP {
            return;
        }
        if j == k {
            *best_mis = mis;
            best_asn.clone_from(asn);
            return;
        }
        if mis + lb_rest(j, k, up_ok, used, forced_pi) >= cut {
            return;
        }
        let cell = start + j;
        let lcol = if cell % N > 0 {
            let (lp, lr) = grid[cell - 1];
            Some(interior.rot_edges[lp as usize][lr as usize][1])
        } else {
            None
        };
        let ucol = {
            let (up, ur) = grid[cell - N];
            interior.rot_edges[up as usize][ur as usize][2]
        };
        let local_m = |pid: u16, rot: u8| -> u32 {
            let e = interior.rot_edges[pid as usize][rot as usize];
            u32::from(lcol.is_some_and(|l| e[3] != l)) + u32::from(e[0] != ucol)
        };
        if let Some((fp, fr)) = forced_tail[j] {
            let pi = forced_pi[j].expect("forced idx");
            let m = local_m(fp, fr);
            *nodes += 1;
            if mis + m >= (*best_mis).min(abort_at) || *nodes > CAP {
                return;
            }
            used[pi] = true;
            grid[cell] = (fp, fr);
            asn[j] = (fp, fr);
            go(
                interior, grid, start, pieces, forced_tail, forced_pi, j + 1,
                mis + m, used, asn, best_mis, best_asn, up_ok, nodes, abort_at,
            );
            used[pi] = false;
            return;
        }
        // try pieces: prefer low local mismatch
        let mut order: Vec<(u32, usize, u8)> = Vec::with_capacity(k * 2);
        for pi in 0..k {
            if used[pi] || forced_pi.iter().flatten().any(|&fpi| fpi == pi) {
                continue;
            }
            let pid = pieces[pi];
            for rot in 0..4u8 {
                order.push((local_m(pid, rot), pi, rot));
            }
        }
        order.sort_unstable_by_key(|&(m, _, _)| m);
        for (m, pi, rot) in order {
            *nodes += 1;
            if mis + m >= (*best_mis).min(abort_at) || *nodes > CAP {
                return;
            }
            used[pi] = true;
            grid[cell] = (pieces[pi], rot);
            asn[j] = (pieces[pi], rot);
            go(
                interior, grid, start, pieces, forced_tail, forced_pi, j + 1,
                mis + m, used, asn, best_mis, best_asn, up_ok, nodes, abort_at,
            );
            used[pi] = false;
        }
    }

    let mut g = grid.to_vec();
    go(
        interior, &mut g, start, pieces, forced_tail, &forced_pi, 0, 0, &mut used,
        &mut asn, &mut best_mis, &mut best_asn, &up_ok, &mut nodes, abort_at,
    );
    (best_mis, best_asn)
}

/// Exact TWO-ROW endgame: the last 28 cells (interior rows 12-13) solved as
/// a column-pair B&B — per column, place (top, bottom) jointly; top's up
/// edge is fixed by row 11, bottom's up is the just-placed top. Handles
/// forced (hint) cells — both deep hints live in row 12. Node-capped,
/// abort-bounded, greedy-seeded (always returns an assignment).
/// Returns (min_mismatch, assignment aligned to cells start..start+28).
fn exact_tail2(
    interior: &Interior,
    grid: &[(u16, u8)],
    start: usize,
    pieces: &[u16],
    forced_tail: &[Option<(u16, u8)>],
    abort_at: u32,
    node_cap: u64,
) -> (u32, Vec<(u16, u8)>) {
    let k = CELLS - start;
    debug_assert_eq!(k, 2 * N);
    debug_assert_eq!(pieces.len(), k);
    // up colors of row 12 cells (fixed: row 11 placed)
    let up11: Vec<u8> = (0..N)
        .map(|c| {
            let (p, r) = grid[start + c - N];
            interior.rot_edges[p as usize][r as usize][2]
        })
        .collect();
    let forced_pi = |cell_off: usize| -> Option<(usize, u8)> {
        forced_tail[cell_off].map(|(fp, fr)| {
            (
                pieces.iter().position(|&p| p == fp).expect("forced in pool"),
                fr,
            )
        })
    };
    // per column: forced constraints for top (row12) and bottom (row13)
    let f_top: Vec<Option<(usize, u8)>> = (0..N).map(|c| forced_pi(c)).collect();
    let f_bot: Vec<Option<(usize, u8)>> = (0..N).map(|c| forced_pi(N + c)).collect();
    // pool indices of forced pieces: never usable at free cells
    let reserved: u32 = f_top
        .iter()
        .chain(f_bot.iter())
        .flatten()
        .fold(0u32, |m, &(pi, _)| m | 1 << pi);

    // candidate pair generation for a column given (left-top E, left-bot E)
    // and budget threshold; returns (cost, pt, rt, pb, rb) sorted by cost
    #[allow(clippy::too_many_arguments)]
    fn column_pairs(
        interior: &Interior,
        pieces: &[u16],
        used: u32,
        reserved: u32,
        c: usize,
        up: u8,
        lt: Option<u8>,
        lb_: Option<u8>,
        f_top: Option<(usize, u8)>,
        f_bot: Option<(usize, u8)>,
        max_cost: u32,
        out: &mut Vec<(u32, u8, u8, u8, u8)>,
    ) {
        out.clear();
        let np = pieces.len();
        let _ = c;
        for pt in 0..np {
            if used >> pt & 1 == 1 {
                continue;
            }
            match f_top {
                Some((fpi, _)) if pt != fpi => continue,
                None if reserved >> pt & 1 == 1 => continue,
                _ => {}
            }
            let rts: &[u8] = &[0, 1, 2, 3];
            for &rt in rts {
                if let Some((_, fr)) = f_top {
                    if rt != fr {
                        continue;
                    }
                }
                let et = interior.rot_edges[pieces[pt] as usize][rt as usize];
                let cost_t = u32::from(et[0] != up) + u32::from(lt.is_some_and(|l| et[3] != l));
                if cost_t > max_cost {
                    continue;
                }
                for pb in 0..np {
                    if pb == pt || used >> pb & 1 == 1 {
                        continue;
                    }
                    match f_bot {
                        Some((fpi, _)) if pb != fpi => continue,
                        None if reserved >> pb & 1 == 1 => continue,
                        _ => {}
                    }
                    for rb in 0..4u8 {
                        if let Some((_, fr)) = f_bot {
                            if rb != fr {
                                continue;
                            }
                        }
                        let eb = interior.rot_edges[pieces[pb] as usize][rb as usize];
                        let cost = cost_t
                            + u32::from(eb[0] != et[2])
                            + u32::from(lb_.is_some_and(|l| eb[3] != l));
                        if cost <= max_cost {
                            out.push((cost, pt as u8, rt, pb as u8, rb));
                        }
                    }
                }
            }
        }
        out.sort_unstable_by_key(|&(m, ..)| m);
    }

    // greedy incumbent
    let best_asn: Vec<(u16, u8)>;
    let best_mis: u32;
    {
        let mut used: u32 = 0;
        let mut mis = 0u32;
        let mut asn: Vec<(u16, u8)> = vec![(0, 0); k];
        let mut lt: Option<u8> = None;
        let mut lb_: Option<u8> = None;
        let mut scratch = Vec::new();
        for c in 0..N {
            column_pairs(
                interior, pieces, used, reserved, c, up11[c], lt, lb_, f_top[c],
                f_bot[c], 99, &mut scratch,
            );
            let &(m, pt, rt, pb, rb) = scratch.first().expect("greedy pair");
            mis += m;
            used |= 1 << pt;
            used |= 1 << pb;
            let et = interior.rot_edges[pieces[pt as usize] as usize][rt as usize];
            let eb = interior.rot_edges[pieces[pb as usize] as usize][rb as usize];
            lt = Some(et[1]);
            lb_ = Some(eb[1]);
            asn[c] = (pieces[pt as usize], rt);
            asn[N + c] = (pieces[pb as usize], rb);
        }
        best_mis = mis;
        best_asn = asn;
    }
    if best_mis == 0 {
        return (best_mis, best_asn);
    }

    // B&B over columns
    struct S<'a> {
        interior: &'a Interior,
        pieces: &'a [u16],
        up11: &'a [u8],
        f_top: &'a [Option<(usize, u8)>],
        f_bot: &'a [Option<(usize, u8)>],
        reserved: u32,
        nodes: u64,
        cap: u64,
        abort_at: u32,
        best_mis: u32,
        best_asn: Vec<(u16, u8)>,
        asn: Vec<(u16, u8)>,
    }
    #[allow(clippy::too_many_arguments)]
    fn go2(s: &mut S, c: usize, mis: u32, used: u32, lt: Option<u8>, lb_: Option<u8>) {
        let cut = s.best_mis.min(s.abort_at);
        if mis >= cut || s.nodes > s.cap {
            return;
        }
        if c == N {
            s.best_mis = mis;
            s.best_asn.clone_from(&s.asn);
            return;
        }
        let mut pairs = Vec::new();
        let max_cost = cut - mis - 1;
        column_pairs(
            s.interior, s.pieces, used, s.reserved, c, s.up11[c], lt, lb_, s.f_top[c],
            s.f_bot[c], max_cost, &mut pairs,
        );
        for &(m, pt, rt, pb, rb) in &pairs {
            s.nodes += 1;
            if mis + m >= s.best_mis.min(s.abort_at) || s.nodes > s.cap {
                return;
            }
            let et = s.interior.rot_edges[s.pieces[pt as usize] as usize][rt as usize];
            let eb = s.interior.rot_edges[s.pieces[pb as usize] as usize][rb as usize];
            s.asn[c] = (s.pieces[pt as usize], rt);
            s.asn[N + c] = (s.pieces[pb as usize], rb);
            go2(
                s,
                c + 1,
                mis + m,
                used | 1 << pt | 1 << pb,
                Some(et[1]),
                Some(eb[1]),
            );
        }
    }
    let mut s = S {
        interior,
        pieces,
        up11: &up11,
        f_top: &f_top,
        f_bot: &f_bot,
        reserved,
        nodes: 0,
        cap: node_cap,
        abort_at,
        best_mis,
        best_asn: best_asn.clone(),
        asn: vec![(0, 0); k],
    };
    go2(&mut s, 0, 0, 0, None, None);
    (s.best_mis, s.best_asn)
}

/// `break_schedule`: ascending depth gates; the (j+1)-th mismatch may only be
/// spent at scan depth >= break_schedule[j]. Empty = perfect-only DFS.
/// Break candidates are cost-1 only (exactly one of left/up mismatched) and
/// only at 2-constraint cells; cost-2 placements are never taken.
/// `exact_tail_k`: when scan reaches depth CELLS-k, solve the endgame
/// EXACTLY (optimal assignment of the k leftover pieces) and backtrack;
/// every deep prefix gets its optimal completion (anytime II maximization).
#[allow(clippy::too_many_lines)]
fn dfs_run(
    interior: &Interior,
    seed: u64,
    budget_ms: u64,
    hinted: bool,
    break_schedule: &[usize],
    exact_tail_k: usize,
    restart_ms: u64,
    tail2: bool,
) -> DfsResult {
    let mut rng = AlnsRng::new(seed);
    // candidate tables keyed by (left color, up color); 0 = unconstrained
    // pack candidate as pid<<2 | rot
    let pack = |pid: usize, rot: usize| -> u16 { ((pid << 2) | rot) as u16 };
    // hint pieces are only placeable at their hint cells (using one
    // elsewhere makes hint compliance impossible) — exclude from tables
    let mut hint_piece = [false; 196];
    if hinted {
        for &(_, pid, _) in &interior.hints {
            hint_piece[pid] = true;
        }
    }
    let mut cand_lu = vec![Vec::new(); 23 * 23];
    let mut cand_l: Vec<Vec<u16>> = vec![Vec::new(); 23];
    let mut cand_u: Vec<Vec<u16>> = vec![Vec::new(); 23];
    let mut cand_free: Vec<u16> = Vec::new();
    for pid in 0..196usize {
        if hint_piece[pid] {
            continue;
        }
        for rot in 0..4usize {
            let e = interior.rot_edges[pid][rot];
            // W=e[3] matches left's E; N=e[0] matches up's S
            cand_lu[e[3] as usize * 23 + e[0] as usize].push(pack(pid, rot));
            cand_l[e[3] as usize].push(pack(pid, rot));
            cand_u[e[0] as usize].push(pack(pid, rot));
            cand_free.push(pack(pid, rot));
        }
    }

    // pre-placed hints: a hint fixes (piece, rot) at a cell; its edges may
    // still mismatch neighbors at normal break cost (hint-compliance is
    // about placement, not edge perfection)
    let mut forced: Vec<Option<(u16, u8)>> = vec![None; CELLS];
    if hinted {
        for &(cell, pid, rot) in &interior.hints {
            forced[cell] = Some((pid as u16, rot));
        }
    }
    // hard neighbor pre-filters for hints BEFORE the first break gate (their
    // mismatches are unpayable there, so filtering early is sound and avoids
    // the late-constraint-check blowup); deep hints stay break-payable
    let first_gate = break_schedule.first().copied().unwrap_or(usize::MAX);
    let mut req_e: Vec<Option<u8>> = vec![None; CELLS];
    let mut req_s: Vec<Option<u8>> = vec![None; CELLS];
    for cell in 0..CELLS {
        if let Some((pid, rot)) = forced[cell] {
            if cell < first_gate {
                let e = interior.rot_edges[pid as usize][rot as usize];
                if cell % N > 0 {
                    req_e[cell - 1] = Some(e[3]);
                }
                if cell >= N {
                    req_s[cell - N] = Some(e[0]);
                }
            }
        }
    }
    // break reservation: 1 break held back per not-yet-placed deep hint so
    // ordinary breaks can't starve the hints (hint placement uses the full
    // budget). hint_after[d] = deep-hint cells at index >= d
    let mut hint_after = vec![0u32; CELLS + 1];
    for d in (0..CELLS).rev() {
        hint_after[d] = hint_after[d + 1]
            + u32::from(forced[d].is_some() && d >= first_gate);
    }
    // rim-supply tie-break: at rim cells prefer candidates whose outward
    // color still has border-supply headroom (rim profile -> supply shape,
    // free IB potential, zero II cost). rim_side[d] = the outward side used
    // for the preference test (first one for interior corners).
    let rim_side: Vec<Option<usize>> = (0..CELLS)
        .map(|c| {
            let (sides, n) = rim_sides_of(c);
            if n > 0 { Some(sides[0]) } else { None }
        })
        .collect();
    let mut rim_used = [0u32; 23];

    let mut grid: Vec<(u16, u8)> = vec![(u16::MAX, 0); CELLS];
    let mut choice_idx = vec![0usize; CELLS + 1];
    let mut cost_at = vec![0u32; CELLS];
    let budget = break_schedule.len() as u32;
    let mut max_depth = 0usize;
    let mut best_prefix: Vec<(u16, u8)> = Vec::new();
    let mut best_complete: Option<(Vec<(u16, u8)>, u32)> = None;
    let mut completes_found: u64 = 0;
    let mut nodes: u64 = 0;
    let mut ms_at_max: u128 = 0;
    let t0 = Instant::now();

    let set_used = |used: &mut [u64; 4], pid: u16| used[pid as usize >> 6] |= 1 << (pid & 63);
    let clr_used = |used: &mut [u64; 4], pid: u16| used[pid as usize >> 6] &= !(1 << (pid & 63));
    let is_used = |used: &[u64; 4], pid: u16| used[pid as usize >> 6] >> (pid & 63) & 1 == 1;

    // exact tail handles forced (hint) cells; clamp to one row so every
    // tail cell's up-neighbor is placed. tail2 = two-row column-pair B&B.
    let k_exact = if tail2 { 2 * N } else { exact_tail_k.min(N) };

    'epoch: loop {
    // fresh shuffle per epoch = structurally new search tree
    for v in &mut cand_lu {
        shuffle(v, &mut rng);
    }
    for v in &mut cand_l {
        shuffle(v, &mut rng);
    }
    for v in &mut cand_u {
        shuffle(v, &mut rng);
    }
    shuffle(&mut cand_free, &mut rng);
    let mut used = [0u64; 4];
    grid.iter_mut().for_each(|g| *g = (u16::MAX, 0));
    choice_idx.iter_mut().for_each(|c| *c = 0);
    cost_at.iter_mut().for_each(|c| *c = 0);
    let mut spent: u32 = 0;
    rim_used = [0u32; 23];
    let epoch_t0 = Instant::now();

    let mut d = 0usize; // scan index == cell (row-major)
    let mut backtrack_now = false;
    loop {
        if k_exact > 0 && d == CELLS - k_exact && !backtrack_now {
            // optimal endgame for this prefix, then force backtrack
            let mut rest: Vec<u16> = Vec::with_capacity(k_exact);
            for pid in 0..196u16 {
                if !is_used(&used, pid) {
                    rest.push(pid);
                }
            }
            let abort_at = best_complete
                .as_ref()
                .map_or(u32::MAX, |&(_, b)| b.saturating_sub(spent));
            if abort_at > 0 {
                let (mis, asn) = if tail2 {
                    exact_tail2(interior, &grid, d, &rest, &forced[d..], abort_at, 30_000)
                } else {
                    exact_tail(interior, &grid, d, &rest, &forced[d..], abort_at)
                };
                completes_found += 1;
                if best_complete.as_ref().is_none_or(|&(_, b)| spent + mis < b) {
                    let mut full = grid.clone();
                    for (j, &pr) in asn.iter().enumerate() {
                        full[d + j] = pr;
                    }
                    let recount = count_breaks(interior, &full);
                    assert_eq!(recount, spent + mis, "exact-tail accounting");
                    best_complete = Some((full, spent + mis));
                    if spent + mis == 0 {
                        let (full, _) = best_complete.clone().expect("just set");
                        return DfsResult {
                            seed,
                            max_depth: CELLS,
                            nodes,
                            ms_at_max: t0.elapsed().as_millis(),
                            complete: best_complete,
                            completes_found,
                            best_prefix: full,
                        };
                    }
                }
            }
            backtrack_now = true;
        }
        if d == CELLS {
            let recount = count_breaks(interior, &grid);
            assert_eq!(recount, spent, "break accounting mismatch");
            completes_found += 1;
            let better = best_complete.as_ref().is_none_or(|(_, b)| spent < *b);
            if better {
                best_complete = Some((grid.clone(), spent));
            }
            if spent == 0 {
                // perfect interior: cannot do better
                return DfsResult {
                    seed,
                    max_depth: CELLS,
                    nodes,
                    ms_at_max: t0.elapsed().as_millis(),
                    complete: best_complete,
                    completes_found,
                    best_prefix: grid,
                };
            }
            // keep searching for a lower-break complete
            backtrack_now = true;
        }
        nodes += 1;
        if nodes & 0xFFFF == 0 {
            if t0.elapsed().as_millis() as u64 >= budget_ms {
                return DfsResult {
                    seed, max_depth, nodes, ms_at_max,
                    complete: best_complete, completes_found, best_prefix,
                };
            }
            if epoch_t0.elapsed().as_millis() as u64 >= restart_ms {
                continue 'epoch;
            }
        }

        let mut placed = false;
        if !backtrack_now {
            let lcol = if d % N > 0 {
                let (pid, rot) = grid[d - 1];
                Some(interior.rot_edges[pid as usize][rot as usize][1])
            } else {
                None
            };
            let ucol = if d >= N {
                let (pid, rot) = grid[d - N];
                Some(interior.rot_edges[pid as usize][rot as usize][2])
            } else {
                None
            };

            if let Some((fp, fr)) = forced[d] {
                // forced cell: single candidate (first visit only); its edge
                // mismatches cost breaks, gated like any other break
                if choice_idx[d] == 0 && !is_used(&used, fp) {
                    let e = interior.rot_edges[fp as usize][fr as usize];
                    let cost = u32::from(lcol.is_some_and(|c| c != e[3]))
                        + u32::from(ucol.is_some_and(|c| c != e[0]));
                    let gate_ok = cost == 0
                        || (spent + cost <= budget
                            && d >= break_schedule[(spent + cost - 1) as usize]);
                    if gate_ok {
                        grid[d] = (fp, fr);
                        set_used(&mut used, fp);
                        choice_idx[d] = 1;
                        cost_at[d] = cost;
                        spent += cost;
                        placed = true;
                    }
                }
            } else {
                // virtual candidate sequence: [cost-0][up-break][left-break]
                let cost0: &[u16] = match (lcol, ucol) {
                    (Some(l), Some(u)) => &cand_lu[l as usize * 23 + u as usize],
                    (Some(l), None) => &cand_l[l as usize],
                    (None, Some(u)) => &cand_u[u as usize],
                    (None, None) => &cand_free,
                };
                // breaks: only at 2-constraint cells, within schedule gate,
                // leaving 1 reserved break per remaining deep hint
                let break_open = spent + 1 + hint_after[d] <= budget
                    && d >= break_schedule[spent as usize]
                    && lcol.is_some()
                    && ucol.is_some();
                let (l, u) = (
                    lcol.unwrap_or(0) as usize,
                    ucol.unwrap_or(0) as usize,
                );
                let seg1: &[u16] = if break_open { &cand_l[l] } else { &[] };
                let seg2: &[u16] = if break_open { &cand_u[u] } else { &[] };
                let (n0, n1, n2) = (cost0.len(), seg1.len(), seg2.len());
                let l_total = n0 + n1 + n2;
                // rim cells iterate the sequence twice: pass 1 takes only
                // candidates whose outward color has border-supply headroom
                let lim = if rim_side[d].is_some() { 2 * l_total } else { l_total };

                let mut i = choice_idx[d];
                while i < lim {
                    let (vi, pass2) = if i < l_total { (i, false) } else { (i - l_total, true) };
                    let (c, cost) = if vi < n0 {
                        (cost0[vi], 0u32)
                    } else if vi < n0 + n1 {
                        let c = seg1[vi - n0];
                        // skip entries that also match up (those are cost-0)
                        let e = interior.rot_edges[(c >> 2) as usize][(c & 3) as usize];
                        if e[0] as usize == u {
                            i += 1;
                            continue;
                        }
                        (c, 1)
                    } else {
                        let c = seg2[vi - n0 - n1];
                        let e = interior.rot_edges[(c >> 2) as usize][(c & 3) as usize];
                        if e[3] as usize == l {
                            i += 1;
                            continue;
                        }
                        (c, 1)
                    };
                    let (pid, rot) = (c >> 2, (c & 3) as u8);
                    i += 1;
                    if is_used(&used, pid) {
                        continue;
                    }
                    let e = interior.rot_edges[pid as usize][rot as usize];
                    if req_e[d].is_some_and(|x| x != e[1]) || req_s[d].is_some_and(|x| x != e[2]) {
                        continue;
                    }
                    if let Some(side) = rim_side[d] {
                        let oc = e[side] as usize;
                        let headroom = rim_used[oc] < interior.edge_inward_supply[oc];
                        if headroom == pass2 {
                            continue; // pass1 wants headroom, pass2 the rest
                        }
                    }
                    grid[d] = (pid, rot);
                    set_used(&mut used, pid);
                    choice_idx[d] = i;
                    cost_at[d] = cost;
                    spent += cost;
                    placed = true;
                    break;
                }
            }
        }

        if placed {
            if rim_side[d].is_some() {
                let (sides, n) = rim_sides_of(d);
                let (pid, rot) = grid[d];
                let e = interior.rot_edges[pid as usize][rot as usize];
                for &s in &sides[..n] {
                    rim_used[e[s] as usize] += 1;
                }
            }
            d += 1;
            if d > max_depth {
                max_depth = d;
                ms_at_max = t0.elapsed().as_millis();
                best_prefix = grid[..d].to_vec();
            }
        } else {
            // exhausted candidates at d (or returning from a complete): backtrack
            backtrack_now = false;
            choice_idx[d] = 0;
            if d == 0 {
                // tree exhausted under this shuffle: restart
                continue 'epoch;
            }
            d -= 1;
            // un-place d (skip-back over forced cells consumes their flag too)
            let (pid, rot_u) = grid[d];
            if rim_side[d].is_some() {
                let (sides, n) = rim_sides_of(d);
                let e = interior.rot_edges[pid as usize][rot_u as usize];
                for &s in &sides[..n] {
                    rim_used[e[s] as usize] -= 1;
                }
            }
            clr_used(&mut used, pid);
            grid[d] = (u16::MAX, 0);
            spent -= cost_at[d];
            cost_at[d] = 0;
            if forced[d].is_some() {
                // forced cell has no alternatives: keep backtracking
                choice_idx[d] = 0;
                loop {
                    if d == 0 {
                        continue 'epoch;
                    }
                    d -= 1;
                    let (pid, rot_u) = grid[d];
                    if rim_side[d].is_some() {
                        let (sides, n) = rim_sides_of(d);
                        let e = interior.rot_edges[pid as usize][rot_u as usize];
                        for &s in &sides[..n] {
                            rim_used[e[s] as usize] -= 1;
                        }
                    }
                    clr_used(&mut used, pid);
                    grid[d] = (u16::MAX, 0);
                    spent -= cost_at[d];
                    cost_at[d] = 0;
                    if forced[d].is_none() {
                        break;
                    }
                    choice_idx[d] = 0;
                }
            }
        }
    }
    } // 'epoch
}

// --------------------------------------------------------------------- SA

struct SaResult {
    seed: u64,
    best_ii: u32,
    /// rim-supply overlap (IB upper bound) of the best-scoring state
    best_overlap: u32,
    best_state: Vec<(u16, u8)>,
    moves: u64,
}

/// position-exact rim targets from an assembled full board: for each rim
/// side of each interior cell, the color of the adjacent BORDER piece's
/// inward-facing edge. targets[cell] aligned with rim_sides_of(cell).
fn border_targets_from(path: &str, interior: &Interior) -> Vec<[Option<u8>; 2]> {
    let txt = std::fs::read_to_string(path).expect("read attached board");
    let v: serde_json::Value = serde_json::from_str(&txt).expect("parse attached board");
    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, _) = load_puzzle_with_hints(&puzzle_path).expect("puzzle");
    let mut place = std::collections::HashMap::new();
    for e in v["placement"].as_array().expect("placement") {
        place.insert(
            e["pos"].as_u64().expect("pos") as usize,
            (
                e["piece_id"].as_u64().expect("pid") as u16,
                e["rotation"].as_u64().expect("rot") as u8,
            ),
        );
    }
    let edge = |pos: usize, side: usize| -> Option<u8> {
        place.get(&pos).map(|&(p, r)| {
            puzzle
                .piece(p)
                .expect("piece")
                .edges
                .rotated(Rotation::from_u8(r).expect("rot"))
                .as_array()[side]
        })
    };
    let _ = interior;
    let mut out = vec![[None, None]; CELLS];
    for cell in 0..CELLS {
        let (sides, n) = rim_sides_of(cell);
        let (y, x) = (cell / N, cell % N);
        let full = (y + 1) * 16 + (x + 1);
        for (slot, &s) in sides[..n].iter().enumerate() {
            // neighbor border cell + its facing side
            let (npos, nside) = match s {
                0 => (full - 16, 2),
                2 => (full + 16, 0),
                3 => (full - 1, 1),
                _ => (full + 1, 3),
            };
            out[cell][slot] = edge(npos, nside);
        }
    }
    out
}

/// outward (rim) sides of a 14x14 cell: up to 2 (corners of the interior)
fn rim_sides_of(cell: usize) -> ([usize; 2], usize) {
    let (y, x) = (cell / N, cell % N);
    let mut sides = [0usize; 2];
    let mut n = 0;
    if y == 0 {
        sides[n] = 0;
        n += 1;
    }
    if y == N - 1 {
        sides[n] = 2;
        n += 1;
    }
    if x == 0 {
        sides[n] = 3;
        n += 1;
    }
    if x == N - 1 {
        sides[n] = 1;
        n += 1;
    }
    (sides, n)
}

struct SaState<'a> {
    interior: &'a Interior,
    cell_piece: Vec<u16>,
    cell_rot: Vec<u8>,
    piece_cell: Vec<u16>,
}

impl SaState<'_> {
    fn edges_at(&self, cell: usize) -> [u8; 4] {
        self.interior.rot_edges[self.cell_piece[cell] as usize][self.cell_rot[cell] as usize]
    }

    /// matched II edges incident to `cell` under current assignment
    fn local_matches(&self, cell: usize) -> u32 {
        let e = self.edges_at(cell);
        let (y, x) = (cell / N, cell % N);
        let mut m = 0;
        if x > 0 && self.edges_at(cell - 1)[1] == e[3] {
            m += 1;
        }
        if x + 1 < N && self.edges_at(cell + 1)[3] == e[1] {
            m += 1;
        }
        if y > 0 && self.edges_at(cell - N)[2] == e[0] {
            m += 1;
        }
        if y + 1 < N && self.edges_at(cell + N)[0] == e[2] {
            m += 1;
        }
        m
    }

    /// matched count over a set of cells, counting each edge once
    /// (edges with both ends in the set counted once; edges to outside once)
    fn region_matches(&self, cells: &[usize], member: &[bool]) -> u32 {
        let mut m = 0;
        for &cell in cells {
            let e = self.edges_at(cell);
            let (y, x) = (cell / N, cell % N);
            // count left/up always; right/down only when neighbor outside set
            if x > 0 && self.edges_at(cell - 1)[1] == e[3] {
                m += 1;
            }
            if y > 0 && self.edges_at(cell - N)[2] == e[0] {
                m += 1;
            }
            if x + 1 < N && !member[cell + 1] && self.edges_at(cell + 1)[3] == e[1] {
                m += 1;
            }
            if y + 1 < N && !member[cell + N] && self.edges_at(cell + N)[0] == e[2] {
                m += 1;
            }
        }
        m
    }

    fn full_ii(&self) -> u32 {
        let mut m = 0;
        for cell in 0..CELLS {
            let e = self.edges_at(cell);
            let (y, x) = (cell / N, cell % N);
            if x + 1 < N && self.edges_at(cell + 1)[3] == e[1] {
                m += 1;
            }
            if y + 1 < N && self.edges_at(cell + N)[0] == e[2] {
                m += 1;
            }
        }
        m
    }
}

/// Optimal reassignment of `cells` (region) using exactly the pieces
/// currently on them. Pure B&B (no state mutation); incumbent = current
/// assignment, so the returned matched count is >= the current one.
/// Returns (assignment aligned to `cells`, matched count of the region).
fn exact_region(
    st: &SaState,
    cells: &[usize],
    member: &[bool],
    node_cap: u64,
) -> (Vec<(u16, u8)>, u32) {
    let interior = st.interior;
    let k = cells.len();
    let mut idx_of = vec![usize::MAX; CELLS];
    for (j, &c) in cells.iter().enumerate() {
        idx_of[c] = j;
    }
    // per region cell: edges to FIXED outside neighbors (side, required color)
    // and to EARLIER region cells (side, earlier index)
    let mut fixed: Vec<Vec<(usize, u8)>> = vec![Vec::new(); k];
    let mut earlier: Vec<Vec<(usize, usize)>> = vec![Vec::new(); k];
    for (j, &c) in cells.iter().enumerate() {
        let (y, x) = (c / N, c % N);
        let nbs: [(bool, usize, usize, usize); 4] = [
            (x > 0, c.wrapping_sub(1), 3, 1),       // my W vs left's E
            (x + 1 < N, c + 1, 1, 3),               // my E vs right's W
            (y > 0, c.wrapping_sub(N), 0, 2),       // my N vs up's S
            (y + 1 < N, c + N, 2, 0),               // my S vs down's N
        ];
        for &(ok, nc, my_side, their_side) in &nbs {
            if !ok {
                continue;
            }
            if member[nc] {
                let i = idx_of[nc];
                if i < j {
                    earlier[j].push((my_side, i));
                }
            } else {
                fixed[j].push((my_side, st.edges_at(nc)[their_side]));
            }
        }
    }
    // optimistic suffix bound: every remaining edge matches
    let mut suffix_max = vec![0u32; k + 1];
    for j in (0..k).rev() {
        suffix_max[j] = suffix_max[j + 1] + (fixed[j].len() + earlier[j].len()) as u32;
    }
    let pool: Vec<u16> = cells.iter().map(|&c| st.cell_piece[c]).collect();
    let cur: Vec<(u16, u8)> = cells
        .iter()
        .map(|&c| (st.cell_piece[c], st.cell_rot[c]))
        .collect();
    let place_matches = |asn: &[(u16, u8)], j: usize, pid: u16, rot: u8| -> u32 {
        let e = interior.rot_edges[pid as usize][rot as usize];
        let mut m = 0;
        for &(side, color) in &fixed[j] {
            if e[side] == color {
                m += 1;
            }
        }
        for &(side, i) in &earlier[j] {
            let (ip, ir) = asn[i];
            let ie = interior.rot_edges[ip as usize][ir as usize];
            // their side opposite mine: N<->S (0<->2), E<->W (1<->3)
            if e[side] == ie[(side + 2) % 4] {
                m += 1;
            }
        }
        m
    };
    // incumbent
    let mut best_asn = cur.clone();
    let mut best_m = {
        let mut m = 0;
        for j in 0..k {
            m += place_matches(&cur, j, cur[j].0, cur[j].1);
        }
        m
    };
    if best_m == suffix_max[0] {
        return (best_asn, best_m); // already perfect region
    }

    let region_max = suffix_max[0];

    #[allow(clippy::too_many_arguments)]
    fn go(
        k: usize,
        j: usize,
        m: u32,
        used: &mut u32,
        asn: &mut Vec<(u16, u8)>,
        pool: &[u16],
        place: &dyn Fn(&[(u16, u8)], usize, u16, u8) -> u32,
        suffix_max: &[u32],
        best_m: &mut u32,
        best_asn: &mut Vec<(u16, u8)>,
        nodes: &mut u64,
        cap: u64,
        region_max: u32,
    ) {
        if *nodes > cap {
            return;
        }
        if j == k {
            if m > *best_m {
                *best_m = m;
                best_asn.clone_from(asn);
                if m == region_max {
                    *nodes = cap + 1; // perfect region: unwind everything
                }
            }
            return;
        }
        if m + suffix_max[j] <= *best_m {
            return;
        }
        // stack-allocated candidate order (k<=10 pieces x 4 rots)
        let mut order = [(0u32, 0u8, 0u8); 40];
        let mut no = 0usize;
        for (pi, &pid) in pool.iter().enumerate() {
            if *used >> pi & 1 == 1 {
                continue;
            }
            for rot in 0..4u8 {
                order[no] = (place(asn, j, pid, rot), pi as u8, rot);
                no += 1;
            }
        }
        order[..no].sort_unstable_by(|a, b| b.0.cmp(&a.0));
        for &(madd, pi, rot) in &order[..no] {
            let pi = pi as usize;
            *nodes += 1;
            if *nodes > cap {
                return;
            }
            *used |= 1 << pi;
            asn[j] = (pool[pi], rot);
            go(
                k, j + 1, m + madd, used, asn, pool, place, suffix_max, best_m,
                best_asn, nodes, cap, region_max,
            );
            *used &= !(1 << pi);
        }
    }

    let mut asn = cur;
    let mut used: u32 = 0;
    let mut nodes: u64 = 0;
    go(
        k, 0, 0, &mut used, &mut asn, &pool, &place_matches, &suffix_max,
        &mut best_m, &mut best_asn, &mut nodes, node_cap, region_max,
    );
    (best_asn, best_m)
}

#[allow(clippy::too_many_lines)]
fn sa_run(
    interior: &Interior,
    seed: u64,
    budget_ms: u64,
    hinted: bool,
    t0_temp: f64,
    init: Option<&[(u16, u8)]>,
    rim_lambda: f64,
    targets: Option<&[[Option<u8>; 2]]>,
) -> SaResult {
    let mut rng = AlnsRng::new(seed.wrapping_mul(0x9E37_79B9).wrapping_add(seed));
    let mut st = SaState {
        interior,
        cell_piece: (0..CELLS as u16).collect(),
        cell_rot: vec![0u8; CELLS],
        piece_cell: (0..CELLS as u16).collect(),
    };
    if let Some(init) = init {
        assert_eq!(init.len(), CELLS, "init must cover all 196 cells");
        for (cell, &(pid, rot)) in init.iter().enumerate() {
            st.cell_piece[cell] = pid;
            st.cell_rot[cell] = rot;
            st.piece_cell[pid as usize] = cell as u16;
        }
    } else {
        // random init permutation + rots
        let mut perm: Vec<u16> = (0..CELLS as u16).collect();
        shuffle(&mut perm, &mut rng);
        for (cell, &pid) in perm.iter().enumerate() {
            st.cell_piece[cell] = pid;
            st.piece_cell[pid as usize] = cell as u16;
            st.cell_rot[cell] = (rng.next_u64() & 3) as u8;
        }
    }
    // pin hints
    let hint_cell: Vec<bool> = {
        let mut v = vec![false; CELLS];
        if hinted {
            for &(cell, pid, rot) in &interior.hints {
                // swap pid into its hint cell
                let cur_cell = st.piece_cell[pid] as usize;
                let occupant = st.cell_piece[cell];
                st.cell_piece.swap(cell, cur_cell);
                st.piece_cell[pid] = cell as u16;
                st.piece_cell[occupant as usize] = cur_cell as u16;
                st.cell_rot[cell] = rot;
                v[cell] = true;
            }
        }
        v
    };

    let mut ii = st.full_ii();

    // position-exact rim term: when `targets` is given (from an attached
    // border), a rim side scores 1 iff its outward color equals the border
    // piece's inward color at that position — i.e. a REAL IB edge. At
    // lambda=1 the exchange rate vs an II edge is exact (alternating
    // projections with the border MIP).
    let lam_on = rim_lambda > 0.0 && targets.is_some();
    let rim_cell_match = |st: &SaState, cell: usize| -> i64 {
        let Some(tg) = targets else { return 0 };
        let (sides, n) = rim_sides_of(cell);
        if n == 0 {
            return 0;
        }
        let e = st.edges_at(cell);
        let mut m = 0;
        for (slot, &s) in sides[..n].iter().enumerate() {
            if tg[cell][slot] == Some(e[s]) {
                m += 1;
            }
        }
        m
    };
    let mut rim_value: i64 = if lam_on {
        (0..CELLS).map(|c| rim_cell_match(&st, c)).sum()
    } else {
        0
    };
    let score_of = |ii: u32, rv: i64| -> f64 { f64::from(ii) + rim_lambda * rv as f64 };

    let mut best_ii = ii;
    let mut best_overlap = rim_value as u32;
    let mut best_score = score_of(ii, rim_value);
    let mut best_state: Vec<(u16, u8)> = (0..CELLS)
        .map(|c| (st.cell_piece[c], st.cell_rot[c]))
        .collect();

    let t_start = Instant::now();
    let mut temp = t0_temp;
    let mut moves: u64 = 0;
    let mut last_improve: u64 = 0;
    // window-LNS scratch
    let mut member = vec![false; CELLS];


    loop {
        moves += 1;
        if moves & 0x3FF == 0 {
            let el = t_start.elapsed().as_millis() as u64;
            if el >= budget_ms {
                break;
            }
            // geometric cooling mapped to elapsed fraction; on stagnation,
            // restart from best with a warm temperature
            let frac = el as f64 / budget_ms as f64;
            temp = t0_temp * (0.005f64 / t0_temp).powf(frac);
            if moves - last_improve > 2_000_000 {
                for (c, &(pid, rot)) in best_state.iter().enumerate() {
                    st.cell_piece[c] = pid;
                    st.cell_rot[c] = rot;
                    st.piece_cell[pid as usize] = c as u16;
                }
                ii = best_ii;
                rim_value = i64::from(best_overlap);
                temp = t0_temp * 0.5;
                last_improve = moves;
            }
        }
        let kind = rng.next_u64() % 100;
        if kind < 15 {
            // ROT move
            let cell = (rng.next_u64() % CELLS as u64) as usize;
            if hint_cell[cell] {
                continue;
            }
            let old_rot = st.cell_rot[cell];
            let new_rot = ((old_rot as u64 + 1 + rng.next_u64() % 3) & 3) as u8;
            let before = st.local_matches(cell);
            let rv_b = if lam_on { rim_cell_match(&st, cell) } else { 0 };
            st.cell_rot[cell] = new_rot;
            let after = st.local_matches(cell);
            let rv_a = if lam_on { rim_cell_match(&st, cell) } else { 0 };
            let delta = after as i64 - before as i64;
            let d_rim = rv_a - rv_b;
            let dscore = delta as f64 + rim_lambda * d_rim as f64;
            if dscore >= 0.0
                || (rng.next_u64() as f64 / u64::MAX as f64) < (dscore / temp).exp()
            {
                ii = (ii as i64 + delta) as u32;
                rim_value += d_rim;
            } else {
                st.cell_rot[cell] = old_rot;
                continue;
            }
        } else if kind < 50 {
            // SWAP move, conflict-biased on the first cell
            let mut a = (rng.next_u64() % CELLS as u64) as usize;
            for _ in 0..8 {
                let s = (rng.next_u64() % CELLS as u64) as usize;
                let (y, x) = (s / N, s % N);
                let deg = u32::from(x > 0)
                    + u32::from(x + 1 < N)
                    + u32::from(y > 0)
                    + u32::from(y + 1 < N);
                if st.local_matches(s) < deg {
                    a = s;
                    break;
                }
            }
            let b = (rng.next_u64() % CELLS as u64) as usize;
            if a == b || hint_cell[a] || hint_cell[b] {
                continue;
            }
            let (pa, ra) = (st.cell_piece[a], st.cell_rot[a]);
            let (pb, rb) = (st.cell_piece[b], st.cell_rot[b]);
            let before = if a.abs_diff(b) == 1 || a.abs_diff(b) == N {
                // adjacent: count joint region once
                let cells = [a, b];
                member[a] = true;
                member[b] = true;
                let m = st.region_matches(&cells, &member);
                member[a] = false;
                member[b] = false;
                m
            } else {
                st.local_matches(a) + st.local_matches(b)
            };
            let rv_b = if lam_on {
                rim_cell_match(&st, a) + rim_cell_match(&st, b)
            } else {
                0
            };
            // place pb at a with best rot, pa at b with best rot
            st.cell_piece[a] = pb;
            st.cell_piece[b] = pa;
            let mut best = (0u32, 0u8, 0u8);
            for ra2 in 0..4u8 {
                st.cell_rot[a] = ra2;
                for rb2 in 0..4u8 {
                    st.cell_rot[b] = rb2;
                    let m = if a.abs_diff(b) == 1 || a.abs_diff(b) == N {
                        let cells = [a, b];
                        member[a] = true;
                        member[b] = true;
                        let m = st.region_matches(&cells, &member);
                        member[a] = false;
                        member[b] = false;
                        m
                    } else {
                        st.local_matches(a) + st.local_matches(b)
                    };
                    if m >= best.0 {
                        best = (m, ra2, rb2);
                    }
                }
            }
            st.cell_rot[a] = best.1;
            st.cell_rot[b] = best.2;
            let rv_a = if lam_on {
                rim_cell_match(&st, a) + rim_cell_match(&st, b)
            } else {
                0
            };
            let delta = best.0 as i64 - before as i64;
            let d_rim = rv_a - rv_b;
            let dscore = delta as f64 + rim_lambda * d_rim as f64;
            if dscore >= 0.0
                || (rng.next_u64() as f64 / u64::MAX as f64) < (dscore / temp).exp()
            {
                st.piece_cell[pb as usize] = a as u16;
                st.piece_cell[pa as usize] = b as u16;
                ii = (ii as i64 + delta) as u32;
                rim_value += d_rim;
            } else {
                st.cell_piece[a] = pa;
                st.cell_rot[a] = ra;
                st.cell_piece[b] = pb;
                st.cell_rot[b] = rb;
                continue;
            }
        } else if kind < 80 {
            // region-LNS: destroy a k×k window (or a 1×len band), greedy refill
            let mut cells: Vec<usize> = Vec::new();
            if kind < 72 {
                let k = 2 + (rng.next_u64() % 4) as usize; // 2..5
                // half the time pick the worst of 8 random windows
                let pick_worst = rng.next_u64() & 1 == 0;
                let mut wy = (rng.next_u64() % (N - k + 1) as u64) as usize;
                let mut wx = (rng.next_u64() % (N - k + 1) as u64) as usize;
                if pick_worst {
                    let mut worst = u32::MAX;
                    for _ in 0..8 {
                        let ty = (rng.next_u64() % (N - k + 1) as u64) as usize;
                        let tx = (rng.next_u64() % (N - k + 1) as u64) as usize;
                        let mut m = 0;
                        for dy in 0..k {
                            for dx in 0..k {
                                m += st.local_matches((ty + dy) * N + tx + dx);
                            }
                        }
                        if m < worst {
                            worst = m;
                            wy = ty;
                            wx = tx;
                        }
                    }
                }
                for dy in 0..k {
                    for dx in 0..k {
                        let c = (wy + dy) * N + wx + dx;
                        if !hint_cell[c] {
                            cells.push(c);
                        }
                    }
                }
            } else {
                // band: horizontal or vertical strip of 5..=10 cells
                let len = 5 + (rng.next_u64() % 6) as usize;
                let horiz = rng.next_u64() & 1 == 0;
                let lane = (rng.next_u64() % N as u64) as usize;
                let off = (rng.next_u64() % (N - len + 1) as u64) as usize;
                for j in 0..len {
                    let c = if horiz {
                        lane * N + off + j
                    } else {
                        (off + j) * N + lane
                    };
                    if !hint_cell[c] {
                        cells.push(c);
                    }
                }
            }
            if cells.is_empty() {
                continue;
            }
            for &c in &cells {
                member[c] = true;
            }
            let before = st.region_matches(&cells, &member);
            let rv_b: i64 = if lam_on {
                cells.iter().map(|&c| rim_cell_match(&st, c)).sum()
            } else {
                0
            };
            let saved: Vec<(u16, u8)> = cells.iter().map(|&c| (st.cell_piece[c], st.cell_rot[c])).collect();
            // pool = removed pieces, shuffled
            let mut pool: Vec<u16> = saved.iter().map(|&(p, _)| p).collect();
            shuffle(&mut pool, &mut rng);
            // greedy refill in scan order: pick (pool piece, rot) maximizing
            // matches against already-decided neighbors (outside window or
            // earlier refilled cells)
            let mut decided = vec![false; CELLS];
            for c in 0..CELLS {
                decided[c] = !member[c];
            }
            for &c in &cells {
                let (y, x) = (c / N, c % N);
                let mut bestm = -1i64;
                let mut bestpick = (0usize, 0u8);
                for (pi, &pid) in pool.iter().enumerate() {
                    if pid == u16::MAX {
                        continue;
                    }
                    for rot in 0..4u8 {
                        let e = interior.rot_edges[pid as usize][rot as usize];
                        let mut m = 0i64;
                        if x > 0 && decided[c - 1] {
                            let ne = st.edges_at(c - 1);
                            if ne[1] == e[3] {
                                m += 1;
                            }
                        }
                        if x + 1 < N && decided[c + 1] {
                            let ne = st.edges_at(c + 1);
                            if ne[3] == e[1] {
                                m += 1;
                            }
                        }
                        if y > 0 && decided[c - N] {
                            let ne = st.edges_at(c - N);
                            if ne[2] == e[0] {
                                m += 1;
                            }
                        }
                        if y + 1 < N && decided[c + N] {
                            let ne = st.edges_at(c + N);
                            if ne[0] == e[2] {
                                m += 1;
                            }
                        }
                        if m > bestm {
                            bestm = m;
                            bestpick = (pi, rot);
                        }
                    }
                }
                let (pi, rot) = bestpick;
                let pid = pool[pi];
                pool[pi] = u16::MAX;
                st.cell_piece[c] = pid;
                st.cell_rot[c] = rot;
                st.piece_cell[pid as usize] = c as u16;
                decided[c] = true;
            }
            let after = st.region_matches(&cells, &member);
            let rv_a: i64 = if lam_on {
                cells.iter().map(|&c| rim_cell_match(&st, c)).sum()
            } else {
                0
            };
            let delta = after as i64 - before as i64;
            let d_rim = rv_a - rv_b;
            let dscore = delta as f64 + rim_lambda * d_rim as f64;
            let accept = dscore >= 0.0
                || (rng.next_u64() as f64 / u64::MAX as f64) < (dscore / temp).exp();
            if accept {
                ii = (ii as i64 + delta) as u32;
                rim_value += d_rim;
            } else {
                for (idx, &c) in cells.iter().enumerate() {
                    let (pid, rot) = saved[idx];
                    st.cell_piece[c] = pid;
                    st.cell_rot[c] = rot;
                    st.piece_cell[pid as usize] = c as u16;
                }
            }
            for &c in &cells {
                member[c] = false;
            }
        } else if kind < 97 {
            // extra region-LNS pressure on the worst 3x3 (cheap, frequent)
            let mut wy = 0;
            let mut wx = 0;
            let mut worst = u32::MAX;
            for _ in 0..4 {
                let ty = (rng.next_u64() % (N - 3 + 1) as u64) as usize;
                let tx = (rng.next_u64() % (N - 3 + 1) as u64) as usize;
                let mut m = 0;
                for dy in 0..3 {
                    for dx in 0..3 {
                        m += st.local_matches((ty + dy) * N + tx + dx);
                    }
                }
                if m < worst {
                    worst = m;
                    wy = ty;
                    wx = tx;
                }
            }
            let mut cells = Vec::with_capacity(9);
            for dy in 0..3 {
                for dx in 0..3 {
                    let c = (wy + dy) * N + wx + dx;
                    if !hint_cell[c] {
                        cells.push(c);
                    }
                }
            }
            if cells.len() < 2 {
                continue;
            }
            for &c in &cells {
                member[c] = true;
            }
            let before = st.region_matches(&cells, &member);
            let (asn, after) = exact_region(&st, &cells, &member, 3_000);
            if after > before {
                let saved: Vec<(u16, u8)> =
                    cells.iter().map(|&c| (st.cell_piece[c], st.cell_rot[c])).collect();
                let rv_b: i64 = if lam_on {
                    cells.iter().map(|&c| rim_cell_match(&st, c)).sum()
                } else {
                    0
                };
                for (j, &c) in cells.iter().enumerate() {
                    let (pid, rot) = asn[j];
                    st.cell_piece[c] = pid;
                    st.cell_rot[c] = rot;
                    st.piece_cell[pid as usize] = c as u16;
                }
                let rv_a: i64 = if lam_on {
                    cells.iter().map(|&c| rim_cell_match(&st, c)).sum()
                } else {
                    0
                };
                let d_rim = rv_a - rv_b;
                let dscore = f64::from(after - before) + rim_lambda * d_rim as f64;
                if dscore > 0.0 {
                    ii += after - before;
                    rim_value += d_rim;
                } else {
                    for (j, &c) in cells.iter().enumerate() {
                        let (pid, rot) = saved[j];
                        st.cell_piece[c] = pid;
                        st.cell_rot[c] = rot;
                        st.piece_cell[pid as usize] = c as u16;
                    }
                }
            }
            for &c in &cells {
                member[c] = false;
            }
        } else {
            // exact-region: optimal reassignment of a small worst window's
            // own pieces (incumbent-seeded B&B -> never worsening)
            let (kw, kh) = if kind < 99 {
                (3usize, 3usize)
            } else if rng.next_u64() & 1 == 0 {
                (5, 2)
            } else {
                (2, 5)
            };
            let mut wy = 0;
            let mut wx = 0;
            let mut worst = u32::MAX;
            for _ in 0..8 {
                let ty = (rng.next_u64() % (N - kh + 1) as u64) as usize;
                let tx = (rng.next_u64() % (N - kw + 1) as u64) as usize;
                let mut m = 0;
                for dy in 0..kh {
                    for dx in 0..kw {
                        m += st.local_matches((ty + dy) * N + tx + dx);
                    }
                }
                if m < worst {
                    worst = m;
                    wy = ty;
                    wx = tx;
                }
            }
            let mut cells = Vec::with_capacity(kw * kh);
            for dy in 0..kh {
                for dx in 0..kw {
                    let c = (wy + dy) * N + wx + dx;
                    if !hint_cell[c] {
                        cells.push(c);
                    }
                }
            }
            if cells.len() < 2 {
                continue;
            }
            for &c in &cells {
                member[c] = true;
            }
            let before = st.region_matches(&cells, &member);
            let (asn, after) = exact_region(&st, &cells, &member, 200_000);
            if after > before {
                let saved: Vec<(u16, u8)> =
                    cells.iter().map(|&c| (st.cell_piece[c], st.cell_rot[c])).collect();
                let rv_b: i64 = if lam_on {
                    cells.iter().map(|&c| rim_cell_match(&st, c)).sum()
                } else {
                    0
                };
                for (j, &c) in cells.iter().enumerate() {
                    let (pid, rot) = asn[j];
                    st.cell_piece[c] = pid;
                    st.cell_rot[c] = rot;
                    st.piece_cell[pid as usize] = c as u16;
                }
                let rv_a: i64 = if lam_on {
                    cells.iter().map(|&c| rim_cell_match(&st, c)).sum()
                } else {
                    0
                };
                let d_rim = rv_a - rv_b;
                let dscore = f64::from(after - before) + rim_lambda * d_rim as f64;
                if dscore > 0.0 {
                    ii += after - before;
                    rim_value += d_rim;
                } else {
                    for (j, &c) in cells.iter().enumerate() {
                        let (pid, rot) = saved[j];
                        st.cell_piece[c] = pid;
                        st.cell_rot[c] = rot;
                        st.piece_cell[pid as usize] = c as u16;
                    }
                }
            }
            for &c in &cells {
                member[c] = false;
            }
        }

        let sc = score_of(ii, rim_value);
        if sc > best_score {
            best_score = sc;
            best_ii = ii;
            best_overlap = rim_value as u32;
            for (c, slot) in best_state.iter_mut().enumerate() {
                *slot = (st.cell_piece[c], st.cell_rot[c]);
            }
            last_improve = moves;
        }
    }

    SaResult { seed, best_ii, best_overlap, best_state, moves }
}

/// greedy completion of a (possibly partial) prefix into a full assignment:
/// remaining cells get the unused (piece, rot) maximizing matches vs placed
/// left/up neighbors, scan order
fn greedy_complete(interior: &Interior, prefix: &[(u16, u8)]) -> Vec<(u16, u8)> {
    let mut grid: Vec<(u16, u8)> = vec![(u16::MAX, 0); CELLS];
    let mut used = vec![false; 196];
    for (cell, &(pid, rot)) in prefix.iter().enumerate() {
        grid[cell] = (pid, rot);
        used[pid as usize] = true;
    }
    for cell in prefix.len()..CELLS {
        let (y, x) = (cell / N, cell % N);
        let mut best = (-1i64, 0u16, 0u8);
        for pid in 0..196u16 {
            if used[pid as usize] {
                continue;
            }
            for rot in 0..4u8 {
                let e = interior.rot_edges[pid as usize][rot as usize];
                let mut m = 0i64;
                if x > 0 {
                    let (lp, lr) = grid[cell - 1];
                    if interior.rot_edges[lp as usize][lr as usize][1] == e[3] {
                        m += 1;
                    }
                }
                if y > 0 {
                    let (up, ur) = grid[cell - N];
                    if interior.rot_edges[up as usize][ur as usize][2] == e[0] {
                        m += 1;
                    }
                }
                if m > best.0 {
                    best = (m, pid, rot);
                }
            }
        }
        grid[cell] = (best.1, best.2);
        used[best.1 as usize] = true;
    }
    grid
}

/// load a saved interior board JSON (sparse pos on 16x16, interior cells)
/// into a local assignment vec
fn load_interior_board(path: &str, interior: &Interior) -> Vec<(u16, u8)> {
    let txt = std::fs::read_to_string(path).expect("read init board");
    let v: serde_json::Value = serde_json::from_str(&txt).expect("parse init board");
    let mut g2l = vec![u16::MAX; 256];
    for (l, &g) in interior.global_id.iter().enumerate() {
        g2l[g as usize] = l as u16;
    }
    let mut out: Vec<(u16, u8)> = vec![(u16::MAX, 0); CELLS];
    let arr = v["placement"].as_array().expect("placement array");
    for e in arr {
        let pos = e["pos"].as_u64().expect("pos") as usize;
        let (y, x) = (pos / 16, pos % 16);
        assert!((1..=N).contains(&x) && (1..=N).contains(&y), "non-interior pos {pos}");
        let cell = (y - 1) * N + (x - 1);
        let gpid = e["piece_id"].as_u64().expect("piece_id") as usize;
        let local = g2l[gpid];
        assert!(local != u16::MAX, "piece {gpid} not interior");
        let rot = e["rotation"].as_u64().expect("rotation") as u8;
        out[cell] = (local, rot);
    }
    assert!(
        out.iter().all(|&(p, _)| p != u16::MAX),
        "init board must cover all 196 interior cells"
    );
    out
}

// ------------------------------------------------------------------- main

#[allow(clippy::too_many_lines)]
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let get = |flag: &str| -> Option<String> {
        args.iter()
            .position(|a| a == flag)
            .and_then(|i| args.get(i + 1).cloned())
    };
    let has = |flag: &str| args.iter().any(|a| a == flag);
    let mode = get("--mode").unwrap_or_else(|| "sa".into());
    let seeds: u64 = get("--seeds").and_then(|s| s.parse().ok()).unwrap_or(8);
    let seed0: u64 = get("--seed0").and_then(|s| s.parse().ok()).unwrap_or(1);
    let budget_ms: u64 = get("--budget-ms").and_then(|s| s.parse().ok()).unwrap_or(60_000);
    let hinted = has("--hints");
    let t0_temp: f64 = get("--t0").and_then(|s| s.parse().ok()).unwrap_or(1.5);
    let threads: usize = get("--threads").and_then(|s| s.parse().ok()).unwrap_or(8);
    let exact_tail_k: usize = get("--exact-tail").and_then(|s| s.parse().ok()).unwrap_or(8);
    let restart_ms: u64 = get("--restart-ms").and_then(|s| s.parse().ok()).unwrap_or(5_000);
    let rim_lambda: f64 = get("--rim-lambda").and_then(|s| s.parse().ok()).unwrap_or(0.0);
    let tail2 = has("--tail2");
    // break budget: --break-schedule "154,162,170,178,186" (ascending depth
    // gates) or --breaks B (evenly spaced default gates 154..186)
    let break_schedule: Vec<usize> = get("--break-schedule").map_or_else(
        || {
            let b: usize = get("--breaks").and_then(|s| s.parse().ok()).unwrap_or(0);
            (0..b)
                .map(|j| if b == 1 { 170 } else { 154 + j * 32 / (b - 1) })
                .collect()
        },
        |s| {
            let mut v: Vec<usize> = s
                .split(',')
                .map(|x| x.trim().parse().expect("schedule depth"))
                .collect();
            v.sort_unstable();
            v
        },
    );

    rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build_global()
        .expect("rayon pool");

    let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
    let interior = extract_interior(&puzzle, &hints);
    let colors: std::collections::BTreeSet<u8> = interior
        .rot_edges
        .iter()
        .flat_map(|re| re[0].iter().copied())
        .collect();
    eprintln!(
        "interior: 196 pieces, {} colors {:?}, {} hints in interior, edge-inward supply {:?}",
        colors.len(),
        colors,
        interior.hints.len(),
        &interior.edge_inward_supply[1..]
    );

    let ts = chrono_like_ts();
    let dir = PathBuf::from(format!("output/vol-211/cloister_{mode}_{ts}"));
    std::fs::create_dir_all(&dir).expect("mkdir");
    let mut summary = std::fs::File::create(dir.join("summary.tsv")).expect("summary");

    match mode.as_str() {
        "dfs" => {
            writeln!(summary, "seed\tmax_depth\tnodes\tms_at_max\tcompletes\tbest_breaks").unwrap();
            let results: Vec<DfsResult> = (seed0..seed0 + seeds)
                .into_par_iter()
                .map(|s| {
                    dfs_run(
                        &interior, s, budget_ms, hinted, &break_schedule, exact_tail_k,
                        restart_ms, tail2,
                    )
                })
                .collect();
            let mut depths: Vec<usize> = Vec::new();
            let mut best_iis: Vec<u32> = Vec::new();
            for r in &results {
                let bb = r.complete.as_ref().map(|(_, b)| *b);
                writeln!(
                    summary,
                    "{}\t{}\t{}\t{}\t{}\t{}",
                    r.seed,
                    r.max_depth,
                    r.nodes,
                    r.ms_at_max,
                    r.completes_found,
                    bb.map_or("-".into(), |b| b.to_string()),
                )
                .unwrap();
                println!(
                    "seed {:>3}: max_depth {:>3}/196  nodes {:>12}  completes {:>6}  best II {}",
                    r.seed,
                    r.max_depth,
                    r.nodes,
                    r.completes_found,
                    bb.map_or("-".into(), |b| (II_MAX - b).to_string()),
                );
                depths.push(r.max_depth);
                if let Some((state, b)) = &r.complete {
                    let ii = II_MAX - b;
                    best_iis.push(ii);
                    let name = format!("COMPLETE_II{}_seed{}.json", ii, r.seed);
                    save_board(
                        &dir,
                        &name,
                        &interior,
                        state,
                        ii,
                        &format!(
                            "\"mode\":\"dfs\",\"seed\":{},\"hinted\":{},\"breaks\":{},",
                            r.seed, hinted, b
                        ),
                    );
                    append_history(
                        &dir,
                        "dfs",
                        r.seed,
                        ii,
                        &format!(
                            "budget_ms={budget_ms};hinted={hinted};sched={break_schedule:?};et={exact_tail_k};restart={restart_ms}"
                        ).replace(',', "|"),
                        &name,
                        &bucas_url(&interior, state),
                    );
                }
            }
            depths.sort_unstable();
            println!(
                "DFS wall ({} seeds, {}ms, hinted={}, schedule={:?}): depth min={} median={} max={}",
                seeds,
                budget_ms,
                hinted,
                break_schedule,
                depths[0],
                depths[depths.len() / 2],
                depths[depths.len() - 1]
            );
            if !best_iis.is_empty() {
                best_iis.sort_unstable();
                println!(
                    "completed interiors: {}/{} seeds, II min={} median={} max={}",
                    best_iis.len(),
                    seeds,
                    best_iis[0],
                    best_iis[best_iis.len() / 2],
                    best_iis[best_iis.len() - 1]
                );
            }
        }
        "sa" | "hybrid" => {
            let init_board: Option<Vec<(u16, u8)>> = get("--init-board")
                .map(|p| load_interior_board(&p, &interior));
            // position-exact rim targets from an attached full board
            // (alternating projections: interior SA <-> border MIP)
            let targets: Option<Vec<[Option<u8>; 2]>> =
                get("--border-board").map(|p| border_targets_from(&p, &interior));
            let dfs_ms: u64 = get("--dfs-ms")
                .and_then(|s| s.parse().ok())
                .unwrap_or_else(|| (budget_ms / 4).clamp(5_000, 60_000));
            let is_hybrid = mode == "hybrid";
            writeln!(summary, "seed\tbest_ii\tmoves").unwrap();
            let results: Vec<SaResult> = (seed0..seed0 + seeds)
                .into_par_iter()
                .map(|s| {
                    if is_hybrid {
                        let d = dfs_run(
                            &interior, s, dfs_ms, hinted, &break_schedule, exact_tail_k,
                            restart_ms, tail2,
                        );
                        let init = d.complete.map_or_else(
                            || greedy_complete(&interior, &d.best_prefix),
                            |(state, _)| state,
                        );
                        sa_run(
                            &interior,
                            s,
                            budget_ms.saturating_sub(dfs_ms),
                            hinted,
                            t0_temp,
                            Some(&init),
                            rim_lambda,
                            targets.as_deref(),
                        )
                    } else {
                        sa_run(
                            &interior,
                            s,
                            budget_ms,
                            hinted,
                            t0_temp,
                            init_board.as_deref(),
                            rim_lambda,
                            targets.as_deref(),
                        )
                    }
                })
                .collect();
            let mut iis: Vec<u32> = Vec::new();
            let mut best: Option<&SaResult> = None;
            for r in &results {
                writeln!(summary, "{}\t{}\t{}\t{}", r.seed, r.best_ii, r.best_overlap, r.moves)
                    .unwrap();
                println!(
                    "seed {:>3}: best II {:>3}/364  rim-overlap {:>2}/56  II+ov {:>3}  ({} moves)",
                    r.seed,
                    r.best_ii,
                    r.best_overlap,
                    r.best_ii + r.best_overlap,
                    r.moves
                );
                iis.push(r.best_ii);
                if best.is_none() || r.best_ii > best.unwrap().best_ii {
                    best = Some(r);
                }
            }
            iis.sort_unstable();
            println!(
                "{} ({} seeds, {}ms, hinted={}): min={} median={} max={}",
                mode,
                seeds,
                budget_ms,
                hinted,
                iis[0],
                iis[iis.len() / 2],
                iis[iis.len() - 1]
            );
            let _ = best;
            // save every seed's best (full history, small files)
            for r in &results {
                let name = format!("BEST_II{}_seed{}.json", r.best_ii, r.seed);
                save_board(
                    &dir,
                    &name,
                    &interior,
                    &r.best_state,
                    r.best_ii,
                    &format!("\"mode\":\"{}\",\"seed\":{},\"hinted\":{},", mode, r.seed, hinted),
                );
                append_history(
                    &dir,
                    &mode,
                    r.seed,
                    r.best_ii,
                    &format!(
                        "budget_ms={budget_ms};hinted={hinted};sched={break_schedule:?};et={exact_tail_k};dfs_ms={dfs_ms};t0={t0_temp}"
                    ).replace(',', "|"),
                    &name,
                    &bucas_url(&interior, &r.best_state),
                );
            }
        }
        "tail2polish" => {
            // exact re-solve of the last two rows of a COMPLETE interior
            // board; abort-bounded by its current 2-row mismatch count
            let path = get("--init-board").expect("tail2polish needs --init-board");
            let init = load_interior_board(&path, &interior);
            let start = CELLS - 2 * N;
            let cur_breaks = count_breaks(&interior, &init);
            // mismatches attributable to the tail region (edges counted at
            // their later-in-scan endpoint from cell `start` on)
            let mut tail_mis = 0u32;
            for cell in start..CELLS {
                let (pid, rot) = init[cell];
                let e = interior.rot_edges[pid as usize][rot as usize];
                if cell % N > 0 {
                    let (lp, lr) = init[cell - 1];
                    if interior.rot_edges[lp as usize][lr as usize][1] != e[3] {
                        tail_mis += 1;
                    }
                }
                let (up, ur) = init[cell - N];
                if interior.rot_edges[up as usize][ur as usize][2] != e[0] {
                    tail_mis += 1;
                }
            }
            let pieces: Vec<u16> = init[start..].iter().map(|&(p, _)| p).collect();
            let mut forced_tail: Vec<Option<(u16, u8)>> = vec![None; 2 * N];
            if hinted {
                for &(cell, pid, rot) in &interior.hints {
                    if cell >= start {
                        forced_tail[cell - start] = Some((pid as u16, rot));
                    }
                }
            }
            println!(
                "tail2polish {path}: II={} (tail mismatches {tail_mis})",
                II_MAX - cur_breaks
            );
            let cap: u64 = get("--cap").and_then(|s| s.parse().ok()).unwrap_or(2_000_000_000);
            let t0 = Instant::now();
            let (mis, asn) =
                exact_tail2(&interior, &init, start, &pieces, &forced_tail, tail_mis, cap);
            println!(
                "tail2 exact: {} -> {} ({}s)",
                tail_mis,
                mis,
                t0.elapsed().as_secs()
            );
            if mis < tail_mis {
                let mut full = init.clone();
                for (j, &pr) in asn.iter().enumerate() {
                    full[start + j] = pr;
                }
                let new_ii = II_MAX - count_breaks(&interior, &full);
                let name = format!("POLISHED_II{new_ii}.json");
                save_board(
                    &dir,
                    &name,
                    &interior,
                    &full,
                    new_ii,
                    &format!("\"mode\":\"tail2polish\",\"src\":\"{path}\",\"hinted\":{hinted},"),
                );
                append_history(
                    &dir, "tail2polish", 0, new_ii,
                    &format!("src={path};cap={cap}").replace(',', "|"),
                    &name,
                    &bucas_url(&interior, &full),
                );
            } else {
                println!("no improvement (2-row arrangement already optimal at this cap)");
            }
        }
        m => {
            eprintln!("unknown mode {m}");
            std::process::exit(2);
        }
    }
}

fn chrono_like_ts() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_secs();
    // UTC date arithmetic, good enough for a unique run tag
    let days = secs / 86_400;
    let (mut y, mut rem) = (1970u64, days);
    loop {
        let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
        let len = if leap { 366 } else { 365 };
        if rem < len {
            break;
        }
        rem -= len;
        y += 1;
    }
    let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    let ml = [31, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let mut m = 0;
    while rem >= ml[m] {
        rem -= ml[m];
        m += 1;
    }
    let tod = secs % 86_400;
    format!(
        "{:04}{:02}{:02}T{:02}{:02}{:02}",
        y,
        m + 1,
        rem + 1,
        tod / 3600,
        (tod % 3600) / 60,
        tod % 60
    )
}
