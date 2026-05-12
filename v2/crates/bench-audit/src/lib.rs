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

use eternity2_core::{Board, Color, PieceId, Position, Puzzle, Rotation};
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_localsearch::alns::score_board as score_board_baseline;
use eternity2_propagators::{PlacementInfo, PropagatorContext, gacolor_check, parity_check};

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
    -> (Vec<Option<PlacementInfo>>, Vec<bool>, Vec<Vec<u32>>)
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
    let domains: Vec<Vec<u32>> = vec![Vec::new(); n];
    (placed, used, domains)
}

pub fn run_gacolor(puzzle: &Puzzle,
                   placed: &[Option<PlacementInfo>],
                   used: &[bool],
                   domains: &[Vec<u32>])
{
    let ctx = PropagatorContext { puzzle, placed, used_pieces: used, domains };
    let _ = gacolor_check(&ctx);
}

pub fn run_parity(puzzle: &Puzzle,
                  placed: &[Option<PlacementInfo>],
                  used: &[bool],
                  domains: &[Vec<u32>])
{
    let ctx = PropagatorContext { puzzle, placed, used_pieces: used, domains };
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
