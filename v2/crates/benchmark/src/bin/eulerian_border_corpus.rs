// eulerian_border_corpus — anr_56's Eulerian-cycle border-feasibility
// test, calibrated on the 100k feasible-border corpus (output/borders/
// sample_100k.jsonl) sampled by `border_enumerate` in vol-6.
//
// What we test:
//   (a) Sanity. All 100k corpus rings are *known feasible* (corpus was
//       built by side-by-side backtracking respecting color matching);
//       `eulerian_ring_check_full` must return TRUE on every one.
//   (b) Synthetic violations — chain-perturbation. For each ring,
//       swap two random tiles (preserving piece set but breaking
//       adjacency). Report what fraction the Euler-full check rejects.
//   (c) Synthetic violations — random-subset borders. Sample a random
//       set of 60 border tiles from the piece set; assemble them as a
//       hypothetical ring (in the corpus's TL/top/TR/right/... order).
//       Report Euler-full pass rate. (This estimates the "raw fail rate"
//       of arbitrary border-tile subsets — anr_56's prediction was 0.78
//       at P=15 / 0.70 at P=16 for *random borders with even L-R*. Our
//       sample is from a different distribution; we don't directly
//       reproduce his number but we measure ours.)
//   (d) Pool-OR check on the 60 real border pieces of E2. With NO ring
//       assigned, just the OR-graph: is it always connected? (Expected
//       yes — E2's border palette is small and dense.)

#![forbid(unsafe_code)]

use std::fs::{create_dir_all, File};
use std::io::{BufRead, BufReader, BufWriter, Write};
use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Piece, PieceId, Puzzle};
use eternity2_propagators::border_eulerian::{
    corner_tile_ring_edge, edge_tile_ring_edge, eulerian_pool_or_check, CornerKind, RingEdge,
    RingSide,
};

#[derive(Parser, Debug)]
#[command(
    name = "eulerian_border_corpus",
    about = "anr_56 Eulerian-cycle calibration on the 100k border corpus"
)]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long, default_value = "output/borders/sample_100k.jsonl")]
    corpus: PathBuf,

    #[arg(long, default_value = "output/v9_eulerian/calibration.json")]
    out: PathBuf,

    /// Number of random-subset trials in test (c).
    #[arg(long, default_value_t = 100_000u64)]
    n_random_subset: u64,

    /// Number of swap-perturbation trials per ring in test (b).
    #[arg(long, default_value_t = 1u64)]
    n_swap_per_ring: u64,

    /// RNG seed.
    #[arg(long, default_value_t = 0xDEC0DE_DAD_C0DEu64)]
    seed: u64,

    /// Limit to first N rings from corpus (0 = all).
    #[arg(long, default_value_t = 0u64)]
    limit: u64,
}

struct SimpleRng { state: u64 }
impl SimpleRng {
    fn new(seed: u64) -> Self { Self { state: if seed == 0 { 0xDEADBEEFCAFEBABE } else { seed } } }
    fn next_u64(&mut self) -> u64 {
        let mut x = self.state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.state = x;
        x.wrapping_mul(0x2545F4914F6CDD1D)
    }
}

// 16x16: perimeter = 60. side_len = 14.
const SIDE_LEN: usize = 14;
const TL: usize = 0;
const TR: usize = 1 + SIDE_LEN;          // 15
const BR: usize = 2 + 2 * SIDE_LEN;       // 30
const BL: usize = 3 + 3 * SIDE_LEN;       // 45
const PERIMETER: usize = 60;

/// Map ring-index → side/corner kind.
fn kind_at(idx: usize) -> Result<(Option<RingSide>, Option<CornerKind>), String> {
    match idx {
        TL => Ok((None, Some(CornerKind::TL))),
        TR => Ok((None, Some(CornerKind::TR))),
        BR => Ok((None, Some(CornerKind::BR))),
        BL => Ok((None, Some(CornerKind::BL))),
        i if i > TL && i < TR => Ok((Some(RingSide::Top), None)),
        i if i > TR && i < BR => Ok((Some(RingSide::Right), None)),
        i if i > BR && i < BL => Ok((Some(RingSide::Bottom), None)),
        i if i > BL && i < PERIMETER => Ok((Some(RingSide::Left), None)),
        _ => Err(format!("invalid ring index {idx}")),
    }
}

fn lookup_piece(puzzle: &Puzzle, pid: PieceId) -> Option<&Piece> {
    puzzle.piece(pid)
}

fn ring_edge_at(puzzle: &Puzzle, idx: usize, pid: PieceId) -> Result<RingEdge, String> {
    let piece = lookup_piece(puzzle, pid).ok_or_else(|| format!("piece {pid} not found"))?;
    let (side, corner) = kind_at(idx)?;
    match (side, corner) {
        (Some(s), None) => edge_tile_ring_edge(piece, s)
            .ok_or_else(|| format!("edge piece {pid} cannot place on {s:?}")),
        (None, Some(k)) => corner_tile_ring_edge(piece, k)
            .ok_or_else(|| format!("corner piece {pid} cannot place at {k:?}")),
        _ => Err(format!("ambiguous ring index {idx}")),
    }
}

/// Recompute RingEdges for an entire 60-tile (pid, _rot) sequence using
/// the *side-derived* rotation (not the stored rotation, which we treat
/// as advisory and re-derive for trust). The stored rotation is checked
/// against ours for sanity.
fn decode_ring(puzzle: &Puzzle, raw: &[(PieceId, u8)]) -> Result<(Vec<RingEdge>, usize), String> {
    if raw.len() != PERIMETER { return Err(format!("expected 60 tiles, got {}", raw.len())); }
    let mut out = Vec::with_capacity(PERIMETER);
    let mut rot_mismatches = 0usize;
    for (idx, &(pid, stored_rot)) in raw.iter().enumerate() {
        let re = ring_edge_at(puzzle, idx, pid)?;
        if re.rotation != stored_rot { rot_mismatches += 1; }
        out.push(re);
    }
    Ok((out, rot_mismatches))
}

#[derive(Debug, Default)]
struct Stats {
    n: u64,
    pass: u64,
    fail_chain: u64,
    fail_degree: u64,
    fail_connect: u64,
}

impl Stats {
    fn add(&mut self, result: RingClass) {
        self.n += 1;
        match result {
            RingClass::Pass => self.pass += 1,
            RingClass::FailChain => self.fail_chain += 1,
            RingClass::FailDegree => self.fail_degree += 1,
            RingClass::FailConnect => self.fail_connect += 1,
        }
    }
    fn rate(&self, num: u64) -> f64 {
        if self.n == 0 { 0.0 } else { num as f64 / self.n as f64 }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RingClass {
    Pass,
    FailChain,
    FailDegree,
    FailConnect,
}

/// Diagnostic version: classify *why* an Euler-full check would have
/// failed. Mirrors the staged checks inside the propagator so we can
/// report which stage actually rejects.
fn classify_ring(ring: &[RingEdge]) -> RingClass {
    // chain consistency
    let n = ring.len();
    if n == 0 { return RingClass::FailChain; }
    for i in 0..n {
        let cur = &ring[i];
        let prev = &ring[(i + n - 1) % n];
        if cur.prev_color != prev.next_color { return RingClass::FailChain; }
    }
    // degree balance
    let max_color = ring
        .iter()
        .flat_map(|e| [e.prev_color, e.next_color])
        .max()
        .unwrap_or(0) as usize;
    let n_v = max_color + 1;
    let mut indeg = vec![0i32; n_v];
    let mut outdeg = vec![0i32; n_v];
    for e in ring {
        outdeg[e.prev_color as usize] += 1;
        indeg[e.next_color as usize] += 1;
    }
    for v in 0..n_v {
        if indeg[v] != outdeg[v] { return RingClass::FailDegree; }
    }
    // connectivity
    let raw: Vec<(usize, usize)> = ring
        .iter()
        .map(|e| (e.prev_color as usize, e.next_color as usize))
        .collect();
    let mut parent: Vec<usize> = (0..n_v).collect();
    fn find(parent: &mut [usize], mut x: usize) -> usize {
        while parent[x] != x { parent[x] = parent[parent[x]]; x = parent[x]; }
        x
    }
    let mut has_edge = vec![false; n_v];
    for &(u, v) in &raw {
        has_edge[u] = true;
        has_edge[v] = true;
        let (ru, rv) = (find(&mut parent, u), find(&mut parent, v));
        if ru != rv { parent[ru] = rv; }
    }
    let root = (0..n_v).find(|&v| has_edge[v]).map(|v| find(&mut parent, v));
    let connected = match root {
        None => true,
        Some(r) => (0..n_v).all(|v| !has_edge[v] || find(&mut parent, v) == r),
    };
    if connected { RingClass::Pass } else { RingClass::FailConnect }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).map_err(|e| format!("{e}"))?;
    eprintln!("puzzle: {}x{}, {} pieces", puzzle.width, puzzle.height, puzzle.pieces().len());

    // Read corpus.
    let reader = BufReader::new(File::open(&args.corpus)?);
    let mut all_rings: Vec<Vec<(PieceId, u8)>> = Vec::new();
    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() { continue; }
        #[derive(serde::Deserialize)]
        struct Row { border: Vec<[i64; 2]> }
        let row: Row = serde_json::from_str(&line)?;
        let parsed: Vec<(PieceId, u8)> = row
            .border
            .into_iter()
            .map(|[p, r]| (p as PieceId, r as u8))
            .collect();
        all_rings.push(parsed);
        if args.limit > 0 && all_rings.len() as u64 >= args.limit { break; }
    }
    eprintln!("corpus: {} rings loaded", all_rings.len());

    // (a) Sanity — every real ring must pass.
    let t0 = Instant::now();
    let mut sanity = Stats::default();
    let mut total_rot_mismatch = 0usize;
    for raw in &all_rings {
        let (ring, mm) = decode_ring(&puzzle, raw)?;
        total_rot_mismatch += mm;
        sanity.add(classify_ring(&ring));
    }
    let t_sanity = t0.elapsed();
    eprintln!(
        "(a) SANITY: {}/{} pass, fail_chain={} fail_deg={} fail_conn={}, rot_mismatch={}, {:.1} ms",
        sanity.pass, sanity.n, sanity.fail_chain, sanity.fail_degree, sanity.fail_connect,
        total_rot_mismatch, t_sanity.as_secs_f64() * 1000.0
    );
    let ns_per_ring = t_sanity.as_nanos() as f64 / sanity.n as f64;
    eprintln!("    avg per-ring cost: {:.0} ns", ns_per_ring);
    // sanity.fail_chain expected 0; rot_mismatch is a CSV/loader format
    // detail (the corpus's stored rotation may use a different convention).

    // (b) Two-tile swap perturbation. We pick two random distinct
    // edge-tile positions in the ring, swap their (pid) entries — and
    // since each tile rotates to fit ITS NEW side, the (prev,next) for
    // each tile is recomputed from the new side. Report fraction caught.
    let mut rng = SimpleRng::new(args.seed);
    let mut swap_stats = Stats::default();
    let t1 = Instant::now();
    for raw in &all_rings {
        for _ in 0..args.n_swap_per_ring {
            let mut perturbed = raw.clone();
            // Pick two distinct edge-side positions (avoiding corners 0,15,30,45).
            let edge_positions: Vec<usize> = (0..PERIMETER).filter(|&i| !matches!(i, TL | TR | BR | BL)).collect();
            let i_a = (rng.next_u64() as usize) % edge_positions.len();
            let mut i_b = (rng.next_u64() as usize) % edge_positions.len();
            while i_b == i_a { i_b = (rng.next_u64() as usize) % edge_positions.len(); }
            let pos_a = edge_positions[i_a];
            let pos_b = edge_positions[i_b];
            // Skip if same side (swap would be a no-op for connectivity).
            let (side_a, _) = kind_at(pos_a)?;
            let (side_b, _) = kind_at(pos_b)?;
            if side_a == side_b { continue; }
            // Swap piece ids (rotations re-derived).
            let pid_a = perturbed[pos_a].0;
            let pid_b = perturbed[pos_b].0;
            perturbed[pos_a].0 = pid_b;
            perturbed[pos_b].0 = pid_a;
            // Re-derive rotations (rotation field unused by classifier).
            let result = decode_ring(&puzzle, &perturbed);
            let class = match result {
                Ok((ring, _)) => classify_ring(&ring),
                Err(_) => RingClass::FailChain, // can't even place: counts as a catch (chain stage).
            };
            swap_stats.add(class);
        }
    }
    let t_swap = t1.elapsed();
    eprintln!(
        "(b) SWAP-PERTURB: {} trials, pass={} ({:.2}%) chain={} ({:.2}%) deg={} ({:.2}%) conn={} ({:.2}%), {:.1} s",
        swap_stats.n, swap_stats.pass, swap_stats.rate(swap_stats.pass) * 100.0,
        swap_stats.fail_chain, swap_stats.rate(swap_stats.fail_chain) * 100.0,
        swap_stats.fail_degree, swap_stats.rate(swap_stats.fail_degree) * 100.0,
        swap_stats.fail_connect, swap_stats.rate(swap_stats.fail_connect) * 100.0,
        t_swap.as_secs_f64()
    );

    // (c) Random-subset borders. Sample 60 border pieces uniformly
    // (with replacement is wrong — sample WITHOUT replacement from the
    // border piece set). Slot them in ring order (4 corners + 4×14 edges).
    // Re-derive (prev,next) per side and run classify_ring.
    let border_pieces: Vec<&Piece> = puzzle
        .pieces()
        .iter()
        .filter(|p| p.is_corner() || p.is_edge())
        .collect();
    let corner_pieces: Vec<&Piece> = border_pieces.iter().filter(|p| p.is_corner()).copied().collect();
    let edge_pieces: Vec<&Piece> = border_pieces.iter().filter(|p| p.is_edge()).copied().collect();
    eprintln!(
        "border piece supply: {} corners, {} edges (total {})",
        corner_pieces.len(),
        edge_pieces.len(),
        border_pieces.len()
    );
    let mut subset_stats = Stats::default();
    let t2 = Instant::now();
    let mut n_corner_short = 0u64; // sampled corner-set was wrong cardinality
    for _ in 0..args.n_random_subset {
        // Pick 4 distinct corners and assign to TL/TR/BR/BL (any
        // assignment is fine; we draw a permutation).
        if corner_pieces.len() < 4 { n_corner_short += 1; continue; }
        let mut corner_idx: Vec<usize> = (0..corner_pieces.len()).collect();
        // Shuffle and take first 4.
        for i in (1..corner_idx.len()).rev() {
            let j = (rng.next_u64() as usize) % (i + 1);
            corner_idx.swap(i, j);
        }
        let four_corners = [
            corner_pieces[corner_idx[0]],
            corner_pieces[corner_idx[1]],
            corner_pieces[corner_idx[2]],
            corner_pieces[corner_idx[3]],
        ];
        // Pick 56 distinct edges.
        if edge_pieces.len() < 4 * SIDE_LEN {
            n_corner_short += 1;
            continue;
        }
        let mut edge_idx: Vec<usize> = (0..edge_pieces.len()).collect();
        for i in (1..edge_idx.len()).rev() {
            let j = (rng.next_u64() as usize) % (i + 1);
            edge_idx.swap(i, j);
        }
        let chosen_edges: Vec<&Piece> = edge_idx
            .iter()
            .take(4 * SIDE_LEN)
            .map(|&i| edge_pieces[i])
            .collect();

        // Build the ring: index 0 = corner 0 at TL, 1..15 = first 14 edges on top, etc.
        let mut raw: Vec<(PieceId, u8)> = Vec::with_capacity(PERIMETER);
        let assign_corner = |k: usize| -> (PieceId, u8) {
            // rotation will be re-derived
            (four_corners[k].id, 0)
        };
        raw.push(assign_corner(0));
        for i in 0..SIDE_LEN { raw.push((chosen_edges[i].id, 0)); }
        raw.push(assign_corner(1));
        for i in 0..SIDE_LEN { raw.push((chosen_edges[SIDE_LEN + i].id, 0)); }
        raw.push(assign_corner(2));
        for i in 0..SIDE_LEN { raw.push((chosen_edges[2 * SIDE_LEN + i].id, 0)); }
        raw.push(assign_corner(3));
        for i in 0..SIDE_LEN { raw.push((chosen_edges[3 * SIDE_LEN + i].id, 0)); }
        let class = match decode_ring(&puzzle, &raw) {
            Ok((ring, _)) => classify_ring(&ring),
            Err(_) => RingClass::FailChain,
        };
        subset_stats.add(class);
    }
    let t_subset = t2.elapsed();
    eprintln!(
        "(c) RANDOM-SUBSET: {} trials, pass={} ({:.2}%) chain={} ({:.2}%) deg={} ({:.2}%) conn={} ({:.2}%), corner_short={}, {:.1} s",
        subset_stats.n, subset_stats.pass, subset_stats.rate(subset_stats.pass) * 100.0,
        subset_stats.fail_chain, subset_stats.rate(subset_stats.fail_chain) * 100.0,
        subset_stats.fail_degree, subset_stats.rate(subset_stats.fail_degree) * 100.0,
        subset_stats.fail_connect, subset_stats.rate(subset_stats.fail_connect) * 100.0,
        n_corner_short, t_subset.as_secs_f64()
    );

    // (d) Pool-OR check on the full E2 border piece set with no
    // assignment. Sanity test: should be connected.
    let all_border_pids: Vec<PieceId> = border_pieces.iter().map(|p| p.id).collect();
    let pool_or_ok = eulerian_pool_or_check(&puzzle, &all_border_pids);
    eprintln!("(d) POOL-OR on full border set: connected={}", pool_or_ok);

    // (e) anr_56 analog. For each trial: draw 14 distinct edge pieces
    // for each of top/right/bottom/left (56 total without replacement)
    // and 4 distinct corners assigned TL/TR/BR/BL. This *fixes the side*
    // of every tile, so each tile's (prev,next) is now determined. Build
    // the multigraph and test (degree balance) AND (connectivity).
    // Report:
    //   - fraction with degree balance,
    //   - fraction with degree balance AND connectivity (the conjunction
    //     is anr_56's "tileable closed-ring" predictor).
    let mut e_n = 0u64;
    let mut e_degree_ok = 0u64;
    let mut e_full_ok = 0u64;
    let mut e_connect_given_degree = 0u64;
    let t3 = Instant::now();
    let max_e_trials = args.n_random_subset;
    let edge_supply = edge_pieces.len();
    let corner_supply = corner_pieces.len();
    if edge_supply < 4 * SIDE_LEN || corner_supply < 4 {
        eprintln!("(e) skipped: insufficient supply ({} corners, {} edges)", corner_supply, edge_supply);
    } else {
        for _ in 0..max_e_trials {
            let mut corner_idx: Vec<usize> = (0..corner_supply).collect();
            for i in (1..corner_idx.len()).rev() {
                let j = (rng.next_u64() as usize) % (i + 1);
                corner_idx.swap(i, j);
            }
            let four = [
                corner_pieces[corner_idx[0]],
                corner_pieces[corner_idx[1]],
                corner_pieces[corner_idx[2]],
                corner_pieces[corner_idx[3]],
            ];
            let mut edge_idx: Vec<usize> = (0..edge_supply).collect();
            for i in (1..edge_idx.len()).rev() {
                let j = (rng.next_u64() as usize) % (i + 1);
                edge_idx.swap(i, j);
            }

            // Build the side-pinned (prev,next) edges for the multigraph.
            let mut ring_edges: Vec<RingEdge> = Vec::with_capacity(PERIMETER);
            ring_edges.push(corner_tile_ring_edge(four[0], CornerKind::TL).unwrap());
            for k in 0..SIDE_LEN {
                ring_edges.push(edge_tile_ring_edge(edge_pieces[edge_idx[k]], RingSide::Top).unwrap());
            }
            ring_edges.push(corner_tile_ring_edge(four[1], CornerKind::TR).unwrap());
            for k in 0..SIDE_LEN {
                ring_edges.push(edge_tile_ring_edge(edge_pieces[edge_idx[SIDE_LEN + k]], RingSide::Right).unwrap());
            }
            ring_edges.push(corner_tile_ring_edge(four[2], CornerKind::BR).unwrap());
            for k in 0..SIDE_LEN {
                ring_edges.push(edge_tile_ring_edge(edge_pieces[edge_idx[2 * SIDE_LEN + k]], RingSide::Bottom).unwrap());
            }
            ring_edges.push(corner_tile_ring_edge(four[3], CornerKind::BL).unwrap());
            for k in 0..SIDE_LEN {
                ring_edges.push(edge_tile_ring_edge(edge_pieces[edge_idx[3 * SIDE_LEN + k]], RingSide::Left).unwrap());
            }
            // Degree balance + connectivity (skip the chain-consistency
            // requirement — random-subset borders almost never chain).
            let max_color = ring_edges.iter().flat_map(|e| [e.prev_color, e.next_color]).max().unwrap_or(0) as usize;
            let n_v = max_color + 1;
            let mut indeg = vec![0i32; n_v];
            let mut outdeg = vec![0i32; n_v];
            for e in &ring_edges {
                outdeg[e.prev_color as usize] += 1;
                indeg[e.next_color as usize] += 1;
            }
            let degree_ok = (0..n_v).all(|v| indeg[v] == outdeg[v]);
            // connectivity
            let raw: Vec<(usize, usize)> = ring_edges.iter().map(|e| (e.prev_color as usize, e.next_color as usize)).collect();
            let mut parent: Vec<usize> = (0..n_v).collect();
            fn find(parent: &mut [usize], mut x: usize) -> usize {
                while parent[x] != x { parent[x] = parent[parent[x]]; x = parent[x]; }
                x
            }
            let mut has_edge = vec![false; n_v];
            for &(u, v) in &raw {
                has_edge[u] = true; has_edge[v] = true;
                let (ru, rv) = (find(&mut parent, u), find(&mut parent, v));
                if ru != rv { parent[ru] = rv; }
            }
            let root = (0..n_v).find(|&v| has_edge[v]).map(|v| find(&mut parent, v));
            let connected = match root {
                None => true,
                Some(r) => (0..n_v).all(|v| !has_edge[v] || find(&mut parent, v) == r),
            };
            e_n += 1;
            if degree_ok { e_degree_ok += 1; }
            if degree_ok && connected { e_full_ok += 1; }
            if degree_ok && connected { e_connect_given_degree += 1; }
        }
        let t_e = t3.elapsed();
        let p_deg = if e_n > 0 { e_degree_ok as f64 / e_n as f64 } else { 0.0 };
        let p_full = if e_n > 0 { e_full_ok as f64 / e_n as f64 } else { 0.0 };
        let p_conn_g_deg = if e_degree_ok > 0 { e_connect_given_degree as f64 / e_degree_ok as f64 } else { 0.0 };
        eprintln!(
            "(e) anr_56 ANALOG: {} trials, P(deg-balance)={:.4}, P(deg AND connect)={:.4}, P(connect | deg)={:.4}, {:.2} s",
            e_n, p_deg, p_full, p_conn_g_deg, t_e.as_secs_f64()
        );
    }

    // (f) Mid-search "alternative-completion" pruning. For each ring in
    // the corpus, fix a prefix of length K (drawn from the ring) and
    // consider an *alternative* completion: random side-respecting
    // assignment of the remaining 60-K tile slots, drawn from the
    // border-piece supply minus the prefix's used pieces. Measure how
    // often the alternative-completion multigraph fails (deg or conn).
    //
    // Pruning power = fraction REJECTED. If 0 → propagator never fires
    // at this depth; if >0 → propagator can prune at this depth.
    let mut f_results: Vec<(usize, u64, u64, u64)> = Vec::new(); // (K, n, n_deg_fail, n_conn_fail_given_deg_ok)
    for &k_prefix in &[10usize, 20, 30, 45, 55] {
        let mut n = 0u64;
        let mut n_deg_fail = 0u64;
        let mut n_conn_fail = 0u64;
        let trials_per_ring = 1u64;
        for raw in &all_rings {
            for _ in 0..trials_per_ring {
                // Decode the prefix.
                if k_prefix >= PERIMETER { continue; }
                let (full_ring, _) = decode_ring(&puzzle, raw)?;
                let prefix = &full_ring[..k_prefix];
                // Used set = prefix piece ids
                let used_pids: std::collections::HashSet<PieceId> =
                    prefix.iter().map(|e| e.piece_id).collect();
                // Determine per-suffix-position side requirements.
                let mut suffix_edges_by_side: [Vec<usize>; 4] = [Vec::new(), Vec::new(), Vec::new(), Vec::new()];
                let mut suffix_corners: Vec<CornerKind> = Vec::new();
                for idx in k_prefix..PERIMETER {
                    match kind_at(idx)? {
                        (Some(s), _) => {
                            let bin = match s {
                                RingSide::Top => 0, RingSide::Right => 1, RingSide::Bottom => 2, RingSide::Left => 3,
                            };
                            suffix_edges_by_side[bin].push(idx);
                        }
                        (_, Some(c)) => suffix_corners.push(c),
                        _ => {}
                    }
                }
                // Available pool by class.
                let avail_corners: Vec<&Piece> = corner_pieces
                    .iter()
                    .copied()
                    .filter(|p| !used_pids.contains(&p.id))
                    .collect();
                let avail_edges: Vec<&Piece> = edge_pieces
                    .iter()
                    .copied()
                    .filter(|p| !used_pids.contains(&p.id))
                    .collect();
                let need_corners = suffix_corners.len();
                let need_edges: usize = suffix_edges_by_side.iter().map(|v| v.len()).sum();
                if avail_corners.len() < need_corners || avail_edges.len() < need_edges { continue; }
                // Shuffle.
                let mut ci: Vec<usize> = (0..avail_corners.len()).collect();
                for i in (1..ci.len()).rev() {
                    let j = (rng.next_u64() as usize) % (i + 1);
                    ci.swap(i, j);
                }
                let mut ei: Vec<usize> = (0..avail_edges.len()).collect();
                for i in (1..ei.len()).rev() {
                    let j = (rng.next_u64() as usize) % (i + 1);
                    ei.swap(i, j);
                }
                // Build the full ring (prefix REAL + suffix RANDOM):
                // consume the shuffled avail_edges/avail_corners pools
                // sequentially as we walk suffix positions; each suffix
                // edge slot consumes one shuffled piece whose (prev,next)
                // is determined by that slot's side.
                let mut combined: Vec<RingEdge> = Vec::with_capacity(PERIMETER);
                combined.extend_from_slice(prefix);
                let mut taken = 0usize;
                let mut taken_corner = 0usize;
                for idx in k_prefix..PERIMETER {
                    match kind_at(idx)? {
                        (Some(s), _) => {
                            let piece = avail_edges[ei[taken]];
                            taken += 1;
                            let re = edge_tile_ring_edge(piece, s);
                            match re {
                                Some(r) => combined.push(r),
                                None => { combined.push(RingEdge { piece_id: piece.id, rotation: 0, prev_color: 255, next_color: 255 }); }
                            }
                        }
                        (_, Some(c)) => {
                            let piece = avail_corners[ci[taken_corner]];
                            taken_corner += 1;
                            let re = corner_tile_ring_edge(piece, c);
                            match re {
                                Some(r) => combined.push(r),
                                None => { combined.push(RingEdge { piece_id: piece.id, rotation: 0, prev_color: 255, next_color: 255 }); }
                            }
                        }
                        _ => {}
                    }
                }
                // Test degree balance + connectivity (skip chain).
                let max_color = combined.iter().flat_map(|e| [e.prev_color, e.next_color]).max().unwrap_or(0) as usize;
                let n_v = max_color + 1;
                let mut indeg = vec![0i32; n_v];
                let mut outdeg = vec![0i32; n_v];
                for e in &combined {
                    outdeg[e.prev_color as usize] += 1;
                    indeg[e.next_color as usize] += 1;
                }
                let degree_ok = (0..n_v).all(|v| indeg[v] == outdeg[v]);
                let conn_ok = if degree_ok {
                    let raw: Vec<(usize, usize)> = combined.iter().map(|e| (e.prev_color as usize, e.next_color as usize)).collect();
                    let mut parent: Vec<usize> = (0..n_v).collect();
                    fn find(parent: &mut [usize], mut x: usize) -> usize {
                        while parent[x] != x { parent[x] = parent[parent[x]]; x = parent[x]; }
                        x
                    }
                    let mut has_edge = vec![false; n_v];
                    for &(u, v) in &raw {
                        has_edge[u] = true; has_edge[v] = true;
                        let (ru, rv) = (find(&mut parent, u), find(&mut parent, v));
                        if ru != rv { parent[ru] = rv; }
                    }
                    let root = (0..n_v).find(|&v| has_edge[v]).map(|v| find(&mut parent, v));
                    match root {
                        None => true,
                        Some(r) => (0..n_v).all(|v| !has_edge[v] || find(&mut parent, v) == r),
                    }
                } else { false };
                n += 1;
                if !degree_ok { n_deg_fail += 1; }
                if degree_ok && !conn_ok { n_conn_fail += 1; }
            }
        }
        f_results.push((k_prefix, n, n_deg_fail, n_conn_fail));
    }
    eprintln!("(f) MID-SEARCH alternative-completion pruning:");
    for &(k, n, ndf, ncf) in &f_results {
        let p_deg = if n > 0 { ndf as f64 / n as f64 } else { 0.0 };
        let p_conn = if n > 0 { ncf as f64 / n as f64 } else { 0.0 };
        let total_rej = ndf + ncf;
        let p_rej = if n > 0 { total_rej as f64 / n as f64 } else { 0.0 };
        eprintln!(
            "    K={}: n={}, deg_fail={} ({:.4}), conn_fail_given_deg_ok={} ({:.4}), total_rejection={:.4}",
            k, n, ndf, p_deg, ncf, p_conn, p_rej
        );
    }

    // Emit JSON summary.
    if let Some(p) = args.out.parent() { create_dir_all(p)?; }
    let mut writer = BufWriter::new(File::create(&args.out)?);
    let summary = serde_json::json!({
        "corpus": args.corpus.display().to_string(),
        "n_rings": all_rings.len(),
        "n_random_subset": args.n_random_subset,
        "rot_mismatch": total_rot_mismatch,
        "sanity": {
            "n": sanity.n, "pass": sanity.pass,
            "fail_chain": sanity.fail_chain,
            "fail_degree": sanity.fail_degree,
            "fail_connect": sanity.fail_connect,
            "ns_per_ring": ns_per_ring,
        },
        "swap": {
            "n": swap_stats.n, "pass": swap_stats.pass,
            "fail_chain": swap_stats.fail_chain,
            "fail_degree": swap_stats.fail_degree,
            "fail_connect": swap_stats.fail_connect,
        },
        "random_subset": {
            "n": subset_stats.n, "pass": subset_stats.pass,
            "fail_chain": subset_stats.fail_chain,
            "fail_degree": subset_stats.fail_degree,
            "fail_connect": subset_stats.fail_connect,
            "n_corner_short": n_corner_short,
        },
        "pool_or_full_border_connected": pool_or_ok,
        "anr56_analog": {
            "n": e_n,
            "degree_ok": e_degree_ok,
            "degree_and_connected_ok": e_full_ok,
        },
        "mid_search_pruning": f_results.iter().map(|(k, n, df, cf)| serde_json::json!({
            "K": k, "n": n, "deg_fail": df, "conn_fail_given_deg_ok": cf,
        })).collect::<Vec<_>>(),
    });
    serde_json::to_writer_pretty(&mut writer, &summary)?;
    writeln!(writer)?;
    drop(writer);
    eprintln!("wrote {}", args.out.display());

    Ok(())
}
