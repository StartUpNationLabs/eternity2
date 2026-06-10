// Frame: a fixed assignment of the 60 border pieces to the 16×16 ring.
// CLOISTER-II anchors the interior search on one; the frame supplies
// position-exact rim color targets so the 56 IB edges are real edges.

use std::collections::HashMap;
use std::path::Path;

use eternity2_core::{Puzzle, Rotation, BORDER};

use crate::model::RimTargets;

pub const W: usize = 16;

pub struct Frame {
    /// (full-board pos, global piece id, rotation) for the 60 ring cells
    pub placement: Vec<(usize, u16, u8)>,
    /// ring-ring matched edges (60 = perfect ring)
    pub bb: u32,
    /// per interior cell (14×14 index), per side NESW: required color
    pub targets: RimTargets,
    pub label: String,
}

#[must_use]
pub fn is_ring(pos: usize) -> bool {
    let (y, x) = (pos / W, pos % W);
    y == 0 || y == W - 1 || x == 0 || x == W - 1
}

/// Extract the ring of any board JSON (full boards, ring-only frame files,
/// and interior-only boards are all sparse `placement` arrays with `pos`).
/// Fails if the ring is incomplete or a piece is not legally oriented
/// (grey sides outward, exactly).
pub fn load(path: &Path, puzzle: &Puzzle) -> Result<Frame, String> {
    let txt = std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let v: serde_json::Value =
        serde_json::from_str(&txt).map_err(|e| format!("{}: {e}", path.display()))?;
    let arr = v["placement"]
        .as_array()
        .ok_or_else(|| format!("{}: no placement array", path.display()))?;
    let mut ring: HashMap<usize, (u16, u8)> = HashMap::new();
    for e in arr {
        let pos = e["pos"].as_u64().ok_or("placement entry without pos")? as usize;
        if is_ring(pos) {
            ring.insert(
                pos,
                (
                    e["piece_id"].as_u64().ok_or("no piece_id")? as u16,
                    e["rotation"].as_u64().ok_or("no rotation")? as u8,
                ),
            );
        }
    }
    if ring.len() != 60 {
        return Err(format!("{}: ring has {}/60 cells", path.display(), ring.len()));
    }
    let label = path
        .file_stem()
        .map_or_else(|| "frame".into(), |s| s.to_string_lossy().into_owned());
    from_ring(&ring, puzzle, label)
}

pub fn from_ring(
    ring: &HashMap<usize, (u16, u8)>,
    puzzle: &Puzzle,
    label: String,
) -> Result<Frame, String> {
    let edges_of = |pid: u16, rot: u8| -> [u8; 4] {
        puzzle
            .piece(pid)
            .expect("piece")
            .edges
            .rotated(Rotation::from_u8(rot).expect("rot"))
            .as_array()
    };
    // legality: grey sides exactly on the outward sides
    let mut seen = [false; 256];
    for (&pos, &(pid, rot)) in ring {
        if seen[pid as usize] {
            return Err(format!("duplicate piece {pid} in ring"));
        }
        seen[pid as usize] = true;
        let e = edges_of(pid, rot);
        let (y, x) = (pos / W, pos % W);
        for (s, on_edge) in [
            (0, y == 0),
            (1, x == W - 1),
            (2, y == W - 1),
            (3, x == 0),
        ] {
            if on_edge != (e[s] == BORDER) {
                return Err(format!(
                    "piece {pid} at pos {pos}: grey orientation illegal (side {s})"
                ));
            }
        }
    }
    // BB: matched non-grey edges between ring neighbors
    let mut bb = 0u32;
    for (&pos, &(pid, rot)) in ring {
        let e = edges_of(pid, rot);
        let (y, x) = (pos / W, pos % W);
        if x + 1 < W {
            if let Some(&(np, nr)) = ring.get(&(pos + 1)) {
                if e[1] != BORDER && e[1] == edges_of(np, nr)[3] {
                    bb += 1;
                }
            }
        }
        if y + 1 < W {
            if let Some(&(np, nr)) = ring.get(&(pos + W)) {
                if e[2] != BORDER && e[2] == edges_of(np, nr)[0] {
                    bb += 1;
                }
            }
        }
    }
    // rim targets: for each interior cell adjacent to the ring, the border
    // piece's inward-facing color
    let n = W - 2;
    let mut targets: RimTargets = vec![[None; 4]; n * n];
    for cell in 0..n * n {
        let (iy, ix) = (cell / n, cell % n);
        let full = (iy + 1) * W + (ix + 1);
        // (my side, neighbor pos, neighbor's facing side)
        let nbs = [
            (0usize, full - W, 2usize),
            (1, full + 1, 3),
            (2, full + W, 0),
            (3, full - 1, 1),
        ];
        for (s, npos, nside) in nbs {
            if is_ring(npos) {
                let &(pid, rot) = ring
                    .get(&npos)
                    .ok_or_else(|| format!("ring missing pos {npos}"))?;
                targets[cell][s] = Some(edges_of(pid, rot)[nside]);
            }
        }
    }
    let mut placement: Vec<(usize, u16, u8)> =
        ring.iter().map(|(&p, &(pid, r))| (p, pid, r)).collect();
    placement.sort_unstable();
    Ok(Frame { placement, bb, targets, label })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ring_positions_count() {
        assert_eq!((0..256).filter(|&p| is_ring(p)).count(), 60);
    }
}
