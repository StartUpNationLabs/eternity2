// Parallel Tempering (Replica Exchange MCMC) for Eternity II local search.
//
// Why this exists: vanilla SA on the official Eternity II saturates at
// ~65% matched edges after CP seeding. The plateau is a *landscape*
// problem, not a throughput problem — single-temperature SA can't cross
// the energy barriers between local optima. PT addresses this by running
// multiple chains at different temperatures and periodically swapping
// configurations between adjacent chains. The hot chains tunnel through
// barriers; the cold chains exploit. Swaps move good configurations
// downward in temperature, and trapped configurations upward where they
// can escape.
//
// To my knowledge no published E2 solver uses PT. The community's
// metaheuristic work (Wauters 2010, Verhaard 2008) all uses single-T SA
// or single-T with restarts. PT is well-studied in statistical physics
// for spin glasses (Hukushima-Nemoto 1996, Marinari-Parisi 1992) where
// it routinely beats single-T methods on hard landscapes.
//
// Algorithm:
//   - N replicas at temperatures T_1 < T_2 < ... < T_N (geometric ladder).
//   - Each round: every replica runs `inner_iters` independent SA steps
//     at its own fixed temperature (parallel via rayon).
//   - After a round: propose swap of replicas i and i+1 with Metropolis
//     acceptance prob = min(1, exp[(score_i - score_{i+1}) * (1/T_i - 1/T_{i+1})]).
//   - Repeat until time budget exhausted or perfect score reached.
//   - Track best score across all replicas; output that as the result.

use std::time::Instant;

use eternity2_core::{Board, Position, Puzzle};

use crate::{
    houdayer::{apply_proposal, enumerate_proposals},
    repair::{repair_region, worst_region},
    run_sa_steps_fixed_temp, RngHandle, SaOutcome, StateRef,
};

/// Configuration for parallel tempering.
#[derive(Debug, Clone)]
pub struct PtConfig {
    /// Number of replicas (parallel chains).
    pub n_replicas: usize,
    /// Lowest temperature in the ladder.
    pub t_min: f64,
    /// Highest temperature in the ladder.
    pub t_max: f64,
    /// SA iterations per replica per round.
    pub inner_iters: u64,
    /// Hard cap on total rounds (0 = unlimited).
    pub max_rounds: u64,
    /// Wall-clock budget in milliseconds (0 = unlimited).
    pub time_budget_ms: u64,
    /// PRNG seed (used as base; per-replica seed = seed + replica_idx).
    pub seed: u64,
    /// If true, emit per-round progress logs to stderr.
    pub verbose: bool,
    /// If true, replicas start from a greedy fill of the CP partial
    /// (good for hybrid CP→PT). If false, random fill (good when
    /// you want each replica to start from a different basin).
    pub greedy_fill: bool,
    /// If `greedy_fill` is true, only the FIRST replica gets the pure
    /// greedy fill; remaining replicas get a stochastic greedy fill
    /// (still good, but with diversification via small random
    /// perturbations). For now we use the same greedy fill for all
    /// (deterministic given seed), trading off some chain diversity
    /// for guaranteed good starting score.
    pub diversify_fill: bool,
    /// If > 0, every `repair_every` rounds, do a mini-CP repair on
    /// the cold chain (find worst k×k region, re-solve with CP).
    /// Set to 0 to disable.
    pub repair_every: u64,
    /// Size of the region (k×k) to attempt mini-CP repair on.
    pub repair_k: u32,
    /// Wall-clock budget for each mini-CP repair attempt (milliseconds).
    pub repair_budget_ms: u64,
    /// If > 0, every `kick_every` rounds, perturb the cold chain by
    /// performing N random swaps unconditionally (basin hopping).
    /// 0 disables.
    pub kick_every: u64,
    /// Number of random swap perturbations per kick.
    pub kick_n_swaps: u32,
    /// Cell positions that must NEVER move (piece and rotation preserved).
    /// Used to honour the official E2 hint pieces during local search. Empty
    /// by default — solver runs unconstrained.
    pub pinned_positions: Vec<Position>,
    /// If > 0, every `houdayer_every` rounds, apply Houdayer cluster moves
    /// between adjacent replica pairs. The cluster move identifies
    /// connected disagreement components (cells where replica i and i+1
    /// disagree), checks they are piece-multiset-swappable, and unconditionally
    /// swaps the contents. Joint score is preserved exactly (microcanonical);
    /// the move's value is teleporting both replicas to a different basin
    /// that single-cell moves cannot reach. 0 disables.
    pub houdayer_every: u64,
    /// Skip Houdayer components larger than this size (cells). Large
    /// components are massive perturbations; small components are localized
    /// rearrangements. Defaults to 20 (= ~8% of board).
    pub houdayer_max_component: usize,
    /// Skip Houdayer components smaller than this size. Components of size
    /// < 2 are degenerate. Defaults to 4.
    pub houdayer_min_component: usize,
}

impl Default for PtConfig {
    fn default() -> Self {
        Self {
            n_replicas: 8,
            t_min: 0.05,
            t_max: 2.0,
            inner_iters: 100_000,
            max_rounds: 0,
            time_budget_ms: 0,
            seed: 0xE2_E2_E2_E2,
            verbose: false,
            greedy_fill: true,
            diversify_fill: false,
            repair_every: 0,
            repair_k: 4,
            repair_budget_ms: 200,
            kick_every: 0,
            kick_n_swaps: 20,
            pinned_positions: Vec::new(),
            houdayer_every: 0,
            houdayer_max_component: 20,
            houdayer_min_component: 4,
        }
    }
}

/// Statistics across the PT run.
#[derive(Debug, Clone)]
pub struct PtStats {
    pub rounds: u64,
    pub total_swap_proposals: u64,
    pub total_swap_accepts: u64,
    /// Per-pair (i, i+1) acceptance counts.
    pub pair_accepts: Vec<u64>,
    pub pair_proposals: Vec<u64>,
    /// Final score per replica, in temperature-order.
    pub final_scores: Vec<u32>,
    /// Total number of Houdayer cluster-move applications across the run.
    pub houdayer_applications: u64,
    /// Components proposed (i.e. found as valid swappable + in size range).
    pub houdayer_components_proposed: u64,
    /// Components actually swapped (after any acceptance filter).
    pub houdayer_components_applied: u64,
}

/// Run parallel tempering starting from `initial` (which may be partial;
/// each replica fills it in differently via fill_in_initial). Returns the
/// best board found across all replicas and all time.
pub fn run_pt_from(
    puzzle: &Puzzle,
    initial: &Board,
    cfg: &PtConfig,
) -> (SaOutcome, PtStats) {
    assert!(cfg.n_replicas >= 2, "PT needs ≥ 2 replicas");
    assert!(cfg.t_min > 0.0 && cfg.t_max > cfg.t_min, "bad temperature range");
    let started = Instant::now();
    let state = StateRef::new_with_pinned(puzzle, &cfg.pinned_positions);
    let total_edges = state.total_interior_edges();

    // Geometric temperature ladder. Standard for PT: equal acceptance
    // rates across adjacent pairs in the absence of phase transitions.
    let n = cfg.n_replicas;
    let ratio = (cfg.t_max / cfg.t_min).powf(1.0 / (n as f64 - 1.0));
    let temps: Vec<f64> = (0..n).map(|i| cfg.t_min * ratio.powi(i as i32)).collect();

    // Per-replica state.
    let mut boards: Vec<Board> = Vec::with_capacity(n);
    let mut scores: Vec<u32> = Vec::with_capacity(n);
    let mut best_boards: Vec<Board> = Vec::with_capacity(n);
    let mut best_scores: Vec<u32> = Vec::with_capacity(n);
    let mut rngs: Vec<RngHandle> = Vec::with_capacity(n);
    for r in 0..n {
        let mut rng = RngHandle::new(cfg.seed.wrapping_add((r as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15)));
        let b = if cfg.greedy_fill {
            state.greedy_fill_initial(initial, &mut rng)
        } else {
            state.fill_in_initial(initial, &mut rng)
        };
        let s = state.score(&b);
        boards.push(b.clone());
        scores.push(s);
        best_boards.push(b);
        best_scores.push(s);
        rngs.push(rng);
    }

    // Global best across replicas.
    let mut global_best_score: u32 = *best_scores.iter().max().unwrap();
    let mut global_best_idx = best_scores.iter().position(|s| *s == global_best_score).unwrap();
    let mut global_best_board = best_boards[global_best_idx].clone();

    // Swap-acceptance bookkeeping for diagnostics.
    let mut pair_proposals = vec![0u64; n - 1];
    let mut pair_accepts = vec![0u64; n - 1];
    let mut houdayer_applications: u64 = 0;
    let mut houdayer_components_proposed: u64 = 0;
    let mut houdayer_components_applied: u64 = 0;
    let mut total_swap_proposals = 0u64;
    let mut total_swap_accepts = 0u64;
    let mut rounds = 0u64;

    // A separate RNG for swap proposals — keeps the math identical
    // regardless of how replicas consume their own RNGs in parallel.
    let mut swap_rng = RngHandle::new(cfg.seed ^ 0xDEAD_BEEF_CAFE_BABE);

    let timed_out = || cfg.time_budget_ms != 0
        && started.elapsed().as_millis() >= u128::from(cfg.time_budget_ms);

    loop {
        if cfg.max_rounds != 0 && rounds >= cfg.max_rounds { break; }
        if timed_out() { break; }
        if global_best_score == total_edges { break; }

        // -------------------------------------------------------------
        // PHASE 1: each replica advances `inner_iters` steps at its T.
        // Parallel: each replica is independent in this phase.
        // -------------------------------------------------------------
        // We use rayon scope to mutate the per-replica state in parallel.
        // The state arrays are partitioned by index; no aliasing.
        use rayon::prelude::*;
        let temps_ref = &temps;
        let state_ref = &state;
        // Build a vector of per-replica mut-tuples, hand to rayon.
        let mut bundles: Vec<(&mut Board, &mut u32, &mut Board, &mut u32, &mut RngHandle, f64)> =
            boards.iter_mut()
                .zip(scores.iter_mut())
                .zip(best_boards.iter_mut())
                .zip(best_scores.iter_mut())
                .zip(rngs.iter_mut())
                .zip(temps_ref.iter().copied())
                .map(|(((((b, s), bb), bs), rng), t)| (b, s, bb, bs, rng, t))
                .collect();
        bundles.par_iter_mut().for_each(|(b, s, bb, bs, rng, t)| {
            run_sa_steps_fixed_temp(state_ref, b, s, bb, bs, rng, *t, cfg.inner_iters);
        });

        // Update global best after the parallel phase.
        for (i, &bs) in best_scores.iter().enumerate() {
            if bs > global_best_score {
                global_best_score = bs;
                global_best_idx = i;
                global_best_board = best_boards[i].clone();
            }
        }

        // Diagnostic: every 50 rounds, recompute true score for each
        // replica and check it matches the tracked score. Drift means
        // the incremental score-update logic has a bug.
        if cfg.verbose && rounds % 50 == 0 {
            for i in 0..n {
                let true_score = state.score(&boards[i]);
                if true_score != scores[i] {
                    eprintln!("[PT round {}] score DRIFT on replica {}: tracked={} true={}",
                        rounds, i, scores[i], true_score);
                    scores[i] = true_score; // correct it
                }
            }
        }

        // -------------------------------------------------------------
        // PHASE 2: replica-exchange proposals. We do (n-1) proposals
        // per round, alternating even/odd start to avoid lockstep
        // correlations. Each proposal swaps configurations between
        // adjacent temperatures with Metropolis acceptance.
        // -------------------------------------------------------------
        let start = (rounds & 1) as usize; // 0 or 1 — even rounds start at 0, odd at 1
        let mut i = start;
        while i + 1 < n {
            // Metropolis acceptance for replica exchange.
            //   E = -score (maximizing score = minimizing energy)
            //   Boltzmann weight at chain k = exp(-β_k * E_k) = exp(β_k * score_k)
            //   Joint weight = exp(β_i s_i + β_j s_j)
            //   Post-swap joint = exp(β_i s_j + β_j s_i)
            //   ratio = post/pre = exp((s_i - s_j)(β_j - β_i))
            //         = exp((s_i - s_j)(1/T_j - 1/T_i))
            // With T_i < T_j we have 1/T_j - 1/T_i < 0. So:
            //   If s_i > s_j (cold has better config): exponent < 0, prob < 1
            //     → mostly reject swap (good: keep good config cold)
            //   If s_i < s_j (hot has better config): exponent > 0, prob ≥ 1
            //     → always accept (good: pull good config colder)
            // Earlier draft had the sign flipped — that destroyed cold chains.
            let beta_lo = 1.0 / temps[i];
            let beta_hi = 1.0 / temps[i + 1]; // smaller, since T_{i+1} > T_i
            let s_lo = scores[i] as f64;
            let s_hi = scores[i + 1] as f64;
            let log_p = (s_lo - s_hi) * (beta_hi - beta_lo);
            let accept = log_p >= 0.0 || swap_rng.next_f64() < log_p.exp();
            total_swap_proposals += 1;
            pair_proposals[i] += 1;
            if accept {
                // Swap boards, scores, best (best stays with the chain).
                boards.swap(i, i + 1);
                scores.swap(i, i + 1);
                // best_boards and best_scores are PER-CHAIN-AT-CURRENT-T historically;
                // for "best ever at this temperature" we keep them. But the
                // GLOBAL best is tracked separately above, so swaps don't lose it.
                // We also DO swap them so a chain's "best" tracks its current
                // configuration's ancestry.
                best_boards.swap(i, i + 1);
                best_scores.swap(i, i + 1);
                total_swap_accepts += 1;
                pair_accepts[i] += 1;
            }
            i += 2;
        }

        rounds += 1;

        // ---- Houdayer cluster move between adjacent replica pairs ----
        // Energy-preserving teleportation: identify cells where adjacent
        // replicas i and i+1 disagree, find connected components whose
        // piece-multisets match between A and B (so the swap doesn't
        // duplicate pieces), and swap one randomly-chosen swappable
        // component. Joint matched-edge count is preserved exactly
        // (offline analysis showed all swappable components have
        // joint_delta = 0 on our plateau states). The hoped-for benefit
        // comes from SA continuing on the new joint configuration,
        // which may reach a better local optimum than either replica
        // would have found alone.
        if cfg.houdayer_every > 0 && rounds % cfg.houdayer_every == 0 {
            for i in 0..(n - 1) {
                houdayer_applications += 1;
                // Use the swap RNG so randomness is reproducible per seed.
                let proposals = enumerate_proposals(puzzle, &boards[i], &boards[i + 1]);
                // Filter to components within the size band.
                let mut admissible: Vec<&_> = proposals
                    .iter()
                    .filter(|p| {
                        p.component.len() >= cfg.houdayer_min_component
                            && p.component.len() <= cfg.houdayer_max_component
                    })
                    .collect();
                houdayer_components_proposed += admissible.len() as u64;
                if admissible.is_empty() {
                    continue;
                }
                // Pick one uniformly at random.
                let idx = (swap_rng.next_u64() as usize) % admissible.len();
                let chosen = admissible.remove(idx);
                // Snapshot for revert if Metropolis decides against.
                // For now (microcanonical), always apply.
                let prop = chosen.clone();
                // Boards need disjoint mutable access; split via split_at_mut.
                let (lo, hi) = boards.split_at_mut(i + 1);
                apply_proposal(&mut lo[i], &mut hi[0], &prop);
                // Recompute scores after swap. Since joint_delta = 0 by
                // construction (swap preserves matched edges), we can
                // also just trust offline-tested invariant and recompute
                // for safety / metric correctness.
                scores[i] = state.score(&boards[i]);
                scores[i + 1] = state.score(&boards[i + 1]);
                houdayer_components_applied += 1;
                // Track best.
                if scores[i] > best_scores[i] {
                    best_scores[i] = scores[i];
                    best_boards[i] = boards[i].clone();
                }
                if scores[i + 1] > best_scores[i + 1] {
                    best_scores[i + 1] = scores[i + 1];
                    best_boards[i + 1] = boards[i + 1].clone();
                }
                if cfg.verbose {
                    eprintln!(
                        "[PT round {:4}] HOUDAYER pair ({},{}) comp_size={} scores={:?}",
                        rounds, i, i + 1, prop.component.len(),
                        (scores[i], scores[i + 1])
                    );
                }
            }
        }

        // ---- mini-CP region repair on the cold chain ----
        if cfg.repair_every > 0 && rounds % cfg.repair_every == 0 {
            // Find worst k×k region on the cold chain's current board.
            if let Some((rx, ry)) = worst_region(puzzle, &boards[0], cfg.repair_k) {
                let before = scores[0];
                let repair_out = repair_region(
                    puzzle, &boards[0], rx, ry, cfg.repair_k, cfg.repair_budget_ms,
                );
                let outcome_str = match &repair_out {
                    None => "FAIL (CP didn't complete region)".to_string(),
                    Some(b) => {
                        let s = state.score(b);
                        format!("CP returned score={} (delta={:+})", s, (s as i64) - (before as i64))
                    }
                };
                if cfg.verbose {
                    eprintln!("[PT round {:4}] repair@({},{}) k={} before={} → {}",
                        rounds, rx, ry, cfg.repair_k, before, outcome_str);
                }
                if let Some(new_board) = repair_out {
                    let new_score = state.score(&new_board);
                    if new_score > before {
                        boards[0] = new_board.clone();
                        scores[0] = new_score;
                        if new_score > best_scores[0] {
                            best_scores[0] = new_score;
                            best_boards[0] = new_board.clone();
                        }
                        if new_score > global_best_score {
                            global_best_score = new_score;
                            global_best_idx = 0;
                            global_best_board = new_board;
                        }
                    }
                }
            }
        }

        // ---- Basin hop: deliberately kick the cold chain out of its basin ----
        if cfg.kick_every > 0 && rounds % cfg.kick_every == 0 {
            // Perform N random pair-swaps on cold chain unconditionally.
            // Then SA at T_min will pull it back toward a (possibly
            // different) local optimum next round. Classic basin-hopping
            // perturbation (Wales & Doye 1997). Used for atomic-cluster
            // global minimisation in chemistry; not used in published
            // E2 solvers.
            let interior_n = state.interior_cell_count();
            let cold_before = scores[0];
            // RNG: derive from base seed + round number for reproducibility.
            let raw_seed = cfg.seed
                .wrapping_add(rounds.wrapping_mul(0xA5A5_A5A5_A5A5_A5A5));
            let mut kr = RngHandle::new(raw_seed);
            for _ in 0..cfg.kick_n_swaps {
                if interior_n < 2 { break; }
                let i = (kr.next_u64() as usize) % interior_n;
                let mut j = (kr.next_u64() as usize) % interior_n;
                if i == j { j = (j + 1) % interior_n; }
                let pi = state.interior_cell(i);
                let pj = state.interior_cell(j);
                if let (Some((pid_i, rot_i)), Some((pid_j, rot_j))) =
                    (boards[0].get(pi), boards[0].get(pj))
                {
                    boards[0].place(pi, pid_j, rot_j);
                    boards[0].place(pj, pid_i, rot_i);
                }
            }
            scores[0] = state.score(&boards[0]);
            if cfg.verbose {
                eprintln!("[PT round {:4}] KICK cold: {} swaps, {} → {}",
                    rounds, cfg.kick_n_swaps, cold_before, scores[0]);
            }
        }

        if cfg.verbose && rounds % 5 == 0 {
            let elapsed_s = started.elapsed().as_secs_f64();
            let swap_rate = if total_swap_proposals > 0 {
                (total_swap_accepts as f64) / (total_swap_proposals as f64)
            } else { 0.0 };
            eprintln!(
                "[PT round {:4}] t={:.1}s  global_best={}/{} ({:.1}%)  swap_accept={:.1}%  per_chain_scores={:?}",
                rounds, elapsed_s,
                global_best_score, total_edges,
                100.0 * (global_best_score as f64) / (total_edges as f64),
                100.0 * swap_rate,
                scores,
            );
        }
        let _ = global_best_idx; // suppress unused warning
    }

    let outcome = SaOutcome {
        best_board: global_best_board,
        best_score: global_best_score,
        total_edges,
        iterations: rounds * cfg.inner_iters * (n as u64),
        elapsed_us: started.elapsed().as_micros(),
    };
    let stats = PtStats {
        rounds,
        total_swap_proposals,
        total_swap_accepts,
        pair_accepts,
        pair_proposals,
        final_scores: scores,
        houdayer_applications,
        houdayer_components_proposed,
        houdayer_components_applied,
    };
    (outcome, stats)
}

/// Parallel tempering from a random initial state (no CP seed).
pub fn run_pt(puzzle: &Puzzle, cfg: &PtConfig) -> (SaOutcome, PtStats) {
    let empty = Board::empty(puzzle);
    run_pt_from(puzzle, &empty, cfg)
}
