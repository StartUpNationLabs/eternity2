// Vol-122 N10b — 3×3 around-hint enumerator with raw-binary output.
//
// Same as n10 but writes a packed binary format to a file (BufWriter),
// avoiding SQLite locking entirely. A Python sidecar reads the file
// and indexes it into SQLite asynchronously.
//
// Record format (28 bytes, little-endian):
//   1 byte:  position_index (0..8 = 3*hr + hc)
//   For each of 9 cells:
//     2 bytes: piece_id (u16)
//     1 byte:  rotation (u8)
//   Total: 1 + 9 * 3 = 28 bytes.
//
// Flush via BufWriter every 64 KB (~2300 rows). Periodic stderr report.

#![forbid(unsafe_code)]
#![allow(clippy::too_many_arguments)]

use std::path::PathBuf;
use std::time::Instant;
use std::sync::atomic::{AtomicU64, Ordering};
use std::io::{BufWriter, Write};
use std::fs::File;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::Rotation;

const BLOCK_N: usize = 3;
const BLOCK_CELLS: usize = BLOCK_N * BLOCK_N;

#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
struct PieceSet { low: u128, high: u128 }
impl PieceSet {
    fn new() -> Self { Self { low: 0, high: 0 } }
    fn set(&mut self, pid: u16) {
        if pid < 128 { self.low |= 1u128 << pid; }
        else { self.high |= 1u128 << (pid - 128); }
    }
    fn unset(&mut self, pid: u16) {
        if pid < 128 { self.low &= !(1u128 << pid); }
        else { self.high &= !(1u128 << (pid - 128)); }
    }
    fn contains(&self, pid: u16) -> bool {
        if pid < 128 { (self.low >> pid) & 1 == 1 }
        else { (self.high >> (pid - 128)) & 1 == 1 }
    }
}

fn rot_edges(e: [u8; 4], r: u8) -> [u8; 4] {
    match r {
        0 => e,
        1 => [e[3], e[0], e[1], e[2]],
        2 => [e[2], e[3], e[0], e[1]],
        _ => [e[1], e[2], e[3], e[0]],
    }
}

#[derive(Clone, Copy, Debug)]
struct Cell { pid: u16, rot: u8, edges: [u8; 4] }

fn local_neighbors(idx: usize) -> Vec<(usize, u8, u8)> {
    let r = idx / BLOCK_N;
    let c = idx % BLOCK_N;
    let mut out = Vec::new();
    if r > 0 { out.push(((r - 1) * BLOCK_N + c, 0, 2)); }
    if c + 1 < BLOCK_N { out.push((r * BLOCK_N + (c + 1), 1, 3)); }
    if r + 1 < BLOCK_N { out.push(((r + 1) * BLOCK_N + c, 2, 0)); }
    if c > 0 { out.push((r * BLOCK_N + (c - 1), 3, 1)); }
    out
}

#[allow(clippy::too_many_arguments)]
fn recurse(
    order: &[usize],
    step: usize,
    block: &mut [Option<Cell>; BLOCK_CELLS],
    used: &mut PieceSet,
    interior_pieces: &Vec<u16>,
    pieces: &Vec<[u8; 4]>,
    hint_pids_reserved: &[u16],
    count: &AtomicU64,
    writer: &mut BufWriter<File>,
    position_idx: u8,
    last_report: &mut Instant,
) {
    if step == order.len() {
        let c = count.fetch_add(1, Ordering::Relaxed) + 1;
        // Encode and write 28 bytes
        let mut buf = [0u8; 28];
        buf[0] = position_idx;
        for i in 0..BLOCK_CELLS {
            let cell = block[i].expect("cell filled");
            let off = 1 + i * 3;
            buf[off] = (cell.pid & 0xff) as u8;
            buf[off + 1] = (cell.pid >> 8) as u8;
            buf[off + 2] = cell.rot;
        }
        writer.write_all(&buf).expect("write");
        if c % 1_000_000 == 0 {
            let now = Instant::now();
            let dt = now.duration_since(*last_report).as_secs_f64();
            *last_report = now;
            eprintln!("  position {}: count={} rate={:.0}/s",
                position_idx, c, 1_000_000.0 / dt.max(1e-6));
            std::io::stderr().flush().ok();
        }
        return;
    }
    let cell = order[step];
    for &pid in interior_pieces {
        if used.contains(pid) { continue; }
        if hint_pids_reserved.contains(&pid) { continue; }
        for rot in 0..4u8 {
            let edges = rot_edges(pieces[pid as usize], rot);
            let mut ok = true;
            for (nb_idx, this_side, nb_side) in local_neighbors(cell) {
                if let Some(nb) = block[nb_idx] {
                    if edges[this_side as usize] != nb.edges[nb_side as usize] || edges[this_side as usize] == 0 {
                        ok = false;
                        break;
                    }
                }
            }
            if !ok { continue; }
            block[cell] = Some(Cell { pid, rot, edges });
            used.set(pid);
            recurse(order, step + 1, block, used, interior_pieces, pieces, hint_pids_reserved,
                count, writer, position_idx, last_report);
            used.unset(pid);
            block[cell] = None;
        }
    }
}

fn enumerate_position(
    hint_local_r: usize,
    hint_local_c: usize,
    pieces: &Vec<[u8; 4]>,
    interior_pieces: &Vec<u16>,
    writer: &mut BufWriter<File>,
) -> u64 {
    let hint_idx = hint_local_r * BLOCK_N + hint_local_c;
    let position_idx = (hint_local_r * BLOCK_N + hint_local_c) as u8;
    let hint_pid: u16 = 138;
    let hint_rot: u8 = 0;
    let hint_edges = rot_edges(pieces[hint_pid as usize], hint_rot);

    let mut block: [Option<Cell>; BLOCK_CELLS] = [None; BLOCK_CELLS];
    block[hint_idx] = Some(Cell { pid: hint_pid, rot: hint_rot, edges: hint_edges });
    let mut used = PieceSet::new();
    used.set(hint_pid);
    let hint_pids_reserved: Vec<u16> = vec![207, 254, 180, 248];

    let mut order: Vec<usize> = Vec::new();
    let mut visited = vec![false; BLOCK_CELLS];
    visited[hint_idx] = true;
    let mut frontier: Vec<usize> = Vec::new();
    for (nb, _, _) in local_neighbors(hint_idx) { frontier.push(nb); }
    while !frontier.is_empty() {
        let mut next_frontier: Vec<usize> = Vec::new();
        for &cell in &frontier {
            if visited[cell] { continue; }
            visited[cell] = true;
            order.push(cell);
            for (nb, _, _) in local_neighbors(cell) {
                if !visited[nb] { next_frontier.push(nb); }
            }
        }
        frontier = next_frontier;
    }
    for i in 0..BLOCK_CELLS { if !visited[i] { order.push(i); } }

    eprintln!("\n=== position {}: hint at local ({},{}) ===", position_idx, hint_local_r, hint_local_c);
    eprintln!("  board cells: rows {}..={} × cols {}..={}",
        8 - hint_local_r, 8 - hint_local_r + 2,
        7 - hint_local_c, 7 - hint_local_c + 2);
    eprintln!("  fill order: {:?}", order);
    std::io::stderr().flush().ok();

    let count = AtomicU64::new(0);
    let t0 = Instant::now();
    let mut last_report = Instant::now();
    recurse(&order, 0, &mut block, &mut used, interior_pieces, pieces, &hint_pids_reserved,
        &count, writer, position_idx, &mut last_report);
    let c = count.load(Ordering::Relaxed);
    eprintln!("  position {} done: {} valid 3×3 in {:.2}s",
        position_idx, c, t0.elapsed().as_secs_f64());
    std::io::stderr().flush().ok();
    c
}

fn main() {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut out_file = PathBuf::from("output/vol-122/n10b_raw.bin");
    let mut only_position: Option<(usize, usize)> = None;

    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--out-file" => out_file = PathBuf::from(args.next().unwrap()),
            "--only-position" => {
                let s = args.next().unwrap();
                let parts: Vec<&str> = s.split(',').collect();
                only_position = Some((parts[0].parse().unwrap(), parts[1].parse().unwrap()));
            }
            other => panic!("unknown arg {other}"),
        }
    }

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    let pieces: Vec<[u8; 4]> = puzzle.pieces().iter().map(|p| {
        let e = p.edges.rotated(Rotation::R0).as_array();
        [e[0] as u8, e[1] as u8, e[2] as u8, e[3] as u8]
    }).collect();
    let interior_pieces: Vec<u16> = (0..256u16).filter(|&pid| {
        let e = pieces[pid as usize];
        e.iter().filter(|&&x| x == 0).count() == 0
    }).collect();
    eprintln!("interior pieces: {}", interior_pieces.len());

    std::fs::create_dir_all(out_file.parent().unwrap()).ok();
    let f = File::create(&out_file).expect("create out");
    let mut writer = BufWriter::with_capacity(1 << 20, f);  // 1 MB buffer

    let t_all = Instant::now();
    let mut total_count: u64 = 0;

    let positions: Vec<(usize, usize)> = if let Some(p) = only_position {
        vec![p]
    } else {
        (0..3).flat_map(|r| (0..3).map(move |c| (r, c))).collect()
    };

    for (hr, hc) in positions {
        let c = enumerate_position(hr, hc, &pieces, &interior_pieces, &mut writer);
        total_count += c;
    }

    writer.flush().expect("final flush");
    drop(writer);

    let file_size = std::fs::metadata(&out_file).map(|m| m.len()).unwrap_or(0);
    eprintln!("\n=== GRAND TOTAL ===");
    eprintln!("valid 3×3 across all positions: {}", total_count);
    eprintln!("output file: {} ({:.2} MB)", out_file.display(), file_size as f64 / 1_000_000.0);
    eprintln!("elapsed: {:.2}s", t_all.elapsed().as_secs_f64());
}
