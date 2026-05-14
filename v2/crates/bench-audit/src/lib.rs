// Microbenchmark helpers for the hot-path audit.
//
// This crate is intentionally lean: it exposes builder functions that
// the criterion benches in `benches/` use to construct realistic inputs
// (puzzles, boards, domains) without re-implementing solver internals.
//
// Each "candidate" function here corresponds to a hot-path operation
// identified in the audit. Some have a "baseline" (matches current
// engine implementation) and a "candidate" (a proposed reformulation:
// packed Edges-as-u32, branchless rotation, SIMD-friendly score loop).
// The bench file compares them head-to-head.

#![forbid(unsafe_code)]

use std::io::Write;
use std::path::Path;
use std::time::Instant;

use eternity2_core::{Board, Color, PieceId, Position, Puzzle, Rotation};
use eternity2_events::{EventBody, EventSink, FinalStats, SolverEvent};
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_localsearch::alns::score_board as score_board_baseline;
use eternity2_propagators::{PlacementInfo, PropagatorContext, gacolor_check, parity_check};

/// Reusable progress sink for bench bins.
///
/// Tracks `best_depth` across all events; captures `FinalStats` on any
/// terminal event (Solved / Exhausted / TimedOut / Cancelled); appends
/// a progress line `[<elapsed_ms> ms]  depth=N  best_depth=M  node_id=K`
/// to the log file every `period_ms` milliseconds.
///
/// Usage:
/// ```ignore
/// let mut sink = ProgressSink::new(&log_path, 5_000)?;
/// sink.write_line("=== my run header ===");
/// let outcome = solver.solve(&puzzle, &opts, &mut sink);
/// // sink.final_stats / sink.best_depth populated.
/// ```
pub struct ProgressSink {
    pub log: std::fs::File,
    started: Instant,
    last_log_ms: u64,
    period_ms: u64,
    pub best_depth: u32,
    pub final_stats: Option<FinalStats>,
}

impl ProgressSink {
    pub fn new(path: &Path, period_ms: u64) -> std::io::Result<Self> {
        Ok(Self {
            log: std::fs::File::create(path)?,
            started: Instant::now(),
            last_log_ms: 0,
            period_ms,
            best_depth: 0,
            final_stats: None,
        })
    }

    pub fn write_line(&mut self, line: &str) {
        let _ = writeln!(self.log, "{line}");
        let _ = self.log.flush();
    }
}

impl EventSink for ProgressSink {
    fn emit(&mut self, event: SolverEvent) {
        let elapsed_ms = self.started.elapsed().as_millis() as u64;

        if let EventBody::Backtrack { from_depth, .. } = &event.body {
            if *from_depth > self.best_depth { self.best_depth = *from_depth; }
        }
        if event.depth > self.best_depth { self.best_depth = event.depth; }

        if elapsed_ms.saturating_sub(self.last_log_ms) >= self.period_ms {
            self.last_log_ms = elapsed_ms;
            let _ = writeln!(self.log,
                "[{:>7} ms]  depth={:>4}  best_depth={:>4}  node_id={}",
                elapsed_ms, event.depth, self.best_depth, event.node_id);
            let _ = self.log.flush();
        }

        match event.body {
            EventBody::Solved { final_stats, .. }
            | EventBody::Exhausted { final_stats, .. }
            | EventBody::TimedOut { final_stats, .. }
            | EventBody::Cancelled { final_stats, .. } => {
                let _ = writeln!(self.log,
                    "=== terminal event at {elapsed_ms}ms: nodes={} backtracks={} max_depth_seen={} ===",
                    final_stats.nodes, final_stats.backtracks, final_stats.max_depth_seen);
                let _ = self.log.flush();
                self.final_stats = Some(final_stats);
            }
            _ => {}
        }
    }
}

// ---------- Vol-16 Cat-3 — shared harness helpers ----------
//
// The bench bins in `src/bin/` share ~80 lines of boilerplate each.
// These helpers move the common parts into one place so each bin is
// just CLI parsing + a Pipeline invocation. Migration is incremental:
// bins added in vol-12 / vol-14 / vol-15 originally inlined their own
// copies of the helpers below; vol-16 swaps them out one at a time.

// Reporting / scoring helpers now live in `eternity2-export`. Re-export so
// existing call sites (`use eternity2_bench_audit::{score_board, ...}`)
// keep working. New code should import from `eternity2_export` directly.
pub use eternity2_export::{internal_edge_count, placed_count, render_board, score_board};

/// Score `board` against the puzzle's *total internal-edge count*
/// (= `internal_edge_count(puzzle)`). Returns `(matched, total)`.
/// Equivalent to `score_board` for fully-placed boards; differs on
/// partials because the denominator includes adjacencies where one
/// or both cells are empty.
#[must_use]
pub fn score_board_dense(puzzle: &Puzzle, board: &Board) -> (u32, u32) {
    let total = internal_edge_count(puzzle);
    let (matched, _) = score_board(puzzle, board);
    (matched, total)
}

// ---------- Workload builders ----------

/// Build a deterministic random puzzle of a given size. Used by all
/// benches to keep inputs reproducible across runs.
#[must_use]
pub fn build_puzzle(size: u32, colors: u32, seed: u64) -> Puzzle {
    generate(GeneratorConfig { size, interior_colors: colors, seed })
        .expect("generator must succeed for valid sizes")
}

/// Place every piece of the puzzle at its canonical position (the
/// generator emits pieces in solved row-major order with each piece's
/// rotation = R0). Produces a fully-matched board to exercise scoring
/// at saturation.
#[must_use]
pub fn solved_board(puzzle: &Puzzle) -> Board {
    let mut b = Board::empty(puzzle);
    for (i, p) in puzzle.pieces().iter().enumerate() {
        b.place(i as Position, p.id, Rotation::R0);
    }
    b
}

// ---------- Edges rotation ----------

/// Baseline: array-based, current implementation in eternity2-core.
#[inline(always)]
#[must_use]
pub fn rotate_edges_baseline(e: [Color; 4], r: u8) -> [Color; 4] {
    let [t, ri, b, l] = e;
    match r & 0b11 {
        0 => [t, ri, b, l],
        1 => [l, t, ri, b],
        2 => [b, l, t, ri],
        _ => [ri, b, l, t],
    }
}

/// Candidate: pack [Color; 4] into u32, rotate by byte-shift, unpack.
/// On aarch64-apple-darwin this collapses to a single ROR on the
/// packed u32 (then a load to memory). Layout: byte0=top, byte1=right,
/// byte2=bottom, byte3=left (little-endian).
#[inline(always)]
#[must_use]
pub fn rotate_edges_packed(e: [Color; 4], r: u8) -> [Color; 4] {
    let packed = u32::from_le_bytes(e);
    let rot = (r & 0b11) * 8;
    // Baseline R90 sends (t,r,b,l) → (l,t,r,b). In LE bytes: byte0=t
    // moves to byte1, byte3=l moves to byte0. That's a rotate-left of
    // the *value* by 8 bits, which (in LE) maps to byte-position +1.
    let rotated = packed.rotate_left(rot.into());
    rotated.to_le_bytes()
}

// ---------- Score ----------

/// Candidate score: a flat over-row+column loop that always touches
/// edges in a packed [u32] cache instead of `Option<(...)>` calls.
/// Demonstrates the per-cell-edge-cache idea from the audit.
#[must_use]
pub fn score_packed(puzzle: &Puzzle, edges_grid: &[[Color; 4]]) -> u32 {
    let w = puzzle.width as usize;
    let h = puzzle.height as usize;
    let mut m: u32 = 0;
    for y in 0..h {
        for x in 0..w {
            let i = y * w + x;
            let e = edges_grid[i];
            if x + 1 < w {
                let ne = edges_grid[i + 1];
                if e[1] != 0 && e[1] == ne[3] { m += 1; }
            }
            if y + 1 < h {
                let ne = edges_grid[i + w];
                if e[2] != 0 && e[2] == ne[0] { m += 1; }
            }
        }
    }
    m
}

/// Build the dense edges-grid used by `score_packed`.
#[must_use]
pub fn build_edges_grid(puzzle: &Puzzle, board: &Board) -> Vec<[Color; 4]> {
    let n = puzzle.cell_count() as usize;
    let mut out = vec![[0u8; 4]; n];
    // Materialise edges_for(pid, rot) via Piece::edges and Rotation::rotated.
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, rot)) = board.get(pos) {
            if let Some(p) = puzzle.piece(pid) {
                out[pos as usize] = p.edges.rotated(rot).as_array();
            }
        }
    }
    out
}

/// Re-export of the localsearch baseline scorer so benches can compare.
pub fn score_board_baseline_wrapper(puzzle: &Puzzle, board: &Board) -> u32 {
    score_board_baseline(puzzle, board)
}

// ---------- Propagator state ----------

/// Build a `PropagatorContext`-shaped tuple. Returns the owned buffers
/// so the bench can hand them to the propagator without re-creating
/// them inside the timed section.
#[must_use]
pub fn build_propagator_inputs(puzzle: &Puzzle, board: &Board)
    -> (Vec<Option<PlacementInfo>>, Vec<bool>, Vec<u64>, usize)
{
    let n = puzzle.cell_count() as usize;
    let mut placed = vec![None; n];
    let max_pid = puzzle.pieces().iter().map(|p| usize::from(p.id) + 1).max().unwrap_or(0);
    let mut used = vec![false; max_pid];
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, rot)) = board.get(pos) {
            if let Some(p) = puzzle.piece(pid) {
                placed[pos as usize] = Some(PlacementInfo {
                    edges_after_rotation: p.edges.rotated(rot).as_array(),
                });
                used[usize::from(pid)] = true;
            }
        }
    }
    let n_rows = max_pid * 4;
    let wpp = n_rows.div_ceil(64).max(1);
    let domain_bits = vec![0u64; n * wpp];
    (placed, used, domain_bits, wpp)
}

pub fn run_gacolor(puzzle: &Puzzle,
                   placed: &[Option<PlacementInfo>],
                   used: &[bool],
                   domain_bits: &[u64],
                   words_per_pos: usize)
{
    let ctx = PropagatorContext { puzzle, placed, used_pieces: used, domain_bits, words_per_pos };
    let _ = gacolor_check(&ctx);
}

pub fn run_parity(puzzle: &Puzzle,
                  placed: &[Option<PlacementInfo>],
                  used: &[bool],
                  domain_bits: &[u64],
                  words_per_pos: usize)
{
    let ctx = PropagatorContext { puzzle, placed, used_pieces: used, domain_bits, words_per_pos };
    let _ = parity_check(&ctx);
}

// ---------- Board cell representation ----------

/// Candidate Board representation: pack (piece_id u16, rotation u8) into
/// u32 with sentinel 0xFFFF_FFFF for empty. Avoids the `Option<(u16,u8)>`
/// niche churn and gives a 4-byte aligned cell — friendly to SIMD loads.
#[derive(Debug, Clone)]
pub struct PackedBoard {
    pub width: u32,
    pub height: u32,
    /// One u32 per cell: low 16 bits = piece_id, bits 16..18 = rotation,
    /// bits 24..32 = flags. 0xFFFF_FFFF means empty.
    pub cells: Vec<u32>,
}

const EMPTY_CELL: u32 = 0xFFFF_FFFF;

impl PackedBoard {
    #[must_use]
    pub fn empty(puzzle: &Puzzle) -> Self {
        let n = (puzzle.width as usize) * (puzzle.height as usize);
        Self {
            width: puzzle.width,
            height: puzzle.height,
            cells: vec![EMPTY_CELL; n],
        }
    }

    #[inline(always)]
    pub fn place(&mut self, pos: Position, piece_id: PieceId, rot: Rotation) {
        let packed = u32::from(piece_id) | ((rot.as_u8() as u32) << 16);
        self.cells[pos as usize] = packed;
    }

    #[inline(always)]
    #[must_use]
    pub fn get(&self, pos: Position) -> Option<(PieceId, Rotation)> {
        let c = self.cells[pos as usize];
        if c == EMPTY_CELL { return None; }
        Some((c as u16, Rotation::from_u8(((c >> 16) & 0b11) as u8).unwrap()))
    }
}

/// Build a `PackedBoard` from a regular `Board`.
#[must_use]
pub fn pack_board(puzzle: &Puzzle, board: &Board) -> PackedBoard {
    let mut p = PackedBoard::empty(puzzle);
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, rot)) = board.get(pos) {
            p.place(pos, pid, rot);
        }
    }
    p
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rotate_packed_matches_baseline() {
        for t in 0..3 { for r in 0..3 { for b in 0..3 { for l in 0..3 {
            let e = [t as Color, r as Color, b as Color, l as Color];
            for rot in 0..4u8 {
                assert_eq!(rotate_edges_baseline(e, rot), rotate_edges_packed(e, rot),
                    "rotation mismatch on {:?} r={}", e, rot);
            }
        }}}}
    }

    #[test]
    fn score_packed_matches_baseline() {
        let p = build_puzzle(6, 5, 42);
        let b = solved_board(&p);
        let grid = build_edges_grid(&p, &b);
        // The solved board is a valid solution so every interior edge matches:
        // the bench just confirms scoring is not catastrophically broken.
        let s_packed = score_packed(&p, &grid);
        let s_base = score_board_baseline_wrapper(&p, &b);
        assert_eq!(s_packed, s_base);
    }

    #[test]
    fn packed_board_roundtrip() {
        let p = build_puzzle(5, 4, 7);
        let b = solved_board(&p);
        let pb = pack_board(&p, &b);
        for pos in 0..p.cell_count() {
            assert_eq!(pb.get(pos), b.get(pos));
        }
    }

}
