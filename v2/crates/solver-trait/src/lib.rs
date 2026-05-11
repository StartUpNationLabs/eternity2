#![forbid(unsafe_code)]

use eternity2_core::{Board, Hints, PathPolicy, Puzzle};
use eternity2_events::EventSink;

#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

// Stable string identifiers. New solvers opt in by adding registry entries
// (see V2_DESIGN.md §"Resolved design decisions"). Strings are cheap to
// match in non-hot paths and avoid proto/registry coupling.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct SolverId(pub String);

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct HeuristicProfile(pub String);

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub enum SolveMode {
    FirstSolution,
    AllSolutions,
    CountOnly,
}

#[derive(Debug, Clone)]
pub struct SolveOpts {
    pub mode: SolveMode,
    pub path: Vec<u32>,
    pub path_policy: PathPolicy,
    pub hints: Hints,
    pub seed: u64,
    pub time_budget_ms: u64,       // 0 = unlimited
    pub max_solutions: u32,        // 0 = unlimited (AllSolutions only)
    pub solver_run_id: u64,
}

impl Default for SolveOpts {
    fn default() -> Self {
        Self {
            mode: SolveMode::FirstSolution,
            path: Vec::new(),
            path_policy: PathPolicy::Ignored,
            hints: Hints::default(),
            seed: 0,
            time_budget_ms: 0,
            max_solutions: 0,
            solver_run_id: 0,
        }
    }
}

#[derive(Debug, Clone)]
pub enum SolveOutcome {
    Solved(Board),
    AllSolutions(Vec<Board>),
    Exhausted,
    TimedOut { best_partial: Board, best_depth: u32 },
    Cancelled { best_partial: Board, best_depth: u32, solutions_so_far: Vec<Board> },
    Error(String),
}

pub trait Solver: Send {
    fn id(&self) -> SolverId;
    fn heuristic_profile(&self) -> HeuristicProfile;

    fn supports_path_policy(&self, policy: &PathPolicy) -> bool;

    fn solve(
        &mut self,
        puzzle: &Puzzle,
        opts: &SolveOpts,
        sink: &mut dyn EventSink,
    ) -> SolveOutcome;
}
