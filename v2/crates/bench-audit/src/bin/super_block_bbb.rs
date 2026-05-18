// Vol-125 T10 — Super-block BB&B (Bourreau-style backtracking on blocks).
//
// Day-1 deliverables (this file):
//   - Load all 64 super-cell alphabets from output/vol-125/w14/alphabet/.
//   - In-memory representation: Block struct + per-cell Vec<Block>.
//   - Per-cell boundary-key index: HashMap<(u8,u8), Vec<usize>> for each side
//     (N/E/S/W) so we can query "which blocks have N-edge = (c0, c1)" in O(1).
//   - Per-piece occurrence index: Vec<Vec<(sc, slot, block_idx)>> for piece-uniqueness
//     propagation.
//   - Initial reduction via canonical-hint pinning (5 hints → 5 cells reduced to
//     domain size 1 each).
//   - Initial AC-3 (pairwise boundary equality) propagation pass.
//   - Initial piece-uniqueness propagation pass (each piece can appear in ≤1
//     selected block).
//
// Day-2+ (to be added incrementally):
//   - DFS with MRV variable order, value heuristic.
//   - Cube-and-conquer when undecided.

#![forbid(unsafe_code)]

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

const SW: usize = 8; // super-grid side: 8 × 8 = 64 super-cells

// Side indices (matching W14 enum):
const N: usize = 0;
const E: usize = 1;
const S: usize = 2;
const W: usize = 3;

// Block: 4 pieces in slots [TL, TR, BL, BR] with 4 rotations + 4 boundary
// tuples (each tuple is 2 colors).
#[derive(Debug, Clone, Copy)]
struct Block {
    pieces: [u16; 4],
    rots: [u8; 4],
    edge: [[u8; 2]; 4], // edge[side] = (c_min, c_max) for that side
}

fn read_blocks(path: &PathBuf) -> Vec<Block> {
    let bytes = fs::read(path).expect("read alphabet file");
    assert_eq!(&bytes[..4], b"W14B");
    let n = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
    let mut blocks = Vec::with_capacity(n);
    let mut off = 8;
    let block_size = 4 * 2 + 4 + 4 * 2;
    for _ in 0..n {
        let mut b = Block {
            pieces: [0; 4], rots: [0; 4],
            edge: [[0; 2]; 4],
        };
        for j in 0..4 {
            b.pieces[j] = u16::from_le_bytes([bytes[off + 2 * j], bytes[off + 2 * j + 1]]);
        }
        off += 8;
        for j in 0..4 { b.rots[j] = bytes[off + j]; }
        off += 4;
        for s in 0..4 {
            b.edge[s].copy_from_slice(&bytes[off..off + 2]);
            off += 2;
        }
        blocks.push(b);
    }
    assert!(off <= bytes.len());
    blocks
}

#[derive(Debug)]
struct State {
    /// Per-supercell list of currently-valid block indices into `alphabets[sr][sc]`.
    /// Pinned cells have domain = vec![pinned_block_idx].
    domain: Vec<Vec<Vec<u32>>>, // domain[sr][sc] : Vec<u32>
    /// The alphabet (immutable after init). domain[sr][sc] indexes into alphabets[sr][sc].
    alphabets: Vec<Vec<Vec<Block>>>,
    /// Cells that are pinned (decision frozen).
    pinned: Vec<Vec<bool>>,
    /// For each piece-id, set of currently-used (bool).
    used_pieces: Vec<bool>,
}

impl State {
    fn load_alphabets(in_dir: &PathBuf) -> (Vec<Vec<Vec<Block>>>, u64) {
        let mut alphabets: Vec<Vec<Vec<Block>>> =
            (0..SW).map(|_| (0..SW).map(|_| Vec::new()).collect()).collect();
        let mut total: u64 = 0;
        let t0 = Instant::now();
        for sr in 0..SW {
            for sc in 0..SW {
                let path = in_dir.join(format!("sc_{:02}_{:02}.bin", sr, sc));
                let blocks = read_blocks(&path);
                total += blocks.len() as u64;
                alphabets[sr][sc] = blocks;
            }
        }
        eprintln!("Loaded {} blocks across 64 super-cells in {:.1}s",
                  total, t0.elapsed().as_secs_f64());
        (alphabets, total)
    }

    fn build_init(in_dir: &PathBuf) -> Self {
        let (alphabets, _) = Self::load_alphabets(in_dir);
        let domain: Vec<Vec<Vec<u32>>> = (0..SW).map(|sr| {
            (0..SW).map(|sc| (0..alphabets[sr][sc].len() as u32).collect::<Vec<_>>()).collect()
        }).collect();
        let pinned = vec![vec![false; SW]; SW];
        let used_pieces = vec![false; 256];
        State { domain, alphabets, pinned, used_pieces }
    }

    fn domain_sum(&self) -> u64 {
        self.domain.iter().map(|row| row.iter().map(|v| v.len() as u64).sum::<u64>()).sum()
    }

    fn min_domain_unpinned(&self) -> Option<(usize, usize, usize)> {
        let mut best: Option<(usize, usize, usize)> = None;
        for sr in 0..SW {
            for sc in 0..SW {
                if self.pinned[sr][sc] { continue; }
                let n = self.domain[sr][sc].len();
                if n == 0 { return Some((sr, sc, 0)); } // wipeout signal
                match best {
                    None => best = Some((sr, sc, n)),
                    Some((_, _, prev_n)) if n < prev_n => best = Some((sr, sc, n)),
                    _ => {}
                }
            }
        }
        best
    }

    /// AC-3 over boundary equality: for each super-cell, restrict its domain to
    /// blocks whose each boundary tuple appears as the opposite-side tuple of
    /// some block in the adjacent super-cell.
    /// Returns total removed, or None if wipeout.
    fn boundary_ac3_pass(&mut self) -> Option<u64> {
        let mut removed: u64 = 0;

        // For each super-cell, compute set of boundary tuples observed on each side.
        let mut bsets: Vec<Vec<[HashSet<(u8, u8)>; 4]>> =
            (0..SW).map(|_| (0..SW).map(|_| [HashSet::new(), HashSet::new(), HashSet::new(), HashSet::new()]).collect()).collect();
        for sr in 0..SW {
            for sc in 0..SW {
                for &idx in &self.domain[sr][sc] {
                    let b = self.alphabets[sr][sc][idx as usize];
                    for s in 0..4 {
                        bsets[sr][sc][s].insert((b.edge[s][0], b.edge[s][1]));
                    }
                }
            }
        }

        let opposite: [usize; 4] = [S, W, N, E]; // N→S, E→W, S→N, W→E
        let side_dirs: [(isize, isize); 4] = [(-1, 0), (0, 1), (1, 0), (0, -1)];

        for sr in 0..SW {
            for sc in 0..SW {
                if self.pinned[sr][sc] { continue; }
                let mut allowed: [Option<HashSet<(u8, u8)>>; 4] = Default::default();
                for s in 0..4 {
                    let (dr, dc) = side_dirs[s];
                    let nr = sr as isize + dr;
                    let nc = sc as isize + dc;
                    if nr < 0 || nc < 0 || nr >= SW as isize || nc >= SW as isize { continue; }
                    let nbr_r = nr as usize;
                    let nbr_c = nc as usize;
                    allowed[s] = Some(bsets[nbr_r][nbr_c][opposite[s]].clone());
                }
                let before = self.domain[sr][sc].len();
                self.domain[sr][sc].retain(|&idx| {
                    let b = self.alphabets[sr][sc][idx as usize];
                    for s in 0..4 {
                        if let Some(ref set) = allowed[s] {
                            if !set.contains(&(b.edge[s][0], b.edge[s][1])) {
                                return false;
                            }
                        }
                    }
                    true
                });
                let after = self.domain[sr][sc].len();
                removed += (before - after) as u64;
                if after == 0 {
                    eprintln!("  ** boundary-AC3 wipeout at ({},{}) (before={})", sr, sc, before);
                    return None;
                }
            }
        }
        Some(removed)
    }

    /// Piece-uniqueness pass: any piece used by a pinned block is removed from
    /// non-pinned cell domains. Returns total removed, or None if wipeout.
    fn piece_uniqueness_pass(&mut self) -> Option<u64> {
        let mut removed: u64 = 0;
        for sr in 0..SW {
            for sc in 0..SW {
                if self.pinned[sr][sc] { continue; }
                let before = self.domain[sr][sc].len();
                let alphabet = &self.alphabets[sr][sc];
                let used_pieces = &self.used_pieces;
                self.domain[sr][sc].retain(|&idx| {
                    let b = alphabet[idx as usize];
                    !b.pieces.iter().any(|p| used_pieces[*p as usize])
                });
                let after = self.domain[sr][sc].len();
                removed += (before - after) as u64;
                if after == 0 {
                    eprintln!("  ** piece-uniqueness wipeout at ({},{}) (before={})", sr, sc, before);
                    return None;
                }
            }
        }
        Some(removed)
    }

    /// Pin a super-cell to a specific block index (in the local alphabet).
    fn pin(&mut self, sr: usize, sc: usize, local_idx: u32) {
        let b = self.alphabets[sr][sc][local_idx as usize];
        self.domain[sr][sc].clear();
        self.domain[sr][sc].push(local_idx);
        self.pinned[sr][sc] = true;
        for &p in &b.pieces {
            self.used_pieces[p as usize] = true;
        }
    }

    /// Snapshot the search-mutable state (for backtracking).
    fn snapshot(&self) -> Snapshot {
        Snapshot {
            domain: self.domain.clone(),
            pinned: self.pinned.clone(),
            used_pieces: self.used_pieces.clone(),
        }
    }

    fn restore(&mut self, s: Snapshot) {
        self.domain = s.domain;
        self.pinned = s.pinned;
        self.used_pieces = s.used_pieces;
    }

    /// Are all cells pinned? If so, we have a 480 solution.
    fn all_pinned(&self) -> bool {
        for sr in 0..SW {
            for sc in 0..SW {
                if !self.pinned[sr][sc] { return false; }
            }
        }
        true
    }

    /// Extract the 256-cell placement from a fully-pinned state.
    fn extract_placement(&self) -> Vec<(u32, u16, u8)> {
        let mut out = Vec::with_capacity(256);
        // Each super-cell pins a block of 4 pieces in slots TL, TR, BL, BR.
        // sr,sc give the super-cell; cells are at:
        //   TL = (sr*2, sc*2), TR = (sr*2, sc*2+1)
        //   BL = (sr*2+1, sc*2), BR = (sr*2+1, sc*2+1)
        for sr in 0..SW {
            for sc in 0..SW {
                let local_idx = self.domain[sr][sc][0];
                let b = self.alphabets[sr][sc][local_idx as usize];
                let slot_pos = [
                    ((sr * 2) * 16 + sc * 2) as u32,         // TL
                    ((sr * 2) * 16 + sc * 2 + 1) as u32,     // TR
                    ((sr * 2 + 1) * 16 + sc * 2) as u32,     // BL
                    ((sr * 2 + 1) * 16 + sc * 2 + 1) as u32, // BR
                ];
                for slot in 0..4 {
                    out.push((slot_pos[slot], b.pieces[slot], b.rots[slot]));
                }
            }
        }
        out
    }

    /// Run AC-3 + uniqueness propagation to fixed point. Returns None on wipeout.
    fn propagate_to_fixpoint(&mut self) -> Option<()> {
        loop {
            let r1 = self.boundary_ac3_pass()?;
            let r2 = self.piece_uniqueness_pass()?;
            if r1 == 0 && r2 == 0 { return Some(()); }
        }
    }

    /// Hint-piece propagation: hint cells (already alphabet-restricted by the
    /// enumerator) ALWAYS use the specific hint piece in the specific slot.
    /// We extract the SET of hint pieces, mark them as "claimed by the hint
    /// cell", and remove them from non-hint cell domains.
    ///
    /// hint_cells: list of (sr, sc, hint_piece_id). All blocks in the alphabet
    /// at these cells contain the hint piece. Other cells' blocks containing
    /// the hint piece are infeasible.
    fn apply_hint_piece_uniqueness(&mut self,
                                     hint_cells: &[(usize, usize, u16)]) -> Option<u64> {
        let mut hint_pieces: HashSet<u16> = HashSet::new();
        let hint_cell_set: HashSet<(usize, usize)> =
            hint_cells.iter().map(|(r, c, _)| (*r, *c)).collect();
        for (_, _, p) in hint_cells {
            hint_pieces.insert(*p);
        }
        let mut removed: u64 = 0;
        for sr in 0..SW {
            for sc in 0..SW {
                if hint_cell_set.contains(&(sr, sc)) { continue; }
                let before = self.domain[sr][sc].len();
                let alphabet = &self.alphabets[sr][sc];
                self.domain[sr][sc].retain(|&idx| {
                    let b = alphabet[idx as usize];
                    !b.pieces.iter().any(|p| hint_pieces.contains(p))
                });
                let after = self.domain[sr][sc].len();
                removed += (before - after) as u64;
                if after == 0 { return None; }
            }
        }
        // NOTE: we deliberately do NOT mark these pieces as `used_pieces`
        // because the hint cells themselves still legally hold them.
        // The hint-piece-uniqueness step removed them from all non-hint cells,
        // which is enough.
        Some(removed)
    }
}

#[derive(Debug, Clone)]
struct Snapshot {
    domain: Vec<Vec<Vec<u32>>>,
    pinned: Vec<Vec<bool>>,
    used_pieces: Vec<bool>,
}

/// DFS search. Returns Some(placement) if a 480 board is found.
/// max_nodes: stop after this many decisions (for budgets).
fn dfs(state: &mut State, depth: usize, max_nodes: u64, nodes: &mut u64, t_start: Instant) -> Option<Vec<(u32, u16, u8)>> {
    if *nodes >= max_nodes {
        return None;
    }
    *nodes += 1;
    if state.all_pinned() {
        return Some(state.extract_placement());
    }
    let (sr, sc, dom_size) = match state.min_domain_unpinned() {
        Some(t) => t,
        None => return None,
    };
    if dom_size == 0 { return None; }
    if *nodes % 100 == 0 {
        let elapsed = t_start.elapsed().as_secs_f64();
        let dom_sum = state.domain_sum();
        let pinned_count: usize = state.pinned.iter().flat_map(|r| r.iter()).filter(|&&b| b).count();
        eprintln!("[node {}] depth={} pinned={} dom_sum={} elapsed={:.1}s next=({},{}) dom_size={}",
                  *nodes, depth, pinned_count, dom_sum, elapsed, sr, sc, dom_size);
    }

    let candidates = state.domain[sr][sc].clone();
    for cand_idx in candidates {
        // Snapshot, pin, propagate, recurse.
        let snap = state.snapshot();
        state.pin(sr, sc, cand_idx);
        if state.propagate_to_fixpoint().is_some() {
            if let Some(res) = dfs(state, depth + 1, max_nodes, nodes, t_start) {
                return Some(res);
            }
        }
        state.restore(snap);
        if *nodes >= max_nodes { return None; }
    }
    None
}

fn main() {
    let mut in_dir: PathBuf = "output/vol-125/w14/alphabet".into();
    let mut max_nodes: u64 = 1000;
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--in-dir" => { in_dir = args[i + 1].clone().into(); i += 2; }
            "--max-nodes" => { max_nodes = args[i + 1].parse().unwrap(); i += 2; }
            _ => { eprintln!("Unknown arg: {}", args[i]); std::process::exit(2); }
        }
    }

    eprintln!("=== Super-block BB&B (Day-1 init pass) ===");
    eprintln!("Loading alphabets from {}...", in_dir.display());
    let mut state = State::build_init(&in_dir);
    let init_sum = state.domain_sum();
    eprintln!("Initial domain sum: {}", init_sum);

    // Canonical hints (from W14 enumerator):
    //   pos 135 → (4,3) slot TR piece 138 rot 0
    //   pos 210 → (6,1) slot BL piece 180 rot 1
    //   pos 34  → (1,1) slot TL piece 207 rot 1
    //   pos 221 → (6,6) slot BR piece 248 rot 2
    //   pos 45  → (1,6) slot TR piece 254 rot 1
    let hint_cells: Vec<(usize, usize, u16)> = vec![
        (4, 3, 138),
        (6, 1, 180),
        (1, 1, 207),
        (6, 6, 248),
        (1, 6, 254),
    ];

    eprintln!("\nApplying hint-piece uniqueness (remove hint pieces from non-hint cells)...");
    let t_hint = Instant::now();
    match state.apply_hint_piece_uniqueness(&hint_cells) {
        Some(removed) => {
            eprintln!("  removed {} block-options in {:.1}s",
                       removed, t_hint.elapsed().as_secs_f64());
            eprintln!("  domain sum after hint prop: {} (was {})",
                       state.domain_sum(), init_sum);
        }
        None => {
            eprintln!("  UNSAT during hint propagation (shouldn't happen)");
            return;
        }
    }

    eprintln!("\nRunning AC-3 + piece-uniqueness to fixpoint...");
    let t0 = Instant::now();
    match state.propagate_to_fixpoint() {
        Some(()) => {
            let final_sum = state.domain_sum();
            eprintln!("  Done in {:.1}s", t0.elapsed().as_secs_f64());
            eprintln!("  Final domain sum: {} (was {})", final_sum, init_sum);
            eprintln!("  Reduction: {:.2}x",
                       init_sum as f64 / final_sum.max(1) as f64);

            // Per-cell sizes
            let mut sizes: Vec<((usize, usize), usize)> = Vec::with_capacity(64);
            for sr in 0..SW {
                for sc in 0..SW {
                    sizes.push(((sr, sc), state.domain[sr][sc].len()));
                }
            }
            sizes.sort_by_key(|(_, n)| *n);
            eprintln!("\nPer-cell sizes (smallest 10):");
            for ((sr, sc), n) in sizes.iter().take(10) {
                eprintln!("  ({},{}): {}", sr, sc, n);
            }
            eprintln!("\nPer-cell sizes (largest 5):");
            for ((sr, sc), n) in sizes.iter().rev().take(5).rev() {
                eprintln!("  ({},{}): {}", sr, sc, n);
            }
            eprintln!("\nMin: {} | Max: {} | Mean: {:.0}",
                       sizes.first().map(|x| x.1).unwrap_or(0),
                       sizes.last().map(|x| x.1).unwrap_or(0),
                       final_sum as f64 / 64.0);

            // Pieces still unused
            let unused = state.used_pieces.iter().filter(|&&u| !u).count();
            eprintln!("\nUnused pieces: {} (used: {})", unused, 256 - unused);
        }
        None => {
            eprintln!("  UNSAT: domain wipeout during initial propagation");
            return;
        }
    }

    eprintln!("\n=== DFS search (max_nodes={}) ===", max_nodes);
    let t_dfs = Instant::now();
    let mut nodes = 0u64;
    match dfs(&mut state, 0, max_nodes, &mut nodes, t_dfs) {
        Some(placement) => {
            eprintln!("\n🎯 480 SOLUTION FOUND after {} nodes ({:.1}s)",
                       nodes, t_dfs.elapsed().as_secs_f64());
            // Dump solution to a JSON
            let json = serde_json::json!({
                "matched": 480,
                "placement": placement.iter().map(|(pos, pid, rot)| {
                    serde_json::json!({"pos": pos, "piece_id": pid, "rotation": rot})
                }).collect::<Vec<_>>(),
                "source": "super_block_bbb"
            });
            let path = "output/vol-125/SOLUTION_480.json";
            std::fs::write(path, serde_json::to_string_pretty(&json).unwrap())
                .expect("write");
            eprintln!("Saved to: {}", path);
        }
        None => {
            eprintln!("\nDFS exhausted/exceeded budget without 480.");
            eprintln!("Nodes explored: {} | Time: {:.1}s", nodes, t_dfs.elapsed().as_secs_f64());
        }
    }

    eprintln!("\nDone.");
}
