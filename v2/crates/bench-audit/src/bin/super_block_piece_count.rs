// Vol-125 T5 — count per-piece occurrence across all super-cell alphabets.
//
// For each piece p ∈ 0..255, count:
//   - Number of (sc, slot) pairs where p appears as some block's piece in slot.
//   - Number of super-cells containing AT LEAST ONE block with p.
//   - Total occurrences (sum over sc, slot, block).
//
// Outputs a table sorted by total occurrences ascending. Pieces with rare
// occurrence are candidates for explicit branching.

#![forbid(unsafe_code)]

use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

const SW: usize = 8;

fn main() {
    let mut in_dir: PathBuf = "output/vol-125/w14/alphabet".into();
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--in-dir" => { in_dir = args[i + 1].clone().into(); i += 2; }
            _ => { eprintln!("Unknown arg: {}", args[i]); std::process::exit(2); }
        }
    }

    // (piece, slot) → count, ALSO (piece) → set of (sc, slot).
    let mut piece_total: BTreeMap<u16, u64> = BTreeMap::new();
    let mut piece_sc_set: BTreeMap<u16, std::collections::BTreeSet<(usize, usize)>> = BTreeMap::new();

    let t0 = Instant::now();
    let mut grand_total: u64 = 0;
    for sr in 0..SW {
        for sc in 0..SW {
            let path = in_dir.join(format!("sc_{:02}_{:02}.bin", sr, sc));
            let bytes = fs::read(&path).expect("read alphabet file");
            assert_eq!(&bytes[..4], b"W14B");
            let n = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
            let mut off = 8;
            let block_size = 4 * 2 + 4 + 4 * 2;
            grand_total += n as u64;
            for _ in 0..n {
                for slot in 0..4 {
                    let p = u16::from_le_bytes([bytes[off + 2 * slot], bytes[off + 2 * slot + 1]]);
                    *piece_total.entry(p).or_insert(0) += 1;
                    piece_sc_set.entry(p).or_default().insert((sr, sc));
                }
                off += block_size;
            }
        }
    }
    let n_pieces: u16 = 256;
    eprintln!("Loaded {} blocks across 64 super-cells in {:.1}s",
              grand_total, t0.elapsed().as_secs_f64());
    eprintln!("Total piece occurrences = {} (expected: {} × 4 = {})",
              piece_total.values().sum::<u64>(), grand_total, grand_total * 4);

    // Sort pieces by total occurrences ascending
    let mut pieces: Vec<(u16, u64, usize)> = (0..n_pieces).map(|p| {
        let t = piece_total.get(&p).copied().unwrap_or(0);
        let sc = piece_sc_set.get(&p).map(|s| s.len()).unwrap_or(0);
        (p, t, sc)
    }).collect();
    pieces.sort_by_key(|x| x.1);

    println!("\n=== Pieces sorted by total occurrence (ascending) ===");
    println!("piece_id\ttotal_occ\tn_super_cells");
    for (p, t, sc) in pieces.iter().take(30) {
        println!("{p}\t{t}\t{sc}");
    }
    println!("...");
    for (p, t, sc) in pieces.iter().rev().take(5).rev() {
        println!("{p}\t{t}\t{sc}");
    }

    // Pieces that appear in only ONE super-cell:
    let only_one_sc: Vec<&(u16, u64, usize)> = pieces.iter()
        .filter(|(_, _, sc)| *sc == 1).collect();
    println!("\nPieces appearing in only ONE super-cell: {}",
             only_one_sc.len());
    for (p, t, _) in &only_one_sc {
        if let Some(set) = piece_sc_set.get(p) {
            let (sr, sc) = *set.iter().next().unwrap();
            println!("  piece {p}: only at ({sr},{sc}), {t} block-slot occurrences");
        }
    }

    // Pieces that appear in only ONE super-cell × ONE slot:
    // (Would require reload + slot tracking; skipped here.)
}
