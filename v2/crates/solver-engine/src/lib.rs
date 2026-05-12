// Unified search engine. Backtracking over per-position (piece, rotation)
// domains, with edge-color propagation and piece-uniqueness propagation
// always on. Variable and value ordering are configurable; additional
// propagators (parity, island, AC-3) will plug in here in Step 8.
//
// One engine + one Config covers everything that used to be split across
// "DLX" and "CSP" families. The two families' performance gap turned out
// to live entirely in propagation, not in the search strategy — so we
// model propagation as a first-class dimension of Config.

#![forbid(unsafe_code)]

mod clock;

use clock::Clock;
use eternity2_core::{Board, Color, PathPolicy, PieceId, Position, Puzzle, Rotation, BORDER};
use eternity2_events::{
    BacktrackCause, EventBody, EventSink, FinalStats, SelectionReason, SolverEvent,
};
use eternity2_propagators::{
    class_balance_check, gacolor_check, island_check, multiset_equality_check, parity_check,
    GaColorState, NeighborInfo,
    PlacementInfo, PropagatorContext, PropagatorResult,
};
use eternity2_solver_trait::{
    HeuristicProfile, SolveMode, SolveOpts, SolveOutcome, Solver, SolverId,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VariableOrder {
    BorderFirstMrv,        // corners > edges > inner, ties by smallest domain
    Mrv,                   // pure smallest-domain
    RareColorFirst,        // border-first, ties by globally rare colors
    BorderFirstRandom,     // border-first, ties by seeded random
    // CHESS heuristic from Ansótegui et al. CP'08:
    //   1. corners
    //   2. border edges
    //   3. interior "black" cells (checkerboard parity 0) in a spiral
    //      from center outward
    //   4. interior "white" cells (parity 1) in the same spiral
    // Static order; ties broken by domain size.
    BorderFirstChess,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ValueOrder {
    InsertionOrder,        // try rows in domain insertion order
    LeastConstraining,     // LCV — pick value that prunes fewest neighbor rows (v2.1)
    RandomShuffle,         // shuffle the domain via the opts.seed RNG at each node
    /// Stable partition: rows whose piece-id is in
    /// `SolveOpts.preferred_pieces` first, then the rest. Used by
    /// Verhaard's phase-1 to load "hard pieces" (deferred + worst
    /// good-set members) into early placements where the search has
    /// maximum flexibility. groups.io 105190116 (Verhaard 2008-04-11).
    PreferredFirst,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Parallelism {
    SingleThread,
    // Root-level work-stealing: enumerate partial placements to depth K,
    // dispatch one rayon task per partial state. Workers replay the
    // prefix to rebuild domains, then run the standard sequential
    // search. Same algorithm as the legacy v3_par parallel_dlx_solver.
    //
    // split_depth=0 ⇒ auto-pick from puzzle size + rayon threads, matching
    // the legacy heuristic. WASM target always falls back to SingleThread.
    RootSplit { split_depth: u32 },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EngineConfig {
    pub variable_order: VariableOrder,
    pub value_order: ValueOrder,
    // Baseline propagation (edge-color matching + piece-uniqueness) is
    // always on. These flags toggle additional propagators that
    // execute after baseline succeeds. class_balance is cheap enough
    // to be on by default for any engine profile; parity/island are
    // opt-in per profile.
    pub class_balance_propagator: bool,
    pub parity_propagator: bool,
    pub island_propagator: bool,
    /// Maintain arc consistency on neighbouring-cell domains after each
    /// placement. Propagates further than baseline forward-checking by
    /// re-checking edges across already-pruned domains until a fixpoint.
    pub ac3_propagator: bool,
    // GAColor — symmetric-alldiff feasibility per color. Strictly tighter
    // than parity_propagator on the same problem; intended replacement.
    pub gacolor_propagator: bool,
    /// NS-1 / Hopfer 2022 multiset-equality propagator. Necessary
    /// condition for any full solution: the multiset of inward-facing
    /// colors on the 56 edge-class cells equals the multiset of border-
    /// facing colors on the 56 14×14-perimeter interior cells. Cheap
    /// (O(cells + remaining_pieces·4 + color_count)); most useful late
    /// in search (once the border ring closes), so consider gating
    /// behind `depth_threshold_for_propagators`.
    pub multiset_equality_propagator: bool,
    /// Joe-Saunders 2026: skip the expensive Step-8 propagators
    /// (class_balance / parity / island / gacolor / multiset_equality)
    /// at depths below this threshold. AC-3 and edge/uniqueness
    /// propagation still run at every depth. `None` = always run.
    /// Empirical sweet spot for canonical E2 reported as ~150.
    pub depth_threshold_for_propagators: Option<u32>,
    /// Break rotational symmetry by fixing the lowest-id corner piece at
    /// position (0,0) in its only valid rotation. Reduces search space
    /// by 4× on puzzles with 4 distinct corners (i.e., generated
    /// puzzles, which almost always satisfy this).
    pub break_symmetry: bool,
    pub parallelism: Parallelism,
}

impl EngineConfig {
    pub const BORDER_FIRST_LCV: Self = Self {
        variable_order: VariableOrder::BorderFirstMrv,
        value_order: ValueOrder::InsertionOrder,
        class_balance_propagator: true,
        parity_propagator: false,
        island_propagator: false,
        ac3_propagator: false,
        gacolor_propagator: false,
        multiset_equality_propagator: false,
        depth_threshold_for_propagators: None,
        break_symmetry: false,
        parallelism: Parallelism::SingleThread,
    };

    // Experiment A: GAColor as the strong global propagator.
    pub const BORDER_FIRST_GACOLOR: Self = Self {
        gacolor_propagator: true,
        ..Self::BORDER_FIRST_LCV
    };

    pub const BORDER_FIRST_GACOLOR_PAR: Self = Self {
        gacolor_propagator: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment D: GAColor + AC-3.
    pub const GACOLOR_AC3: Self = Self {
        gacolor_propagator: true,
        ac3_propagator: true,
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment E — true LCV value ordering combined with our best
    // propagation (gacolor + AC-3).
    pub const GACOLOR_AC3_LCV: Self = Self {
        value_order: ValueOrder::LeastConstraining,
        gacolor_propagator: true,
        ac3_propagator: true,
        ..Self::BORDER_FIRST_LCV
    };

    pub const GACOLOR_AC3_LCV_PAR: Self = Self {
        value_order: ValueOrder::LeastConstraining,
        gacolor_propagator: true,
        ac3_propagator: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment B' — CHESS revisited with AC-3 propagation.
    pub const CHESS_GACOLOR_AC3: Self = Self {
        variable_order: VariableOrder::BorderFirstChess,
        gacolor_propagator: true,
        ac3_propagator: true,
        ..Self::BORDER_FIRST_LCV
    };

    pub const GACOLOR_AC3_PAR: Self = Self {
        gacolor_propagator: true,
        ac3_propagator: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    // Same as GACOLOR_AC3_PAR (deterministic MRV variable-ordering, both
    // propagators) but with a seeded-random VALUE order: domain rows are
    // shuffled at each node. Different seeds produce different CP partials,
    // which is needed when downstream local search saturates because every
    // seed of CP+greedy_fill converges to the same canonical (and globally
    // wrong) prefix. Keeping MRV intact preserves CP's pruning power; only
    // tie-breaks between equally-good piece choices are randomised.
    pub const GACOLOR_AC3_RANDOM_PAR: Self = Self {
        value_order: ValueOrder::RandomShuffle,
        gacolor_propagator: true,
        ac3_propagator: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment C: GAColor + symmetry breaking.
    pub const GACOLOR_SYMBREAK: Self = Self {
        gacolor_propagator: true,
        break_symmetry: true,
        ..Self::BORDER_FIRST_LCV
    };

    pub const GACOLOR_SYMBREAK_PAR: Self = Self {
        gacolor_propagator: true,
        break_symmetry: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment B: CHESS + GAColor.
    pub const CHESS_GACOLOR: Self = Self {
        variable_order: VariableOrder::BorderFirstChess,
        gacolor_propagator: true,
        ..Self::BORDER_FIRST_LCV
    };

    pub const CHESS_GACOLOR_PAR: Self = Self {
        variable_order: VariableOrder::BorderFirstChess,
        gacolor_propagator: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    pub const BORDER_FIRST_LCV_PAR: Self = Self {
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    pub const BORDER_FIRST_FULL_PAR: Self = Self {
        parity_propagator: true,
        island_propagator: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    pub const RARE_COLOR_FIRST: Self = Self {
        variable_order: VariableOrder::RareColorFirst,
        value_order: ValueOrder::InsertionOrder,
        ..Self::BORDER_FIRST_LCV
    };

    pub const BORDER_FIRST_RANDOM: Self = Self {
        variable_order: VariableOrder::BorderFirstRandom,
        value_order: ValueOrder::InsertionOrder,
        ..Self::BORDER_FIRST_LCV
    };

    // Vol-12: gacolor + AC-3 + NS-1 multiset equality (Hopfer 2022).
    pub const GACOLOR_AC3_NS1: Self = Self {
        gacolor_propagator: true,
        ac3_propagator: true,
        multiset_equality_propagator: true,
        ..Self::BORDER_FIRST_LCV
    };

    pub const GACOLOR_AC3_NS1_PAR: Self = Self {
        gacolor_propagator: true,
        ac3_propagator: true,
        multiset_equality_propagator: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    // Vol-12: Joe-Saunders 2026 — gacolor + AC-3, but extras only fire
    // at depth ≥ 150. Tries to bridge our ~2k nodes/sec to McGavin's
    // ~300M/sec by skipping per-node Step-8 work during early search.
    pub const JOE_DEPTH150: Self = Self {
        gacolor_propagator: true,
        ac3_propagator: true,
        multiset_equality_propagator: true,
        depth_threshold_for_propagators: Some(150),
        ..Self::BORDER_FIRST_LCV
    };

    pub const JOE_DEPTH150_PAR: Self = Self {
        gacolor_propagator: true,
        ac3_propagator: true,
        multiset_equality_propagator: true,
        depth_threshold_for_propagators: Some(150),
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    // Step 8 profiles: baseline + extra propagators.
    pub const BORDER_FIRST_PARITY: Self = Self {
        parity_propagator: true,
        ..Self::BORDER_FIRST_LCV
    };

    pub const BORDER_FIRST_FULL: Self = Self {
        parity_propagator: true,
        island_propagator: true,
        ..Self::BORDER_FIRST_LCV
    };

    /// Verhaard 2008 — gacolor + AC-3 + PreferredFirst value ordering.
    /// Caller sets `SolveOpts.preferred_pieces` to (deferred ∪ worst-good)
    /// from phase-0 SA. See `solver-verhaard` crate.
    pub const VERHAARD_PREFERRED: Self = Self {
        value_order: ValueOrder::PreferredFirst,
        gacolor_propagator: true,
        ac3_propagator: true,
        ..Self::BORDER_FIRST_LCV
    };

    pub const VERHAARD_PREFERRED_PAR: Self = Self {
        value_order: ValueOrder::PreferredFirst,
        gacolor_propagator: true,
        ac3_propagator: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };
}

pub struct EngineSolver {
    config: EngineConfig,
    solver_id: String,
    heuristic_profile: String,
}

impl EngineSolver {
    #[must_use]
    pub fn new(config: EngineConfig, solver_id: impl Into<String>, heuristic_profile: impl Into<String>) -> Self {
        Self {
            config,
            solver_id: solver_id.into(),
            heuristic_profile: heuristic_profile.into(),
        }
    }

    #[must_use]
    pub fn border_first_lcv() -> Self {
        Self::new(EngineConfig::BORDER_FIRST_LCV, "engine", "border_first_lcv")
    }

    #[must_use]
    pub fn rare_color_first() -> Self {
        Self::new(EngineConfig::RARE_COLOR_FIRST, "engine", "rare_color_first")
    }

    #[must_use]
    pub fn border_first_random() -> Self {
        Self::new(EngineConfig::BORDER_FIRST_RANDOM, "engine", "border_first_random")
    }

    #[must_use]
    pub fn border_first_parity() -> Self {
        Self::new(EngineConfig::BORDER_FIRST_PARITY, "engine", "border_first_parity")
    }

    #[must_use]
    pub fn border_first_full() -> Self {
        Self::new(EngineConfig::BORDER_FIRST_FULL, "engine", "border_first_full")
    }

    #[must_use]
    pub fn border_first_lcv_par() -> Self {
        Self::new(EngineConfig::BORDER_FIRST_LCV_PAR, "engine", "border_first_lcv_par")
    }

    #[must_use]
    pub fn border_first_full_par() -> Self {
        Self::new(EngineConfig::BORDER_FIRST_FULL_PAR, "engine", "border_first_full_par")
    }

    #[must_use]
    pub fn border_first_gacolor() -> Self {
        Self::new(EngineConfig::BORDER_FIRST_GACOLOR, "engine", "border_first_gacolor")
    }

    #[must_use]
    pub fn border_first_gacolor_par() -> Self {
        Self::new(EngineConfig::BORDER_FIRST_GACOLOR_PAR, "engine", "border_first_gacolor_par")
    }

    #[must_use]
    pub fn chess_gacolor() -> Self {
        Self::new(EngineConfig::CHESS_GACOLOR, "engine", "chess_gacolor")
    }

    #[must_use]
    pub fn chess_gacolor_par() -> Self {
        Self::new(EngineConfig::CHESS_GACOLOR_PAR, "engine", "chess_gacolor_par")
    }

    #[must_use]
    pub fn gacolor_symbreak() -> Self {
        Self::new(EngineConfig::GACOLOR_SYMBREAK, "engine", "gacolor_symbreak")
    }

    #[must_use]
    pub fn gacolor_symbreak_par() -> Self {
        Self::new(EngineConfig::GACOLOR_SYMBREAK_PAR, "engine", "gacolor_symbreak_par")
    }

    #[must_use]
    pub fn gacolor_ac3() -> Self {
        Self::new(EngineConfig::GACOLOR_AC3, "engine", "gacolor_ac3")
    }

    #[must_use]
    pub fn gacolor_ac3_par() -> Self {
        Self::new(EngineConfig::GACOLOR_AC3_PAR, "engine", "gacolor_ac3_par")
    }

    /// Same as `gacolor_ac3_par` but with a seeded random tiebreaker in the
    /// variable-order step. Different `opts.seed` values produce different
    /// CP partials, which is necessary when downstream search saturates
    /// because every seed of the deterministic pipeline converges to the
    /// same wrong prefix.
    #[must_use]
    pub fn gacolor_ac3_random_par() -> Self {
        Self::new(EngineConfig::GACOLOR_AC3_RANDOM_PAR, "engine", "gacolor_ac3_random_par")
    }

    #[must_use]
    pub fn chess_gacolor_ac3() -> Self {
        Self::new(EngineConfig::CHESS_GACOLOR_AC3, "engine", "chess_gacolor_ac3")
    }

    /// Vol-12: gacolor + AC-3 + NS-1 multiset-equality propagator.
    #[must_use]
    pub fn gacolor_ac3_ns1() -> Self {
        Self::new(EngineConfig::GACOLOR_AC3_NS1, "engine", "gacolor_ac3_ns1")
    }

    #[must_use]
    pub fn gacolor_ac3_ns1_par() -> Self {
        Self::new(EngineConfig::GACOLOR_AC3_NS1_PAR, "engine", "gacolor_ac3_ns1_par")
    }

    /// Vol-12: gacolor + AC-3 + NS-1 with Step-8 propagators gated to
    /// depth ≥ 150 (Joe-Saunders 2026 pruning policy).
    #[must_use]
    pub fn joe_depth150() -> Self {
        Self::new(EngineConfig::JOE_DEPTH150, "engine", "joe_depth150")
    }

    #[must_use]
    pub fn joe_depth150_par() -> Self {
        Self::new(EngineConfig::JOE_DEPTH150_PAR, "engine", "joe_depth150_par")
    }

    /// Verhaard-style value ordering: prefer the pieces listed in
    /// `SolveOpts.preferred_pieces`. Combined with gacolor + AC-3.
    /// Single-thread.
    #[must_use]
    pub fn verhaard_preferred() -> Self {
        Self::new(EngineConfig::VERHAARD_PREFERRED, "engine", "verhaard_preferred")
    }

    /// Parallel variant of verhaard_preferred.
    #[must_use]
    pub fn verhaard_preferred_par() -> Self {
        Self::new(EngineConfig::VERHAARD_PREFERRED_PAR, "engine", "verhaard_preferred_par")
    }

    #[must_use]
    pub fn gacolor_ac3_lcv() -> Self {
        Self::new(EngineConfig::GACOLOR_AC3_LCV, "engine", "gacolor_ac3_lcv")
    }

    #[must_use]
    pub fn gacolor_ac3_lcv_par() -> Self {
        Self::new(EngineConfig::GACOLOR_AC3_LCV_PAR, "engine", "gacolor_ac3_lcv_par")
    }
}

impl Solver for EngineSolver {
    fn id(&self) -> SolverId { SolverId(self.solver_id.clone()) }
    fn heuristic_profile(&self) -> HeuristicProfile {
        HeuristicProfile(self.heuristic_profile.clone())
    }

    fn supports_path_policy(&self, policy: &PathPolicy) -> bool {
        !matches!(policy, PathPolicy::Strict)
    }

    fn solve(
        &mut self,
        puzzle: &Puzzle,
        opts: &SolveOpts,
        sink: &mut dyn EventSink,
    ) -> SolveOutcome {
        #[cfg(not(target_arch = "wasm32"))]
        {
            if matches!(self.config.parallelism, Parallelism::RootSplit { .. }) {
                return parallel::solve_parallel(self, puzzle, opts, sink);
            }
        }
        SearchState::new(puzzle, self, opts).run(sink)
    }
}

#[cfg(not(target_arch = "wasm32"))]
mod parallel;

/// Compute the static CHESS-heuristic rank for each board position.
///
/// Order classes (lower rank = picked sooner):
///   0..=3        — the four corners, in fixed reading order
///   4..=4+B-1    — border non-corner cells
///   next         — interior "black" parity-0 cells, spiraling from center
///   next         — interior "white" parity-1 cells, spiraling from center
///
/// Spiral-from-center: at each step pick the unvisited cell of the
/// desired parity closest to the geometric center (Chebyshev distance);
/// ties broken by row-major position to keep the order deterministic.
fn compute_chess_rank(puzzle: &Puzzle) -> Vec<u32> {
    let n = puzzle.cell_count() as usize;
    let w = puzzle.width;
    let h = puzzle.height;
    let mut rank = vec![u32::MAX; n];
    let mut next_rank: u32 = 0;

    // Class 1: corners.
    let corners: [(u32, u32); 4] = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)];
    let mut seen = vec![false; n];
    for (x, y) in corners {
        let p = y * w + x;
        if !seen[p as usize] {
            rank[p as usize] = next_rank;
            seen[p as usize] = true;
            next_rank += 1;
        }
    }

    // Class 2: border (non-corner) cells in row-major order. Keeps the
    // ordering deterministic and follows the perimeter naturally.
    for pos in 0..puzzle.cell_count() {
        if seen[pos as usize] { continue; }
        let mask = puzzle.border_mask(pos);
        if mask.iter().any(|m| *m) {
            rank[pos as usize] = next_rank;
            seen[pos as usize] = true;
            next_rank += 1;
        }
    }

    // Center coordinates for Chebyshev-distance spiral.
    let cx = (w - 1) as i32;
    let cy = (h - 1) as i32;
    let center = (cx as f32 / 2.0, cy as f32 / 2.0);

    let mut interior: Vec<(u32, u32, u32)> = Vec::new(); // (pos, parity, dist_metric)
    for pos in 0..puzzle.cell_count() {
        if seen[pos as usize] { continue; }
        let (x, y) = puzzle.xy(pos);
        let dx = (x as f32 - center.0).abs();
        let dy = (y as f32 - center.1).abs();
        // Use 1000 * Chebyshev + row-major as deterministic tiebreaker.
        let cheb = (dx.max(dy) * 1000.0) as u32;
        let parity = (x + y) & 1;
        interior.push((pos, parity, cheb * 10_000 + pos));
    }

    // Class 3: parity-0 ("black") spiraling from center.
    let mut blacks: Vec<_> = interior.iter().filter(|(_, par, _)| *par == 0).collect();
    blacks.sort_by_key(|(_, _, m)| *m);
    for (pos, _, _) in blacks {
        rank[*pos as usize] = next_rank;
        next_rank += 1;
    }
    // Class 4: parity-1 ("white") spiraling from center.
    let mut whites: Vec<_> = interior.iter().filter(|(_, par, _)| *par == 1).collect();
    whites.sort_by_key(|(_, _, m)| *m);
    for (pos, _, _) in whites {
        rank[*pos as usize] = next_rank;
        next_rank += 1;
    }
    rank
}

#[derive(Debug, Clone, Copy)]
pub(crate) struct Row {
    pub(crate) piece_id: PieceId,
    pub(crate) edges: [Color; 4],
    pub(crate) rotation: u8,
    valid: bool,
}

pub(crate) struct SearchState<'a> {
    pub(crate) puzzle: &'a Puzzle,
    pub(crate) opts: &'a SolveOpts,
    pub(crate) config: EngineConfig,
    pub(crate) solver_id: String,
    pub(crate) heuristic_profile: String,
    pub(crate) rows: Vec<Row>,
    pub(crate) domains: Vec<Vec<u32>>,
    pub(crate) placed: Vec<Option<u32>>,
    pub(crate) path_order: Vec<Position>,
    pub(crate) path_index_of: Vec<u32>,
    pub(crate) used: Vec<bool>,
    pub(crate) rng_state: u64,
    pub(crate) started: Clock,
    pub(crate) node_id: u64,
    pub(crate) stats: FinalStats,
    pub(crate) best_depth: u32,
    pub(crate) best_partial: Option<Board>,
    pub(crate) gacolor: Option<GaColorState>,
    /// Precomputed static-rank for CHESS variable ordering.
    /// `chess_rank[pos]` is the position's priority (lower = picked
    /// sooner). Only consulted when `variable_order ==
    /// BorderFirstChess`. Empty for other orders.
    pub(crate) chess_rank: Vec<u32>,
    /// Static per-position priority class: 0 = corner, 1 = edge, 2 = inner.
    /// Read on every `select_position` call (hot — once per node); cached
    /// here so we don't redo the `border_mask` arithmetic every time.
    pub(crate) border_priority_cache: Vec<u32>,
    /// Reusable scratch for AC-3's hot-path count cache (Exp I).
    /// Shape is fixed at construction: `(n_pos * 4 * n_colors)` u16s for
    /// `ac3_count` and `(n_pos * words_per_pos)` u64s for `ac3_present`.
    /// `propagate_ac3` zeroes-then-rebuilds the slices at entry. Holding
    /// them on SearchState avoids per-call allocator round-trips.
    pub(crate) ac3_count: Vec<u16>,
    pub(crate) ac3_present: Vec<u64>,
    pub(crate) ac3_on_queue: Vec<bool>,
}

impl<'a> SearchState<'a> {
    pub(crate) fn new(puzzle: &'a Puzzle, solver: &EngineSolver, opts: &'a SolveOpts) -> Self {
        let pieces = puzzle.pieces();
        let max_piece_index = pieces.iter().map(|p| usize::from(p.id) + 1).max().unwrap_or(0);
        let mut rows = vec![
            Row { piece_id: 0, edges: [0; 4], rotation: 0, valid: false };
            max_piece_index * 4
        ];
        // SolveOpts.excluded_pieces (used by Verhaard phase-1 scaffold)
        // forbids these piece-ids from appearing in any domain. Mark
        // all four rows of an excluded piece as invalid below.
        let mut excluded = vec![false; max_piece_index];
        for &pid in &opts.excluded_pieces {
            let idx = usize::from(pid);
            if idx < excluded.len() {
                excluded[idx] = true;
            }
        }
        for piece in pieces {
            let pid = usize::from(piece.id);
            let is_excluded = excluded.get(pid).copied().unwrap_or(false);
            let mut seen: Vec<[Color; 4]> = Vec::with_capacity(4);
            for r in 0..4u8 {
                let rot = Rotation::from_u8(r).unwrap();
                let e = piece.edges.rotated(rot).as_array();
                let dup = seen.iter().any(|s| *s == e);
                if !dup { seen.push(e); }
                rows[pid * 4 + r as usize] = Row {
                    piece_id: piece.id,
                    edges: e,
                    rotation: r,
                    valid: !dup && !is_excluded,
                };
            }
        }

        let n_pos = puzzle.cell_count() as usize;
        let mut domains = vec![Vec::<u32>::new(); n_pos];
        for pos in 0..puzzle.cell_count() {
            let mask = puzzle.border_mask(pos);
            let [on_top, on_right, on_bot, on_left] = mask;
            for (idx, row) in rows.iter().enumerate() {
                if !row.valid { continue; }
                let [t, ri, b, l] = row.edges;
                if on_top != (t == BORDER) { continue; }
                if on_right != (ri == BORDER) { continue; }
                if on_bot != (b == BORDER) { continue; }
                if on_left != (l == BORDER) { continue; }
                domains[pos as usize].push(idx as u32);
            }
        }

        let path_order = opts.path.clone();
        let mut path_index_of = vec![u32::MAX; n_pos];
        for (i, &p) in path_order.iter().enumerate() {
            if (p as usize) < n_pos {
                path_index_of[p as usize] = i as u32;
            }
        }

        Self {
            puzzle,
            opts,
            config: solver.config,
            solver_id: solver.solver_id.clone(),
            heuristic_profile: solver.heuristic_profile.clone(),
            rows,
            domains,
            placed: vec![None; n_pos],
            path_order,
            path_index_of,
            used: vec![false; max_piece_index.max(1)],
            rng_state: opts.seed.wrapping_add(0x9E37_79B9_7F4A_7C15),
            started: Clock::now(),
            node_id: 0,
            stats: FinalStats::default(),
            best_depth: 0,
            best_partial: None,
            gacolor: if solver.config.gacolor_propagator {
                Some(GaColorState::new(puzzle))
            } else {
                None
            },
            chess_rank: if matches!(solver.config.variable_order, VariableOrder::BorderFirstChess) {
                compute_chess_rank(puzzle)
            } else {
                Vec::new()
            },
            border_priority_cache: {
                let mut v = vec![0u32; n_pos];
                for pos in 0..puzzle.cell_count() {
                    let mask = puzzle.border_mask(pos);
                    let n = u32::from(mask[0]) + u32::from(mask[1])
                          + u32::from(mask[2]) + u32::from(mask[3]);
                    v[pos as usize] = match n { 2 => 0, 1 => 1, _ => 2 };
                }
                v
            },
            ac3_count: if solver.config.ac3_propagator {
                vec![0u16; n_pos * 4 * puzzle.color_count as usize]
            } else {
                Vec::new()
            },
            ac3_present: if solver.config.ac3_propagator {
                let n_rows = max_piece_index * 4;
                vec![0u64; n_pos * n_rows.div_ceil(64)]
            } else {
                Vec::new()
            },
            ac3_on_queue: if solver.config.ac3_propagator {
                vec![false; n_pos]
            } else {
                Vec::new()
            },
        }
    }

    fn elapsed_us(&self) -> u64 { self.started.elapsed_us() }

    fn timed_out(&self) -> bool {
        self.opts.time_budget_ms != 0
            && self.elapsed_us() / 1000 >= self.opts.time_budget_ms
    }

    fn next_random(&mut self) -> u64 {
        self.rng_state = self.rng_state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.rng_state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    fn emit(&mut self, sink: &mut dyn EventSink, depth: u32, body: EventBody) {
        self.node_id += 1;
        let event = SolverEvent {
            schema_version: 1,
            solver_run_id: self.opts.solver_run_id,
            node_id: self.node_id,
            depth,
            timestamp_us: self.elapsed_us(),
            body,
        };
        sink.emit(event);
    }

    #[inline(always)]
    fn border_priority(&self, pos: Position) -> u32 {
        self.border_priority_cache[pos as usize]
    }

    fn position_score(&mut self, pos: Position) -> (u32, u32) {
        let d = self.domains[pos as usize].len() as u32;
        let bp = self.border_priority(pos);
        let path_tie = match self.opts.path_policy {
            PathPolicy::OrderingPrior => self.path_index_of[pos as usize],
            _ => 0,
        };
        match self.config.variable_order {
            VariableOrder::BorderFirstMrv => (bp, d.saturating_add(path_tie / 1000)),
            VariableOrder::Mrv => (d, path_tie),
            VariableOrder::RareColorFirst => (bp, d),  // placeholder; real impl in Step 8
            VariableOrder::BorderFirstRandom => (bp, (self.next_random() & 0xFFFF) as u32),
            // CHESS: primary key is the static precomputed rank; ties
            // broken by current domain size (smallest first, MRV style).
            VariableOrder::BorderFirstChess => {
                let r = self.chess_rank
                    .get(pos as usize)
                    .copied()
                    .unwrap_or(u32::MAX);
                (r, d)
            }
        }
    }

    fn selection_reason(&self) -> SelectionReason {
        match self.config.variable_order {
            VariableOrder::BorderFirstMrv
            | VariableOrder::BorderFirstRandom
            | VariableOrder::BorderFirstChess => SelectionReason::BorderFirst,
            VariableOrder::Mrv => SelectionReason::Mrv,
            VariableOrder::RareColorFirst => SelectionReason::RareColor,
        }
    }

    pub(crate) fn select_position(&mut self) -> Option<Position> {
        if let PathPolicy::PrefixConstraint { k } = self.opts.path_policy {
            if self.stats.current_depth < k {
                for &p in &self.path_order {
                    if self.placed[p as usize].is_none() {
                        return Some(p);
                    }
                }
            }
        }
        let mut best: Option<(Position, (u32, u32))> = None;
        for pos in 0..self.puzzle.cell_count() {
            if self.placed[pos as usize].is_some() { continue; }
            let score = self.position_score(pos);
            match &best {
                None => best = Some((pos, score)),
                Some((_, bs)) if score < *bs => best = Some((pos, score)),
                _ => {}
            }
        }
        best.map(|(p, _)| p)
    }

    pub(crate) fn place_and_propagate(
        &mut self,
        sink: &mut dyn EventSink,
        depth: u32,
        pos: Position,
        row_id: u32,
    ) -> PropagationOutcome {
        let row = self.rows[row_id as usize];
        // Snapshot neighbor state BEFORE placement so we can update the
        // incremental GAColor state, and so a later unplace can be
        // reproduced from the same snapshot.
        let n_info = self.neighbor_info(pos);
        self.placed[pos as usize] = Some(row_id);
        let piece_idx = usize::from(row.piece_id);
        self.used[piece_idx] = true;
        if let Some(gc) = self.gacolor.as_mut() {
            gc.apply_place(&row.edges, &n_info);
        }
        let mut undo: Vec<(Position, Vec<u32>)> = Vec::new();

        let (x, y) = self.puzzle.xy(pos);
        let w = self.puzzle.width;
        let h = self.puzzle.height;

        let prune = |this: &mut Self,
                     neighbor: Position,
                     neighbor_edge_idx: usize,
                     required: Color|
         -> PruneResult {
            if this.placed[neighbor as usize].is_some() {
                return PruneResult::Ok;
            }
            let domain = &mut this.domains[neighbor as usize];
            let mut removed = Vec::new();
            let mut i = 0;
            while i < domain.len() {
                let r_id = domain[i];
                let r = this.rows[r_id as usize];
                if r.piece_id == row.piece_id || r.edges[neighbor_edge_idx] != required {
                    removed.push(r_id);
                    domain.swap_remove(i);
                } else {
                    i += 1;
                }
            }
            if !removed.is_empty() {
                this.stats.propagations += removed.len() as u64;
            }
            if domain.is_empty() {
                PruneResult::Wipeout { removed }
            } else {
                PruneResult::Removed(removed)
            }
        };

        // Four neighbor prunes (edge-color propagation).
        let neighbors: [(Option<Position>, usize, Color); 4] = [
            (if y > 0 { Some((y - 1) * w + x) } else { None }, 2, row.edges[0]),
            (if x + 1 < w { Some(y * w + (x + 1)) } else { None }, 3, row.edges[1]),
            (if y + 1 < h { Some((y + 1) * w + x) } else { None }, 0, row.edges[2]),
            (if x > 0 { Some(y * w + (x - 1)) } else { None }, 1, row.edges[3]),
        ];
        for (maybe_np, edge_idx, required) in neighbors {
            let Some(np) = maybe_np else { continue; };
            match prune(self, np, edge_idx, required) {
                PruneResult::Wipeout { removed } => {
                    undo.push((np, removed));
                    self.stats.domain_wipeouts += 1;
                    self.emit(sink, depth, EventBody::DomainWipeout { position: np });
                    return PropagationOutcome::Wipeout { undo };
                }
                PruneResult::Removed(r) if !r.is_empty() => undo.push((np, r)),
                _ => {}
            }
        }

        // Piece-uniqueness propagation (the "column" of classic DLX).
        let mut other_undo: Vec<(Position, Vec<u32>)> = Vec::new();
        for p in 0..self.puzzle.cell_count() {
            if p == pos || self.placed[p as usize].is_some() { continue; }
            let domain = &mut self.domains[p as usize];
            let mut removed = Vec::new();
            let mut i = 0;
            while i < domain.len() {
                let r_id = domain[i];
                let r = self.rows[r_id as usize];
                if r.piece_id == row.piece_id {
                    removed.push(r_id);
                    domain.swap_remove(i);
                } else {
                    i += 1;
                }
            }
            if !removed.is_empty() {
                self.stats.propagations += removed.len() as u64;
                if domain.is_empty() {
                    other_undo.push((p, removed));
                    self.stats.domain_wipeouts += 1;
                    undo.extend(other_undo);
                    self.emit(sink, depth, EventBody::DomainWipeout { position: p });
                    return PropagationOutcome::Wipeout { undo };
                }
                other_undo.push((p, removed));
            }
        }
        undo.extend(other_undo);

        // AC-3 cascading propagation. Re-checks arc-consistency from the
        // freshly-placed cell outward until fixpoint. Each row r at
        // position a is "supported by" position b if some row r' in
        // domain[b] has matching color on the shared edge and r.piece !=
        // r'.piece. If support is lost we drop r from domain[a]. Updates
        // can cascade through the grid.
        if self.config.ac3_propagator {
            match self.propagate_ac3(sink, depth, pos) {
                Ac3Outcome::Wipeout { removed } => {
                    for (p, rs) in removed { undo.push((p, rs)); }
                    return PropagationOutcome::Wipeout { undo };
                }
                Ac3Outcome::Ok { removed } => {
                    for (p, rs) in removed { undo.push((p, rs)); }
                }
            }
        }

        // Step 8 propagators: run only the ones enabled in config. They
        // are read-only over engine state (don't mutate domains) so the
        // undo log doesn't change. Order is cheapest-first.
        if self.run_extra_propagators(depth) == PropagatorResult::Wipeout {
            self.emit(sink, depth, EventBody::DomainWipeout { position: pos });
            return PropagationOutcome::Wipeout { undo };
        }

        PropagationOutcome::Ok { undo }
    }

    fn snapshot_placement_info(&self) -> Vec<Option<PlacementInfo>> {
        self.placed.iter().map(|p| p.map(|row_id| {
            let r = self.rows[row_id as usize];
            PlacementInfo { edges_after_rotation: r.edges }
        })).collect()
    }

    /// AC-3 cascading propagation. Maintains arc-consistency across
    /// neighbouring positions starting from the just-placed cell. Drops
    /// any row from an unplaced position's domain that has no supporting
    /// row in some neighbouring unplaced domain.
    ///
    /// Returns the list of (position, removed_rows) pairs so the caller
    /// can extend its undo log; or `Wipeout` if any domain emptied.
    fn propagate_ac3(
        &mut self,
        sink: &mut dyn EventSink,
        depth: u32,
        start_pos: Position,
    ) -> Ac3Outcome {
        let w = self.puzzle.width;
        let h = self.puzzle.height;
        let n_pos = self.puzzle.cell_count();
        let n_rows = self.rows.len();
        let n_colors = self.puzzle.color_count as usize;
        // Hot-path acceleration (Exp I, revised in Exp K):
        //   count[pos * stride_pos + side * n_colors + color] = #rows in
        //     domains[pos] whose edges[side]==color.
        //   present[pos] is a row-id bitset.
        // Buffers live on SearchState so we pay the alloc only once.
        // We zero the relevant slices then rebuild for unplaced positions
        // — no fresh allocation per AC-3 entry.
        let stride_pos = 4 * n_colors;
        let words_per_pos = n_rows.div_ceil(64);
        let count_len = (n_pos as usize) * stride_pos;
        let present_len = (n_pos as usize) * words_per_pos;
        debug_assert!(self.ac3_count.len() == count_len);
        debug_assert!(self.ac3_present.len() == present_len);
        for v in &mut self.ac3_count[..count_len] { *v = 0; }
        for v in &mut self.ac3_present[..present_len] { *v = 0; }
        for v in &mut self.ac3_on_queue[..n_pos as usize] { *v = false; }
        // Pin a non-borrow timeout snapshot before we take mut-borrows
        // on the cache fields. self.started doesn't implement Copy so
        // we read elapsed once into a closure-ish form.
        let time_budget_ms = self.opts.time_budget_ms;
        let timeout_at_us: u64 = if time_budget_ms == 0 {
            u64::MAX
        } else {
            time_budget_ms.saturating_mul(1000)
        };
        let count = &mut self.ac3_count;
        let present = &mut self.ac3_present;
        let on_queue = &mut self.ac3_on_queue;
        for p in 0..n_pos as usize {
            if self.placed[p].is_some() { continue; }
            for &r_id in &self.domains[p] {
                let r = self.rows[r_id as usize];
                let r_idx = r_id as usize;
                present[p * words_per_pos + r_idx / 64] |= 1u64 << (r_idx % 64);
                for s in 0..4 {
                    let c = r.edges[s] as usize;
                    count[p * stride_pos + s * n_colors + c] += 1;
                }
            }
        }
        let mut queue: Vec<Position> = Vec::with_capacity(16);
        // Seed: all unplaced neighbours of start_pos (and their unplaced
        // neighbours).
        let seed_neighbors = |p: Position, w: u32, h: u32| -> [Option<Position>; 4] {
            let (x, y) = (p % w, p / w);
            [
                if y > 0 { Some((y - 1) * w + x) } else { None },
                if x + 1 < w { Some(y * w + (x + 1)) } else { None },
                if y + 1 < h { Some((y + 1) * w + x) } else { None },
                if x > 0 { Some(y * w + (x - 1)) } else { None },
            ]
        };
        for np in seed_neighbors(start_pos, w, h).iter().flatten() {
            if self.placed[*np as usize].is_none() && !on_queue[*np as usize] {
                queue.push(*np);
                on_queue[*np as usize] = true;
            }
        }
        let mut all_removed: Vec<(Position, Vec<u32>)> = Vec::new();

        let mut ac3_tick: u32 = 0;
        while let Some(a) = queue.pop() {
            ac3_tick = ac3_tick.wrapping_add(1);
            // Cooperative timeout check inside the AC-3 loop. On hard
            // puzzles a single AC-3 invocation can churn for seconds;
            // without this the outer per-N-nodes timeout check fires
            // late. Check every 64 queue pops — cheap relative to the
            // O(|D|² × neighbours) inner work. Reading self.started
            // through an immutable borrow is fine here because count/
            // present/on_queue are disjoint fields (NLL).
            if ac3_tick & 0x3f == 0 && self.started.elapsed_us() >= timeout_at_us {
                return Ac3Outcome::Ok { removed: all_removed };
            }
            on_queue[a as usize] = false;
            if self.placed[a as usize].is_some() { continue; }

            // For each row in domain[a], check it has support across each
            // of its unplaced neighbours.
            // edge order: top=0, right=1, bottom=2, left=3
            //   neighbour-facing-edge index from a's side ↔ b's side:
            //   a-top(0)    ↔ b-bottom(2)
            //   a-right(1)  ↔ b-left(3)
            //   a-bottom(2) ↔ b-top(0)
            //   a-left(3)   ↔ b-right(1)
            let (ax, ay) = (a % w, a / w);
            let nb_info: [(Option<Position>, usize, usize); 4] = [
                (if ay > 0 { Some((ay - 1) * w + ax) } else { None }, 0, 2),
                (if ax + 1 < w { Some(ay * w + (ax + 1)) } else { None }, 1, 3),
                (if ay + 1 < h { Some((ay + 1) * w + ax) } else { None }, 2, 0),
                (if ax > 0 { Some(ay * w + (ax - 1)) } else { None }, 3, 1),
            ];

            let mut removed_here: Vec<u32> = Vec::new();
            let mut i = 0;
            while i < self.domains[a as usize].len() {
                let r_id = self.domains[a as usize][i];
                let r = self.rows[r_id as usize];
                let mut supported = true;
                for (nb_opt, side_a, side_b) in nb_info.iter() {
                    let Some(nb) = nb_opt else { continue; };
                    if self.placed[*nb as usize].is_some() { continue; }
                    let required = r.edges[*side_a] as usize;
                    let nb_u = *nb as usize;
                    // O(1) total: count of in-D[nb] rows with edges[side_b]=required.
                    let total = count[nb_u * stride_pos + side_b * n_colors + required];
                    // Subtract same-piece rows present in D[nb] with matching face.
                    // Each piece has up to 4 rotations; iterate them.
                    let pid_base = usize::from(r.piece_id) * 4;
                    let mut same_piece = 0u16;
                    for rot in 0..4usize {
                        let cand = pid_base + rot;
                        if cand >= n_rows { break; }
                        let row_cand = self.rows[cand];
                        if !row_cand.valid { continue; }
                        if row_cand.edges[*side_b] as usize != required { continue; }
                        let word = present[nb_u * words_per_pos + cand / 64];
                        if (word >> (cand % 64)) & 1 == 1 {
                            same_piece += 1;
                        }
                    }
                    if total <= same_piece {
                        supported = false;
                        break;
                    }
                }
                if supported {
                    i += 1;
                } else {
                    removed_here.push(r_id);
                    self.domains[a as usize].swap_remove(i);
                    // Incremental cache update for position a.
                    let a_u = a as usize;
                    let r_idx = r_id as usize;
                    present[a_u * words_per_pos + r_idx / 64] &= !(1u64 << (r_idx % 64));
                    for s in 0..4 {
                        let c = r.edges[s] as usize;
                        count[a_u * stride_pos + s * n_colors + c] -= 1;
                    }
                }
            }
            if !removed_here.is_empty() {
                self.stats.propagations += removed_here.len() as u64;
                let empty = self.domains[a as usize].is_empty();
                all_removed.push((a, removed_here));
                if empty {
                    self.stats.domain_wipeouts += 1;
                    self.emit(sink, depth, EventBody::DomainWipeout { position: a });
                    return Ac3Outcome::Wipeout { removed: all_removed };
                }
                // Re-queue unplaced neighbours of a: their support in a
                // may have changed.
                for nb_opt in seed_neighbors(a, w, h).iter() {
                    let Some(nb) = nb_opt else { continue; };
                    if self.placed[*nb as usize].is_none() && !on_queue[*nb as usize] {
                        queue.push(*nb);
                        on_queue[*nb as usize] = true;
                    }
                }
            }
        }
        Ac3Outcome::Ok { removed: all_removed }
    }

    /// Build a 4-element neighbor snapshot for `pos`: [top, right, bot,
    /// left]. For placed neighbors we report their facing-edge color
    /// (the edge that touches `pos`). `placed_lookup` is consulted to
    /// determine which neighbors are currently placed.
    fn neighbor_info(&self, pos: Position) -> [Option<NeighborInfo>; 4] {
        let (x, y) = self.puzzle.xy(pos);
        let w = self.puzzle.width;
        let h = self.puzzle.height;
        let nps: [(Option<Position>, usize); 4] = [
            (if y > 0 { Some((y - 1) * w + x) } else { None }, 2),  // top: their bottom face
            (if x + 1 < w { Some(y * w + (x + 1)) } else { None }, 3), // right: their left
            (if y + 1 < h { Some((y + 1) * w + x) } else { None }, 0), // bot: their top
            (if x > 0 { Some(y * w + (x - 1)) } else { None }, 1),  // left: their right
        ];
        let mut out: [Option<NeighborInfo>; 4] = [None; 4];
        for (i, (np, facing_idx)) in nps.iter().enumerate() {
            let Some(np) = np else { continue; };
            let placed = self.placed[*np as usize].is_some();
            let facing_color = if placed {
                let row_id = self.placed[*np as usize].unwrap();
                self.rows[row_id as usize].edges[*facing_idx]
            } else {
                0 // arbitrary; consumer ignores facing_color when placed=false
            };
            out[i] = Some(NeighborInfo { placed, facing_color });
        }
        out
    }

    fn run_extra_propagators(&self, depth: u32) -> PropagatorResult {
        if !self.config.class_balance_propagator
            && !self.config.parity_propagator
            && !self.config.island_propagator
            && !self.config.gacolor_propagator
            && !self.config.multiset_equality_propagator
        {
            return PropagatorResult::Ok;
        }
        // Depth gate (Joe-Saunders 2026): suppress Step-8 propagators
        // below threshold so early-search throughput approaches the
        // bare-edge-equality + AC-3 inner-loop ceiling.
        if let Some(threshold) = self.config.depth_threshold_for_propagators {
            if depth < threshold {
                return PropagatorResult::Ok;
            }
        }
        let placed_info = self.snapshot_placement_info();
        let ctx = PropagatorContext {
            puzzle: self.puzzle,
            placed: &placed_info,
            used_pieces: &self.used,
            domains: &self.domains,
        };
        if self.config.class_balance_propagator
            && class_balance_check(&ctx) == PropagatorResult::Wipeout
        {
            return PropagatorResult::Wipeout;
        }
        // gacolor uses the incremental cache for O(color_count) checks;
        // a fresh full recompute via `gacolor_check` is available for
        // unit testing parity vs incremental correctness, but the hot
        // path goes through GaColorState.
        if self.config.gacolor_propagator {
            let _ = gacolor_check; // keep symbol live for tests
            if let Some(gc) = self.gacolor.as_ref() {
                if gc.feasible() == PropagatorResult::Wipeout {
                    return PropagatorResult::Wipeout;
                }
            }
        }
        if self.config.island_propagator
            && island_check(&ctx) == PropagatorResult::Wipeout
        {
            return PropagatorResult::Wipeout;
        }
        if self.config.parity_propagator
            && parity_check(&ctx) == PropagatorResult::Wipeout
        {
            return PropagatorResult::Wipeout;
        }
        // NS-1 multiset equality: cheapest after the border ring closes;
        // before that the supply terms are loose and rarely triggers.
        if self.config.multiset_equality_propagator
            && multiset_equality_check(&ctx) == PropagatorResult::Wipeout
        {
            return PropagatorResult::Wipeout;
        }
        PropagatorResult::Ok
    }

    pub(crate) fn restore(&mut self, undo: Vec<(Position, Vec<u32>)>) {
        for (pos, mut removed) in undo {
            self.domains[pos as usize].append(&mut removed);
        }
    }

    fn board_from_state(&self) -> Board {
        let mut b = Board::empty(self.puzzle);
        for (i, p) in self.placed.iter().enumerate() {
            if let Some(row_id) = p {
                let r = self.rows[*row_id as usize];
                b.place(i as Position, r.piece_id, Rotation::from_u8(r.rotation).unwrap());
            }
        }
        b
    }

    // Apply symmetry-breaking pin (canonical corner at (0,0) when no user
    // hint touches it) and user-supplied hints (each hint position has its
    // domain restricted to the chosen (piece, rotation) and is committed
    // via place_and_propagate). Returns Err with the outcome if either
    // step is infeasible. Used by both the single-threaded run() and the
    // parallel root-split path so hints are honoured in both.
    pub(crate) fn apply_symmetry_and_hints(
        &mut self,
        sink: &mut dyn EventSink,
    ) -> Result<(), SolveOutcome> {
        // Symmetry-breaking. The board has D4 rotational symmetry: each
        // solution has 4 rotational copies (or 8 if we also count
        // reflection, which we don't here because pieces are
        // distinguishable). We pin the lowest-id corner piece at (0,0)
        // in its single rotation that puts BORDER on top and left. Any
        // valid solution under our pieces has *some* corner piece at
        // (0,0); by forcing the canonical one we visit exactly 1/4 of
        // the symmetric copies. If the puzzle's user_hints already pin
        // (0,0), we skip this (user knows best).
        if self.config.break_symmetry && self.opts.hints.hints.iter().all(|h| h.position != 0) {
            let canonical_corner = self.puzzle.pieces().iter()
                .filter(|p| p.is_corner())
                .min_by_key(|p| p.id);
            if let Some(piece) = canonical_corner {
                let pid = usize::from(piece.id);
                let canonical_row_id = (0..4u32).find_map(|r| {
                    let row = self.rows[pid * 4 + r as usize];
                    if !row.valid { return None; }
                    if row.edges[0] == BORDER && row.edges[3] == BORDER {
                        Some(pid as u32 * 4 + r)
                    } else { None }
                });
                if let Some(row_id) = canonical_row_id {
                    if self.domains[0].iter().any(|r| *r == row_id) {
                        self.domains[0].retain(|r| *r == row_id);
                        if let PropagationOutcome::Wipeout { .. } =
                            self.place_and_propagate(sink, 0, 0, row_id)
                        {
                            return Err(SolveOutcome::Error(
                                "symmetry-breaking placement caused immediate wipeout".into()
                            ));
                        }
                    }
                }
            }
        }

        for h in self.opts.hints.hints.clone() {
            let row_id = u32::from(h.piece_id) * 4 + u32::from(h.rotation.as_u8());
            let pos_idx = h.position as usize;
            if pos_idx >= self.domains.len()
                || !self.domains[pos_idx].iter().any(|r| *r == row_id)
            {
                return Err(SolveOutcome::Error(format!(
                    "hint at position {} is incompatible with constraints", h.position
                )));
            }
            self.domains[pos_idx].retain(|r| *r == row_id);
            if let PropagationOutcome::Wipeout { .. } = self.place_and_propagate(sink, 0, h.position, row_id) {
                return Err(SolveOutcome::Error(format!(
                    "hint at position {} causes immediate wipeout", h.position
                )));
            }
        }
        Ok(())
    }

    pub(crate) fn run(mut self, sink: &mut dyn EventSink) -> SolveOutcome {
        self.emit(sink, 0, EventBody::Started {
            solver_id: self.solver_id.clone(),
            heuristic_profile: self.heuristic_profile.clone(),
            puzzle_fingerprint: self.puzzle.fingerprint(),
            seed: self.opts.seed,
            started_wall_us: 0,
        });

        if let Err(e) = self.apply_symmetry_and_hints(sink) {
            return e;
        }

        let mut solutions = Vec::<Board>::new();
        let res = self.recurse(sink, 0, &mut solutions);

        self.stats.time_ms = self.elapsed_us() / 1000;
        match res {
            RecurseResult::Found if matches!(self.opts.mode, SolveMode::FirstSolution) => {
                self.stats.solutions_found = 1;
                let board = solutions.into_iter().next().unwrap();
                self.emit(sink, 0, EventBody::Solved {
                    board: board.clone(), final_stats: self.stats,
                });
                SolveOutcome::Solved(board)
            }
            RecurseResult::Found | RecurseResult::Exhausted => {
                self.stats.solutions_found = solutions.len() as u64;
                self.emit(sink, 0, EventBody::Exhausted {
                    final_stats: self.stats,
                    solutions_found: solutions.len() as u64,
                });
                if matches!(self.opts.mode, SolveMode::FirstSolution) || solutions.is_empty() {
                    SolveOutcome::Exhausted
                } else {
                    SolveOutcome::AllSolutions(solutions)
                }
            }
            RecurseResult::TimedOut => {
                let best = self.best_partial.clone().unwrap_or_else(|| self.board_from_state());
                let best_depth = self.best_depth;
                self.emit(sink, 0, EventBody::TimedOut {
                    final_stats: self.stats,
                    best_partial: best.clone(),
                    best_depth,
                });
                SolveOutcome::TimedOut { best_partial: best, best_depth }
            }
            RecurseResult::Cancelled => {
                let best = self.best_partial.clone().unwrap_or_else(|| self.board_from_state());
                let best_depth = self.best_depth;
                self.emit(sink, 0, EventBody::Cancelled {
                    final_stats: self.stats,
                    best_partial: best.clone(),
                    best_depth,
                    solutions_so_far: solutions.clone(),
                });
                SolveOutcome::Cancelled {
                    best_partial: best, best_depth,
                    solutions_so_far: solutions,
                }
            }
        }
    }

    // Phase-1 enumerator for RootSplit parallelism. Walks the search to
    // `target_depth`, pushing each valid partial placement (as a sequence
    // of (position, row_id)) to `units`. Caller resets engine state
    // between calls; restoration of placed/used/domains here mirrors the
    // standard recursion's backtracking. Limits to `cap_units` to avoid
    // pathological enumeration on already-easy puzzles.
    pub(crate) fn enumerate_units(
        &mut self,
        depth: u32,
        target_depth: u32,
        prefix: &mut Vec<(Position, u32)>,
        units: &mut Vec<Vec<(Position, u32)>>,
        cap_units: usize,
    ) {
        if units.len() >= cap_units { return; }
        if depth >= target_depth {
            units.push(prefix.clone());
            return;
        }
        let pos = match self.select_position() {
            Some(p) => p,
            None => {
                // Reached a complete state in the prefix — treat as a unit
                // even though there's nothing left to search; the worker
                // will discover the solution immediately.
                units.push(prefix.clone());
                return;
            }
        };
        let domain_snapshot = self.domains[pos as usize].clone();
        for &row_id in &domain_snapshot {
            if units.len() >= cap_units { return; }
            let row = self.rows[row_id as usize];
            let piece_idx = usize::from(row.piece_id);
            if self.used[piece_idx] { continue; }
            let saved_domain = std::mem::take(&mut self.domains[pos as usize]);
            // Reuse place_and_propagate against a null sink — we
            // intentionally throw away events during enumeration.
            let mut null = eternity2_events::NullSink;
            match self.place_and_propagate(&mut null, depth, pos, row_id) {
                PropagationOutcome::Ok { undo } => {
                    prefix.push((pos, row_id));
                    self.enumerate_units(depth + 1, target_depth, prefix, units, cap_units);
                    prefix.pop();
                    self.restore(undo);
                }
                PropagationOutcome::Wipeout { undo } => {
                    self.restore(undo);
                }
            }
            self.undo_place(pos, row_id);
            self.domains[pos as usize] = saved_domain;
            if units.len() >= cap_units { return; }
        }
    }

    pub(crate) fn recurse(
        &mut self,
        sink: &mut dyn EventSink,
        depth: u32,
        solutions: &mut Vec<Board>,
    ) -> RecurseResult {
        if self.node_id & 0xf == 0 {
            if !sink.should_continue() { return RecurseResult::Cancelled; }
            if self.timed_out() { return RecurseResult::TimedOut; }
        }

        self.stats.current_depth = depth;
        if depth > self.best_depth {
            self.best_depth = depth;
            self.best_partial = Some(self.board_from_state());
            self.stats.max_depth_seen = depth;
        }

        let pos = match self.select_position() {
            Some(p) => p,
            None => {
                solutions.push(self.board_from_state());
                return RecurseResult::Found;
            }
        };

        let mut domain_snapshot = self.domains[pos as usize].clone();
        let reason = self.selection_reason();
        self.emit(sink, depth, EventBody::VariableSelected {
            position: pos,
            domain_size: domain_snapshot.len() as u32,
            score: 0.0,
            reason,
        });

        // LCV — Least Constraining Value. Score each candidate row by
        // the number of neighbour-domain rows it would eliminate, pick
        // ascending so we try the "safest" (most-future-options) values
        // first. Standard CP technique (Haralick & Elliott 1980).
        //
        // Cost: O(|D| × 4 × |D_nb|) once per node. Pays for itself when
        // it lets us avoid a deep wrong branch.
        if matches!(self.config.value_order, ValueOrder::LeastConstraining)
            && domain_snapshot.len() > 1
        {
            let (x, y) = self.puzzle.xy(pos);
            let w = self.puzzle.width;
            let h = self.puzzle.height;
            // (neighbour, our_side, their_side)
            let nbs: [(Option<Position>, usize, usize); 4] = [
                (if y > 0 { Some((y - 1) * w + x) } else { None }, 0, 2),
                (if x + 1 < w { Some(y * w + (x + 1)) } else { None }, 1, 3),
                (if y + 1 < h { Some((y + 1) * w + x) } else { None }, 2, 0),
                (if x > 0 { Some(y * w + (x - 1)) } else { None }, 3, 1),
            ];
            let mut scored: Vec<(u32, u32)> = domain_snapshot.iter().map(|&r_id| {
                let r = self.rows[r_id as usize];
                let mut prune_count = 0u32;
                for (nb_opt, our_side, their_side) in nbs.iter() {
                    let Some(nb) = nb_opt else { continue; };
                    if self.placed[*nb as usize].is_some() { continue; }
                    let needed = r.edges[*our_side];
                    for &nb_r_id in &self.domains[*nb as usize] {
                        let nb_r = self.rows[nb_r_id as usize];
                        if nb_r.piece_id == r.piece_id || nb_r.edges[*their_side] != needed {
                            prune_count += 1;
                        }
                    }
                }
                (prune_count, r_id)
            }).collect();
            scored.sort_by_key(|(s, _)| *s);
            domain_snapshot.clear();
            domain_snapshot.extend(scored.into_iter().map(|(_, r)| r));
        }

        // RandomShuffle value order: shuffle the candidate-row order using
        // the opts.seed-derived RNG. Combined with deterministic
        // BorderFirstMrv variable ordering, this diversifies CP partials
        // across seeds while keeping the variable selection strong.
        if matches!(self.config.value_order, ValueOrder::RandomShuffle)
            && domain_snapshot.len() > 1
        {
            // Fisher-Yates with our seeded RNG.
            let n = domain_snapshot.len();
            for i in (1..n).rev() {
                let j = (self.next_random() as usize) % (i + 1);
                domain_snapshot.swap(i, j);
            }
        }

        // PreferredFirst: stable partition; preferred-piece rows first.
        // Verhaard 2008. Caller sets `opts.preferred_pieces`.
        if matches!(self.config.value_order, ValueOrder::PreferredFirst)
            && domain_snapshot.len() > 1
            && !self.opts.preferred_pieces.is_empty()
        {
            // O(|preferred|) bitset lookup keeps this cheap per node.
            let max_pid = self.opts.preferred_pieces.iter().map(|p| *p as usize).max().unwrap_or(0) + 1;
            let mut pref = vec![false; max_pid];
            for &pid in &self.opts.preferred_pieces {
                if (pid as usize) < pref.len() { pref[pid as usize] = true; }
            }
            // Stable partition: preferred first, others after; preserve
            // existing relative order within each bucket.
            let mut a: Vec<u32> = Vec::with_capacity(domain_snapshot.len());
            let mut b: Vec<u32> = Vec::new();
            for &r_id in domain_snapshot.iter() {
                let pid = self.rows[r_id as usize].piece_id as usize;
                if pid < pref.len() && pref[pid] {
                    a.push(r_id);
                } else {
                    b.push(r_id);
                }
            }
            a.extend(b);
            domain_snapshot.clear();
            domain_snapshot.extend(a);
        }

        for &row_id in &domain_snapshot {
            let row = self.rows[row_id as usize];
            let piece_idx = usize::from(row.piece_id);
            if self.used[piece_idx] { continue; }
            self.emit(sink, depth, EventBody::ValueTried {
                position: pos,
                piece_id: row.piece_id,
                rotation: Rotation::from_u8(row.rotation).unwrap(),
            });
            self.stats.nodes += 1;
            let saved_domain = std::mem::take(&mut self.domains[pos as usize]);
            let outcome = self.place_and_propagate(sink, depth, pos, row_id);
            match outcome {
                PropagationOutcome::Ok { undo } => {
                    match self.recurse(sink, depth + 1, solutions) {
                        RecurseResult::Found => {
                            if matches!(self.opts.mode, SolveMode::FirstSolution) {
                                return RecurseResult::Found;
                            }
                            if self.opts.max_solutions > 0
                                && solutions.len() as u32 >= self.opts.max_solutions
                            {
                                return RecurseResult::Found;
                            }
                        }
                        terminal @ (RecurseResult::TimedOut | RecurseResult::Cancelled) => {
                            self.restore(undo);
                            self.undo_place(pos, row_id);
                            self.domains[pos as usize] = saved_domain;
                            return terminal;
                        }
                        RecurseResult::Exhausted => {}
                    }
                    self.restore(undo);
                }
                PropagationOutcome::Wipeout { undo } => {
                    self.restore(undo);
                    self.stats.backtracks += 1;
                    self.emit(sink, depth, EventBody::Backtrack {
                        from_depth: depth + 1,
                        to_depth: depth,
                        cause: BacktrackCause::DomainWipeout,
                    });
                }
            }
            self.undo_place(pos, row_id);
            self.domains[pos as usize] = saved_domain.clone();
        }
        RecurseResult::Exhausted
    }

    /// Reverse the bookkeeping side-effects of a placement (NOT the
    /// domain pruning — that's `restore(undo)`'s job). Must be called
    /// while `placed[pos]` still references the row, before
    /// `domains[pos]` is rebuilt.
    pub(crate) fn undo_place(&mut self, pos: Position, row_id: u32) {
        let row = self.rows[row_id as usize];
        if self.gacolor.is_some() {
            let n_info = self.neighbor_info(pos);
            if let Some(gc) = self.gacolor.as_mut() {
                gc.apply_unplace(&row.edges, &n_info);
            }
        }
        self.placed[pos as usize] = None;
        let piece_idx = usize::from(row.piece_id);
        self.used[piece_idx] = false;
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum RecurseResult { Found, Exhausted, TimedOut, Cancelled }

pub(crate) enum PropagationOutcome {
    Ok { undo: Vec<(Position, Vec<u32>)> },
    Wipeout { undo: Vec<(Position, Vec<u32>)> },
}

pub(crate) enum Ac3Outcome {
    Ok { removed: Vec<(Position, Vec<u32>)> },
    Wipeout { removed: Vec<(Position, Vec<u32>)> },
}

enum PruneResult {
    Ok,
    Removed(Vec<u32>),
    Wipeout { removed: Vec<u32> },
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_core::{Edges, Piece};

    fn p(id: PieceId, t: Color, r: Color, b: Color, l: Color) -> Piece {
        Piece::new(id, Edges::new(t, r, b, l))
    }

    #[test]
    fn solves_2x2_trivial() {
        let pieces = vec![
            p(0, 0, 1, 1, 0),
            p(1, 0, 0, 1, 1),
            p(2, 1, 1, 0, 0),
            p(3, 1, 0, 0, 1),
        ];
        let puzzle = Puzzle::new(2, 2, 2, pieces).unwrap();
        let mut s = EngineSolver::border_first_lcv();
        let mut sink = eternity2_events::BufferSink::new();
        assert!(matches!(s.solve(&puzzle, &SolveOpts::default(), &mut sink), SolveOutcome::Solved(_)));
    }

    #[test]
    fn solves_5x5_from_generator() {
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 5, interior_colors: 5, seed: 11 }).unwrap();
        for mut s in [
            EngineSolver::border_first_lcv(),
            EngineSolver::rare_color_first(),
            EngineSolver::border_first_random(),
        ] {
            let mut sink = eternity2_events::BufferSink::new();
            let mut opts = SolveOpts::default();
            opts.time_budget_ms = 60_000;
            let outcome = s.solve(&puzzle, &opts, &mut sink);
            let profile = s.heuristic_profile().0;
            assert!(matches!(outcome, SolveOutcome::Solved(_)), "{profile} got {outcome:?}");
        }
    }

    #[test]
    #[ignore = "performance comparison; run with --ignored"]
    fn parity_propagator_node_count_comparison_6x6() {
        // Propagators are pruning rules, but search order can be
        // sensitive to *which* state we backtrack from — a stronger
        // propagator occasionally forces an alternative path that
        // happens to take more nodes on a given seed. The honest
        // assertion is on averages, not per-seed monotonicity.
        use eternity2_events::{BufferSink, EventBody};
        use eternity2_generator::{generate, GeneratorConfig};
        let seeds = [3u64, 7, 13, 21, 42];
        let mut sum_a = 0u64;
        let mut sum_b = 0u64;
        let mut sum_c = 0u64;
        for seed in seeds {
            let puzzle = generate(GeneratorConfig { size: 6, interior_colors: 5, seed }).unwrap();
            let nodes = |s: &mut EngineSolver, puzzle: &Puzzle| -> u64 {
                let mut sink = BufferSink::new();
                let mut opts = SolveOpts::default();
                opts.time_budget_ms = 60_000;
                s.solve(puzzle, &opts, &mut sink);
                sink.events.iter().filter(|e| matches!(e.body, EventBody::ValueTried { .. })).count() as u64
            };
            let n_a = nodes(&mut EngineSolver::border_first_lcv(), &puzzle);
            let n_b = nodes(&mut EngineSolver::border_first_parity(), &puzzle);
            let n_c = nodes(&mut EngineSolver::border_first_full(), &puzzle);
            eprintln!("seed={seed} baseline={n_a} parity={n_b} full={n_c}");
            sum_a += n_a;
            sum_b += n_b;
            sum_c += n_c;
        }
        eprintln!("totals: baseline={sum_a} parity={sum_b} full={sum_c}");
        // On average across seeds, the stronger propagator set should
        // not be dramatically worse. Use a 50% headroom assertion to
        // catch real regressions while accepting per-seed variance.
        assert!(sum_b <= sum_a + sum_a / 2,
            "parity sum {sum_b} unexpectedly larger than baseline {sum_a}");
        assert!(sum_c <= sum_a + sum_a / 2,
            "full sum {sum_c} unexpectedly larger than baseline {sum_a}");
    }

    #[test]
    fn parity_propagator_reduces_or_equals_nodes() {
        // Compare node count: with parity propagator on, the engine
        // should never explore more nodes than without (parity is a
        // strict superset of edge_color pruning; in practice it should
        // explore fewer nodes on hard-ish puzzles, but the loose
        // assertion ("not more") is the safe contract).
        use eternity2_events::{BufferSink, EventBody};
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 5, interior_colors: 5, seed: 11 }).unwrap();

        fn nodes(sink: &BufferSink) -> u64 {
            sink.events.iter().filter(|e| matches!(e.body, EventBody::ValueTried { .. })).count() as u64
        }

        let mut baseline = EngineSolver::border_first_lcv();
        let mut sink_a = BufferSink::new();
        baseline.solve(&puzzle, &SolveOpts::default(), &mut sink_a);

        let mut with_parity = EngineSolver::border_first_parity();
        let mut sink_b = BufferSink::new();
        with_parity.solve(&puzzle, &SolveOpts::default(), &mut sink_b);

        let n_a = nodes(&sink_a);
        let n_b = nodes(&sink_b);
        eprintln!("baseline nodes: {n_a}, with parity: {n_b}");
        // Parity should be at least as strong as baseline (never more nodes).
        // Strict reduction depends on the puzzle — for this seed it should
        // be equal-or-less.
        assert!(n_b <= n_a, "parity should not increase node count; baseline={n_a} parity={n_b}");
    }

    #[test]
    fn propagator_enabled_profiles_solve_5x5() {
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 5, interior_colors: 5, seed: 11 }).unwrap();
        for mut s in [
            EngineSolver::border_first_parity(),
            EngineSolver::border_first_full(),
        ] {
            let mut sink = eternity2_events::BufferSink::new();
            let mut opts = SolveOpts::default();
            opts.time_budget_ms = 60_000;
            let outcome = s.solve(&puzzle, &opts, &mut sink);
            let profile = s.heuristic_profile().0;
            assert!(matches!(outcome, SolveOutcome::Solved(_)),
                "{profile} got {outcome:?}");
        }
    }

    #[test]
    #[ignore = "wall-time scaling check; run with --ignored"]
    fn root_split_scales_on_6x6() {
        use std::time::Instant;
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 6, interior_colors: 5, seed: 3 }).unwrap();
        let measure = |mut s: EngineSolver| -> u128 {
            let mut sink = eternity2_events::BufferSink::new();
            let mut opts = SolveOpts::default();
            opts.time_budget_ms = 120_000;
            let t = Instant::now();
            s.solve(&puzzle, &opts, &mut sink);
            t.elapsed().as_millis()
        };
        let seq_ms = measure(EngineSolver::border_first_lcv());
        let par_ms = measure(EngineSolver::border_first_lcv_par());
        eprintln!("seq: {seq_ms} ms, par: {par_ms} ms (threads={})",
                  rayon::current_num_threads());
    }

    #[test]
    fn root_split_solves_4x4_and_5x5() {
        use eternity2_generator::{generate, GeneratorConfig};
        for size in [4u32, 5] {
            let puzzle = generate(GeneratorConfig { size, interior_colors: size, seed: 17 }).unwrap();
            let mut s = EngineSolver::border_first_lcv_par();
            let mut sink = eternity2_events::BufferSink::new();
            let mut opts = SolveOpts::default();
            opts.time_budget_ms = 60_000;
            let outcome = s.solve(&puzzle, &opts, &mut sink);
            assert!(matches!(outcome, SolveOutcome::Solved(_)),
                "{size}x{size} parallel got {outcome:?}");
        }
    }

    #[test]
    fn root_split_emits_one_started_event() {
        use eternity2_events::EventBody;
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 4, interior_colors: 4, seed: 3 }).unwrap();
        let mut s = EngineSolver::border_first_lcv_par();
        let mut sink = eternity2_events::BufferSink::new();
        s.solve(&puzzle, &SolveOpts::default(), &mut sink);
        let started_count = sink.events.iter()
            .filter(|e| matches!(e.body, EventBody::Started { .. }))
            .count();
        assert_eq!(started_count, 1, "parallel run must emit exactly one Started");
    }

    #[test]
    fn engine_id_and_profile_in_started() {
        use eternity2_events::EventBody;
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 3, interior_colors: 3, seed: 1 }).unwrap();
        let mut s = EngineSolver::border_first_lcv();
        let mut sink = eternity2_events::BufferSink::new();
        s.solve(&puzzle, &SolveOpts::default(), &mut sink);
        let (sid, prof) = sink.events.iter().find_map(|e| match &e.body {
            EventBody::Started { solver_id, heuristic_profile, .. } => Some((solver_id.clone(), heuristic_profile.clone())),
            _ => None,
        }).unwrap();
        assert_eq!(sid, "engine");
        assert_eq!(prof, "border_first_lcv");
    }
}
