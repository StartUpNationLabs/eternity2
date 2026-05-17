// Vol-122 A4 — DLX-XCC (Knuth Algorithm X with color-secondary items) for E2.
//
// XCC extends standard DLX:
//   - Primary items: must be covered EXACTLY once.
//   - Secondary items: each cover-node carries a COLOR. Multiple rows may
//     cover the same secondary item, but ALL such rows must agree on the
//     color. The first cover "purifies" the column to its color; subsequent
//     covers with different colors are blocked.
//
// E2 ENCODING (clean):
//   Primary items: 1 per cell (256) + 1 per piece (256) = 512.
//   Secondary items: 1 per ADJACENCY (480 for full board). Each placement
//   covers the 4 adjacencies adjacent to its cell (or fewer if at border),
//   with COLOR = the piece-rotation's edge-color on the side facing each
//   adjacency.
//
// Search finds a perfect assignment where every cell + every piece is used,
// AND every adjacency is "purified" to a single color from both sides.
// Equivalent to a 480/480 perfect Eternity-II solution.
//
// For partial-match (< 480): add SLACK piece placements that have no color
// constraints (= "this side doesn't claim color matching for this adj").
// Defer to next iter.

#![forbid(unsafe_code)]

use std::path::PathBuf;
use std::time::Instant;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_core::{Puzzle, Rotation};

#[derive(Clone, Copy, Debug)]
struct Node {
    left: usize,
    right: usize,
    up: usize,
    down: usize,
    column: usize,
    row_meta: usize,
    color: i32,         // XCC: -1 = no color, 0+ = color id
}

#[derive(Clone, Copy, Debug)]
struct Column {
    size: u32,
    primary: bool,
    purified_color: i32,  // -1 = unpurified
}

struct Dlx {
    nodes: Vec<Node>,
    columns: Vec<Column>,
    header: usize,
    solution: Vec<usize>,
    found_rows: Vec<Vec<usize>>,
    max_solutions: usize,
    nodes_visited: u64,
}

impl Dlx {
    fn new(n_cols: usize, primary_count: usize) -> Self {
        let mut nodes = Vec::with_capacity(n_cols + 1);
        let mut columns = Vec::with_capacity(n_cols + 1);

        nodes.push(Node {
            left: primary_count.max(1), right: 1,
            up: 0, down: 0, column: 0, row_meta: 0, color: -1,
        });
        columns.push(Column { size: 0, primary: false, purified_color: -1 });

        for c in 1..=n_cols {
            let primary = c <= primary_count;
            let left = c - 1;
            let right = if c == n_cols { 0 } else { c + 1 };
            nodes.push(Node {
                left, right, up: c, down: c,
                column: c, row_meta: 0, color: -1,
            });
            columns.push(Column { size: 0, primary, purified_color: -1 });
        }

        // Detach secondary columns from horizontal header chain
        if primary_count < n_cols && primary_count > 0 {
            let last_primary = primary_count;
            nodes[last_primary].right = 0;
            nodes[0].left = last_primary;
            for c in (primary_count + 1)..=n_cols {
                nodes[c].left = c;
                nodes[c].right = c;
            }
        } else if primary_count == 0 {
            nodes[0].right = 0;
            nodes[0].left = 0;
        }

        Self {
            nodes, columns, header: 0,
            solution: Vec::new(),
            found_rows: Vec::new(),
            max_solutions: 1,
            nodes_visited: 0,
        }
    }

    fn add_row(&mut self, cells: &[(usize, i32)], row_id: usize) {
        // cells: Vec of (column_idx, color). color = -1 for primary items.
        if cells.is_empty() { return; }
        let first = self.nodes.len();
        let len = cells.len();
        for (i, &(col, color)) in cells.iter().enumerate() {
            let up = self.nodes[col].up;
            let left = if i == 0 { first + len - 1 } else { first + i - 1 };
            let right = if i == len - 1 { first } else { first + i + 1 };
            let idx = self.nodes.len();
            self.nodes.push(Node {
                left, right, up, down: col,
                column: col, row_meta: row_id, color,
            });
            self.nodes[up].down = idx;
            self.nodes[col].up = idx;
            self.columns[col].size += 1;
        }
    }

    fn hide(&mut self, p: usize) {
        // Remove node p from its column
        let mut q = self.nodes[p].right;
        while q != p {
            let col = self.nodes[q].column;
            // Only hide if this row's node has uncompatible color, otherwise keep
            // For XCC: hide only when standard cover; "purify" handles secondaries.
            // Simplified: always hide (per Knuth Alg-C basic version).
            let up = self.nodes[q].up;
            let dn = self.nodes[q].down;
            self.nodes[up].down = dn;
            self.nodes[dn].up = up;
            self.columns[col].size -= 1;
            q = self.nodes[q].right;
        }
    }

    fn unhide(&mut self, p: usize) {
        let mut q = self.nodes[p].left;
        while q != p {
            let col = self.nodes[q].column;
            let up = self.nodes[q].up;
            let dn = self.nodes[q].down;
            self.nodes[up].down = q;
            self.nodes[dn].up = q;
            self.columns[col].size += 1;
            q = self.nodes[q].left;
        }
    }

    fn cover(&mut self, c: usize) {
        // PRIMARY cover: remove column c from header + hide all rows that
        // contain a node in column c.
        let l = self.nodes[c].left;
        let r = self.nodes[c].right;
        self.nodes[l].right = r;
        self.nodes[r].left = l;
        let mut i = self.nodes[c].down;
        while i != c {
            self.hide(i);
            i = self.nodes[i].down;
        }
    }

    fn uncover(&mut self, c: usize) {
        let mut i = self.nodes[c].up;
        while i != c {
            self.unhide(i);
            i = self.nodes[i].up;
        }
        let l = self.nodes[c].left;
        let r = self.nodes[c].right;
        self.nodes[l].right = c;
        self.nodes[r].left = c;
    }

    fn purify(&mut self, p: usize) {
        // XCC purify: column c gets purified to color of node p.
        // Walk DOWN the column; for each node q:
        //   - if color matches: mark with -1 (this row stays alive but this
        //     node is "consumed").
        //   - else: hide its row.
        // NOTE: we must walk the column carefully — `hide(q)` removes q from
        // its row's other columns but NOT from c itself. Standard Knuth Alg-C
        // walks via .down pointer which skips hidden rows.
        let c = self.nodes[p].column;
        let target_color = self.nodes[p].color;
        self.columns[c].purified_color = target_color;
        let mut q = self.nodes[c].down;
        while q != c {
            let next = self.nodes[q].down;
            if self.nodes[q].color != target_color {
                self.hide(q);
            } else {
                self.nodes[q].color = -1;
            }
            q = next;
        }
    }

    fn unpurify(&mut self, p: usize) {
        // Mirror of purify, walking UP.
        let c = self.nodes[p].column;
        let target_color = self.columns[c].purified_color;
        self.columns[c].purified_color = -1;
        let mut q = self.nodes[c].up;
        while q != c {
            let next = self.nodes[q].up;
            if self.nodes[q].color == -1 {
                self.nodes[q].color = target_color;
            } else {
                self.unhide(q);
            }
            q = next;
        }
    }

    fn search(&mut self) -> bool {
        self.nodes_visited += 1;
        if self.nodes[self.header].right == self.header {
            let rows: Vec<usize> = self.solution.iter()
                .map(|&n| self.nodes[n].row_meta)
                .collect();
            self.found_rows.push(rows);
            return self.found_rows.len() >= self.max_solutions;
        }

        // S-heuristic
        let mut min_size = u32::MAX;
        let mut chosen = 0;
        let mut c = self.nodes[self.header].right;
        while c != self.header {
            if self.columns[c].size < min_size {
                min_size = self.columns[c].size;
                chosen = c;
                if min_size == 0 { break; }
            }
            c = self.nodes[c].right;
        }
        if min_size == 0 { return false; }

        self.cover(chosen);
        let mut r = self.nodes[chosen].down;
        while r != chosen {
            self.solution.push(r);
            // For each node in this row, cover/purify its column
            let mut feasible = true;
            let mut covered_so_far: Vec<usize> = Vec::new();
            let mut j = self.nodes[r].right;
            while j != r {
                let col = self.nodes[j].column;
                if self.columns[col].primary {
                    self.cover(col);
                    covered_so_far.push(j);
                } else if self.nodes[j].color == -1 {
                    self.cover(col);
                    covered_so_far.push(j);
                } else {
                    let cur = self.columns[col].purified_color;
                    if cur == -1 {
                        self.purify(j);
                        covered_so_far.push(j);
                    } else if cur == self.nodes[j].color {
                        // Already purified to matching color — nothing to do
                    } else {
                        // Conflict — this row is infeasible
                        feasible = false;
                        break;
                    }
                }
                j = self.nodes[j].right;
            }
            if feasible {
                if self.search() { return true; }
            }
            self.solution.pop();
            // Unwind only what we covered, in reverse.
            for &k in covered_so_far.iter().rev() {
                let col = self.nodes[k].column;
                if self.columns[col].primary {
                    self.uncover(col);
                } else if self.nodes[k].color == -1 {
                    self.uncover(col);
                } else {
                    self.unpurify(k);
                }
            }
            r = self.nodes[r].down;
        }
        self.uncover(chosen);
        false
    }
}

// ============================================================
// E2 encoding helpers
// ============================================================

fn parse_args() -> (PathBuf, u64) {
    let mut puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
    let mut max_solutions: u64 = 1;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--puzzle" => puzzle_path = PathBuf::from(args.next().unwrap()),
            "--max-solutions" => max_solutions = args.next().unwrap().parse().unwrap(),
            "--test-4queens" => {
                test_4queens();
                std::process::exit(0);
            }
            other => panic!("unknown arg {other}"),
        }
    }
    (puzzle_path, max_solutions)
}

fn test_4queens() {
    test_nqueens(4, 2);
    test_nqueens(5, 10);
    test_nqueens(6, 4);
    test_nqueens(8, 92);
}

fn test_nqueens(n: usize, expected: usize) {
    let n_primary = n + n;
    let n_secondary = (2 * n - 1) * 2;
    let n_cols = n_primary + n_secondary;
    let mut dlx = Dlx::new(n_cols, n_primary);
    let mut row_id = 0;
    for r in 0..n {
        for c in 0..n {
            let row_item = r + 1;
            let col_item = n + c + 1;
            let up_item = 2 * n + 1 + (r + c);
            let dn_item = 2 * n + 1 + (2 * n - 1) + (r + n - 1 - c);
            // Treat diagonals as secondaries with no color (color = -1).
            // But our XCC purify expects color >= 0. So use color = 0 (same
            // color) so all queens "agree" on no-queen — which is wrong.
            // Workaround: for queens, treat diagonals as PRIMARY (must NOT
            // be covered twice — that's same as exactly-once if we don't
            // add slack rows). Or: do not use XCC for queens; use plain DLX.
            // For PoC: add diagonals as primary with the queens NOT covering
            // them more than once.
            dlx.add_row(&[(row_item, -1), (col_item, -1), (up_item, -1), (dn_item, -1)], row_id);
            row_id += 1;
        }
    }
    dlx.max_solutions = 10000;
    let t0 = Instant::now();
    let _ = dlx.search();
    let ok = if dlx.found_rows.len() == expected { "OK" } else { "FAIL" };
    println!(
        "{}-queens: {} solutions in {:?}, nodes visited: {} (expected {}, {})",
        n, dlx.found_rows.len(), t0.elapsed(), dlx.nodes_visited, expected, ok
    );
}

fn encode_e2(puzzle: &Puzzle) -> Dlx {
    let side = puzzle.width as usize;
    let n_cells = side * side;
    let n_pieces = puzzle.pieces().len();
    assert_eq!(n_cells, n_pieces);

    // Adjacencies: indexed 0..(2 * side * (side - 1))
    // Horizontal: (r, c) ↔ (r, c+1) for c in 0..side-1
    // Vertical:   (r, c) ↔ (r+1, c) for r in 0..side-1
    let n_h_adj = side * (side - 1);
    let n_v_adj = (side - 1) * side;
    let n_adj = n_h_adj + n_v_adj;

    let h_adj_index = |r: usize, c: usize| -> usize { r * (side - 1) + c };
    let v_adj_index = |r: usize, c: usize| -> usize { n_h_adj + r * side + c };

    let n_primary = n_cells + n_pieces;
    let n_cols = n_primary + n_adj;
    println!(
        "encoding: cells={}, pieces={}, adj={}, total_cols={}",
        n_cells, n_pieces, n_adj, n_cols
    );

    let mut dlx = Dlx::new(n_cols, n_primary);

    // Place each piece × rotation at each cell:
    let mut n_rows = 0;
    for cell in 0..n_cells {
        let r = cell / side;
        let c = cell % side;
        for pid in 0..n_pieces {
            for rot in Rotation::ALL {
                let edges_rotated = puzzle.pieces()[pid].edges
                    .rotated(rot).as_array();
                let top = edges_rotated[0];
                let right_e = edges_rotated[1];
                let bottom = edges_rotated[2];
                let left = edges_rotated[3];

                // Border consistency: top side at r==0 must be color 0 (border);
                // bottom side at r==side-1 must be 0; right at c==side-1 must
                // be 0; left at c==0 must be 0. Non-border sides cannot be 0.
                if r == 0 && top != 0 { continue; }
                if r != 0 && top == 0 { continue; }
                if r == side - 1 && bottom != 0 { continue; }
                if r != side - 1 && bottom == 0 { continue; }
                if c == 0 && left != 0 { continue; }
                if c != 0 && left == 0 { continue; }
                if c == side - 1 && right_e != 0 { continue; }
                if c != side - 1 && right_e == 0 { continue; }

                let mut row_items: Vec<(usize, i32)> = Vec::with_capacity(6);
                row_items.push((1 + cell, -1));
                row_items.push((1 + n_cells + pid, -1));
                // Adjacencies:
                //   top side connects to cell (r-1, c) via vertical adj (r-1, c)
                //   bottom side connects to (r+1, c) via vertical adj (r, c)
                //   left side connects to (r, c-1) via horizontal adj (r, c-1)
                //   right side connects to (r, c+1) via horizontal adj (r, c)
                if r > 0 {
                    let adj = v_adj_index(r - 1, c);
                    row_items.push((1 + n_primary + adj, top as i32));
                }
                if r < side - 1 {
                    let adj = v_adj_index(r, c);
                    row_items.push((1 + n_primary + adj, bottom as i32));
                }
                if c > 0 {
                    let adj = h_adj_index(r, c - 1);
                    row_items.push((1 + n_primary + adj, left as i32));
                }
                if c < side - 1 {
                    let adj = h_adj_index(r, c);
                    row_items.push((1 + n_primary + adj, right_e as i32));
                }

                dlx.add_row(&row_items, n_rows);
                if std::env::var("DLX_DEBUG").is_ok() {
                    eprintln!("row #{}: cell={} pid={} rot={:?} items={:?}", n_rows, cell, pid, rot, row_items);
                }
                n_rows += 1;
            }
        }
    }
    println!("rows added: {}", n_rows);
    dlx
}

fn main() {
    let (puzzle_path, max_solutions) = parse_args();
    println!("vol-122 A4 — DLX-XCC for E2");
    println!("puzzle: {}", puzzle_path.display());

    let (puzzle, _hints) = load_puzzle_with_hints(&puzzle_path).expect("load");
    println!("loaded puzzle: side={} pieces={}", puzzle.width, puzzle.pieces().len());

    let t_enc = Instant::now();
    let mut dlx = encode_e2(&puzzle);
    println!("encoding took: {:?}", t_enc.elapsed());

    dlx.max_solutions = max_solutions as usize;
    println!("\nsearch starting (max_solutions={})...", max_solutions);
    let t_search = Instant::now();
    let _ = dlx.search();
    let elapsed = t_search.elapsed();
    println!(
        "\nsearch done: {} solutions in {:?}, nodes visited: {}",
        dlx.found_rows.len(), elapsed, dlx.nodes_visited
    );
    if !dlx.found_rows.is_empty() {
        println!("first solution rows: {}", dlx.found_rows[0].len());
    }
}
