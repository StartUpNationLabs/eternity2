// Directed E2 pipeline: CP → PT (general LS) → directed (focused LS on
// bad-cells). The directed phase identifies cells touching mismatched
// edges and runs SA restricted to that set, with periodic refresh.

use std::path::PathBuf;
use std::time::Instant;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_benchmark::report::{puzzle_name_from_path, write_report};
use eternity2_core::{Board, Piece, PieceId, Puzzle, BORDER};
use eternity2_events::BufferSink;
use eternity2_localsearch::{
    run_directed, run_pt_from, DirectedConfig, PtConfig,
};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

#[derive(Parser, Debug)]
#[command(name = "directed_e2", about = "CP → PT → directed-SA pipeline")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long, default_value_t = 30)]
    cp_seconds: u64,

    #[arg(long, default_value_t = 120)]
    pt_seconds: u64,

    #[arg(long, default_value_t = 120)]
    directed_seconds: u64,

    #[arg(long, default_value_t = 8)]
    n_replicas: usize,

    #[arg(long, default_value_t = 0xE2_E2_E2_E2)]
    seed: u64,

    #[arg(long, default_value_t = 0.05)]
    directed_temp: f64,

    #[arg(long, default_value_t = 1)]
    directed_pad: u32,
}

fn lookup_piece(p: &Puzzle, id: PieceId) -> Option<&Piece> {
    p.pieces().iter().find(|q| q.id == id)
}
fn score(p: &Puzzle, b: &Board) -> (u32, u32) {
    let w = p.width; let h = p.height;
    let mut m = 0u32;
    let total = (w-1)*h + w*(h-1);
    for y in 0..h { for x in 0..w {
        let pos = y*w+x;
        let Some((pid, rot)) = b.get(pos) else { continue; };
        let Some(piece) = lookup_piece(p, pid) else { continue; };
        let e = piece.edges.rotated(rot).as_array();
        if x+1<w { if let Some((rp, rr)) = b.get(y*w+(x+1)) {
            if let Some(rpc) = lookup_piece(p, rp) {
                let re = rpc.edges.rotated(rr).as_array();
                if e[1]==re[3] && e[1]!=BORDER && e[1]!=0 { m += 1; }
            }
        }}
        if y+1<h { if let Some((bp, br)) = b.get((y+1)*w+x) {
            if let Some(bpc) = lookup_piece(p, bp) {
                let be = bpc.edges.rotated(br).as_array();
                if e[2]==be[0] && e[2]!=BORDER && e[2]!=0 { m += 1; }
            }
        }}
    }}
    (m, total)
}
fn pct(n: u32, d: u32) -> f64 { 100.0 * (n as f64) / (d as f64) }

fn main() {
    let args = Args::parse();
    eprintln!("=== DIRECTED E2: CP → PT → directed-SA ===");
    eprintln!("cp={}s pt={}s directed={}s n_replicas={}", args.cp_seconds, args.pt_seconds, args.directed_seconds, args.n_replicas);

    let (puzzle, hints) = load_puzzle_with_hints(&args.puzzle).expect("load");

    // ----- CP -----
    eprintln!("\n--- CP ({}s) ---", args.cp_seconds);
    let mut solver = EngineSolver::gacolor_ac3_par();
    let mut sink = BufferSink::new();
    let mut opts = SolveOpts::default();
    opts.time_budget_ms = args.cp_seconds * 1000;
    opts.hints = hints;
    let t0 = Instant::now();
    let out = solver.solve(&puzzle, &opts, &mut sink);
    let cp_elapsed = t0.elapsed();
    let cp_board: Board = match out {
        SolveOutcome::Solved(b) | SolveOutcome::TimedOut { best_partial: b, .. }
        | SolveOutcome::Cancelled { best_partial: b, .. } => b,
        SolveOutcome::AllSolutions(bs) => bs.into_iter().next().unwrap_or_else(|| Board::empty(&puzzle)),
        SolveOutcome::Exhausted => Board::empty(&puzzle),
        SolveOutcome::Error(_) => Board::empty(&puzzle),
    };
    let (cp_s, total) = score(&puzzle, &cp_board);
    eprintln!("CP done {:.1}s: {}/{} ({:.1}%)", cp_elapsed.as_secs_f64(), cp_s, total, pct(cp_s, total));

    // ----- PT -----
    eprintln!("\n--- PT ({}s, {} replicas) ---", args.pt_seconds, args.n_replicas);
    let pt_cfg = PtConfig {
        n_replicas: args.n_replicas,
        t_min: 0.02,
        t_max: 0.5,
        inner_iters: 30_000,
        max_rounds: 0,
        time_budget_ms: args.pt_seconds * 1000,
        seed: args.seed,
        verbose: true,
        greedy_fill: true,
        diversify_fill: false,
        repair_every: 0,
        repair_k: 4,
        repair_budget_ms: 200,
        kick_every: 0,
        kick_n_swaps: 6,
        pinned_positions: Vec::new(),
        houdayer_every: 0,
        houdayer_max_component: 20,
        houdayer_min_component: 4,
    };
    let t1 = Instant::now();
    let (pt_out, _stats) = run_pt_from(&puzzle, &cp_board, &pt_cfg);
    eprintln!("PT done {:.1}s: best={}/{} ({:.1}%)",
        t1.elapsed().as_secs_f64(), pt_out.best_score, pt_out.total_edges,
        pct(pt_out.best_score, pt_out.total_edges));

    let output_dir = std::path::PathBuf::from("output");
    let puzzle_name = puzzle_name_from_path(&args.puzzle);

    // ----- Directed phase -----
    if args.directed_seconds == 0 {
        eprintln!("\n=== SUMMARY ===");
        eprintln!("CP: {}/{} ({:.1}%)  PT: {}/{} ({:.1}%)",
            cp_s, total, pct(cp_s, total),
            pt_out.best_score, pt_out.total_edges, pct(pt_out.best_score, pt_out.total_edges));
        let extra = serde_json::json!({
            "cp": { "score": cp_s, "elapsed_s": cp_elapsed.as_secs_f64(), "budget_s": args.cp_seconds },
            "pt": { "score": pt_out.best_score, "budget_s": args.pt_seconds },
            "directed": null,
            "seed": args.seed,
        });
        match write_report(&output_dir, "directed_e2", &puzzle, &puzzle_name, &pt_out.best_board, extra) {
            Ok(r) => { eprintln!("\nReport: {}", r.json_path.display()); eprintln!("Bucas:  {}", r.url); }
            Err(e) => eprintln!("warning: failed to write report: {e}"),
        }
        return;
    }
    eprintln!("\n--- Directed phase ({}s) ---", args.directed_seconds);
    let dir_cfg = DirectedConfig {
        temperature: args.directed_temp,
        iterations: 0,
        time_budget_ms: args.directed_seconds * 1000,
        seed: args.seed ^ 0xC0DE_C0DE,
        refresh_every: 50_000,
        pad: args.directed_pad,
    };
    let t2 = Instant::now();
    let dir_out = run_directed(&puzzle, &pt_out.best_board, &dir_cfg);
    eprintln!("Directed done {:.1}s: iters={} best={}/{} ({:.1}%)",
        t2.elapsed().as_secs_f64(), dir_out.iterations,
        dir_out.best_score, dir_out.total_edges,
        pct(dir_out.best_score, dir_out.total_edges));

    eprintln!("\n=== SUMMARY ===");
    eprintln!("CP:        {}/{} ({:.1}%)", cp_s, total, pct(cp_s, total));
    eprintln!("PT:        {}/{} ({:.1}%)", pt_out.best_score, total, pct(pt_out.best_score, total));
    eprintln!("Directed:  {}/{} ({:.1}%)", dir_out.best_score, total, pct(dir_out.best_score, total));
    eprintln!("Community: 467/480 (97.3%)");

    let extra = serde_json::json!({
        "cp": { "score": cp_s, "elapsed_s": cp_elapsed.as_secs_f64(), "budget_s": args.cp_seconds },
        "pt": { "score": pt_out.best_score, "budget_s": args.pt_seconds },
        "directed": { "score": dir_out.best_score, "iters": dir_out.iterations, "budget_s": args.directed_seconds, "temperature": args.directed_temp, "pad": args.directed_pad },
        "seed": args.seed,
    });
    match write_report(&output_dir, "directed_e2", &puzzle, &puzzle_name, &dir_out.best_board, extra) {
        Ok(r) => { eprintln!("\nReport: {}", r.json_path.display()); eprintln!("Bucas:  {}", r.url); }
        Err(e) => eprintln!("warning: failed to write report: {e}"),
    }
}
