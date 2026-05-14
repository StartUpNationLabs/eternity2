use eternity2_core::{Board, Puzzle};

// Bucas viewer at e2.bucas.name encodes each tile as 4 letters (top, right,
// bottom, left). Color 0 (BORDER) maps to 'a'; inner colors 1..=22 map to
// 'b'..='w'. Empty cells encode as "aaaa" — same as a fully grey border tile.
fn color_to_bucas(c: u8) -> char {
    if c as usize > 22 {
        return 'a';
    }
    (b'a' + c) as char
}

#[must_use]
pub fn board_to_bucas_edges(puzzle: &Puzzle, board: &Board) -> String {
    let mut s = String::with_capacity((puzzle.cell_count() as usize) * 4);
    for pos in 0..puzzle.cell_count() {
        match board.get(pos) {
            Some((pid, rot)) => {
                if let Some(piece) = puzzle.piece(pid) {
                    let e = piece.edges.rotated(rot).as_array();
                    s.push(color_to_bucas(e[0]));
                    s.push(color_to_bucas(e[1]));
                    s.push(color_to_bucas(e[2]));
                    s.push(color_to_bucas(e[3]));
                } else {
                    s.push_str("aaaa");
                }
            }
            None => s.push_str("aaaa"),
        }
    }
    s
}

#[must_use]
pub fn bucas_url(puzzle: &Puzzle, board: &Board, puzzle_name: &str) -> String {
    let edges = board_to_bucas_edges(puzzle, board);
    format!(
        "https://e2.bucas.name/#puzzle={}&board_w={}&board_h={}&board_edges={}",
        puzzle_name, puzzle.width, puzzle.height, edges
    )
}
