// Break-DFS over the interior, free-rim or border-anchored.
//
// Mechanics (ported from vol-211 cloister.rs, generalized):
//   - scan order is a permutation of cells (row-major / boustrophedon);
//     a cell's constraints at placement = already-placed neighbors + fixed
//     rim targets from the anchored frame (CLOISTER-II: IB edges are real
//     edges from cell 1, entering the same break budget as II edges);
//   - candidates come from precomputed per-(color,color) lists (pair NW /
//     pair NE / singles), shuffled per epoch — vol-212 measured this 1.56×
//     faster than bitset-intersection candidates (lists ARE the
//     intersection, paid at build time), so the vol-211 architecture
//     stands; extra constraints beyond the pair (bordered last column,
//     bottom-row rim) are post-filters;
//   - scheduled break gates: the (j+1)-th mismatch may only be spent at
//     scan depth ≥ schedule[j]; break candidates violate EXACTLY ONE
//     constraint and only at cells with ≥ 2 constraints;
//   - hints fix (piece, rot), not edge perfection: forced cells pay normal
//     break costs; hard neighbor pre-filters only before the first gate;
//     1 break reserved per unplaced gated hint (else ordinary breaks
//     starve the deep hints — every vol-211 seed died at cell 180);
//   - exact endgame at depth cells−k: optimal completion of the leftovers,
//     anytime-minimizing total breaks across thousands of completions;
//   - optional discrepancy bound (LDS-style): a path may take a
//     non-first candidate at most `max_disc` times.
//   - the vol-211 rim-supply two-pass tie-break is NOT ported (refuted,
//     −2 II).

use std::time::Instant;

use crate::endgame::{exact_tail, exact_tail2};
use crate::model::{
    mask_clear, mask_get, mask_set, InteriorModel, PieceMask, RimTargets, Tables, WORDS,
};
use crate::rng::Rng;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Scan {
    RowMajor,
    Boustro,
    /// CLOISTER-III (vol-213): two fronts — rows 0..seam top-down, then
    /// rows n-1..seam+1 bottom-up — closing at `seam` last. The seam row's
    /// cells have BOTH N and S placed, so the exact endgame there is
    /// two-sided (strictly tighter than a bottom tail), and the leftover
    /// pool damage lands mid-board instead of in the starved last rows.
    /// Both deep hints (row 12) sit EARLY in the bottom front.
    Seam(usize),
}

impl Scan {
    #[must_use]
    pub fn order(self, n: usize) -> Vec<usize> {
        match self {
            Self::RowMajor => (0..n * n).collect(),
            Self::Boustro => {
                let mut v = Vec::with_capacity(n * n);
                for y in 0..n {
                    if y % 2 == 0 {
                        v.extend((0..n).map(|x| y * n + x));
                    } else {
                        v.extend((0..n).rev().map(|x| y * n + x));
                    }
                }
                v
            }
            Self::Seam(seam) => {
                assert!(seam > 0 && seam < n - 1, "seam must be an inner row");
                let mut v = Vec::with_capacity(n * n);
                for y in 0..seam {
                    v.extend((0..n).map(|x| y * n + x));
                }
                for y in (seam + 1..n).rev() {
                    v.extend((0..n).map(|x| y * n + x));
                }
                v.extend((0..n).map(|x| seam * n + x));
                v
            }
        }
    }

    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::RowMajor => "row",
            Self::Boustro => "boustro",
            Self::Seam(_) => "seam",
        }
    }
}

#[derive(Clone, Copy)]
pub enum Src {
    /// neighbor placed earlier in scan order: read its facing side
    Placed { cell: u16, their_side: u8 },
    /// rim color target from the anchored frame
    Fixed(u8),
}

/// priors-buffer entries: bits 0-11 = pid<<2|rot (≤ 1023), bits 12-13 = cost
const PB_COST_SHIFT: u16 = 12;
const PB_CODE_MASK: u16 = 0x0FFF;

#[derive(Clone, Copy)]
enum Tab {
    /// pair_nw keyed by (ccol[n], ccol[w])
    PairNW { n: u8, w: u8 },
    PairNE { n: u8, e: u8 },
    PairSW { s: u8, w: u8 },
    Single { side: u8, i: u8 },
    Free,
}

/// one candidate segment: a base list + post-filters. Segment 0 is the
/// cost-0 segment (all constraints matched); cost-1 segments violate
/// exactly one constraint; cost-2 segments (vol-213 double-break: the
/// community strict-460s contain 4-5 cells paying two mismatches at
/// placement — unreachable with cost-1 only) violate exactly two.
/// Non-zero-cost segments exist only for cells with k ≥ 2.
#[derive(Clone, Copy)]
struct Seg {
    tab: Tab,
    /// constraint indices that must additionally match
    extra: [u8; 3],
    n_extra: u8,
    /// constraint indices that must mismatch
    violate: [u8; 2],
    n_violate: u8,
}

pub struct CellPlan {
    pub cell: u16,
    /// number of constraints known at placement time
    pub k: u8,
    /// my side for constraint i
    pub sides: [u8; 4],
    pub src: [Src; 4],
    /// my sides facing LATER in-grid cells (LEDGER: demands I expose)
    pub fwd: [u8; 4],
    pub n_fwd: u8,
    segs: Vec<Seg>,
}

fn make_seg(sides: &[u8; 4], k: usize, exclude: &[usize]) -> Seg {
    let active: Vec<usize> = (0..k).filter(|i| !exclude.contains(i)).collect();
    let find = |side: u8| active.iter().copied().find(|&i| sides[i] == side);
    let (i_n, i_e, i_s, i_w) = (find(0), find(1), find(2), find(3));
    let (tab, covered): (Tab, Vec<usize>) = match (i_n, i_w, i_e, i_s) {
        (Some(n), Some(w), _, _) => (Tab::PairNW { n: n as u8, w: w as u8 }, vec![n, w]),
        (Some(n), None, Some(e), _) => (Tab::PairNE { n: n as u8, e: e as u8 }, vec![n, e]),
        (None, Some(w), _, Some(s)) => (Tab::PairSW { s: s as u8, w: w as u8 }, vec![s, w]),
        (Some(n), None, None, _) => (Tab::Single { side: 0, i: n as u8 }, vec![n]),
        (None, Some(w), _, None) => (Tab::Single { side: 3, i: w as u8 }, vec![w]),
        (None, None, Some(e), _) => (Tab::Single { side: 1, i: e as u8 }, vec![e]),
        (None, None, None, _) => i_s.map_or((Tab::Free, vec![]), |s| {
            (Tab::Single { side: 2, i: s as u8 }, vec![s])
        }),
    };
    let mut extra = [0u8; 3];
    let mut n_extra = 0u8;
    for &i in &active {
        if !covered.contains(&i) {
            extra[n_extra as usize] = i as u8;
            n_extra += 1;
        }
    }
    let mut violate = [0u8; 2];
    for (vi, &i) in exclude.iter().enumerate() {
        violate[vi] = i as u8;
    }
    Seg {
        tab,
        extra,
        n_extra,
        violate,
        n_violate: exclude.len() as u8,
    }
}

pub fn build_plans(
    model: &InteriorModel,
    scan: &[usize],
    targets: Option<&RimTargets>,
) -> Vec<CellPlan> {
    let n = model.n;
    let mut pos_in_scan = vec![0usize; model.cells];
    for (d, &c) in scan.iter().enumerate() {
        pos_in_scan[c] = d;
    }
    scan.iter()
        .map(|&cell| {
            let (y, x) = (cell / n, cell % n);
            let mut sides = [0u8; 4];
            let mut src = [Src::Fixed(0); 4];
            let mut k = 0u8;
            let mut fwd = [0u8; 4];
            let mut n_fwd = 0u8;
            let nb: [(usize, Option<usize>); 4] = [
                (0, (y > 0).then(|| cell - n)),
                (1, (x + 1 < n).then(|| cell + 1)),
                (2, (y + 1 < n).then(|| cell + n)),
                (3, (x > 0).then(|| cell - 1)),
            ];
            for (s, nc) in nb {
                match nc {
                    Some(ncell) => {
                        if pos_in_scan[ncell] < pos_in_scan[cell] {
                            sides[k as usize] = s as u8;
                            src[k as usize] = Src::Placed {
                                cell: ncell as u16,
                                their_side: ((s + 2) % 4) as u8,
                            };
                            k += 1;
                        } else {
                            fwd[n_fwd as usize] = s as u8;
                            n_fwd += 1;
                        }
                    }
                    None => {
                        if let Some(tg) = targets {
                            if let Some(c) = tg[cell][s] {
                                sides[k as usize] = s as u8;
                                src[k as usize] = Src::Fixed(c);
                                k += 1;
                            }
                        }
                    }
                }
            }
            // order: cost-0, then all cost-1, then all cost-2 (cheap-first;
            // nseg at runtime exposes a prefix of this list)
            let mut segs = vec![make_seg(&sides, k as usize, &[])];
            if k >= 2 {
                for i in 0..k as usize {
                    segs.push(make_seg(&sides, k as usize, &[i]));
                }
                for i in 0..k as usize {
                    for j in i + 1..k as usize {
                        segs.push(make_seg(&sides, k as usize, &[i, j]));
                    }
                }
            }
            CellPlan { cell: cell as u16, k, sides, src, fwd, n_fwd, segs }
        })
        .collect()
}

/// LEDGER (vol-214): admissible color-deficit accounting. f[c] = open
/// demands of color c (rim targets on empty cells + placed sides facing
/// empty cells); s[c] = sides of color c among available pieces (hint
/// pieces included — they deploy at forced cells). Every surplus demand
/// max(0, f[c]−s[c]) is ≥ 1 future mismatch (walked or in-tail), so
/// spent + deficit > budget is a sound prune that turns the schedule
/// length into a TOTAL-breaks cap (record hunt: budget 19 ⇔ ≥ 461).
struct Ledger {
    f: Vec<u32>,
    s: Vec<u32>,
    deficit: u32,
}

impl Ledger {
    fn surplus(&self, c: usize) -> u32 {
        self.f[c].saturating_sub(self.s[c])
    }
    fn add_f(&mut self, c: u8, up: bool) {
        let c = c as usize;
        let before = self.surplus(c);
        if up {
            self.f[c] += 1;
        } else {
            self.f[c] -= 1;
        }
        self.deficit = self.deficit + self.surplus(c) - before;
    }
    fn add_s(&mut self, c: u8, up: bool) {
        let c = c as usize;
        let before = self.surplus(c);
        if up {
            self.s[c] += 1;
        } else {
            self.s[c] -= 1;
        }
        self.deficit = self.deficit + self.surplus(c) - before;
    }
    /// piece (pid, rot) placed at `plan`'s cell: consumes one demand per
    /// constraint, exposes fwd-side demands, removes its 4 sides from
    /// supply. `ccol` = the constraint colors at this cell.
    fn place(&mut self, tables: &Tables, plan: &CellPlan, ccol: &[u8; 4], pid: u16, rot: u8) {
        for i in 0..plan.k as usize {
            self.add_f(ccol[i], false);
        }
        let e = &tables.rot_edges[pid as usize][rot as usize];
        for i in 0..plan.n_fwd as usize {
            self.add_f(e[plan.fwd[i] as usize], true);
        }
        let base = &tables.rot_edges[pid as usize][0];
        for &c in base {
            self.add_s(c, false);
        }
    }
    fn unplace(&mut self, tables: &Tables, plan: &CellPlan, ccol: &[u8; 4], pid: u16, rot: u8) {
        for i in 0..plan.k as usize {
            self.add_f(ccol[i], true);
        }
        let e = &tables.rot_edges[pid as usize][rot as usize];
        for i in 0..plan.n_fwd as usize {
            self.add_f(e[plan.fwd[i] as usize], false);
        }
        let base = &tables.rot_edges[pid as usize][0];
        for &c in base {
            self.add_s(c, true);
        }
    }
}

/// CAIRN (vol-214): cross-epoch frontier nogoods. State key = Zobrist
/// XOR over {available pieces} ∪ {active frontier edges (consumer cell,
/// consumer side, color)} — rim targets on empty cells start active;
/// placing a cell consumes its constraint edges and exposes its
/// fwd-side edges (the consumer keys coincide, so place/unplace is one
/// XOR toggle). The avail set implies depth, so gates/hint_after are
/// keyed; spent is stored. A refuted (frontier, spent) prunes any
/// revisit with spent' ≥ spent (less budget room). Inserts only on
/// CLEAN exhaustion (attempt ran, no TT-prune, free cell) and only when
/// the explored set is order-independent (no LDS, no perturb). Sound
/// across the anytime incumbent because best_complete is monotone
/// non-increasing. 64-bit tags ⇒ false-prune probability negligible
/// but nonzero (record claims are independently verified anyway).
struct Cairn {
    z_avail: Vec<u64>,
    z_edge: Vec<u64>,
    ncolors: usize,
    n: usize,
    h: u64,
    h0: u64,
    /// (tag, spent+1); spent+1 == 0 means empty slot
    tt: Vec<(u32, u32)>,
    mask: usize,
}

impl Cairn {
    fn new(model: &InteriorModel, tables: &Tables, targets: Option<&RimTargets>) -> Self {
        let mut rng = Rng::new(0xCA12_57AF_0123_4567);
        let ncolors = tables.ncolors;
        let z_avail: Vec<u64> = (0..model.np).map(|_| rng.next_u64()).collect();
        let z_edge: Vec<u64> = (0..model.cells * 4 * ncolors)
            .map(|_| rng.next_u64())
            .collect();
        let mut h0 = 0u64;
        for &z in &z_avail {
            h0 ^= z;
        }
        let ze = |cell: usize, side: usize, color: u8| {
            z_edge[(cell * 4 + side) * ncolors + color as usize]
        };
        if let Some(tg) = targets {
            for (cell, t) in tg.iter().enumerate() {
                for (side, c) in t.iter().enumerate() {
                    if let Some(c) = c {
                        h0 ^= ze(cell, side, *c);
                    }
                }
            }
        }
        const TT_BITS: usize = 22;
        Self {
            z_avail,
            z_edge,
            ncolors,
            n: model.n,
            h: h0,
            h0,
            tt: vec![(0, 0); 1 << TT_BITS],
            mask: (1 << TT_BITS) - 1,
        }
    }

    fn ze(&self, cell: usize, side: usize, color: u8) -> u64 {
        self.z_edge[(cell * 4 + side) * self.ncolors + color as usize]
    }

    /// place == unplace (XOR involution)
    fn toggle(&mut self, tables: &Tables, plan: &CellPlan, ccol: &[u8; 4], pid: u16, rot: u8) {
        self.h ^= self.z_avail[pid as usize];
        let cell = plan.cell as usize;
        for i in 0..plan.k as usize {
            self.h ^= self.ze(cell, plan.sides[i] as usize, ccol[i]);
        }
        let e = &tables.rot_edges[pid as usize][rot as usize];
        for i in 0..plan.n_fwd as usize {
            let s = plan.fwd[i] as usize;
            let nc = match s {
                0 => cell - self.n,
                1 => cell + 1,
                2 => cell + self.n,
                _ => cell - 1,
            };
            self.h ^= self.ze(nc, (s + 2) % 4, e[s]);
        }
    }

    fn probe(&self, spent: u32) -> bool {
        let e = self.tt[(self.h as usize) & self.mask];
        e.1 != 0 && e.0 == (self.h >> 32) as u32 && e.1 - 1 <= spent
    }

    fn insert(&mut self, spent: u32) {
        let i = (self.h as usize) & self.mask;
        let tag = (self.h >> 32) as u32;
        let e = &mut self.tt[i];
        // keep the more general (lower-spent) entry on tag match
        if e.1 == 0 || e.0 != tag || e.1 - 1 > spent {
            *e = (tag, spent + 1);
        }
    }
}

/// constraint colors of `plan`'s cell under the current grid (neighbors
/// referenced by the plan are guaranteed placed)
fn ccol_of(tables: &Tables, plan: &CellPlan, grid: &[(u16, u8)]) -> [u8; 4] {
    let mut ccol = [0u8; 4];
    for i in 0..plan.k as usize {
        ccol[i] = match plan.src[i] {
            Src::Fixed(c) => c,
            Src::Placed { cell: nc, their_side } => {
                let (np_, nr) = grid[nc as usize];
                tables.rot_edges[np_ as usize][nr as usize][their_side as usize]
            }
        };
    }
    ccol
}

#[derive(Clone, Copy)]
struct Cursor {
    seg: u8,
    idx: u32,
    started: bool,
}

impl Cursor {
    const FRESH: Self = Self { seg: 0, idx: 0, started: false };
}

// --------------------------------------------------------------------- run

pub struct DfsParams {
    pub seed: u64,
    pub budget_ms: u64,
    pub restart_ms: u64,
    pub hinted: bool,
    /// ascending depth gates; len = break budget
    pub schedule: Vec<usize>,
    /// 0 = off; clamped to n (one row)
    pub exact_tail_k: usize,
    /// node cap per exact_tail call (vol-213: witness A's 13-mismatch
    /// 3-double tail needs > 2M nodes — the default cap returned the
    /// greedy 15 and silently cost the replay 2 breaks)
    pub exact_tail_cap: u64,
    /// two-row endgame as the in-DFS trigger (vol-211: post-hoc only)
    pub tail2: bool,
    /// node cap per in-DFS tail2 call
    pub tail2_cap: u64,
    /// LDS-style bound on non-first choices per path
    pub max_disc: Option<u32>,
    pub scan: Scan,
    /// REPLAY mode (vol-213): with priors, ALSO drain break-segment
    /// candidates into the weight-ordered buffer, sorted by
    /// (Reverse(weight), cost) — a high-weight break candidate is taken
    /// BEFORE unseen cost-0 candidates, so a witness walk pays its breaks
    /// at the witness's break cells instead of detouring into cost-0
    /// subtrees. Sound because break_open is invariant within a cell
    /// instance (any backtrack through d resets the cursor).
    pub prior_over_cost: bool,
    /// max breaks payable at ONE free cell (vol-213 double-break: the
    /// community strict-460s have 4-5 cells paying 2 mismatches at
    /// placement — unreachable at 1). 1 = vol-212 behavior; 2 enables
    /// cost-2 segments, each gated as two break spends.
    pub max_cell_breaks: u8,
    /// deviate-then-replay (vol-213): per epoch, sample one depth in
    /// [lo, hi); at that depth the prior buffer's TOP candidate is
    /// excluded for the whole epoch — forcing a single deviation off the
    /// witness walk, with fully guided continuation. Samples the
    /// perfect-prefix neighborhood one deviation at a time.
    pub replay_perturb: Option<(usize, usize)>,
    /// LEDGER (vol-214): admissible color-deficit prune — backtrack any
    /// state with spent + Σ_c max(0, F_c − S_c) > budget. Turns the
    /// schedule length into a TOTAL-breaks cap (walked + tail).
    pub ledger: bool,
    /// CAIRN (vol-214): cross-epoch frontier-nogood table. Auto-disabled
    /// when max_disc or replay_perturb is set (explored set becomes
    /// order-dependent, inserts would be unsound).
    pub cairn: bool,
}

impl Default for DfsParams {
    fn default() -> Self {
        Self {
            seed: 1,
            budget_ms: 30_000,
            restart_ms: 5_000,
            hinted: false,
            schedule: Vec::new(),
            exact_tail_k: 0,
            exact_tail_cap: crate::endgame::TAIL_CAP,
            tail2: false,
            tail2_cap: 30_000,
            max_disc: None,
            scan: Scan::RowMajor,
            prior_over_cost: false,
            max_cell_breaks: 1,
            replay_perturb: None,
            ledger: false,
            cairn: false,
        }
    }
}

pub struct DfsResult {
    pub seed: u64,
    pub max_depth: usize,
    pub nodes: u64,
    pub ms_at_max: u128,
    /// best complete assignment and its total breaks
    /// (II mismatches + rim-target mismatches)
    pub complete: Option<(Vec<(u16, u8)>, u32)>,
    pub completes_found: u64,
    /// cells scan[0..max_depth] at the max-depth moment
    pub best_prefix: Vec<(u16, u8)>,
    pub epochs: u64,
    /// choke map (vol-213): death_hist[d] = # epochs whose deepest reach
    /// was d when they ended (restart timeout or root exhaustion)
    pub death_hist: Vec<u32>,
}

#[allow(clippy::too_many_lines)]
pub fn dfs_run(
    model: &InteriorModel,
    targets: Option<&RimTargets>,
    priors: Option<&crate::priors::Priors>,
    p: &DfsParams,
) -> DfsResult {
    let cells = model.cells;
    let n = model.n;
    let scan = p.scan.order(n);
    let plans = build_plans(model, &scan, targets);
    let mut pos_in_scan = vec![0usize; cells];
    for (d, &c) in scan.iter().enumerate() {
        pos_in_scan[c] = d;
    }
    let budget = p.schedule.len() as u32;
    let first_gate = p.schedule.first().copied().unwrap_or(usize::MAX);

    // pre-gate hint protection: neighbors facing a pre-gate forced cell
    // must present the hint's color (sound: those mismatches are unpayable)
    let mut req: Vec<[Option<u8>; 4]> = vec![[None; 4]; cells];
    let mut forced_by_cell: Vec<Option<(u16, u8)>> = vec![None; cells];
    let mut hint_scanpos: Vec<usize> = Vec::new();
    if p.hinted {
        for &(cell, pid, rot) in &model.hints {
            forced_by_cell[cell] = Some((pid as u16, rot));
            let d = pos_in_scan[cell];
            hint_scanpos.push(d);
            if d < first_gate {
                let e = model.rot_edges[pid][rot as usize];
                let plan = &plans[d];
                for i in 0..plan.k as usize {
                    if let Src::Placed { cell: nc, their_side } = plan.src[i] {
                        req[nc as usize][their_side as usize] =
                            Some(e[plan.sides[i] as usize]);
                    }
                }
            }
        }
    }
    // break reservation: # gated (deep) forced cells at scan pos >= d
    let mut hint_after = vec![0u32; cells + 1];
    for d in (0..cells).rev() {
        let deep_hint_here = hint_scanpos.iter().any(|&hd| hd == d && hd >= first_gate);
        hint_after[d] = hint_after[d + 1] + u32::from(deep_hint_here);
    }
    let cell_has_req: Vec<bool> = req
        .iter()
        .map(|r| r.iter().any(Option::is_some))
        .collect();
    // schedule padded with a sentinel so the hot loop indexes directly
    let mut sched_at = p.schedule.clone();
    sched_at.push(usize::MAX);

    let k_exact = if p.tail2 { 2 * n } else { p.exact_tail_k.min(n) };
    if p.tail2 {
        // the column-pair endgame is hard-wired to the last two rows
        assert!(
            !matches!(p.scan, Scan::Seam(_)),
            "tail2 requires a row-sequential scan"
        );
        assert!(
            scan[cells - 2 * n..].iter().all(|&c| c >= (n - 2) * n),
            "scan tail must cover the last two rows"
        );
    }
    // exact_tail itself is scan-generic: tail-cell constraints come from
    // plans, which only ever reference earlier scan positions (the seam
    // scan's closure row gets two-sided N+S constraints this way).

    let trace = std::env::var_os("E2_TRACE").is_some();
    let mut rng = Rng::new(p.seed);
    let mut tables = Tables::build(model, p.hinted);
    let mut grid: Vec<(u16, u8)> = vec![(u16::MAX, 0); cells];
    let mut cursors: Vec<Cursor> = vec![Cursor::FRESH; cells + 1];
    let mut cost_at = vec![0u32; cells + 1];
    let mut yields = vec![0u32; cells + 1];
    let mut disc_flag = vec![false; cells + 1];
    // priors: per-depth cost-0 candidate buffers, weight-ordered at the
    // first visit of a cell instance (list shuffle supplies tie-breaking)
    let mut pbuf: Vec<Vec<u16>> = vec![Vec::new(); cells + 1];
    let mut pbuf_idx = vec![0u32; cells + 1];
    let mut led = Ledger {
        f: vec![0; tables.ncolors],
        s: vec![0; tables.ncolors],
        deficit: 0,
    };
    let cairn_on = p.cairn && p.max_disc.is_none() && p.replay_perturb.is_none();
    let mut cairn = cairn_on.then(|| Cairn::new(model, &tables, targets));
    let mut tt_pruned = vec![false; cells + 1];

    let mut max_depth = 0usize;
    let mut death_hist = vec![0u32; cells + 1];
    let mut ms_at_max: u128 = 0;
    let mut best_prefix: Vec<(u16, u8)> = Vec::new();
    let mut best_complete: Option<(Vec<(u16, u8)>, u32)> = None;
    let mut completes_found: u64 = 0;
    let mut nodes: u64 = 0;
    let mut epochs: u64 = 0;
    let t0 = Instant::now();

    'epoch: loop {
        epochs += 1;
        tables.shuffle_lists(&mut rng);
        let mut avail: PieceMask = [0; WORDS];
        for pid in 0..model.np as u16 {
            mask_set(&mut avail, pid);
        }
        grid.iter_mut().for_each(|g| *g = (u16::MAX, 0));
        cursors.iter_mut().for_each(|c| *c = Cursor::FRESH);
        cost_at.iter_mut().for_each(|c| *c = 0);
        yields.iter_mut().for_each(|y| *y = 0);
        disc_flag.iter_mut().for_each(|f| *f = false);
        let mut spent: u32 = 0;
        let mut disc: u32 = 0;
        let mut epoch_max = 0usize;
        let skip_depth: usize = p.replay_perturb.map_or(usize::MAX, |(lo, hi)| {
            lo + (rng.next_u64() as usize) % (hi - lo).max(1)
        });
        if p.ledger {
            led.f.iter_mut().for_each(|v| *v = 0);
            led.s.iter_mut().for_each(|v| *v = 0);
            for pid in 0..model.np {
                for &c in &tables.rot_edges[pid][0] {
                    led.s[c as usize] += 1;
                }
            }
            if let Some(tg) = targets {
                for t in tg {
                    for c in t.iter().flatten() {
                        led.f[*c as usize] += 1;
                    }
                }
            }
            led.deficit = (0..tables.ncolors).map(|c| led.surplus(c)).sum();
        }
        if let Some(ca) = cairn.as_mut() {
            ca.h = ca.h0;
        }
        tt_pruned.iter_mut().for_each(|t| *t = false);
        let epoch_t0 = Instant::now();

        let mut d = 0usize;
        let mut backtrack_now = false;
        loop {
            // LEDGER prune: state cannot complete within total budget
            if p.ledger && !backtrack_now && spent + led.deficit > budget {
                backtrack_now = true;
            }
            if k_exact > 0 && d == cells - k_exact && !backtrack_now {
                let mut rest: Vec<u16> = Vec::with_capacity(k_exact);
                for pid in 0..model.np as u16 {
                    if mask_get(&avail, pid) {
                        rest.push(pid);
                    }
                }
                let abort_at = best_complete
                    .as_ref()
                    .map_or(u32::MAX, |&(_, b)| b.saturating_sub(spent));
                if abort_at > 0 {
                    let (mis, asn) = if p.tail2 {
                        exact_tail2(
                            model, &tables, &grid, &rest, &forced_by_cell, targets,
                            abort_at, p.tail2_cap,
                        )
                    } else {
                        exact_tail(
                            &tables, &plans, &scan, &mut grid, d, &rest,
                            &forced_by_cell, abort_at, p.exact_tail_cap,
                        )
                    };
                    completes_found += 1;
                    if best_complete.as_ref().is_none_or(|&(_, b)| spent + mis < b) {
                        let mut full = grid.clone();
                        if p.tail2 {
                            let start = (n - 2) * n;
                            for (j, &pr) in asn.iter().enumerate() {
                                full[start + j] = pr;
                            }
                        } else {
                            for (j, &pr) in asn.iter().enumerate() {
                                full[scan[d + j]] = pr;
                            }
                        }
                        let recount = model.count_breaks(&full, targets);
                        assert_eq!(recount, spent + mis, "endgame break accounting");
                        best_complete = Some((full.clone(), spent + mis));
                        if spent + mis == 0 {
                            return DfsResult {
                                seed: p.seed,
                                max_depth: cells,
                                nodes,
                                ms_at_max: t0.elapsed().as_millis(),
                                complete: best_complete,
                                completes_found,
                                best_prefix: full,
                                epochs,
                                death_hist,
                            };
                        }
                    }
                }
                backtrack_now = true;
            }
            if d == cells {
                let recount = model.count_breaks(&grid, targets);
                assert_eq!(recount, spent, "break accounting");
                completes_found += 1;
                if best_complete.as_ref().is_none_or(|&(_, b)| spent < b) {
                    best_complete = Some((grid.clone(), spent));
                }
                if spent == 0 {
                    return DfsResult {
                        seed: p.seed,
                        max_depth: cells,
                        nodes,
                        ms_at_max: t0.elapsed().as_millis(),
                        complete: best_complete,
                        completes_found,
                        best_prefix: grid,
                        epochs,
                        death_hist,
                    };
                }
                backtrack_now = true;
            }
            nodes += 1;
            if nodes & 0xFFFF == 0 {
                if t0.elapsed().as_millis() as u64 >= p.budget_ms {
                    return DfsResult {
                        seed: p.seed,
                        max_depth,
                        nodes,
                        ms_at_max,
                        complete: best_complete,
                        completes_found,
                        best_prefix,
                        epochs,
                        death_hist,
                    };
                }
                if epoch_t0.elapsed().as_millis() as u64 >= p.restart_ms {
                    death_hist[epoch_max] += 1;
                    continue 'epoch;
                }
            }

            let was_bt = backtrack_now;
            let mut placed = false;
            if !backtrack_now {
                let plan = &plans[d];
                let cell = plan.cell as usize;
                if let Some((fp, fr)) = forced_by_cell[cell] {
                    if !cursors[d].started && mask_get(&avail, fp) {
                        cursors[d].started = true;
                        let e = tables.rot_edges[fp as usize][fr as usize];
                        let fcol = ccol_of(&tables, plan, &grid);
                        let mut cost = 0u32;
                        for i in 0..plan.k as usize {
                            if e[plan.sides[i] as usize] != fcol[i] {
                                cost += 1;
                            }
                        }
                        let gate_ok = cost == 0
                            || (spent + cost <= budget
                                && d >= p.schedule[(spent + cost - 1) as usize]);
                        if gate_ok {
                            grid[cell] = (fp, fr);
                            mask_clear(&mut avail, fp);
                            cost_at[d] = cost;
                            spent += cost;
                            if p.ledger {
                                led.place(&tables, plan, &fcol, fp, fr);
                            }
                            if let Some(ca) = cairn.as_mut() {
                                ca.toggle(&tables, plan, &fcol, fp, fr);
                            }
                            placed = true;
                        }
                    }
                } else {
                    let mut ccol = [0u8; 4];
                    for i in 0..plan.k as usize {
                        ccol[i] = match plan.src[i] {
                            Src::Fixed(c) => c,
                            Src::Placed { cell: nc, their_side } => {
                                let (np_, nr) = grid[nc as usize];
                                tables.rot_edges[np_ as usize][nr as usize]
                                    [their_side as usize]
                            }
                        };
                    }
                    let break1_open = spent + 1 + hint_after[d] <= budget
                        && d >= sched_at[(spent as usize).min(budget as usize)]
                        && plan.k >= 2;
                    // paying 2 at once needs room for both AND the
                    // (spent+2)-th gate reached (sorted schedule ⇒ implies
                    // the (spent+1)-th); break2_open ⊆ break1_open
                    let break2_open = p.max_cell_breaks >= 2
                        && spent + 2 + hint_after[d] <= budget
                        && d >= sched_at[(spent as usize + 1).min(budget as usize)]
                        && plan.k >= 2;
                    // LDS: once the discrepancy budget is full, a cell that
                    // already yielded may not deviate further — unless it
                    // already holds a counted deviation
                    let lds_block = p
                        .max_disc
                        .is_some_and(|m| disc >= m && yields[d] >= 1 && !disc_flag[d]);
                    // CAIRN probe at instance start: a recorded nogood with
                    // ≤ spent kills the whole instance before enumeration
                    if let Some(ca) = cairn.as_ref() {
                        if !cursors[d].started && ca.probe(spent) {
                            tt_pruned[d] = true;
                        }
                    }
                    if !lds_block && !tt_pruned[d] {
                        let mut cur = cursors[d];
                        let n1 = plan.k as usize;
                        let nseg = if break2_open {
                            1 + n1 + n1 * (n1 - 1) / 2
                        } else if break1_open {
                            1 + n1
                        } else {
                            1
                        };
                        let rq = &req[cell];
                        let has_req = cell_has_req[cell];
                        // priors: cost-0 candidates are drained into a
                        // weight-ordered buffer at the first visit of the
                        // instance (the per-epoch list shuffle remains the
                        // tie-break); break segments stay lazy via cursor —
                        // unless prior_over_cost (REPLAY), which drains ALL
                        // open segments and sorts (Reverse(weight), cost)
                        if let Some(pri) = priors {
                            if !cur.started {
                                cur.started = true;
                                let nfill = if p.prior_over_cost && break1_open {
                                    nseg
                                } else {
                                    1
                                };
                                cur.seg = nfill as u8;
                                cur.idx = 0;
                                let buf = &mut pbuf[d];
                                buf.clear();
                                for seg in plan.segs.iter().take(nfill) {
                                    let list: &[u16] = match seg.tab {
                                        Tab::PairNW { n: ni, w: wi } => {
                                            &tables.pair_nw[ccol[ni as usize] as usize
                                                * tables.ncolors
                                                + ccol[wi as usize] as usize]
                                        }
                                        Tab::PairNE { n: ni, e: ei } => {
                                            &tables.pair_ne[ccol[ni as usize] as usize
                                                * tables.ncolors
                                                + ccol[ei as usize] as usize]
                                        }
                                        Tab::PairSW { s: si2, w: wi } => {
                                            &tables.pair_sw[ccol[si2 as usize] as usize
                                                * tables.ncolors
                                                + ccol[wi as usize] as usize]
                                        }
                                        Tab::Single { side, i } => {
                                            &tables.single[side as usize]
                                                [ccol[i as usize] as usize]
                                        }
                                        Tab::Free => &tables.free,
                                    };
                                    for &c in list {
                                        let pid = c >> 2;
                                        if !mask_get(&avail, pid) {
                                            continue;
                                        }
                                        let rot = (c & 3) as u8;
                                        let e = &tables.rot_edges[pid as usize][rot as usize];
                                        let mut ok = true;
                                        for xi in 0..seg.n_extra as usize {
                                            let i = seg.extra[xi] as usize;
                                            if e[plan.sides[i] as usize] != ccol[i] {
                                                ok = false;
                                                break;
                                            }
                                        }
                                        if !ok {
                                            continue;
                                        }
                                        let mut viol = true;
                                        for vi in 0..seg.n_violate as usize {
                                            let i = seg.violate[vi] as usize;
                                            if e[plan.sides[i] as usize] == ccol[i] {
                                                viol = false;
                                                break;
                                            }
                                        }
                                        if !viol {
                                            continue;
                                        }
                                        if has_req
                                            && (0..4).any(|s| {
                                                rq[s].is_some_and(|c2| c2 != e[s])
                                            })
                                        {
                                            continue;
                                        }
                                        buf.push(
                                            c | (u16::from(seg.n_violate) << PB_COST_SHIFT),
                                        );
                                    }
                                }
                                buf.sort_by_key(|&c| {
                                    (
                                        std::cmp::Reverse(pri.weight(
                                            cell,
                                            (c & PB_CODE_MASK) >> 2,
                                            (c & 3) as u8,
                                        )),
                                        c >> PB_COST_SHIFT,
                                    )
                                });
                                // deviate-then-replay: at the epoch's
                                // sampled depth, never take the top
                                // candidate (forces one deviation)
                                pbuf_idx[d] = u32::from(d == skip_depth && buf.len() > 1);
                            }
                            if (pbuf_idx[d] as usize) < pbuf[d].len() {
                                let raw = pbuf[d][pbuf_idx[d] as usize];
                                pbuf_idx[d] += 1;
                                let cost = u32::from(raw >> PB_COST_SHIFT);
                                let c = raw & PB_CODE_MASK;
                                let (pid, rot) = (c >> 2, (c & 3) as u8);
                                grid[cell] = (pid, rot);
                                mask_clear(&mut avail, pid);
                                cost_at[d] = cost;
                                spent += cost;
                                if p.ledger {
                                    led.place(&tables, plan, &ccol, pid, rot);
                                }
                                if let Some(ca) = cairn.as_mut() {
                                    ca.toggle(&tables, plan, &ccol, pid, rot);
                                }
                                yields[d] += 1;
                                if yields[d] == 2 {
                                    disc += 1;
                                    disc_flag[d] = true;
                                }
                                placed = true;
                            }
                        }
                        cur.started = true;
                        'segs: while !placed && (cur.seg as usize) < nseg {
                            let seg = &plan.segs[cur.seg as usize];
                            let list: &[u16] = match seg.tab {
                                Tab::PairNW { n: ni, w: wi } => {
                                    &tables.pair_nw[ccol[ni as usize] as usize
                                        * tables.ncolors
                                        + ccol[wi as usize] as usize]
                                }
                                Tab::PairNE { n: ni, e: ei } => {
                                    &tables.pair_ne[ccol[ni as usize] as usize
                                        * tables.ncolors
                                        + ccol[ei as usize] as usize]
                                }
                                Tab::PairSW { s: si, w: wi } => {
                                    &tables.pair_sw[ccol[si as usize] as usize
                                        * tables.ncolors
                                        + ccol[wi as usize] as usize]
                                }
                                Tab::Single { side, i } => {
                                    &tables.single[side as usize][ccol[i as usize] as usize]
                                }
                                Tab::Free => &tables.free,
                            };
                            while (cur.idx as usize) < list.len() {
                                let c = list[cur.idx as usize];
                                cur.idx += 1;
                                let pid = c >> 2;
                                if !mask_get(&avail, pid) {
                                    continue;
                                }
                                let rot = (c & 3) as u8;
                                let e = &tables.rot_edges[pid as usize][rot as usize];
                                let mut ok = true;
                                for xi in 0..seg.n_extra as usize {
                                    let i = seg.extra[xi] as usize;
                                    if e[plan.sides[i] as usize] != ccol[i] {
                                        ok = false;
                                        break;
                                    }
                                }
                                if !ok {
                                    continue;
                                }
                                let mut viol = true;
                                for vi in 0..seg.n_violate as usize {
                                    let i = seg.violate[vi] as usize;
                                    if e[plan.sides[i] as usize] == ccol[i] {
                                        viol = false;
                                        break;
                                    }
                                }
                                if !viol {
                                    continue;
                                }
                                if has_req
                                    && (0..4).any(|s| rq[s].is_some_and(|c2| c2 != e[s]))
                                {
                                    continue;
                                }
                                let cost = u32::from(seg.n_violate);
                                grid[cell] = (pid, rot);
                                mask_clear(&mut avail, pid);
                                cost_at[d] = cost;
                                spent += cost;
                                if p.ledger {
                                    led.place(&tables, plan, &ccol, pid, rot);
                                }
                                if let Some(ca) = cairn.as_mut() {
                                    ca.toggle(&tables, plan, &ccol, pid, rot);
                                }
                                yields[d] += 1;
                                if yields[d] == 2 {
                                    disc += 1;
                                    disc_flag[d] = true;
                                }
                                placed = true;
                                break 'segs;
                            }
                            cur.seg += 1;
                            cur.idx = 0;
                        }
                        cursors[d] = cur;
                    }
                }
            }

            if placed {
                if trace && epochs == 1 && d >= 160 {
                    let cell = plans[d].cell as usize;
                    eprintln!(
                        "TRACE d={d} cell={cell} pid={} rot={} cost={} spent={spent}",
                        grid[cell].0, grid[cell].1, cost_at[d]
                    );
                }
                d += 1;
                if d > epoch_max {
                    epoch_max = d;
                }
                if d > max_depth {
                    max_depth = d;
                    ms_at_max = t0.elapsed().as_millis();
                    best_prefix = (0..d).map(|j| grid[scan[j]]).collect();
                }
            } else {
                backtrack_now = false;
                // CAIRN insert: clean exhaustion of a free-cell instance
                // (attempt ran, not a TT replay, not an endgame/ledger
                // forced backtrack)
                if let Some(ca) = cairn.as_mut() {
                    if !was_bt
                        && !tt_pruned[d]
                        && d < cells
                        && forced_by_cell[plans[d].cell as usize].is_none()
                    {
                        ca.insert(spent);
                    }
                }
                tt_pruned[d] = false;
                cursors[d] = Cursor::FRESH;
                yields[d] = 0;
                if disc_flag[d] {
                    disc -= 1;
                    disc_flag[d] = false;
                }
                if d == 0 {
                    death_hist[epoch_max] += 1;
                    continue 'epoch;
                }
                d -= 1;
                let cell = plans[d].cell as usize;
                let (pid, rot) = grid[cell];
                if p.ledger || cairn.is_some() {
                    let fcol = ccol_of(&tables, &plans[d], &grid);
                    if p.ledger {
                        led.unplace(&tables, &plans[d], &fcol, pid, rot);
                    }
                    if let Some(ca) = cairn.as_mut() {
                        ca.toggle(&tables, &plans[d], &fcol, pid, rot);
                    }
                }
                mask_set(&mut avail, pid);
                grid[cell] = (u16::MAX, 0);
                spent -= cost_at[d];
                cost_at[d] = 0;
                if forced_by_cell[cell].is_some() {
                    cursors[d] = Cursor::FRESH;
                    loop {
                        if d == 0 {
                            death_hist[epoch_max] += 1;
                            continue 'epoch;
                        }
                        d -= 1;
                        let cell = plans[d].cell as usize;
                        let (pid, rot) = grid[cell];
                        if p.ledger || cairn.is_some() {
                            let fcol = ccol_of(&tables, &plans[d], &grid);
                            if p.ledger {
                                led.unplace(&tables, &plans[d], &fcol, pid, rot);
                            }
                            if let Some(ca) = cairn.as_mut() {
                                ca.toggle(&tables, &plans[d], &fcol, pid, rot);
                            }
                        }
                        mask_set(&mut avail, pid);
                        grid[cell] = (u16::MAX, 0);
                        spent -= cost_at[d];
                        cost_at[d] = 0;
                        if forced_by_cell[cell].is_none() {
                            break;
                        }
                        cursors[d] = Cursor::FRESH;
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// brute-force reference: all (pid, rot, cost) candidates at a cell
    fn reference_cands(
        tables: &Tables,
        model: &InteriorModel,
        plan: &CellPlan,
        ccol: &[u8; 4],
        avail: &PieceMask,
        max_mis: u32,
        hinted: bool,
    ) -> Vec<(u16, u8, u32)> {
        let mut hint_piece = vec![false; model.np];
        if hinted {
            for &(_, pid, _) in &model.hints {
                hint_piece[pid] = true;
            }
        }
        let mut out = Vec::new();
        for pid in 0..tables.np as u16 {
            if !mask_get(avail, pid) || hint_piece[pid as usize] {
                continue;
            }
            for rot in 0..4u8 {
                let e = tables.rot_edges[pid as usize][rot as usize];
                let mut mis = 0u32;
                for i in 0..plan.k as usize {
                    if e[plan.sides[i] as usize] != ccol[i] {
                        mis += 1;
                    }
                }
                if mis == 0 {
                    out.push((pid, rot, 0));
                } else if mis <= max_mis && plan.k >= 2 {
                    out.push((pid, rot, mis));
                }
            }
        }
        out
    }

    /// drain all candidates at a cell through the segment machinery
    fn drain(
        tables: &Tables,
        plan: &CellPlan,
        ccol: &[u8; 4],
        avail: &PieceMask,
        max_mis: u32,
    ) -> Vec<(u16, u8, u32)> {
        let mut out = Vec::new();
        let n1 = plan.k as usize;
        let nseg = match max_mis {
            0 => 1,
            1 => 1 + n1,
            _ => plan.segs.len(),
        };
        for seg in plan.segs.iter().take(nseg) {
            let list: &[u16] = match seg.tab {
                Tab::PairNW { n, w } => {
                    &tables.pair_nw
                        [ccol[n as usize] as usize * tables.ncolors + ccol[w as usize] as usize]
                }
                Tab::PairNE { n, e } => {
                    &tables.pair_ne
                        [ccol[n as usize] as usize * tables.ncolors + ccol[e as usize] as usize]
                }
                Tab::PairSW { s, w } => {
                    &tables.pair_sw
                        [ccol[s as usize] as usize * tables.ncolors + ccol[w as usize] as usize]
                }
                Tab::Single { side, i } => {
                    &tables.single[side as usize][ccol[i as usize] as usize]
                }
                Tab::Free => &tables.free,
            };
            for &c in list {
                let pid = c >> 2;
                if !mask_get(avail, pid) {
                    continue;
                }
                let rot = (c & 3) as u8;
                let e = tables.rot_edges[pid as usize][rot as usize];
                let mut ok = true;
                for xi in 0..seg.n_extra as usize {
                    let i = seg.extra[xi] as usize;
                    if e[plan.sides[i] as usize] != ccol[i] {
                        ok = false;
                        break;
                    }
                }
                if !ok {
                    continue;
                }
                let mut viol = true;
                for vi in 0..seg.n_violate as usize {
                    let i = seg.violate[vi] as usize;
                    if e[plan.sides[i] as usize] == ccol[i] {
                        viol = false;
                        break;
                    }
                }
                if !viol {
                    continue;
                }
                out.push((pid, rot, u32::from(seg.n_violate)));
            }
        }
        out
    }

    #[test]
    fn segments_enumerate_reference_set() {
        for (hinted, scan) in [(false, Scan::Boustro), (true, Scan::RowMajor)] {
            let (mut m, sol, targets) = InteriorModel::synthetic(5, 5, 3);
            if hinted {
                m.hints.push((7, sol[7].0 as usize, sol[7].1));
            }
            let so = scan.order(5);
            let plans = build_plans(&m, &so, Some(&targets));
            let tables = Tables::build(&m, hinted);
            let mut grid = vec![(u16::MAX, 0u8); m.cells];
            let mut avail: PieceMask = [0; WORDS];
            for pid in 0..m.np as u16 {
                mask_set(&mut avail, pid);
            }
            let mut placed_to = 0usize;
            for d in [5usize, 12, 19, 24] {
                while placed_to < d {
                    let cell = so[placed_to];
                    let pid = placed_to as u16;
                    grid[cell] = (pid, (placed_to % 4) as u8);
                    mask_clear(&mut avail, pid);
                    placed_to += 1;
                }
                let plan = &plans[d];
                let mut ccol = [0u8; 4];
                for i in 0..plan.k as usize {
                    ccol[i] = match plan.src[i] {
                        Src::Fixed(c) => c,
                        Src::Placed { cell, their_side } => {
                            let (p2, r) = grid[cell as usize];
                            assert!(p2 != u16::MAX, "plan must reference placed cells");
                            tables.rot_edges[p2 as usize][r as usize][their_side as usize]
                        }
                    };
                }
                for max_mis in [0u32, 1, 2] {
                    let got = drain(&tables, plan, &ccol, &avail, max_mis);
                    let mut got_sorted = got.clone();
                    got_sorted.sort_unstable();
                    let mut want =
                        reference_cands(&tables, &m, plan, &ccol, &avail, max_mis, hinted);
                    want.sort_unstable();
                    assert_eq!(got_sorted, want, "d={d} max_mis={max_mis}");
                    // cheap-first: cost non-decreasing across the yield order
                    for w in got.windows(2) {
                        assert!(w[0].2 <= w[1].2, "d={d} max_mis={max_mis}");
                    }
                }
            }
        }
    }

    #[test]
    fn perfect_dfs_solves_synthetic_free_and_bordered() {
        for seed in 1..=3u64 {
            let (m, _, targets) = InteriorModel::synthetic(5, 6, seed * 11);
            for tg in [None, Some(&targets)] {
                let p = DfsParams {
                    seed,
                    budget_ms: 20_000,
                    restart_ms: 2_000,
                    exact_tail_k: 0,
                    ..DfsParams::default()
                };
                let r = dfs_run(&m, tg, None, &p);
                let (grid, breaks) =
                    r.complete.unwrap_or_else(|| panic!("no completion seed {seed}"));
                assert_eq!(breaks, 0);
                assert_eq!(m.count_breaks(&grid, tg), 0);
                let mut seen = vec![false; m.np];
                for &(pid, _) in &grid {
                    assert!(!seen[pid as usize]);
                    seen[pid as usize] = true;
                }
            }
        }
    }

    #[test]
    fn break_dfs_with_exact_tail_completes_and_accounts() {
        let (m, _, targets) = InteriorModel::synthetic(6, 4, 5);
        let p = DfsParams {
            seed: 2,
            budget_ms: 3_000,
            restart_ms: 1_000,
            schedule: vec![20, 26, 30],
            exact_tail_k: 6,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), None, &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(m.count_breaks(&grid, Some(&targets)), breaks);
    }

    #[test]
    fn hints_respected_with_breaks() {
        let (mut m, sol, targets) = InteriorModel::synthetic(5, 4, 9);
        for &cell in &[6usize, 12, 22] {
            m.hints.push((cell, sol[cell].0 as usize, sol[cell].1));
        }
        let p = DfsParams {
            seed: 4,
            budget_ms: 10_000,
            restart_ms: 2_000,
            hinted: true,
            schedule: vec![15, 18, 21, 23],
            exact_tail_k: 5,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), None, &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(m.count_breaks(&grid, Some(&targets)), breaks);
        for &(cell, pid, rot) in &m.hints {
            assert_eq!(grid[cell], (pid as u16, rot), "hint at {cell}");
        }
    }

    #[test]
    fn seam_scan_orders_and_plans_are_sound() {
        let (m, _, targets) = InteriorModel::synthetic(6, 5, 8);
        let scan = Scan::Seam(3).order(6);
        // permutation; seam row last
        let mut seen = vec![false; 36];
        for &c in &scan {
            assert!(!seen[c]);
            seen[c] = true;
        }
        assert!(scan[30..].iter().all(|&c| (18..24).contains(&c)));
        // seam cells must carry BOTH N and S placed constraints
        let plans = build_plans(&m, &scan, Some(&targets));
        for d in 30..36 {
            let plan = &plans[d];
            let has = |side: u8| (0..plan.k as usize).any(|i| plan.sides[i] == side);
            assert!(has(0) && has(2), "seam cell {d} needs N+S");
        }
    }

    #[test]
    fn seam_dfs_solves_and_accounts() {
        for seed in [3u64, 7] {
            let (m, _, targets) = InteriorModel::synthetic(6, 6, seed);
            // perfect solve, bordered, seam scan
            let p = DfsParams {
                seed,
                budget_ms: 20_000,
                restart_ms: 2_000,
                scan: Scan::Seam(3),
                ..DfsParams::default()
            };
            let r = dfs_run(&m, Some(&targets), None, &p);
            let (grid, breaks) = r.complete.expect("complete");
            assert_eq!(breaks, 0);
            assert_eq!(m.count_breaks(&grid, Some(&targets)), 0);
        }
        // break-DFS + seam-row exact endgame accounting
        let (m, _, targets) = InteriorModel::synthetic(6, 4, 11);
        let p = DfsParams {
            seed: 5,
            budget_ms: 3_000,
            restart_ms: 1_000,
            schedule: vec![16, 22, 27],
            exact_tail_k: 6,
            scan: Scan::Seam(3),
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), None, &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(m.count_breaks(&grid, Some(&targets)), breaks);
    }

    fn priors_from_grids(
        m: &InteriorModel,
        grids: &[&Vec<(u16, u8)>],
        tag: &str,
    ) -> crate::priors::Priors {
        let dir = std::env::temp_dir()
            .join(format!("cloister_dfs_pri_{}_{tag}", std::process::id()));
        std::fs::create_dir_all(&dir).expect("tmp");
        for (bi, g) in grids.iter().enumerate() {
            let body: Vec<String> = g
                .iter()
                .enumerate()
                .map(|(cell, &(pid, rot))| {
                    let pos = (cell / m.n + 1) * 16 + (cell % m.n + 1);
                    format!("{{\"pos\":{pos},\"piece_id\":{pid},\"rotation\":{rot}}}")
                })
                .collect();
            std::fs::write(
                dir.join(format!("{bi}.json")),
                format!("{{\"placement\":[{}]}}", body.join(",")),
            )
            .expect("write");
        }
        let pri = crate::priors::Priors::from_board_dir(m, &dir).expect("priors");
        std::fs::remove_dir_all(&dir).ok();
        pri
    }

    /// REPLAY: a pool holding the exact solution + prior-over-cost must
    /// walk straight to it (weight-1 candidates first at every depth,
    /// including through the all-segment fill at gated depths)
    #[test]
    fn prior_over_cost_replays_pool_solution() {
        let (m, sol, targets) = InteriorModel::synthetic(6, 6, 21);
        let pri = priors_from_grids(&m, &[&sol], "replay");
        let p = DfsParams {
            seed: 9,
            budget_ms: 10_000,
            restart_ms: 5_000,
            schedule: vec![6, 12, 18],
            exact_tail_k: 6,
            prior_over_cost: true,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), Some(&pri), &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(breaks, 0);
        assert_eq!(m.count_breaks(&grid, Some(&targets)), 0);
        assert_eq!(r.epochs, 1);
        assert!(r.nodes < 100, "replay must not detour: {} nodes", r.nodes);
    }

    /// foreign pool steers into breaks; placements (incl. cost-1 from the
    /// buffer) must keep exact break accounting (the in-DFS recount
    /// asserts fire on any mismatch)
    #[test]
    fn prior_over_cost_break_accounting() {
        let (m, _, targets) = InteriorModel::synthetic(6, 4, 5);
        let (_, sol_b, _) = InteriorModel::synthetic(6, 4, 23);
        let pri = priors_from_grids(&m, &[&sol_b], "foreign");
        let p = DfsParams {
            seed: 2,
            budget_ms: 3_000,
            restart_ms: 1_000,
            schedule: vec![20, 26, 30],
            exact_tail_k: 6,
            prior_over_cost: true,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), Some(&pri), &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(m.count_breaks(&grid, Some(&targets)), breaks);
    }

    /// LEDGER incremental bookkeeping must agree with a from-scratch
    /// recomputation after any place/unplace sequence
    #[test]
    fn ledger_incremental_matches_recompute() {
        let (m, sol, targets) = InteriorModel::synthetic(6, 5, 31);
        let scan = Scan::RowMajor.order(6);
        let plans = build_plans(&m, &scan, Some(&targets));
        let tables = Tables::build(&m, false);
        let mut grid = vec![(u16::MAX, 0u8); m.cells];
        let init = |grid: &Vec<(u16, u8)>| -> Ledger {
            let mut led = Ledger {
                f: vec![0; tables.ncolors],
                s: vec![0; tables.ncolors],
                deficit: 0,
            };
            for pid in 0..m.np {
                if grid.iter().all(|&(p, _)| p != pid as u16) {
                    for &c in &tables.rot_edges[pid][0] {
                        led.s[c as usize] += 1;
                    }
                }
            }
            // demands: rim targets on empty cells + placed sides facing empty
            for (cell, t) in targets.iter().enumerate() {
                if grid[cell].0 == u16::MAX {
                    for c in t.iter().flatten() {
                        led.f[*c as usize] += 1;
                    }
                }
            }
            for cell in 0..m.cells {
                let (p, r) = grid[cell];
                if p == u16::MAX {
                    continue;
                }
                let e = tables.rot_edges[p as usize][r as usize];
                let (y, x) = (cell / m.n, cell % m.n);
                let nb = [
                    (0usize, (y > 0).then(|| cell - m.n)),
                    (1, (x + 1 < m.n).then(|| cell + 1)),
                    (2, (y + 1 < m.n).then(|| cell + m.n)),
                    (3, (x > 0).then(|| cell - 1)),
                ];
                for (s, nc) in nb {
                    if let Some(ncell) = nc {
                        if grid[ncell].0 == u16::MAX {
                            led.f[e[s] as usize] += 1;
                        }
                    }
                }
            }
            led.deficit = (0..tables.ncolors).map(|c| led.surplus(c)).sum();
            led
        };
        let mut led = init(&grid);
        // place the first 12 solution cells, checking after each
        for d in 0..12 {
            let cell = scan[d];
            let ccol = ccol_of(&tables, &plans[d], &grid);
            grid[cell] = sol[cell];
            led.place(&tables, &plans[d], &ccol, sol[cell].0, sol[cell].1);
            let want = init(&grid);
            assert_eq!(led.f, want.f, "f after place d={d}");
            assert_eq!(led.s, want.s, "s after place d={d}");
            assert_eq!(led.deficit, want.deficit, "deficit after place d={d}");
        }
        // unplace back down, checking after each
        for d in (6..12).rev() {
            let cell = scan[d];
            let (pid, rot) = grid[cell];
            let ccol = ccol_of(&tables, &plans[d], &grid);
            led.unplace(&tables, &plans[d], &ccol, pid, rot);
            grid[cell] = (u16::MAX, 0);
            let want = init(&grid);
            assert_eq!(led.f, want.f, "f after unplace d={d}");
            assert_eq!(led.deficit, want.deficit, "deficit after unplace d={d}");
        }
    }

    /// LEDGER admissibility: a perfect solution path never violates the
    /// budget-0 prune, so the bordered perfect solve must still succeed
    #[test]
    fn ledger_dfs_solves_and_accounts() {
        let (m, _, targets) = InteriorModel::synthetic(6, 6, 17);
        let p = DfsParams {
            seed: 3,
            budget_ms: 20_000,
            restart_ms: 2_000,
            ledger: true,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), None, &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(breaks, 0);
        assert_eq!(m.count_breaks(&grid, Some(&targets)), 0);
        // break-DFS under ledger: total stays within budget and accounts
        let (m2, _, tg2) = InteriorModel::synthetic(6, 4, 5);
        let p2 = DfsParams {
            seed: 2,
            budget_ms: 5_000,
            restart_ms: 1_000,
            schedule: vec![16, 20, 24, 27, 30, 33],
            exact_tail_k: 6,
            ledger: true,
            ..DfsParams::default()
        };
        let r2 = dfs_run(&m2, Some(&tg2), None, &p2);
        if let Some((grid2, breaks2)) = r2.complete {
            assert_eq!(m2.count_breaks(&grid2, Some(&tg2)), breaks2);
        }
    }

    /// CAIRN: hash toggling is consistent (place+unplace restores h),
    /// and the full DFS with nogoods still solves perfectly / accounts
    #[test]
    fn cairn_dfs_solves_and_accounts() {
        let (m, sol, targets) = InteriorModel::synthetic(6, 5, 41);
        // toggle involution along a partial solution path
        let scan = Scan::RowMajor.order(6);
        let plans = build_plans(&m, &scan, Some(&targets));
        let tables = Tables::build(&m, false);
        let mut ca = Cairn::new(&m, &tables, Some(&targets));
        let h_start = ca.h;
        let mut grid = vec![(u16::MAX, 0u8); m.cells];
        for d in 0..10 {
            let cell = scan[d];
            let ccol = ccol_of(&tables, &plans[d], &grid);
            ca.toggle(&tables, &plans[d], &ccol, sol[cell].0, sol[cell].1);
            grid[cell] = sol[cell];
        }
        let h_mid = ca.h;
        assert_ne!(h_mid, h_start);
        for d in (0..10).rev() {
            let cell = scan[d];
            let (pid, rot) = grid[cell];
            let ccol = ccol_of(&tables, &plans[d], &grid);
            ca.toggle(&tables, &plans[d], &ccol, pid, rot);
            grid[cell] = (u16::MAX, 0);
        }
        assert_eq!(ca.h, h_start, "toggle must be an involution");
        // perfect solve with nogoods on (nogoods may only prune refuted
        // states — the solution path must survive)
        let p = DfsParams {
            seed: 6,
            budget_ms: 20_000,
            restart_ms: 2_000,
            cairn: true,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), None, &p);
        let (g, breaks) = r.complete.expect("complete");
        assert_eq!(breaks, 0);
        assert_eq!(m.count_breaks(&g, Some(&targets)), 0);
        // break-DFS with cairn + ledger together: accounting holds
        let (m2, _, tg2) = InteriorModel::synthetic(6, 4, 5);
        let p2 = DfsParams {
            seed: 2,
            budget_ms: 5_000,
            restart_ms: 1_000,
            schedule: vec![16, 20, 24, 27, 30, 33],
            exact_tail_k: 6,
            ledger: true,
            cairn: true,
            ..DfsParams::default()
        };
        let r2 = dfs_run(&m2, Some(&tg2), None, &p2);
        if let Some((g2, b2)) = r2.complete {
            assert_eq!(m2.count_breaks(&g2, Some(&tg2)), b2);
        }
    }

    /// cost-2 segments end-to-end: completes, accounts exactly, and the
    /// double-break gate semantics (2 spends at one cell) hold
    #[test]
    fn double_break_dfs_completes_and_accounts() {
        let (m, _, targets) = InteriorModel::synthetic(6, 4, 13);
        let p = DfsParams {
            seed: 7,
            budget_ms: 3_000,
            restart_ms: 1_000,
            schedule: vec![18, 22, 26, 30],
            exact_tail_k: 6,
            max_cell_breaks: 2,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), None, &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(m.count_breaks(&grid, Some(&targets)), breaks);
    }

    #[test]
    fn boustro_dfs_with_tail_completes() {
        let (m, _, targets) = InteriorModel::synthetic(6, 4, 17);
        let p = DfsParams {
            seed: 3,
            budget_ms: 3_000,
            restart_ms: 1_000,
            schedule: vec![18, 24, 30],
            exact_tail_k: 6,
            scan: Scan::Boustro,
            ..DfsParams::default()
        };
        let r = dfs_run(&m, Some(&targets), None, &p);
        let (grid, breaks) = r.complete.expect("complete");
        assert_eq!(m.count_breaks(&grid, Some(&targets)), breaks);
    }
}
