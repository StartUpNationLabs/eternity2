// Dump a generated puzzle to the legacy CSV format that
// vanilla_fast / engine bins read.
//
// Format (per eternity2-puzzle-io):
//   line 1: size N
//   lines 2..N²+1: top,right,bottom,left,x,y,rotation
// where each color is a 16-bit binary string ("1111111111111111" for BORDER,
// "0000000000000001" for color 1, etc.), x/y/rotation are hint-position
// (0,0,0 for non-hint pieces).
//
// Usage:
//   dump_puzzle_csv --size 16 --colors 22 --seed 1 --out /tmp/p.csv

use std::path::PathBuf;

use eternity2_core::BORDER;
use eternity2_generator::{generate, GeneratorConfig};

fn color_to_binary(c: u8) -> String {
    if c == BORDER {
        "1".repeat(16)
    } else {
        format!("{:016b}", c as u32)
    }
}

fn main() {
    let mut size: u32 = 16;
    let mut colors: u32 = 22;
    let mut seed: u64 = 1;
    let mut out = PathBuf::from("/tmp/p.csv");
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--size" => size = args.next().unwrap().parse().unwrap(),
            "--colors" => colors = args.next().unwrap().parse().unwrap(),
            "--seed" => seed = args.next().unwrap().parse().unwrap(),
            "--out" => out = PathBuf::from(args.next().unwrap()),
            other => panic!("unknown arg {other}"),
        }
    }

    let puzzle = generate(GeneratorConfig {
        size,
        interior_colors: colors,
        seed,
    })
    .expect("generate");

    let mut s = String::new();
    s.push_str(&format!("{}\n", size));
    for piece in puzzle.pieces() {
        let e = piece.edges.as_array();
        s.push_str(&format!(
            "{},{},{},{},0,0,0\n",
            color_to_binary(e[0]),
            color_to_binary(e[1]),
            color_to_binary(e[2]),
            color_to_binary(e[3])
        ));
    }
    if let Some(p) = out.parent() {
        std::fs::create_dir_all(p).ok();
    }
    std::fs::write(&out, s).expect("write csv");
    eprintln!(
        "[dump] {} pieces × size {} colors {} seed {} → {}",
        puzzle.pieces().len(),
        size,
        colors,
        seed,
        out.display()
    );
}
