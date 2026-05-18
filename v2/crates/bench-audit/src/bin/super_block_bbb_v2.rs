// Vol-125 T10 v2 — Super-block BB&B with sparse-set domains + trail-based undo.
//
// Performance contract:
//   - Loading 64 alphabets: ~8s (unavoidable I/O).
//   - Initial AC-3 + hint-uniqueness fixpoint: ~30s (full pass).
//   - Each DFS pin: ms not seconds. Backtracking restores trail in O(removed).
//
// Sparse-set: domain[sr][sc] is a Vec<u32> + a `live_size` counter. Indices
// past live_size are removed. Removing index at position i: swap with
// live_size-1, decrement live_size. Restoring: just restore live_size.

#![forbid(unsafe_code)]

use std::collections::HashSet;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

const SW: usize = 8;

// Sides: N=0, E=1, S=2, W=3
const N: usize = 0;
const E: usize = 1;
const S: usize = 2;
const W: usize = 3;

#[derive(Debug, Clone, Copy)]
struct Block {
    pieces: [u16; 4],
    rots: [u8; 4],
    edge: [[u8; 2]; 4],
}

fn read_blocks(path: &PathBuf) -> Vec<Block> {
    let bytes = fs::read(path).expect("read alphabet file");
    assert_eq!(&bytes[..4], b"W14B");
    let n = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
    let mut blocks = Vec::with_capacity(n);
    let mut off = 8;
    for _ in 0..n {
        let mut b = Block { pieces: [0; 4], rots: [0; 4], edge: [[0; 2]; 4] };
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
    blocks
}

/// Sparse-set domain for one super-cell. The buffer holds ALL alphabet indices;
/// indices [0, live_size) are "alive", the rest are "removed".
struct SparseDomain {
    buf: Vec<u32>,
    live: u32,
}

impl SparseDomain {
    fn full(n: u32) -> Self {
        SparseDomain { buf: (0..n).collect(), live: n }
    }
    #[inline] fn len(&self) -> u32 { self.live }
    #[inline] fn iter_live(&self) -> &[u32] { &self.buf[..self.live as usize] }

    /// Remove the element at buffer position `pos` (within [0, live)).
    /// Returns the removed index. O(1).
    #[inline]
    fn swap_remove_at(&mut self, pos: usize) -> u32 {
        let last = self.live as usize - 1;
        let removed = self.buf[pos];
        self.buf[pos] = self.buf[last];
        self.buf[last] = removed;
        self.live -= 1;
        removed
    }

    /// Restore live size to `target` (must be >= current live size).
    /// Used in trail-based backtracking.
    #[inline]
    fn restore_live(&mut self, target: u32) {
        debug_assert!(target >= self.live);
        self.live = target;
    }
}

struct State {
    alphabets: Vec<Vec<Vec<Block>>>,
    domain: Vec<Vec<SparseDomain>>,
    pinned: Vec<Vec<bool>>,
    used_pieces: [bool; 256],
    /// Per-(piece, side) hint-cell ownership. piece_owner[p] = Some((sr, sc))
    /// if piece p is restricted to that super-cell (typically a hint piece).
    /// Otherwise None; piece may be used anywhere.
    piece_owner: [Option<(u8, u8)>; 256],
    /// For each piece, list of (sr, sc, local_alphabet_index) where the piece
    /// appears. Used by piece-uniqueness propagation.
    piece_occ: Vec<Vec<(u8, u8, u32)>>,
    /// Trail: each entry is (sr, sc, prev_live_size). On backtrack, restore.
    /// Levels mark checkpoints.
    trail: Vec<(u8, u8, u32)>,
    /// Per-level start index in `trail`.
    levels: Vec<u32>,
}

impl State {
    fn load(in_dir: &PathBuf) -> Self {
        let t0 = Instant::now();
        let mut alphabets: Vec<Vec<Vec<Block>>> =
            (0..SW).map(|_| (0..SW).map(|_| Vec::new()).collect()).collect();
        let mut total: u64 = 0;
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

        let domain: Vec<Vec<SparseDomain>> = (0..SW).map(|sr| {
            (0..SW).map(|sc| SparseDomain::full(alphabets[sr][sc].len() as u32)).collect()
        }).collect();

        // Build piece_occ
        let mut piece_occ: Vec<Vec<(u8, u8, u32)>> = vec![Vec::new(); 256];
        for sr in 0..SW {
            for sc in 0..SW {
                for (idx, b) in alphabets[sr][sc].iter().enumerate() {
                    for &p in &b.pieces {
                        piece_occ[p as usize].push((sr as u8, sc as u8, idx as u32));
                    }
                }
            }
        }
        eprintln!("Built piece_occ in {:.1}s (total occurrences: {})",
                  t0.elapsed().as_secs_f64(), piece_occ.iter().map(|v| v.len()).sum::<usize>());

        State {
            alphabets,
            domain,
            pinned: vec![vec![false; SW]; SW],
            used_pieces: [false; 256],
            piece_owner: [None; 256],
            piece_occ,
            trail: Vec::with_capacity(1_000_000),
            levels: Vec::with_capacity(128),
        }
    }

    fn domain_sum(&self) -> u64 {
        let mut s = 0u64;
        for sr in 0..SW { for sc in 0..SW { s += self.domain[sr][sc].len() as u64; } }
        s
    }

    /// Remove a single block index from a cell's domain. Returns true if it was present.
    /// Records the change on the trail for backtracking.
    fn remove_block(&mut self, sr: usize, sc: usize, block_idx: u32) -> bool {
        let d = &mut self.domain[sr][sc];
        // Linear scan to find the position. (Could be O(1) with a reverse map per cell, but
        // adds memory. For now, scan; this is the hottest path so we may need to optimize.)
        let n = d.live as usize;
        for i in 0..n {
            if d.buf[i] == block_idx {
                // Record (sr, sc, prev_live) once per cell per level — but to keep
                // restoration simple, record EVERY removal: actually, sparse-set
                // restoration only needs (sr, sc, prev_live) ONCE per cell per level.
                // So we use a different scheme: trail records the OLD live_size
                // exactly once per (cell, level). To avoid re-trailing, we use a
                // separate "trailed_this_level" bitmap — but that's complex.
                //
                // Simpler approach: every removal pushes a (sr, sc, prev_live) entry
                // pointing to the live BEFORE this removal. On backtrack, pop entries
                // and restore each cell's live to MAX of the trail values seen for it.
                self.trail.push((sr as u8, sc as u8, d.live));
                d.swap_remove_at(i);
                return true;
            }
        }
        false
    }

    /// Begin a new search level. Records current trail position.
    fn push_level(&mut self) {
        self.levels.push(self.trail.len() as u32);
    }

    /// Pop the topmost level, restoring all changes made since it was pushed.
    fn pop_level(&mut self) {
        let start = self.levels.pop().expect("no level to pop") as usize;
        // For sparse-set restoration: walk the trail backwards, restore each cell's live
        // to the MAX recorded value. But since pushes were in order live decreasing, the
        // FIRST trail entry for a cell at this level recorded the LARGEST live value.
        // So scanning from end to start and restoring whichever live is larger works.
        for i in (start..self.trail.len()).rev() {
            let (sr, sc, prev_live) = self.trail[i];
            let d = &mut self.domain[sr as usize][sc as usize];
            if d.live < prev_live { d.live = prev_live; }
        }
        self.trail.truncate(start);
    }

    /// Build per-cell boundary-tuple sets and prune blocks whose any side's
    /// tuple is not in the opposite cell's allowed set. Single pass; caller
    /// must loop to fixpoint.
    fn boundary_ac3_pass(&mut self) -> Option<u64> {
        // Compute per-cell boundary sets (HashSet per side).
        let mut bsets: Vec<Vec<[HashSet<(u8, u8)>; 4]>> =
            (0..SW).map(|_| (0..SW).map(|_| [HashSet::new(), HashSet::new(), HashSet::new(), HashSet::new()]).collect()).collect();
        for sr in 0..SW {
            for sc in 0..SW {
                let d = &self.domain[sr][sc];
                let alphabet = &self.alphabets[sr][sc];
                for &idx in d.iter_live() {
                    let b = alphabet[idx as usize];
                    for s in 0..4 {
                        bsets[sr][sc][s].insert((b.edge[s][0], b.edge[s][1]));
                    }
                }
            }
        }

        let opposite: [usize; 4] = [S, W, N, E];
        let side_dirs: [(isize, isize); 4] = [(-1, 0), (0, 1), (1, 0), (0, -1)];

        let mut removed_total: u64 = 0;
        for sr in 0..SW {
            for sc in 0..SW {
                if self.pinned[sr][sc] { continue; }
                let mut allowed: [Option<&HashSet<(u8, u8)>>; 4] = [None, None, None, None];
                for s in 0..4 {
                    let (dr, dc) = side_dirs[s];
                    let nr = sr as isize + dr;
                    let nc = sc as isize + dc;
                    if nr < 0 || nc < 0 || nr >= SW as isize || nc >= SW as isize { continue; }
                    allowed[s] = Some(&bsets[nr as usize][nc as usize][opposite[s]]);
                }
                // Walk the domain, swap-removing blocks that fail the test.
                let mut i = 0;
                while i < self.domain[sr][sc].live as usize {
                    let idx = self.domain[sr][sc].buf[i];
                    let b = self.alphabets[sr][sc][idx as usize];
                    let mut ok = true;
                    for s in 0..4 {
                        if let Some(set) = allowed[s] {
                            if !set.contains(&(b.edge[s][0], b.edge[s][1])) {
                                ok = false; break;
                            }
                        }
                    }
                    if ok {
                        i += 1;
                    } else {
                        // Trail + swap-remove.
                        self.trail.push((sr as u8, sc as u8, self.domain[sr][sc].live));
                        self.domain[sr][sc].swap_remove_at(i);
                        removed_total += 1;
                        // don't increment i — new element at position i needs checking.
                    }
                }
                if self.domain[sr][sc].live == 0 { return None; }
            }
        }
        Some(removed_total)
    }

    /// Piece-uniqueness propagation: remove blocks containing any used piece,
    /// from all non-owning cells.
    fn piece_uniqueness_pass(&mut self) -> Option<u64> {
        let mut removed_total: u64 = 0;
        for sr in 0..SW {
            for sc in 0..SW {
                if self.pinned[sr][sc] { continue; }
                let owner = (sr as u8, sc as u8);
                let mut i = 0;
                while i < self.domain[sr][sc].live as usize {
                    let idx = self.domain[sr][sc].buf[i];
                    let b = self.alphabets[sr][sc][idx as usize];
                    let mut bad = false;
                    for &p in &b.pieces {
                        if self.used_pieces[p as usize] {
                            // Is this cell the owner of piece p? If yes, allowed.
                            if self.piece_owner[p as usize] != Some(owner) {
                                bad = true; break;
                            }
                        }
                    }
                    if bad {
                        self.trail.push((sr as u8, sc as u8, self.domain[sr][sc].live));
                        self.domain[sr][sc].swap_remove_at(i);
                        removed_total += 1;
                    } else {
                        i += 1;
                    }
                }
                if self.domain[sr][sc].live == 0 { return None; }
            }
        }
        Some(removed_total)
    }

    /// Apply hint-piece uniqueness: mark hint pieces as "used" but owned by the hint cell.
    /// Then piece_uniqueness_pass will only remove hint pieces from non-hint cells.
    fn apply_hints(&mut self, hint_cells: &[(usize, usize, u16)]) -> Option<u64> {
        for &(sr, sc, p) in hint_cells {
            self.used_pieces[p as usize] = true;
            self.piece_owner[p as usize] = Some((sr as u8, sc as u8));
        }
        self.piece_uniqueness_pass()
    }

    /// Propagate AC-3 + uniqueness to fixpoint.
    fn propagate_to_fixpoint(&mut self) -> Option<()> {
        loop {
            let r1 = self.boundary_ac3_pass()?;
            let r2 = self.piece_uniqueness_pass()?;
            if r1 == 0 && r2 == 0 { return Some(()); }
        }
    }

    fn min_domain_unpinned(&self) -> Option<(usize, usize, u32)> {
        let mut best: Option<(usize, usize, u32)> = None;
        for sr in 0..SW {
            for sc in 0..SW {
                if self.pinned[sr][sc] { continue; }
                let n = self.domain[sr][sc].live;
                if n == 0 { return Some((sr, sc, 0)); }
                match best {
                    None => best = Some((sr, sc, n)),
                    Some((_, _, prev_n)) if n < prev_n => best = Some((sr, sc, n)),
                    _ => {}
                }
            }
        }
        best
    }

    fn all_pinned(&self) -> bool {
        for sr in 0..SW {
            for sc in 0..SW {
                if !self.pinned[sr][sc] { return false; }
            }
        }
        true
    }

    /// Pin cell (sr, sc) to its k-th alphabet index. Domain becomes size 1.
    /// All other blocks in this cell's domain are removed (trailed). The 4
    /// pieces of the pinned block are marked used (with this cell as owner).
    /// Caller must save the state of pieces too if needed: we record the
    /// previous (used_pieces[p], piece_owner[p]) into the trail via a special
    /// encoding. Use sr=SW, sc=SW (out of range) to mark piece-trail entries.
    fn pin_to_index(&mut self, sr: usize, sc: usize, block_idx: u32) {
        // Remove every other block from the domain (trailing).
        let mut i = 0;
        while i < self.domain[sr][sc].live as usize {
            if self.domain[sr][sc].buf[i] != block_idx {
                self.trail.push((sr as u8, sc as u8, self.domain[sr][sc].live));
                self.domain[sr][sc].swap_remove_at(i);
            } else {
                i += 1;
            }
        }
        // Now domain has only block_idx (at position 0 or wherever).
        // Mark cell as pinned.
        self.pinned[sr][sc] = true;
        // Mark the 4 pieces used by this block.
        let b = self.alphabets[sr][sc][block_idx as usize];
        for &p in &b.pieces {
            // Trail piece state via sentinel sr=SW, sc=p_high (encoding the piece)
            // Hmm, our trail is (u8, u8, u32). For piece trail, use:
            //   sr = 0xFF (sentinel "piece trail")
            //   sc = piece_id_low_byte
            //   prev_live = piece_id_high | (was_used<<8) | (owner_sr<<16) | (owner_sc<<24)
            let was_used = self.used_pieces[p as usize] as u32;
            let (osr, osc) = match self.piece_owner[p as usize] {
                Some((s, c)) => (s as u32 | 0x80, c as u32),
                None => (0, 0),
            };
            let packed = (p as u32 >> 8) | (was_used << 8) | (osr << 16) | (osc << 24);
            self.trail.push((0xFF, p as u8, packed));
            self.used_pieces[p as usize] = true;
            self.piece_owner[p as usize] = Some((sr as u8, sc as u8));
        }
        // Also trail the pinned state (so backtrack can undo it).
        // Use sentinel sr=0xFE: (0xFE, sc, sr) records that (sr, sc) was just pinned.
        self.trail.push((0xFE, sc as u8, sr as u32));
    }
}

/// Walk the trail back to position `start`, restoring everything.
fn rewind_trail(state: &mut State, start: usize) {
    while state.trail.len() > start {
        let (a, b, c) = state.trail.pop().unwrap();
        if a == 0xFF {
            // Piece trail entry. b = piece_id low byte, c = packed.
            let p_high = c & 0xFF;
            let p = (p_high << 8) | (b as u32);
            let was_used = ((c >> 8) & 0x01) != 0;
            let osr_packed = (c >> 16) & 0xFF;
            let osc = (c >> 24) & 0xFF;
            state.used_pieces[p as usize] = was_used;
            state.piece_owner[p as usize] = if (osr_packed & 0x80) != 0 {
                Some(((osr_packed & 0x7F) as u8, osc as u8))
            } else {
                None
            };
        } else if a == 0xFE {
            // Pinned trail entry: (sr, sc) was pinned; unpin.
            let sc = b as usize;
            let sr = c as usize;
            state.pinned[sr][sc] = false;
        } else {
            // Normal domain entry: (sr, sc, prev_live).
            let d = &mut state.domain[a as usize][b as usize];
            if d.live < c { d.live = c; }
        }
    }
}

fn dfs(state: &mut State, depth: usize, max_nodes: u64, nodes: &mut u64,
       t_start: Instant) -> Option<Vec<(u32, u16, u8)>> {
    if *nodes >= max_nodes { return None; }
    *nodes += 1;
    if state.all_pinned() {
        return Some(extract_placement(state));
    }
    let (sr, sc, dom_size) = state.min_domain_unpinned()?;
    if dom_size == 0 { return None; }
    if *nodes % 50 == 0 {
        let elapsed = t_start.elapsed().as_secs_f64();
        let dom_sum = state.domain_sum();
        let pinned_count: usize = state.pinned.iter().flat_map(|r| r.iter())
            .filter(|&&b| b).count();
        eprintln!("[node {}] depth={} pinned={} dom_sum={} elapsed={:.1}s next=({},{}) dom_size={}",
                  *nodes, depth, pinned_count, dom_sum, elapsed, sr, sc, dom_size);
    }

    // Snapshot candidate list (since pin_to_index will modify domain).
    let candidates: Vec<u32> = state.domain[sr][sc].iter_live().to_vec();
    for cand_idx in candidates {
        let trail_mark = state.trail.len();
        state.pin_to_index(sr, sc, cand_idx);
        if state.propagate_to_fixpoint().is_some() {
            if let Some(res) = dfs(state, depth + 1, max_nodes, nodes, t_start) {
                return Some(res);
            }
        }
        rewind_trail(state, trail_mark);
        if *nodes >= max_nodes { return None; }
    }
    None
}

fn extract_placement(state: &State) -> Vec<(u32, u16, u8)> {
    let mut out = Vec::with_capacity(256);
    for sr in 0..SW {
        for sc in 0..SW {
            let local_idx = state.domain[sr][sc].buf[0];
            let b = state.alphabets[sr][sc][local_idx as usize];
            let slot_pos = [
                ((sr * 2) * 16 + sc * 2) as u32,
                ((sr * 2) * 16 + sc * 2 + 1) as u32,
                ((sr * 2 + 1) * 16 + sc * 2) as u32,
                ((sr * 2 + 1) * 16 + sc * 2 + 1) as u32,
            ];
            for slot in 0..4 {
                out.push((slot_pos[slot], b.pieces[slot], b.rots[slot]));
            }
        }
    }
    out
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

    eprintln!("=== Super-block BB&B v2 (sparse-set + trail) ===");
    let mut state = State::load(&in_dir);
    let init_sum = state.domain_sum();
    eprintln!("Initial domain sum: {}", init_sum);

    let hint_cells: Vec<(usize, usize, u16)> = vec![
        (4, 3, 138), (6, 1, 180), (1, 1, 207), (6, 6, 248), (1, 6, 254),
    ];

    eprintln!("\nApplying hints...");
    let t = Instant::now();
    if state.apply_hints(&hint_cells).is_none() {
        eprintln!("UNSAT applying hints (shouldn't happen)");
        return;
    }
    eprintln!("  domain sum after hints: {} (in {:.1}s)",
              state.domain_sum(), t.elapsed().as_secs_f64());

    eprintln!("\nAC-3 + uniqueness to fixpoint...");
    let t = Instant::now();
    match state.propagate_to_fixpoint() {
        Some(()) => {
            eprintln!("  done in {:.1}s, domain sum: {} (init: {}, reduction: {:.2}x)",
                      t.elapsed().as_secs_f64(), state.domain_sum(), init_sum,
                      init_sum as f64 / state.domain_sum().max(1) as f64);
        }
        None => {
            eprintln!("  UNSAT during init propagation");
            return;
        }
    }

    eprintln!("\n=== DFS (max_nodes={}) ===", max_nodes);
    let t_dfs = Instant::now();
    let mut nodes = 0u64;
    match dfs(&mut state, 0, max_nodes, &mut nodes, t_dfs) {
        Some(placement) => {
            eprintln!("\n🎯 480 SOLUTION found after {} nodes ({:.1}s)",
                      nodes, t_dfs.elapsed().as_secs_f64());
            let json = serde_json::json!({
                "matched": 480,
                "placement": placement.iter().map(|(pos, pid, rot)| {
                    serde_json::json!({"pos": pos, "piece_id": pid, "rotation": rot})
                }).collect::<Vec<_>>(),
                "source": "super_block_bbb_v2"
            });
            let path = "output/vol-125/SOLUTION_480.json";
            std::fs::write(path, serde_json::to_string_pretty(&json).unwrap()).expect("write");
            eprintln!("Saved to: {}", path);
        }
        None => {
            eprintln!("\nDFS exhausted/exceeded after {} nodes ({:.1}s) without 480.",
                      nodes, t_dfs.elapsed().as_secs_f64());
        }
    }
}
