// Vol-32 bonus: measure unsat-propagator lookup speed.
// Loads forbidden_all.bin (vol-32 output), runs N random placement
// lookups, measures per-lookup latency. Used to budget the engine
// integration in vol-33.

#![forbid(unsafe_code)]

use std::fs::File;
use std::io::{BufReader, Read};
use std::path::PathBuf;
use std::time::Instant;

const N_LITERALS: usize = 130_180;

#[derive(Debug)]
struct ForbiddenTable {
    row_starts: Vec<u32>,
    col: Vec<u32>,
    decoder: Vec<(u8, u16, u8)>,  // (field, piece_id_0_indexed, rot_0_indexed)
    encoder: Vec<i32>,            // (field, piece_id, rot) -> literal (-1 if missing)
}

fn load(path: &std::path::Path) -> ForbiddenTable {
    let f = File::open(path).expect("open");
    let mut r = BufReader::new(f);
    let mut magic = [0u8; 4];
    r.read_exact(&mut magic).unwrap();
    assert_eq!(&magic, b"UCP1", "bad magic");

    let mut n_lit_buf = [0u8; 4];
    r.read_exact(&mut n_lit_buf).unwrap();
    let n_lit = u32::from_le_bytes(n_lit_buf) as usize;
    assert_eq!(n_lit, N_LITERALS);

    let mut n_col_buf = [0u8; 4];
    r.read_exact(&mut n_col_buf).unwrap();
    let n_col = u32::from_le_bytes(n_col_buf) as usize;

    let mut row_starts = vec![0u32; n_lit + 2];
    for x in &mut row_starts {
        let mut b = [0u8; 4];
        r.read_exact(&mut b).unwrap();
        *x = u32::from_le_bytes(b);
    }

    let mut col = vec![0u32; n_col];
    for x in &mut col {
        let mut b = [0u8; 4];
        r.read_exact(&mut b).unwrap();
        *x = u32::from_le_bytes(b);
    }

    let mut decoder = vec![(0u8, 0u16, 0u8); n_lit + 1];
    for x in &mut decoder {
        let mut b = [0u8; 1];
        r.read_exact(&mut b).unwrap();
        let f_ = b[0];
        let mut p = [0u8; 2];
        r.read_exact(&mut p).unwrap();
        let pid = u16::from_le_bytes(p);
        let mut r2 = [0u8; 1];
        r.read_exact(&mut r2).unwrap();
        let rot = r2[0];
        *x = (f_, pid, rot);
    }

    // Build encoder: (field, piece, rot) -> literal. 256 fields × 256 pieces × 4 rots = 262144 entries.
    let mut encoder = vec![-1i32; 256 * 256 * 4];
    for (lit, (f_, pid, rot)) in decoder.iter().enumerate() {
        if lit == 0 {
            continue;
        }
        let idx = (*f_ as usize) * 256 * 4 + (*pid as usize) * 4 + (*rot as usize);
        if idx < encoder.len() {
            encoder[idx] = lit as i32;
        }
    }

    ForbiddenTable {
        row_starts,
        col,
        decoder,
        encoder,
    }
}

fn main() {
    let path = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "output/vol-33/forbidden_all.bin".to_string());
    let path = PathBuf::from(path);
    eprintln!("[load] reading {}", path.display());
    let t0 = Instant::now();
    let table = load(&path);
    let elapsed = t0.elapsed().as_secs_f64();
    eprintln!(
        "[load] done in {:.2}s — n_lit={} n_col={} encoder_entries={}",
        elapsed,
        table.decoder.len(),
        table.col.len(),
        table.encoder.iter().filter(|&&x| x >= 0).count(),
    );
    eprintln!(
        "[mem] CSR row_starts ~{:.1} MB + col ~{:.1} MB + decoder ~{:.1} MB + encoder ~{:.1} MB",
        (table.row_starts.len() * 4) as f64 / 1.0e6,
        (table.col.len() * 4) as f64 / 1.0e6,
        (table.decoder.len() * 4) as f64 / 1.0e6,
        (table.encoder.len() * 4) as f64 / 1.0e6,
    );

    // Benchmark: 1M random placements, time the iteration over forbidden partners.
    let n_bench = 1_000_000u64;
    let mut total_forbidden = 0u64;
    let mut state: u64 = 0xdead_beef_cafe_babe;
    let bench_t0 = Instant::now();
    for _ in 0..n_bench {
        // simple xorshift
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        // random (field, piece, rot)
        let f_ = (state >> 16) as usize % 256;
        let p = (state >> 32) as usize % 256;
        let r_ = (state >> 48) as usize % 4;
        let enc_idx = f_ * 256 * 4 + p * 4 + r_;
        let lit = table.encoder[enc_idx];
        if lit < 0 {
            continue;
        }
        let row = lit as usize;
        let s = table.row_starts[row] as usize;
        let e = table.row_starts[row + 1] as usize;
        // Iterate forbidden partners (just sum to prevent dead-code elim)
        let mut local = 0u64;
        for k in s..e {
            local += table.col[k] as u64;
        }
        total_forbidden += local;
    }
    let bench_elapsed = bench_t0.elapsed().as_secs_f64();
    eprintln!(
        "[bench] {n_bench} placements in {:.2}s = {:.0} ns/placement avg ({:.0} placements/sec)",
        bench_elapsed,
        bench_elapsed * 1.0e9 / (n_bench as f64),
        (n_bench as f64) / bench_elapsed,
    );
    eprintln!("[checksum] {total_forbidden}");

    // Sample: literal 1 forbidden partners
    let lit = 1usize;
    let s = table.row_starts[lit] as usize;
    let e = table.row_starts[lit + 1] as usize;
    eprintln!(
        "[sample] literal 1 -> (field={}, pid={}, rot={}); forbidden count = {}",
        table.decoder[lit].0,
        table.decoder[lit].1,
        table.decoder[lit].2,
        e - s,
    );
}
