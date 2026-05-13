// Vol-26 — measure 6×6/5-color difficulty under BorderFirstMRV+LCV.
// Sanity check: does the gate even have headroom? If MRV solves every
// puzzle with zero backtracks, the "median nodes ratio" gate condition
// can't be improved by any value-order.

#![forbid(unsafe_code)]

use eternity2_events::{EventBody, EventSink, SolverEvent};
use eternity2_generator::{generate_with_solution, GeneratorConfig};
use eternity2_solver_engine::{EngineConfig, EngineSolver};
use eternity2_solver_trait::{SolveMode, SolveOpts, Solver};

struct StatsSink {
    nodes: u64,
    backtracks: u64,
    solved: bool,
}

impl EventSink for StatsSink {
    fn emit(&mut self, e: SolverEvent) {
        match e.body {
            EventBody::Solved { final_stats, .. } => {
                self.nodes = final_stats.nodes;
                self.backtracks = final_stats.backtracks;
                self.solved = true;
            }
            EventBody::Exhausted { final_stats, .. } => {
                self.nodes = final_stats.nodes;
                self.backtracks = final_stats.backtracks;
            }
            EventBody::TimedOut { final_stats, .. } => {
                self.nodes = final_stats.nodes;
                self.backtracks = final_stats.backtracks;
            }
            _ => {}
        }
    }
}

fn measure(size: u32, colors: u32, seed: u64) -> (u64, u64, bool) {
    let (puz, _) = generate_with_solution(GeneratorConfig {
        size, interior_colors: colors, seed,
    }).expect("gen");
    let mut solver = EngineSolver::new(EngineConfig::BORDER_FIRST_LCV, "e", "m");
    let opts = SolveOpts {
        mode: SolveMode::FirstSolution,
        seed,
        time_budget_ms: 5_000,
        ..SolveOpts::default()
    };
    let mut sink = StatsSink { nodes: 0, backtracks: 0, solved: false };
    let _ = solver.solve(&puz, &opts, &mut sink);
    (sink.nodes, sink.backtracks, sink.solved)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let size: u32 = args.get(1).map(|s| s.parse().unwrap()).unwrap_or(6);
    let colors: u32 = args.get(2).map(|s| s.parse().unwrap()).unwrap_or(5);
    let n: u64 = args.get(3).map(|s| s.parse().unwrap()).unwrap_or(200);

    let mut nodes_v = Vec::with_capacity(n as usize);
    let mut bt_v = Vec::with_capacity(n as usize);
    let mut solved = 0u64;
    for seed in 1..=n {
        let (nodes, bt, ok) = measure(size, colors, seed);
        nodes_v.push(nodes);
        bt_v.push(bt);
        if ok { solved += 1; }
    }
    nodes_v.sort_unstable();
    bt_v.sort_unstable();
    let med = nodes_v[nodes_v.len() / 2];
    let p90 = nodes_v[(nodes_v.len() * 9) / 10];
    let max = *nodes_v.last().unwrap();
    let med_bt = bt_v[bt_v.len() / 2];
    let bt_zero = bt_v.iter().filter(|&&b| b == 0).count();
    println!(
        "size={size} colors={colors} n={n} solved={solved} \
         nodes: median={med} p90={p90} max={max} | backtracks: median={med_bt} zero-bt-count={bt_zero}"
    );
}
