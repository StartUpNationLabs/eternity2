// Audit: do the harvested plateau states preserve the 5 official E2 hints?
//
// CP places hints; localsearch/PT has no hint-pinning machinery and can
// swap any cell of the right class, including hint cells. If the dumps
// show hint cells no longer holding hint pieces, our entire pipeline is
// running an underconstrained version of the puzzle — which would
// explain plateau ambiguity AND why we sometimes see scores ABOVE 449
// (we'd be solving an easier instance).
//
// This binary reads each sample_*.json from a plateau dir, plus the
// official puzzle CSV's hints, and reports per-sample hint preservation.

use std::path::PathBuf;

use clap::Parser;
use eternity2_benchmark::board_io::read_dump;
use eternity2_benchmark::loader::load_puzzle_with_hints;

#[derive(Parser, Debug)]
#[command(name = "audit_hints", about = "Check hint preservation in harvested boards")]
struct Args {
    #[arg(long, default_value = "../data/puzzles/size_16_official_eternity.csv")]
    puzzle: PathBuf,

    #[arg(long, default_value = "default")]
    run_name: String,
}

fn main() {
    let args = Args::parse();
    let (puzzle, hints) = load_puzzle_with_hints(&args.puzzle).expect("load");
    eprintln!("=== audit_hints ===");
    eprintln!("puzzle: {}", args.puzzle.display());
    eprintln!("hints from CSV ({}):", hints.hints.len());
    for h in &hints.hints {
        let (x, y) = puzzle.xy(h.position);
        eprintln!("  pos {:>3} (x={:>2}, y={:>2})  piece={:>3}  rot={}",
            h.position, x, y, u32::from(h.piece_id), h.rotation.as_u8());
    }

    let dir = PathBuf::from("output").join("plateau").join(&args.run_name);
    let mut entries: Vec<PathBuf> = std::fs::read_dir(&dir)
        .unwrap_or_else(|e| panic!("read_dir {}: {e}", dir.display()))
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().and_then(|s| s.to_str()) == Some("json"))
        .filter(|p| p.file_name().and_then(|s| s.to_str()).map(|s| s.starts_with("sample_")).unwrap_or(false))
        .collect();
    entries.sort();
    eprintln!("\nfound {} dumps in {}", entries.len(), dir.display());
    if entries.is_empty() { return; }

    let mut totals = vec![0u32; hints.hints.len()];
    let mut totals_rot = vec![0u32; hints.hints.len()];
    let mut piece_at_anywhere = vec![0u32; hints.hints.len()];
    let mut perfect_samples = 0u32;

    eprintln!("\nper-sample audit (X = hint preserved with correct rot, P = piece there but wrong rot, p = piece elsewhere, ø = piece displaced):");
    println!("sample,score,{}", hints.hints.iter().enumerate().map(|(i, _)| format!("h{}", i)).collect::<Vec<_>>().join(","));
    for path in &entries {
        let dump = match read_dump(path) {
            Ok(d) => d,
            Err(e) => { eprintln!("skip {}: {e}", path.display()); continue; }
        };
        let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("?");
        let mut row = Vec::with_capacity(hints.hints.len());
        let mut all_perfect = true;
        for (i, h) in hints.hints.iter().enumerate() {
            let pos_idx = h.position as usize;
            let cell = dump.cells.get(pos_idx).copied().flatten();
            // Is the hint piece anywhere on this board?
            let piece_at_any = dump.cells.iter().any(|c| {
                if let Some([pid, _]) = c {
                    *pid as u16 == h.piece_id
                } else { false }
            });
            if piece_at_any { piece_at_anywhere[i] += 1; }
            match cell {
                Some([pid, rot]) if pid as u16 == h.piece_id => {
                    totals[i] += 1;
                    if rot == u32::from(h.rotation.as_u8()) {
                        totals_rot[i] += 1;
                        row.push('X');
                    } else {
                        row.push('P');
                        all_perfect = false;
                    }
                }
                _ => {
                    if piece_at_any { row.push('p'); } else { row.push('ø'); }
                    all_perfect = false;
                }
            }
        }
        if all_perfect { perfect_samples += 1; }
        eprintln!("  {}  score={:>3}  [{}]", stem, dump.score, row.iter().collect::<String>());
        println!("{},{},{}", stem, dump.score, row.iter().collect::<String>());
    }

    let n = entries.len() as u32;
    eprintln!("\n--- summary across {} samples ---", n);
    for (i, h) in hints.hints.iter().enumerate() {
        let (x, y) = puzzle.xy(h.position);
        eprintln!("  hint {}: pos=({},{}) piece={} rot={}",
            i, x, y, u32::from(h.piece_id), h.rotation.as_u8());
        eprintln!("      piece at correct position:        {:>3}/{} ({:.0}%)",
            totals[i], n, 100.0 * (totals[i] as f64) / (n as f64));
        eprintln!("      piece at correct pos AND rot:     {:>3}/{} ({:.0}%)",
            totals_rot[i], n, 100.0 * (totals_rot[i] as f64) / (n as f64));
        eprintln!("      piece present somewhere on board: {:>3}/{} ({:.0}%)",
            piece_at_anywhere[i], n, 100.0 * (piece_at_anywhere[i] as f64) / (n as f64));
    }
    eprintln!("\nsamples preserving ALL hints with correct rotation: {}/{} ({:.0}%)",
        perfect_samples, n, 100.0 * (perfect_samples as f64) / (n as f64));

    eprintln!("\nVerdict:");
    if perfect_samples == n {
        eprintln!("  ALL hints preserved in all samples. PT may not formally pin them but");
        eprintln!("  the SA acceptance criterion keeps them in place because moving them");
        eprintln!("  hurts local score. Officially correct.");
    } else if perfect_samples == 0 {
        eprintln!("  NO sample preserves all hints. We are solving an unconstrained version");
        eprintln!("  of the puzzle. Add explicit hint-pinning to PT/SA before any further");
        eprintln!("  optimisation work — scores above 449 may not even be valid E2 boards.");
    } else {
        eprintln!("  {} of {} samples preserve all hints. PT can drop them probabilistically.",
            perfect_samples, n);
        eprintln!("  Add hint pinning to remove this confound.");
    }
}
