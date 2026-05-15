// CP-with-LP-UB-pruning: backtracking border-placement search that
// prunes by LP relaxation upper-bound at each placement.
//
// Goal: efficiently find borders with LP UB above some threshold T,
// without enumerating the full 56! perimeter space.
//
// See vault/concepts/cp-with-lp-ub-pruning.md for the design.

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_core::{Board, Position, Puzzle};

/// User-facing options for the search.
#[derive(Debug, Clone)]
pub struct CpLpSearchOpts {
    /// Prune branches with LP UB < this threshold.
    pub threshold_ub: f64,
    /// Below this depth, use cheap pruning only (color count, Hall).
    pub phase1_depth_max: u32,
    /// At or below this depth, use reduced LP (B-B + B-I only).
    pub phase2_depth_max: u32,
    /// Total wall-clock budget.
    pub time_budget_secs: f64,
    pub threads: u32,
    pub save_dir: PathBuf,
}

impl Default for CpLpSearchOpts {
    fn default() -> Self {
        Self {
            threshold_ub: 478.0,
            phase1_depth_max: 30,
            phase2_depth_max: 55,
            time_budget_secs: 3600.0,
            threads: 8,
            save_dir: PathBuf::from("output/cp_lp_search"),
        }
    }
}

/// Result of a search run.
#[derive(Debug, Clone, Default)]
pub struct CpLpResult {
    pub n_explored: u64,
    pub n_pruned_cheap: u64,
    pub n_pruned_reduced_lp: u64,
    pub n_pruned_full_lp: u64,
    pub n_leaves_kept: u64,
    pub best_lp_ub_seen: f64,
    pub elapsed_secs: f64,
}

/// Placeholder: not yet implemented.
pub fn run_cp_lp_search(_puzzle: &Puzzle, _opts: &CpLpSearchOpts) -> Result<CpLpResult, String> {
    Err("cp-lp-search: implementation in progress".to_string())
}

/// Compute a *partial* LP UB given a partially-placed border board.
/// `placed` is the cells already committed. Empty cells are allowed.
/// Returns the LP optimum value (sum over y vars) given the partial state.
pub fn partial_lp_ub(_puzzle: &Puzzle, _board: &Board, _placed: &[Position])
    -> Result<f64, String>
{
    Err("partial_lp_ub: not yet implemented".to_string())
}

/// Cheap lower-bound check: returns false if it can prove LP UB < threshold.
/// Currently a placeholder that always returns true (no pruning).
pub fn cheap_lb_passes(_puzzle: &Puzzle, _board: &Board, _placed: &[Position],
                       _threshold: f64) -> bool {
    true
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn skeleton_builds() {
        let _opts = CpLpSearchOpts::default();
        assert!(true);
    }
}
