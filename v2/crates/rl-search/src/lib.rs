// RL self-play for Eternity II value-ordering.
//
// vol-48 design: see vault/concepts/rl-self-play-value-order.md.
//
// This crate provides:
// - Episode runner: invokes the engine with a custom value-order policy
//   and captures the trajectory (states, actions, reward).
// - Replay buffer: collected episodes for offline training.
// - Policy interface: trait for value-order policies (random, MRV,
//   learned, etc.).
// - Trainer (later phase): REINFORCE / PPO updates from collected
//   trajectories.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

use eternity2_core::{PieceId, Position, Rotation};

/// A single decision the agent made during an episode.
///
/// The `cell` is the variable chosen by the variable-order policy
/// (MRV/AC3/whatever the engine does). The agent's policy CHOSE
/// among the `candidates` to place `(chosen_piece, chosen_rot)`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EpisodeStep {
    pub depth: u32,
    pub cell: Position,
    /// List of (piece_id, rotation) that were valid at decision time.
    pub candidates: Vec<(PieceId, u8)>,
    /// Index into `candidates` of the action taken.
    pub action_index: u32,
    /// The chosen (piece, rotation).
    pub chosen_piece: PieceId,
    pub chosen_rot: u8,
    /// Optional features used at decision time (filled by learned policies).
    pub features: Option<Vec<f32>>,
    /// Log-probability of the chosen action under the policy (for REINFORCE).
    pub log_prob: Option<f32>,
}

/// One complete episode (one CP search attempt).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Episode {
    /// Random seed used for the episode.
    pub seed: u64,
    /// Policy name (e.g., "random", "mrv-baseline", "learned-v1").
    pub policy: String,
    /// All decisions taken.
    pub steps: Vec<EpisodeStep>,
    /// Final outcome.
    pub outcome: EpisodeOutcome,
    /// Wall-clock time for the whole episode.
    pub elapsed_secs: f32,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum EpisodeOutcome {
    /// Found a solution at depth N.
    Solved { depth: u32, matched: u32 },
    /// Hit time/node budget without solving. Best-partial reached.
    TimedOut { best_depth: u32, best_matched: u32 },
    /// Exhausted search without solving.
    Exhausted { best_depth: u32, best_matched: u32 },
}

impl EpisodeOutcome {
    pub fn best_depth(&self) -> u32 {
        match self {
            EpisodeOutcome::Solved { depth, .. } => *depth,
            EpisodeOutcome::TimedOut { best_depth, .. } => *best_depth,
            EpisodeOutcome::Exhausted { best_depth, .. } => *best_depth,
        }
    }
    pub fn best_matched(&self) -> u32 {
        match self {
            EpisodeOutcome::Solved { matched, .. } => *matched,
            EpisodeOutcome::TimedOut { best_matched, .. } => *best_matched,
            EpisodeOutcome::Exhausted { best_matched, .. } => *best_matched,
        }
    }
}

/// Reward computed from an episode.
pub fn compute_reward_depth(ep: &Episode) -> f32 {
    ep.outcome.best_depth() as f32
}

pub fn compute_reward_score(ep: &Episode) -> f32 {
    ep.outcome.best_matched() as f32
}

/// A policy that the engine can call to choose among candidates at each cell.
pub trait ValueOrderPolicy: Send {
    /// Given a (cell, candidates) decision, return the index of the
    /// chosen candidate AND its log-probability under the policy.
    fn choose(
        &mut self,
        cell: Position,
        candidates: &[(PieceId, Rotation)],
        features: Option<&[f32]>,
    ) -> (u32, f32);
}

/// Simple uniform-random policy (for baseline + early scaffolding).
pub struct RandomPolicy {
    state: u64,
}

impl RandomPolicy {
    pub fn new(seed: u64) -> Self {
        Self { state: seed.max(1) }
    }
    fn next(&mut self) -> u64 {
        let mut s = self.state;
        s ^= s << 13;
        s ^= s >> 7;
        s ^= s << 17;
        self.state = s;
        s
    }
}

impl ValueOrderPolicy for RandomPolicy {
    fn choose(
        &mut self,
        _cell: Position,
        candidates: &[(PieceId, Rotation)],
        _features: Option<&[f32]>,
    ) -> (u32, f32) {
        let idx = (self.next() as usize) % candidates.len();
        let p = 1.0_f32 / (candidates.len() as f32);
        (idx as u32, p.ln())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn random_policy_choice_in_range() {
        let mut pol = RandomPolicy::new(42);
        let cands: Vec<(PieceId, Rotation)> = (0..5)
            .map(|i| (i as PieceId, Rotation::R0))
            .collect();
        for _ in 0..100 {
            let (idx, _lp) = pol.choose(0, &cands, None);
            assert!((idx as usize) < cands.len());
        }
    }

    #[test]
    fn outcome_accessors() {
        let o = EpisodeOutcome::Solved { depth: 256, matched: 480 };
        assert_eq!(o.best_depth(), 256);
        assert_eq!(o.best_matched(), 480);
    }
}
