// Interior model: the n×n sub-puzzle of interior pieces (n=14 for E2),
// plus the bitset candidate tables the DFS hot loop runs on.
//
// Side convention everywhere: 0=N, 1=E, 2=S, 3=W (eternity2-core order).
// A piece's side s faces the neighbor side (s+2)%4. Rotation r maps stored
// base edges to oriented edges via oriented[s] = base[(s + 4 - r) % 4]
// (same convention as eternity2_core::Edges::rotated).

use eternity2_core::{Puzzle, Rotation, BORDER};

use crate::rng::Rng;

/// piece-capacity bitmask (≤ 256 pieces; E2 interior uses 196)
pub const WORDS: usize = 4;
pub type PieceMask = [u64; WORDS];

pub fn mask_set(m: &mut PieceMask, pid: u16) {
    m[pid as usize >> 6] |= 1 << (pid & 63);
}
pub fn mask_clear(m: &mut PieceMask, pid: u16) {
    m[pid as usize >> 6] &= !(1 << (pid & 63));
}
#[must_use]
pub fn mask_get(m: &PieceMask, pid: u16) -> bool {
    m[pid as usize >> 6] >> (pid & 63) & 1 == 1
}

/// per interior cell, per side (NESW): required color on the outward (rim)
/// side, from a fixed border. None on inner sides / free-rim runs.
pub type RimTargets = Vec<[Option<u8>; 4]>;

pub struct InteriorModel {
    pub n: usize,
    pub cells: usize,
    /// number of interior pieces (= cells)
    pub np: usize,
    /// color table dimension (max color value + 1)
    pub ncolors: usize,
    pub ii_max: u32,
    /// rot_edges[pid][rot] = oriented [N,E,S,W], pid = canonical local id
    pub rot_edges: Vec<[[u8; 4]; 4]>,
    /// canonical local pid -> global PieceId (identity for synthetic models)
    pub global_id: Vec<u16>,
    /// (cell, canonical local pid, rot) for hints that land in the interior
    pub hints: Vec<(usize, usize, u8)>,
    /// inward-color multiset of the 56 border edge pieces
    pub edge_inward_supply: Vec<u32>,
}

impl InteriorModel {
    pub fn from_puzzle(puzzle: &Puzzle, hints: &eternity2_core::Hints) -> Self {
        let n = 14usize;
        let mut rot_edges = Vec::new();
        let mut global_id = Vec::new();
        let mut g2l = vec![usize::MAX; 256];
        let mut edge_inward_supply = vec![0u32; 23];
        for pid in 0..256u16 {
            let p = puzzle.piece(pid).expect("piece");
            let e = p.edges.as_array();
            match e.iter().filter(|&&c| c == BORDER).count() {
                0 => {
                    g2l[pid as usize] = global_id.len();
                    let mut re = [[0u8; 4]; 4];
                    for r in 0..4u8 {
                        re[r as usize] = p
                            .edges
                            .rotated(Rotation::from_u8(r).expect("rot"))
                            .as_array();
                    }
                    rot_edges.push(re);
                    global_id.push(pid);
                }
                1 => {
                    let grey_side = e.iter().position(|&c| c == BORDER).expect("grey");
                    let inward = e[(grey_side + 2) % 4];
                    edge_inward_supply[inward as usize] += 1;
                }
                _ => {}
            }
        }
        assert_eq!(global_id.len(), n * n, "interior piece count");

        let mut ih = Vec::new();
        for h in &hints.hints {
            let (x, y) = puzzle.xy(h.position);
            let (x, y) = (x as usize, y as usize);
            if (1..=n).contains(&x) && (1..=n).contains(&y) {
                let local = g2l[h.piece_id as usize];
                assert!(local != usize::MAX, "hint piece must be interior");
                ih.push(((y - 1) * n + (x - 1), local, h.rotation.as_u8()));
            }
        }
        Self {
            n,
            cells: n * n,
            np: n * n,
            ncolors: 23,
            ii_max: 2 * (n * (n - 1)) as u32,
            rot_edges,
            global_id,
            hints: ih,
            edge_inward_supply,
        }
    }

    /// Random perfect n×n interior for tests: colors 1..ncolors on every
    /// edge (internal + rim), pieces cut at random rotations and shuffled.
    /// Returns (model, one perfect assignment, full rim targets).
    pub fn synthetic(n: usize, ncolors: usize, seed: u64) -> (Self, Vec<(u16, u8)>, RimTargets) {
        assert!(ncolors >= 3, "color 0 is reserved for grey");
        let mut rng = Rng::new(seed);
        let col = |rng: &mut Rng| 1 + rng.below(ncolors - 1) as u8;
        // h[y][x]: edge between (y-1,x) and (y,x), y in 0..=n
        let h: Vec<Vec<u8>> = (0..=n)
            .map(|_| (0..n).map(|_| col(&mut rng)).collect())
            .collect();
        let v: Vec<Vec<u8>> = (0..n)
            .map(|_| (0..=n).map(|_| col(&mut rng)).collect())
            .collect();
        let true_edges = |cell: usize| -> [u8; 4] {
            let (y, x) = (cell / n, cell % n);
            [h[y][x], v[y][x + 1], h[y + 1][x], v[y][x]]
        };
        let cells = n * n;
        // shuffle which canonical pid sits at which solution cell
        let mut pid_of_cell: Vec<u16> = (0..cells as u16).collect();
        rng.shuffle(&mut pid_of_cell);
        let mut base = vec![[0u8; 4]; cells];
        let mut sol = vec![(0u16, 0u8); cells];
        for cell in 0..cells {
            let pid = pid_of_cell[cell];
            let te = true_edges(cell);
            let r_sol = (rng.next_u64() & 3) as u8;
            let mut stored = [0u8; 4];
            for t in 0..4 {
                stored[t] = te[(t + r_sol as usize) % 4];
            }
            base[pid as usize] = stored;
            sol[cell] = (pid, r_sol);
        }
        let rot_edges: Vec<[[u8; 4]; 4]> = base
            .iter()
            .map(|b| {
                let mut re = [[0u8; 4]; 4];
                for r in 0..4usize {
                    for s in 0..4 {
                        re[r][s] = b[(s + 4 - r) % 4];
                    }
                }
                re
            })
            .collect();
        let mut targets: RimTargets = vec![[None; 4]; cells];
        for cell in 0..cells {
            let (y, x) = (cell / n, cell % n);
            if y == 0 {
                targets[cell][0] = Some(h[0][x]);
            }
            if y == n - 1 {
                targets[cell][2] = Some(h[n][x]);
            }
            if x == 0 {
                targets[cell][3] = Some(v[y][0]);
            }
            if x == n - 1 {
                targets[cell][1] = Some(v[y][n]);
            }
        }
        let model = Self {
            n,
            cells,
            np: cells,
            ncolors,
            ii_max: 2 * (n * (n - 1)) as u32,
            rot_edges,
            global_id: (0..cells as u16).collect(),
            hints: Vec::new(),
            edge_inward_supply: vec![0; ncolors],
        };
        (model, sol, targets)
    }

    #[must_use]
    pub fn edges(&self, pid: u16, rot: u8) -> [u8; 4] {
        self.rot_edges[pid as usize][rot as usize]
    }

    /// total mismatches over II edges plus (if given) fixed rim targets —
    /// the quantity the break-DFS minimizes. grid is in canonical pid space.
    #[must_use]
    pub fn count_breaks(&self, grid: &[(u16, u8)], targets: Option<&RimTargets>) -> u32 {
        let n = self.n;
        let mut b = 0;
        for cell in 0..self.cells {
            let e = self.edges(grid[cell].0, grid[cell].1);
            if cell % n > 0 {
                let (lp, lr) = grid[cell - 1];
                if self.edges(lp, lr)[1] != e[3] {
                    b += 1;
                }
            }
            if cell >= n {
                let (up, ur) = grid[cell - n];
                if self.edges(up, ur)[2] != e[0] {
                    b += 1;
                }
            }
            if let Some(tg) = targets {
                for s in 0..4 {
                    if tg[cell][s].is_some_and(|c| c != e[s]) {
                        b += 1;
                    }
                }
            }
        }
        b
    }

    /// matched II edges of a complete assignment
    #[must_use]
    pub fn ii_matches(&self, grid: &[(u16, u8)]) -> u32 {
        self.ii_max - self.count_breaks(grid, None)
    }

    /// matched rim sides against fixed targets (the realized IB)
    #[must_use]
    pub fn ib_matches(&self, grid: &[(u16, u8)], targets: &RimTargets) -> u32 {
        let mut m = 0;
        for cell in 0..self.cells {
            let e = self.edges(grid[cell].0, grid[cell].1);
            for s in 0..4 {
                if targets[cell][s] == Some(e[s]) {
                    m += 1;
                }
            }
        }
        m
    }

    /// number of rim target sides present (56 for a full E2 frame)
    #[must_use]
    pub fn ib_max(targets: &RimTargets) -> u32 {
        targets
            .iter()
            .map(|t| t.iter().flatten().count() as u32)
            .sum()
    }

    /// outward (rim) sides of a cell: up to 2 (interior corners)
    #[must_use]
    pub fn rim_sides(&self, cell: usize) -> ([usize; 2], usize) {
        let (y, x) = (cell / self.n, cell % self.n);
        let mut sides = [0usize; 2];
        let mut k = 0;
        if y == 0 {
            sides[k] = 0;
            k += 1;
        }
        if y == self.n - 1 {
            sides[k] = 2;
            k += 1;
        }
        if x == 0 {
            sides[k] = 3;
            k += 1;
        }
        if x == self.n - 1 {
            sides[k] = 1;
            k += 1;
        }
        (sides, k)
    }
}

// ------------------------------------------------------------ search tables

/// pack a candidate as pid<<2 | rot (vol-211 encoding)
#[inline]
#[must_use]
pub const fn pack(pid: u16, rot: u8) -> u16 {
    pid << 2 | rot as u16
}

/// Candidate tables, canonical pid space. The hot path is precomputed
/// per-(color, color) candidate LISTS — measured 1.56× faster than bitset
/// intersections on the wall workload (vol-212 head-to-head; the lists ARE
/// the intersection, paid once at build). Per-epoch `shuffle_lists`
/// re-randomizes DFS tie-breaking (the vol-211 mechanism).
///
/// Hint pieces are excluded from all lists: they are only placeable at
/// their forced cells. `rotmask` is kept for the endgame's admissible
/// satisfiability bound (covers ALL pieces, including hints).
pub struct Tables {
    pub rot_edges: Vec<[[u8; 4]; 4]>,
    pub np: usize,
    pub ncolors: usize,
    /// pair_nw[cN * ncolors + cW]: candidates with e[0]==cN && e[3]==cW
    pub pair_nw: Vec<Vec<u16>>,
    /// pair_ne[cN * ncolors + cE]: candidates with e[0]==cN && e[1]==cE
    pub pair_ne: Vec<Vec<u16>>,
    /// single[side][color]: candidates with e[side]==color
    pub single: [Vec<Vec<u16>>; 4],
    /// all (pid, rot) of non-hint pieces
    pub free: Vec<u16>,
    /// rotmask[(side*ncolors + color)*np + pid] = bitmask of rots matching
    rotmask: Vec<u8>,
}

impl Tables {
    pub fn build(model: &InteriorModel, hinted: bool) -> Self {
        let np = model.np;
        let nc = model.ncolors;
        let mut hint_piece = vec![false; np];
        if hinted {
            for &(_, pid, _) in &model.hints {
                hint_piece[pid] = true;
            }
        }
        let rot_edges = model.rot_edges.clone();
        let mut pair_nw = vec![Vec::new(); nc * nc];
        let mut pair_ne = vec![Vec::new(); nc * nc];
        let mut single: [Vec<Vec<u16>>; 4] =
            core::array::from_fn(|_| vec![Vec::new(); nc]);
        let mut free = Vec::with_capacity(np * 4);
        let mut rotmask = vec![0u8; 4 * nc * np];
        for pid in 0..np {
            for rot in 0..4u8 {
                let e = rot_edges[pid][rot as usize];
                for s in 0..4 {
                    rotmask[(s * nc + e[s] as usize) * np + pid] |= 1 << rot;
                }
                if hint_piece[pid] {
                    continue;
                }
                let c = pack(pid as u16, rot);
                pair_nw[e[0] as usize * nc + e[3] as usize].push(c);
                pair_ne[e[0] as usize * nc + e[1] as usize].push(c);
                for s in 0..4 {
                    single[s][e[s] as usize].push(c);
                }
                free.push(c);
            }
        }
        Self { rot_edges, np, ncolors: nc, pair_nw, pair_ne, single, free, rotmask }
    }

    /// fresh tie-breaking for a new DFS epoch
    pub fn shuffle_lists(&mut self, rng: &mut Rng) {
        for v in self.pair_nw.iter_mut().chain(self.pair_ne.iter_mut()) {
            rng.shuffle(v);
        }
        for side in &mut self.single {
            for v in side.iter_mut() {
                rng.shuffle(v);
            }
        }
        rng.shuffle(&mut self.free);
    }

    #[inline]
    #[must_use]
    pub fn rotmask(&self, side: usize, color: u8, pid: usize) -> u8 {
        self.rotmask[(side * self.ncolors + color as usize) * self.np + pid]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn synthetic_solution_is_perfect() {
        for seed in 0..4 {
            let (m, sol, targets) = InteriorModel::synthetic(5, 7, seed);
            assert_eq!(m.count_breaks(&sol, None), 0);
            assert_eq!(m.count_breaks(&sol, Some(&targets)), 0);
            assert_eq!(m.ii_matches(&sol), m.ii_max);
            assert_eq!(m.ib_matches(&sol, &targets), InteriorModel::ib_max(&targets));
            assert_eq!(InteriorModel::ib_max(&targets), 4 * 5);
        }
    }

    #[test]
    fn tables_lists_agree_with_edges() {
        let (m, _, _) = InteriorModel::synthetic(4, 6, 9);
        let t = Tables::build(&m, false);
        for pid in 0..m.np {
            for rot in 0..4u8 {
                let e = t.rot_edges[pid][rot as usize];
                let c = pack(pid as u16, rot);
                let nc = t.ncolors;
                assert!(t.pair_nw[e[0] as usize * nc + e[3] as usize].contains(&c));
                assert!(t.pair_ne[e[0] as usize * nc + e[1] as usize].contains(&c));
                for s in 0..4 {
                    assert!(t.single[s][e[s] as usize].contains(&c));
                    assert!(t.rotmask(s, e[s], pid) & (1 << rot) != 0);
                }
                assert!(t.free.contains(&c));
            }
        }
        // hint exclusion: hinted build drops the hint piece from lists
        let mut m2 = m;
        m2.hints.push((0, 3, 1));
        let t2 = Tables::build(&m2, true);
        assert!(t2.free.iter().all(|&c| c >> 2 != 3));
        assert!(t2.pair_nw.iter().all(|v| v.iter().all(|&c| c >> 2 != 3)));
    }
}
