// Dump a generated puzzle CSV + its guaranteed solution as board JSON.
use eternity2_core::BORDER;
use eternity2_generator::{generate_with_solution, GeneratorConfig};
use std::io::Write;

fn color_to_binary(c: u8) -> String {
    if c == BORDER { format!("{:b}", 65535u16) } else { format!("{:b}", c as u16) }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let size: u32 = args.get(1).unwrap().parse().unwrap();
    let colors: u32 = args.get(2).unwrap().parse().unwrap();
    let seed: u64 = args.get(3).unwrap().parse().unwrap();
    let csv_path = args.get(4).unwrap().clone();
    let json_path = args.get(5).unwrap().clone();

    let (puzzle, sol) = generate_with_solution(GeneratorConfig { size, interior_colors: colors, seed }).unwrap();
    // Write the CSV in CANONICAL id order (line index == piece.id) so the
    // puzzle-io loader (which assigns id = line index) recovers the same ids
    // the solution JSON refers to. The Puzzle stores pieces in shuffled
    // order, so we must sort by id here.
    let mut ordered: Vec<_> = puzzle.pieces().iter().collect();
    ordered.sort_by_key(|p| p.id);
    let mut f = std::fs::File::create(&csv_path).unwrap();
    writeln!(f, "{}", size).unwrap();
    for piece in ordered.iter() {
        let e = piece.edges.as_array();
        writeln!(f, "{},{},{},{}", color_to_binary(e[0]), color_to_binary(e[1]),
                 color_to_binary(e[2]), color_to_binary(e[3])).unwrap();
    }
    // solution JSON: placement list with pos, piece_id, rotation
    let mut jf = std::fs::File::create(&json_path).unwrap();
    write!(jf, "{{\"placement\":[").unwrap();
    for (i, p) in sol.iter().enumerate() {
        if i>0 { write!(jf, ",").unwrap(); }
        write!(jf, "{{\"pos\":{},\"piece_id\":{},\"rotation\":{}}}",
               p.position, p.piece_id, p.rotation.as_u8()).unwrap();
    }
    write!(jf, "]}}").unwrap();
    println!("wrote {} + {}", csv_path, json_path);
}
