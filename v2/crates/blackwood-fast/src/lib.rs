// eternity2-blackwood-fast — vol-106 T1
//
// Hyper-optimized Rust port of the Bucas libblackwood backtracker.
// Ports the SHAPE of the C engine (per-cell unrolled DFS with precomputed
// constraint-indexed candidate lists, stack-allocated state) without the
// codegen layer — we use const generics + #[inline(always)] so LLVM
// produces equivalent unrolled code.
//
// Vol-106 design notes:
// - The C engine's `master_lists_of_union_rotated_pieces[ref]` is a 2D
//   table indexed by a packed (top_color, left_color) reference. We
//   replicate it as `RowMajorIndex`. For row-major scan, every interior
//   cell has TWO known neighbours (the cell above and the cell to the
//   left); border cells fall back to a 1-color or 0-color index.
// - The C engine has 256 inlined depth blocks. We loop over depth in a
//   single function; the inner work is `#[inline(always)]` to give LLVM
//   the same inlining opportunity. For canonical 16x16 with 256 depth
//   levels LLVM will not literally unroll, but the inner step is
//   monomorphized on W,H,NPIECES so the per-cell work has zero VTable
//   dispatch, zero bounds checks (with const W*H), and zero allocation.
// - Borders are colored 0. Interior pieces have colors 1..=max_color.
//   A "match" between two adjacent edges means they're equal and != 0.
//   This matches the rest of the workspace.
// - `solve_raw_sized` uses `unsafe { get_unchecked }` for hot-loop bounds
//   elision (precedent: `vanilla_fastest.rs`). All other crates retain
//   `#![forbid(unsafe_code)]`. CLAUDE.md vol-32 authorisation.

#![allow(unsafe_code)]

pub mod schedule;
pub use schedule::{blackwood_schedule_469, blackwood_schedule_calibrated_v17a, compute_heuristic_sides};

use eternity2_core::{Color, PieceId, Puzzle, Rotation, BORDER};

/// A piece + rotation encoded as a single u16 to keep the candidate
/// lists compact. Low 14 bits: piece index (0..NPIECES). High 2 bits:
/// rotation (0..4). NPIECES is capped at 16384 by this encoding.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PieceRot(pub u16);

impl PieceRot {
    pub const NONE: Self = Self(u16::MAX);

    #[must_use]
    #[inline(always)]
    pub const fn new(piece_idx: u16, rot: u8) -> Self {
        Self((piece_idx & 0x3FFF) | ((rot as u16 & 0x3) << 14))
    }

    #[must_use]
    #[inline(always)]
    pub const fn piece_idx(self) -> u16 {
        self.0 & 0x3FFF
    }

    #[must_use]
    #[inline(always)]
    pub const fn rot(self) -> u8 {
        (self.0 >> 14) as u8
    }
}

/// Reference key for row-major candidate index. Packs (top_color, left_color)
/// where each color is a u8, into a u16. top in high byte, left in low byte.
#[must_use]
#[inline(always)]
pub fn ref_key(top: Color, left: Color) -> u16 {
    ((top as u16) << 8) | (left as u16)
}

/// Row-major candidate index. Four separate index tables, one per
/// combination of (right_is_border, bottom_is_border). Inside each
/// table, the same `(top, left)` ref-key partitions the candidate
/// list into a contiguous slice.
///
/// We choose to maintain 4 tables (vs one table + try-time border
/// filter) because the border filter would otherwise live in the
/// inner loop, hitting 94 cells of canonical 16×16 (right column +
/// bottom row, minus shared corner). Materialising 4 tables costs
/// ~4× the offsets array (256 KB vs 64 KB) which is still L2-resident.
/// One flat CSR-style table indexed by an 18-bit key: low 16 bits are
/// `ref_key(top, left)`, high 2 bits encode (right_border, bottom_border).
/// This avoids the `tables[tbl]` indirection on every candidate fetch.
#[derive(Debug, Clone)]
pub struct RowMajorIndex {
    /// `offsets[k]..offsets[k+1]` are the candidate-slice bounds in `entries`
    /// for key k. Length = 4 * 65536 + 1.
    offsets: Vec<u32>,
    entries: Vec<PieceRot>,
    /// Number of pieces in the original puzzle.
    pub n_pieces: u16,
    /// Per-piece-idx, the actual piece edges in 4 rotations (precomputed).
    /// `edges[piece_idx * 4 + rot]` is the rotated edge array [t,r,b,l].
    pub edges: Vec<[Color; 4]>,
    /// Per-piece-idx, the piece_id (for back-translation).
    pub piece_ids: Vec<PieceId>,
    /// Per-PieceRot.0 (u16), the TOP color (for break-index mismatch test).
    pub top_of: Vec<Color>,
    /// Per-PieceRot.0 (u16), the BOTTOM color (for fast top-color lookup
    /// from depth-w board cell).
    pub bottom_of: Vec<Color>,
    /// Per-PieceRot.0 (u16), the LEFT color (for break-index mismatch test).
    pub left_of: Vec<Color>,
    /// Per-PieceRot.0 (u16), the RIGHT color (for fast left-color lookup
    /// from depth-1 board cell).
    pub right_of: Vec<Color>,
    /// Per-PieceRot.0 (u16), the count of heuristic-color edges on
    /// this piece-rotation (0..=4). Populated by `set_heuristic_sides`;
    /// all-zero otherwise (no Blackwood schedule effect).
    pub heur_count_of: Vec<u8>,
    /// Optional 1-mismatch-allowed candidate index. Same shape as
    /// `offsets` / `entries` but each bucket contains piece-rotations
    /// matching EXACTLY ONE of (top_color, left_color). Built on
    /// demand by `build_relaxed_index`. Empty if not built.
    pub relaxed_offsets: Vec<u32>,
    pub relaxed_entries: Vec<PieceRot>,
}

/// Blackwood schedule parameters for `solve_blackwood`.
/// Vol-15-style heuristic-color schedule + break-index allowance.
#[derive(Debug, Clone)]
pub struct BlackwoodSchedule {
    /// Set of edge colors that count toward the exhaustion schedule
    /// (typically 3 colors with the most piece-edge occurrences).
    pub heuristic_sides: Vec<Color>,
    /// Piecewise-linear schedule control points: `(depth, target_count)`,
    /// sorted ascending by depth. The required cumulative count of
    /// placed heuristic-edges at intermediate depths is linearly
    /// interpolated.
    pub exhaustion_targets: Vec<(u32, u32)>,
    /// Maximum depth at which the schedule applies; beyond this, no
    /// schedule check.
    pub max_heuristic_index: u32,
    /// Break-index depths: at these depths, the placement may have
    /// one neighbour-side mismatch instead of strict matching.
    /// Cumulative mismatches across the run cannot exceed the count
    /// of break-indexes reached. Standard set = [201, 206, 211, 216,
    /// 221, 225, 229, 233, 237, 239, 241, 256] for canonical 256-cell.
    /// Empty disables break-index allowance.
    pub break_indexes_allowed: Vec<u32>,
}

impl BlackwoodSchedule {
    /// Target heuristic-piece-occurrence count at `depth`, piecewise-
    /// linear interpolation. Saturates at endpoints.
    #[must_use]
    #[inline]
    pub fn target_at(&self, depth: u32) -> u32 {
        let xs = &self.exhaustion_targets;
        if xs.is_empty() {
            return 0;
        }
        if depth <= xs[0].0 {
            return xs[0].1;
        }
        if depth >= xs[xs.len() - 1].0 {
            return xs[xs.len() - 1].1;
        }
        for w in xs.windows(2) {
            let (d0, c0) = w[0];
            let (d1, c1) = w[1];
            if depth >= d0 && depth <= d1 {
                if d1 == d0 {
                    return c1;
                }
                let span = (d1 - d0) as u64;
                let dc = (c1 as i64) - (c0 as i64);
                let off = (depth - d0) as u64;
                let interp = (c0 as i64) + ((dc * off as i64) / span as i64);
                return interp.max(0) as u32;
            }
        }
        xs[xs.len() - 1].1
    }

    /// Precomputed per-depth target, length WH.
    #[must_use]
    pub fn target_table(&self, wh: usize) -> Vec<u32> {
        (0..wh as u32).map(|d| self.target_at(d)).collect()
    }
}

#[inline(always)]
fn flat_key(tbl: u8, key: u16) -> usize {
    ((tbl as usize) << 16) | (key as usize)
}

impl RowMajorIndex {
    /// Build a row-major candidate index from a puzzle.
    #[must_use]
    pub fn build(puzzle: &Puzzle) -> Self {
        let pieces = puzzle.pieces();
        let n_pieces = pieces.len();
        assert!(n_pieces <= 16384, "blackwood-fast supports up to 16384 pieces");

        let mut edges: Vec<[Color; 4]> = Vec::with_capacity(n_pieces * 4);
        let mut piece_ids: Vec<PieceId> = Vec::with_capacity(n_pieces);
        for p in pieces {
            piece_ids.push(p.id);
            for &r in &Rotation::ALL {
                edges.push(p.edges.rotated(r).as_array());
            }
        }

        // top_of / right_of / bottom_of / left_of indexed by PieceRot.0 (u16).
        let mut top_of: Vec<Color> = vec![0; 1 << 16];
        let mut right_of: Vec<Color> = vec![0; 1 << 16];
        let mut bottom_of: Vec<Color> = vec![0; 1 << 16];
        let mut left_of: Vec<Color> = vec![0; 1 << 16];
        for piece_idx in 0..n_pieces as u16 {
            for rot in 0..4u8 {
                let pr = PieceRot::new(piece_idx, rot);
                let e = edges[(piece_idx as usize) * 4 + rot as usize];
                top_of[pr.0 as usize] = e[0];
                right_of[pr.0 as usize] = e[1];
                bottom_of[pr.0 as usize] = e[2];
                left_of[pr.0 as usize] = e[3];
            }
        }

        const N_FLAT_KEYS: usize = 4 * 65536;
        let mut buckets: Vec<Vec<PieceRot>> = (0..N_FLAT_KEYS).map(|_| Vec::new()).collect();
        for piece_idx in 0..n_pieces {
            for rot in 0..4u8 {
                let e = edges[piece_idx * 4 + rot as usize];
                let right_is_border = e[1] == BORDER;
                let bottom_is_border = e[2] == BORDER;
                let key = ref_key(e[0], e[3]);
                let pr = PieceRot::new(piece_idx as u16, rot);
                buckets[flat_key(0, key)].push(pr);
                if bottom_is_border { buckets[flat_key(1, key)].push(pr); }
                if right_is_border { buckets[flat_key(2, key)].push(pr); }
                if right_is_border && bottom_is_border {
                    buckets[flat_key(3, key)].push(pr);
                }
            }
        }
        // Sentinel-terminate each bucket with PieceRot::NONE so the inner
        // loop walks by pointer until it sees the sentinel — same trick
        // libblackwood uses ("piece_to_try_next->value != 0").
        let mut offsets: Vec<u32> = Vec::with_capacity(N_FLAT_KEYS + 1);
        let mut entries: Vec<PieceRot> = Vec::new();
        offsets.push(0);
        for bucket in &buckets {
            entries.extend_from_slice(bucket);
            entries.push(PieceRot::NONE);
            offsets.push(entries.len() as u32);
        }

        Self {
            offsets,
            entries,
            n_pieces: n_pieces as u16,
            edges,
            piece_ids,
            top_of,
            bottom_of,
            left_of,
            right_of,
            heur_count_of: vec![0; 1 << 16],
            relaxed_offsets: Vec::new(),
            relaxed_entries: Vec::new(),
        }
    }

    /// Build the relaxed candidate index used at break-index depths.
    /// For each (tbl, top, left), the bucket contains piece-rotations
    /// with AT MOST 1 mismatch on (top, left). Includes the strict-match
    /// piece-rotations as a subset (0 mismatches). The conflict cost
    /// (0 or 1) is encoded by the high bit of PieceRot.0 (bit 14, normally
    /// the rotation bit's MSB). We use a separate parallel `conflict_of`
    /// table indexed by the candidate index instead, to keep PieceRot
    /// pristine.
    ///
    /// At call time we pass the puzzle's `color_count` so we only fan
    /// out across actually-used colors, keeping the build at ~O(C^2 *
    /// pieces) instead of O(256^2 * pieces).
    pub fn build_relaxed_index(&mut self, color_count: u32) {
        if !self.relaxed_offsets.is_empty() {
            return;
        }
        let n_colors = color_count.max(2) as u8;
        const N_FLAT_KEYS: usize = 4 * 65536;
        let n_pieces = self.n_pieces as usize;
        let mut buckets: Vec<Vec<PieceRot>> = (0..N_FLAT_KEYS).map(|_| Vec::new()).collect();

        // For each (piece, rot), enumerate (required_top, required_left)
        // pairs where the piece would have AT MOST 1 mismatch.
        // Mismatch options:
        //   (a) 0 mismatch: required_top == p.top && required_left == p.left.
        //   (b) 1 mismatch on top: required_top != p.top, required_left == p.left.
        //   (c) 1 mismatch on left: required_top == p.top, required_left != p.left.
        // Iterate colors 0..n_colors (BORDER + interior).
        for piece_idx in 0..n_pieces {
            for rot in 0..4u8 {
                let e = self.edges[piece_idx * 4 + rot as usize];
                let right_is_border = e[1] == BORDER;
                let bottom_is_border = e[2] == BORDER;
                let pr = PieceRot::new(piece_idx as u16, rot);
                let p_top = e[0];
                let p_left = e[3];

                // (a) Strict match.
                {
                    let key = ref_key(p_top, p_left);
                    let mut push_into = |tbl: u8| { buckets[flat_key(tbl, key)].push(pr); };
                    push_into(0);
                    if bottom_is_border { push_into(1); }
                    if right_is_border { push_into(2); }
                    if right_is_border && bottom_is_border { push_into(3); }
                }
                // (b) 1 mismatch on top.
                for required_top in 0..=n_colors {
                    if required_top == p_top { continue; }
                    let key = ref_key(required_top, p_left);
                    let mut push_into = |tbl: u8| { buckets[flat_key(tbl, key)].push(pr); };
                    push_into(0);
                    if bottom_is_border { push_into(1); }
                    if right_is_border { push_into(2); }
                    if right_is_border && bottom_is_border { push_into(3); }
                }
                // (c) 1 mismatch on left.
                for required_left in 0..=n_colors {
                    if required_left == p_left { continue; }
                    let key = ref_key(p_top, required_left);
                    let mut push_into = |tbl: u8| { buckets[flat_key(tbl, key)].push(pr); };
                    push_into(0);
                    if bottom_is_border { push_into(1); }
                    if right_is_border { push_into(2); }
                    if right_is_border && bottom_is_border { push_into(3); }
                }
            }
        }

        let mut offsets: Vec<u32> = Vec::with_capacity(N_FLAT_KEYS + 1);
        let mut entries: Vec<PieceRot> = Vec::new();
        offsets.push(0);
        for bucket in &buckets {
            entries.extend_from_slice(bucket);
            entries.push(PieceRot::NONE);
            offsets.push(entries.len() as u32);
        }
        self.relaxed_offsets = offsets;
        self.relaxed_entries = entries;
    }

    #[must_use]
    #[inline(always)]
    pub fn relaxed_candidates(&self, tbl: usize, key: u16) -> &[PieceRot] {
        let k = (tbl << 16) | (key as usize);
        let lo = self.relaxed_offsets[k] as usize;
        let hi = self.relaxed_offsets[k + 1] as usize;
        &self.relaxed_entries[lo..hi - 1]
    }

    /// Fisher-Yates shuffle within each bucket. Sentinels are preserved
    /// (the last slot of each bucket stays PieceRot::NONE). Used to
    /// diversify per-thread search ordering with `seed` as the RNG seed.
    /// `seed == 0` is a no-op (the global rare-first order is preserved).
    pub fn shuffle_buckets(&mut self, seed: u64) {
        if seed == 0 {
            return;
        }
        let mut state: u64 = seed
            .wrapping_mul(0x9E37_79B9_7F4A_7C15)
            .wrapping_add(0xDEAD_BEEF_CAFE_BABE);
        let mut next = |s: &mut u64| -> u64 {
            *s ^= *s << 13;
            *s ^= *s >> 7;
            *s ^= *s << 17;
            *s
        };
        Self::shuffle_csr(&self.offsets, &mut self.entries, &mut state, &mut next);
        if !self.relaxed_offsets.is_empty() {
            Self::shuffle_csr(&self.relaxed_offsets, &mut self.relaxed_entries, &mut state, &mut next);
        }
    }

    fn shuffle_csr(
        offsets: &[u32],
        entries: &mut [PieceRot],
        state: &mut u64,
        next: &mut dyn FnMut(&mut u64) -> u64,
    ) {
        for k in 0..offsets.len() - 1 {
            let lo = offsets[k] as usize;
            let hi = offsets[k + 1] as usize;
            // last slot is the sentinel; shuffle [lo, hi-1)
            let len = hi.saturating_sub(lo + 1);
            if len <= 1 {
                continue;
            }
            for i in (1..len).rev() {
                let j = (next(state) as usize) % (i + 1);
                entries.swap(lo + i, lo + j);
            }
        }
    }

    /// Populate `heur_count_of` from a set of heuristic colors. Counts
    /// for each (piece, rotation) how many of its 4 edges are in
    /// `heuristic_sides`. Call after `build` if you want to use
    /// `solve_blackwood`.
    pub fn set_heuristic_sides(&mut self, heuristic_sides: &[Color]) {
        // Reset.
        for v in self.heur_count_of.iter_mut() {
            *v = 0;
        }
        // Bitset of heuristic colors for O(1) membership.
        let mut is_heur: [bool; 256] = [false; 256];
        for &c in heuristic_sides {
            is_heur[c as usize] = true;
        }
        for piece_idx in 0..self.n_pieces as u16 {
            for rot in 0..4u8 {
                let pr = PieceRot::new(piece_idx, rot);
                let e = self.edges[(piece_idx as usize) * 4 + rot as usize];
                let mut c = 0u8;
                for &col in &e {
                    if col != BORDER && is_heur[col as usize] {
                        c += 1;
                    }
                }
                self.heur_count_of[pr.0 as usize] = c;
            }
        }
    }

    /// Return the candidate slice for the given (border-flags, ref_key).
    /// `tbl` encodes border requirements: 0=none, 1=bottom, 2=right, 3=both.
    /// Excludes the trailing sentinel (PieceRot::NONE).
    #[must_use]
    #[inline(always)]
    pub fn candidates(&self, tbl: usize, key: u16) -> &[PieceRot] {
        let k = ((tbl) << 16) | (key as usize);
        let lo = self.offsets[k] as usize;
        let hi = self.offsets[k + 1] as usize;
        // hi - 1 excludes the sentinel; hi - 1 ≥ lo always because every
        // bucket got at least the sentinel pushed.
        &self.entries[lo..hi - 1]
    }

    /// Lookup the rotated edges for (piece_idx, rot).
    #[must_use]
    #[inline(always)]
    pub fn rotated_edges(&self, piece_idx: u16, rot: u8) -> [Color; 4] {
        self.edges[piece_idx as usize * 4 + rot as usize]
    }
}

/// Counter of nodes visited so we can report nps.
#[derive(Debug, Clone, Default)]
pub struct SearchStats {
    pub nodes: u64,
    pub max_depth: u32,
    pub solved: bool,
    /// Matched edges of the deepest (best-seen) board, if recovered.
    /// 0 when not computed.
    pub best_score: u32,
}

/// Score a (PieceId, Rotation) board by counting adjacent edge matches
/// across all internal edges. Uses the puzzle to look up each piece's
/// rotated edges. Border edges are not counted as matches (BORDER
/// is reserved color 0).
pub fn score_board(puzzle: &Puzzle, board: &[(PieceId, Rotation)]) -> u32 {
    let w = puzzle.width as usize;
    let h = puzzle.height as usize;
    let wh = w * h;
    debug_assert_eq!(board.len(), wh);
    // Cache rotated edges per cell.
    let mut edges_at: Vec<[Color; 4]> = Vec::with_capacity(wh);
    for &(id, rot) in board {
        if let Some(p) = puzzle.piece(id) {
            edges_at.push(p.edges.rotated(rot).as_array());
        } else {
            edges_at.push([0; 4]);
        }
    }
    let mut matched: u32 = 0;
    for y in 0..h {
        for x in 0..w {
            let p = y * w + x;
            let e = edges_at[p];
            // Right edge
            if x + 1 < w {
                let er = edges_at[p + 1];
                if e[1] != BORDER && e[1] == er[3] {
                    matched += 1;
                }
            }
            // Bottom edge
            if y + 1 < h {
                let eb = edges_at[p + w];
                if e[2] != BORDER && e[2] == eb[0] {
                    matched += 1;
                }
            }
        }
    }
    matched
}

/// Run the raw row-major Blackwood-style backtracker. The puzzle must
/// be N×N with N*N pieces (matches the `Puzzle::new` invariant).
/// `time_budget_us` is the cooperative cutoff (checked once every
/// `STATS_CHECK_INTERVAL` nodes). Returns a copy of the deepest board
/// reached.
pub fn solve_raw(
    puzzle: &Puzzle,
    time_budget_us: u64,
) -> (SearchStats, Vec<(PieceId, Rotation)>) {
    let index = RowMajorIndex::build(puzzle);
    // For canonical 16x16 (WH=256, NPIECES=256) we dispatch to the
    // monomorphized const-generic specialization. For other sizes we use
    // the generic runtime-sized version.
    if puzzle.width == 16 && puzzle.height == 16 && index.n_pieces == 256 {
        return solve_raw_sized::<256, 256, 4>(&index, time_budget_us);
    }
    solve_raw_generic(&index, puzzle, time_budget_us)
}

fn solve_raw_generic(
    index: &RowMajorIndex,
    puzzle: &Puzzle,
    time_budget_us: u64,
) -> (SearchStats, Vec<(PieceId, Rotation)>) {
    let w = puzzle.width as usize;
    let h = puzzle.height as usize;
    let wh = w * h;
    let n_pieces = index.n_pieces as usize;
    assert!(n_pieces <= 4096, "pieces_used bitset capped at 4096 pieces");

    let bitset_words = (n_pieces + 63) / 64;
    let mut pieces_used: Vec<u64> = vec![0; bitset_words];

    let mut board: Vec<PieceRot> = vec![PieceRot::NONE; wh];
    let mut best_board: Vec<PieceRot> = vec![PieceRot::NONE; wh];
    let mut cursor: Vec<u32> = vec![0; wh];
    let mut depth_meta: Vec<(u8, u8, u8, bool, bool)> = Vec::with_capacity(wh);
    for d in 0..wh {
        let x = (d % w) as u8;
        let y = (d / w) as u8;
        let need_bottom = (y as usize) == h - 1;
        let need_right = (x as usize) == w - 1;
        let tbl = ((need_right as u8) << 1) | (need_bottom as u8);
        depth_meta.push((tbl, x, y, y == 0, x == 0));
    }

    let mut stats = SearchStats::default();
    let start = eternity2_time::Clock::now();

    let mut depth: usize = 0;

    'outer: loop {
        if (stats.nodes & 0xFFFF) == 0 && start.elapsed_us() > time_budget_us {
            break 'outer;
        }

        if depth == wh {
            stats.solved = true;
            stats.max_depth = wh as u32;
            break 'outer;
        }

        let (tbl, _x, _y, is_top_row, is_left_col) = depth_meta[depth];
        // top_color from depth - w's bottom_of (or BORDER if top row).
        let top_color: Color = if is_top_row {
            BORDER
        } else {
            index.bottom_of[board[depth - w].0 as usize]
        };
        let left_color: Color = if is_left_col {
            BORDER
        } else {
            index.right_of[board[depth - 1].0 as usize]
        };
        let key = ref_key(top_color, left_color);
        let cands = index.candidates(tbl as usize, key);

        let mut placed = false;
        let mut c_idx = cursor[depth] as usize;
        while c_idx < cands.len() {
            let pr = cands[c_idx];
            c_idx += 1;
            let piece_idx = pr.piece_idx() as usize;
            let word = piece_idx >> 6;
            let bit = 1u64 << (piece_idx & 63);
            if (pieces_used[word] & bit) != 0 {
                continue;
            }
            // Place.
            pieces_used[word] |= bit;
            board[depth] = pr;
            cursor[depth] = c_idx as u32;
            stats.nodes += 1;
            if (depth as u32 + 1) > stats.max_depth {
                stats.max_depth = depth as u32 + 1;
                best_board.copy_from_slice(&board);
            }
            depth += 1;
            if depth < wh {
                cursor[depth] = 0;
            }
            placed = true;
            break;
        }

        if !placed {
            cursor[depth] = 0;
            if depth == 0 {
                break 'outer;
            }
            depth -= 1;
            let pr = board[depth];
            let piece_idx = pr.piece_idx() as usize;
            pieces_used[piece_idx >> 6] &= !(1u64 << (piece_idx & 63));
            board[depth] = PieceRot::NONE;
        }
    }

    let out = board_to_out(index, &best_board);
    (stats, out)
}

#[inline]
fn board_to_out(index: &RowMajorIndex, board: &[PieceRot]) -> Vec<(PieceId, Rotation)> {
    board
        .iter()
        .map(|pr| {
            if pr.0 == PieceRot::NONE.0 {
                (PieceId::MAX, Rotation::R0)
            } else {
                (
                    index.piece_ids[pr.piece_idx() as usize],
                    Rotation::from_u8(pr.rot()).unwrap_or(Rotation::R0),
                )
            }
        })
        .collect()
}

/// Const-generic specialization of the inner DFS loop. `WH` is total
/// cells (width × height), `NPIECES` the piece count, `BITSET_WORDS`
/// is `ceil(NPIECES / 64)`. Stack-allocates all state.
///
/// Currently dispatched from `solve_raw` for canonical 16×16 with 256
/// pieces (constants 256, 256, 4). The width must equal sqrt(WH); this
/// version assumes square boards.
fn solve_raw_sized<const WH: usize, const NPIECES: usize, const BITSET_WORDS: usize>(
    index: &RowMajorIndex,
    time_budget_us: u64,
) -> (SearchStats, Vec<(PieceId, Rotation)>) {
    // We only call this for square boards.
    let w: usize = (WH as f64).sqrt() as usize;
    debug_assert_eq!(w * w, WH, "WH must be a perfect square");
    let h = w;

    let mut pieces_used: [u64; BITSET_WORDS] = [0; BITSET_WORDS];
    let mut board: [PieceRot; WH] = [PieceRot::NONE; WH];
    let mut cursor: [u32; WH] = [0; WH];

    let mut depth_tbl: [u8; WH] = [0; WH];
    let mut depth_top_row: [bool; WH] = [false; WH];
    let mut depth_left_col: [bool; WH] = [false; WH];
    for d in 0..WH {
        let x = d % w;
        let y = d / w;
        depth_tbl[d] = (((x == w - 1) as u8) << 1) | ((y == h - 1) as u8);
        depth_top_row[d] = y == 0;
        depth_left_col[d] = x == 0;
    }

    let mut stats = SearchStats::default();
    let start = eternity2_time::Clock::now();
    let mut depth: usize = 0;

    // Raw pointers / lengths for the index. We've validated bounds at
    // build-time and at each access via the bounds-checked test path.
    let offsets_ptr = index.offsets.as_ptr();
    let entries_ptr = index.entries.as_ptr();
    let bottom_ptr = index.bottom_of.as_ptr();
    let right_ptr = index.right_of.as_ptr();

    'outer: loop {
        if (stats.nodes & 0xFFFF) == 0 && start.elapsed_us() > time_budget_us {
            break 'outer;
        }
        if depth == WH {
            stats.solved = true;
            stats.max_depth = WH as u32;
            break 'outer;
        }

        // SAFETY: depth < WH on this path; depth_* arrays sized WH.
        let tbl = unsafe { *depth_tbl.get_unchecked(depth) } as usize;
        let top_color: Color = if unsafe { *depth_top_row.get_unchecked(depth) } {
            BORDER
        } else {
            // SAFETY: depth >= w on this path (not top row); board sized WH.
            let nbr = unsafe { *board.get_unchecked(depth - w) };
            // SAFETY: bottom_of is sized 65536 (full u16 range); nbr.0 is u16.
            unsafe { *bottom_ptr.add(nbr.0 as usize) }
        };
        let left_color: Color = if unsafe { *depth_left_col.get_unchecked(depth) } {
            BORDER
        } else {
            let nbr = unsafe { *board.get_unchecked(depth - 1) };
            unsafe { *right_ptr.add(nbr.0 as usize) }
        };
        let key = ref_key(top_color, left_color);
        let flat = (tbl << 16) | (key as usize);
        // SAFETY: offsets sized 4*65536+1; flat ≤ 4*65536 - 1.
        let lo = unsafe { *offsets_ptr.add(flat) } as usize;
        // Resume from the cursor offset within this slice.
        let mut c_idx = lo + unsafe { *cursor.get_unchecked(depth) } as usize;

        // Sentinel-terminated walk: each candidate slice ends with
        // PieceRot::NONE. We walk by index until we hit it.
        let mut placed = false;
        loop {
            // SAFETY: entries always ends with at least one sentinel per
            // bucket; we cannot walk past the sentinel without `break`ing.
            let pr = unsafe { *entries_ptr.add(c_idx) };
            if pr.0 == PieceRot::NONE.0 {
                break;
            }
            c_idx += 1;
            let piece_idx = pr.piece_idx() as usize;
            let word = piece_idx >> 6;
            let bit = 1u64 << (piece_idx & 63);
            if (unsafe { *pieces_used.get_unchecked(word) } & bit) != 0 {
                continue;
            }
            unsafe { *pieces_used.get_unchecked_mut(word) |= bit; }
            unsafe { *board.get_unchecked_mut(depth) = pr; }
            unsafe { *cursor.get_unchecked_mut(depth) = (c_idx - lo) as u32; }
            stats.nodes += 1;
            if (depth as u32 + 1) > stats.max_depth {
                stats.max_depth = depth as u32 + 1;
            }
            depth += 1;
            if depth < WH {
                unsafe { *cursor.get_unchecked_mut(depth) = 0; }
            }
            placed = true;
            break;
        }

        if !placed {
            unsafe { *cursor.get_unchecked_mut(depth) = 0; }
            if depth == 0 {
                break 'outer;
            }
            depth -= 1;
            let pr = unsafe { *board.get_unchecked(depth) };
            let piece_idx = pr.piece_idx() as usize;
            unsafe {
                *pieces_used.get_unchecked_mut(piece_idx >> 6) &= !(1u64 << (piece_idx & 63));
                *board.get_unchecked_mut(depth) = PieceRot::NONE;
            }
        }
    }

    let out = board_to_out(index, &board);
    (stats, out)
}

/// Run the Blackwood-schedule-constrained backtracker on canonical
/// 16×16 / 256-piece. Requires `index.heur_count_of` to be set via
/// `set_heuristic_sides`. Branches that fall behind the schedule's
/// `target_at(depth)` are pruned by skipping the candidate.
///
/// Returns (stats, board, best_depth_seen). Currently no break-index
/// allowance; that's vol-107 T1.
/// Multi-thread variant. Spawns `n_threads` worker threads. Worker 0
/// uses the global rare-first ordering; workers 1..n use a per-thread
/// Fisher-Yates shuffle of the candidate lists seeded by thread_id.
/// Returns the BEST board (deepest max_depth) across workers.
pub fn solve_blackwood_par(
    puzzle: &Puzzle,
    schedule: &BlackwoodSchedule,
    n_threads: usize,
    time_budget_us: u64,
) -> (SearchStats, Vec<(PieceId, Rotation)>) {
    solve_blackwood_par_offset(puzzle, schedule, n_threads, 0, time_budget_us)
}

/// Vol-106 T13.c — like `solve_blackwood_par` but with a `seed_offset`
/// added to each thread's bucket-shuffle seed. Lets us sweep different
/// search basins by varying the offset (instead of always exploring
/// seeds 0..n_threads-1).
pub fn solve_blackwood_par_offset(
    puzzle: &Puzzle,
    schedule: &BlackwoodSchedule,
    n_threads: usize,
    seed_offset: u64,
    time_budget_us: u64,
) -> (SearchStats, Vec<(PieceId, Rotation)>) {
    use rayon::prelude::*;
    let mut base_index = RowMajorIndex::build(puzzle);
    base_index.set_heuristic_sides(&schedule.heuristic_sides);
    if !schedule.break_indexes_allowed.is_empty() {
        base_index.build_relaxed_index(puzzle.color_count);
    }
    let targets = schedule.target_table(puzzle.cell_count() as usize);
    let wh = puzzle.cell_count() as usize;
    let mut conflicts_allowed: Vec<u32> = vec![0; wh];
    let mut budget = 0u32;
    let break_set: std::collections::HashSet<u32> =
        schedule.break_indexes_allowed.iter().copied().collect();
    for d in 0..wh as u32 {
        if break_set.contains(&d) {
            budget += 1;
        }
        conflicts_allowed[d as usize] = budget;
    }

    let results: Vec<(SearchStats, Vec<(PieceId, Rotation)>)> = (0..n_threads)
        .into_par_iter()
        .map(|tid| {
            let mut idx = base_index.clone();
            idx.shuffle_buckets(seed_offset + tid as u64);
            if puzzle.width == 16 && puzzle.height == 16 && idx.n_pieces == 256 {
                solve_blackwood_sized::<256, 256, 4>(
                    &idx,
                    &targets,
                    schedule.max_heuristic_index,
                    &conflicts_allowed,
                    time_budget_us,
                )
            } else {
                solve_raw_generic(&idx, puzzle, time_budget_us)
            }
        })
        .collect();

    // Pick the deepest result.
    let best = results.into_iter().max_by_key(|(s, _)| s.max_depth).unwrap();
    best
}

/// Vol-106 T10 — multi-thread variant returning ALL per-thread results
/// for analysis (e.g., measuring cross-worker board similarity to gauge
/// whether cooperative-frontier-hashing would pay off).
pub fn solve_blackwood_par_all(
    puzzle: &Puzzle,
    schedule: &BlackwoodSchedule,
    n_threads: usize,
    time_budget_us: u64,
) -> Vec<(SearchStats, Vec<(PieceId, Rotation)>)> {
    use rayon::prelude::*;
    let mut base_index = RowMajorIndex::build(puzzle);
    base_index.set_heuristic_sides(&schedule.heuristic_sides);
    if !schedule.break_indexes_allowed.is_empty() {
        base_index.build_relaxed_index(puzzle.color_count);
    }
    let targets = schedule.target_table(puzzle.cell_count() as usize);
    let wh = puzzle.cell_count() as usize;
    let mut conflicts_allowed: Vec<u32> = vec![0; wh];
    let mut budget = 0u32;
    let break_set: std::collections::HashSet<u32> =
        schedule.break_indexes_allowed.iter().copied().collect();
    for d in 0..wh as u32 {
        if break_set.contains(&d) {
            budget += 1;
        }
        conflicts_allowed[d as usize] = budget;
    }
    (0..n_threads)
        .into_par_iter()
        .map(|tid| {
            let mut idx = base_index.clone();
            idx.shuffle_buckets(tid as u64);
            if puzzle.width == 16 && puzzle.height == 16 && idx.n_pieces == 256 {
                solve_blackwood_sized::<256, 256, 4>(
                    &idx,
                    &targets,
                    schedule.max_heuristic_index,
                    &conflicts_allowed,
                    time_budget_us,
                )
            } else {
                solve_raw_generic(&idx, puzzle, time_budget_us)
            }
        })
        .collect()
}

/// Vol-106 T10 — measure pairwise board similarity across N workers.
/// Returns a (N×N) matrix `sim[i][j]` = number of cells where worker i
/// and worker j agree (same piece_id + rotation). Diagonal entries
/// are each worker's max_depth.
#[must_use]
pub fn pairwise_similarity(boards: &[Vec<(PieceId, Rotation)>]) -> Vec<Vec<u32>> {
    let n = boards.len();
    let mut sim = vec![vec![0u32; n]; n];
    for i in 0..n {
        for j in 0..n {
            if i == j {
                // Count placed cells (piece_id != MAX = sentinel for unplaced).
                sim[i][j] = boards[i].iter().filter(|(p, _)| *p != PieceId::MAX).count() as u32;
            } else {
                let mut agree = 0u32;
                for (a, b) in boards[i].iter().zip(boards[j].iter()) {
                    if a == b && a.0 != PieceId::MAX {
                        agree += 1;
                    }
                }
                sim[i][j] = agree;
            }
        }
    }
    sim
}

pub fn solve_blackwood(
    puzzle: &Puzzle,
    schedule: &BlackwoodSchedule,
    time_budget_us: u64,
) -> (SearchStats, Vec<(PieceId, Rotation)>) {
    let mut index = RowMajorIndex::build(puzzle);
    index.set_heuristic_sides(&schedule.heuristic_sides);
    if !schedule.break_indexes_allowed.is_empty() {
        index.build_relaxed_index(puzzle.color_count);
    }
    if puzzle.width == 16 && puzzle.height == 16 && index.n_pieces == 256 {
        let targets = schedule.target_table(256);
        // Build per-depth conflicts_allowed table: count of break-indexes
        // at depth ≤ d. At each break-index, budget grows by 1.
        let wh = 256usize;
        let mut conflicts_allowed: Vec<u32> = vec![0; wh];
        let mut budget = 0u32;
        let break_set: std::collections::HashSet<u32> =
            schedule.break_indexes_allowed.iter().copied().collect();
        for d in 0..wh as u32 {
            if break_set.contains(&d) {
                budget += 1;
            }
            conflicts_allowed[d as usize] = budget;
        }
        // Vol-106 T12 — env var to opt into the proc-macro-unrolled
        // variant. Set E2_BF_UNROLLED=1 to use.
        if std::env::var("E2_BF_UNROLLED").as_deref() == Ok("1") {
            return solve_blackwood_unrolled_256(
                &index,
                &targets,
                schedule.max_heuristic_index,
                &conflicts_allowed,
                time_budget_us,
            );
        }
        return solve_blackwood_sized::<256, 256, 4>(
            &index,
            &targets,
            schedule.max_heuristic_index,
            &conflicts_allowed,
            time_budget_us,
        );
    }
    solve_raw_generic(&index, puzzle, time_budget_us)
}

fn solve_blackwood_sized<const WH: usize, const NPIECES: usize, const BITSET_WORDS: usize>(
    index: &RowMajorIndex,
    targets: &[u32],
    max_heuristic_index: u32,
    conflicts_allowed: &[u32],
    time_budget_us: u64,
) -> (SearchStats, Vec<(PieceId, Rotation)>) {
    let w: usize = (WH as f64).sqrt() as usize;
    debug_assert_eq!(w * w, WH);
    let h = w;
    // Compile-time-known w for the canonical 16x16 specialisation
    // (WH == 256). Hot loop uses these directly for cheap bitmask
    // depth-meta computation.
    const W_CANONICAL: usize = 16;
    let canonical = WH == 256;

    let mut pieces_used: [u64; BITSET_WORDS] = [0; BITSET_WORDS];
    let mut board: [PieceRot; WH] = [PieceRot::NONE; WH];
    let mut best_board: [PieceRot; WH] = [PieceRot::NONE; WH];
    let mut cursor: [u32; WH] = [0; WH];
    let mut cum: [u32; WH] = [0; WH];
    // Cumulative conflicts (mismatches placed) at each depth.
    let mut conf: [u32; WH] = [0; WH];

    // Vol-106 T11 — depth-meta tables retained for non-canonical sizes;
    // canonical 16x16 path computes them inline from depth (cheaper).
    let mut depth_tbl: [u8; WH] = [0; WH];
    let mut depth_top_row: [bool; WH] = [false; WH];
    let mut depth_left_col: [bool; WH] = [false; WH];
    for d in 0..WH {
        let x = d % w;
        let y = d / w;
        depth_tbl[d] = (((x == w - 1) as u8) << 1) | ((y == h - 1) as u8);
        depth_top_row[d] = y == 0;
        depth_left_col[d] = x == 0;
    }

    let mut stats = SearchStats::default();
    let start = eternity2_time::Clock::now();
    let mut depth: usize = 0;

    let strict_offsets_ptr = index.offsets.as_ptr();
    let strict_entries_ptr = index.entries.as_ptr();
    let relaxed_offsets_ptr = if index.relaxed_offsets.is_empty() {
        std::ptr::null()
    } else {
        index.relaxed_offsets.as_ptr()
    };
    let relaxed_entries_ptr = if index.relaxed_entries.is_empty() {
        std::ptr::null()
    } else {
        index.relaxed_entries.as_ptr()
    };
    let top_ptr = index.top_of.as_ptr();
    let bottom_ptr = index.bottom_of.as_ptr();
    let left_ptr = index.left_of.as_ptr();
    let right_ptr = index.right_of.as_ptr();
    let heur_ptr = index.heur_count_of.as_ptr();
    let targets_ptr = targets.as_ptr();
    let conf_alw_ptr = conflicts_allowed.as_ptr();

    'outer: loop {
        if (stats.nodes & 0xFFFF) == 0 && start.elapsed_us() > time_budget_us {
            break 'outer;
        }
        if depth == WH {
            stats.solved = true;
            stats.max_depth = WH as u32;
            break 'outer;
        }

        // Vol-106 T11 unrolling — compute depth-meta inline using
        // bitmask arithmetic on the compile-time-constant W=16
        // (when canonical). Eliminates 3 LUT reads per node.
        let (tbl, is_top_row, is_left_col) = if canonical {
            // depth/16 = row, depth%16 = col. Use shifts/masks for cheap codegen.
            let row = depth >> 4;
            let col = depth & 0xF;
            let is_bottom_row = row == W_CANONICAL - 1;
            let is_right_col = col == W_CANONICAL - 1;
            let tbl = ((is_right_col as usize) << 1) | (is_bottom_row as usize);
            (tbl, row == 0, col == 0)
        } else {
            let t = unsafe { *depth_tbl.get_unchecked(depth) } as usize;
            let tr = unsafe { *depth_top_row.get_unchecked(depth) };
            let lc = unsafe { *depth_left_col.get_unchecked(depth) };
            (t, tr, lc)
        };

        let top_color: Color = if is_top_row {
            BORDER
        } else {
            let nbr = unsafe { *board.get_unchecked(depth - w) };
            unsafe { *bottom_ptr.add(nbr.0 as usize) }
        };
        let left_color: Color = if is_left_col {
            BORDER
        } else {
            let nbr = unsafe { *board.get_unchecked(depth - 1) };
            unsafe { *right_ptr.add(nbr.0 as usize) }
        };
        let key = ref_key(top_color, left_color);
        let flat = (tbl << 16) | (key as usize);

        // Choose strict vs relaxed list. We use relaxed only when:
        // (1) relaxed index was built, (2) conflicts_allowed[depth] > 0
        //     (some break-index has been crossed), (3) we still have
        //     budget at this depth (prev_conf < allowed).
        let allowed_here = unsafe { *conf_alw_ptr.add(depth) };
        let prev_conf = if depth == 0 { 0 } else { unsafe { *conf.get_unchecked(depth - 1) } };
        let use_relaxed = !relaxed_offsets_ptr.is_null()
            && allowed_here > 0
            && prev_conf < allowed_here;
        let (lo, list_ptr) = if use_relaxed {
            let lo = unsafe { *relaxed_offsets_ptr.add(flat) } as usize;
            (lo, relaxed_entries_ptr)
        } else {
            let lo = unsafe { *strict_offsets_ptr.add(flat) } as usize;
            (lo, strict_entries_ptr)
        };
        let mut c_idx = lo + unsafe { *cursor.get_unchecked(depth) } as usize;

        // Schedule target for the post-placement depth (depth+1).
        let post_depth = (depth as u32) + 1;
        let schedule_active = post_depth <= max_heuristic_index;
        let target = if schedule_active {
            unsafe { *targets_ptr.add(post_depth as usize - 1) }
        } else {
            0
        };
        let prev_cum = if depth == 0 { 0 } else { unsafe { *cum.get_unchecked(depth - 1) } };

        let mut placed = false;
        loop {
            let pr = unsafe { *list_ptr.add(c_idx) };
            if pr.0 == PieceRot::NONE.0 {
                break;
            }
            c_idx += 1;
            let piece_idx = pr.piece_idx() as usize;
            let word = piece_idx >> 6;
            let bit = 1u64 << (piece_idx & 63);
            if (unsafe { *pieces_used.get_unchecked(word) } & bit) != 0 {
                continue;
            }

            // Conflict count for this candidate at this position.
            // For row-major scan: conflict = (piece.top != required_top)
            // + (piece.left != required_left). Strict list always gives 0;
            // relaxed list gives 0 or 1.
            let candidate_conf = if use_relaxed {
                let p_top = unsafe { *top_ptr.add(pr.0 as usize) };
                let p_left = unsafe { *left_ptr.add(pr.0 as usize) };
                ((p_top != top_color) as u32) + ((p_left != left_color) as u32)
            } else {
                0
            };
            let new_conf = prev_conf + candidate_conf;
            if new_conf > allowed_here {
                continue;
            }

            // Heuristic-schedule pruning.
            if schedule_active {
                let new_cum = prev_cum + unsafe { *heur_ptr.add(pr.0 as usize) } as u32;
                if new_cum < target {
                    continue;
                }
                unsafe { *cum.get_unchecked_mut(depth) = new_cum; }
            } else {
                unsafe { *cum.get_unchecked_mut(depth) = prev_cum; }
            }
            unsafe { *conf.get_unchecked_mut(depth) = new_conf; }
            unsafe { *pieces_used.get_unchecked_mut(word) |= bit; }
            unsafe { *board.get_unchecked_mut(depth) = pr; }
            unsafe { *cursor.get_unchecked_mut(depth) = (c_idx - lo) as u32; }
            stats.nodes += 1;
            if (depth as u32 + 1) > stats.max_depth {
                stats.max_depth = depth as u32 + 1;
                // Snapshot the deepest board seen so we can report its score.
                best_board.copy_from_slice(&board);
            }
            depth += 1;
            if depth < WH {
                unsafe { *cursor.get_unchecked_mut(depth) = 0; }
            }
            placed = true;
            break;
        }

        if !placed {
            unsafe { *cursor.get_unchecked_mut(depth) = 0; }
            if depth == 0 {
                break 'outer;
            }
            depth -= 1;
            let pr = unsafe { *board.get_unchecked(depth) };
            let piece_idx = pr.piece_idx() as usize;
            unsafe {
                *pieces_used.get_unchecked_mut(piece_idx >> 6) &= !(1u64 << (piece_idx & 63));
                *board.get_unchecked_mut(depth) = PieceRot::NONE;
            }
        }
    }

    let out = board_to_out(index, &best_board);
    (stats, out)
}

/// Vol-106 T12 — proc-macro-unrolled variant of `solve_blackwood_sized`
/// for canonical 16×16. Uses `depth_dispatch_256!` from the codegen
/// crate to emit 256 distinct per-depth match arms with the literal
/// depth value baked in as constants where helpful.
///
/// Currently only canonical W=16 is supported (`WH=256`).
fn solve_blackwood_unrolled_256(
    index: &RowMajorIndex,
    targets: &[u32],
    max_heuristic_index: u32,
    conflicts_allowed: &[u32],
    time_budget_us: u64,
) -> (SearchStats, Vec<(PieceId, Rotation)>) {
    use eternity2_blackwood_fast_codegen::depth_dispatch_256;
    const WH: usize = 256;
    const W: usize = 16;
    const H: usize = 16;
    const NPIECES: usize = 256;
    const BITSET_WORDS: usize = 4;

    let mut pieces_used: [u64; BITSET_WORDS] = [0; BITSET_WORDS];
    let mut board: [PieceRot; WH] = [PieceRot::NONE; WH];
    let mut best_board: [PieceRot; WH] = [PieceRot::NONE; WH];
    let mut cursor: [u32; WH] = [0; WH];
    let mut cum: [u32; WH] = [0; WH];
    let mut conf: [u32; WH] = [0; WH];

    let mut stats = SearchStats::default();
    let start = eternity2_time::Clock::now();
    let mut depth: usize = 0;

    let strict_offsets_ptr = index.offsets.as_ptr();
    let strict_entries_ptr = index.entries.as_ptr();
    let relaxed_offsets_ptr = if index.relaxed_offsets.is_empty() {
        std::ptr::null()
    } else {
        index.relaxed_offsets.as_ptr()
    };
    let relaxed_entries_ptr = if index.relaxed_entries.is_empty() {
        std::ptr::null()
    } else {
        index.relaxed_entries.as_ptr()
    };
    let top_ptr = index.top_of.as_ptr();
    let bottom_ptr = index.bottom_of.as_ptr();
    let left_ptr = index.left_of.as_ptr();
    let right_ptr = index.right_of.as_ptr();
    let heur_ptr = index.heur_count_of.as_ptr();
    let targets_ptr = targets.as_ptr();
    let conf_alw_ptr = conflicts_allowed.as_ptr();

    'outer: loop {
        if (stats.nodes & 0xFFFF) == 0 && start.elapsed_us() > time_budget_us {
            break 'outer;
        }
        if depth == WH {
            stats.solved = true;
            stats.max_depth = WH as u32;
            break 'outer;
        }

        // 256-arm dispatch via proc-macro. In each arm, __D__ is the
        // literal depth value; depth (runtime) == __D__ at arm entry.
        depth_dispatch_256! {
            // Per-D compile-time constants.
            const D_ROW: usize = __D__ / 16;
            const D_COL: usize = __D__ % 16;
            const IS_TOP_ROW: bool = D_ROW == 0;
            const IS_BOTTOM_ROW: bool = D_ROW == 15;
            const IS_LEFT_COL: bool = D_COL == 0;
            const IS_RIGHT_COL: bool = D_COL == 15;
            const TBL: usize = ((IS_RIGHT_COL as usize) << 1) | (IS_BOTTOM_ROW as usize);

            let top_color: Color = if IS_TOP_ROW {
                BORDER
            } else {
                let nbr = unsafe { *board.get_unchecked(__D__.wrapping_sub(W)) };
                unsafe { *bottom_ptr.add(nbr.0 as usize) }
            };
            let left_color: Color = if IS_LEFT_COL {
                BORDER
            } else {
                let nbr = unsafe { *board.get_unchecked(__D__.wrapping_sub(1)) };
                unsafe { *right_ptr.add(nbr.0 as usize) }
            };
            let key = ref_key(top_color, left_color);
            let flat = (TBL << 16) | (key as usize);

            let allowed_here = unsafe { *conf_alw_ptr.add(__D__) };
            let prev_conf = if __D__ == 0 { 0 } else { unsafe { *conf.get_unchecked(__D__.wrapping_sub(1)) } };
            let use_relaxed = !relaxed_offsets_ptr.is_null()
                && allowed_here > 0
                && prev_conf < allowed_here;
            let (lo, list_ptr) = if use_relaxed {
                let lo = unsafe { *relaxed_offsets_ptr.add(flat) } as usize;
                (lo, relaxed_entries_ptr)
            } else {
                let lo = unsafe { *strict_offsets_ptr.add(flat) } as usize;
                (lo, strict_entries_ptr)
            };
            let mut c_idx = lo + unsafe { *cursor.get_unchecked(__D__) } as usize;

            const POST_DEPTH: u32 = (__D__ + 1) as u32;
            let schedule_active = POST_DEPTH <= max_heuristic_index;
            let target = if schedule_active {
                unsafe { *targets_ptr.add(POST_DEPTH as usize - 1) }
            } else {
                0
            };
            let prev_cum = if __D__ == 0 { 0 } else { unsafe { *cum.get_unchecked(__D__.wrapping_sub(1)) } };

            let mut placed = false;
            loop {
                let pr = unsafe { *list_ptr.add(c_idx) };
                if pr.0 == PieceRot::NONE.0 {
                    break;
                }
                c_idx += 1;
                let piece_idx = pr.piece_idx() as usize;
                let word = piece_idx >> 6;
                let bit = 1u64 << (piece_idx & 63);
                if (unsafe { *pieces_used.get_unchecked(word) } & bit) != 0 {
                    continue;
                }

                let candidate_conf = if use_relaxed {
                    let p_top = unsafe { *top_ptr.add(pr.0 as usize) };
                    let p_left = unsafe { *left_ptr.add(pr.0 as usize) };
                    ((p_top != top_color) as u32) + ((p_left != left_color) as u32)
                } else {
                    0
                };
                let new_conf = prev_conf + candidate_conf;
                if new_conf > allowed_here {
                    continue;
                }

                if schedule_active {
                    let new_cum = prev_cum + unsafe { *heur_ptr.add(pr.0 as usize) } as u32;
                    if new_cum < target {
                        continue;
                    }
                    unsafe { *cum.get_unchecked_mut(__D__) = new_cum; }
                } else {
                    unsafe { *cum.get_unchecked_mut(__D__) = prev_cum; }
                }
                unsafe { *conf.get_unchecked_mut(__D__) = new_conf; }
                unsafe { *pieces_used.get_unchecked_mut(word) |= bit; }
                unsafe { *board.get_unchecked_mut(__D__) = pr; }
                unsafe { *cursor.get_unchecked_mut(__D__) = (c_idx - lo) as u32; }
                stats.nodes += 1;
                const POST_PLUS_1: u32 = (__D__ + 1) as u32;
                if POST_PLUS_1 > stats.max_depth {
                    stats.max_depth = POST_PLUS_1;
                    best_board.copy_from_slice(&board);
                }
                depth = __D__ + 1;
                if depth < WH {
                    unsafe { *cursor.get_unchecked_mut(depth) = 0; }
                }
                placed = true;
                break;
            }

            if !placed {
                unsafe { *cursor.get_unchecked_mut(__D__) = 0; }
                if __D__ == 0 {
                    break 'outer;
                }
                depth = __D__.wrapping_sub(1);
                let pr = unsafe { *board.get_unchecked(depth) };
                let piece_idx = pr.piece_idx() as usize;
                unsafe {
                    *pieces_used.get_unchecked_mut(piece_idx >> 6) &= !(1u64 << (piece_idx & 63));
                    *board.get_unchecked_mut(depth) = PieceRot::NONE;
                }
            }
        }
    }

    let out = board_to_out(index, &best_board);
    (stats, out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_core::{Edges, Piece};

    fn p(id: PieceId, t: Color, r: Color, b: Color, l: Color) -> Piece {
        Piece::new(id, Edges::new(t, r, b, l))
    }

    #[test]
    fn ref_key_roundtrip() {
        assert_eq!(ref_key(3, 7), (3 << 8) | 7);
    }

    #[test]
    fn piece_rot_encoding() {
        let pr = PieceRot::new(255, 2);
        assert_eq!(pr.piece_idx(), 255);
        assert_eq!(pr.rot(), 2);
        let pr = PieceRot::new(16383, 3);
        assert_eq!(pr.piece_idx(), 16383);
        assert_eq!(pr.rot(), 3);
    }

    #[test]
    fn solves_2x2_trivial() {
        // 2x2 board with 4 corner pieces. Only one orientation per piece
        // is legal (corners can only sit where their borders are).
        // Top-left: borders top+left, interior right+bottom both = 1.
        // Top-right: borders top+right, interior left=1, bottom=2.
        // Bot-left:  borders bottom+left, interior top=1, right=2.
        // Bot-right: borders bottom+right, interior top=2, left=2.
        let pieces = vec![
            // (id, top, right, bottom, left)
            p(0, BORDER, 1, 1, BORDER),
            p(1, BORDER, BORDER, 2, 1),
            p(2, 1, 2, BORDER, BORDER),
            p(3, 2, BORDER, BORDER, 2),
        ];
        let puzzle = Puzzle::new(2, 2, 3, pieces).unwrap();
        let (stats, board) = solve_raw(&puzzle, 1_000_000);
        assert!(stats.solved, "should solve trivial 2x2");
        assert_eq!(stats.max_depth, 4);
        // Verify the placement makes sense — piece 0 at corner 0, etc.
        // (Order of pieces in candidate list depends on bucket order;
        // we only assert correctness of the solution, not a specific
        // ordering.)
        // Score-check inline: every adjacent edge matches.
        let w = 2;
        let h = 2;
        let index = RowMajorIndex::build(&puzzle);
        // Build a piece_id -> rotated_edges lookup via the index.
        let edges_for = |id: PieceId, rot: Rotation| -> [Color; 4] {
            let piece = puzzle.pieces().iter().position(|p| p.id == id).unwrap();
            index.rotated_edges(piece as u16, rot.as_u8())
        };
        let mut matches = 0;
        for y in 0..h {
            for x in 0..w {
                let pos = y * w + x;
                let (id, rot) = board[pos];
                let e = edges_for(id, rot);
                if x + 1 < w {
                    let (idr, rotr) = board[pos + 1];
                    let er = edges_for(idr, rotr);
                    if e[1] == er[3] && e[1] != BORDER { matches += 1; }
                }
                if y + 1 < h {
                    let (idb, rotb) = board[pos + w];
                    let eb = edges_for(idb, rotb);
                    if e[2] == eb[0] && e[2] != BORDER { matches += 1; }
                }
            }
        }
        // 2x2 has 4 interior edges (2 horizontal + 2 vertical).
        assert_eq!(matches, 4, "2x2 should have all 4 interior edges matched");
    }
}
