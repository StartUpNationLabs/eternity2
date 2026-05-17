// Vol-122 J6 — Frontier-State Memoized CSP (FSMC) for E2.
//
// Per the Python PoC (scripts/vol122_fsmc_poc.py), CSP backtracking
// paths often converge on equivalent states (same placed-piece set,
// same frontier color signature). This Rust port:
//
// 1. Implements row-major CSP backtracking.
// 2. At every node, computes a Zobrist-style state hash from
//    (placed_pieces_bitset, frontier_color_signature).
// 3. Caches "subtree-exhausted" per state.
// 4. On re-visit, skips subtree if cached.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Puzzle, Rotation};

#[derive(Clone, Copy, Debug)]
struct PlacedCell {
    edges: [u8; 4],
}

struct Zobrist {
    piece_hash: Vec<u64>,
    frontier_hash: Vec<u64>,
}

impl Zobrist {
    fn new(n_pieces: usize, n_cells: usize, max_color: u8) -> Self {
        let mut state: u64 = 0xC3A5_C85C_97CB_3127;
        let mut next = || -> u64 {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            state
        };
        let piece_hash: Vec<u64> = (0..n_pieces).map(|_| next()).collect();
        let frontier_hash: Vec<u64> = (0..(n_cells * 4 * (max_color as usize + 1)))
            .map(|_| next())
            .collect();
        Self { piece_hash, frontier_hash }
    }

    fn frontier_idx(&self, pos: usize, side: usize, color: u8, max_color: u8) -> usize {
        pos * 4 * (max_color as usize + 1) + side * (max_color as usize + 1) + color as usize
    }
}

struct Stats {
    nodes: u64,
    cache_hits: u64,
    cache_misses: u64,
    best_depth: usize,
    nodes_saved_estimate: u64,
    cfcc_prunes: u64,
}

struct Searcher {
    side: usize,
    n_cells: usize,
    n_pieces: usize,
    max_color: u8,
    pieces_rot: Vec<[[u8; 4]; 4]>,
    /// piece_color_counts[pid][color] = # edges of color on piece pid (rotation-invariant)
    piece_color_counts: Vec<Vec<u16>>,
    pos_order: Vec<usize>,
    board: Vec<Option<PlacedCell>>,
    used_pids: Vec<bool>,
    zob: Zobrist,
    cache: HashMap<u64, u32>,
    use_memo: bool,
    /// If > 0, only hash the most-recently-placed K cells' frontier (partial state).
    partial_frontier_k: usize,
    /// If true, don't include piece-bitset in hash.
    frontier_only: bool,
    /// PIH: use remaining-color-supply multiset instead of piece-bitset.
    color_supply_key: bool,
    /// K3 CFCC: enable color-flow-capacity propagator.
    use_cfcc: bool,
    /// Live remaining color supply (incremental).
    color_supply: Vec<u16>,
    /// Live frontier color demand (incremental).
    color_demand: Vec<u16>,
    stats: Stats,
    max_nodes: u64,
    time_limit: std::time::Duration,
    t_start: Instant,
}

impl Searcher {
    fn new(puzzle: Puzzle, max_nodes: u64, time_secs: f64, use_memo: bool, partial_frontier_k: usize, frontier_only: bool, color_supply_key: bool, use_cfcc: bool) -> Self {
        let side = puzzle.width as usize;
        let n_cells = side * side;
        let n_pieces = puzzle.pieces().len();
        let max_color = puzzle.color_count as u8;
        let mut pieces_rot = vec![[[0u8; 4]; 4]; n_pieces];
        let n_colors = max_color as usize + 1;
        let mut piece_color_counts = vec![vec![0u16; n_colors]; n_pieces];
        let mut color_supply = vec![0u16; n_colors];
        for (pid, piece) in puzzle.pieces().iter().enumerate() {
            for r in 0..4u8 {
                let rot = Rotation::from_u8(r).unwrap();
                let e = piece.edges.rotated(rot).as_array();
                pieces_rot[pid][r as usize] = [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8];
            }
            // Color counts (rotation-invariant)
            for c in piece.edges.as_array() {
                let ci = c as usize;
                if ci != 0 {
                    piece_color_counts[pid][ci] += 1;
                    color_supply[ci] += 1;
                }
            }
        }
        let pos_order: Vec<usize> = (0..n_cells).collect();
        Self {
            side, n_cells, n_pieces, max_color,
            pieces_rot,
            piece_color_counts,
            pos_order,
            board: vec![None; n_cells],
            used_pids: vec![false; n_pieces],
            zob: Zobrist::new(n_pieces, n_cells, max_color),
            cache: HashMap::new(),
            use_memo,
            partial_frontier_k,
            frontier_only,
            color_supply_key,
            use_cfcc,
            color_supply,
            color_demand: vec![0u16; n_colors],
            stats: Stats { nodes: 0, cache_hits: 0, cache_misses: 0, best_depth: 0, nodes_saved_estimate: 0, cfcc_prunes: 0 },
            max_nodes,
            time_limit: std::time::Duration::from_secs_f64(time_secs),
            t_start: Instant::now(),
        }
    }

    fn valid_border(&self, edges: &[u8; 4], pos: usize) -> bool {
        let r = pos / self.side;
        let c = pos % self.side;
        let top = edges[0];
        let right = edges[1];
        let bot = edges[2];
        let left = edges[3];
        if (r == 0) != (top == 0) { return false; }
        if (r == self.side - 1) != (bot == 0) { return false; }
        if (c == 0) != (left == 0) { return false; }
        if (c == self.side - 1) != (right == 0) { return false; }
        true
    }

    fn compat_neighbors(&self, edges: &[u8; 4], pos: usize) -> bool {
        let r = pos / self.side;
        let c = pos % self.side;
        if r > 0 {
            if let Some(n) = &self.board[pos - self.side] {
                if n.edges[2] != edges[0] { return false; }
            }
        }
        if r < self.side - 1 {
            if let Some(n) = &self.board[pos + self.side] {
                if n.edges[0] != edges[2] { return false; }
            }
        }
        if c > 0 {
            if let Some(n) = &self.board[pos - 1] {
                if n.edges[1] != edges[3] { return false; }
            }
        }
        if c < self.side - 1 {
            if let Some(n) = &self.board[pos + 1] {
                if n.edges[3] != edges[1] { return false; }
            }
        }
        true
    }

    fn state_hash(&self, depth: usize) -> u64 {
        let mut h: u64 = 0;
        if self.color_supply_key {
            // Path-Independent Hash: use REMAINING-COLOR-SUPPLY multiset
            // instead of placed-piece-bitset. Two states with same
            // remaining-color-multiset + same frontier-colors collide.
            // Hash = sum of count-of-each-color-still-available * random_per_color.
            let mut color_counts = vec![0u32; self.max_color as usize + 1];
            for pid in 0..self.n_pieces {
                if !self.used_pids[pid] {
                    // Count colors on each edge of UNUSED piece (any rotation = same multiset)
                    for s in 0..4 {
                        color_counts[self.pieces_rot[pid][0][s] as usize] += 1;
                    }
                }
            }
            for (c, &count) in color_counts.iter().enumerate() {
                // Mix count and color into hash via a position-independent multiplier
                let color_zob = self.zob.piece_hash[c.min(self.n_pieces - 1)];
                h = h.wrapping_add(color_zob.wrapping_mul(count as u64));
            }
        } else if !self.frontier_only {
            for pid in 0..self.n_pieces {
                if self.used_pids[pid] {
                    h ^= self.zob.piece_hash[pid];
                }
            }
        }
        // Choose which cells to include in frontier hash
        let start_d = if self.partial_frontier_k > 0 && self.partial_frontier_k < depth {
            depth - self.partial_frontier_k
        } else {
            0
        };
        for d in start_d..depth {
            let pos = self.pos_order[d];
            let pc = self.board[pos].as_ref().expect("placed");
            let r = pos / self.side;
            let c = pos % self.side;
            for (side_idx, (dr, dc)) in [(-1i32, 0i32), (0, 1), (1, 0), (0, -1)].iter().enumerate() {
                let nr = r as i32 + dr;
                let nc = c as i32 + dc;
                if nr < 0 || nc < 0 || nr >= self.side as i32 || nc >= self.side as i32 {
                    continue;
                }
                let npos = (nr as usize) * self.side + nc as usize;
                if self.board[npos].is_some() {
                    continue;
                }
                let color = pc.edges[side_idx];
                let idx = self.zob.frontier_idx(pos, side_idx, color, self.max_color);
                h ^= self.zob.frontier_hash[idx];
            }
        }
        h
    }

    /// CFCC check: returns true if feasible (no color demand > supply).
    fn cfcc_ok(&self) -> bool {
        for k in 1..self.color_demand.len() {
            if self.color_demand[k] > self.color_supply[k] {
                return false;
            }
        }
        true
    }

    /// Update demand incrementally when placing a piece at pos with edges.
    /// Returns delta to undo on backtrack.
    fn update_demand_on_place(&mut self, pos: usize, edges: &[u8; 4]) {
        let r = pos / self.side;
        let c = pos % self.side;
        let offsets: [(i32, i32, usize); 4] = [
            (-1, 0, 0), (0, 1, 1), (1, 0, 2), (0, -1, 3),
        ];
        for &(dr, dc, my_side) in &offsets {
            let nr = r as i32 + dr;
            let nc = c as i32 + dc;
            if nr < 0 || nc < 0 || nr >= self.side as i32 || nc >= self.side as i32 {
                continue; // boundary
            }
            let npos = (nr as usize) * self.side + nc as usize;
            let my_color = edges[my_side];
            if let Some(n) = &self.board[npos] {
                // Neighbor already placed: that side WAS in demand, now satisfied.
                // Subtract the neighbor's color (which equals my_color since we matched).
                let n_side = 2 ^ my_side;  // opposite side index (0↔2, 1↔3 — for 0,1,2,3: opp = (my+2)%4)
                let opp_side = (my_side + 2) % 4;
                let their_color = n.edges[opp_side];
                if their_color != 0 {
                    // That neighbor was contributing to demand; remove it.
                    self.color_demand[their_color as usize] = self.color_demand[their_color as usize].saturating_sub(1);
                }
                let _ = n_side; // unused, kept for clarity
            } else {
                // Neighbor unplaced: my color contributes new demand.
                if my_color != 0 {
                    self.color_demand[my_color as usize] += 1;
                }
            }
        }
    }

    fn update_demand_on_unplace(&mut self, pos: usize, edges: &[u8; 4]) {
        let r = pos / self.side;
        let c = pos % self.side;
        let offsets: [(i32, i32, usize); 4] = [
            (-1, 0, 0), (0, 1, 1), (1, 0, 2), (0, -1, 3),
        ];
        for &(dr, dc, my_side) in &offsets {
            let nr = r as i32 + dr;
            let nc = c as i32 + dc;
            if nr < 0 || nc < 0 || nr >= self.side as i32 || nc >= self.side as i32 {
                continue;
            }
            let npos = (nr as usize) * self.side + nc as usize;
            let my_color = edges[my_side];
            if let Some(n) = &self.board[npos] {
                // Neighbor still placed: re-add their demand.
                let opp_side = (my_side + 2) % 4;
                let their_color = n.edges[opp_side];
                if their_color != 0 {
                    self.color_demand[their_color as usize] += 1;
                }
            } else {
                // Neighbor unplaced: remove my contribution.
                if my_color != 0 {
                    self.color_demand[my_color as usize] = self.color_demand[my_color as usize].saturating_sub(1);
                }
            }
        }
    }

    fn search(&mut self, depth: usize) -> bool {
        self.stats.nodes += 1;
        if self.stats.nodes > self.max_nodes { return false; }
        if self.t_start.elapsed() > self.time_limit { return false; }
        if depth > self.stats.best_depth {
            self.stats.best_depth = depth;
        }
        if depth == self.n_cells {
            return true;
        }

        if self.use_cfcc && !self.cfcc_ok() {
            self.stats.cfcc_prunes += 1;
            return false;
        }

        if self.use_memo {
            let h = self.state_hash(depth);
            if self.cache.contains_key(&h) {
                self.stats.cache_hits += 1;
                self.stats.nodes_saved_estimate += 1;
                return false;
            }
            self.stats.cache_misses += 1;
        }

        let pos = self.pos_order[depth];
        for pid in 0..self.n_pieces {
            if self.used_pids[pid] { continue; }
            for rot in 0..4u8 {
                let edges = self.pieces_rot[pid][rot as usize];
                if !self.valid_border(&edges, pos) { continue; }
                if !self.compat_neighbors(&edges, pos) { continue; }
                self.board[pos] = Some(PlacedCell { edges });
                self.used_pids[pid] = true;
                // Update CFCC state: subtract piece's color supply, update frontier demand
                if self.use_cfcc {
                    for k in 1..self.color_supply.len() {
                        self.color_supply[k] = self.color_supply[k].saturating_sub(self.piece_color_counts[pid][k]);
                    }
                    self.update_demand_on_place(pos, &edges);
                }
                if self.search(depth + 1) {
                    return true;
                }
                if self.use_cfcc {
                    self.update_demand_on_unplace(pos, &edges);
                    for k in 1..self.color_supply.len() {
                        self.color_supply[k] += self.piece_color_counts[pid][k];
                    }
                }
                self.board[pos] = None;
                self.used_pids[pid] = false;
            }
        }
        if self.use_memo {
            let h = self.state_hash(depth);
            self.cache.insert(h, depth as u32);
        }
        false
    }
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/generated/size_5_colors_4_3347f2df.csv");
    let mut max_nodes: u64 = 10_000_000;
    let mut time_secs: f64 = 120.0;
    let mut use_memo = true;
    let mut partial_frontier_k: usize = 0;
    let mut frontier_only = false;
    let mut color_supply_key = false;
    let mut use_cfcc = false;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--max-nodes" => max_nodes = args.next().unwrap().parse().unwrap(),
            "--time-secs" => time_secs = args.next().unwrap().parse().unwrap(),
            "--no-memo" => use_memo = false,
            "--partial-frontier-k" => partial_frontier_k = args.next().unwrap().parse().unwrap(),
            "--frontier-only" => frontier_only = true,
            "--color-supply-key" => color_supply_key = true,
            "--cfcc" => use_cfcc = true,
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    println!("puzzle: {} side={} pieces={} color_count={}",
        puzzle_path.display(), puzzle.width, puzzle.pieces().len(), puzzle.color_count);
    println!("memo: {} partial_k: {} frontier_only: {} color_supply_key: {} cfcc: {}",
        use_memo, partial_frontier_k, frontier_only, color_supply_key, use_cfcc);

    let mut s = Searcher::new(puzzle, max_nodes, time_secs, use_memo, partial_frontier_k, frontier_only, color_supply_key, use_cfcc);
    let t = Instant::now();
    let solved = s.search(0);
    let elapsed = t.elapsed();

    println!("solved: {}", solved);
    println!("best_depth: {}/{}", s.stats.best_depth, s.n_cells);
    println!("nodes_visited: {}", s.stats.nodes);
    println!("cache_size: {}", s.cache.len());
    println!("cache_hits: {}  cache_misses: {}  cfcc_prunes: {}", s.stats.cache_hits, s.stats.cache_misses, s.stats.cfcc_prunes);
    let total = s.stats.cache_hits + s.stats.cache_misses;
    if total > 0 {
        println!("hit_rate: {:.2}%", 100.0 * s.stats.cache_hits as f64 / total as f64);
    }
    println!("elapsed: {:.3}s ({:.0} nps)", elapsed.as_secs_f64(), s.stats.nodes as f64 / elapsed.as_secs_f64());
}
