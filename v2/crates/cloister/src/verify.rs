// Independent full-board verification — run on every record candidate
// BEFORE any claim (CLAUDE.md discipline; vol-35 found 200 fake records,
// V199 invalidated the old strict-459 via dup pieces).
//
// Conventions enforced here:
//   - 256/256 distinct pieces;
//   - border legality: grey sides exactly on the outer rim;
//   - grey-grey adjacencies NEVER count as matches (corpus "448" artifact);
//   - II/IB/BB split per the 480 = 364 + 56 + 60 decomposition;
//   - strict-canonical = all 5 hints placed (piece AND rotation).

use eternity2_core::{Hints, Puzzle, Rotation, BORDER};

use crate::frame::{is_ring, W};

#[derive(Debug)]
pub struct BoardCheck {
    pub n_placed: usize,
    pub unique: bool,
    pub border_legal: bool,
    pub hints_ok: usize,
    pub hints_total: usize,
    pub ii: u32,
    pub ib: u32,
    pub bb: u32,
    pub grey_grey: u32,
}

impl BoardCheck {
    #[must_use]
    pub fn total(&self) -> u32 {
        self.ii + self.ib + self.bb
    }
    #[must_use]
    pub fn is_legal_complete(&self) -> bool {
        self.n_placed == 256 && self.unique && self.border_legal
    }
    #[must_use]
    pub fn is_strict(&self) -> bool {
        self.is_legal_complete() && self.hints_ok == self.hints_total
    }
}

pub fn verify(puzzle: &Puzzle, hints: &Hints, placement: &[(usize, u16, u8)]) -> BoardCheck {
    let mut at: Vec<Option<(u16, u8)>> = vec![None; 256];
    let mut seen = [0u32; 256];
    let mut unique = true;
    for &(pos, pid, rot) in placement {
        at[pos] = Some((pid, rot));
        seen[pid as usize] += 1;
        if seen[pid as usize] > 1 {
            unique = false;
        }
    }
    let n_placed = at.iter().flatten().count();
    let edges_of = |pid: u16, rot: u8| -> [u8; 4] {
        puzzle
            .piece(pid)
            .expect("piece")
            .edges
            .rotated(Rotation::from_u8(rot).expect("rot"))
            .as_array()
    };
    let mut border_legal = true;
    for pos in 0..256 {
        let Some((pid, rot)) = at[pos] else { continue };
        let e = edges_of(pid, rot);
        let (y, x) = (pos / W, pos % W);
        for (s, on_edge) in [(0, y == 0), (1, x == W - 1), (2, y == W - 1), (3, x == 0)] {
            if (e[s] == BORDER) != on_edge {
                border_legal = false;
            }
        }
    }
    let (mut ii, mut ib, mut bb, mut grey_grey) = (0u32, 0u32, 0u32, 0u32);
    for pos in 0..256 {
        let Some((pid, rot)) = at[pos] else { continue };
        let e = edges_of(pid, rot);
        let (y, x) = (pos / W, pos % W);
        let mut tally = |my: u8, npos: usize, their_side: usize| {
            let Some((np, nr)) = at[npos] else { return };
            let ne = edges_of(np, nr)[their_side];
            if my == BORDER && ne == BORDER {
                grey_grey += 1;
                return;
            }
            if my == ne && my != BORDER {
                match (is_ring(pos), is_ring(npos)) {
                    (true, true) => bb += 1,
                    (false, false) => ii += 1,
                    _ => ib += 1,
                }
            }
        };
        if x + 1 < W {
            tally(e[1], pos + 1, 3);
        }
        if y + 1 < W {
            tally(e[2], pos + W, 0);
        }
    }
    let mut hints_ok = 0;
    for h in &hints.hints {
        if at[h.position as usize] == Some((h.piece_id, h.rotation.as_u8())) {
            hints_ok += 1;
        }
    }
    BoardCheck {
        n_placed,
        unique,
        border_legal,
        hints_ok,
        hints_total: hints.hints.len(),
        ii,
        ib,
        bb,
        grey_grey,
    }
}
