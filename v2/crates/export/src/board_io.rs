// Lightweight Board serializer for diagnostic dumps.
//
// Board itself only derives serde behind a feature flag; rather than turn
// that on transitively, this module dumps just what the overlap analysis
// needs: width, height, and (piece_id, rotation) per cell (null for empty).
// Round-trippable by anything that knows the puzzle.

use std::fs;
use std::io::Write;
use std::path::Path;

use eternity2_core::{Board, Puzzle, Rotation};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct DumpedBoard {
    pub width: u32,
    pub height: u32,
    pub seed: u64,
    pub score: u32,
    pub total_edges: u32,
    pub cells: Vec<Option<[u32; 2]>>,
}

impl DumpedBoard {
    #[must_use]
    pub fn from_board(board: &Board, seed: u64, score: u32, total_edges: u32) -> Self {
        let cells = board
            .cells()
            .iter()
            .map(|c| c.map(|(pid, rot)| [u32::from(pid), u32::from(rot.as_u8())]))
            .collect();
        Self {
            width: board.width(),
            height: board.height(),
            seed,
            score,
            total_edges,
            cells,
        }
    }

    #[must_use]
    pub fn to_board(&self, puzzle: &Puzzle) -> Board {
        let mut b = Board::empty(puzzle);
        for (pos, slot) in self.cells.iter().enumerate() {
            if let Some([pid, rot]) = slot {
                let rotation = Rotation::from_u8(*rot as u8).unwrap_or(Rotation::R0);
                b.place(pos as u32, *pid as u16, rotation);
            }
        }
        b
    }
}

pub fn write_dump(path: &Path, dump: &DumpedBoard) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut f = fs::File::create(path)?;
    f.write_all(serde_json::to_string(dump)?.as_bytes())?;
    f.write_all(b"\n")?;
    Ok(())
}

pub fn read_dump(path: &Path) -> std::io::Result<DumpedBoard> {
    let s = fs::read_to_string(path)?;
    serde_json::from_str(&s).map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
}
