// Vol-125 T37 — LAP solver microbench: Kuhn-Munkres (pathfinding) vs JV (lsap).
//
// Generates k × k cost matrices and times each solver. Reports
// median assignments/sec across ≥ 8 seeds.

#![forbid(unsafe_code)]

use std::time::Instant;
use pathfinding::kuhn_munkres::kuhn_munkres;
use pathfinding::matrix::Matrix;

fn gen_matrix(k: usize, seed: u64) -> Vec<i64> {
    // Simple LCG.
    let mut state = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
    let mut v = Vec::with_capacity(k * k);
    for _ in 0..k * k {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        v.push(((state >> 32) as i32 & 0xFFF) as i64); // 0..4095
    }
    v
}

fn bench_km(k: usize, matrices: &[Vec<i64>]) -> (f64, i64) {
    let mut total_score: i64 = 0;
    let t0 = Instant::now();
    for m in matrices {
        let cost_matrix = Matrix::from_vec(k, k, m.clone()).unwrap();
        let (score, _assignment) = kuhn_munkres(&cost_matrix);
        total_score += score;
    }
    let elapsed = t0.elapsed().as_secs_f64();
    let solves_per_sec = matrices.len() as f64 / elapsed;
    (solves_per_sec, total_score)
}

fn bench_jv(k: usize, matrices: &[Vec<i64>]) -> (f64, i64) {
    let mut total_score: i64 = 0;
    let t0 = Instant::now();
    for m in matrices {
        // lsap MINIMIZES. KM MAXIMIZES. To match KM (maximization), use
        // maximize=true. Note: lsap's maximize flag tells it to negate costs
        // internally.
        // We need to convert i64 -> f64 for lsap.
        let costs: Vec<f64> = m.iter().map(|&x| x as f64).collect();
        let (_, col_ind) = lsap::solve(k, k, &costs, true).expect("LAP solvable");
        // Compute total weight from the assignment (same as KM would output).
        let s: i64 = (0..k).map(|i| m[i * k + col_ind[i] as usize]).sum();
        total_score += s;
    }
    let elapsed = t0.elapsed().as_secs_f64();
    let solves_per_sec = matrices.len() as f64 / elapsed;
    (solves_per_sec, total_score)
}

fn bench_jv_joint(k: usize, matrices: &[Vec<i64>]) -> (f64, i64) {
    // For the joint formulation, build 4k × 4k matrices from each k × k.
    // Each row r = piece_i * 4 + rot_i. Cost for col j (real position) is the
    // k × k entry. For dummy columns: cheap for same piece, BIG for others.
    let big = 1000.0;
    let mut total_score: i64 = 0;
    let t0 = Instant::now();
    for m in matrices {
        let dim = 4 * k;
        let mut cost = vec![big; dim * dim];
        for piece_i in 0..k {
            for rot in 0..4 {
                let row = piece_i * 4 + rot;
                for j in 0..k {
                    // Use the original k×k entry; vary by rotation by a small perturbation
                    // (so the joint version actually has 4 rotation choices). For the
                    // microbench, just replicate the row 4 times. That's a degenerate test
                    // but exercises the LAP machinery.
                    cost[row * dim + j] = m[piece_i * k + j] as f64;
                }
                for d in 0..3 {
                    let dummy_col = k + piece_i * 3 + d;
                    cost[row * dim + dummy_col] = 0.0;
                }
            }
        }
        let (_, col_ind) = lsap::solve(dim, dim, &cost, true).expect("LAP solvable");
        // Score: sum over rows where col < k.
        let mut s: i64 = 0;
        for piece_i in 0..k {
            for rot in 0..4 {
                let row = piece_i * 4 + rot;
                let col = col_ind[row] as usize;
                if col < k {
                    s += m[piece_i * k + col];
                    break;
                }
            }
        }
        total_score += s;
    }
    let elapsed = t0.elapsed().as_secs_f64();
    let solves_per_sec = matrices.len() as f64 / elapsed;
    (solves_per_sec, total_score)
}

fn main() {
    let ks = [16, 32, 64, 128];
    let n_seeds = 8;
    let n_repeats = 50; // per seed, to reduce timing noise

    println!("k\tn_solves\tKM_solves/s\tJV_solves/s\tspeedup\tKM_score\tJV_score\tequal?");
    for k in ks {
        // Build matrices once per (k, seed).
        let mut matrices = Vec::new();
        for seed in 0..n_seeds {
            let m = gen_matrix(k, seed as u64);
            for _ in 0..n_repeats { matrices.push(m.clone()); }
        }
        let n_total = matrices.len();

        let (km_sps, km_score) = bench_km(k, &matrices);
        let (jv_sps, jv_score) = bench_jv(k, &matrices);
        let speedup = jv_sps / km_sps;
        // Verify: KM and JV should produce the SAME optimal score.
        let equal = if km_score == jv_score { "✓" } else { "✗" };
        println!("{}\t{}\t{:.1}\t{:.1}\t{:.2}x\t{}\t{}\t{}",
                 k, n_total, km_sps, jv_sps, speedup, km_score, jv_score, equal);
    }

    // Also test the JV-joint formulation overhead.
    println!("\n=== JV-joint (4k × 4k) overhead ===");
    println!("k\tn\tJV_solves/s\tJVjoint_solves/s\tslowdown");
    for k in [16, 32, 64] {  // 128 might be slow for 4k=512
        let mut matrices = Vec::new();
        for seed in 0..4 {
            let m = gen_matrix(k, seed);
            for _ in 0..10 { matrices.push(m.clone()); }
        }
        let n_total = matrices.len();
        let (jv_sps, _) = bench_jv(k, &matrices);
        let (jvj_sps, _) = bench_jv_joint(k, &matrices);
        let slowdown = jv_sps / jvj_sps;
        println!("{}\t{}\t{:.1}\t{:.1}\t{:.2}x", k, n_total, jv_sps, jvj_sps, slowdown);
    }
}
