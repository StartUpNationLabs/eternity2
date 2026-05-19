// Generate a small Eternity-II-family puzzle and write it to CSV.
// CSV format: BORDER (color 0 in core) is encoded as 65535 to match
// data/puzzles/size_NN_official_eternity.csv format.

use eternity2_core::BORDER;
use eternity2_generator::{generate, GeneratorConfig};
use std::io::Write;

fn color_to_binary(c: u8) -> String {
    if c == BORDER {
        format!("{:b}", 65535u16)
    } else {
        format!("{:b}", c as u16)
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let size: u32 = args.get(1).map(|s| s.parse().unwrap()).unwrap_or(5);
    let colors: u32 = args.get(2).map(|s| s.parse().unwrap()).unwrap_or(6);
    let seed: u64 = args.get(3).map(|s| s.parse().unwrap()).unwrap_or(0xDEADBEEFu64);
    let out_path = args.get(4).cloned().unwrap_or_else(|| {
        format!("output/vol-126/gen_size_{}_c{}_s{}.csv", size, colors, seed)
    });

    let puzzle = generate(GeneratorConfig {
        size,
        interior_colors: colors,
        seed,
    }).expect("generate");

    if let Some(dir) = std::path::Path::new(&out_path).parent() {
        std::fs::create_dir_all(dir).ok();
    }
    let mut f = std::fs::File::create(&out_path).expect("create CSV");
    writeln!(f, "{}", size).unwrap();
    for piece in puzzle.pieces().iter() {
        let e = piece.edges.as_array();
        writeln!(f, "{},{},{},{}",
            color_to_binary(e[0]),
            color_to_binary(e[1]),
            color_to_binary(e[2]),
            color_to_binary(e[3])
        ).unwrap();
    }
    println!("Wrote {} ({}×{}, {} interior colors, {} pieces)",
             out_path, size, size, colors, puzzle.pieces().len());
}
