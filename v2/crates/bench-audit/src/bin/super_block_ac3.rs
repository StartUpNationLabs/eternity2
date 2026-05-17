// W14 step 2: AC-3 over super-cell alphabets.
//
// Load each super-cell's alphabet (written by super_block_enum), index each
// block by its 4 boundary tuples (N, E, S, W) — each tuple is a pair of colors.
// Iteratively prune: a block at sc (sr, sc) is removed if its `side` tuple
// doesn't appear in any block at the neighbor super-cell's `opposite-side`
// boundary set.
//
// Output: pruned alphabets in output/w14/alphabet_ac3/

use std::collections::{HashMap, HashSet};
use std::fs;
use std::io::{BufWriter, Read, Write};
use std::path::PathBuf;
use std::time::Instant;

const SW: usize = 8;

#[derive(Debug, Clone, Copy)]
struct Block {
    pieces: [u16; 4],
    rots: [u8; 4],
    n_edge: [u8; 2],
    e_edge: [u8; 2],
    s_edge: [u8; 2],
    w_edge: [u8; 2],
}

fn read_blocks(path: &PathBuf) -> Vec<Block> {
    let bytes = fs::read(path).expect("read alphabet file");
    assert_eq!(&bytes[..4], b"W14B");
    let n = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
    let mut blocks = Vec::with_capacity(n);
    let mut off = 8;
    let block_size = 4 * 2 + 4 + 2 + 2 + 2 + 2;
    for _ in 0..n {
        let mut b = Block {
            pieces: [0; 4], rots: [0; 4],
            n_edge: [0; 2], e_edge: [0; 2], s_edge: [0; 2], w_edge: [0; 2],
        };
        for j in 0..4 {
            b.pieces[j] = u16::from_le_bytes([bytes[off], bytes[off + 1]]);
            off += 2;
        }
        for j in 0..4 { b.rots[j] = bytes[off + j]; }
        off += 4;
        b.n_edge.copy_from_slice(&bytes[off..off + 2]); off += 2;
        b.e_edge.copy_from_slice(&bytes[off..off + 2]); off += 2;
        b.s_edge.copy_from_slice(&bytes[off..off + 2]); off += 2;
        b.w_edge.copy_from_slice(&bytes[off..off + 2]); off += 2;
        blocks.push(b);
    }
    assert_eq!(blocks.len(), n);
    blocks
}

fn write_blocks(blocks: &[Block], path: &PathBuf) -> std::io::Result<()> {
    let mut f = BufWriter::new(fs::File::create(path)?);
    f.write_all(b"W14B")?;
    f.write_all(&(blocks.len() as u32).to_le_bytes())?;
    for b in blocks {
        for p in &b.pieces { f.write_all(&p.to_le_bytes())?; }
        f.write_all(&b.rots)?;
        f.write_all(&b.n_edge)?;
        f.write_all(&b.e_edge)?;
        f.write_all(&b.s_edge)?;
        f.write_all(&b.w_edge)?;
    }
    f.flush()
}

/// For one alphabet, compute the SET of boundary tuples on each side.
fn boundary_sets(blocks: &[Block]) -> [HashSet<(u8, u8)>; 4] {
    let mut sets = [HashSet::new(), HashSet::new(), HashSet::new(), HashSet::new()];
    for b in blocks {
        sets[0].insert((b.n_edge[0], b.n_edge[1]));
        sets[1].insert((b.e_edge[0], b.e_edge[1]));
        sets[2].insert((b.s_edge[0], b.s_edge[1]));
        sets[3].insert((b.w_edge[0], b.w_edge[1]));
    }
    sets
}

/// Filter blocks where each side-tuple is in the corresponding allowed set.
/// allowed[s] = Some(&Set) means side s must be in that set.
fn filter_blocks(
    blocks: &[Block],
    allowed: &[Option<&HashSet<(u8, u8)>>; 4],
) -> Vec<Block> {
    let mut out = Vec::with_capacity(blocks.len());
    for b in blocks {
        let nt = (b.n_edge[0], b.n_edge[1]);
        let et = (b.e_edge[0], b.e_edge[1]);
        let st = (b.s_edge[0], b.s_edge[1]);
        let wt = (b.w_edge[0], b.w_edge[1]);
        let mut ok = true;
        if let Some(s) = allowed[0] { if !s.contains(&nt) { ok = false; } }
        if ok { if let Some(s) = allowed[1] { if !s.contains(&et) { ok = false; } } }
        if ok { if let Some(s) = allowed[2] { if !s.contains(&st) { ok = false; } } }
        if ok { if let Some(s) = allowed[3] { if !s.contains(&wt) { ok = false; } } }
        if ok { out.push(*b); }
    }
    out
}

fn main() {
    let mut in_dir: PathBuf = "output/w14/alphabet".into();
    let mut out_dir: PathBuf = "output/w14/alphabet_ac3".into();
    let mut max_iters: u32 = 10;

    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--in-dir" => { in_dir = args[i + 1].clone().into(); i += 2; }
            "--out-dir" => { out_dir = args[i + 1].clone().into(); i += 2; }
            "--max-iters" => { max_iters = args[i + 1].parse().unwrap(); i += 2; }
            _ => { eprintln!("Unknown arg: {}", args[i]); std::process::exit(2); }
        }
    }

    fs::create_dir_all(&out_dir).expect("create out dir");

    eprintln!("Loading alphabets from {}...", in_dir.display());
    let t_load = Instant::now();
    let mut alphabets: HashMap<(usize, usize), Vec<Block>> = HashMap::new();
    for sr in 0..SW {
        for sc in 0..SW {
            let path = in_dir.join(format!("sc_{:02}_{:02}.bin", sr, sc));
            let blocks = read_blocks(&path);
            alphabets.insert((sr, sc), blocks);
        }
    }
    let total_initial: usize = alphabets.values().map(|v| v.len()).sum();
    eprintln!("  Loaded {} total blocks in {:.1}s",
        total_initial, t_load.elapsed().as_secs_f64());

    // AC-3 loop
    let side_dirs: [(isize, isize); 4] = [(-1, 0), (0, 1), (1, 0), (0, -1)];
    let opposite: [usize; 4] = [2, 3, 0, 1]; // N→S, E→W, S→N, W→E

    for iter in 0..max_iters {
        let t_iter = Instant::now();
        // Compute boundary sets for all super-cells
        let bsets: HashMap<(usize, usize), [HashSet<(u8, u8)>; 4]> = alphabets
            .iter()
            .map(|(k, v)| (*k, boundary_sets(v)))
            .collect();

        let mut total_removed: usize = 0;
        let mut new_alphabets = HashMap::new();
        for ((sr, sc), blocks) in &alphabets {
            let mut allowed: [Option<&HashSet<(u8, u8)>>; 4] = [None, None, None, None];
            for side in 0..4 {
                let (dr, dc) = side_dirs[side];
                let nr = *sr as isize + dr;
                let nc = *sc as isize + dc;
                if nr < 0 || nc < 0 || nr >= SW as isize || nc >= SW as isize {
                    continue;
                }
                let nbr = (nr as usize, nc as usize);
                if let Some(nb_bsets) = bsets.get(&nbr) {
                    allowed[side] = Some(&nb_bsets[opposite[side]]);
                }
            }
            let filtered = filter_blocks(blocks, &allowed);
            let removed = blocks.len() - filtered.len();
            total_removed += removed;
            new_alphabets.insert((*sr, *sc), filtered);
        }
        alphabets = new_alphabets;
        let total: usize = alphabets.values().map(|v| v.len()).sum();
        eprintln!(
            "  iter {}: total={} (removed {}, {:.1}s)",
            iter + 1, total, total_removed, t_iter.elapsed().as_secs_f64()
        );
        if total_removed == 0 { break; }
        // Early exit if any super-cell empty (UNSAT)
        for ((sr, sc), v) in &alphabets {
            if v.is_empty() {
                eprintln!("\nUNSAT! super-cell ({sr},{sc}) has empty alphabet after iter {}",
                    iter + 1);
                return;
            }
        }
    }

    // Final sizes
    eprintln!("\nFinal per-super-cell sizes (sorted ascending):");
    let mut sizes: Vec<((usize, usize), usize)> =
        alphabets.iter().map(|(k, v)| (*k, v.len())).collect();
    sizes.sort_by_key(|x| x.1);
    for ((sr, sc), n) in &sizes {
        eprintln!("  ({sr},{sc}): {}", n);
    }
    let final_total: usize = sizes.iter().map(|x| x.1).sum();
    eprintln!("\nFinal total: {} (was {})", final_total, total_initial);
    eprintln!("Reduction: {:.1}x", total_initial as f64 / final_total.max(1) as f64);

    // Write back
    eprintln!("\nWriting pruned alphabets to {}...", out_dir.display());
    for ((sr, sc), blocks) in &alphabets {
        let path = out_dir.join(format!("sc_{:02}_{:02}.bin", sr, sc));
        write_blocks(blocks, &path).expect("write");
    }
    eprintln!("Done.");
}
