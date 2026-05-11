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

    /// Plateau-anchored mode: load a plateau JSON and pin all 205-ish
    /// unambiguous (non-mismatch-incident) cells as hints, in addition
    /// to the puzzle's 5 official hints. The 51 mismatch cells remain
    /// free. Produces a much smaller instance focused on local
    /// improvability.
    #[arg(long)]
    anchor_plateau: Option<PathBuf>,

    /// plateau_analysis JSON listing the mismatch-incident cells to
    /// leave free. Required when --anchor-plateau is set.
    #[arg(long)]
    anchor_analysis: Option<PathBuf>,
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

    if let Some(plateau_path) = &args.anchor_plateau {
        let analysis_path = args.anchor_analysis.as_ref()
            .expect("--anchor-analysis required with --anchor-plateau");
        eprintln!("\n--- plateau-anchored mode ---");
        eprintln!("plateau: {}", plateau_path.display());
        eprintln!("analysis: {}", analysis_path.display());

        let plateau_json: serde_json::Value = serde_json::from_str(
            &std::fs::read_to_string(plateau_path).expect("read plateau")
        ).expect("parse plateau");
        let analysis_json: serde_json::Value = serde_json::from_str(
            &std::fs::read_to_string(analysis_path).expect("read analysis")
        ).expect("parse analysis");

        // Collect mismatch-incident cells (these stay free).
        let mut free_cells: std::collections::BTreeSet<u32> = std::collections::BTreeSet::new();
        if let Some(comps) = analysis_json.get("components").and_then(|x| x.as_array()) {
            for c in comps {
                if let Some(cells) = c.get("cells").and_then(|x| x.as_array()) {
                    for v in cells {
                        if let Some(n) = v.as_u64() { free_cells.insert(n as u32); }
                    }
                }
            }
        }
        eprintln!("free (mismatch-incident) cells: {}", free_cells.len());

        // Load per-cell placement from plateau JSON's `placement` field
        // (preferred). Else decode the bucas URL.
        let placement: Vec<Option<(eternity2_core::PieceId, eternity2_core::Rotation)>> =
            if let Some(p) = plateau_json.get("placement").and_then(|x| x.as_array()) {
                let mut out = Vec::with_capacity(p.len());
                for entry in p {
                    if entry.is_null() { out.push(None); }
                    else {
                        let pid = entry.get("piece_id").unwrap().as_u64().unwrap() as eternity2_core::PieceId;
                        let rot_u = entry.get("rotation").unwrap().as_u64().unwrap() as u8;
                        out.push(Some((pid, eternity2_core::Rotation::from_u8(rot_u).unwrap())));
                    }
                }
                eprintln!("using enriched `placement` field");
                out
            } else {
                // Bucas decode fallback.
                let url = plateau_json.get("bucas_url").and_then(|x| x.as_str()).expect("bucas_url");
                eprintln!("decoding placement from bucas_url");
                decode_from_bucas(&puzzle, url)
            };

        // Add hints for non-free placed cells.
        let mut anchor_hints = Vec::new();
        for (pos, slot) in placement.iter().enumerate() {
            if free_cells.contains(&(pos as u32)) { continue; }
            if let Some((pid, rot)) = slot {
                anchor_hints.push(eternity2_core::Hint {
                    position: pos as u32, piece_id: *pid, rotation: *rot,
                });
            }
        }
        eprintln!("adding {} anchor hints (pinning non-mismatch cells)", anchor_hints.len());
        // Combine with existing hints (deduplicate by position).
        let mut existing_positions: std::collections::BTreeSet<u32> =
            hints.hints.iter().map(|h| h.position).collect();
        for h in anchor_hints {
            if existing_positions.insert(h.position) {
                hints.hints.push(h);
            }
        }
        eprintln!("total hints (existing + anchor): {}", hints.hints.len());
    }

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

fn decode_from_bucas(
    puzzle: &eternity2_core::Puzzle,
    bucas_url: &str,
) -> Vec<Option<(eternity2_core::PieceId, eternity2_core::Rotation)>> {
    use eternity2_core::Rotation;
    let n_cells = puzzle.cell_count() as usize;
    let mut out = vec![None; n_cells];
    let Some(idx) = bucas_url.find("board_edges=") else { return out };
    let blob = &bucas_url[idx + "board_edges=".len()..];
    let blob = blob.split('&').next().unwrap_or(blob);
    let bytes = blob.as_bytes();
    if bytes.len() < n_cells * 4 { return out; }
    for pos in 0..n_cells {
        let q: [u8; 4] = std::array::from_fn(|i| bytes[pos * 4 + i] - b'a');
        if q.iter().all(|&c| c == 0) { continue; }
        let mut found = None;
        let mut multi = false;
        'outer: for piece in puzzle.pieces() {
            for rot in Rotation::ALL {
                if piece.edges.rotated(rot).as_array() == q {
                    if found.is_some() { multi = true; break 'outer; }
                    found = Some((piece.id, rot));
                }
            }
        }
        if !multi { out[pos] = found; }
    }
    out
}
