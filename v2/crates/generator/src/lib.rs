#![no_std]
#![forbid(unsafe_code)]

extern crate alloc;

use alloc::vec::Vec;
use eternity2_core::{Color, Edges, Piece, PieceId, Position, Puzzle, PuzzleError, Rotation, BORDER};

// Deterministic PRNG. SplitMix64 — small, fast, no dep, wasm-clean. Not
// crypto-grade but plenty for shuffling puzzle pieces; benchmark
// reproducibility is what we actually need.
#[derive(Debug, Clone)]
pub struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    #[must_use]
    pub const fn new(seed: u64) -> Self {
        // Wrap 0 into a non-zero state so seed=0 still produces a stream.
        Self { state: seed.wrapping_add(0x9E37_79B9_7F4A_7C15) }
    }

    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    // Uniform integer in [0, n). n must be > 0.
    pub fn gen_range(&mut self, n: u32) -> u32 {
        // Lemire's nearly-divisionless method, scaled down to u32.
        // For our small N, simple modulo is fine and easier to audit.
        debug_assert!(n > 0);
        (self.next_u64() % u64::from(n)) as u32
    }

    pub fn shuffle<T>(&mut self, slice: &mut [T]) {
        // Fisher-Yates.
        for i in (1..slice.len()).rev() {
            #[allow(clippy::cast_possible_truncation)]
            let j = self.gen_range(i as u32 + 1) as usize;
            slice.swap(i, j);
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GeneratorConfig {
    pub size: u32,                 // board is size × size
    pub interior_colors: u32,      // number of non-border colors
    pub seed: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GeneratorError {
    SizeZero,
    InteriorColorsZero,
    TooManyColors { max: u32, requested: u32 },
    Puzzle(PuzzleError),
}

impl GeneratorConfig {
    // Max distinct interior colors a board can sustain while every color
    // appears at least once: there are 2 * size * (size - 1) interior
    // edges (size*(size-1) horizontal + size*(size-1) vertical). For
    // size=1 there are zero interior edges (no constraints), so we cap
    // interior_colors at 0 in that case.
    #[must_use]
    pub const fn max_interior_colors(size: u32) -> u32 {
        if size <= 1 { 0 } else { 2 * size * (size - 1) }
    }
}

pub fn generate(cfg: GeneratorConfig) -> Result<Puzzle, GeneratorError> {
    generate_with_solution(cfg).map(|(p, _)| p)
}

/// A single placement in the canonical solution: at `position`, place the
/// piece with `piece_id` rotated by `rotation`. The placed edges then
/// satisfy adjacency with all neighbours by construction.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Placement {
    pub position: Position,
    pub piece_id: PieceId,
    pub rotation: Rotation,
}

/// Like `generate`, but also returns the canonical solution that was
/// implicitly constructed by the Selby-Riordan procedure (place pieces
/// at their original positions first, then randomly rotate + shuffle).
/// Used by vol-26 to dump training data: each puzzle has a known
/// optimal placement sequence.
pub fn generate_with_solution(
    cfg: GeneratorConfig,
) -> Result<(Puzzle, Vec<Placement>), GeneratorError> {
    if cfg.size == 0 {
        return Err(GeneratorError::SizeZero);
    }
    if cfg.size > 1 && cfg.interior_colors == 0 {
        return Err(GeneratorError::InteriorColorsZero);
    }
    let max = GeneratorConfig::max_interior_colors(cfg.size);
    if cfg.interior_colors > max {
        return Err(GeneratorError::TooManyColors {
            max,
            requested: cfg.interior_colors,
        });
    }

    let mut rng = SplitMix64::new(cfg.seed);
    let size = cfg.size;

    let n_vertical = size * (size - 1);
    let n_horizontal = size * (size - 1);
    let total_interior = (n_vertical + n_horizontal) as usize;

    let mut edges: Vec<Color> = Vec::with_capacity(total_interior);
    if total_interior > 0 {
        for c in 1..=cfg.interior_colors {
            edges.push(c as Color);
        }
        let need = total_interior - edges.len();
        for _ in 0..need {
            let c = 1 + rng.gen_range(cfg.interior_colors);
            edges.push(c as Color);
        }
        rng.shuffle(&mut edges);
    }

    let vertical = &edges[..n_vertical as usize];
    let horizontal = &edges[n_vertical as usize..];

    let mut pieces: Vec<Piece> = Vec::with_capacity((size * size) as usize);
    for y in 0..size {
        for x in 0..size {
            let top = if y == 0 { BORDER } else {
                horizontal[((y - 1) * size + x) as usize]
            };
            let bottom = if y == size - 1 { BORDER } else {
                horizontal[(y * size + x) as usize]
            };
            let left = if x == 0 { BORDER } else {
                vertical[(y * (size - 1) + (x - 1)) as usize]
            };
            let right = if x == size - 1 { BORDER } else {
                vertical[(y * (size - 1) + x) as usize]
            };
            let id = (y * size + x) as PieceId;
            pieces.push(Piece::new(id, Edges::new(top, right, bottom, left)));
        }
    }

    // Record the per-piece rotation applied by the generator. To place
    // piece `i` into its canonical position the solver must rotate it
    // BACK by `(4 - applied) % 4` (an R90 turn moves edge slots clockwise;
    // its inverse is R270).
    let mut applied_rotation = alloc::vec![0u8; pieces.len()];
    for (idx, p) in pieces.iter_mut().enumerate() {
        let r = rng.gen_range(4) as u8;
        applied_rotation[idx] = r;
        let rot = Rotation::from_u8(r).unwrap();
        p.edges = p.edges.rotated(rot);
    }
    rng.shuffle(&mut pieces);

    // After the shuffle, build the solution table: piece_id encodes the
    // canonical (x, y) via `id = y*size + x`. The rotation needed at that
    // position is the inverse of the random rotation we baked into the
    // edges. We look up `applied_rotation` by the piece's original index
    // in the pre-shuffle order, which is identical to `piece_id` (since
    // pre-shuffle pieces[i].id == i).
    let mut solution: Vec<Placement> = Vec::with_capacity(pieces.len());
    for p in &pieces {
        let pos: Position = u32::from(p.id);
        let applied = applied_rotation[p.id as usize];
        let inverse = ((4 - applied) % 4) as u8;
        solution.push(Placement {
            position: pos,
            piece_id: p.id,
            rotation: Rotation::from_u8(inverse).unwrap(),
        });
    }
    solution.sort_by_key(|p| p.position);

    let puzzle = Puzzle::new(size, size, cfg.interior_colors + 1, pieces)
        .map_err(GeneratorError::Puzzle)?;
    Ok((puzzle, solution))
}

#[cfg(test)]
mod tests {
    use super::*;
    use alloc::collections::BTreeSet;

    #[test]
    fn deterministic_for_same_seed() {
        let cfg = GeneratorConfig { size: 4, interior_colors: 5, seed: 42 };
        let a = generate(cfg).unwrap();
        let b = generate(cfg).unwrap();
        assert_eq!(a, b);
    }

    #[test]
    fn different_seeds_diverge() {
        let a = generate(GeneratorConfig { size: 4, interior_colors: 5, seed: 1 }).unwrap();
        let b = generate(GeneratorConfig { size: 4, interior_colors: 5, seed: 2 }).unwrap();
        assert_ne!(a, b);
    }

    #[test]
    fn color_coverage_holds() {
        let cfg = GeneratorConfig { size: 5, interior_colors: 6, seed: 7 };
        let puz = generate(cfg).unwrap();
        let mut seen = BTreeSet::new();
        for p in puz.pieces() {
            for &c in &p.edges.as_array() {
                if c != BORDER { seen.insert(c); }
            }
        }
        for c in 1..=6u8 {
            assert!(seen.contains(&c), "color {c} missing");
        }
    }

    #[test]
    fn border_geometry_correct() {
        let cfg = GeneratorConfig { size: 4, interior_colors: 4, seed: 99 };
        let puz = generate(cfg).unwrap();
        // Some piece must have exactly 2 border edges (corners); some
        // must have exactly 1 (edges); some 0 (inner). The shuffled
        // order doesn't change those counts.
        let mut corners = 0;
        let mut edges = 0;
        let mut inner = 0;
        for p in puz.pieces() {
            if p.is_corner() { corners += 1; }
            else if p.is_edge() { edges += 1; }
            else if p.is_inner() { inner += 1; }
        }
        assert_eq!(corners, 4);
        assert_eq!(edges, 4 * (4 - 2));
        assert_eq!(inner, (4 - 2) * (4 - 2));
    }

    #[test]
    fn solution_satisfies_all_adjacencies() {
        for seed in 0..16u64 {
            let cfg = GeneratorConfig { size: 6, interior_colors: 5, seed };
            let (puz, sol) = generate_with_solution(cfg).unwrap();
            assert_eq!(sol.len() as u32, puz.cell_count());

            // Compute the placed edges at every cell, then check that
            // every adjacent pair matches and every boundary edge is
            // BORDER.
            let w = puz.width;
            let h = puz.height;
            let mut placed_edges: Vec<[Color; 4]> = alloc::vec![[BORDER; 4]; sol.len()];
            for placement in &sol {
                let piece = puz.piece(placement.piece_id).unwrap();
                placed_edges[placement.position as usize] =
                    piece.edges.rotated(placement.rotation).as_array();
            }
            for y in 0..h {
                for x in 0..w {
                    let pos = (y * w + x) as usize;
                    let e = placed_edges[pos];
                    // Top
                    if y == 0 {
                        assert_eq!(e[0], BORDER, "seed {seed} cell ({x},{y}) top should be BORDER");
                    } else {
                        let above = placed_edges[((y - 1) * w + x) as usize];
                        assert_eq!(e[0], above[2], "seed {seed} cell ({x},{y}) top != above bottom");
                    }
                    // Right
                    if x == w - 1 {
                        assert_eq!(e[1], BORDER, "seed {seed} cell ({x},{y}) right should be BORDER");
                    } else {
                        let right = placed_edges[(y * w + x + 1) as usize];
                        assert_eq!(e[1], right[3], "seed {seed} cell ({x},{y}) right != neighbor left");
                    }
                    // Bottom
                    if y == h - 1 {
                        assert_eq!(e[2], BORDER, "seed {seed} cell ({x},{y}) bottom should be BORDER");
                    }
                    // Left
                    if x == 0 {
                        assert_eq!(e[3], BORDER, "seed {seed} cell ({x},{y}) left should be BORDER");
                    }
                }
            }
        }
    }

    #[test]
    fn rejects_too_many_colors() {
        let err = generate(GeneratorConfig {
            size: 3, interior_colors: GeneratorConfig::max_interior_colors(3) + 1, seed: 0,
        }).unwrap_err();
        assert!(matches!(err, GeneratorError::TooManyColors { .. }));
    }
}
