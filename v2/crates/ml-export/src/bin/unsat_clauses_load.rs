// Vol-32 bootstrap (matures into vol-33 T1).
// Loads capiman/e2's literal-decoder table + one or more CNF.gz files
// into an in-memory forbidden-pair index. Prints throughput + memory
// stats. Does NOT integrate with the engine yet — that's vol-33.
//
// Schema:
//   e2_info.c: text rows `{ idx, field, card, rotation, pn, pe, ps, pw }`.
//     literal=idx (1-indexed). field=0..255, card=1..256, rotation=1..4.
//   *.cnf.gz: text lines `-X -Y 0`. X, Y in 1..130180.
//
// Output:
//   CSR-style forbidden table: row_starts[L+1], col[K] (both u32).
//   Plus the (field, piece, rot) decoder Vec<(u8, u8, u8)>.
//
// Run: target/release/unsat-clauses-load --info output/capiman_e2/e2_info.c \
//         --cnf 'output/capiman_e2/*.cnf.gz' --out output/vol-33/forbidden.bin

#![forbid(unsafe_code)]

use std::fs::File;
use std::io::{BufRead, BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

use flate2::read::GzDecoder;

const N_LITERALS: usize = 130_180;

fn parse_info(path: &Path) -> Vec<(u8, u16, u8)> {
    // Returns Vec<(field, piece_id_0_indexed, rot_0_indexed)> indexed by literal.
    // literal 0 is unused (CNF is 1-indexed); we put a zero tuple there.
    let mut out = vec![(0u8, 0u16, 0u8); N_LITERALS + 1];
    let f = File::open(path).expect("open e2_info.c");
    let reader = BufReader::new(f);
    let mut parsed = 0u64;
    for line in reader.lines() {
        let line = line.unwrap();
        let s = line.trim();
        if !s.starts_with('{') {
            continue;
        }
        // strip braces and trailing comma/whitespace
        let s = s.trim_start_matches('{').trim_end_matches(',').trim();
        let s = s.trim_end_matches('}').trim();
        let parts: Vec<&str> = s.split(',').map(str::trim).collect();
        if parts.len() < 4 {
            continue;
        }
        let idx: usize = match parts[0].parse() {
            Ok(v) => v,
            Err(_) => continue,
        };
        let field: u8 = match parts[1].parse() {
            Ok(v) => v,
            Err(_) => continue,
        };
        let card: u16 = match parts[2].parse() {
            Ok(v) => v,
            Err(_) => continue,
        };
        let rot: u8 = match parts[3].parse() {
            Ok(v) => v,
            Err(_) => continue,
        };
        if idx == 0 || idx > N_LITERALS {
            continue;
        }
        // 1-indexed card → 0-indexed piece_id
        // 1-indexed rotation → 0-indexed
        out[idx] = (field, card.saturating_sub(1), rot.saturating_sub(1));
        parsed += 1;
    }
    eprintln!("[info] parsed {parsed} rows");
    out
}

fn parse_cnf_gz(path: &Path) -> Vec<(u32, u32)> {
    let f = File::open(path).expect("open cnf.gz");
    let gz = GzDecoder::new(f);
    let reader = BufReader::new(gz);
    let mut pairs: Vec<(u32, u32)> = Vec::new();
    for line in reader.lines() {
        let line = line.unwrap();
        let s = line.trim();
        if s.is_empty() {
            continue;
        }
        // Lines like "-X -Y 0"
        let mut it = s.split_whitespace();
        let a: i32 = match it.next().and_then(|t| t.parse().ok()) {
            Some(v) => v,
            None => continue,
        };
        let b: i32 = match it.next().and_then(|t| t.parse().ok()) {
            Some(v) => v,
            None => continue,
        };
        let term: i32 = match it.next().and_then(|t| t.parse().ok()) {
            Some(v) => v,
            None => continue,
        };
        if term != 0 || a >= 0 || b >= 0 {
            continue;
        }
        pairs.push(((-a) as u32, (-b) as u32));
    }
    pairs
}

fn build_csr(pairs: &[(u32, u32)]) -> (Vec<u32>, Vec<u32>) {
    // CSR: row_starts[L+1] and col[]. Each pair (a, b) adds b to a's list and a to b's list.
    // 1-indexed: literal 0 is unused.
    let n = N_LITERALS + 1;
    // count degrees
    let mut deg = vec![0u32; n];
    for &(a, b) in pairs {
        deg[a as usize] += 1;
        deg[b as usize] += 1;
    }
    // exclusive prefix sum into row_starts
    let mut row_starts = vec![0u32; n + 1];
    for i in 0..n {
        row_starts[i + 1] = row_starts[i] + deg[i];
    }
    let total = row_starts[n] as usize;
    let mut col = vec![0u32; total];
    // refill deg as cursor
    let mut cursor = row_starts.clone();
    for &(a, b) in pairs {
        let p = cursor[a as usize] as usize;
        col[p] = b;
        cursor[a as usize] += 1;
        let p = cursor[b as usize] as usize;
        col[p] = a;
        cursor[b as usize] += 1;
    }
    (row_starts, col)
}

fn main() {
    let mut info_path = PathBuf::from("output/capiman_e2/e2_info.c");
    let mut cnf_paths: Vec<PathBuf> = Vec::new();
    let mut out_path: Option<PathBuf> = None;
    let mut sample = false;
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "--info" => {
                info_path = PathBuf::from(&raw[i + 1]);
                i += 2;
            }
            "--cnf" => {
                cnf_paths.push(PathBuf::from(&raw[i + 1]));
                i += 2;
            }
            "--out" => {
                out_path = Some(PathBuf::from(&raw[i + 1]));
                i += 2;
            }
            "--sample" => {
                // Run on the 3 smallest CNF files only (smoke test).
                sample = true;
                i += 1;
            }
            other => panic!("unknown arg: {other}"),
        }
    }

    let t0 = Instant::now();
    eprintln!("[info] reading {}", info_path.display());
    let decoder = parse_info(&info_path);
    eprintln!("[info] decoder built in {:.2}s, {} entries", t0.elapsed().as_secs_f64(), decoder.len());

    if sample && cnf_paths.is_empty() {
        // auto-find 3 smallest .cnf.gz under output/capiman_e2/
        let dir = info_path.parent().unwrap();
        let mut entries: Vec<(PathBuf, u64)> = std::fs::read_dir(dir)
            .unwrap()
            .filter_map(|e| {
                let p = e.ok()?.path();
                if p.extension()?.to_str()? == "gz" {
                    let sz = p.metadata().ok()?.len();
                    Some((p, sz))
                } else {
                    None
                }
            })
            .collect();
        entries.sort_by_key(|e| e.1);
        for (p, _) in entries.into_iter().take(3) {
            cnf_paths.push(p);
        }
    }

    let mut all_pairs: Vec<(u32, u32)> = Vec::new();
    for p in &cnf_paths {
        let t1 = Instant::now();
        let pairs = parse_cnf_gz(p);
        eprintln!(
            "[cnf] {}: {} pairs in {:.2}s",
            p.file_name().unwrap().to_str().unwrap(),
            pairs.len(),
            t1.elapsed().as_secs_f64(),
        );
        all_pairs.extend(pairs);
    }
    eprintln!("[total] {} pairs from {} files", all_pairs.len(), cnf_paths.len());

    let t_csr = Instant::now();
    let (row_starts, col) = build_csr(&all_pairs);
    eprintln!(
        "[csr] built in {:.2}s, |col|={} ({:.1} MB)",
        t_csr.elapsed().as_secs_f64(),
        col.len(),
        (col.len() * 4) as f64 / 1.0e6,
    );

    // Stats
    let mut degrees: Vec<u32> = (0..N_LITERALS + 1)
        .map(|i| row_starts[i + 1] - row_starts[i])
        .collect();
    degrees.sort_unstable();
    let nonempty = degrees.iter().filter(|&&d| d > 0).count();
    let med = degrees[degrees.len() / 2];
    let max = *degrees.iter().max().unwrap();
    let mean = col.len() as f64 / nonempty.max(1) as f64;
    eprintln!(
        "[stats] {} literals with forbidden partners; median deg {} max {} mean {:.0}",
        nonempty, med, max, mean,
    );

    if let Some(out) = out_path {
        // Binary dump: header (n_literals, n_col), row_starts (u32), col (u32), decoder (field u8, pid u16, rot u8 — 4 bytes each).
        if let Some(parent) = out.parent() {
            std::fs::create_dir_all(parent).ok();
        }
        let f = File::create(&out).expect("create out");
        let mut w = BufWriter::new(f);
        // magic + version
        w.write_all(b"UCP1").unwrap();
        w.write_all(&(N_LITERALS as u32).to_le_bytes()).unwrap();
        w.write_all(&(col.len() as u32).to_le_bytes()).unwrap();
        // row_starts
        for r in &row_starts {
            w.write_all(&r.to_le_bytes()).unwrap();
        }
        // col
        for c in &col {
            w.write_all(&c.to_le_bytes()).unwrap();
        }
        // decoder
        for (f_, p_, r_) in &decoder {
            w.write_all(&[*f_]).unwrap();
            w.write_all(&p_.to_le_bytes()).unwrap();
            w.write_all(&[*r_]).unwrap();
        }
        eprintln!("[out] wrote {}", out.display());
    }
}

// silence the unused-import warning when --sample isn't run
fn _unused() {
    let mut _r = Vec::<u8>::new();
    let _ = std::io::Cursor::new(&mut _r).read(&mut [0u8; 0]);
}
