// ISENTROPE #2 (vol-209) — entropy of the REAL bordered E2 board via chi-truncated
// boundary-MPS contraction. With mu=0 the cell tensor entry counts placements with
// a given (N,E,S,W); contracting the network sums over all valid REUSABLE colorings
// of the bordered board => W_grammar(size). log10(W)/size^2 = entropy density.
//
// Exact transfer hits the 2^width wall at width ~5 (bench-audit isentrope_count);
// here the chi-truncated MPS (peps log_z) reaches the TRUE width 16.
//
// Validation: on any board, chi=0 is the exact contraction; truncated chi converges
// to it as chi grows (monotone). We report log10(W) and density vs chi.
//
// Usage: isentrope_peps --puzzle <csv> --chi <c1,c2,...>

use std::sync::Arc;
use eternity2_peps::{PepsContext, mps_proper::log_z_mps};
use eternity2_puzzle_io::load_puzzle;

fn main() {
    let mut puzzle_path = "../data/puzzles/size_16_official_eternity.csv".to_string();
    let mut chis: Vec<usize> = vec![0]; // 0 = exact
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--puzzle" => { puzzle_path = args[i + 1].clone(); i += 2; }
            "--chi" => {
                chis = args[i + 1].split(',').map(|s| s.parse().unwrap()).collect();
                i += 2;
            }
            _ => { i += 1; }
        }
    }
    let puzzle = load_puzzle(std::path::Path::new(&puzzle_path)).expect("load puzzle");
    let size = puzzle.width as usize;
    let ctx = PepsContext::new(Arc::new(puzzle));
    eprintln!("[init] size={size} K={} n_pieces={}", ctx.k_colors, ctx.n_pieces);

    let cells2 = size * size;
    println!("chi,logW_e,logW_10,density_per_cell,secs");
    for &chi in &chis {
        let t = std::time::Instant::now();
        let logz = log_z_mps(&ctx, chi);
        let secs = t.elapsed().as_secs_f64();
        let log10 = logz / std::f64::consts::LN_10;
        let density = log10 / cells2 as f64;
        let chi_label = if chi == 0 { "exact".to_string() } else { chi.to_string() };
        println!("{chi_label},{logz:.6},{log10:.6},{density:.8},{secs:.2}");
        eprintln!("[chi={chi_label}] log_e(W)={logz:.4} log10(W)={log10:.4} \
                   density/cell={density:.6} ({secs:.1}s)");
    }
}
