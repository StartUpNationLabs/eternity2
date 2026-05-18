// Vol-125 — lightweight count-only variant of sigma_break_row0.
// Avoids the HashMap, just counts internally-valid row-0 sequences.

#![forbid(unsafe_code)]

use std::fs;
use std::path::PathBuf;
use std::time::Instant;

const SW: usize = 8;
const N: usize = 0;
const E: usize = 1;
const S: usize = 2;
const W: usize = 3;
const BORDER: u8 = 0;

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
    eprintln!("=== sigma_break_row0_count (count-only, low memory) ===");
    let t = Instant::now();
    let mut alphabets: Vec<Vec<Block>> = Vec::with_capacity(SW);
    for sc in 0..SW {
        let path = in_dir.join(format!("sc_{:02}_{:02}.bin", 0, sc));
        let blocks = read_blocks(&path);
        eprintln!("  (0,{}): {} blocks", sc, blocks.len());
        alphabets.push(blocks);
    }
    eprintln!("Loaded in {:.1}s", t.elapsed().as_secs_f64());

    // Index each cell's blocks by W-edge (col1, col2) for fast lookup.
    use std::collections::HashMap;
    let mut by_west_edge: Vec<HashMap<(u8, u8), Vec<usize>>> = Vec::with_capacity(SW);
    for sc in 0..SW {
        let mut idx: HashMap<(u8, u8), Vec<usize>> = HashMap::new();
        for (i, b) in alphabets[sc].iter().enumerate() {
            if b.edge[N][0] != BORDER || b.edge[N][1] != BORDER { continue; }
            if sc == 0 && (b.edge[W][0] != BORDER || b.edge[W][1] != BORDER) { continue; }
            if sc == SW - 1 && (b.edge[E][0] != BORDER || b.edge[E][1] != BORDER) { continue; }
            let key = (b.edge[W][0], b.edge[W][1]);
            idx.entry(key).or_insert_with(Vec::new).push(i);
        }
        eprintln!("  (0,{}) W-edge index: {} distinct keys", sc, idx.len());
        by_west_edge.push(idx);
    }

    eprintln!("\nEnumerate (count only)...");
    let t = Instant::now();
    let mut count: u64 = 0;
    let mut pieces_used = [0u64; 4];

    fn bit_set(bs: &[u64; 4], p: u16) -> bool {
        (bs[(p as usize) >> 6] >> (p & 63)) & 1 == 1
    }
    fn bit_or(bs: &mut [u64; 4], p: u16) {
        bs[(p as usize) >> 6] |= 1u64 << (p & 63);
    }
    fn bit_and_not(bs: &mut [u64; 4], p: u16) {
        bs[(p as usize) >> 6] &= !(1u64 << (p & 63));
    }

    fn enumerate(
        sc: usize,
        w_constraint: Option<(u8, u8)>,
        alphabets: &[Vec<Block>],
        by_west_edge: &[HashMap<(u8, u8), Vec<usize>>],
        pieces_used: &mut [u64; 4],
        count: &mut u64,
    ) {
        if sc == SW {
            *count += 1;
            return;
        }
        let candidates: &[usize] = if let Some(k) = w_constraint {
            by_west_edge[sc].get(&k).map(|v| v.as_slice()).unwrap_or(&[])
        } else {
            // sc == 0: lookup with W = (BORDER, BORDER)
            by_west_edge[sc].get(&(BORDER, BORDER)).map(|v| v.as_slice()).unwrap_or(&[])
        };
        for &cand_idx in candidates {
            let b = &alphabets[sc][cand_idx];
            // Piece-uniqueness.
            let mut ok = true;
            for slot in 0..4 {
                if bit_set(pieces_used, b.pieces[slot]) { ok = false; break; }
            }
            if !ok { continue; }
            for slot in 0..4 { bit_or(pieces_used, b.pieces[slot]); }
            enumerate(
                sc + 1,
                Some((b.edge[E][0], b.edge[E][1])),
                alphabets,
                by_west_edge,
                pieces_used,
                count,
            );
            for slot in 0..4 { bit_and_not(pieces_used, b.pieces[slot]); }
            if *count > 1_000_000_000_000 { return; }
        }
    }

    enumerate(0, None, &alphabets, &by_west_edge, &mut pieces_used, &mut count);
    eprintln!("\nFinished in {:.1}s", t.elapsed().as_secs_f64());
    eprintln!("Row-0 internally-valid count: {}", count);
}
