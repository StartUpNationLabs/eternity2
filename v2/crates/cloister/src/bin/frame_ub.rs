// frame_ub — LP upper bound on II+IB for a FIXED frame (vol-212).
//
// Assignment relaxation with per-edge color linearization (the cloister
// border-MIP z-var trick lifted to the interior): continuous x[cell,p,r],
// both-way assignment rows, z[edge,color] ≤ side-supplies, rim sides score
// x directly against the frame target. Optional --hints fixes the 5 hint
// placements. SOUND upper bound on II+IB (LP ≥ best integer); rank frames
// by admitted ceiling, and calibrate on the Bucas-469 control
// (integer witness II+IB = 409).
//
// Usage: frame_ub <frame.json|dir> [--hints] [--time-limit-secs N]

#![forbid(unsafe_code)]

use std::path::PathBuf;

use eternity2_benchmark::loader::load_puzzle_with_hints;
use eternity2_cloister::frame;
use eternity2_cloister::model::InteriorModel;
use good_lp::{
    constraint, solvers::highs::highs, Expression, ProblemVariables, Solution, SolverModel,
    Variable, variable,
};

#[allow(clippy::too_many_lines)]
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let get = |flag: &str| -> Option<String> {
        args.iter()
            .position(|a| a == flag)
            .and_then(|i| args.get(i + 1).cloned())
    };
    let hinted = args.iter().any(|a| a == "--hints");
    let time_limit: f64 = get("--time-limit-secs").and_then(|s| s.parse().ok()).unwrap_or(600.0);
    let target = args
        .first()
        .filter(|a| !a.starts_with("--"))
        .expect("usage: frame_ub <frame.json|dir>");

    let puzzle_path = PathBuf::from(
        get("--puzzle").unwrap_or_else(|| "../data/puzzles/size_16_official_eternity.csv".into()),
    );
    let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("puzzle");
    let model = InteriorModel::from_puzzle(&puzzle, &hints);

    let path = PathBuf::from(target);
    let files: Vec<PathBuf> = if path.is_dir() {
        let mut v: Vec<PathBuf> = std::fs::read_dir(&path)
            .expect("dir")
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.extension().is_some_and(|e| e == "json"))
            .collect();
        v.sort();
        v
    } else {
        vec![path]
    };

    for f in files {
        let fr = match frame::load(&f, &puzzle) {
            Ok(fr) => fr,
            Err(e) => {
                eprintln!("skip {}: {e}", f.display());
                continue;
            }
        };
        let ub = lp_ub(&model, &fr.targets, hinted, time_limit);
        println!(
            "{}\tbb={}\thinted={}\tII+IB_LP_UB={:.2}\ttotal_UB={:.2}",
            fr.label,
            fr.bb,
            hinted,
            ub,
            ub + f64::from(fr.bb)
        );
    }
}

fn lp_ub(
    model: &InteriorModel,
    targets: &eternity2_cloister::model::RimTargets,
    hinted: bool,
    time_limit: f64,
) -> f64 {
    let n = model.n;
    let cells = model.cells;
    let np = model.np;
    let mut prob = ProblemVariables::new();
    // x[cell][pid][rot]
    let mut x = vec![vec![[None::<Variable>; 4]; np]; cells];
    for c in 0..cells {
        for p in 0..np {
            for r in 0..4 {
                x[c][p][r] = Some(prob.add(variable().min(0.0).max(1.0)));
            }
        }
    }
    let xv = |c: usize, p: usize, r: usize| x[c][p][r].expect("var");

    // horizontal & vertical II edges with shared color vars
    struct Edge {
        a: usize,
        b: usize,
        /// side of a facing b, side of b facing a
        sa: usize,
        sb: usize,
    }
    let mut edges = Vec::new();
    for y in 0..n {
        for xx in 0..n {
            let c = y * n + xx;
            if xx + 1 < n {
                edges.push(Edge { a: c, b: c + 1, sa: 1, sb: 3 });
            }
            if y + 1 < n {
                edges.push(Edge { a: c, b: c + n, sa: 2, sb: 0 });
            }
        }
    }
    // colors present on interior piece sides
    let mut colors: Vec<u8> = Vec::new();
    for p in 0..np {
        for r in 0..4 {
            for s in 0..4 {
                let col = model.rot_edges[p][r][s];
                if !colors.contains(&col) {
                    colors.push(col);
                }
            }
        }
    }

    let mut obj = Expression::from(0.0);
    let mut constraints: Vec<good_lp::Constraint> = Vec::new();

    // assignment
    for c in 0..cells {
        let mut s = Expression::from(0.0);
        for p in 0..np {
            for r in 0..4 {
                s += xv(c, p, r);
            }
        }
        constraints.push(constraint!(s == 1.0));
    }
    for p in 0..np {
        let mut s = Expression::from(0.0);
        for c in 0..cells {
            for r in 0..4 {
                s += xv(c, p, r);
            }
        }
        constraints.push(constraint!(s == 1.0));
    }

    // z per edge per color
    for e in &edges {
        let mut zsum = Expression::from(0.0);
        for &col in &colors {
            let z = prob.add(variable().min(0.0).max(1.0));
            let mut sup_a = Expression::from(0.0);
            let mut sup_b = Expression::from(0.0);
            for p in 0..np {
                for r in 0..4 {
                    if model.rot_edges[p][r][e.sa] == col {
                        sup_a += xv(e.a, p, r);
                    }
                    if model.rot_edges[p][r][e.sb] == col {
                        sup_b += xv(e.b, p, r);
                    }
                }
            }
            constraints.push(constraint!(z - sup_a <= 0.0));
            constraints.push(constraint!(z - sup_b <= 0.0));
            zsum += z;
            obj += z;
        }
        constraints.push(constraint!(zsum <= 1.0));
    }

    // rim sides: coefficient on x where the oriented side matches the target
    for c in 0..cells {
        for s in 0..4 {
            if let Some(t) = targets[c][s] {
                for p in 0..np {
                    for r in 0..4 {
                        if model.rot_edges[p][r][s] == t {
                            obj += xv(c, p, r);
                        }
                    }
                }
            }
        }
    }

    if hinted {
        for &(cell, pid, rot) in &model.hints {
            constraints.push(constraint!(xv(cell, pid, rot as usize) == 1.0));
        }
    }

    let mut m = prob.maximise(obj.clone()).using(highs);
    m = m.set_time_limit(time_limit);
    m = m.set_parallel(good_lp::solvers::highs::HighsParallelType::On);
    for c in constraints {
        m = m.with(c);
    }
    let sol = m.solve().expect("LP solve");
    sol.eval(&obj)
}
