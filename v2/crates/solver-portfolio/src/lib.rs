#![forbid(unsafe_code)]

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use crossbeam_channel::{Receiver, Sender};
use eternity2_core::Puzzle;
use eternity2_events::{EventSink, SolverEvent};
use eternity2_solver_trait::{SolveOpts, SolveOutcome, Solver};

// One entry in a portfolio submission. The runner spawns one worker per
// entry; the worker streams events through a channel back to the merger.
pub struct PortfolioEntry {
    pub solver: Box<dyn Solver>,
    pub opts: SolveOpts,
}

pub struct PortfolioReport {
    pub outcomes: Vec<(u64, SolveOutcome)>,
}

// Run all entries in parallel. Events from all workers are forwarded to
// `merged_sink` on the calling thread (so the sink doesn't need to be
// Sync). Workers cancel cooperatively if any worker reports Solved (in
// FirstSolution mode) or if the caller asks via the cancel flag.
pub fn run_parallel<S: EventSink + Send>(
    puzzle: &Puzzle,
    entries: Vec<PortfolioEntry>,
    merged_sink: &mut S,
    cancel: Arc<AtomicBool>,
    stop_on_first: bool,
) -> PortfolioReport {
    let n = entries.len();
    let (tx, rx): (Sender<WorkerMsg>, Receiver<WorkerMsg>) = crossbeam_channel::unbounded();
    let any_solved = Arc::new(AtomicBool::new(false));

    let outcomes = std::sync::Mutex::new(Vec::<(u64, SolveOutcome)>::with_capacity(n));

    rayon::scope(|scope| {
        for entry in entries {
            let tx = tx.clone();
            let cancel = cancel.clone();
            let any_solved = any_solved.clone();
            let outcomes = &outcomes;
            scope.spawn(move |_| {
                let mut entry = entry;
                let run_id = entry.opts.solver_run_id;
                let mut sink = ChannelSink {
                    tx: tx.clone(),
                    run_id,
                    cancel: cancel.clone(),
                    any_solved: any_solved.clone(),
                    stop_on_first,
                };
                let outcome = entry.solver.solve(puzzle, &entry.opts, &mut sink);
                if stop_on_first && matches!(outcome, SolveOutcome::Solved(_)) {
                    any_solved.store(true, Ordering::SeqCst);
                }
                outcomes.lock().unwrap().push((run_id, outcome));
                // Drop the tx clone so the receiver can eventually finish.
                drop(tx);
            });
        }
        drop(tx);

        // Drain events on the main thread, forwarding to the merged sink.
        while let Ok(msg) = rx.recv() {
            match msg {
                WorkerMsg::Event(ev) => merged_sink.emit(ev),
            }
            if !merged_sink.should_continue() {
                cancel.store(true, Ordering::SeqCst);
            }
        }
    });

    PortfolioReport { outcomes: outcomes.into_inner().unwrap() }
}

enum WorkerMsg {
    Event(SolverEvent),
}

struct ChannelSink {
    tx: Sender<WorkerMsg>,
    #[allow(dead_code)]
    run_id: u64,
    cancel: Arc<AtomicBool>,
    any_solved: Arc<AtomicBool>,
    stop_on_first: bool,
}

impl EventSink for ChannelSink {
    fn emit(&mut self, event: SolverEvent) {
        let _ = self.tx.send(WorkerMsg::Event(event));
    }
    fn should_continue(&self) -> bool {
        if self.cancel.load(Ordering::Relaxed) { return false; }
        if self.stop_on_first && self.any_solved.load(Ordering::Relaxed) { return false; }
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_events::BufferSink;
    use eternity2_generator::{generate, GeneratorConfig};
    use eternity2_solver_engine::EngineSolver;
    use eternity2_solver_naive::NaiveSolver;

    #[test]
    fn portfolio_runs_in_parallel_and_first_wins() {
        let puzzle = generate(GeneratorConfig { size: 4, interior_colors: 4, seed: 9 }).unwrap();
        let entries = vec![
            PortfolioEntry {
                solver: Box::new(NaiveSolver::row_by_row()),
                opts: SolveOpts { solver_run_id: 1, ..Default::default() },
            },
            PortfolioEntry {
                solver: Box::new(EngineSolver::border_first_lcv()),
                opts: SolveOpts { solver_run_id: 2, ..Default::default() },
            },
        ];
        let mut sink = BufferSink::new();
        let cancel = Arc::new(AtomicBool::new(false));
        let report = run_parallel(&puzzle, entries, &mut sink, cancel, true);
        assert!(report.outcomes.iter().any(|(_, o)| matches!(o, SolveOutcome::Solved(_))));
        assert!(!sink.events.is_empty());
        // Events are tagged with solver_run_id so the merger can demux.
        let run_ids: std::collections::HashSet<u64> = sink.events.iter().map(|e| e.solver_run_id).collect();
        assert!(run_ids.contains(&1) && run_ids.contains(&2),
            "events should come from both runs; got {run_ids:?}");
    }
}
