// verhaard_sa — outer simulated annealer over piece-set composition,
// optimising the count of 2x2 sub-tilings (Verhaard's 2008 metric).
//
// This is phase-1 of the Verhaard pipeline (the OUTER SA). It does not
// place pieces on the board — it only selects which subset of 180-190
// of the 196 inner pieces to commit to. Phase-2 (scaffold backtrack)
// and phase-3 (full completion) follow.

#![forbid(unsafe_code)]

use std::fs::{create_dir_all, File};
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Piece;
use eternity2_solver_verhaard::sa::{run_sa, SaConfig};
use eternity2_solver_verhaard::tile2x2::Tile2x2Index;

#[derive(Parser, Debug)]
#[command(name = "verhaard_sa", about = "Outer SA over piece-set composition")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long, default_value = "output/v9_verhaard/sa_result.json")]
    out: PathBuf,

    /// Target |in_set|. Verhaard used 180-190 of 196 inner pieces.
    #[arg(long, default_value_t = 186)]
    k_target: usize,

    #[arg(long, default_value_t = 5_000)]
    max_iters: u64,

    #[arg(long, default_value_t = 50.0)]
    t_initial: f64,

    #[arg(long, default_value_t = 0.5)]
    t_final: f64,

    #[arg(long, default_value_t = 0.999)]
    cooling: f64,

    #[arg(long, default_value_t = 0xDEC0DEDADC0DEu64)]
    seed: u64,

    #[arg(long, default_value_t = 100)]
    log_every: u64,

    #[arg(long, default_value_t = 0)]
    sanity_every: u64,

    /// Compute the baseline metric over ALL 196 inner pieces for reference.
    #[arg(long, default_value_t = true)]
    compute_baseline: bool,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let (puzzle, _hints) = load_puzzle_with_hints(&args.puzzle).map_err(|e| format!("{e}"))?;
    eprintln!("puzzle: {}x{}, {} pieces", puzzle.width, puzzle.height, puzzle.pieces().len());

    let inner_pieces: Vec<Piece> = puzzle.pieces().iter().filter(|p| p.is_inner()).copied().collect();
    eprintln!("inner pieces: {}", inner_pieces.len());

    let max_color = puzzle.color_count as usize;
    let t_idx0 = Instant::now();
    let idx = Tile2x2Index::build(&inner_pieces, max_color);
    eprintln!(
        "Tile2x2Index: {} rotated-piece entries, built in {:.2} s",
        idx.all.len(),
        t_idx0.elapsed().as_secs_f64()
    );

    if args.compute_baseline {
        let in_all: Vec<bool> = (0..256).map(|pid| inner_pieces.iter().any(|p| p.id as usize == pid)).collect();
        let t0 = Instant::now();
        let baseline = idx.count_total(&in_all);
        eprintln!(
            "BASELINE: 2x2 sub-tilings on full 196 inner pieces = {} ({:.2} s)",
            baseline,
            t0.elapsed().as_secs_f64()
        );
    }

    let cfg = SaConfig {
        k_target: args.k_target,
        max_iters: args.max_iters,
        t_initial: args.t_initial,
        t_final: args.t_final,
        cooling: args.cooling,
        seed: args.seed,
        log_every: args.log_every,
        sanity_every: args.sanity_every,
    };
    let t1 = Instant::now();
    let result = run_sa(&inner_pieces, &idx, &cfg);
    let elapsed = t1.elapsed();
    eprintln!(
        "SA done: iters={} accepts={} rejects={} best_metric={} final_metric={} elapsed={:.1}s",
        result.iters, result.accepts, result.rejects, result.best_metric, result.final_metric,
        elapsed.as_secs_f64()
    );
    eprintln!("|best_set| = {}", result.best_set.len());

    // Serialize.
    if let Some(p) = args.out.parent() { create_dir_all(p)?; }
    let mut writer = BufWriter::new(File::create(&args.out)?);
    let summary = serde_json::json!({
        "config": {
            "k_target": cfg.k_target,
            "max_iters": cfg.max_iters,
            "t_initial": cfg.t_initial,
            "t_final": cfg.t_final,
            "cooling": cfg.cooling,
            "seed": cfg.seed,
        },
        "elapsed_s": elapsed.as_secs_f64(),
        "result": result,
    });
    serde_json::to_writer_pretty(&mut writer, &summary)?;
    writeln!(writer)?;
    drop(writer);
    eprintln!("wrote {}", args.out.display());
    Ok(())
}
