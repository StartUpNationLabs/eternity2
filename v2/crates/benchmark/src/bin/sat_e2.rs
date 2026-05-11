// Encode an E2 puzzle as DIMACS CNF (decision SAT) or WCNF (MaxSAT).
//
// Outputs:
//   output/sat_e2_<stem>_<timestamp>.cnf   — decision SAT
//   output/sat_e2_<stem>_<timestamp>.wcnf  — MaxSAT (new format)
//
// Encoding follows Ansótegui-Sellmann-Tabar 2008 style with our own
// variable layout: piece-rotation-at-cell + edge-match aux vars.
//
// MaxSAT objective: maximize # of satisfied soft clauses, where each
// soft clause asserts "interior edge e has some color that matches on
// both sides." The optimum equals the maximum matched-edge count
// achievable under the puzzle's hard constraints (alldiff + 5 hints).
// If MaxSAT optimum == 480, the puzzle admits a perfect solution.
//
// To actually solve: feed the .cnf to a CDCL SAT solver (kissat,
// CaDiCaL) or the .wcnf to a native MaxSAT solver (EvalMaxSAT,
// CashWMaxSAT, UWrMaxSAT — all stream intermediate bounds). The
// pysat RC2 wrapper is opaque (no intermediate output) and was
// removed from this pipeline.

use std::fs;
use std::path::PathBuf;
use std::time::SystemTime;

use clap::Parser;
use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_sat_encoder::{encode, write_dimacs_cnf, write_wcnf_new, write_wcnf_old, EncodeOptions, VarMap};

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

    /// Use old-style WCNF ("p wcnf vars clauses top") instead of the
    /// new format ("h" prefix). Required by Z3's -wcnf parser and some
    /// older MaxSAT solvers.
    #[arg(long, default_value_t = false)]
    wcnf_old: bool,

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

    /// Pin cells from a plateau-JSON board EXCEPT those in the center
    /// region. The center region is the inner k×k area; the rest is
    /// pinned from the source board. Asks MaxSAT to optimize over the
    /// center k×k given the boundary fixed.
    ///
    /// Set `--pin-outside-from path` to enable; `--center-k k` to
    /// pick the free-region size (e.g. k=10 for inner 10×10, k=12 for 12×12).
    #[arg(long)]
    pin_outside_from: Option<PathBuf>,

    /// Side length of the free center region. Cells outside this are
    /// pinned from --pin-outside-from. Only used when --pin-outside-from
    /// is set. Default 10 = inner 10×10 region free on a 16×16 puzzle.
    #[arg(long, default_value_t = 10)]
    center_k: u32,
}

fn main() {
    let args = Args::parse();
    eprintln!("=== sat_e2 ===");
    eprintln!("puzzle: {}", args.puzzle.display());

    let (puzzle, mut hints) = if let Some(n) = args.generate_n {
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

    // Optional: pin all cells outside the center k×k region from a
    // plateau JSON. Asks SAT/MaxSAT to optimize over only the center.
    if let Some(plateau_path) = &args.pin_outside_from {
        let raw = std::fs::read_to_string(plateau_path).expect("read plateau JSON");
        let v: serde_json::Value = serde_json::from_str(&raw).expect("parse plateau JSON");
        // Get per-cell placement either from `placement` field or bucas URL.
        let placement: Vec<Option<(eternity2_core::PieceId, eternity2_core::Rotation)>> =
            if let Some(arr) = v.get("placement").and_then(|x| x.as_array()) {
                let mut out = Vec::with_capacity(arr.len());
                for entry in arr {
                    if entry.is_null() { out.push(None); }
                    else {
                        let pid = entry.get("piece_id").unwrap().as_u64().unwrap() as eternity2_core::PieceId;
                        let rot_u = entry.get("rotation").unwrap().as_u64().unwrap() as u8;
                        out.push(Some((pid, eternity2_core::Rotation::from_u8(rot_u).unwrap())));
                    }
                }
                eprintln!("\nusing enriched `placement` field from {}", plateau_path.display());
                out
            } else if let Some(url) = v.get("bucas_url").and_then(|x| x.as_str()) {
                eprintln!("\ndecoding placement from bucas_url in {}", plateau_path.display());
                decode_from_bucas_for_pinning(&puzzle, url)
            } else {
                panic!("plateau JSON has neither `placement` nor `bucas_url`");
            };

        // Determine the center k×k box.
        let k = args.center_k;
        if k > puzzle.width || k > puzzle.height {
            panic!("center_k={} exceeds puzzle dimensions", k);
        }
        let x0 = (puzzle.width - k) / 2;
        let y0 = (puzzle.height - k) / 2;
        let x1 = x0 + k;
        let y1 = y0 + k;
        eprintln!("free region: rows {}..{}, cols {}..{} ({}×{} = {} cells)",
            y0, y1, x0, x1, k, k, k * k);

        // Pin every cell OUTSIDE the center box (using its placement from the plateau).
        let mut anchor_hints = Vec::new();
        let mut existing: std::collections::BTreeSet<u32> = hints.hints.iter().map(|h| h.position).collect();
        for pos in 0..puzzle.cell_count() {
            let x = pos % puzzle.width;
            let y = pos / puzzle.width;
            let in_center = x >= x0 && x < x1 && y >= y0 && y < y1;
            if in_center { continue; }
            if existing.contains(&pos) { continue; }
            if let Some((pid, rot)) = placement[pos as usize] {
                anchor_hints.push(eternity2_core::Hint { position: pos, piece_id: pid, rotation: rot });
                existing.insert(pos);
            }
        }
        eprintln!("adding {} anchor hints (pinning cells outside the {}×{} center)",
            anchor_hints.len(), k, k);
        for h in anchor_hints { hints.hints.push(h); }
        eprintln!("total hints (existing + anchor): {}", hints.hints.len());
    }

    eprintln!("\nBuilding variable map...");
    let t0 = std::time::Instant::now();
    let vmap = VarMap::build(&puzzle);
    eprintln!("  built in {:.2}s", t0.elapsed().as_secs_f64());
    eprintln!("  piece-vars: {}", vmap.var_to_cpr.len());
    eprintln!("  interior edges: {}", vmap.edges.len());
    eprintln!("  total vars (with edge-match aux): {}", vmap.n_vars);

    let stem_str = if let Some(n) = args.generate_n {
        format!("generated_{}x{}_seed{}", n, n, args.generate_seed)
    } else { stem(&args.puzzle) };

    if !args.skip_cnf {
        eprintln!("\nEncoding decision SAT...");
        let t1 = std::time::Instant::now();
        let cnf = encode(&puzzle, &hints, &vmap, &EncodeOptions { soft_edge_match: false });
        eprintln!("  encoded in {:.2}s", t1.elapsed().as_secs_f64());
        eprintln!("  total vars: {}", cnf.n_vars());
        eprintln!("  hard clauses: {}", cnf.clauses.len());
        if !args.dry_run {
            let ts = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs();
            let out = args.output_dir.join(format!("sat_e2_{}_{}.cnf", stem_str, ts));
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
            let ts = SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs();
            let out = args.output_dir.join(format!("sat_e2_{}_{}.wcnf", stem_str, ts));
            fs::create_dir_all(&args.output_dir).ok();
            eprintln!("  serializing...");
            let t2 = std::time::Instant::now();
            let dimacs = if args.wcnf_old { write_wcnf_old(&wcnf) } else { write_wcnf_new(&wcnf) };
            eprintln!("    serialized {:.1} MB in {:.2}s ({})",
                dimacs.len() as f64 / 1_048_576.0, t2.elapsed().as_secs_f64(),
                if args.wcnf_old { "old format" } else { "new format" });
            fs::write(&out, dimacs).expect("write wcnf");
            eprintln!("  wrote {}", out.display());
        }
    }

    eprintln!("\nNext step: solve the emitted file with a native solver.");
    eprintln!("  Decision SAT:");
    eprintln!("    kissat output/sat_e2_*.cnf");
    eprintln!("    cadical output/sat_e2_*.cnf");
    eprintln!("  MaxSAT (streams intermediate bounds, prefer these):");
    eprintln!("    EvalMaxSAT --TimeOut=3600 output/sat_e2_*.wcnf");
    eprintln!("    cashwmaxsat-core output/sat_e2_*.wcnf");
    eprintln!("    uwrmaxsat -m -v0 output/sat_e2_*.wcnf");
}

fn stem(p: &std::path::Path) -> String {
    p.file_stem().and_then(|s| s.to_str()).unwrap_or("puzzle").to_string()
}

fn decode_from_bucas_for_pinning(
    puzzle: &eternity2_core::Puzzle,
    url: &str,
) -> Vec<Option<(eternity2_core::PieceId, eternity2_core::Rotation)>> {
    use eternity2_core::Rotation;
    let n_cells = puzzle.cell_count() as usize;
    let mut out = vec![None; n_cells];
    let Some(idx) = url.find("board_edges=") else { return out };
    let blob = &url[idx + "board_edges=".len()..];
    let blob = blob.split('&').next().unwrap_or(blob);
    let bytes = blob.as_bytes();
    if bytes.len() < n_cells * 4 { return out; }
    for pos in 0..n_cells {
        let q: [u8; 4] = std::array::from_fn(|i| bytes[pos * 4 + i] - b'a');
        if q.iter().all(|&c| c == 0) { continue; }
        for piece in puzzle.pieces() {
            for rot in Rotation::ALL {
                if piece.edges.rotated(rot).as_array() == q {
                    out[pos] = Some((piece.id, rot));
                    break;
                }
            }
        }
    }
    out
}
