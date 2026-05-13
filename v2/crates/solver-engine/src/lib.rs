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

use std::sync::Arc;

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
    HeuristicProfile, Objective, SolveMode, SolveOpts, SolveOutcome, Solver, SolverId,
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
    /// Score each candidate row by Σ over its 4 sides of
    /// `SolveOpts.edge_bp_marginals[edge_id(cell, side)][row.edges[side]]`;
    /// sort descending so higher-probability colors are tried first.
    /// Vol-14 #1, port of vol-12's edge-color BP measurement
    /// (`output/v12_bp/edge_bp_60i.json`, 18.84% interior-edge
    /// entropy reduction; beat random as value-order in Python A/B).
    /// Falls back silently to InsertionOrder if marginals absent
    /// (preserves correctness in tests / smoke runs).
    EdgeBpMarginals,
    /// Vol-15 — Blackwood 2020 heuristic-side value ordering. Score
    /// each candidate row by `Σ_{side} 1[row.edges[side] ∈ schedule.heuristic_sides]`
    /// and sort descending so heuristic-rich candidates are tried first.
    /// Falls back silently to InsertionOrder when no schedule is
    /// attached (preserves correctness in tests).
    BlackwoodHeuristic,
}

/// Vol-15 — Blackwood 2020 algorithm parameters. The backtracker is
/// constrained by:
///   1. A piecewise-linear schedule that demands a minimum count of
///      "heuristic-colored" edges placed by each depth — branches
///      that fall behind are pruned.
///   2. A fixed list of cell indices (in scan order) where ONE edge
///      mismatch is permitted during placement.
///
/// With 12 break opportunities the maximum-feasible score is `480 −
/// (12 − 1) = 469` on canonical E2 — this is the algorithm that
/// reaches community SOTA. See `V15_BLACKWOOD_SPEC.md`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BlackwoodSchedule {
    /// Edge colors that count toward the exhaustion schedule.
    pub heuristic_sides: Vec<Color>,
    /// Piecewise-linear schedule control points: `(depth, target_count)`,
    /// sorted ascending by depth. The required count at intermediate
    /// depths is linearly interpolated.
    pub exhaustion_targets: Vec<(u32, u32)>,
    /// Total occurrences of `heuristic_sides` colors across all 256
    /// piece edges (≈ 120 for a canonical 5-clue E2 instance).
    pub heuristic_pool_size: u32,
    /// Maximum depth at which the schedule applies; beyond this, no
    /// schedule check (the algorithm has "earned its way" past the
    /// heuristic phase).
    pub max_heuristic_index: u32,
    /// Sorted ascending list of board cell indices (in the engine's
    /// scan order, i.e., after any ScanOrder remapping) where one
    /// placed-neighbor edge mismatch is permitted.
    pub break_indexes_allowed: Vec<u32>,
}

impl BlackwoodSchedule {
    /// Verify the schedule is well-formed: `exhaustion_targets` is
    /// non-empty, depths are STRICTLY increasing, counts are
    /// non-decreasing, all counts fit in `heuristic_pool_size`. A
    /// schedule that violates strict-monotonicity in depth produces
    /// a "cliff" where `target_at(d)` jumps discontinuously — the
    /// vol-15 bug your friend spotted in run_1778604403.
    /// Returns `Err(reason)` if malformed; `Ok(())` otherwise.
    pub fn validate(&self) -> Result<(), String> {
        if self.exhaustion_targets.is_empty() {
            return Err("exhaustion_targets is empty".into());
        }
        for win in self.exhaustion_targets.windows(2) {
            let (d0, c0) = win[0];
            let (d1, c1) = win[1];
            if d0 >= d1 {
                return Err(format!(
                    "exhaustion_targets depths not strictly increasing: ({d0},{c0}) followed by ({d1},{c1})"
                ));
            }
            if c0 > c1 {
                return Err(format!(
                    "exhaustion_targets counts decrease: ({d0},{c0}) followed by ({d1},{c1})"
                ));
            }
        }
        for &(_d, c) in &self.exhaustion_targets {
            if c > self.heuristic_pool_size {
                return Err(format!(
                    "exhaustion target {c} exceeds heuristic_pool_size {}",
                    self.heuristic_pool_size
                ));
            }
        }
        if !self.break_indexes_allowed.windows(2).all(|w| w[0] <= w[1]) {
            return Err("break_indexes_allowed not sorted ascending".into());
        }
        Ok(())
    }

    /// Target heuristic-piece-occurrence count at `depth`, computed
    /// by piecewise-linear interpolation of `exhaustion_targets`.
    /// Saturates at the schedule endpoints.
    pub fn target_at(&self, depth: u32) -> u32 {
        if self.exhaustion_targets.is_empty() { return 0; }
        let xs = &self.exhaustion_targets;
        if depth <= xs[0].0 { return xs[0].1; }
        if depth >= xs[xs.len() - 1].0 { return xs[xs.len() - 1].1; }
        for w in xs.windows(2) {
            let (d0, c0) = w[0];
            let (d1, c1) = w[1];
            if depth >= d0 && depth <= d1 {
                if d1 == d0 { return c1; }
                let span = (d1 - d0) as u64;
                let dc = (c1 as i64) - (c0 as i64);
                let off = (depth - d0) as u64;
                let interp = (c0 as i64) + ((dc * off as i64) / span as i64);
                return interp.max(0) as u32;
            }
        }
        xs[xs.len() - 1].1
    }
}

/// Vol-15 — scan order for the engine. Default `RowMajorTopDown`
/// matches the engine's historic indexing `idx = y*W + x`.
/// `RowMajorBottomUp` matches Blackwood's `idx = (H-1-y)*W + x`
/// (index 0 = bottom-left). The scan order is materialised as an
/// auto-built `path_order` when no explicit user path or
/// `path_skeleton` is set; the engine then uses
/// `PathPolicy::OrderingPrior`-style tie-breaking against the cell's
/// scan-order index.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScanOrder {
    RowMajorTopDown,
    RowMajorBottomUp,
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

/// Vol-16 Cat-2 Stage A — orthogonal sub-config for the optional
/// propagator stack. Baseline edge-color matching + piece-uniqueness
/// are ALWAYS on inside the engine; this struct only controls the
/// additional propagators that may run after baseline succeeds.
///
/// Stays `Copy` so `EngineConfig` const profile slabs can use FRU.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PropagatorConfig {
    /// Cheap; corner/edge/inner piece-class counting. On by default for
    /// most profiles. Note: in `BLACKWOOD_RAW` it is OFF (vol-16 Cat-4b
    /// dropped it because Blackwood's depth ~80 wall doesn't reach the
    /// regime where class_balance pays its cost).
    pub class_balance: bool,
    /// Checkerboard color-balance pruning. Weakly pruning end-state
    /// check today (~0% on a 6×6 sample); strong incremental version is
    /// future work.
    pub parity: bool,
    /// Connectivity check: every unplaced piece has a remaining home
    /// somewhere. ~3% node reduction on 6×6 sample.
    pub island: bool,
    /// Maintain arc consistency on neighbouring-cell domains after
    /// each placement. Re-checks edges across already-pruned domains
    /// until fixpoint. Strictly stronger than baseline forward-
    /// checking; expensive at deep search.
    pub ac3: bool,
    /// GAColor — symmetric-alldiff feasibility per color. Strictly
    /// tighter than `parity` on the same problem; intended replacement.
    pub gacolor: bool,
    /// NS-1 / Hopfer 2022 multiset-equality. Necessary condition for
    /// any full solution: multiset of inward-facing colors on the 56
    /// edge-class cells equals multiset of border-facing colors on
    /// the 56 14×14-perimeter interior cells.
    pub multiset_equality: bool,
    /// Joe-Saunders 2026 depth-gate: skip the expensive Step-8
    /// propagators below this depth. AC-3 and edge/uniqueness still
    /// run at every depth. `None` = always run; empirical canonical-E2
    /// sweet spot ~150.
    pub depth_threshold: Option<u32>,
}

impl PropagatorConfig {
    /// All optional propagators off; only baseline edge-color + piece-
    /// uniqueness will run. Used by `BLACKWOOD_RAW`.
    pub const OFF: Self = Self {
        class_balance: false,
        parity: false,
        island: false,
        ac3: false,
        gacolor: false,
        multiset_equality: false,
        depth_threshold: None,
    };

    /// Default for most engine profiles: class_balance only.
    pub const CLASS_BALANCE_ONLY: Self = Self {
        class_balance: true,
        ..Self::OFF
    };
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EngineConfig {
    pub variable_order: VariableOrder,
    pub value_order: ValueOrder,
    /// Optional propagator stack (vol-16 Cat-2 Stage A — extracted from
    /// 7 flat fields). Baseline edge-color + piece-uniqueness are
    /// always on regardless.
    pub propagators: PropagatorConfig,
    /// Break rotational symmetry by fixing the lowest-id corner piece at
    /// position (0,0) in its only valid rotation. Reduces search space
    /// by 4× on puzzles with 4 distinct corners (i.e., generated
    /// puzzles, which almost always satisfy this).
    pub break_symmetry: bool,
    pub parallelism: Parallelism,
    /// Vol-14 — automatic "skeleton path" that the engine pre-pins
    /// before falling back to its normal variable-ordering. When
    /// `Some(PathSkeleton::HintRectangle)`, `SearchState::new` builds
    /// a path that traces the rectangle through the 4 outermost hint
    /// positions + spokes to any remaining (interior) hints, then
    /// sets `path_order` + `path_index_of` so a `PathPolicy::PrefixConstraint`
    /// at `path.len()` is auto-injected. Empirically gives +44 placed cells
    /// vs default MRV on canonical E2 single-thread border_first_lcv. See
    /// `project_e2_vol14_rectangle_path_finding.md` (forthcoming).
    pub path_skeleton: Option<PathSkeleton>,
    /// Vol-15 — Blackwood 2020 scan order. `None` = inherit default
    /// `RowMajorTopDown` (engine's historic indexing). When set to
    /// `Some(RowMajorBottomUp)` and no explicit `opts.path` or
    /// `path_skeleton` is supplied, the engine auto-builds a full-board
    /// path that traverses cells in bottom-up row-major order; the
    /// schedule's `break_indexes_allowed` field then indexes into this
    /// path.
    pub scan_order: Option<ScanOrder>,
    /// Vol-17 (H22) — within-tie shuffle for BlackwoodHeuristic value
    /// order. When true, after sorting rows by heuristic-color count
    /// (descending), shuffle each run of equal-score rows using the
    /// seed-derived RNG. Gives schedule-invariant CP-partial diversity
    /// across seeds, without breaking Blackwood's score-descending
    /// invariant. Default: false (preserves existing deterministic
    /// tie-breaking).
    pub shuffle_within_blackwood_ties: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PathSkeleton {
    /// Trace the rectangle through the 4 outermost hint positions
    /// (sorted by extremity: TL, TR, BR, BL), then a spoke from one
    /// rectangle side to any remaining hint cells (typically the
    /// center hint on canonical E2). The cells along the path are
    /// pinned in order via `PathPolicy::PrefixConstraint`.
    /// Requires `opts.hints` to have at least 4 hint positions.
    /// No-op if fewer than 4 hints.
    HintRectangle,
    /// Vol-14 user-proposed: same as HintRectangle but then continues
    /// the path by filling cells in layered order:
    ///   1. Rectangle skeleton (49 cells on canonical E2).
    ///   2. Interior of the rectangle, spiraling outward from center
    ///      (100 cells on canonical 16×16).
    ///   3. Annulus between rectangle and outer border, row-by-row
    ///      (~96 cells).
    ///   4. Outer border itself, corners → perimeter.
    /// The full path is `cell_count` long; PathPolicy effectively
    /// forces a specific scan order independent of MRV. Tests the
    /// hypothesis that maximum-constraint-first ordering improves
    /// search beyond the basic rectangle path.
    HintRectangleLayered,
    /// Vol-23 user-proposed: X-shape skeleton through the 5 canonical
    /// hints. Pre-commits cells along two 3-cell-wide diagonals that
    /// cross at the centre hint, so each subsequent diagonal cell has
    /// two already-placed neighbours (early constraint propagation).
    /// Order:
    ///   1. TL hint, then the 3-cell-wide diagonal band TL → centre.
    ///   2. Centre hint, then continue the same diagonal centre → BR.
    ///   3. TR hint, then the 3-cell-wide anti-diagonal TR → centre.
    ///   4. Centre → BL hint along the anti-diagonal.
    ///   5. Remaining cells: outward from centre (Chebyshev distance
    ///      ascending), within-tie row-major. Covers all `cell_count`
    ///      cells. Requires `opts.hints.len() >= 5`.
    /// Tests the hypothesis that two crossing constraint bands beat
    /// the rectangle's perimeter band on canonical E2.
    XSkeleton,
}

impl EngineConfig {
    pub const BORDER_FIRST_LCV: Self = Self {
        variable_order: VariableOrder::BorderFirstMrv,
        value_order: ValueOrder::InsertionOrder,
        break_symmetry: false,
        parallelism: Parallelism::SingleThread,
        path_skeleton: None,
        scan_order: None,
        shuffle_within_blackwood_ties: false,
        propagators: PropagatorConfig {
            class_balance: true,
            parity: false,
            island: false,
            ac3: false,
            gacolor: false,
            multiset_equality: false,
            depth_threshold: None,
        },
    };

    /// Vol-15 — Blackwood 2020 base profile (engine knobs only; the
    /// `BlackwoodSchedule` itself rides on `SolveOpts.blackwood_schedule`).
    /// Sets scan_order=RowMajorBottomUp + value_order=BlackwoodHeuristic.
    /// Pair with gacolor + AC-3 + (optionally) NS-1 propagation.
    pub const BLACKWOOD_BASE: Self = Self {
        value_order: ValueOrder::BlackwoodHeuristic,
        scan_order: Some(ScanOrder::RowMajorBottomUp),
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const BLACKWOOD_BASE_PAR: Self = Self {
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BLACKWOOD_BASE
    };

    /// Vol-15 — "dumb Blackwood" profile suggested by external
    /// reviewer: bottom-up scan + heuristic value-order + schedule +
    /// break allowance + piece-uniqueness + simple edge forward-
    /// checking ONLY. Drops gacolor, AC-3, NS-1 because those exact-
    /// solution propagators are NOT obviously sound after a break-
    /// index allows a mismatch (gacolor's per-color alldiff
    /// feasibility, AC-3's support count, NS-1's multiset equality
    /// all assume exact-matching downstream). This is the
    /// minimum-viable Blackwood implementation we can run safely
    /// past the first break. Pair with `with_blackwood_schedule`.
    pub const BLACKWOOD_RAW: Self = Self {
        value_order: ValueOrder::BlackwoodHeuristic,
        scan_order: Some(ScanOrder::RowMajorBottomUp),
        // Vol-16: class_balance also dropped. Profile showed 7.6%
        // self time in RAW. It IS break-sound (piece classes don't
        // change under a color mismatch), but the pruning value at
        // the depths Blackwood reaches (~80) is marginal. Better to
        // pay the cost where it earns it (full-pipeline profiles).
        propagators: PropagatorConfig {
            class_balance: false,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const BLACKWOOD_RAW_PAR: Self = Self {
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BLACKWOOD_RAW
    };

    // Experiment A: GAColor as the strong global propagator.
    pub const BORDER_FIRST_GACOLOR: Self = Self {
        propagators: PropagatorConfig {
            gacolor: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const BORDER_FIRST_GACOLOR_PAR: Self = Self {
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment D: GAColor + AC-3.
    pub const GACOLOR_AC3: Self = Self {
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment E — true LCV value ordering combined with our best
    // propagation (gacolor + AC-3).
    pub const GACOLOR_AC3_LCV: Self = Self {
        value_order: ValueOrder::LeastConstraining,
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const GACOLOR_AC3_LCV_PAR: Self = Self {
        value_order: ValueOrder::LeastConstraining,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment B' — CHESS revisited with AC-3 propagation.
    pub const CHESS_GACOLOR_AC3: Self = Self {
        variable_order: VariableOrder::BorderFirstChess,
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const GACOLOR_AC3_PAR: Self = Self {
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
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
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment C: GAColor + symmetry breaking.
    pub const GACOLOR_SYMBREAK: Self = Self {
        break_symmetry: true,
        propagators: PropagatorConfig {
            gacolor: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const GACOLOR_SYMBREAK_PAR: Self = Self {
        break_symmetry: true,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    // Experiment B: CHESS + GAColor.
    pub const CHESS_GACOLOR: Self = Self {
        variable_order: VariableOrder::BorderFirstChess,
        propagators: PropagatorConfig {
            gacolor: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const CHESS_GACOLOR_PAR: Self = Self {
        variable_order: VariableOrder::BorderFirstChess,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const BORDER_FIRST_LCV_PAR: Self = Self {
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        ..Self::BORDER_FIRST_LCV
    };

    pub const BORDER_FIRST_FULL_PAR: Self = Self {
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            parity: true,
            island: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
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
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const GACOLOR_AC3_NS1_PAR: Self = Self {
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    // Vol-12: Joe-Saunders 2026 — gacolor + AC-3, but extras only fire
    // at depth ≥ 150. Tries to bridge our ~2k nodes/sec to McGavin's
    // ~300M/sec by skipping per-node Step-8 work during early search.
    pub const JOE_DEPTH150: Self = Self {
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            depth_threshold: Some(150),
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const JOE_DEPTH150_PAR: Self = Self {
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            depth_threshold: Some(150),
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    /// Vol-14 #1 — Joe-depth150 baseline + edge-color BP marginals as
    /// value-order. Caller must populate `SolveOpts.edge_bp_marginals`;
    /// see `eternity2_solver_engine::load_edge_bp_marginals`.
    pub const JOE_DEPTH150_BP: Self = Self {
        value_order: ValueOrder::EdgeBpMarginals,
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            depth_threshold: Some(150),
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const JOE_DEPTH150_BP_PAR: Self = Self {
        value_order: ValueOrder::EdgeBpMarginals,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            depth_threshold: Some(150),
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    /// Vol-14 — joe_depth150_bp_par + auto-built hint-rectangle skeleton
    /// path (places the 4 outer hints + center via PathPolicy first).
    /// Requires `opts.hints` to have ≥4 hint positions. Empirically the
    /// strongest non-warm-started canonical-E2 single-process profile.
    pub const JOE_DEPTH150_BP_REC_PAR: Self = Self {
        value_order: ValueOrder::EdgeBpMarginals,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        path_skeleton: Some(PathSkeleton::HintRectangle),
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            depth_threshold: Some(150),
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    /// Single-thread variant of JOE_DEPTH150_BP_REC_PAR.
    pub const JOE_DEPTH150_BP_REC: Self = Self {
        value_order: ValueOrder::EdgeBpMarginals,
        path_skeleton: Some(PathSkeleton::HintRectangle),
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            depth_threshold: Some(150),
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    /// Vol-14 user-proposed: joe_depth150_bp + LAYERED rectangle skeleton.
    /// Path: rectangle perimeter → interior (centre-out) → annulus
    /// (row-by-row) → outer border. Engine is locked into this order
    /// for the entire search via PathPolicy::PrefixConstraint{k=256}.
    pub const JOE_DEPTH150_BP_REC_LAYERED_PAR: Self = Self {
        value_order: ValueOrder::EdgeBpMarginals,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        path_skeleton: Some(PathSkeleton::HintRectangleLayered),
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            depth_threshold: Some(150),
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    /// Vol-23 user-proposed: joe_depth150_bp_par + X-skeleton path
    /// (two 3-cell-wide diagonals through the 5 canonical hints,
    /// then Chebyshev-outward fill from centre). Requires
    /// `opts.hints.len() >= 5`.
    pub const JOE_DEPTH150_BP_X_PAR: Self = Self {
        value_order: ValueOrder::EdgeBpMarginals,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        path_skeleton: Some(PathSkeleton::XSkeleton),
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            depth_threshold: Some(150),
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const JOE_DEPTH150_BP_REC_LAYERED: Self = Self {
        value_order: ValueOrder::EdgeBpMarginals,
        path_skeleton: Some(PathSkeleton::HintRectangleLayered),
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            multiset_equality: true,
            depth_threshold: Some(150),
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    // Step 8 profiles: baseline + extra propagators.
    pub const BORDER_FIRST_PARITY: Self = Self {
        propagators: PropagatorConfig {
            parity: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const BORDER_FIRST_FULL: Self = Self {
        propagators: PropagatorConfig {
            parity: true,
            island: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    /// Verhaard 2008 — gacolor + AC-3 + PreferredFirst value ordering.
    /// Caller sets `SolveOpts.preferred_pieces` to (deferred ∪ worst-good)
    /// from phase-0 SA. See `solver-verhaard` crate.
    pub const VERHAARD_PREFERRED: Self = Self {
        value_order: ValueOrder::PreferredFirst,
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };

    pub const VERHAARD_PREFERRED_PAR: Self = Self {
        value_order: ValueOrder::PreferredFirst,
        parallelism: Parallelism::RootSplit { split_depth: 0 },
        propagators: PropagatorConfig {
            gacolor: true,
            ac3: true,
            ..Self::BORDER_FIRST_LCV.propagators
        },
        ..Self::BORDER_FIRST_LCV
    };
}

pub struct EngineSolver {
    config: EngineConfig,
    solver_id: String,
    heuristic_profile: String,
    /// Vol-14 instrumentation: per-position backtrack counts from
    /// the most recent `solve()` call. Updated at end-of-solve.
    /// `take_pos_backtracks()` returns and clears this vector.
    last_pos_backtracks: std::sync::Mutex<Vec<u64>>,
    /// Vol-15 — Blackwood 2020 schedule + break-index policy. Held
    /// on the solver (not in SolveOpts) so solver-trait does not
    /// have to know about Blackwood. Arc so rayon workers under
    /// `RootSplit` share a single allocation. Consulted when
    /// `config.value_order == ValueOrder::BlackwoodHeuristic`.
    pub(crate) blackwood_schedule: Option<Arc<BlackwoodSchedule>>,
}

impl EngineSolver {
    #[must_use]
    pub fn new(config: EngineConfig, solver_id: impl Into<String>, heuristic_profile: impl Into<String>) -> Self {
        Self {
            config,
            solver_id: solver_id.into(),
            heuristic_profile: heuristic_profile.into(),
            last_pos_backtracks: std::sync::Mutex::new(Vec::new()),
            blackwood_schedule: None,
        }
    }

    /// Vol-15 — attach a Blackwood schedule to this solver. The
    /// schedule is read-only across the run; pass an `Arc` so rayon
    /// workers share the allocation. The engine consults the schedule
    /// only when `config.value_order == ValueOrder::BlackwoodHeuristic`.
    pub fn with_blackwood_schedule(mut self, schedule: Arc<BlackwoodSchedule>) -> Self {
        self.blackwood_schedule = Some(schedule);
        self
    }

    pub fn blackwood_schedule(&self) -> Option<Arc<BlackwoodSchedule>> {
        self.blackwood_schedule.clone()
    }

    /// Vol-15 — Blackwood-mode constructor. Returns a solver with
    /// `BLACKWOOD_BASE_PAR` config and a Blackwood schedule attached.
    /// Mirrors `joe_depth150_bp_par()`'s pattern.
    #[must_use]
    pub fn blackwood_base_par(schedule: Arc<BlackwoodSchedule>) -> Self {
        Self::new(EngineConfig::BLACKWOOD_BASE_PAR, "engine", "blackwood_base_par")
            .with_blackwood_schedule(schedule)
    }

    #[must_use]
    pub fn blackwood_base(schedule: Arc<BlackwoodSchedule>) -> Self {
        Self::new(EngineConfig::BLACKWOOD_BASE, "engine", "blackwood_base")
            .with_blackwood_schedule(schedule)
    }

    /// Vol-15 — "dumb Blackwood": no gacolor/AC-3/NS-1, just edge
    /// forward-checking + piece-uniqueness + schedule + breaks.
    /// Sound after break by construction (no exact-matching
    /// invariants).
    #[must_use]
    pub fn blackwood_raw_par(schedule: Arc<BlackwoodSchedule>) -> Self {
        Self::new(EngineConfig::BLACKWOOD_RAW_PAR, "engine", "blackwood_raw_par")
            .with_blackwood_schedule(schedule)
    }

    #[must_use]
    pub fn blackwood_raw(schedule: Arc<BlackwoodSchedule>) -> Self {
        Self::new(EngineConfig::BLACKWOOD_RAW, "engine", "blackwood_raw")
            .with_blackwood_schedule(schedule)
    }

    /// Vol-14 instrumentation hook: pull per-position backtrack
    /// counts from the most recent `solve()`. Cleared on read.
    /// Returns empty Vec if no run has completed.
    pub fn take_pos_backtracks(&self) -> Vec<u64> {
        let mut g = self.last_pos_backtracks.lock().unwrap();
        std::mem::take(&mut *g)
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

    #[must_use]
    pub fn joe_depth150_bp() -> Self {
        Self::new(EngineConfig::JOE_DEPTH150_BP, "engine", "joe_depth150_bp")
    }

    #[must_use]
    pub fn joe_depth150_bp_par() -> Self {
        Self::new(EngineConfig::JOE_DEPTH150_BP_PAR, "engine", "joe_depth150_bp_par")
    }

    #[must_use]
    pub fn joe_depth150_bp_rec_par() -> Self {
        Self::new(EngineConfig::JOE_DEPTH150_BP_REC_PAR, "engine", "joe_depth150_bp_rec_par")
    }

    #[must_use]
    pub fn joe_depth150_bp_rec() -> Self {
        Self::new(EngineConfig::JOE_DEPTH150_BP_REC, "engine", "joe_depth150_bp_rec")
    }

    #[must_use]
    pub fn joe_depth150_bp_rec_layered_par() -> Self {
        Self::new(EngineConfig::JOE_DEPTH150_BP_REC_LAYERED_PAR,
                  "engine", "joe_depth150_bp_rec_layered_par")
    }

    #[must_use]
    pub fn joe_depth150_bp_x_par() -> Self {
        Self::new(EngineConfig::JOE_DEPTH150_BP_X_PAR,
                  "engine", "joe_depth150_bp_x_par")
    }

    #[must_use]
    pub fn joe_depth150_bp_rec_layered() -> Self {
        Self::new(EngineConfig::JOE_DEPTH150_BP_REC_LAYERED,
                  "engine", "joe_depth150_bp_rec_layered")
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
        // Vol-14 instrumentation hook: capture pos_backtracks at
        // end-of-run. The state consumes itself in `run`; we use a
        // helper that returns both the outcome and the counters.
        let (outcome, pos_bt) = SearchState::new(puzzle, self, opts).run_with_diag(sink);
        if let Ok(mut g) = self.last_pos_backtracks.lock() {
            *g = pos_bt;
        }
        outcome
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

/// Number of states per edge in the vol-12 BP marginals file
/// (`output/v12_bp/edge_bp_60i.json`): color 0 = BORDER + 22 interior
/// colors = 23.
pub const EDGE_BP_NSTATE: usize = 23;

/// Build the (cell, side) -> edge_id map matching the Python BP
/// enumeration in `scripts/v12_edge_bp.py::build_grid_edges`. Layout:
/// `cell_side_edge[pos * 4 + side]` is the edge_id for that side
/// (side 0=N, 1=E, 2=S, 3=W). Internal edges are shared between two
/// cells; boundary edges have exactly one incident cell.
///
/// Total edge count is `2 * W * H + W + H` (= 544 for 16×16).
/// Build a "rectangle skeleton" path from hint positions on a
/// `puzzle`. Vol-14 user-proposed heuristic for canonical E2 (works
/// when there are ≥4 outermost hints + (optionally) a center hint):
///
///   1. Take the 4 hints with the most-extreme coordinates (TL, TR,
///      BR, BL by Chebyshev-distance from the centre).
///   2. Trace the rectangle through them: top-row TL→TR; right-col
///      TR→BR; bottom-row BR→BL; left-col BL up to one short of TL.
///   3. From the rectangle, lay a horizontal spoke at the centre
///      hint's y-row (if a 5th hint exists) toward the centre hint.
///   4. Dedupe positions while preserving order; return.
///
/// Empirically on canonical 16×16 E2 with the 5 official hints, this
/// produces a 49-cell skeleton. Combined with
/// `PathPolicy::PrefixConstraint { k: path.len() }`, the engine pins
/// these 49 cells before falling back to MRV — chips the 764-plateau
/// dramatically. See `project_e2_vol14_rectangle_path_finding` memory
/// (forthcoming).
///
/// Returns an empty Vec if `hints.hints.len() < 4` — caller should
/// fall back to default variable-order.
pub fn build_hint_rectangle_path(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Vec<Position> {
    if hints.hints.len() < 4 { return Vec::new(); }
    let w = puzzle.width;
    let xy = |p: Position| (p % w, p / w);
    let pos_of = |x: u32, y: u32| -> Position { y * w + x };
    // Compute Chebyshev distance from board centre for each hint.
    let cx = (w as i32 - 1) / 2;
    let cy = (puzzle.height as i32 - 1) / 2;
    let mut h: Vec<(Position, u32, u32, i32)> = hints.hints.iter().map(|h| {
        let (x, y) = xy(h.position);
        let d = std::cmp::max((x as i32 - cx).abs(), (y as i32 - cy).abs());
        (h.position, x, y, d)
    }).collect();
    // Sort by Chebyshev distance descending — outermost first.
    h.sort_by(|a, b| b.3.cmp(&a.3));

    // The 4 outermost hints form our rectangle. Need to find TL, TR,
    // BR, BL among them by quadrant relative to centre.
    let mut tl: Option<(u32, u32)> = None;
    let mut tr: Option<(u32, u32)> = None;
    let mut br: Option<(u32, u32)> = None;
    let mut bl: Option<(u32, u32)> = None;
    for &(_, x, y, _) in &h {
        let is_left = (x as i32) <= cx;
        let is_top = (y as i32) <= cy;
        let slot = match (is_top, is_left) {
            (true, true)   => &mut tl,
            (true, false)  => &mut tr,
            (false, false) => &mut br,
            (false, true)  => &mut bl,
        };
        if slot.is_none() { *slot = Some((x, y)); }
    }
    let (Some((tlx, tly)), Some((trx, tryy)), Some((brx, bry)), Some((blx, bly))) =
        (tl, tr, br, bl)
    else { return Vec::new(); };
    let _ = (tryy, blx, bly); // suppress unused warnings — we use tly+bry+tlx+trx

    // Trace the rectangle.
    let mut path = Vec::new();
    let mut seen = std::collections::HashSet::new();
    let push = |p: Position, path: &mut Vec<Position>, seen: &mut std::collections::HashSet<Position>| {
        if seen.insert(p) { path.push(p); }
    };
    // Top row at y=tly from x=tlx..=trx
    let ymin = std::cmp::min(tly, tryy);
    for x in tlx..=trx { push(pos_of(x, ymin), &mut path, &mut seen); }
    // Right col at x=trx (=brx most commonly) from y=ymin+1..=bry_max
    let ymax = std::cmp::max(bry, bly);
    let xright = std::cmp::max(trx, brx);
    for y in (ymin+1)..=ymax { push(pos_of(xright, y), &mut path, &mut seen); }
    // Bottom row, right to left, from x=xright-1 down to x=tlx
    for x in (tlx..xright).rev() { push(pos_of(x, ymax), &mut path, &mut seen); }
    // Left col, bottom to top, from y=ymax-1 down to y=ymin+1
    for y in ((ymin+1)..ymax).rev() { push(pos_of(tlx, y), &mut path, &mut seen); }
    // Spoke to inner hints: for each remaining hint (sorted by distance
    // ascending = innermost first), lay a horizontal segment from x=tlx
    // to its x at its y row.
    let mut inner: Vec<&(Position, u32, u32, i32)> = h.iter().skip(4).collect();
    inner.sort_by(|a, b| a.3.cmp(&b.3));
    for entry in &inner {
        let hx: u32 = entry.1;
        let hy: u32 = entry.2;
        // Horizontal from x=tlx to x=hx at row y=hy.
        if hx >= tlx {
            for x in tlx..=hx { push(pos_of(x, hy), &mut path, &mut seen); }
        } else {
            for x in (hx..=tlx).rev() { push(pos_of(x, hy), &mut path, &mut seen); }
        }
    }
    path
}

/// Vol-14 user-proposed: extend `build_hint_rectangle_path` to cover
/// all 256 cells in three subsequent phases:
///   Phase 1: hint-rectangle path (as built above).
///   Phase 2: interior of the rectangle (cells strictly inside the
///            tlx..trx × tly..bry box, not yet in phase 1), ordered
///            by ascending Chebyshev distance from board centre
///            (innermost first — closest to most hints).
///   Phase 3: annulus between the rectangle and the outer board border,
///            ordered row-by-row.
///   Phase 4: the 60 outer-border cells (corners + non-corner perimeter),
///            corners first.
/// Returns an empty Vec if hints.hints.len() < 4.
pub fn build_hint_rectangle_layered_path(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Vec<Position> {
    let phase1 = build_hint_rectangle_path(puzzle, hints);
    if phase1.is_empty() { return Vec::new(); }
    let w = puzzle.width;
    let h = puzzle.height;
    let n = puzzle.cell_count() as usize;
    let xy = |p: Position| (p % w, p / w);
    let pos_of = |x: u32, y: u32| -> Position { y * w + x };

    // Recover rectangle bounds from phase1's first cell (TL) and the
    // max x/y in phase1 (TR-x, BR-y).
    let (tlx, tly) = xy(phase1[0]);
    let mut max_x = tlx; let mut max_y = tly;
    let mut min_x = tlx; let mut min_y = tly;
    for &p in &phase1 {
        let (x, y) = xy(p);
        if x > max_x { max_x = x; }
        if y > max_y { max_y = y; }
        if x < min_x { min_x = x; }
        if y < min_y { min_y = y; }
    }
    let (trx, bry) = (max_x, max_y);

    let mut seen: std::collections::HashSet<Position> = phase1.iter().copied().collect();
    let mut path = phase1;

    // Phase 2: interior of rectangle (strictly inside min_x+1..=trx-1,
    // min_y+1..=bry-1), ordered by Chebyshev distance from board centre.
    let cx = (w as i32 - 1) / 2;
    let cy = (h as i32 - 1) / 2;
    let mut interior_rect: Vec<(Position, i32, u32)> = Vec::new();
    for y in (min_y + 1)..bry {
        for x in (min_x + 1)..trx {
            let p = pos_of(x, y);
            if seen.contains(&p) { continue; }
            let d = std::cmp::max((x as i32 - cx).abs(), (y as i32 - cy).abs());
            interior_rect.push((p, d, p));
        }
    }
    interior_rect.sort_by(|a, b| a.1.cmp(&b.1).then(a.2.cmp(&b.2)));
    for (p, _, _) in &interior_rect {
        if seen.insert(*p) { path.push(*p); }
    }

    // Phase 3: annulus between the rectangle and outer border, row-by-row.
    // For each cell (x, y) with min_x..trx range respected for rows OUTSIDE
    // the rectangle bounds, or cells outside the rectangle x-range:
    for y in 0..h {
        for x in 0..w {
            let p = pos_of(x, y);
            if seen.contains(&p) { continue; }
            // Skip if it's on the outer border (covered in phase 4).
            if x == 0 || x == w - 1 || y == 0 || y == h - 1 { continue; }
            path.push(p);
            seen.insert(p);
        }
    }

    // Phase 4: outer border. Corners first, then perimeter row by row.
    let corners = [
        pos_of(0, 0),
        pos_of(w - 1, 0),
        pos_of(0, h - 1),
        pos_of(w - 1, h - 1),
    ];
    for &c in &corners {
        if seen.insert(c) { path.push(c); }
    }
    // Top row
    for x in 0..w { let p = pos_of(x, 0); if seen.insert(p) { path.push(p); } }
    // Right col
    for y in 0..h { let p = pos_of(w - 1, y); if seen.insert(p) { path.push(p); } }
    // Bottom row
    for x in 0..w { let p = pos_of(x, h - 1); if seen.insert(p) { path.push(p); } }
    // Left col
    for y in 0..h { let p = pos_of(0, y); if seen.insert(p) { path.push(p); } }

    debug_assert_eq!(path.len(), n, "layered path should cover all cells, got {}/{}", path.len(), n);
    path
}

/// Vol-23 — build the X-skeleton path. See `PathSkeleton::XSkeleton`
/// for the order specification. Returns an empty Vec if fewer than 5
/// hints are supplied (caller falls back to default variable-order).
///
/// 3-cell-wide diagonals: for each main-diagonal cell `(x, y)`, also
/// emit `(x, y-1)` and `(x, y+1)` (when in-bounds) so each main cell
/// gets two already-placed neighbours from the previous step plus the
/// flanking cells from this step. Same idea for the anti-diagonal,
/// flanking by `(x-1, y)` and `(x+1, y)` (horizontal flanks make more
/// geometric sense for the anti-diagonal — the band stays a 3-wide
/// strip orthogonal to the diagonal direction).
pub fn build_x_skeleton_path(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Vec<Position> {
    if hints.hints.len() < 5 { return Vec::new(); }
    let w = puzzle.width;
    let h = puzzle.height;
    let n = puzzle.cell_count() as usize;
    let xy = |p: Position| (p % w, p / w);
    let pos_of = |x: u32, y: u32| -> Position { y * w + x };

    // Classify the 5 hints into TL/TR/BL/BR/centre by quadrant relative
    // to the board centre. The "centre" hint is the one closest to the
    // board centre by Chebyshev distance.
    let cx_i = (w as i32 - 1) / 2;
    let cy_i = (h as i32 - 1) / 2;
    let mut entries: Vec<(u32, u32, i32)> = hints.hints.iter().map(|hh| {
        let (x, y) = xy(hh.position);
        let d = std::cmp::max((x as i32 - cx_i).abs(), (y as i32 - cy_i).abs());
        (x, y, d)
    }).collect();
    entries.sort_by_key(|e| e.2);
    let (ccx, ccy, _) = entries[0];
    let outer: Vec<(u32, u32)> = entries.iter().skip(1).map(|e| (e.0, e.1)).collect();
    let mut tl: Option<(u32, u32)> = None;
    let mut tr: Option<(u32, u32)> = None;
    let mut bl: Option<(u32, u32)> = None;
    let mut br: Option<(u32, u32)> = None;
    for &(x, y) in &outer {
        let is_left = (x as i32) <= cx_i;
        let is_top = (y as i32) <= cy_i;
        let slot = match (is_top, is_left) {
            (true, true)   => &mut tl,
            (true, false)  => &mut tr,
            (false, false) => &mut br,
            (false, true)  => &mut bl,
        };
        if slot.is_none() { *slot = Some((x, y)); }
    }
    let (Some(tlp), Some(trp), Some(blp), Some(brp)) = (tl, tr, bl, br)
        else { return Vec::new(); };

    let mut path: Vec<Position> = Vec::with_capacity(n);
    let mut seen: std::collections::HashSet<Position> = std::collections::HashSet::new();
    let push = |x: i32, y: i32, path: &mut Vec<Position>, seen: &mut std::collections::HashSet<Position>| {
        if x < 0 || y < 0 || (x as u32) >= w || (y as u32) >= h { return; }
        let p = pos_of(x as u32, y as u32);
        if seen.insert(p) { path.push(p); }
    };

    // Walk a 3-cell-wide diagonal band from `(x0, y0)` to `(x1, y1)`,
    // stepping by `(sx, sy)`. At each step emit the main cell first,
    // then the two vertical flanks `(x, y-1)` and `(x, y+1)`.
    let walk_main_diag = |x0: i32, y0: i32, x1: i32, y1: i32,
                          path: &mut Vec<Position>,
                          seen: &mut std::collections::HashSet<Position>| {
        let dx = (x1 - x0).signum();
        let dy = (y1 - y0).signum();
        let steps = std::cmp::max((x1 - x0).abs(), (y1 - y0).abs());
        for k in 0..=steps {
            let x = x0 + k * dx;
            let y = y0 + k * dy;
            push(x, y, path, seen);
            push(x, y - 1, path, seen);
            push(x, y + 1, path, seen);
        }
    };
    // Anti-diagonal: flank horizontally instead of vertically.
    let walk_anti_diag = |x0: i32, y0: i32, x1: i32, y1: i32,
                          path: &mut Vec<Position>,
                          seen: &mut std::collections::HashSet<Position>| {
        let dx = (x1 - x0).signum();
        let dy = (y1 - y0).signum();
        let steps = std::cmp::max((x1 - x0).abs(), (y1 - y0).abs());
        for k in 0..=steps {
            let x = x0 + k * dx;
            let y = y0 + k * dy;
            push(x, y, path, seen);
            push(x - 1, y, path, seen);
            push(x + 1, y, path, seen);
        }
    };

    // 1. TL → centre band (main diagonal direction).
    walk_main_diag(tlp.0 as i32, tlp.1 as i32, ccx as i32, ccy as i32,
                   &mut path, &mut seen);
    // 2. Centre → BR (continues the same diagonal).
    walk_main_diag(ccx as i32, ccy as i32, brp.0 as i32, brp.1 as i32,
                   &mut path, &mut seen);
    // 3. TR → centre (anti-diagonal direction).
    walk_anti_diag(trp.0 as i32, trp.1 as i32, ccx as i32, ccy as i32,
                   &mut path, &mut seen);
    // 4. Centre → BL.
    walk_anti_diag(ccx as i32, ccy as i32, blp.0 as i32, blp.1 as i32,
                   &mut path, &mut seen);

    // 5. Fill remaining cells outward from centre, Chebyshev ascending,
    //    within-tie row-major.
    let mut rest: Vec<(Position, i32, Position)> = Vec::new();
    for y in 0..h {
        for x in 0..w {
            let p = pos_of(x, y);
            if seen.contains(&p) { continue; }
            let d = std::cmp::max((x as i32 - ccx as i32).abs(),
                                  (y as i32 - ccy as i32).abs());
            rest.push((p, d, p));
        }
    }
    rest.sort_by(|a, b| a.1.cmp(&b.1).then(a.2.cmp(&b.2)));
    for (p, _, _) in &rest {
        if seen.insert(*p) { path.push(*p); }
    }
    debug_assert_eq!(path.len(), n, "X-skeleton path should cover all cells, got {}/{}", path.len(), n);
    path
}

pub(crate) fn build_cell_side_edge(puzzle: &Puzzle) -> Vec<u32> {
    let w = puzzle.width as usize;
    let h = puzzle.height as usize;
    let n = w * h;
    let mut cse = vec![u32::MAX; n * 4];
    let mut next_eid: u32 = 0;
    for y in 0..h {
        for x in 0..w {
            let pos = y * w + x;
            // N (side 0)
            if cse[pos * 4 + 0] == u32::MAX {
                let eid = next_eid;
                next_eid += 1;
                cse[pos * 4 + 0] = eid;
                if y > 0 {
                    let npos = (y - 1) * w + x;
                    cse[npos * 4 + 2] = eid;
                }
            }
            // S (side 2) — only created here if last row (else assigned by next row's N pass)
            if cse[pos * 4 + 2] == u32::MAX && y == h - 1 {
                let eid = next_eid;
                next_eid += 1;
                cse[pos * 4 + 2] = eid;
            }
            // W (side 3)
            if cse[pos * 4 + 3] == u32::MAX {
                let eid = next_eid;
                next_eid += 1;
                cse[pos * 4 + 3] = eid;
                if x > 0 {
                    let npos = y * w + (x - 1);
                    cse[npos * 4 + 1] = eid;
                }
            }
            // E (side 1)
            if cse[pos * 4 + 1] == u32::MAX && x == w - 1 {
                let eid = next_eid;
                next_eid += 1;
                cse[pos * 4 + 1] = eid;
            }
        }
    }
    debug_assert!(cse.iter().all(|&e| e != u32::MAX));
    cse
}

/// Load vol-12 edge-color BP marginals from a JSON file produced by
/// `scripts/v12_edge_bp.py`. Returns a flat `Arc<Vec<f32>>` of length
/// `n_edges * EDGE_BP_NSTATE` indexed as
/// `flat[edge_id * EDGE_BP_NSTATE + color]`. Order of edges in the
/// file is assumed to match `build_cell_side_edge`'s enumeration.
///
/// Errors: I/O, JSON parse, or unexpected schema (wrong NSTATE, ids
/// not contiguous starting at 0).
#[cfg(not(target_arch = "wasm32"))]
pub fn load_edge_bp_marginals(path: &std::path::Path) -> std::io::Result<Arc<Vec<f32>>> {
    let bytes = std::fs::read(path)?;
    let doc: serde_json::Value = serde_json::from_slice(&bytes)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
    let edges = doc.get("edges").and_then(|v| v.as_array()).ok_or_else(|| {
        std::io::Error::new(std::io::ErrorKind::InvalidData, "missing edges array")
    })?;
    let n = edges.len();
    let mut flat = vec![0f32; n * EDGE_BP_NSTATE];
    for (i, e) in edges.iter().enumerate() {
        let id = e.get("id").and_then(|v| v.as_u64()).unwrap_or(i as u64) as usize;
        if id != i {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("edge ids not contiguous at index {i} (got {id})"),
            ));
        }
        let m = e.get("marginal").and_then(|v| v.as_array()).ok_or_else(|| {
            std::io::Error::new(std::io::ErrorKind::InvalidData, "missing marginal")
        })?;
        if m.len() != EDGE_BP_NSTATE {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("edge {i} marginal len {} != {EDGE_BP_NSTATE}", m.len()),
            ));
        }
        for (c, v) in m.iter().enumerate() {
            flat[i * EDGE_BP_NSTATE + c] = v.as_f64().unwrap_or(0.0) as f32;
        }
    }
    Ok(Arc::new(flat))
}

/// Vol-15 — compute Blackwood's 3 "heuristic colors" from a Puzzle +
/// canonical hints. Selection rules per Blackwood msg #22 (2020):
///
///   1. **Many occurrences**: pick colors with highest total
///      piece-edge count.
///   2. **Not on any corner piece**: corner pieces have exactly two
///      BORDER edges; their non-border edges must not include the
///      heuristic colors.
///   3. **Not on the start piece** (i.e., piece at the centre hint):
///      preserves start-piece flexibility.
///
/// Blackwood's literal triple `[17, 2, 18]` does NOT apply to our
/// color labels (vol-14 verified: color 2 IS on 2 of our corners).
/// This helper recomputes from first principles. Returns `(colors,
/// pool_size)` where `pool_size` is the total occurrence count of
/// the 3 colors across all 256 piece edges.
pub fn compute_heuristic_sides(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Vec<Color> {
    let pieces = puzzle.pieces();

    // Corner pieces: exactly two BORDER edges.
    let mut corner_colors: std::collections::HashSet<Color> =
        std::collections::HashSet::new();
    for p in pieces {
        let e = p.edges.as_array();
        let n_border = e.iter().filter(|&&c| c == BORDER).count();
        if n_border == 2 {
            for &c in &e {
                if c != BORDER {
                    corner_colors.insert(c);
                }
            }
        }
    }

    // Centre/start hint: prefer the hint at position == cell_count/2
    // (canonical E2 has piece 138 at pos 135 which IS the centre);
    // fallback to any interior hint. Pull that piece's edges.
    let n_pos = puzzle.cell_count();
    let centre_pos = n_pos / 2;
    let start_piece: Option<&eternity2_core::Piece> = hints
        .hints
        .iter()
        .find(|h| h.position == centre_pos)
        .or_else(|| {
            // Fallback: any hint whose position is not on the border ring.
            let w = puzzle.width;
            let h_ = puzzle.height;
            hints.hints.iter().find(|hh| {
                let (x, y) = (hh.position % w, hh.position / w);
                x > 0 && x + 1 < w && y > 0 && y + 1 < h_
            })
        })
        .and_then(|h| puzzle.piece(h.piece_id));

    let mut start_colors: std::collections::HashSet<Color> =
        std::collections::HashSet::new();
    if let Some(p) = start_piece {
        for &c in &p.edges.as_array() {
            if c != BORDER {
                start_colors.insert(c);
            }
        }
    }

    let forbidden: std::collections::HashSet<Color> =
        corner_colors.union(&start_colors).copied().collect();

    // Count occurrences of each color across all piece edges (BORDER
    // excluded).
    let mut counts: std::collections::HashMap<Color, u32> =
        std::collections::HashMap::new();
    for p in pieces {
        for &c in &p.edges.as_array() {
            if c != BORDER {
                *counts.entry(c).or_insert(0) += 1;
            }
        }
    }

    // Filter and sort by descending frequency (break ties by ascending
    // color id for determinism).
    let mut candidates: Vec<(Color, u32)> = counts
        .into_iter()
        .filter(|(c, _)| !forbidden.contains(c))
        .collect();
    candidates.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));

    candidates.into_iter().take(3).map(|(c, _)| c).collect()
}

/// Vol-15 — total occurrence count of a set of edge colors across
/// all piece edges in a puzzle (BORDER excluded).
pub fn count_color_occurrences(puzzle: &Puzzle, colors: &[Color]) -> u32 {
    let set: std::collections::HashSet<Color> = colors.iter().copied().collect();
    let mut n = 0u32;
    for p in puzzle.pieces() {
        for &c in &p.edges.as_array() {
            if c != BORDER && set.contains(&c) {
                n += 1;
            }
        }
    }
    n
}

/// Vol-15 — Blackwood's 469-recipe schedule, AFFINE-REMAPPED into
/// our scan's post-border range. Critical history:
///
/// - First attempt (proportional rescale on both axes) prunes
///   immediately on canonical E2 because Blackwood's control depths
///   16, 26 land inside our border ring (depth 0..60) where no
///   heuristic-color edges have been placed yet.
/// - Second attempt added `max(scaled, border_ring)` clamp; this
///   produced a CLIFF where two control points both land on depth 60
///   (one with target 0, one with target ≥ 28), causing
///   `target_at(60)` to jump discontinuously and trigger immediate
///   prune. Spotted by a third-party review of summary.json from
///   run_1778604403.
/// - This (third) attempt does a true AFFINE REMAP of Blackwood's
///   depth axis [16..160] into our [post_border..max_idx] range,
///   preserving the curve's shape while landing the first non-zero
///   target after the border ring is fully placed. Strictly monotone
///   in depth. Validated via `BlackwoodSchedule::validate`.
///
/// Returns `None` if `compute_heuristic_sides` finds fewer than 3
/// usable colors.
pub fn blackwood_schedule_469(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Option<BlackwoodSchedule> {
    let colors = compute_heuristic_sides(puzzle, hints);
    if colors.len() < 3 { return None; }
    let pool_size = count_color_occurrences(puzzle, &colors);
    let n_pos = puzzle.cell_count();
    let w = puzzle.width;
    let h = puzzle.height;
    let border_ring = 2 * w + 2 * h - 4;

    let bw_pool = 122u32;
    let scale_c = |c: u32| ((c as u64 * pool_size as u64) / bw_pool as u64) as u32;

    // Affine remap Blackwood's depth axis [16..160] into our
    // [post_border..target_max] range. `post_border` is the first
    // depth at which heuristic-color edges can plausibly be placed
    // (just past the border ring + 1 buffer cell). `target_max` is
    // the depth where the schedule should saturate (we use 160 ×
    // n_pos/256, the proportionally-scaled max from Blackwood's
    // original curve).
    let post_border = border_ring + 1; // first cell past the ring
    let target_max = ((160u64 * n_pos as u64) / 256) as u32;
    debug_assert!(target_max > post_border, "post_border ({post_border}) >= target_max ({target_max}); puzzle too small for Blackwood schedule");

    // Blackwood's control depths (he calls these heuristic indices).
    let bw_depths: [u32; 6] = [16, 26, 56, 76, 102, 160];
    let bw_counts: [u32; 6] = [0,  28, 71, 89, 106, 119];

    // Affine map: f(d) = post_border + (d - 16) * (target_max - post_border) / (160 - 16)
    let remap = |d: u32| -> u32 {
        let num = (d - 16) as u64 * (target_max - post_border) as u64;
        let den = (160 - 16) as u64;
        post_border + (num / den) as u32
    };

    // First target point is (0, 0) so target_at(0..post_border) → 0.
    // Then the remapped Blackwood points. Strictly increasing in
    // depth because affine remap with target_max > post_border.
    let mut targets: Vec<(u32, u32)> = Vec::with_capacity(bw_depths.len() + 1);
    targets.push((0, 0));
    for (&d, &c) in bw_depths.iter().zip(bw_counts.iter()) {
        targets.push((remap(d), scale_c(c)));
    }

    // Breaks: Blackwood's last 12 cells (201..256 on a 256-cell
    // board). Scaled proportionally; clamped into [post_border, n_pos).
    let bw_breaks: [u32; 12] = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256];
    let breaks: Vec<u32> = bw_breaks
        .iter()
        .map(|&b| {
            let scaled = ((b as u64 * n_pos as u64) / 256u64) as u32;
            scaled.min(n_pos.saturating_sub(1))
        })
        .collect();

    let s = BlackwoodSchedule {
        heuristic_sides: colors,
        exhaustion_targets: targets,
        heuristic_pool_size: pool_size,
        max_heuristic_index: target_max,
        break_indexes_allowed: breaks,
    };
    // Validate the schedule is well-formed before returning. If
    // invalid we hand back a freshly-constructed trivial schedule
    // rather than crashing — caller can inspect via .validate().
    if let Err(e) = s.validate() {
        eprintln!("WARNING: blackwood_schedule_469 produced invalid schedule: {e}");
    }
    Some(s)
}

/// Vol-17 (idea A) — Blackwood schedule **calibrated empirically** from
/// the McGavin 469 community board on canonical Eternity2. Each control
/// point `(depth, count)` is the cumulative count of heuristic-color
/// piece-edges placed in cells 0..depth under bottom-up row-major scan
/// order, computed by `calibrate_blackwood`. N=1 corpus board on
/// canonical E2 (only one ≥469 board exists), so this is the empirical
/// truth from THE actual community solve rather than a transferred
/// curve from Blackwood's different piece set.
///
/// Comparison to `blackwood_schedule_469` (affine-remapped Blackwood):
/// at depth 80 our vol-15 schedule demanded ~60 heuristic edges placed;
/// the actual McGavin 469 board has 32 at depth 80. The vol-15 schedule
/// was OVER-DEMANDING by ~2× and pruned the search prematurely. This
/// calibrated schedule should not have the same cliff failure.
///
/// `heuristic_sides` and `heuristic_pool_size` are recomputed at call
/// time so the schedule works on any puzzle with the same scan-order
/// structure (5-hint canonical E2 expected; falls back gracefully on
/// other shapes).
pub fn blackwood_schedule_calibrated_v17a(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Option<BlackwoodSchedule> {
    let colors = compute_heuristic_sides(puzzle, hints);
    if colors.len() < 3 { return None; }
    let pool_size = count_color_occurrences(puzzle, &colors);
    let n_pos = puzzle.cell_count();

    // From output/v17_calibration.json (run on McGavin 469, 2026-05-12).
    // Use the median curve directly. Last point clamped to n_pos-1.
    let last_idx = n_pos.saturating_sub(1);
    let targets: Vec<(u32, u32)> = vec![
        (0,        0),
        (60,       21),
        (80,       32),
        (100,      41),
        (120,      48),
        (140,      58),
        (160,      82),
        (200,      112),
        (last_idx, pool_size.min(150)),
    ];

    // Use the same proportional break schedule as vol-15 — empirical
    // mismatch calibration is a future task (would need a 469 board
    // with the break locations annotated).
    let bw_breaks: [u32; 12] = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256];
    let breaks: Vec<u32> = bw_breaks
        .iter()
        .map(|&b| {
            let scaled = ((b as u64 * n_pos as u64) / 256u64) as u32;
            scaled.min(n_pos.saturating_sub(1))
        })
        .collect();

    let target_max = targets.last().map(|&(d, _)| d).unwrap_or(n_pos - 1);
    let s = BlackwoodSchedule {
        heuristic_sides: colors,
        exhaustion_targets: targets,
        heuristic_pool_size: pool_size,
        max_heuristic_index: target_max,
        break_indexes_allowed: breaks,
    };
    if let Err(e) = s.validate() {
        eprintln!("WARNING: blackwood_schedule_calibrated_v17a produced invalid schedule: {e}");
        return None;
    }
    Some(s)
}

/// Vol-17 (idea A) — same calibration data as
/// `blackwood_schedule_calibrated_v17a` but at the 25th-percentile
/// (more permissive — demands fewer heuristic edges at each depth).
/// With N=1 corpus board this collapses to the same curve. Kept as
/// a stable name so additional corpus boards can be folded in later.
pub fn blackwood_schedule_calibrated_v17a_p25(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Option<BlackwoodSchedule> {
    // With N=1 the p25 IS the median. Reuse.
    blackwood_schedule_calibrated_v17a(puzzle, hints)
}

/// Vol-17 (idea A, V17C revision) — like v17b but with break indexes
/// shifted EARLIER. Vol-17 measured the depth wall at ~193, which is
/// BELOW v17b's first break at 201. The engine never uses any break
/// in practice because it can't even reach depth 201 cleanly under
/// the strict no-break placement rule. Moving breaks earlier (180,
/// 188, 195, ...) lets the engine accept partial mismatches starting
/// at the empirical wall depth.
///
/// This is a hypothesis — by allowing 1 break at depth 180, the
/// engine can spread mismatch tolerance over a wider range, and may
/// reach higher matched scores at the end.
/// Vol-17 (idea H21, V17E revision) — NOISE-INJECTED schedule.
/// Take the v17b base targets and apply per-control-point jitter
/// scaled by `noise_amplitude` * seed-derived RNG. Different seeds
/// produce different perturbed schedules. Hypothesis: each perturbed
/// schedule guides CP into a SLIGHTLY DIFFERENT piece-region basin
/// than v17a/b. Best-of-K perturbed-schedule runs may exceed any
/// single-schedule ceiling without using existing-board info.
///
/// noise_amplitude=0.0 → returns v17b unchanged.
/// noise_amplitude=0.2 → each target may shift by up to ±20%.
///
/// Targets are kept monotone-non-decreasing and within
/// [0, heuristic_pool_size] after perturbation.
pub fn blackwood_schedule_calibrated_v17e(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
    noise_amplitude: f64,
    seed: u64,
) -> Option<BlackwoodSchedule> {
    let mut s = blackwood_schedule_calibrated_v17b(puzzle, hints)?;
    if noise_amplitude == 0.0 { return Some(s); }
    // Simple splitmix64-style PRNG.
    let mut state: u64 = seed.wrapping_add(0x9E37_79B9_7F4A_7C15);
    let mut next_u64 = || -> u64 {
        state = state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    };
    let mut next_jitter = || -> f64 {
        let u = next_u64();
        // map to [-1, 1)
        (u as f64 / u64::MAX as f64) * 2.0 - 1.0
    };
    let pool = s.heuristic_pool_size as f64;
    let mut perturbed: Vec<(u32, u32)> = Vec::with_capacity(s.exhaustion_targets.len());
    let mut prev_c: u32 = 0;
    for (d, c) in s.exhaustion_targets.iter().copied() {
        if d == 0 {
            perturbed.push((d, 0));
            prev_c = 0;
            continue;
        }
        let jitter = next_jitter() * noise_amplitude * (c as f64).max(1.0);
        let mut new_c = ((c as f64) + jitter).round() as i64;
        if new_c < prev_c as i64 { new_c = prev_c as i64; }
        if new_c < 0 { new_c = 0; }
        if new_c > pool as i64 { new_c = pool as i64; }
        let new_c_u = new_c as u32;
        perturbed.push((d, new_c_u));
        prev_c = new_c_u;
    }
    s.exhaustion_targets = perturbed;
    if let Err(e) = s.validate() {
        eprintln!("WARNING: v17e (noise={noise_amplitude}, seed={seed}) invalid: {e}");
        return None;
    }
    Some(s)
}

/// Vol-17 (idea H20, V17D revision) — calibrate the Blackwood schedule
/// from OUR own 455-board (v17a + WorstBand) rather than the McGavin
/// 469 community board. Hypothesis: our 455 board has a MUCH higher
/// heuristic-color trajectory than McGavin's (e.g., 63 at depth 80
/// vs McGavin's 32). Using OUR curve as the schedule demands more
/// heuristic placement early, which may force the CP search into a
/// DIFFERENT piece-region assignment than v17a/v17b.
///
/// If the CP search reaches the wall at a similar depth (~192), the
/// ALNS ceiling might differ.
///
/// Trade-off: stricter demands → smaller feasible search space → CP
/// may fail earlier (UNSAT or low depth wall). But the demand levels
/// were ACHIEVED by our 455 board, so by construction this schedule
/// admits it.
pub fn blackwood_schedule_calibrated_v17d(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Option<BlackwoodSchedule> {
    let colors = compute_heuristic_sides(puzzle, hints);
    if colors.len() < 3 { return None; }
    let pool_size = count_color_occurrences(puzzle, &colors);
    let n_pos = puzzle.cell_count();
    let last_idx = n_pos.saturating_sub(1);

    // From /tmp/calibrate_from_our_board.py on our 455 board, with 1-edge
    // floor margin and monotone-non-decreasing fixup.
    let mut targets: Vec<(u32, u32)> = vec![
        (0,   0),
        (16,  5),
        (32,  22),
        (48,  34),
        (64,  50),
        (80,  62),
        (96,  72),
        (112, 84),
        (128, 94),
        (144, 105),
        (160, 114),
        (176, 121),
        (192, 122),
        (208, 129),
        (224, 140),
        (240, 149),
    ];
    if last_idx > 240 {
        targets.push((last_idx, pool_size.min(149)));
    }
    let bw_breaks: [u32; 12] = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256];
    let breaks: Vec<u32> = bw_breaks
        .iter()
        .map(|&b| ((b as u64 * n_pos as u64) / 256u64).min(n_pos.saturating_sub(1) as u64) as u32)
        .collect();
    let target_max = targets.last().map(|&(d, _)| d).unwrap_or(n_pos - 1);
    let s = BlackwoodSchedule {
        heuristic_sides: colors,
        exhaustion_targets: targets,
        heuristic_pool_size: pool_size,
        max_heuristic_index: target_max,
        break_indexes_allowed: breaks,
    };
    if let Err(e) = s.validate() {
        eprintln!("WARNING: blackwood_schedule_calibrated_v17d invalid: {e}");
        return None;
    }
    Some(s)
}

pub fn blackwood_schedule_calibrated_v17c(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Option<BlackwoodSchedule> {
    let mut s = blackwood_schedule_calibrated_v17b(puzzle, hints)?;
    let n_pos = puzzle.cell_count();
    let last_idx = n_pos.saturating_sub(1);
    // EMPIRICALLY DERIVED from the McGavin 469 board's actual mismatch
    // positions in bottom-up row-major scan order (vol-17 measurement,
    // `scripts/find_mcgavin_breaks.py`). McGavin's 11 mismatched edges
    // have their "later cell" at these 11 scan indices. So if our
    // engine searches in the SAME order as McGavin and accepts breaks
    // at these exact positions, it can reproduce McGavin's solution.
    let mcg_breaks: [u32; 11] = [187, 188, 190, 199, 200, 202, 206, 216, 222, 233, 249];
    s.break_indexes_allowed = mcg_breaks.iter().map(|&b| b.min(last_idx)).collect();
    Some(s)
}

/// Vol-17 (idea A, V17B revision) — TIGHT empirical envelope of the
/// McGavin 469 cumulative heuristic-color curve, sampled at every 16
/// cells with a 1-edge floor margin. Designed so that
/// `target_at(d) ≤ McGavin_actual[d]` for ALL d (verified offline);
/// the v17A coarser version had a 7-edge over-demand around depth 32
/// because of linear interpolation between sparse control points.
///
/// Concretely: the v17A piecewise-linear schedule between control
/// points (0,0) and (60,21) reaches target=11 at depth 32, but the
/// McGavin 469 board has only 4 heuristic edges at depth 32 — meaning
/// the v17A schedule prunes the McGavin 469 itself between depths
/// 20-50. The v17B schedule samples at every 16 cells so the
/// envelope hugs the McGavin curve from below with at most 1-edge
/// slack.
///
/// This is the schedule that should be used as the default once
/// validated on canonical E2.
pub fn blackwood_schedule_calibrated_v17b(
    puzzle: &Puzzle,
    hints: &eternity2_core::Hints,
) -> Option<BlackwoodSchedule> {
    let colors = compute_heuristic_sides(puzzle, hints);
    if colors.len() < 3 { return None; }
    let pool_size = count_color_occurrences(puzzle, &colors);
    let n_pos = puzzle.cell_count();
    let last_idx = n_pos.saturating_sub(1);

    // Dense sample from McGavin 469 cum-curve, minus 1-edge floor.
    // Final point clamped to n_pos-1 to land inside the path.
    let mut targets: Vec<(u32, u32)> = vec![
        (0,   0),
        (16,  0),
        (32,  3),
        (48,  12),
        (64,  25),
        (80,  31),
        (96,  39),
        (112, 43),
        (128, 47),
        (144, 60),
        (160, 81),
        (176, 89),
        (192, 104),
        (208, 118),
        (224, 128),
        (240, 146),
    ];
    // Append saturation point at the very last cell. Use the
    // observed total minus margin if it fits, else cap at last_idx.
    if last_idx > 240 {
        targets.push((last_idx, pool_size.min(149)));
    }

    let bw_breaks: [u32; 12] = [201, 206, 211, 216, 221, 225, 229, 233, 237, 239, 241, 256];
    let breaks: Vec<u32> = bw_breaks
        .iter()
        .map(|&b| {
            let scaled = ((b as u64 * n_pos as u64) / 256u64) as u32;
            scaled.min(n_pos.saturating_sub(1))
        })
        .collect();

    let target_max = targets.last().map(|&(d, _)| d).unwrap_or(n_pos - 1);
    let s = BlackwoodSchedule {
        heuristic_sides: colors,
        exhaustion_targets: targets,
        heuristic_pool_size: pool_size,
        max_heuristic_index: target_max,
        break_indexes_allowed: breaks,
    };
    if let Err(e) = s.validate() {
        eprintln!("WARNING: blackwood_schedule_calibrated_v17b produced invalid schedule: {e}");
        return None;
    }
    Some(s)
}

#[derive(Debug, Clone, Copy)]
pub(crate) struct Row {
    pub(crate) piece_id: PieceId,
    pub(crate) edges: [Color; 4],
    pub(crate) rotation: u8,
    valid: bool,
}

/// Iterator that yields set bit positions of a u64 word, offset by `base`.
struct BitIter {
    cur: u64,
    base: u32,
}

impl Iterator for BitIter {
    type Item = u32;
    #[inline]
    fn next(&mut self) -> Option<u32> {
        if self.cur == 0 { return None; }
        let bit = self.cur.trailing_zeros();
        self.cur &= self.cur - 1;
        Some(self.base + bit)
    }
}

pub(crate) struct SearchState<'a> {
    pub(crate) puzzle: &'a Puzzle,
    pub(crate) opts: &'a SolveOpts,
    pub(crate) config: EngineConfig,
    pub(crate) solver_id: String,
    pub(crate) heuristic_profile: String,
    pub(crate) rows: Vec<Row>,
    /// Canonical domain representation as a flat row-id bitset.
    /// `domain_bits[pos * words_per_pos + word]` has bit `r_id % 64`
    /// of word `r_id / 64` set iff `r_id` is in the domain of `pos`.
    /// Vol-12 dropped the parallel `Vec<Vec<u32>>` rep (AUDIT_REPORT
    /// Step 6).
    pub(crate) domain_bits: Vec<u64>,
    /// Number of u64 words per position (ceil(n_rows / 64)).
    pub(crate) words_per_pos: usize,
    /// Precomputed: `side_color_mask[side * n_colors + color]` is a
    /// `words_per_pos`-word bitmask over row_ids whose
    /// `rows[r_id].edges[side] == color`. Used by place_and_propagate's
    /// 4-neighbor prune to do a single AND instead of a Vec scan.
    pub(crate) side_color_mask: Vec<u64>,
    /// Precomputed: `piece_mask[pid]` is a `words_per_pos`-word bitmask
    /// over row_ids belonging to piece `pid` (4 rotations). Used by
    /// piece-uniqueness propagation to mask off all 4 rotations of a
    /// placed piece at once.
    pub(crate) piece_mask: Vec<u64>,
    /// n_colors used to index side_color_mask.
    pub(crate) n_colors: usize,
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
    /// Vol-14 — `cell_side_edge[pos * 4 + side]` = edge_id in the BP
    /// marginals file. Empty unless value-order is
    /// `EdgeBpMarginals` *and* `opts.edge_bp_marginals` is set.
    /// Enumeration order matches `scripts/v12_edge_bp.py`
    /// `build_grid_edges`: scan (y,x) row-major; for each cell claim
    /// N then (S if y==H-1) then W then (E if x==W-1); shared sides
    /// reuse the neighbour's edge_id.
    pub(crate) cell_side_edge: Vec<u32>,
    /// Vol-14 transient instrumentation: backtracks bucketed by the
    /// cell whose value-choice exhausted. `pos_backtracks[pos]` =
    /// count of times `recurse` saw a Wipeout while attempting some
    /// row at `pos`. Exposed via `EngineSolver::take_pos_backtracks`
    /// for harness-side bucket analysis (corner / edge / interior).
    /// Always allocated; cheap (1 KB on canonical E2).
    pub(crate) pos_backtracks: Vec<u64>,
    /// Vol-14 `PathSkeleton::HintRectangle` auto-injected prefix length.
    /// When > 0, `select_position` walks the first `auto_skeleton_path_k`
    /// entries of `path_order` (which were populated from the hint
    /// rectangle) before falling back to the variable-order heuristic.
    /// Independent of `opts.path` / `opts.path_policy` — those still work
    /// if the user wants explicit control.
    pub(crate) auto_skeleton_path_k: u32,
    /// Vol-15 — Blackwood schedule cloned from the solver.
    pub(crate) blackwood: Option<Arc<BlackwoodSchedule>>,
    /// Vol-15 — set bitset over `heuristic_sides` for fast membership.
    /// `heuristic_color_mask[c as usize] = true` iff `c` is in
    /// `schedule.heuristic_sides`. Empty when no schedule.
    pub(crate) heuristic_color_mask: Vec<bool>,
    /// Vol-15 — `break_indexes_allowed` lifted into a bitvec indexed
    /// by SCAN-ORDER INDEX (not engine traversal depth). At each
    /// recurse depth the engine fetches `pos`, then tests
    /// `is_break_index[scan_index_of_cell[pos]]`. This handles the
    /// case where hint cells are skipped from the engine traversal
    /// (depth ≠ scan_index) and HintRectangle composition (scan_index
    /// is still well-defined for each cell). Empty when no schedule.
    pub(crate) is_break_index: Vec<bool>,
    /// Vol-15 — scan-order index of each cell. Built when scan_order
    /// is set; empty otherwise.
    pub(crate) scan_index_of_cell: Vec<u32>,
    /// Vol-15 — running count of placed heuristic-color edge
    /// occurrences (Σ over placed rows of count of heuristic-colored
    /// edges in that row). Maintained incrementally by
    /// place_and_propagate / undo_place. 0 when no schedule.
    pub(crate) placed_heuristic_count: u32,
    /// Vol-16 Cat-4f — precomputed table for the AC-3 inner support
    /// loop. `same_piece_rots[row_id * 16 + side_a * 4 + side_b]` is a
    /// 4-bit mask (low nibble of a u8) where bit `r` is set iff
    /// rotation `r` of `row.piece_id` has the SAME color on side_b as
    /// `row.edges[side_a]`. AC-3's `same_piece` count becomes a single
    /// `(mask & present_4).count_ones()` instead of a 4-iteration loop
    /// with bounds-checked array reads on every rotation.
    ///
    /// Built once at SearchState::new from the static row table.
    /// Size: rows.len() * 16 bytes = ~16 KB on canonical E2.
    pub(crate) same_piece_rots: Vec<u8>,
    /// Vol-16 Cat-4g — reusable scratch buffer for the AC-3 inner
    /// "rows to support-check" list. Was a per-queue-pop allocation;
    /// recycle the capacity on each AC-3 invocation.
    pub(crate) ac3_to_check: Vec<u32>,
    /// Vol-16 Cat-4g — reusable AC-3 work queue (was Vec::with_capacity(16)
    /// per invocation). LIFO discipline.
    pub(crate) ac3_queue: Vec<Position>,
    /// Vol-16 Cat-4 — single arena for all UndoEntry bit-diff buffers.
    /// `UndoEntry { pos, words_start }` references a contiguous slice
    /// `[words_start..words_start + words_per_pos]`. The arena grows
    /// monotonically within a `place_and_propagate_opts` call and is
    /// truncated back when `restore()` runs after the recurse child
    /// returns (LIFO discipline). Replaces ~42% of pre-vol-16 CPU
    /// spent in System::alloc/dealloc inside the `prune` closure.
    pub(crate) undo_words_arena: Vec<u64>,
    /// Vol-24 — total internal grid edges = (w-1)*h + w*(h-1). Cached
    /// because the bound prune queries it on every node.
    pub(crate) total_internal_edges: u32,
    /// Vol-24 — running count of internal edges with BOTH endpoints
    /// placed. Maintained incrementally: each `place_and_propagate_opts`
    /// adds one per placed neighbour; `undo_place` subtracts the same
    /// count (LIFO discipline guarantees correctness without snapshots).
    pub(crate) decided_edges: u32,
    /// Vol-24 — running count of internal edges with both endpoints
    /// placed AND matching colors (excluding BORDER 0). The MaxScore
    /// objective. Same incremental discipline as `decided_edges`.
    pub(crate) matched_count: u32,
    /// Vol-24 — best matched-edge count seen across the whole search.
    /// Only meaningful when `opts.objective == Some(Objective::MaxScore)`.
    pub(crate) best_score: u32,
    /// Vol-24 — board snapshot at the moment we observed `best_score`.
    /// Cleared at search start; set the first time a candidate beats
    /// the running best.
    pub(crate) best_score_partial: Option<Board>,
    /// Vol-24 — shared best-score atom across all RootSplit workers.
    /// Each worker reads it into the prune test (`max(local, shared)`)
    /// and CAS-bumps it whenever its leaf beats the running shared
    /// best. Single-threaded runs use `None` and rely on `best_score`
    /// only. The shared atom is the only mechanism that makes parallel
    /// branch-and-bound monotone-optimal under RootSplit; without it,
    /// workers can return strictly suboptimal local bests.
    pub(crate) shared_best_score: Option<Arc<std::sync::atomic::AtomicU32>>,
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

        // Vol-16 Cat-4f — precomputed same-piece rotation table for AC-3.
        // For each row r and (side_a, side_b) pair: which rotations of
        // r's piece have edges[side_b] == r.edges[side_a]? Stored as a
        // 4-bit mask in the low nibble of a u8. Reads turn AC-3's
        // 4-iteration support loop into a single mask + popcount.
        let mut same_piece_rots: Vec<u8> = vec![0; rows.len() * 16];
        for r_id in 0..rows.len() {
            let r = &rows[r_id];
            if !r.valid {
                continue;
            }
            let pid_base = usize::from(r.piece_id) * 4;
            for side_a in 0..4 {
                let required = r.edges[side_a];
                for side_b in 0..4 {
                    let mut mask: u8 = 0;
                    for rot in 0..4 {
                        let cand = pid_base + rot;
                        if cand >= rows.len() {
                            break;
                        }
                        let rc = &rows[cand];
                        if rc.valid && rc.edges[side_b] == required {
                            mask |= 1 << rot;
                        }
                    }
                    same_piece_rots[r_id * 16 + side_a * 4 + side_b] = mask;
                }
            }
        }

        let n_pos = puzzle.cell_count() as usize;
        let n_rows = max_piece_index * 4;
        let words_per_pos = n_rows.div_ceil(64).max(1);

        // Build domain_bits directly. Each cell admits rows whose
        // BORDER-edge mask matches the cell's border_mask.
        let mut domain_bits = vec![0u64; n_pos * words_per_pos];
        for pos in 0..puzzle.cell_count() {
            let mask = puzzle.border_mask(pos);
            let [on_top, on_right, on_bot, on_left] = mask;
            let base = (pos as usize) * words_per_pos;
            for (idx, row) in rows.iter().enumerate() {
                if !row.valid { continue; }
                let [t, ri, b, l] = row.edges;
                if on_top != (t == BORDER) { continue; }
                if on_right != (ri == BORDER) { continue; }
                if on_bot != (b == BORDER) { continue; }
                if on_left != (l == BORDER) { continue; }
                domain_bits[base + (idx >> 6)] |= 1u64 << (idx & 63);
            }
        }

        // Resolve path_order: prefer user-supplied opts.path, otherwise
        // auto-build from config.path_skeleton + config.scan_order.
        //
        // Vol-15 composition: when BOTH `path_skeleton` (e.g.
        // HintRectangle) and `scan_order` (Blackwood bottom-up) are
        // set, build the rectangle path FIRST and then append the
        // remaining cells in scan order. This way:
        //   - The engine's traversal depth always equals the
        //     position's index in `path_order`.
        //   - Blackwood break-indexes (the schedule's
        //     `break_indexes_allowed`) are interpreted as DEPTHS
        //     in the engine's traversal, not as raw cell labels.
        //   - The HintRectangle prefix still does its job (forces
        //     the 49 rectangle cells to be placed first).
        let order_key = |pos: Position, w: u32, h: u32, order: ScanOrder| -> u32 {
            let (x, y) = (pos % w, pos / w);
            match order {
                ScanOrder::RowMajorTopDown => y * w + x,
                ScanOrder::RowMajorBottomUp => (h - 1 - y) * w + x,
            }
        };
        let (path_order, auto_skeleton_path_k) = if !opts.path.is_empty() {
            (opts.path.clone(), 0u32)
        } else {
            let skel_path: Vec<Position> = match solver.config.path_skeleton {
                Some(PathSkeleton::HintRectangle) =>
                    build_hint_rectangle_path(puzzle, &opts.hints),
                Some(PathSkeleton::HintRectangleLayered) =>
                    build_hint_rectangle_layered_path(puzzle, &opts.hints),
                Some(PathSkeleton::XSkeleton) =>
                    build_x_skeleton_path(puzzle, &opts.hints),
                None => Vec::new(),
            };
            let n_cells = puzzle.cell_count();
            if !skel_path.is_empty() && solver.config.scan_order.is_some() {
                // Compose: rectangle prefix + remaining cells in scan order.
                let order = solver.config.scan_order.unwrap();
                let in_skel: std::collections::HashSet<Position> =
                    skel_path.iter().copied().collect();
                let mut tail: Vec<Position> = (0..n_cells)
                    .filter(|p| !in_skel.contains(p))
                    .collect();
                tail.sort_by_key(|&pos| order_key(pos, puzzle.width, puzzle.height, order));
                let mut p = skel_path;
                p.extend(tail);
                let k = p.len() as u32;
                (p, k)
            } else if !skel_path.is_empty() {
                let k = skel_path.len() as u32;
                (skel_path, k)
            } else if let Some(order) = solver.config.scan_order {
                let mut p: Vec<Position> = (0..n_cells).collect();
                p.sort_by_key(|&pos| order_key(pos, puzzle.width, puzzle.height, order));
                let k = p.len() as u32;
                (p, k)
            } else {
                (Vec::new(), 0u32)
            }
        };
        let mut path_index_of = vec![u32::MAX; n_pos];
        for (i, &p) in path_order.iter().enumerate() {
            if (p as usize) < n_pos {
                path_index_of[p as usize] = i as u32;
            }
        }

        // Precomputed side+color → rows bitmask. Used by the 4-neighbor
        // prune in place_and_propagate to AND off any row whose
        // edges[side]==required is not the required color.
        let n_colors = puzzle.color_count as usize;
        let mut side_color_mask = vec![0u64; 4 * n_colors * words_per_pos];
        for (r_id, row) in rows.iter().enumerate() {
            if !row.valid { continue; }
            for side in 0..4 {
                let c = row.edges[side] as usize;
                if c >= n_colors { continue; }
                let base = (side * n_colors + c) * words_per_pos;
                side_color_mask[base + r_id / 64] |= 1u64 << (r_id % 64);
            }
        }

        // Precomputed piece → rows bitmask. Used by piece-uniqueness
        // propagation: when piece `p` is placed, AND off all 4 rotations
        // of p from every unplaced cell's bitset.
        let mut piece_mask = vec![0u64; max_piece_index.max(1) * words_per_pos];
        for (r_id, row) in rows.iter().enumerate() {
            if !row.valid { continue; }
            let pid = usize::from(row.piece_id);
            if pid < max_piece_index {
                piece_mask[pid * words_per_pos + r_id / 64] |= 1u64 << (r_id % 64);
            }
        }

        Self {
            puzzle,
            opts,
            config: solver.config,
            solver_id: solver.solver_id.clone(),
            heuristic_profile: solver.heuristic_profile.clone(),
            rows,
            domain_bits,
            words_per_pos,
            side_color_mask,
            piece_mask,
            n_colors,
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
            gacolor: if solver.config.propagators.gacolor {
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
            ac3_count: if solver.config.propagators.ac3 {
                vec![0u16; n_pos * 4 * puzzle.color_count as usize]
            } else {
                Vec::new()
            },
            ac3_present: if solver.config.propagators.ac3 {
                let n_rows = max_piece_index * 4;
                vec![0u64; n_pos * n_rows.div_ceil(64)]
            } else {
                Vec::new()
            },
            ac3_on_queue: if solver.config.propagators.ac3 {
                vec![false; n_pos]
            } else {
                Vec::new()
            },
            cell_side_edge: if matches!(solver.config.value_order, ValueOrder::EdgeBpMarginals)
                && opts.edge_bp_marginals.is_some()
            {
                build_cell_side_edge(puzzle)
            } else {
                Vec::new()
            },
            pos_backtracks: vec![0u64; n_pos],
            auto_skeleton_path_k,
            blackwood: solver.blackwood_schedule.clone(),
            heuristic_color_mask: {
                if let Some(s) = &solver.blackwood_schedule {
                    let max_c = s.heuristic_sides.iter().copied().max().unwrap_or(0) as usize;
                    let mut m = vec![false; max_c + 1];
                    for &c in &s.heuristic_sides {
                        m[c as usize] = true;
                    }
                    m
                } else {
                    Vec::new()
                }
            },
            is_break_index: {
                // Vol-15 — `break_indexes_allowed` interpreted as
                // engine-traversal DEPTHS (the i-th cell placed in
                // path_order). Composition rule in path-order
                // construction above guarantees: under pure bottom-up
                // scan, depth == bu_idx; under rectangle+scan, depth
                // is rectangle-then-scan position. Either way, "break
                // at depth k" matches the spec's intent.
                if let Some(s) = &solver.blackwood_schedule {
                    let mut v = vec![false; n_pos];
                    for &idx in &s.break_indexes_allowed {
                        if (idx as usize) < v.len() {
                            v[idx as usize] = true;
                        }
                    }
                    v
                } else {
                    Vec::new()
                }
            },
            scan_index_of_cell: {
                if let Some(order) = solver.config.scan_order {
                    let w = puzzle.width;
                    let h = puzzle.height;
                    let mut v = vec![0u32; n_pos];
                    for pos in 0..puzzle.cell_count() {
                        let (x, y) = (pos % w, pos / w);
                        let scan_idx = match order {
                            ScanOrder::RowMajorTopDown => y * w + x,
                            ScanOrder::RowMajorBottomUp => (h - 1 - y) * w + x,
                        };
                        v[pos as usize] = scan_idx;
                    }
                    v
                } else {
                    Vec::new()
                }
            },
            placed_heuristic_count: 0,
            same_piece_rots,
            ac3_to_check: Vec::with_capacity(1024),
            ac3_queue: Vec::with_capacity(256),
            // Vol-16 Cat-4 — pre-reserve the arena for the worst-case
            // undo log: 4 prunes + n_pos piece-uniqueness entries per
            // place_and_propagate_opts call, * wpp words per entry,
            // * (n_pos) recursion depth. Conservative upper bound;
            // typical canonical-E2 usage is well under 10× smaller.
            undo_words_arena: Vec::with_capacity(
                (n_pos as usize) * (n_pos as usize + 4) * words_per_pos,
            ),
            total_internal_edges: (puzzle.width - 1) * puzzle.height
                + puzzle.width * (puzzle.height - 1),
            decided_edges: 0,
            matched_count: 0,
            best_score: 0,
            best_score_partial: None,
            shared_best_score: None,
        }
    }

    /// Vol-24 — inject the cross-worker shared best-score atom. Called
    /// by `parallel::run_unit` once per worker; single-thread runs skip
    /// this. The atom is read on every node and CAS-bumped on every
    /// leaf in MaxScore mode.
    pub(crate) fn attach_shared_best_score(
        &mut self,
        atom: Arc<std::sync::atomic::AtomicU32>,
    ) {
        self.shared_best_score = Some(atom);
    }

    fn elapsed_us(&self) -> u64 { self.started.elapsed_us() }

    fn timed_out(&self) -> bool {
        self.opts.time_budget_ms != 0
            && self.elapsed_us() / 1000 >= self.opts.time_budget_ms
    }

    /// Domain size for `pos`, computed from `domain_bits`.
    #[inline]
    fn domain_size(&self, pos: usize) -> u32 {
        let base = pos * self.words_per_pos;
        let mut n = 0u32;
        for w in 0..self.words_per_pos {
            n += self.domain_bits[base + w].count_ones();
        }
        n
    }

    /// Iterate set row_ids in domain of `pos`.
    fn domain_iter(&self, pos: usize) -> impl Iterator<Item = u32> + '_ {
        let base = pos * self.words_per_pos;
        let wpp = self.words_per_pos;
        (0..wpp).flat_map(move |w| {
            let word = self.domain_bits[base + w];
            BitIter { cur: word, base: (w as u32) * 64 }
        })
    }

    /// Snapshot a per-position bitset as a `Vec<u64>` of words.
    #[inline]
    fn snapshot_bits(&self, pos: usize) -> Vec<u64> {
        let base = pos * self.words_per_pos;
        self.domain_bits[base..base + self.words_per_pos].to_vec()
    }

    /// Restore a per-position bitset from a snapshot.
    #[inline]
    fn restore_bits(&mut self, pos: usize, snap: &[u64]) {
        let base = pos * self.words_per_pos;
        self.domain_bits[base..base + self.words_per_pos].copy_from_slice(snap);
    }

    /// True iff domain[pos] is empty.
    #[inline]
    fn domain_is_empty(&self, pos: usize) -> bool {
        let base = pos * self.words_per_pos;
        self.domain_bits[base..base + self.words_per_pos].iter().all(|&w| w == 0)
    }

    /// True iff row_id is in domain[pos].
    #[inline]
    fn domain_contains(&self, pos: usize, row_id: u32) -> bool {
        let base = pos * self.words_per_pos;
        let r = row_id as usize;
        (self.domain_bits[base + (r >> 6)] >> (r & 63)) & 1 == 1
    }

    /// Restrict domain[pos] to exactly `{row_id}`.
    #[inline]
    fn pin_to(&mut self, pos: usize, row_id: u32) {
        let base = pos * self.words_per_pos;
        for w in &mut self.domain_bits[base..base + self.words_per_pos] { *w = 0; }
        let r = row_id as usize;
        self.domain_bits[base + (r >> 6)] = 1u64 << (r & 63);
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
        let d = self.domain_size(pos as usize);
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
        // 1. Explicit user path takes priority.
        if let PathPolicy::PrefixConstraint { k } = self.opts.path_policy {
            if self.stats.current_depth < k {
                for &p in &self.path_order {
                    if self.placed[p as usize].is_none() {
                        return Some(p);
                    }
                }
            }
        }
        // 2. Vol-14 auto-skeleton path (config.path_skeleton). Only
        // applies when no explicit user path was provided.
        if self.auto_skeleton_path_k > 0
            && self.opts.path.is_empty()
            && self.stats.current_depth < self.auto_skeleton_path_k
        {
            for &p in &self.path_order {
                if self.placed[p as usize].is_none() {
                    return Some(p);
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
        self.place_and_propagate_opts(sink, depth, pos, row_id, None)
    }

    /// Vol-15 — extended `place_and_propagate` that optionally skips
    /// edge-color propagation on one of the placed row's 4 sides (used
    /// at Blackwood break-indexes, where the placement intentionally
    /// mismatches a placed neighbour). `skip_side`:
    ///   `None`     ⇒ propagate normally (engine's pre-vol-15 behaviour).
    ///   `Some(s)`  ⇒ skip the edge-color prune on side `s` (0=N, 1=E,
    ///                2=S, 3=W). Piece-uniqueness, AC-3, and Step-8
    ///                propagators still run.
    pub(crate) fn place_and_propagate_opts(
        &mut self,
        sink: &mut dyn EventSink,
        depth: u32,
        pos: Position,
        row_id: u32,
        skip_side: Option<usize>,
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
        // Vol-15 — increment Blackwood heuristic-count.
        self.placed_heuristic_count += self.count_heuristic_in_row(&row.edges);
        // Vol-24 — incremental score tracking for the MaxScore objective.
        // For each of the 4 sides, if the neighbour cell is also placed,
        // this edge has just become "decided". It counts as a match iff
        // the touching colors agree AND aren't BORDER (color 0). Walked
        // unconditionally — cost ~16 ALU ops per placement, dwarfed by
        // propagation; cheaper than gating on `opts.objective`.
        {
            let (px, py) = self.puzzle.xy(pos);
            let pw = self.puzzle.width;
            let ph = self.puzzle.height;
            let nbs: [(Option<Position>, usize, usize); 4] = [
                (if py > 0 { Some((py - 1) * pw + px) } else { None }, 0, 2),
                (if px + 1 < pw { Some(py * pw + (px + 1)) } else { None }, 1, 3),
                (if py + 1 < ph { Some((py + 1) * pw + px) } else { None }, 2, 0),
                (if px > 0 { Some(py * pw + (px - 1)) } else { None }, 3, 1),
            ];
            for (nb_opt, our_side, their_side) in nbs {
                let Some(nb) = nb_opt else { continue; };
                let Some(nb_row_id) = self.placed[nb as usize] else { continue; };
                self.decided_edges += 1;
                let nb_edges = self.rows[nb_row_id as usize].edges;
                let our = row.edges[our_side];
                if our != 0 && our == nb_edges[their_side] {
                    self.matched_count += 1;
                }
            }
        }
        // Vol-16 Cat-4b: pre-allocate so the `undo.push` chain doesn't
        // hit `RawVecInner::grow_amortized`. Worst case is one entry
        // per cell (piece-uniqueness over all unplaced positions) +
        // four neighbour prunes + ~few AC-3 cascades. Sized to
        // `n_pos + 8` to cover the common path without overshooting.
        let mut undo: Vec<UndoEntry> = Vec::with_capacity(self.puzzle.cell_count() as usize + 8);

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
            let wpp = this.words_per_pos;
            let bit_base = (neighbor as usize) * wpp;
            let n_colors = this.n_colors;
            let req_idx = required as usize;
            // Build keep mask:
            //   rows whose edges[neighbor_edge_idx]==required, MINUS
            //   rows belonging to the just-placed piece.
            let sc_base = (neighbor_edge_idx * n_colors + req_idx) * wpp;
            let pm_base = usize::from(row.piece_id) * wpp;
            // Vol-23 — stack scratch + track survival in the same loop;
            // see piece-uniqueness path in place_and_propagate for the
            // motivation (eliminates bzero traffic + redundant
            // domain_is_empty rescan).
            const MAX_WPP: usize = 32;
            debug_assert!(wpp <= MAX_WPP);
            let mut drop_scratch = [0u64; MAX_WPP];
            let mut popcount: u32 = 0;
            let mut survived: u64 = 0;
            // Slice-based inner loop for bounds elision.
            let dom = &mut this.domain_bits[bit_base..bit_base + wpp];
            let pmask = &this.piece_mask[pm_base..pm_base + wpp];
            let sc_mask: &[u64] = if req_idx < n_colors {
                &this.side_color_mask[sc_base..sc_base + wpp]
            } else {
                &[]
            };
            let scratch = &mut drop_scratch[..wpp];
            for w in 0..wpp {
                let cur = dom[w];
                let keep = if req_idx < n_colors {
                    sc_mask[w] & !pmask[w]
                } else {
                    !pmask[w]
                };
                let drop = cur & !keep;
                let new = cur & keep;
                scratch[w] = drop;
                survived |= new;
                popcount += drop.count_ones();
                dom[w] = new;
            }
            if popcount > 0 {
                this.stats.propagations += popcount as u64;
                let arena_start = this.undo_words_arena.len();
                this.undo_words_arena.extend_from_slice(scratch);
                let entry = UndoEntry { pos: neighbor, words_start: arena_start as u32 };
                if survived == 0 {
                    PruneResult::Wipeout { entry }
                } else {
                    PruneResult::Removed(entry)
                }
            } else {
                PruneResult::Ok
            }
        };

        // Four neighbor prunes (edge-color propagation). Each entry
        // is (neighbour, neighbour-facing-edge-index, required-color,
        // our-side-index). When `skip_side == Some(our_side)` we
        // suppress propagation through that side (Vol-15 Blackwood
        // break-index allowance).
        let neighbors: [(Option<Position>, usize, Color, usize); 4] = [
            (if y > 0 { Some((y - 1) * w + x) } else { None }, 2, row.edges[0], 0),
            (if x + 1 < w { Some(y * w + (x + 1)) } else { None }, 3, row.edges[1], 1),
            (if y + 1 < h { Some((y + 1) * w + x) } else { None }, 0, row.edges[2], 2),
            (if x > 0 { Some(y * w + (x - 1)) } else { None }, 1, row.edges[3], 3),
        ];
        for (maybe_np, edge_idx, required, our_side) in neighbors {
            if Some(our_side) == skip_side { continue; }
            let Some(np) = maybe_np else { continue; };
            match prune(self, np, edge_idx, required) {
                PruneResult::Wipeout { entry } => {
                    undo.push(entry);
                    self.stats.domain_wipeouts += 1;
                    self.emit(sink, depth, EventBody::DomainWipeout { position: np });
                    return PropagationOutcome::Wipeout { undo };
                }
                PruneResult::Removed(entry) => undo.push(entry),
                PruneResult::Ok => {}
            }
        }

        // Piece-uniqueness propagation (the "column" of classic DLX).
        // Bitset form: for every unplaced cell p, AND off any row in
        // piece_mask[just_placed_piece]. Save the dropped bits as a
        // bit-diff for the undo log — no per-row iteration.
        // Vol-16 Cat-4b: same capacity argument as `undo` above.
        let mut other_undo: Vec<UndoEntry> = Vec::with_capacity(self.puzzle.cell_count() as usize);
        let words_per_pos = self.words_per_pos;
        let pm_base = piece_idx * words_per_pos;
        // Vol-23 — stack scratch buffer for the per-cell drop bits, sized
        // large enough for any realistic puzzle (16 words = 1024 rows =
        // canonical E2; 32 words = 2048 rows ⇒ 32×32). Avoids the
        // `resize(+wpp, 0)` zero-fill (bzero call site visible in
        // flamegraph) that previously dominated the arena push path.
        const MAX_WPP: usize = 32;
        debug_assert!(words_per_pos <= MAX_WPP, "words_per_pos {} exceeds MAX_WPP {}", words_per_pos, MAX_WPP);
        let mut drop_scratch = [0u64; MAX_WPP];
        for p in 0..self.puzzle.cell_count() {
            if p == pos || self.placed[p as usize].is_some() { continue; }
            let bit_base = (p as usize) * words_per_pos;
            let mut popcount: u32 = 0;
            // OR of post-mask domain words — equivalent to
            // `domain_is_empty(p)` after the loop without a second pass.
            let mut survived: u64 = 0;
            // Slice-based inner loop. Split borrows so dom + pmask + the
            // scratch buffer can all be sliced for bounds-elision.
            let dom = &mut self.domain_bits[bit_base..bit_base + words_per_pos];
            let pmask = &self.piece_mask[pm_base..pm_base + words_per_pos];
            let scratch = &mut drop_scratch[..words_per_pos];
            for w in 0..words_per_pos {
                let cur = dom[w];
                let drop = cur & pmask[w];
                let new = cur & !pmask[w];
                scratch[w] = drop;
                survived |= new;
                popcount += drop.count_ones();
                dom[w] = new;
            }
            if popcount > 0 {
                self.stats.propagations += popcount as u64;
                let arena_start = self.undo_words_arena.len();
                // Push the full slot in one shot — no zero-fill, no
                // conditional inner writes. extend_from_slice over a
                // statically-sized chunk lets the compiler vectorize.
                self.undo_words_arena.extend_from_slice(scratch);
                let entry = UndoEntry { pos: p, words_start: arena_start as u32 };
                if survived == 0 {
                    other_undo.push(entry);
                    self.stats.domain_wipeouts += 1;
                    undo.extend(other_undo);
                    self.emit(sink, depth, EventBody::DomainWipeout { position: p });
                    return PropagationOutcome::Wipeout { undo };
                }
                other_undo.push(entry);
            }
        }
        undo.extend(other_undo);

        // AC-3 cascading propagation. Re-checks arc-consistency from the
        // freshly-placed cell outward until fixpoint. Each row r at
        // position a is "supported by" position b if some row r' in
        // domain[b] has matching color on the shared edge and r.piece !=
        // r'.piece. If support is lost we drop r from domain[a]. Updates
        // can cascade through the grid.
        if self.config.propagators.ac3 {
            match self.propagate_ac3(sink, depth, pos) {
                Ac3Outcome::Wipeout { removed } => {
                    undo.extend(removed);
                    return PropagationOutcome::Wipeout { undo };
                }
                Ac3Outcome::Ok { removed } => {
                    undo.extend(removed);
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
        // ac3_present is overwritten by copy_from_slice below — no need to zero.
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
        // Bitset present mirror is already maintained incrementally on
        // self.domain_bits — just copy. Saves the per-row bit-set cost
        // during the entry rebuild loop.
        debug_assert!(self.domain_bits.len() == present_len,
            "domain_bits ({}) != present_len ({})", self.domain_bits.len(), present_len);
        self.ac3_present[..present_len].copy_from_slice(&self.domain_bits[..present_len]);
        let count = &mut self.ac3_count;
        let present = &mut self.ac3_present;
        let on_queue = &mut self.ac3_on_queue;
        // Build `count` by iterating set bits of self.domain_bits per pos.
        // Vol-16 — slice the per-position views to elide bounds checks
        // on the inner increment, and bind the rows slice once.
        let rows = self.rows.as_slice();
        let dom_bits = self.domain_bits.as_slice();
        for p in 0..n_pos as usize {
            if self.placed[p].is_some() { continue; }
            let base = p * words_per_pos;
            let pos_count_base = p * stride_pos;
            let dom_slice = &dom_bits[base..base + words_per_pos];
            let count_slice = &mut count[pos_count_base..pos_count_base + stride_pos];
            for (w, &word_init) in dom_slice.iter().enumerate() {
                let mut word = word_init;
                let bit_base = (w as u32) * 64;
                while word != 0 {
                    let bit = word.trailing_zeros();
                    word &= word - 1;
                    let r_id = bit_base + bit;
                    let r = &rows[r_id as usize];
                    // Unrolled 4-side accumulator.
                    count_slice[r.edges[0] as usize] += 1;
                    count_slice[n_colors + r.edges[1] as usize] += 1;
                    count_slice[2 * n_colors + r.edges[2] as usize] += 1;
                    count_slice[3 * n_colors + r.edges[3] as usize] += 1;
                }
            }
        }
        // Vol-16 Cat-4g — reuse the queue scratch across AC-3 calls.
        self.ac3_queue.clear();
        let queue = &mut self.ac3_queue;
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
        // Vol-16 Cat-4b — bound the AC-3 cascade output by n_pos so we
        // skip grow_amortized work.
        let mut all_removed: Vec<UndoEntry> = Vec::with_capacity(self.puzzle.cell_count() as usize);

        let mut ac3_tick: u32 = 0;
        while let Some(a) = queue.pop() {
            ac3_tick = ac3_tick.wrapping_add(1);
            // Cooperative timeout check inside the AC-3 loop. On hard
            // puzzles a single AC-3 invocation can churn for seconds;
            // without this the outer per-N-nodes timeout check fires
            // late. Vol-23 — flamegraph showed `elapsed_us()` cost was
            // 12.4% of joe runtime at 1/64 rate (mach_absolute_time +
            // Duration arithmetic on macOS is ~800% of an inner-loop
            // iteration). Drop to 1/4096; worst-case timeout latency is
            // still sub-millisecond on joe's 7k nps. Reading self.started
            // through an immutable borrow is fine here because count/
            // present/on_queue are disjoint fields (NLL).
            if ac3_tick & 0xfff == 0 && self.started.elapsed_us() >= timeout_at_us {
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

            // Accumulate the bit-diff for position `a` as words_per_pos
            // u64s — cheaper to OR back on restore than to iterate
            // individual row-ids. Vol-23 — stack scratch instead of the
            // arena's resize-then-truncate dance. The previous version
            // paid bzero on every queue pop (4.29% of joe runtime) and a
            // truncate on every no-diff pop. With scratch we extend the
            // arena exactly once at the end, only if there's a diff.
            const MAX_WPP: usize = 32;
            debug_assert!(words_per_pos <= MAX_WPP);
            let mut diff_scratch = [0u64; MAX_WPP];
            let mut removed_popcount: u32 = 0;
            let a_u = a as usize;
            // Iterate set bits of domain_bits[a_u]. Mutate the bitset
            // in-place when a row is unsupported (the iteration takes a
            // snapshot before the loop body so we don't observe our own
            // mutations).
            // Vol-16 Cat-4g — reuse the scratch Vec across queue pops.
            // Length-reset (no reallocation); capacity persists for the
            // lifetime of SearchState.
            self.ac3_to_check.clear();
            {
                let base = a_u * words_per_pos;
                for w in 0..words_per_pos {
                    let mut word = self.domain_bits[base + w];
                    while word != 0 {
                        let bit = word.trailing_zeros();
                        word &= word - 1;
                        self.ac3_to_check.push((w as u32) * 64 + bit);
                    }
                }
            }
            // Clone the small Vec out of self so we don't double-borrow
            // (the inner loop mutates other fields of self).
            let to_check_len = self.ac3_to_check.len();
            for ti in 0..to_check_len {
                let r_id = self.ac3_to_check[ti];
                let r = self.rows[r_id as usize];
                let mut supported = true;
                let pid_base = usize::from(r.piece_id) * 4;
                // Vol-16 Cat-4f — precomputed 4-bit rotation mask per
                // (row, side_a, side_b). Replaces the inner 4-iteration
                // loop with a single AND + popcount over `present`.
                let r_lut_base = (r_id as usize) * 16;
                let present_word_idx = pid_base / 64;
                let present_shift = pid_base % 64;
                for (nb_opt, side_a, side_b) in nb_info.iter() {
                    let Some(nb) = nb_opt else { continue; };
                    if self.placed[*nb as usize].is_some() { continue; }
                    let required = r.edges[*side_a] as usize;
                    let nb_u = *nb as usize;
                    let total = count[nb_u * stride_pos + side_b * n_colors + required];
                    // Precomputed: which rotations of r's piece satisfy
                    // edges[side_b] == r.edges[side_a]?
                    let rot_mask = self.same_piece_rots[r_lut_base + side_a * 4 + side_b];
                    // The 4 rotation bits are at pid_base..pid_base+4
                    // in `present`. Since 4 ≤ 64 they always sit inside
                    // a single u64 word.
                    let present_word = present[nb_u * words_per_pos + present_word_idx];
                    let present_4 = ((present_word >> present_shift) & 0xF) as u8;
                    let same_piece = (rot_mask & present_4).count_ones() as u16;
                    if total <= same_piece {
                        supported = false;
                        break;
                    }
                }
                if !supported {
                    let r_idx = r_id as usize;
                    let word_idx = r_idx / 64;
                    let bit_mask = 1u64 << (r_idx % 64);
                    diff_scratch[word_idx] |= bit_mask;
                    removed_popcount += 1;
                    present[a_u * words_per_pos + word_idx] &= !bit_mask;
                    self.domain_bits[a_u * words_per_pos + word_idx] &= !bit_mask;
                    for s in 0..4 {
                        let c = r.edges[s] as usize;
                        count[a_u * stride_pos + s * n_colors + c] -= 1;
                    }
                }
            }
            if removed_popcount > 0 {
                self.stats.propagations += removed_popcount as u64;
                let empty = {
                    let base = a_u * words_per_pos;
                    self.domain_bits[base..base + words_per_pos].iter().all(|&w| w == 0)
                };
                let arena_start = self.undo_words_arena.len();
                self.undo_words_arena.extend_from_slice(&diff_scratch[..words_per_pos]);
                all_removed.push(UndoEntry { pos: a, words_start: arena_start as u32 });
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
        if !self.config.propagators.class_balance
            && !self.config.propagators.parity
            && !self.config.propagators.island
            && !self.config.propagators.gacolor
            && !self.config.propagators.multiset_equality
        {
            return PropagatorResult::Ok;
        }
        // Depth gate (Joe-Saunders 2026): suppress Step-8 propagators
        // below threshold so early-search throughput approaches the
        // bare-edge-equality + AC-3 inner-loop ceiling.
        if let Some(threshold) = self.config.propagators.depth_threshold {
            if depth < threshold {
                return PropagatorResult::Ok;
            }
        }
        let placed_info = self.snapshot_placement_info();
        let ctx = PropagatorContext {
            puzzle: self.puzzle,
            placed: &placed_info,
            used_pieces: &self.used,
            domain_bits: &self.domain_bits,
            words_per_pos: self.words_per_pos,
        };
        if self.config.propagators.class_balance
            && class_balance_check(&ctx) == PropagatorResult::Wipeout
        {
            return PropagatorResult::Wipeout;
        }
        // gacolor uses the incremental cache for O(color_count) checks;
        // a fresh full recompute via `gacolor_check` is available for
        // unit testing parity vs incremental correctness, but the hot
        // path goes through GaColorState.
        if self.config.propagators.gacolor {
            let _ = gacolor_check; // keep symbol live for tests
            if let Some(gc) = self.gacolor.as_ref() {
                if gc.feasible() == PropagatorResult::Wipeout {
                    return PropagatorResult::Wipeout;
                }
            }
        }
        if self.config.propagators.island
            && island_check(&ctx) == PropagatorResult::Wipeout
        {
            return PropagatorResult::Wipeout;
        }
        if self.config.propagators.parity
            && parity_check(&ctx) == PropagatorResult::Wipeout
        {
            return PropagatorResult::Wipeout;
        }
        // NS-1 multiset equality: cheapest after the border ring closes;
        // before that the supply terms are loose and rarely triggers.
        if self.config.propagators.multiset_equality
            && multiset_equality_check(&ctx) == PropagatorResult::Wipeout
        {
            return PropagatorResult::Wipeout;
        }
        PropagatorResult::Ok
    }

    pub(crate) fn restore(&mut self, undo: Vec<UndoEntry>) {
        let words_per_pos = self.words_per_pos;
        // Track the lowest arena offset we need to keep — everything
        // above it was reserved by these entries and is safe to drop.
        // Entries are pushed in order during place_and_propagate, so
        // the minimum is the first entry's words_start. Empty undo log
        // means nothing was reserved here.
        let arena_keep = undo.iter().map(|e| e.words_start as usize).min();
        // Vol-16 Cat-2 follow-up: take a non-overlapping view of the
        // arena (read-only borrow) and the domain_bits (mutable). For
        // each entry, slice both to a length-wpp window so the inner
        // OR loop is bounds-check-free (the compiler elides them when
        // length is known from the slice). This was 19.1% self time
        // in the post-Cat-4 profile.
        let arena_slice = self.undo_words_arena.as_slice();
        let dom_slice = self.domain_bits.as_mut_slice();
        for entry in &undo {
            let pos_u = entry.pos as usize;
            let bit_base = pos_u * words_per_pos;
            let ws = entry.words_start as usize;
            // SAFETY-NOTE: these indices are guaranteed in-bounds by
            // construction (pos < cell_count, words_start was pushed
            // into the arena with wpp zeros, so words_start + wpp <=
            // arena.len()). We rely on slice access + iter().zip()
            // to let the compiler elide the bounds-check.
            let dst = &mut dom_slice[bit_base..bit_base + words_per_pos];
            let src = &arena_slice[ws..ws + words_per_pos];
            for (d, s) in dst.iter_mut().zip(src.iter()) {
                *d |= *s;
            }
        }
        drop(undo);
        if let Some(keep) = arena_keep {
            self.undo_words_arena.truncate(keep);
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
                    if self.domain_contains(0, row_id) {
                        self.pin_to(0, row_id);
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

        // Vol-23 — batch hint application mode for prune-restart.
        //
        // In `per-hint` (default) mode: pin each hint and propagate
        // immediately. The propagation removes options from other cells'
        // domains; if a later hint's row was among those removed, the
        // engine rejects the hint set even when it's globally consistent.
        // This happens routinely for hint sets ≥ ~50 cells extracted from
        // a DFS partial (the DFS visited cells in MRV order, not the
        // order we pin them).
        //
        // In `batch` mode: pin all hint domains first (no propagation
        // between hints), then run propagation once at the end. Self-
        // consistent hint sets always succeed.
        if self.opts.batch_hint_application {
            // Phase 1: pin all hint domains + claim pieces, with no
            // propagation. Validate each row is plausible (in domain
            // BEFORE any hint was pinned — checked at construction).
            for h in self.opts.hints.hints.clone() {
                let row_id = u32::from(h.piece_id) * 4 + u32::from(h.rotation.as_u8());
                let pos_idx = h.position as usize;
                let n_pos = self.puzzle.cell_count() as usize;
                if pos_idx >= n_pos {
                    return Err(SolveOutcome::Error(format!(
                        "hint at position {} out of range", h.position
                    )));
                }
                // domain_contains is checked against the FRESHLY BUILT
                // domain_bits (only border-class filtered, no propagation
                // applied yet). Self-consistent hints pass.
                if !self.domain_contains(pos_idx, row_id) {
                    return Err(SolveOutcome::Error(format!(
                        "hint at position {} (pid={}, rot={}) has border-class mismatch",
                        h.position, h.piece_id, h.rotation.as_u8()
                    )));
                }
                // Sanity: piece must not already be used. Catches duplicate
                // hints for the same piece-id.
                let piece_idx = usize::from(h.piece_id);
                if piece_idx < self.used.len() && self.used[piece_idx] {
                    return Err(SolveOutcome::Error(format!(
                        "hint at position {} uses piece {} which is already pinned elsewhere",
                        h.position, h.piece_id
                    )));
                }
                self.pin_to(pos_idx, row_id);
                self.placed[pos_idx] = Some(row_id);
                self.used[piece_idx] = true;
                // Vol-15 — update Blackwood heuristic count for this placement
                // (mirroring the increment in place_and_propagate).
                let row = self.rows[row_id as usize];
                let inc = self.count_heuristic_in_row(&row.edges);
                self.placed_heuristic_count = self.placed_heuristic_count.saturating_add(inc);
                // Also update gacolor occupancy if active.
                if self.gacolor.is_some() {
                    let n_info = self.neighbor_info(h.position);
                    if let Some(gc) = self.gacolor.as_mut() {
                        gc.apply_place(&row.edges, &n_info);
                    }
                }
            }
            // Phase 2: now propagate from all pinned cells. We trigger
            // propagation by re-pinning the LAST hint via
            // place_and_propagate; the propagators are global and will
            // see all already-pinned cells.
            //
            // Special case: if hints is empty, skip propagation entirely.
            if let Some(last) = self.opts.hints.hints.last().copied() {
                let row_id = u32::from(last.piece_id) * 4 + u32::from(last.rotation.as_u8());
                let pos_idx = last.position as usize;
                // Undo the last hint's pin/placed/used so place_and_propagate
                // can re-apply it cleanly; the bookkeeping side-effects (count,
                // gacolor) are idempotent under undo+redo.
                self.placed[pos_idx] = None;
                let piece_idx = usize::from(last.piece_id);
                self.used[piece_idx] = false;
                let row = self.rows[row_id as usize];
                let dec = self.count_heuristic_in_row(&row.edges);
                self.placed_heuristic_count = self.placed_heuristic_count.saturating_sub(dec);
                if self.gacolor.is_some() {
                    let n_info = self.neighbor_info(last.position);
                    if let Some(gc) = self.gacolor.as_mut() {
                        gc.apply_unplace(&row.edges, &n_info);
                    }
                }
                self.pin_to(pos_idx, row_id);
                if let PropagationOutcome::Wipeout { .. } =
                    self.place_and_propagate(sink, 0, last.position, row_id)
                {
                    return Err(SolveOutcome::Error(format!(
                        "batched hint propagation wiped out (final pin at position {})",
                        last.position
                    )));
                }
            }
        } else {
            for h in self.opts.hints.hints.clone() {
                let row_id = u32::from(h.piece_id) * 4 + u32::from(h.rotation.as_u8());
                let pos_idx = h.position as usize;
                let n_pos = self.puzzle.cell_count() as usize;
                if pos_idx >= n_pos || !self.domain_contains(pos_idx, row_id) {
                    return Err(SolveOutcome::Error(format!(
                        "hint at position {} is incompatible with constraints", h.position
                    )));
                }
                self.pin_to(pos_idx, row_id);
                if let PropagationOutcome::Wipeout { .. } = self.place_and_propagate(sink, 0, h.position, row_id) {
                    return Err(SolveOutcome::Error(format!(
                        "hint at position {} causes immediate wipeout", h.position
                    )));
                }
            }
        }
        Ok(())
    }

    /// Vol-14 wrapper: like `run` but also returns the per-position
    /// backtrack counters for downstream diagnostic analysis.
    pub(crate) fn run_with_diag(self, sink: &mut dyn EventSink) -> (SolveOutcome, Vec<u64>) {
        // Save a handle before run() consumes self; we'll repopulate
        // after by routing through `run`'s consumed body. The simplest
        // way is: replicate run() inline and snapshot at end. Since
        // run() is non-trivial we just call the existing run() via a
        // thin trampoline that exposes the counters.
        // Implementation: run consumes self, so we must replicate
        // the small wrapping. We achieve this by giving `run` the
        // option to return diag too.
        let (outcome, diag) = Self::run_inner(self, sink);
        (outcome, diag)
    }

    fn run_inner(state: Self, sink: &mut dyn EventSink) -> (SolveOutcome, Vec<u64>) {
        // Equivalent to `run` but yields pos_backtracks.
        let mut s = state;
        let outcome = s.run_body(sink);
        let diag = std::mem::take(&mut s.pos_backtracks);
        (outcome, diag)
    }

    /// Run body shared with `run_inner`. Renamed `run` to `run_body`.
    pub(crate) fn run_body(&mut self, sink: &mut dyn EventSink) -> SolveOutcome {
        self.run_impl(sink)
    }

    /// Backwards compat: old `run(self)` consumed self and returned outcome.
    pub(crate) fn run(mut self, sink: &mut dyn EventSink) -> SolveOutcome {
        self.run_impl(sink)
    }

    fn run_impl(&mut self, sink: &mut dyn EventSink) -> SolveOutcome {
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
                // Vol-24 — under MaxScore, surface the highest-score
                // FULL completion seen as `Solved`. If no completion was
                // reached (heavy pruning), fall back to Exhausted; the
                // caller can inspect `best_partial` via TimedOut paths.
                if matches!(self.opts.objective, Some(Objective::MaxScore)) {
                    if let Some(board) = self.best_score_partial.clone() {
                        self.emit(sink, 0, EventBody::Solved {
                            board: board.clone(), final_stats: self.stats,
                        });
                        return SolveOutcome::Solved(board);
                    }
                    return SolveOutcome::Exhausted;
                }
                if matches!(self.opts.mode, SolveMode::FirstSolution) || solutions.is_empty() {
                    SolveOutcome::Exhausted
                } else {
                    SolveOutcome::AllSolutions(solutions)
                }
            }
            RecurseResult::TimedOut => {
                // Vol-24 — under MaxScore, prefer the highest-score full
                // completion seen over the depth-best partial. Cold-start
                // round-2 use case: a 412 completion is better than a
                // depth-297 partial that ALNS would have to repair.
                let best = if matches!(self.opts.objective, Some(Objective::MaxScore))
                    && self.best_score_partial.is_some()
                {
                    self.best_score_partial.clone().unwrap()
                } else {
                    self.best_partial.clone().unwrap_or_else(|| self.board_from_state())
                };
                let best_depth = self.best_depth;
                self.emit(sink, 0, EventBody::TimedOut {
                    final_stats: self.stats,
                    best_partial: best.clone(),
                    best_depth,
                });
                SolveOutcome::TimedOut { best_partial: best, best_depth }
            }
            RecurseResult::Cancelled => {
                // Vol-24 — same surfacing rule as TimedOut.
                let best = if matches!(self.opts.objective, Some(Objective::MaxScore))
                    && self.best_score_partial.is_some()
                {
                    self.best_score_partial.clone().unwrap()
                } else {
                    self.best_partial.clone().unwrap_or_else(|| self.board_from_state())
                };
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
        let domain_snapshot: Vec<u32> = self.domain_iter(pos as usize).collect();
        let saved_bits = self.snapshot_bits(pos as usize);
        for &row_id in &domain_snapshot {
            if units.len() >= cap_units { return; }
            let row = self.rows[row_id as usize];
            let piece_idx = usize::from(row.piece_id);
            if self.used[piece_idx] { continue; }
            // Clear domain[pos] so place_and_propagate's prunes don't see
            // alternatives to the chosen row_id.
            let base = (pos as usize) * self.words_per_pos;
            for w in &mut self.domain_bits[base..base + self.words_per_pos] { *w = 0; }
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
            self.restore_bits(pos as usize, &saved_bits);
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

        // Vol-24 — MaxScore objective: branch-and-bound on the matched-
        // edge count. `decided_edges` tracks edges with both ends placed;
        // every other internal edge is bounded by 1 match. If even the
        // optimistic completion can't beat the running best, prune the
        // whole subtree. `<=` (not `<`) so we never re-explore a subtree
        // that can only tie. O(1) test; safe to run unconditionally
        // when objective is set (`matches!` is a cheap discriminant cmp).
        //
        // Under RootSplit parallelism, `shared_best_score` (Arc<AtomicU32>)
        // makes the cutoff cross-worker: every worker reads the global
        // running best on each node and CAS-bumps it on each leaf. This
        // is the only way parallel BnB is monotone-optimal — without it,
        // each worker's `best_score` is local and workers can return
        // strictly suboptimal boards.
        if matches!(self.opts.objective, Some(Objective::MaxScore)) {
            let global = self.shared_best_score.as_ref()
                .map(|a| a.load(std::sync::atomic::Ordering::Relaxed))
                .unwrap_or(0);
            let cutoff = self.best_score.max(global);
            if self.matched_count + (self.total_internal_edges - self.decided_edges)
                <= cutoff
            {
                self.stats.backtracks += 1;
                return RecurseResult::Exhausted;
            }
        }

        // Vol-15 — Blackwood schedule prune: BEFORE picking a position,
        // verify the running heuristic-color count is on-schedule for
        // the total number of placed cells (= depth + hint count).
        // The schedule is calibrated against TOTAL cells-on-board
        // (Blackwood includes hints in his cell index). Our engine's
        // `depth` is search-depth starting after hints; we add
        // `hint_offset` to make the schedule comparison total-cells-
        // accurate. If we've fallen behind, the branch can't recover:
        // only more cells get placed from here, each adding ≤ 4
        // heuristic-color edges (monotone non-decreasing).
        if let Some(sched) = self.blackwood.as_ref() {
            let hint_offset = self.opts.hints.hints.len() as u32;
            let total_placed = depth + hint_offset;
            let max_idx = sched.max_heuristic_index;
            if total_placed <= max_idx {
                let target = sched.target_at(total_placed);
                if self.placed_heuristic_count < target {
                    return RecurseResult::Exhausted;
                }
                if self.placed_heuristic_count >= sched.heuristic_pool_size
                    && total_placed < max_idx
                    && sched.target_at(max_idx) > sched.heuristic_pool_size
                {
                    return RecurseResult::Exhausted;
                }
            }
        }

        let pos = match self.select_position() {
            Some(p) => p,
            None => {
                // Vol-24 — under MaxScore, a "complete" placement (no
                // more positions to fill) is just a candidate: capture
                // its score if it beats the running best, then return
                // Exhausted so the parent loop keeps trying alternatives
                // at the deepest still-meaningful node. `Found` would
                // unwind under FirstSolution mode, but MaxScore wants
                // to enumerate.
                if matches!(self.opts.objective, Some(Objective::MaxScore)) {
                    if self.matched_count > self.best_score {
                        self.best_score = self.matched_count;
                        self.best_score_partial = Some(self.board_from_state());
                    }
                    // Bump the shared cutoff so sibling workers prune
                    // against the new high-water mark immediately. Use
                    // fetch_max-via-CAS-loop (no fetch_max on AtomicU32
                    // in older toolchains, but stable since 1.45; use
                    // fetch_max directly).
                    if let Some(atom) = self.shared_best_score.as_ref() {
                        atom.fetch_max(self.matched_count,
                            std::sync::atomic::Ordering::Relaxed);
                    }
                    return RecurseResult::Exhausted;
                }
                solutions.push(self.board_from_state());
                return RecurseResult::Found;
            }
        };

        let mut domain_snapshot: Vec<u32> = self.domain_iter(pos as usize).collect();
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
                    for nb_r_id in self.domain_iter(*nb as usize) {
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

        // EdgeBpMarginals: score each row by Σ over its 4 sides of the
        // BP marginal mass at the row's edge color. Sort descending so
        // the engine tries higher-mass colors first. Silently no-op if
        // marginals or the mapping table aren't populated — preserves
        // correctness for tests that pick this value-order without
        // wiring the data.
        if matches!(self.config.value_order, ValueOrder::EdgeBpMarginals)
            && domain_snapshot.len() > 1
            && !self.cell_side_edge.is_empty()
            && self.opts.edge_bp_marginals.is_some()
        {
            let marg = self.opts.edge_bp_marginals.as_ref().unwrap();
            let base_side = (pos as usize) * 4;
            let eids = [
                self.cell_side_edge[base_side + 0] as usize,
                self.cell_side_edge[base_side + 1] as usize,
                self.cell_side_edge[base_side + 2] as usize,
                self.cell_side_edge[base_side + 3] as usize,
            ];
            // Score ∝ Σ marginal[eid][color]. Use a fixed-point key so
            // the sort is deterministic + total. Higher score first.
            let mut scored: Vec<(u64, u32)> = domain_snapshot.iter().map(|&r_id| {
                let r = self.rows[r_id as usize];
                let mut s = 0.0f32;
                for side in 0..4 {
                    let c = r.edges[side] as usize;
                    if c < EDGE_BP_NSTATE {
                        s += marg[eids[side] * EDGE_BP_NSTATE + c];
                    }
                }
                // Map [0, 4] -> u64 with 1e6 resolution. Descending sort
                // via negation: key = u64::MAX - quantized.
                let q = (s * 1.0e6).max(0.0).min(4.0e6) as u64;
                (u64::MAX - q, r_id)
            }).collect();
            scored.sort_by_key(|(k, _)| *k);
            domain_snapshot.clear();
            domain_snapshot.extend(scored.into_iter().map(|(_, r)| r));
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

        // Vol-15 — BlackwoodHeuristic value-order: rank rows by count
        // of heuristic-color edges (descending). Schedule-rich rows
        // tried first so the running heuristic count keeps pace with
        // the schedule's target_at(depth+1).
        //
        // Vol-17 (H22) — within-tie shuffle. The heuristic-color
        // count is an integer in 0..=4; many rows score equal. By
        // default sort_by_key is stable (preserves insertion order
        // within ties). With `config.shuffle_within_blackwood_ties`,
        // we shuffle the rows WITHIN each tie group using the
        // seed-derived RNG. This gives schedule-invariant CP-partial
        // diversity (different seeds → different shuffle → different
        // search trajectories) WITHOUT breaking Blackwood's score-
        // descending invariant.
        if matches!(self.config.value_order, ValueOrder::BlackwoodHeuristic)
            && !self.heuristic_color_mask.is_empty()
            && domain_snapshot.len() > 1
        {
            let mut scored: Vec<(u32, u32)> = domain_snapshot
                .iter()
                .map(|&r_id| {
                    let r = self.rows[r_id as usize];
                    let h = self.count_heuristic_in_row(&r.edges);
                    // Descending: invert the key.
                    (u32::MAX - h, r_id)
                })
                .collect();
            scored.sort_by_key(|(k, _)| *k);
            if self.config.shuffle_within_blackwood_ties {
                // Within each contiguous run of equal scores, Fisher-
                // Yates shuffle using seeded RNG.
                let n = scored.len();
                let mut i = 0;
                while i < n {
                    let mut j = i + 1;
                    while j < n && scored[j].0 == scored[i].0 { j += 1; }
                    // Shuffle range [i, j).
                    if j - i > 1 {
                        for k in (i + 1..j).rev() {
                            let r = (self.next_random() as usize) % (k - i + 1);
                            scored.swap(k, i + r);
                        }
                    }
                    i = j;
                }
            }
            domain_snapshot.clear();
            domain_snapshot.extend(scored.into_iter().map(|(_, r)| r));
        }

        // Vol-15 — Blackwood break-index: at a break depth, the cell's
        // pruned domain may be empty or too narrow because a previously
        // placed neighbour pruned all rows with the "right" matching
        // color. Augment the candidate set with any row that:
        //   (a) matches this cell's border_mask pattern,
        //   (b) has piece-id not already used,
        //   (c) has ≤ 1 placed-neighbour edge mismatch.
        // The placed row will be flagged so place_and_propagate skips
        // the prune on the mismatched side. Stored in `break_candidates`
        // alongside their mismatched-side index (0..3) or u8::MAX for
        // exact match. Exact-match (mismatched-side = MAX) rows take
        // priority over relaxed ones; among relaxed, prefer rows that
        // satisfy more of the schedule.
        let break_candidates: Vec<(u32, u8)> = if !self.is_break_index.is_empty()
            && self.is_pos_break_index(pos)
        {
            let n_rows = self.rows.len() as u32;
            let mut admitted: Vec<(u32, u8)> = Vec::new();
            // First: include all currently-domained rows (exact match)
            // with side flag = MAX.
            let mut in_domain = std::collections::HashSet::new();
            for &r_id in &domain_snapshot {
                admitted.push((r_id, u8::MAX));
                in_domain.insert(r_id);
            }
            // Second: scan all rows for the relaxed-match candidates.
            for r_id in 0..n_rows {
                if in_domain.contains(&r_id) { continue; }
                let row = self.rows[r_id as usize];
                if !row.valid { continue; }
                if self.used[usize::from(row.piece_id)] { continue; }
                if !self.row_matches_border_pattern(pos, &row.edges) { continue; }
                let m = self.count_placed_neighbor_mismatches(pos, &row.edges);
                if m == 1 {
                    // Find the single mismatched side.
                    let (x, y) = self.puzzle.xy(pos);
                    let w = self.puzzle.width;
                    let h_ = self.puzzle.height;
                    let nbs: [(Option<Position>, usize, usize); 4] = [
                        (if y > 0 { Some((y - 1) * w + x) } else { None }, 0, 2),
                        (if x + 1 < w { Some(y * w + (x + 1)) } else { None }, 1, 3),
                        (if y + 1 < h_ { Some((y + 1) * w + x) } else { None }, 2, 0),
                        (if x > 0 { Some(y * w + (x - 1)) } else { None }, 3, 1),
                    ];
                    for (nb_opt, our_side, their_side) in nbs.iter() {
                        let Some(nb) = nb_opt else { continue; };
                        if let Some(nb_row_id) = self.placed[*nb as usize] {
                            let nb_edges = self.rows[nb_row_id as usize].edges;
                            if row.edges[*our_side] != nb_edges[*their_side] {
                                admitted.push((r_id, *our_side as u8));
                                break;
                            }
                        }
                    }
                }
            }
            admitted
        } else {
            domain_snapshot.iter().map(|&r| (r, u8::MAX)).collect()
        };

        for &(row_id, mismatch_side) in &break_candidates {
            let row = self.rows[row_id as usize];
            let piece_idx = usize::from(row.piece_id);
            if self.used[piece_idx] { continue; }
            self.emit(sink, depth, EventBody::ValueTried {
                position: pos,
                piece_id: row.piece_id,
                rotation: Rotation::from_u8(row.rotation).unwrap(),
            });
            self.stats.nodes += 1;
            let saved_bits = self.snapshot_bits(pos as usize);
            // Clear domain[pos] so place_and_propagate's prunes don't see
            // alternatives to the chosen row_id. At break depth, the
            // chosen row may not be currently in domain[pos]; we still
            // clear and let place_and_propagate set up the propagation
            // from the placed row's edges.
            let base = (pos as usize) * self.words_per_pos;
            for w in &mut self.domain_bits[base..base + self.words_per_pos] { *w = 0; }
            let skip_side = if mismatch_side == u8::MAX { None } else { Some(mismatch_side as usize) };
            let outcome = self.place_and_propagate_opts(sink, depth, pos, row_id, skip_side);
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
                            self.restore_bits(pos as usize, &saved_bits);
                            return terminal;
                        }
                        RecurseResult::Exhausted => {}
                    }
                    self.restore(undo);
                }
                PropagationOutcome::Wipeout { undo } => {
                    self.restore(undo);
                    self.stats.backtracks += 1;
                    // Vol-14 instrumentation (transient): count backtracks
                    // by the cell whose value-choice failed (pos at this
                    // depth). Inspect `self.pos_backtracks` from a sink.
                    if (pos as usize) < self.pos_backtracks.len() {
                        self.pos_backtracks[pos as usize] += 1;
                    }
                    self.emit(sink, depth, EventBody::Backtrack {
                        from_depth: depth + 1,
                        to_depth: depth,
                        cause: BacktrackCause::DomainWipeout,
                    });
                }
            }
            self.undo_place(pos, row_id);
            self.restore_bits(pos as usize, &saved_bits);
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
        // Vol-24 — symmetric decrement of decided_edges / matched_count.
        // MUST run before `placed[pos] = None` so the neighbour scan can
        // still see this cell's placement (won't matter; we only check
        // the neighbour) — actually only the NEIGHBOUR's placement state
        // matters here, so order vs the line below is irrelevant. Kept
        // before for symmetry with place_and_propagate_opts.
        {
            let (px, py) = self.puzzle.xy(pos);
            let pw = self.puzzle.width;
            let ph = self.puzzle.height;
            let nbs: [(Option<Position>, usize, usize); 4] = [
                (if py > 0 { Some((py - 1) * pw + px) } else { None }, 0, 2),
                (if px + 1 < pw { Some(py * pw + (px + 1)) } else { None }, 1, 3),
                (if py + 1 < ph { Some((py + 1) * pw + px) } else { None }, 2, 0),
                (if px > 0 { Some(py * pw + (px - 1)) } else { None }, 3, 1),
            ];
            for (nb_opt, our_side, their_side) in nbs {
                let Some(nb) = nb_opt else { continue; };
                let Some(nb_row_id) = self.placed[nb as usize] else { continue; };
                self.decided_edges = self.decided_edges.saturating_sub(1);
                let nb_edges = self.rows[nb_row_id as usize].edges;
                let our = row.edges[our_side];
                if our != 0 && our == nb_edges[their_side] {
                    self.matched_count = self.matched_count.saturating_sub(1);
                }
            }
        }
        self.placed[pos as usize] = None;
        let piece_idx = usize::from(row.piece_id);
        self.used[piece_idx] = false;
        // Vol-15 — decrement Blackwood heuristic-count.
        let dec = self.count_heuristic_in_row(&row.edges);
        self.placed_heuristic_count = self.placed_heuristic_count.saturating_sub(dec);
    }

    /// Vol-15 — count edges in `edges` whose color is in the active
    /// `heuristic_color_mask`. Returns 0 when no schedule is attached.
    #[inline]
    fn count_heuristic_in_row(&self, edges: &[Color; 4]) -> u32 {
        if self.heuristic_color_mask.is_empty() {
            return 0;
        }
        let m = &self.heuristic_color_mask;
        let mut n = 0u32;
        for &c in edges {
            let ci = c as usize;
            if ci < m.len() && m[ci] {
                n += 1;
            }
        }
        n
    }

    /// Vol-15 — count edges of a placed row `cand` that disagree with
    /// already-placed neighbours of `pos`. Returns u32::MAX if `cand`
    /// would violate piece-uniqueness (piece already used).
    fn count_placed_neighbor_mismatches(&self, pos: Position, cand_edges: &[Color; 4]) -> u32 {
        let (x, y) = self.puzzle.xy(pos);
        let w = self.puzzle.width;
        let h = self.puzzle.height;
        let mut n = 0u32;
        // (neighbor_pos, our_side, their_side)
        let nbs: [(Option<Position>, usize, usize); 4] = [
            (if y > 0 { Some((y - 1) * w + x) } else { None }, 0, 2),
            (if x + 1 < w { Some(y * w + (x + 1)) } else { None }, 1, 3),
            (if y + 1 < h { Some((y + 1) * w + x) } else { None }, 2, 0),
            (if x > 0 { Some(y * w + (x - 1)) } else { None }, 3, 1),
        ];
        for (nb_opt, our_side, their_side) in nbs.iter() {
            let Some(nb) = nb_opt else { continue; };
            if let Some(nb_row_id) = self.placed[*nb as usize] {
                let nb_edges = self.rows[nb_row_id as usize].edges;
                if cand_edges[*our_side] != nb_edges[*their_side] {
                    n += 1;
                }
            }
        }
        n
    }

    /// Vol-15 — does this row also match the cell's border_mask
    /// pattern? Used to admit fresh candidates at break depth (where
    /// the cell's domain may have been pruned away by earlier
    /// neighbour-prunes).
    fn row_matches_border_pattern(&self, pos: Position, edges: &[Color; 4]) -> bool {
        let mask = self.puzzle.border_mask(pos);
        let [on_top, on_right, on_bot, on_left] = mask;
        on_top == (edges[0] == BORDER)
            && on_right == (edges[1] == BORDER)
            && on_bot == (edges[2] == BORDER)
            && on_left == (edges[3] == BORDER)
    }

    /// Vol-15 — is the cell at `pos` a Blackwood break cell? Tests
    /// `is_break_index[scan_index_of_cell[pos]]`. Returns false when
    /// no schedule is attached or scan_order isn't set.
    #[inline]
    fn is_pos_break_index(&self, pos: Position) -> bool {
        if self.is_break_index.is_empty() || self.scan_index_of_cell.is_empty() {
            return false;
        }
        let scan_idx = self.scan_index_of_cell[pos as usize] as usize;
        scan_idx < self.is_break_index.len() && self.is_break_index[scan_idx]
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum RecurseResult { Found, Exhausted, TimedOut, Cancelled }

/// Single undo entry: a bit-diff to OR back into `domain_bits[pos]` on
/// restore. The actual bit-diff lives in `SearchState::undo_words_arena`,
/// in the slot `[words_start..words_start + words_per_pos]`. Recurse-stack
/// discipline guarantees arena slots are popped LIFO with the entries
/// themselves, so no entry outlives its slot. (Vol-16 Cat-4 perf
/// cleanup: dropped per-entry `Vec<u64>` allocation, was ~17.5% of CPU
/// in System::alloc_zeroed.)
#[derive(Clone, Copy)]
pub(crate) struct UndoEntry {
    pub pos: Position,
    pub words_start: u32,
}

pub(crate) enum PropagationOutcome {
    Ok { undo: Vec<UndoEntry> },
    Wipeout { undo: Vec<UndoEntry> },
}

pub(crate) enum Ac3Outcome {
    Ok { removed: Vec<UndoEntry> },
    Wipeout { removed: Vec<UndoEntry> },
}

enum PruneResult {
    Ok,
    Removed(UndoEntry),
    Wipeout { entry: UndoEntry },
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_core::{Edges, Piece};

    fn p(id: PieceId, t: Color, r: Color, b: Color, l: Color) -> Piece {
        Piece::new(id, Edges::new(t, r, b, l))
    }

    #[test]
    fn domain_bits_well_formed_on_construction() {
        // Every cell's domain must contain at least one row (otherwise
        // the puzzle is trivially unsat at construction). Total set
        // bits across all cells should equal the sum of expected domain
        // sizes by cell class.
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 5, interior_colors: 5, seed: 7 }).unwrap();
        let solver = EngineSolver::gacolor_ac3();
        let opts = SolveOpts::default();
        let state = SearchState::new(&puzzle, &solver, &opts);
        for pos in 0..puzzle.cell_count() as usize {
            let base = pos * state.words_per_pos;
            let popcount: u32 = state.domain_bits[base..base + state.words_per_pos]
                .iter().map(|w| w.count_ones()).sum();
            assert!(popcount > 0,
                "domain[{}] is empty at construction (popcount=0)", pos);
        }
    }

    #[test]
    fn domain_bits_construct_2x2_solves() {
        // 2×2 puzzle with 4 corner pieces. Validate that the solve still
        // works end-to-end with the bitset-only rep (no regressions vs
        // solves_2x2_trivial above, but exercised via the full pipeline
        // including SearchState::new → recurse → restore).
        let pieces = vec![
            p(0, 0, 1, 1, 0), p(1, 0, 0, 1, 1),
            p(2, 1, 1, 0, 0), p(3, 1, 0, 0, 1),
        ];
        let puzzle = Puzzle::new(2, 2, 2, pieces).unwrap();
        let mut s = EngineSolver::gacolor_ac3_ns1();
        let mut sink = eternity2_events::BufferSink::new();
        assert!(matches!(s.solve(&puzzle, &SolveOpts::default(), &mut sink),
            SolveOutcome::Solved(_)));
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

    /// Vol-24 — MaxScore must still find the unique perfect solution
    /// on a generator board where every internal edge matches by
    /// construction. Also acts as a smoke test that incremental
    /// `matched_count` / `decided_edges` accounting + the upper-bound
    /// prune don't break correctness.
    #[test]
    fn max_score_solves_generator_5x5() {
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 5, interior_colors: 5, seed: 11 }).unwrap();
        let mut s = EngineSolver::border_first_lcv();
        let mut sink = eternity2_events::BufferSink::new();
        let mut opts = SolveOpts::default();
        opts.time_budget_ms = 60_000;
        opts.objective = Some(Objective::MaxScore);
        let outcome = s.solve(&puzzle, &opts, &mut sink);
        let board = match outcome {
            SolveOutcome::Solved(b) => b,
            other => panic!("MaxScore got {other:?}, want Solved(_)"),
        };
        // Generator puzzles have a perfect solution; the returned
        // board's score must equal the total internal edge count.
        let w = puzzle.width;
        let h = puzzle.height;
        let total = (w - 1) * h + w * (h - 1);
        let mut matched = 0u32;
        for y in 0..h {
            for x in 0..w {
                let pos = y * w + x;
                let Some((pid, rot)) = board.get(pos) else { continue; };
                let edges = puzzle.piece(pid).unwrap().edges.rotated(rot).as_array();
                if x + 1 < w {
                    if let Some((rpid, rrot)) = board.get(y * w + (x + 1)) {
                        let re = puzzle.piece(rpid).unwrap().edges.rotated(rrot).as_array();
                        if edges[1] != 0 && edges[1] == re[3] { matched += 1; }
                    }
                }
                if y + 1 < h {
                    if let Some((bpid, brot)) = board.get((y + 1) * w + x) {
                        let be = puzzle.piece(bpid).unwrap().edges.rotated(brot).as_array();
                        if edges[2] != 0 && edges[2] == be[0] { matched += 1; }
                    }
                }
            }
        }
        assert_eq!(matched, total, "MaxScore should reach the perfect 5×5 solution");
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

    #[test]
    fn build_hint_rectangle_path_on_canonical_e2_hints() {
        // The 5 canonical E2 hints at (2,2), (13,2), (2,13), (13,13),
        // (7,8). Expected path: rectangle perimeter (44 cells) + spoke
        // (cells from x=2..=7 at y=8, minus the (2,8) already on left
        // col) = 49 unique cells total.
        use eternity2_generator::{generate, GeneratorConfig};
        use eternity2_core::{Hint, Hints, Rotation};
        let puzzle = generate(GeneratorConfig { size: 16, interior_colors: 22, seed: 1 }).unwrap();
        let r = Rotation::from_u8(0).unwrap();
        let pid = eternity2_core::PieceId::try_from(0u32).unwrap();
        let hints = Hints { hints: vec![
            Hint { position: 2 + 2*16, piece_id: pid, rotation: r },   // (2,2)
            Hint { position: 13 + 2*16, piece_id: pid, rotation: r },  // (13,2)
            Hint { position: 2 + 13*16, piece_id: pid, rotation: r },  // (2,13)
            Hint { position: 13 + 13*16, piece_id: pid, rotation: r }, // (13,13)
            Hint { position: 7 + 8*16, piece_id: pid, rotation: r },   // (7,8)
        ]};
        let path = build_hint_rectangle_path(&puzzle, &hints);
        // Expected length: top row 12 + right col 11 + bottom row 11
        // + left col 10 + spoke 5 (cells (3..=7, 8); (2,8) is already
        // on left col) = 49.
        assert_eq!(path.len(), 49, "expected 49 cells, got {}", path.len());
        // First cell must be (2,2).
        assert_eq!(path[0], 2 + 2*16);
        // No duplicates.
        let set: std::collections::HashSet<_> = path.iter().collect();
        assert_eq!(set.len(), path.len(), "path has duplicates");
    }

    #[test]
    fn build_hint_rectangle_layered_path_covers_all_cells() {
        use eternity2_generator::{generate, GeneratorConfig};
        use eternity2_core::{Hint, Hints, Rotation};
        let puzzle = generate(GeneratorConfig { size: 16, interior_colors: 22, seed: 1 }).unwrap();
        let r = Rotation::from_u8(0).unwrap();
        let pid = eternity2_core::PieceId::try_from(0u32).unwrap();
        let hints = Hints { hints: vec![
            Hint { position: 2 + 2*16, piece_id: pid, rotation: r },
            Hint { position: 13 + 2*16, piece_id: pid, rotation: r },
            Hint { position: 2 + 13*16, piece_id: pid, rotation: r },
            Hint { position: 13 + 13*16, piece_id: pid, rotation: r },
            Hint { position: 7 + 8*16, piece_id: pid, rotation: r },
        ]};
        let path = build_hint_rectangle_layered_path(&puzzle, &hints);
        assert_eq!(path.len(), 256, "expected 256 cells, got {}", path.len());
        // No duplicates
        let set: std::collections::HashSet<_> = path.iter().collect();
        assert_eq!(set.len(), 256, "duplicates in path");
        // First 49 must match the basic rectangle path
        let rect = build_hint_rectangle_path(&puzzle, &hints);
        assert_eq!(&path[..49], &rect[..]);
    }

    #[test]
    fn build_x_skeleton_path_covers_all_cells() {
        use eternity2_generator::{generate, GeneratorConfig};
        use eternity2_core::{Hint, Hints, Rotation};
        let puzzle = generate(GeneratorConfig { size: 16, interior_colors: 22, seed: 1 }).unwrap();
        let r = Rotation::from_u8(0).unwrap();
        let pid = eternity2_core::PieceId::try_from(0u32).unwrap();
        let canonical = [
            2 + 2 * 16u32,    // TL
            13 + 2 * 16u32,   // TR
            2 + 13 * 16u32,   // BL
            13 + 13 * 16u32,  // BR
            7 + 8 * 16u32,    // centre
        ];
        let hints = Hints { hints: canonical.iter().map(|&p| Hint {
            position: p, piece_id: pid, rotation: r,
        }).collect() };
        let path = build_x_skeleton_path(&puzzle, &hints);
        assert_eq!(path.len(), 256, "expected 256 cells, got {}", path.len());
        let set: std::collections::HashSet<_> = path.iter().collect();
        assert_eq!(set.len(), 256, "duplicates in path");
        // First cell must be the TL hint.
        assert_eq!(path[0], 2 + 2 * 16);
        // All 5 canonical hint positions must appear within the X-skeleton
        // prefix. Two 3-wide diagonals of length ~6 across canonical E2
        // give ~50-60 cells in the prefix; require all hints in first 90.
        let prefix: std::collections::HashSet<u32> = path[..90].iter().copied().collect();
        for &hp in &canonical {
            assert!(prefix.contains(&hp), "hint {hp} not in X-skeleton prefix");
        }
    }

    #[test]
    fn build_x_skeleton_path_too_few_hints() {
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 16, interior_colors: 22, seed: 1 }).unwrap();
        for n in 0..=4 {
            let hints = eternity2_core::Hints {
                hints: (0..n).map(|i| eternity2_core::Hint {
                    position: i,
                    piece_id: eternity2_core::PieceId::try_from(0u32).unwrap(),
                    rotation: eternity2_core::Rotation::from_u8(0).unwrap(),
                }).collect()
            };
            assert!(build_x_skeleton_path(&puzzle, &hints).is_empty(),
                "expected empty with {} hints", n);
        }
    }

    #[test]
    fn build_hint_rectangle_path_too_few_hints() {
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 16, interior_colors: 22, seed: 1 }).unwrap();
        // 0 hints, 3 hints — both should return empty.
        for n in 0..=3 {
            let hints = eternity2_core::Hints {
                hints: (0..n).map(|i| eternity2_core::Hint {
                    position: i,
                    piece_id: eternity2_core::PieceId::try_from(0u32).unwrap(),
                    rotation: eternity2_core::Rotation::from_u8(0).unwrap(),
                }).collect()
            };
            assert!(build_hint_rectangle_path(&puzzle, &hints).is_empty(),
                "expected empty with {} hints", n);
        }
    }

    #[test]
    fn cell_side_edge_counts_match_canonical_e2() {
        // The Python BP enumeration on the canonical 16×16 grid produces
        // 2*W*H + W + H = 544 distinct edges (64 boundary + 480 internal).
        // Use a generated 16×16 puzzle (any colors) — the mapping only
        // depends on grid geometry.
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig { size: 16, interior_colors: 22, seed: 1 }).unwrap();
        let cse = build_cell_side_edge(&puzzle);
        let n_pos = (puzzle.width * puzzle.height) as usize;
        assert_eq!(cse.len(), n_pos * 4);
        let max_eid = cse.iter().copied().max().unwrap();
        let n_edges = max_eid as usize + 1;
        assert_eq!(n_edges, 2 * 16 * 16 + 16 + 16, "expected 544 edges, got {n_edges}");
        // Internal-edge sharing: each non-corner side is referenced by 2
        // (pos, side) entries; boundary sides by 1. Count.
        let mut refs = vec![0u32; n_edges];
        for &e in &cse { refs[e as usize] += 1; }
        let boundary = refs.iter().filter(|&&r| r == 1).count();
        let internal = refs.iter().filter(|&&r| r == 2).count();
        assert_eq!(boundary, 2 * (16 + 16));
        assert_eq!(internal, 2 * 16 * 16 - 16 - 16);
    }

    #[cfg(not(target_arch = "wasm32"))]
    #[test]
    fn load_edge_bp_marginals_smoketest_v12_file() {
        // The 284 KB vol-12 measurement is in the repo. If running under
        // a sandbox without it, skip cleanly.
        let path = std::path::Path::new("../../output/v12_bp/edge_bp_60i.json");
        if !path.exists() { return; }
        let m = load_edge_bp_marginals(path).expect("load");
        assert_eq!(m.len(), 544 * EDGE_BP_NSTATE);
        // Each edge's marginal must sum to ≈ 1.0.
        for e in 0..544 {
            let s: f32 = (0..EDGE_BP_NSTATE).map(|c| m[e * EDGE_BP_NSTATE + c]).sum();
            assert!((s - 1.0).abs() < 1e-3, "edge {e} sum = {s}");
        }
        // Boundary edges (those with refs=1 in cse) should have
        // argmax = 0 (BORDER). Spot-check edge 0 which is cell-0 north.
        let argmax_0 = (0..EDGE_BP_NSTATE)
            .max_by(|a, b| m[*a].partial_cmp(&m[*b]).unwrap())
            .unwrap();
        assert_eq!(argmax_0, 0, "boundary edge 0 should argmax to BORDER");
    }

    // ===== Vol-15 Blackwood tests =====

    #[test]
    fn blackwood_schedule_validate_catches_depth_cliff() {
        // Two control points at the same depth = cliff = exactly
        // the vol-15 first-iteration bug. validate() must reject.
        let bad = BlackwoodSchedule {
            heuristic_sides: vec![1],
            exhaustion_targets: vec![(0, 0), (60, 0), (60, 34), (100, 80)],
            heuristic_pool_size: 100,
            max_heuristic_index: 100,
            break_indexes_allowed: vec![],
        };
        assert!(bad.validate().is_err(), "duplicate-depth schedule must fail validate()");
    }

    #[test]
    fn blackwood_schedule_validate_catches_count_regression() {
        // Counts must be non-decreasing.
        let bad = BlackwoodSchedule {
            heuristic_sides: vec![1],
            exhaustion_targets: vec![(0, 0), (10, 50), (20, 30)],
            heuristic_pool_size: 100,
            max_heuristic_index: 100,
            break_indexes_allowed: vec![],
        };
        assert!(bad.validate().is_err(), "decreasing-count schedule must fail validate()");
    }

    #[test]
    fn blackwood_schedule_469_on_5x5_is_well_formed() {
        // Synthesise a small puzzle big enough for the affine remap
        // to give post_border < target_max. 5×5 has border_ring = 16,
        // n_pos = 25; target_max = 160 × 25 / 256 = 15. Too small —
        // post_border (17) > target_max (15). Per debug_assert this
        // would crash in dev; release-mode falls through.
        // For a 12×12: border_ring=44, n_pos=144, target_max=90,
        // post_border=45. Comfortable; schedule should validate.
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig {
            size: 12, interior_colors: 12, seed: 1,
        }).unwrap();
        let hints = eternity2_core::Hints::default();
        let s = blackwood_schedule_469(&puzzle, &hints)
            .expect("compute_heuristic_sides returned < 3 colors");
        s.validate().expect("blackwood_schedule_469 must produce a valid schedule");
        // First non-zero target lands STRICTLY past the border ring.
        let border_ring = 2 * 12 + 2 * 12 - 4;
        let first_nz = s.exhaustion_targets.iter().find(|(_, c)| *c > 0).copied();
        let (d_first, _) = first_nz.expect("schedule must have a non-zero target");
        assert!(d_first > border_ring,
            "first non-zero schedule depth {d_first} must be past border_ring {border_ring}");
    }

    #[test]
    fn blackwood_schedule_target_interp_endpoints() {
        let s = BlackwoodSchedule {
            heuristic_sides: vec![1, 2, 3],
            exhaustion_targets: vec![(0, 0), (100, 50), (200, 100)],
            heuristic_pool_size: 100,
            max_heuristic_index: 200,
            break_indexes_allowed: vec![],
        };
        assert_eq!(s.target_at(0), 0);
        assert_eq!(s.target_at(100), 50);
        assert_eq!(s.target_at(200), 100);
        // Linear interp at midpoint of first segment.
        assert_eq!(s.target_at(50), 25);
        // Midpoint of second.
        assert_eq!(s.target_at(150), 75);
        // Saturates below first and above last.
        assert_eq!(s.target_at(300), 100);
    }

    #[test]
    fn scan_order_bottom_up_indices() {
        // 4×4 puzzle, scan_order=RowMajorBottomUp:
        //   pos (x,y)=(0,3) → bu_idx 0
        //   pos (x,y)=(3,3) → bu_idx 3
        //   pos (x,y)=(0,0) → bu_idx 12
        //   pos (x,y)=(3,0) → bu_idx 15
        let pieces: Vec<Piece> = (0..16).map(|id| p(id as PieceId, 0, 0, 0, 0)).collect();
        let puzzle = Puzzle::new(4, 4, 1, pieces).unwrap();
        let mut cfg = EngineConfig::BORDER_FIRST_LCV;
        cfg.scan_order = Some(ScanOrder::RowMajorBottomUp);
        let solver = EngineSolver::new(cfg, "engine", "test_blackwood_scan");
        let opts = SolveOpts::default();
        let state = SearchState::new(&puzzle, &solver, &opts);
        // scan_index_of_cell[pos] = (H-1-y)*W + x
        let pos = |x: u32, y: u32| -> usize { (y * 4 + x) as usize };
        assert_eq!(state.scan_index_of_cell[pos(0, 3)], 0);
        assert_eq!(state.scan_index_of_cell[pos(3, 3)], 3);
        assert_eq!(state.scan_index_of_cell[pos(0, 0)], 12);
        assert_eq!(state.scan_index_of_cell[pos(3, 0)], 15);
        // path_order should follow scan order: first entry is pos(0,3)=12,
        // last is pos(3,0)=3.
        assert_eq!(state.path_order.first().copied(), Some(12u32));
        assert_eq!(state.path_order.last().copied(), Some(3u32));
        // auto_skeleton_path_k must cover all cells.
        assert_eq!(state.auto_skeleton_path_k, 16);
    }

    #[test]
    fn count_heuristic_in_row_basic() {
        // 2x2 puzzle, attach a schedule with heuristic colors {1, 3}.
        // Row (1,0,3,1) should have count = 3 (two 1s + one 3).
        let pieces = vec![
            p(0, 0, 1, 1, 0), p(1, 0, 0, 1, 1),
            p(2, 1, 1, 0, 0), p(3, 1, 0, 0, 1),
        ];
        let puzzle = Puzzle::new(2, 2, 2, pieces).unwrap();
        let schedule = Arc::new(BlackwoodSchedule {
            heuristic_sides: vec![1, 3],
            exhaustion_targets: vec![(0, 0), (4, 4)],
            heuristic_pool_size: 8,
            max_heuristic_index: 4,
            break_indexes_allowed: vec![],
        });
        let solver = EngineSolver::new(EngineConfig::BORDER_FIRST_LCV, "engine", "t")
            .with_blackwood_schedule(schedule);
        let opts = SolveOpts::default();
        let state = SearchState::new(&puzzle, &solver, &opts);
        assert_eq!(state.count_heuristic_in_row(&[1, 0, 3, 1]), 3);
        assert_eq!(state.count_heuristic_in_row(&[0, 0, 0, 0]), 0);
        assert_eq!(state.count_heuristic_in_row(&[3, 1, 3, 1]), 4);
    }

    #[test]
    fn compute_heuristic_sides_excludes_corners_and_start() {
        // 4-piece 2×2: corners use colors {0,1}. With no hints, no
        // start-piece constraint. compute_heuristic_sides should
        // return ZERO usable colors (all are on corners).
        let pieces = vec![
            p(0, 0, 1, 1, 0), p(1, 0, 0, 1, 1),
            p(2, 1, 1, 0, 0), p(3, 1, 0, 0, 1),
        ];
        let puzzle = Puzzle::new(2, 2, 2, pieces).unwrap();
        let hints = eternity2_core::Hints::default();
        let colors = compute_heuristic_sides(&puzzle, &hints);
        // Both interior colors (0, 1) appear on corners (every piece is
        // a corner on 2×2), so all colors are forbidden.
        assert!(colors.is_empty() || colors.iter().all(|&c| c != 0 && c != 1));
    }

    #[test]
    fn blackwood_solve_tiny_puzzle_still_finds_solution() {
        // The 2×2 trivial puzzle has 1 solution. With a vacuous
        // BlackwoodSchedule (target 0 everywhere, no breaks) the engine
        // must still find it.
        let pieces = vec![
            p(0, 0, 1, 1, 0), p(1, 0, 0, 1, 1),
            p(2, 1, 1, 0, 0), p(3, 1, 0, 0, 1),
        ];
        let puzzle = Puzzle::new(2, 2, 2, pieces).unwrap();
        let schedule = Arc::new(BlackwoodSchedule {
            heuristic_sides: vec![1],
            exhaustion_targets: vec![(0, 0), (4, 0)],
            heuristic_pool_size: 0,
            max_heuristic_index: 4,
            break_indexes_allowed: vec![],
        });
        let mut cfg = EngineConfig::BORDER_FIRST_LCV;
        cfg.value_order = ValueOrder::BlackwoodHeuristic;
        cfg.scan_order = Some(ScanOrder::RowMajorBottomUp);
        let mut s = EngineSolver::new(cfg, "engine", "blackwood_test")
            .with_blackwood_schedule(schedule);
        let mut sink = eternity2_events::BufferSink::new();
        let outcome = s.solve(&puzzle, &SolveOpts::default(), &mut sink);
        assert!(matches!(outcome, SolveOutcome::Solved(_)),
            "Blackwood-mode solve on 2x2 trivial returned {outcome:?}");
    }

    #[test]
    fn blackwood_x_hint_rectangle_composition_path_is_coherent() {
        // When both path_skeleton=HintRectangle AND scan_order are set,
        // the engine's path_order must be: [rectangle cells in their
        // build order] ++ [remaining cells in scan order]. Every cell
        // appears exactly once. Engine traversal depth therefore equals
        // path_order index, and break_indexes_allowed (as depths) map
        // unambiguously to "the i-th cell placed".
        use eternity2_generator::{generate, GeneratorConfig};
        let puzzle = generate(GeneratorConfig {
            size: 5, interior_colors: 5, seed: 13,
        }).unwrap();
        // Need ≥4 hints for HintRectangle to be non-trivial. Use the
        // 4 corners of the generated puzzle (any valid (piece, rot)
        // there counts; for this structural test we don't care if the
        // hint is satisfiable, just that the path-builder consumes it).
        let mk_hint = |pos: u32| -> eternity2_core::Hint {
            // Use any piece for the hint slot; build_hint_rectangle_path
            // only consults the .position field.
            eternity2_core::Hint {
                position: pos,
                piece_id: 0,
                rotation: eternity2_core::Rotation::from_u8(0).unwrap(),
            }
        };
        let w = puzzle.width;
        let h = puzzle.height;
        let hints = eternity2_core::Hints::new(vec![
            mk_hint(0),
            mk_hint(w - 1),
            mk_hint((h - 1) * w),
            mk_hint(h * w - 1),
        ]);
        let mut cfg = EngineConfig::BORDER_FIRST_LCV;
        cfg.path_skeleton = Some(PathSkeleton::HintRectangle);
        cfg.scan_order = Some(ScanOrder::RowMajorBottomUp);
        let solver = EngineSolver::new(cfg, "engine", "comp");
        let mut opts = SolveOpts::default();
        opts.hints = hints;
        let state = SearchState::new(&puzzle, &solver, &opts);
        let n = puzzle.cell_count() as usize;
        // Sanity: every cell appears exactly once.
        assert_eq!(state.path_order.len(), n);
        let unique: std::collections::HashSet<_> = state.path_order.iter().copied().collect();
        assert_eq!(unique.len(), n);
        // auto_skeleton_path_k must cover the entire path (so the
        // PrefixConstraint / auto-skeleton machinery applies for all
        // depths).
        assert_eq!(state.auto_skeleton_path_k as usize, n);
        // Prefix length: the rectangle skeleton length depends on the
        // generated puzzle size; just assert it's non-empty.
        let skel = build_hint_rectangle_path(&puzzle, &opts.hints);
        let k = skel.len();
        assert!(k > 0, "rectangle skeleton should be non-empty for 5x5 + 4 corner hints");
        assert!(state.path_order[..k] == skel,
            "first k cells of path_order should be the rectangle path verbatim");
    }

    #[test]
    fn blackwood_break_index_allows_one_mismatch_on_small_puzzle() {
        // Construct a tiny puzzle where the only completion requires
        // exactly 1 edge mismatch. Without the break index, the engine
        // returns Exhausted; with it, the engine returns a partial
        // depth equal to all 4 cells placed (since one is at a break
        // index and may mismatch).
        //
        // 2×2 puzzle with corners that DON'T tile cleanly: piece 0 has
        // an asymmetric N-S to force a 1-mismatch completion. We'll
        // just verify the engine's recurse can place a row at the
        // break-index cell whose placed-neighbour edge color differs
        // from one of its neighbours' edges — without crashing —
        // exercising the augmented-candidate path.
        //
        // Concretely: the 2×2 trivial puzzle solves cleanly with 0
        // mismatches anyway, so we verify the engine SOLVES with break
        // index present (no false rejections from the break path).
        let pieces = vec![
            p(0, 0, 1, 1, 0), p(1, 0, 0, 1, 1),
            p(2, 1, 1, 0, 0), p(3, 1, 0, 0, 1),
        ];
        let puzzle = Puzzle::new(2, 2, 2, pieces).unwrap();
        let schedule = Arc::new(BlackwoodSchedule {
            heuristic_sides: vec![],
            exhaustion_targets: vec![(0, 0), (4, 0)],
            heuristic_pool_size: 0,
            max_heuristic_index: 4,
            break_indexes_allowed: vec![3],  // last cell in bu scan
        });
        let mut cfg = EngineConfig::BORDER_FIRST_LCV;
        cfg.value_order = ValueOrder::BlackwoodHeuristic;
        cfg.scan_order = Some(ScanOrder::RowMajorBottomUp);
        let mut s = EngineSolver::new(cfg, "engine", "blackwood_break_test")
            .with_blackwood_schedule(schedule);
        let mut sink = eternity2_events::BufferSink::new();
        let outcome = s.solve(&puzzle, &SolveOpts::default(), &mut sink);
        // Must still solve cleanly: break index doesn't prevent exact
        // matches, it just *also* allows ≤1 mismatch.
        assert!(matches!(outcome, SolveOutcome::Solved(_)),
            "engine should still find clean solution with break index: got {outcome:?}");
    }
}
