// Vol-125 INVENTION — HR-BBB (Hint-Radiant BB&B)
//
// Phase 0: count the joint feasibility of the 5 hint cells. Each hint
// super-cell has ~5K hint-compliant blocks (alphabet pre-filtered).
// We enumerate all 5-tuples (B1, B2, B3, B4, B5) where:
//   - each B_i is a valid block at its hint cell
//   - the 20 pieces used across B1..B5 are all distinct (the 5 hint
//     pieces are already pinned; we additionally need the OTHER 3
//     slots at each hint cell to use distinct pieces from those of
//     other hint cells)
//
// If this count is tractable (≤ 10^7), we have a finite forced-prefix
// set; for each prefix, run the rest of BB&B from the hint-adjacent
// cells outward.

#![forbid(unsafe_code)]

use std::fs;
use std::path::PathBuf;
use std::time::Instant;

#[derive(Debug, Clone, Copy)]
struct Block {
    pieces: [u16; 4],
    rots: [u8; 4],
    edge: [[u8; 2]; 4],
}

fn read_blocks(path: &PathBuf) -> Vec<Block> {
    let bytes = fs::read(path).expect("read alphabet file");
    assert_eq!(&bytes[..4], b"W14B");
    let n = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
    let mut blocks = Vec::with_capacity(n);
    let mut off = 8;
    for _ in 0..n {
        let mut b = Block { pieces: [0; 4], rots: [0; 4], edge: [[0; 2]; 4] };
        for j in 0..4 {
            b.pieces[j] = u16::from_le_bytes([bytes[off + 2 * j], bytes[off + 2 * j + 1]]);
        }
        off += 8;
        for j in 0..4 { b.rots[j] = bytes[off + j]; }
        off += 4;
        for s in 0..4 {
            b.edge[s].copy_from_slice(&bytes[off..off + 2]);
            off += 2;
        }
        blocks.push(b);
    }
    blocks
}

fn main() {
    let in_dir: PathBuf = "output/vol-125/w14/alphabet".into();
    eprintln!("=== HR-BBB Phase 0: count viable 5-hint-cell joint placements ===");

    // 5 hint super-cells.
    let hint_locs: [(usize, usize); 5] = [
        (4, 3),
        (6, 1),
        (1, 1),
        (6, 6),
        (1, 6),
    ];

    let t = Instant::now();
    let alphabets: Vec<Vec<Block>> = hint_locs.iter().map(|&(sr, sc)| {
        let path = in_dir.join(format!("sc_{:02}_{:02}.bin", sr, sc));
        read_blocks(&path)
    }).collect();
    for (i, &(sr, sc)) in hint_locs.iter().enumerate() {
        eprintln!("  hint ({},{}): {} blocks", sr, sc, alphabets[i].len());
    }
    eprintln!("Loaded {} hint alphabets in {:.1}s", alphabets.len(), t.elapsed().as_secs_f64());

    // Enumerate 5-tuples with piece-disjointness across hint cells.
    // Use a 256-bit bitset for used pieces, descending into hints in order.
    let t = Instant::now();
    let mut count: u64 = 0;
    let mut chosen: [usize; 5] = [0; 5];
    let mut pieces_used = [0u64; 4]; // 256 bits

    // Helper functions for the bitset.
    fn bit_set(bs: &[u64; 4], p: u16) -> bool {
        (bs[(p as usize) >> 6] >> (p & 63)) & 1 == 1
    }
    fn bit_or(bs: &mut [u64; 4], p: u16) {
        bs[(p as usize) >> 6] |= 1u64 << (p & 63);
    }
    fn bit_and_not(bs: &mut [u64; 4], p: u16) {
        bs[(p as usize) >> 6] &= !(1u64 << (p & 63));
    }

    fn block_pieces_disjoint(b: &Block, used: &[u64; 4]) -> bool {
        for slot in 0..4 {
            if bit_set(used, b.pieces[slot]) { return false; }
        }
        true
    }
    fn block_add(b: &Block, used: &mut [u64; 4]) {
        for slot in 0..4 { bit_or(used, b.pieces[slot]); }
    }
    fn block_remove(b: &Block, used: &mut [u64; 4]) {
        for slot in 0..4 { bit_and_not(used, b.pieces[slot]); }
    }

    fn enumerate(
        depth: usize,
        alphabets: &[Vec<Block>],
        chosen: &mut [usize; 5],
        pieces_used: &mut [u64; 4],
        count: &mut u64,
        samples: &mut Vec<[usize; 5]>,
    ) {
        if depth == 5 {
            *count += 1;
            if samples.len() < 5 {
                samples.push(*chosen);
            }
            return;
        }
        let alphabet = &alphabets[depth];
        for (i, b) in alphabet.iter().enumerate() {
            if !block_pieces_disjoint(b, pieces_used) { continue; }
            block_add(b, pieces_used);
            chosen[depth] = i;
            enumerate(depth + 1, alphabets, chosen, pieces_used, count, samples);
            block_remove(b, pieces_used);
            if *count >= 10_000_000_000 { return; } // cap at 10B
        }
    }

    let mut samples: Vec<[usize; 5]> = Vec::new();
    enumerate(0, &alphabets, &mut chosen, &mut pieces_used, &mut count, &mut samples);

    eprintln!("\n5-hint-cell joint count (piece-disjoint only): {}", count);
    eprintln!("Enumeration time: {:.1}s", t.elapsed().as_secs_f64());

    if !samples.is_empty() {
        eprintln!("Sample joint placements (chosen block indices per hint cell):");
        for s in &samples {
            eprintln!("  {:?}", s);
        }
    }

    let out_path = "/tmp/hr_bbb_5tuple_count.txt";
    let _ = fs::write(out_path, format!("count={}\nelapsed={:.3}s\n", count, t.elapsed().as_secs_f64()));
    eprintln!("Saved count to {}", out_path);
}
