// Vol-125 T10 v3 — incremental propagation, O(1) sparse-set swap-remove.
//
// Improvements over v2:
//   1. Per-cell pos_of[block_idx] = position in buf, so swap-remove is O(1).
//   2. Incremental piece-uniqueness: iterate piece_occ[p] for each newly-used
//      piece p, not full-cell-scan.
//   3. Incremental boundary AC-3: after a pin, only re-check the pinned cell's
//      4 neighbors' boundary sides.
//   4. Same trail-based undo as v2.

#![forbid(unsafe_code)]

use std::collections::HashSet;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

const SW: usize = 8;
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

/// Sparse-set domain WITH reverse-index for O(1) removal.
struct SparseDomain {
    buf: Vec<u32>,        // length = alphabet_size; first `live` are alive
    pos_of: Vec<u32>,     // pos_of[block_idx] = current position in buf
    live: u32,
}

impl SparseDomain {
    fn full(n: u32) -> Self {
        let buf: Vec<u32> = (0..n).collect();
        let pos_of: Vec<u32> = (0..n).collect();
        SparseDomain { buf, pos_of, live: n }
    }

    #[inline] fn len(&self) -> u32 { self.live }

    /// Is this block index currently alive?
    #[inline]
    fn contains(&self, block_idx: u32) -> bool {
        self.pos_of[block_idx as usize] < self.live
    }

    #[inline]
    fn iter_live(&self) -> &[u32] { &self.buf[..self.live as usize] }

    /// Remove a block by index. O(1). No-op if not alive. Returns true if removed.
    #[inline]
    fn remove(&mut self, block_idx: u32) -> bool {
        let pos = self.pos_of[block_idx as usize] as usize;
        if pos >= self.live as usize { return false; }
        let last = self.live as usize - 1;
        if pos != last {
            let last_idx = self.buf[last];
            self.buf[pos] = last_idx;
            self.pos_of[last_idx as usize] = pos as u32;
            self.buf[last] = block_idx;
            self.pos_of[block_idx as usize] = last as u32;
        }
        self.live -= 1;
        true
    }

    /// Restore the live size (re-activates blocks that were swapped out).
    /// The pos_of/buf relations remain consistent because we never touched them.
    #[inline]
    fn restore_live(&mut self, target: u32) {
        debug_assert!(target >= self.live);
        self.live = target;
    }
}

/// Trail entry encodings:
///   normal: (sr, sc, prev_live) where sr,sc < 8.
///   sentinel piece: (0xFF, piece_id_low, packed) — same as v2.
///   sentinel pinned: (0xFE, sc, sr).
struct State {
    alphabets: Vec<Vec<Vec<Block>>>,
    domain: Vec<Vec<SparseDomain>>,
    pinned: Vec<Vec<bool>>,
    used_pieces: [bool; 256],
    piece_owner: [Option<(u8, u8)>; 256],
    /// piece_occ[p] = Vec of (sr, sc, alphabet_local_idx) where piece p appears.
    piece_occ: Vec<Vec<(u8, u8, u32)>>,
    trail: Vec<(u8, u8, u32)>,
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
        eprintln!("Loaded {} blocks in {:.1}s", total, t0.elapsed().as_secs_f64());

        let t1 = Instant::now();
        let domain: Vec<Vec<SparseDomain>> = (0..SW).map(|sr| {
            (0..SW).map(|sc| SparseDomain::full(alphabets[sr][sc].len() as u32)).collect()
        }).collect();
        eprintln!("Built domain in {:.1}s", t1.elapsed().as_secs_f64());

        let t2 = Instant::now();
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
        eprintln!("Built piece_occ in {:.1}s (total: {})",
                  t2.elapsed().as_secs_f64(),
                  piece_occ.iter().map(|v| v.len()).sum::<usize>());

        State {
            alphabets, domain,
            pinned: vec![vec![false; SW]; SW],
            used_pieces: [false; 256],
            piece_owner: [None; 256],
            piece_occ,
            trail: Vec::with_capacity(2_000_000),
        }
    }

    fn domain_sum(&self) -> u64 {
        let mut s = 0u64;
        for sr in 0..SW { for sc in 0..SW { s += self.domain[sr][sc].len() as u64; } }
        s
    }

    /// Remove block (sr, sc, block_idx) from its cell's domain. Trail the change.
    /// Returns true if it was actually removed.
    #[inline]
    fn remove(&mut self, sr: u8, sc: u8, block_idx: u32) -> bool {
        let d = &mut self.domain[sr as usize][sc as usize];
        if d.pos_of[block_idx as usize] < d.live {
            self.trail.push((sr, sc, d.live));
            d.remove(block_idx);
            true
        } else { false }
    }

    /// Mark piece p as used and owned by (sr, sc). Trail the change.
    /// Note: caller is responsible for removing piece's occurrences from other cells.
    fn mark_piece_used(&mut self, p: u16, sr: u8, sc: u8) {
        let was_used = self.used_pieces[p as usize] as u32;
        let (osr_packed, osc) = match self.piece_owner[p as usize] {
            Some((s, c)) => (s as u32 | 0x80, c as u32),
            None => (0, 0),
        };
        let packed = (p as u32 >> 8) | (was_used << 8) | (osr_packed << 16) | (osc << 24);
        self.trail.push((0xFF, p as u8, packed));
        self.used_pieces[p as usize] = true;
        self.piece_owner[p as usize] = Some((sr, sc));
    }

    /// Pin cell (sr, sc) to alphabet index `block_idx`.
    /// 1. Remove all other blocks from this cell's domain.
    /// 2. Mark cell as pinned.
    /// 3. Mark 4 pieces of this block as used + owned by this cell.
    /// 4. Iterate piece_occ for each piece, removing every (other cell, block) where the piece occurs.
    /// Returns None on wipeout.
    fn pin_and_propagate_pieces(&mut self, sr: usize, sc: usize, block_idx: u32) -> Option<()> {
        // 1) Remove all other blocks from this cell.
        let alphabet_size = self.alphabets[sr][sc].len() as u32;
        // Collect block-ids to remove (those alive in domain other than block_idx).
        let to_remove: Vec<u32> = {
            let d = &self.domain[sr][sc];
            d.iter_live().iter().filter(|&&i| i != block_idx).copied().collect()
        };
        for bi in to_remove {
            self.remove(sr as u8, sc as u8, bi);
        }
        if self.domain[sr][sc].len() == 0 { return None; }

        // 2) Mark cell pinned. Trail it.
        self.trail.push((0xFE, sc as u8, sr as u32));
        self.pinned[sr][sc] = true;

        // 3+4) For each piece, mark used + iterate piece_occ to remove.
        let block = self.alphabets[sr][sc][block_idx as usize];
        for &p in &block.pieces {
            // If already used by SAME cell (e.g., already pinned), skip.
            // (Shouldn't happen in our case; but defensive.)
            if self.used_pieces[p as usize] {
                if self.piece_owner[p as usize] == Some((sr as u8, sc as u8)) {
                    continue;
                } else {
                    return None; // piece claimed by other cell
                }
            }
            self.mark_piece_used(p, sr as u8, sc as u8);
            // Remove (other cell, block) where piece p occurs.
            // Snapshot piece_occ[p] entries (read-only); for each not at our cell,
            // remove the block from that cell's domain.
            let occ_len = self.piece_occ[p as usize].len();
            for k in 0..occ_len {
                let (osr, osc, b_idx) = self.piece_occ[p as usize][k];
                if osr as usize == sr && osc as usize == sc { continue; }
                if self.pinned[osr as usize][osc as usize] {
                    // Should not happen because pinned cell's piece is also marked,
                    // and we already handled them. Just skip.
                    continue;
                }
                self.remove(osr, osc, b_idx);
                if self.domain[osr as usize][osc as usize].len() == 0 {
                    return None;
                }
            }
        }

        Some(())
    }

    /// Incremental boundary AC-3 from a pinned cell: just verify each of its 4
    /// neighbors only contain blocks whose facing-tuple matches the pin's
    /// outgoing-tuple. (Strict equality since this side is fixed.)
    fn boundary_propagate_from_pin(&mut self, sr: usize, sc: usize, block_idx: u32) -> Option<()> {
        let opposite: [usize; 4] = [S, W, N, E];
        let side_dirs: [(isize, isize); 4] = [(-1, 0), (0, 1), (1, 0), (0, -1)];
        let b = self.alphabets[sr][sc][block_idx as usize];
        for side in 0..4 {
            let (dr, dc) = side_dirs[side];
            let nr = sr as isize + dr;
            let nc = sc as isize + dc;
            if nr < 0 || nc < 0 || nr >= SW as isize || nc >= SW as isize { continue; }
            let nbr_r = nr as usize;
            let nbr_c = nc as usize;
            if self.pinned[nbr_r][nbr_c] {
                // Check pinned neighbor's facing side matches.
                let d = &self.domain[nbr_r][nbr_c];
                if d.len() != 1 { continue; }
                let nb_idx = d.buf[0];
                let nb = self.alphabets[nbr_r][nbr_c][nb_idx as usize];
                if nb.edge[opposite[side]] != b.edge[side] {
                    return None; // contradiction
                }
                continue;
            }
            // Filter the neighbor's domain.
            let target_tuple = b.edge[side];
            // Iterate live blocks and remove those whose opposite-side tuple doesn't match.
            let to_remove: Vec<u32> = {
                let d = &self.domain[nbr_r][nbr_c];
                let alphabet = &self.alphabets[nbr_r][nbr_c];
                d.iter_live().iter().copied().filter(|&i| {
                    alphabet[i as usize].edge[opposite[side]] != target_tuple
                }).collect()
            };
            for bi in to_remove {
                self.remove(nbr_r as u8, nbr_c as u8, bi);
            }
            if self.domain[nbr_r][nbr_c].len() == 0 { return None; }
        }
        Some(())
    }

    /// Full boundary AC-3 pass (used at init only). Returns total removed or None.
    fn full_boundary_ac3_pass(&mut self) -> Option<u64> {
        let mut bsets: Vec<Vec<[HashSet<(u8, u8)>; 4]>> =
            (0..SW).map(|_| (0..SW).map(|_| [HashSet::new(), HashSet::new(), HashSet::new(), HashSet::new()]).collect()).collect();
        for sr in 0..SW {
            for sc in 0..SW {
                for &idx in self.domain[sr][sc].iter_live() {
                    let b = self.alphabets[sr][sc][idx as usize];
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
                let to_remove: Vec<u32> = {
                    let d = &self.domain[sr][sc];
                    let alphabet = &self.alphabets[sr][sc];
                    d.iter_live().iter().copied().filter(|&i| {
                        let b = alphabet[i as usize];
                        for s in 0..4 {
                            if let Some(set) = allowed[s] {
                                if !set.contains(&(b.edge[s][0], b.edge[s][1])) {
                                    return true;
                                }
                            }
                        }
                        false
                    }).collect()
                };
                for bi in to_remove {
                    self.remove(sr as u8, sc as u8, bi);
                    removed_total += 1;
                }
                if self.domain[sr][sc].len() == 0 { return None; }
            }
        }
        Some(removed_total)
    }

    /// Full piece-uniqueness pass (used at init after hint). For each marked-used piece,
    /// remove its blocks from non-owner cells.
    fn full_piece_uniqueness_pass(&mut self) -> Option<u64> {
        let mut removed_total: u64 = 0;
        for p in 0..256 {
            if !self.used_pieces[p] { continue; }
            let owner = self.piece_owner[p];
            let occ_len = self.piece_occ[p].len();
            for k in 0..occ_len {
                let (osr, osc, b_idx) = self.piece_occ[p][k];
                if owner == Some((osr, osc)) { continue; }
                if self.pinned[osr as usize][osc as usize] { continue; }
                if self.remove(osr, osc, b_idx) {
                    removed_total += 1;
                    if self.domain[osr as usize][osc as usize].len() == 0 {
                        return None;
                    }
                }
            }
        }
        Some(removed_total)
    }

    fn apply_hints(&mut self, hint_cells: &[(usize, usize, u16)]) -> Option<u64> {
        for &(sr, sc, p) in hint_cells {
            self.mark_piece_used(p, sr as u8, sc as u8);
        }
        self.full_piece_uniqueness_pass()
    }

    fn init_propagate_to_fixpoint(&mut self) -> Option<()> {
        loop {
            let r1 = self.full_boundary_ac3_pass()?;
            let r2 = self.full_piece_uniqueness_pass()?;
            if r1 == 0 && r2 == 0 { return Some(()); }
        }
    }

    fn min_domain_unpinned(&self) -> Option<(usize, usize, u32)> {
        let mut best: Option<(usize, usize, u32)> = None;
        for sr in 0..SW {
            for sc in 0..SW {
                if self.pinned[sr][sc] { continue; }
                let n = self.domain[sr][sc].len();
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
        for sr in 0..SW { for sc in 0..SW { if !self.pinned[sr][sc] { return false; } } }
        true
    }
}

fn rewind_trail(state: &mut State, start: usize) {
    while state.trail.len() > start {
        let (a, b, c) = state.trail.pop().unwrap();
        if a == 0xFF {
            // Piece state restore.
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
            let sc = b as usize;
            let sr = c as usize;
            state.pinned[sr][sc] = false;
        } else {
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
    if *nodes % 100 == 0 {
        let elapsed = t_start.elapsed().as_secs_f64();
        let dom_sum = state.domain_sum();
        let pinned_count: usize = state.pinned.iter().flat_map(|r| r.iter())
            .filter(|&&b| b).count();
        let rate = *nodes as f64 / elapsed;
        eprintln!("[node {}] depth={} pinned={} dom_sum={} elapsed={:.1}s rate={:.1} nodes/s next=({},{}) dom_size={}",
                  *nodes, depth, pinned_count, dom_sum, elapsed, rate, sr, sc, dom_size);
    }
    let candidates: Vec<u32> = state.domain[sr][sc].iter_live().to_vec();
    for cand_idx in candidates {
        let trail_mark = state.trail.len();
        let ok = state.pin_and_propagate_pieces(sr, sc, cand_idx).is_some()
              && state.boundary_propagate_from_pin(sr, sc, cand_idx).is_some();
        if ok {
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
    let mut max_nodes: u64 = 10000;
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--in-dir" => { in_dir = args[i + 1].clone().into(); i += 2; }
            "--max-nodes" => { max_nodes = args[i + 1].parse().unwrap(); i += 2; }
            _ => { eprintln!("Unknown arg: {}", args[i]); std::process::exit(2); }
        }
    }

    eprintln!("=== Super-block BB&B v3 (incremental propagation + O(1) sparse-set) ===");
    let mut state = State::load(&in_dir);
    let init_sum = state.domain_sum();
    eprintln!("Initial domain sum: {}", init_sum);

    let hint_cells: Vec<(usize, usize, u16)> = vec![
        (4, 3, 138), (6, 1, 180), (1, 1, 207), (6, 6, 248), (1, 6, 254),
    ];

    eprintln!("\nApplying hints...");
    let t = Instant::now();
    if state.apply_hints(&hint_cells).is_none() {
        eprintln!("UNSAT applying hints"); return;
    }
    eprintln!("  domain sum after hints: {} (in {:.1}s)",
              state.domain_sum(), t.elapsed().as_secs_f64());

    eprintln!("\nFull AC-3 + uniqueness fixpoint...");
    let t = Instant::now();
    match state.init_propagate_to_fixpoint() {
        Some(()) => {
            eprintln!("  done in {:.1}s, domain sum: {} (reduction: {:.2}x)",
                      t.elapsed().as_secs_f64(), state.domain_sum(),
                      init_sum as f64 / state.domain_sum().max(1) as f64);
        }
        None => { eprintln!("  UNSAT"); return; }
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
                "source": "super_block_bbb_v3"
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
