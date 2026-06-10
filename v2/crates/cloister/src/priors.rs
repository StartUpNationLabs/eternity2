// Empirical placement priors (vol-213, binding item 2) — the V155
// weaving-prior pattern adapted to CLOISTER-II: per-(cell, piece, rot)
// frequencies over a pool of completed boards order the cost-0 candidate
// scan (descending weight, per-epoch noise for tie-breaks) instead of a
// uniform shuffle. Hypothesis: near-globally-consistent prefixes leave
// better endgame pools. Risk (stated in advance): a pool of σ-locked 44x
// boards may steer back into the same basins — the probe measures the
// delta either way.

use std::path::Path;

use crate::frame::is_ring;
use crate::io::load_placement;
use crate::model::InteriorModel;

pub struct Priors {
    np: usize,
    /// w[cell * np + pid][rot] = count over the board pool
    w: Vec<[u16; 4]>,
    pub n_boards: usize,
}

impl Priors {
    pub fn from_board_dir(model: &InteriorModel, dir: &Path) -> Result<Self, String> {
        let mut files: Vec<_> = std::fs::read_dir(dir)
            .map_err(|e| format!("{}: {e}", dir.display()))?
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.extension().is_some_and(|e| e == "json"))
            .collect();
        files.sort();
        let mut g2l = vec![u16::MAX; 256];
        for (l, &g) in model.global_id.iter().enumerate() {
            g2l[g as usize] = l as u16;
        }
        let mut w = vec![[0u16; 4]; model.cells * model.np];
        let mut n_boards = 0usize;
        for f in &files {
            let Ok(placement) = load_placement(f) else { continue };
            let mut used = 0usize;
            for &(pos, pid, rot) in &placement {
                if is_ring(pos) {
                    continue;
                }
                let (y, x) = (pos / 16, pos % 16);
                if !(1..=model.n).contains(&y) || !(1..=model.n).contains(&x) {
                    continue;
                }
                let local = g2l[pid as usize];
                if local == u16::MAX {
                    continue;
                }
                let cell = (y - 1) * model.n + (x - 1);
                let slot = &mut w[cell * model.np + local as usize][rot as usize & 3];
                *slot = slot.saturating_add(1);
                used += 1;
            }
            if used == model.cells {
                n_boards += 1;
            }
        }
        if n_boards == 0 {
            return Err(format!("{}: no complete interior boards", dir.display()));
        }
        Ok(Self { np: model.np, w, n_boards })
    }

    #[inline]
    #[must_use]
    pub fn weight(&self, cell: usize, pid: u16, rot: u8) -> u32 {
        u32::from(self.w[cell * self.np + pid as usize][rot as usize & 3])
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::InteriorModel;

    #[test]
    fn priors_count_boards() {
        // synthesize: an E2-shaped model is needed for global ids; use the
        // synthetic model with identity global ids and fake 16×16 positions
        let (m, sol, _) = InteriorModel::synthetic(14, 6, 4);
        let dir = std::env::temp_dir().join(format!("cloister_priors_test_{}", std::process::id()));
        std::fs::create_dir_all(&dir).expect("tmp");
        // write two identical boards in sparse-pos format via io::save_board
        // (puzzle-free path: write JSON manually since save_board needs a Puzzle)
        let body: Vec<String> = sol
            .iter()
            .enumerate()
            .map(|(cell, &(pid, rot))| {
                let pos = (cell / 14 + 1) * 16 + (cell % 14 + 1);
                format!("{{\"pos\":{pos},\"piece_id\":{pid},\"rotation\":{rot}}}")
            })
            .collect();
        let json = format!("{{\"placement\":[{}]}}", body.join(","));
        std::fs::write(dir.join("a.json"), &json).expect("write");
        std::fs::write(dir.join("b.json"), &json).expect("write");
        let p = Priors::from_board_dir(&m, &dir).expect("priors");
        assert_eq!(p.n_boards, 2);
        let (pid, rot) = sol[0];
        assert_eq!(p.weight(0, pid, rot), 2);
        assert_eq!(p.weight(0, pid, (rot + 1) & 3), 0);
        std::fs::remove_dir_all(&dir).ok();
    }
}
