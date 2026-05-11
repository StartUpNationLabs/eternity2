// Encode an E2 puzzle (default: 16×16 official with 5 hints) as
// DIMACS CNF (decision SAT) and/or WCNF (MaxSAT).
//
// Outputs:
//   output/sat_e2_<stem>_<timestamp>.cnf   — decision SAT
//   output/sat_e2_<stem>_<timestamp>.wcnf  — MaxSAT (new format)
//
// Encoding follows Ansótegui-Sellmann-Tabar 2008 style with our own
// variable layout: piece-rotation-at-cell + edge-match aux vars.
//
// MaxSAT objective: maximize # of soft clauses, where each soft clause
// asserts "interior edge e has some color that matches on both sides."
// The optimum equals the number of matched edges in the best legal
// placement of all 256 pieces respecting the 5 hints. If MaxSAT
// optimum == 480, the puzzle admits a perfect solution. If < 480, the
// MaxSAT optimum is the structural ceiling — an authoritative answer
// to whether 449+1 is reachable.

use std::fs;
use std::path::PathBuf;
use std::time::SystemTime;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_sat_encoder::{encode, write_dimacs_cnf, write_wcnf_new, EncodeOptions, VarMap};

#[derive(Parser, Debug)]
#[command(name = "sat_e2", about = "Emit SAT/MaxSAT encoding of an E2 puzzle")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long, default_value = "output")]
    output_dir: PathBuf,

    /// Sanity-check mode: encode but don't write files.
    #[arg(long, default_value_t = false)]
    dry_run: bool,

    #[arg(long, default_value_t = false)]
    skip_cnf: bool,

    #[arg(long, default_value_t = false)]
    skip_wcnf: bool,

    /// Encode the unhinted puzzle (ignore file hints).
    #[arg(long, default_value_t = false)]
    no_hints: bool,

    /// Generate a synthetic puzzle instead of loading from disk.
    /// Side length n; uses n+2 interior colors. Useful for validation.
    #[arg(long)]
    generate_n: Option<u32>,

    /// Seed for the generator.
    #[arg(long, default_value_t = 0xC0FFEE)]
    generate_seed: u64,
}

fn main() {
    let args = Args::parse();
    eprintln!("=== sat_e2 ===");
    eprintln!("puzzle: {}", args.puzzle.display());

    let (puzzle, hints) = if let Some(n) = args.generate_n {
        let p = generate(GeneratorConfig {
            size: n, interior_colors: n + 2, seed: args.generate_seed,
        }).expect("generate");
        eprintln!("generated {}×{}, {} pieces, {} colors, seed=0x{:x}",
            p.width, p.height, p.pieces().len(), p.color_count - 1, args.generate_seed);
        (p, eternity2_core::Hints::default())
    } else {
        let (p, h) = load_puzzle_with_hints(&args.puzzle).expect("load");
        let h = if args.no_hints { eternity2_core::Hints::default() } else { h };
        eprintln!("loaded {}×{}, {} pieces, {} colors, {} hints",
            p.width, p.height, p.pieces().len(), p.color_count - 1, h.hints.len());
        (p, h)
    };

    eprintln!("\nBuilding variable map...");
    let t0 = std::time::Instant::now();
    let vmap = VarMap::build(&puzzle);
    eprintln!("  built in {:.2}s", t0.elapsed().as_secs_f64());
    eprintln!("  piece-vars: {}", vmap.var_to_cpr.len());
    eprintln!("  interior edges: {}", vmap.edges.len());
    eprintln!("  total vars (with edge-match aux): {}", vmap.n_vars);

    if !args.skip_cnf {
        eprintln!("\nEncoding decision SAT...");
        let t1 = std::time::Instant::now();
        let cnf = encode(&puzzle, &hints, &vmap, &EncodeOptions { soft_edge_match: false });
        eprintln!("  encoded in {:.2}s", t1.elapsed().as_secs_f64());
        eprintln!("  total vars: {}", cnf.n_vars());
        eprintln!("  hard clauses: {}", cnf.clauses.len());
        if !args.dry_run {
            let stem = if let Some(n) = args.generate_n {
                format!("generated_{}x{}_seed{}", n, n, args.generate_seed)
            } else { stem(&args.puzzle) };
            let ts = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs();
            let out = args.output_dir.join(format!("sat_e2_{}_{}.cnf", stem, ts));
            fs::create_dir_all(&args.output_dir).ok();
            eprintln!("  serializing...");
            let t2 = std::time::Instant::now();
            let dimacs = write_dimacs_cnf(&cnf);
            eprintln!("    serialized {:.1} MB in {:.2}s",
                dimacs.len() as f64 / 1_048_576.0, t2.elapsed().as_secs_f64());
            fs::write(&out, dimacs).expect("write cnf");
            eprintln!("  wrote {}", out.display());
        }
    }

    if !args.skip_wcnf {
        eprintln!("\nEncoding MaxSAT (soft edge-match)...");
        let t1 = std::time::Instant::now();
        let wcnf = encode(&puzzle, &hints, &vmap, &EncodeOptions { soft_edge_match: true });
        eprintln!("  encoded in {:.2}s", t1.elapsed().as_secs_f64());
        eprintln!("  total vars: {}", wcnf.n_vars());
        eprintln!("  hard clauses: {}", wcnf.clauses.len());
        eprintln!("  soft clauses: {} (one per interior edge)", wcnf.soft_clauses.len());
        if !args.dry_run {
            let stem = if let Some(n) = args.generate_n {
                format!("generated_{}x{}_seed{}", n, n, args.generate_seed)
            } else { stem(&args.puzzle) };
            let ts = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs();
            let out = args.output_dir.join(format!("sat_e2_{}_{}.wcnf", stem, ts));
            fs::create_dir_all(&args.output_dir).ok();
            eprintln!("  serializing...");
            let t2 = std::time::Instant::now();
            let dimacs = write_wcnf_new(&wcnf);
            eprintln!("    serialized {:.1} MB in {:.2}s",
                dimacs.len() as f64 / 1_048_576.0, t2.elapsed().as_secs_f64());
            fs::write(&out, dimacs).expect("write wcnf");
            eprintln!("  wrote {}", out.display());
        }
    }

    eprintln!("\nDone.");
}

fn stem(p: &std::path::Path) -> String {
    p.file_stem().and_then(|s| s.to_str()).unwrap_or("puzzle").to_string()
}
