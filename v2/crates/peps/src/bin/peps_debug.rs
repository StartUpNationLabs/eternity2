// Debug helper: dump cell tensors for a tiny puzzle.

use eternity2_peps::{PepsContext, PieceRot};
use eternity2_peps::tensor::build_all_cell_tensors;
use eternity2_puzzle_io::load_puzzle;
use std::path::PathBuf;
use std::sync::Arc;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let path = if args.len() > 1 {
        PathBuf::from(&args[1])
    } else {
        PathBuf::from("../data/generated/size_2_colors_2_c27cbb68.csv")
    };
    let puzzle = load_puzzle(&path).expect("load");
    let ctx = PepsContext::new(Arc::new(puzzle));
    let mu = vec![0.0; ctx.n_pieces];
    let pinned: Vec<Option<PieceRot>> = vec![None; ctx.size * ctx.size];
    let cells = build_all_cell_tensors(&ctx, &mu, &pinned);

    println!("Puzzle: size={} K={} n_pieces={}", ctx.size, ctx.k_colors, ctx.n_pieces);

    for (i, c) in cells.iter().enumerate() {
        let sum: f64 = c.iter().sum();
        let nz = c.iter().filter(|&&v| v > 0.0).count();
        let y = i / ctx.size;
        let x = i % ctx.size;
        println!("\ncell {} (y={}, x={}): sum={:.4} nonzero={}", i, y, x, sum, nz);
        for cn in 0..ctx.k_colors {
            for ce in 0..ctx.k_colors {
                for cs in 0..ctx.k_colors {
                    for cw in 0..ctx.k_colors {
                        let v = c[[cn, ce, cs, cw]];
                        if v > 0.0 {
                            println!("  T[N={}, E={}, S={}, W={}] = {:.4}", cn, ce, cs, cw, v);
                        }
                    }
                }
            }
        }
    }

    // Try contracting
    use eternity2_peps::mps::log_z_lagrangian;
    let log_z_val = log_z_lagrangian(&ctx, &mu, &pinned, 0);
    println!("\nlog_z = {}", log_z_val);
}
