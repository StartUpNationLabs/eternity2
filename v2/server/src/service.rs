use std::pin::Pin;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

use eternity2_events::{EventSink, SolverEvent, ThrottleConfig, ThrottledSink};
use eternity2_solver_engine::EngineSolver;
use eternity2_solver_naive::{NaiveSolver, Traversal};
use eternity2_solver_portfolio::{run_parallel, PortfolioEntry};
use eternity2_solver_trait::{SolveOpts, Solver};
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;
use tokio_stream::Stream;
use tonic::{Request, Response, Status};
use wire::convert::{event_to_pb, hints_from_pb, mode_from_pb, path_policy_from_pb, puzzle_from_pb};
use wire::solver_service_server::SolverService;
use wire::{
    CancelRequest, CancelResponse, HealthResponse, HeuristicProfileEntry, ListSolversRequest,
    ListSolversResponse, ServingStatus, SolveRequest, SolverEntry, SupportedPathPolicy,
};

// One running solve: cancel flag the server-side handler flips when the
// client drops the stream or sends an explicit Cancel.
struct ActiveRun {
    cancel: Arc<AtomicBool>,
}

#[derive(Clone)]
pub struct SolverServiceImpl {
    runs: Arc<Mutex<std::collections::HashMap<u64, ActiveRun>>>,
    next_run_id: Arc<AtomicU64>,
}

impl SolverServiceImpl {
    pub fn new() -> Self {
        Self {
            runs: Arc::new(Mutex::new(std::collections::HashMap::new())),
            next_run_id: Arc::new(AtomicU64::new(1)),
        }
    }

    fn instantiate(&self, solver_id: &str, profile: &str) -> Option<Box<dyn Solver>> {
        match (solver_id, profile) {
            ("naive", "row_by_row") => Some(Box::new(NaiveSolver::row_by_row())),
            ("naive", "spiral") => Some(Box::new(NaiveSolver::spiral())),
            ("naive", "strict_path") => Some(Box::new(NaiveSolver::new(Traversal::StrictPath, true))),
            ("engine", "border_first_lcv") => Some(Box::new(EngineSolver::border_first_lcv())),
            ("engine", "rare_color_first") => Some(Box::new(EngineSolver::rare_color_first())),
            ("engine", "border_first_random") => Some(Box::new(EngineSolver::border_first_random())),
            ("engine", "border_first_parity") => Some(Box::new(EngineSolver::border_first_parity())),
            ("engine", "border_first_full") => Some(Box::new(EngineSolver::border_first_full())),
            ("engine", "border_first_lcv_par") => Some(Box::new(EngineSolver::border_first_lcv_par())),
            ("engine", "border_first_full_par") => Some(Box::new(EngineSolver::border_first_full_par())),
            ("engine", "border_first_gacolor") => Some(Box::new(EngineSolver::border_first_gacolor())),
            ("engine", "border_first_gacolor_par") => Some(Box::new(EngineSolver::border_first_gacolor_par())),
            ("engine", "chess_gacolor") => Some(Box::new(EngineSolver::chess_gacolor())),
            ("engine", "chess_gacolor_par") => Some(Box::new(EngineSolver::chess_gacolor_par())),
            ("engine", "chess_gacolor_ac3") => Some(Box::new(EngineSolver::chess_gacolor_ac3())),
            ("engine", "gacolor_symbreak") => Some(Box::new(EngineSolver::gacolor_symbreak())),
            ("engine", "gacolor_symbreak_par") => Some(Box::new(EngineSolver::gacolor_symbreak_par())),
            ("engine", "gacolor_ac3") => Some(Box::new(EngineSolver::gacolor_ac3())),
            ("engine", "gacolor_ac3_par") => Some(Box::new(EngineSolver::gacolor_ac3_par())),
            ("engine", "gacolor_ac3_random_par") => Some(Box::new(EngineSolver::gacolor_ac3_random_par())),
            ("engine", "gacolor_ac3_lcv") => Some(Box::new(EngineSolver::gacolor_ac3_lcv())),
            ("engine", "gacolor_ac3_lcv_par") => Some(Box::new(EngineSolver::gacolor_ac3_lcv_par())),
            ("engine", "gacolor_ac3_ns1") => Some(Box::new(EngineSolver::gacolor_ac3_ns1())),
            ("engine", "gacolor_ac3_ns1_par") => Some(Box::new(EngineSolver::gacolor_ac3_ns1_par())),
            ("engine", "verhaard_preferred") => Some(Box::new(EngineSolver::verhaard_preferred())),
            ("engine", "verhaard_preferred_par") => Some(Box::new(EngineSolver::verhaard_preferred_par())),
            ("engine", "joe_depth150") => Some(Box::new(EngineSolver::joe_depth150())),
            ("engine", "joe_depth150_par") => Some(Box::new(EngineSolver::joe_depth150_par())),
            ("engine", "joe_depth150_bp") => Some(Box::new(EngineSolver::joe_depth150_bp())),
            ("engine", "joe_depth150_bp_par") => Some(Box::new(EngineSolver::joe_depth150_bp_par())),
            ("engine", "joe_depth150_bp_rec") => Some(Box::new(EngineSolver::joe_depth150_bp_rec())),
            ("engine", "joe_depth150_bp_rec_par") => Some(Box::new(EngineSolver::joe_depth150_bp_rec_par())),
            ("engine", "joe_depth150_bp_rec_layered") => Some(Box::new(EngineSolver::joe_depth150_bp_rec_layered())),
            ("engine", "joe_depth150_bp_rec_layered_par") => Some(Box::new(EngineSolver::joe_depth150_bp_rec_layered_par())),

            // Vol-15 — Blackwood profiles need an Arc<BlackwoodSchedule>
            // injected into EngineSolver; today's (solver_id, profile)
            // pair lacks a place to carry it through the SolveRequest
            // proto. They are listed in ListSolvers for discoverability,
            // but Solve returns InvalidArgument until vol-17 ships a
            // SolveRequest schedule attachment (or a JSON config
            // overlay per the Cat-8 design decision).
            ("engine", "blackwood_base")
            | ("engine", "blackwood_base_par")
            | ("engine", "blackwood_raw")
            | ("engine", "blackwood_raw_par") => None,

            _ => None,
        }
    }
}

type SolveStream = Pin<Box<dyn Stream<Item = Result<wire::SolverEvent, Status>> + Send>>;

#[tonic::async_trait]
impl SolverService for SolverServiceImpl {
    type SolveStream = SolveStream;

    async fn solve(&self, request: Request<SolveRequest>) -> Result<Response<SolveStream>, Status> {
        let req = request.into_inner();
        let puzzle_pb = req.puzzle.ok_or_else(|| Status::invalid_argument("missing puzzle"))?;
        let puzzle = puzzle_from_pb(puzzle_pb)
            .map_err(|e| Status::invalid_argument(format!("{e}")))?;
        let path_config = req.path_config.unwrap_or_default();
        let path_policy = path_policy_from_pb(&path_config)
            .unwrap_or(eternity2_core::PathPolicy::Ignored);
        let hints = hints_from_pb(&path_config)
            .map_err(|e| Status::invalid_argument(format!("{e}")))?;
        let mode = mode_from_pb(req.mode)
            .map_err(|e| Status::invalid_argument(format!("{e}")))?;

        if req.selections.is_empty() {
            return Err(Status::invalid_argument("at least one solver selection required"));
        }

        let mut entries = Vec::with_capacity(req.selections.len());
        for sel in req.selections {
            let solver = self.instantiate(&sel.solver_id, &sel.heuristic_profile)
                .ok_or_else(|| {
                    // Blackwood profiles are listed but not yet wired up
                    // for server-side instantiation (no schedule attachment
                    // in SolveRequest yet — see V2_DESIGN.md
                    // "Strategy composition (vol-16)" for the deferred
                    // proto change).
                    if sel.solver_id == "engine"
                        && sel.heuristic_profile.starts_with("blackwood_")
                    {
                        Status::invalid_argument(format!(
                            "profile ({}, {}) requires a BlackwoodSchedule attachment which is not yet wired into SolveRequest. Use the bench harnesses (run_e2_blackwood) for now; server-side support lands in vol-17.",
                            sel.solver_id, sel.heuristic_profile
                        ))
                    } else {
                        Status::invalid_argument(format!(
                            "unknown solver/profile: ({}, {})",
                            sel.solver_id, sel.heuristic_profile
                        ))
                    }
                })?;
            let run_id = self.next_run_id.fetch_add(1, Ordering::Relaxed);
            entries.push(PortfolioEntry {
                solver,
                opts: SolveOpts {
                    mode,
                    path: path_config.path.clone(),
                    path_policy,
                    hints: hints.clone(),
                    seed: sel.seed,
                    time_budget_ms: req.time_budget_ms,
                    max_solutions: req.max_solutions,
                    solver_run_id: run_id,
                    excluded_pieces: Vec::new(),
                    preferred_pieces: Vec::new(),
                    edge_bp_marginals: None,
                    batch_hint_application: false,
                },
            });
        }

        let cancel = Arc::new(AtomicBool::new(false));
        // Register the cancel flag under the *first* solver_run_id so an
        // explicit Cancel RPC can locate it. The stream-drop path also
        // flips the flag via the ReceiverStream drop.
        let registered_id = entries[0].opts.solver_run_id;
        self.runs.lock().unwrap().insert(registered_id, ActiveRun { cancel: cancel.clone() });

        let (tx, rx) = mpsc::channel::<Result<wire::SolverEvent, Status>>(1024);
        let runs = self.runs.clone();

        let stop_on_first = matches!(mode, eternity2_solver_trait::SolveMode::FirstSolution);
        tokio::task::spawn_blocking(move || {
            let mut adapter = ChannelSink { tx, cancel: cancel.clone() };
            // Server-side default throttling = wire profile, unless the
            // client explicitly overrides (TODO Step 6.1: honor request
            // throttle config; defaults are correct for now).
            let mut throttled = ThrottledSink::new(adapter, ThrottleConfig::wire());
            let _report = run_parallel(&puzzle, entries, &mut throttled, cancel, stop_on_first);
            adapter = throttled.into_inner();
            drop(adapter);
            runs.lock().unwrap().remove(&registered_id);
        });

        Ok(Response::new(Box::pin(ReceiverStream::new(rx)) as SolveStream))
    }

    async fn cancel(&self, request: Request<CancelRequest>) -> Result<Response<CancelResponse>, Status> {
        let req = request.into_inner();
        let mut already_terminal = true;
        let mut runs = self.runs.lock().unwrap();
        if req.solver_run_id == 0 {
            for run in runs.values() {
                run.cancel.store(true, Ordering::SeqCst);
            }
            already_terminal = runs.is_empty();
            runs.clear();
        } else if let Some(run) = runs.remove(&req.solver_run_id) {
            run.cancel.store(true, Ordering::SeqCst);
            already_terminal = false;
        }
        Ok(Response::new(CancelResponse { already_terminal }))
    }

    async fn list_solvers(&self, _: Request<ListSolversRequest>) -> Result<Response<ListSolversResponse>, Status> {
        let all_policies = vec![
            SupportedPathPolicy::OrderingPrior as i32,
            SupportedPathPolicy::PrefixConstraint as i32,
            SupportedPathPolicy::Ignored as i32,
        ];
        let naive_policies = vec![
            SupportedPathPolicy::Strict as i32,
            SupportedPathPolicy::Ignored as i32,
        ];

        let entries = vec![
            SolverEntry {
                solver_id: "naive".into(),
                display_name: "Naive DFS".into(),
                description: "Educational depth-first search. Strict path or simple cell ordering.".into(),
                supported_path_policies: naive_policies,
                heuristic_profiles: vec![
                    HeuristicProfileEntry {
                        id: "row_by_row".into(),
                        display_name: "Row by row".into(),
                        description: "Fills cells left-to-right, top-to-bottom.".into(),
                        is_default: true,
                    },
                    HeuristicProfileEntry {
                        id: "spiral".into(),
                        display_name: "Spiral".into(),
                        description: "Fills the outer ring, then spirals inward.".into(),
                        is_default: false,
                    },
                ],
            },
            SolverEntry {
                solver_id: "engine".into(),
                display_name: "Backtracker with propagation".into(),
                description: "Domain-pruning backtracker with edge-color + piece-uniqueness propagation. The default research solver.".into(),
                supported_path_policies: all_policies,
                heuristic_profiles: vec![
                    HeuristicProfileEntry {
                        id: "border_first_lcv".into(),
                        display_name: "Border first".into(),
                        description: "Default. Picks corners and edges before inner cells.".into(),
                        is_default: true,
                    },
                    HeuristicProfileEntry {
                        id: "rare_color_first".into(),
                        display_name: "Rare color first".into(),
                        description: "Border first; ties broken by globally rare edge colors.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "border_first_random".into(),
                        display_name: "Border first + random".into(),
                        description: "Border first; ties broken randomly (seeded). Adds portfolio diversity.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "border_first_parity".into(),
                        display_name: "Border first + parity".into(),
                        description: "Adds checkerboard color-balance pruning on top of border_first_lcv.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "border_first_full".into(),
                        display_name: "Border first + parity + island".into(),
                        description: "All propagators enabled: edge color, piece uniqueness, class balance, parity, island.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "border_first_lcv_par".into(),
                        display_name: "Border first (multi-core)".into(),
                        description: "Root-split work-stealing over all CPU cores. Same algorithm as legacy v3_par.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "border_first_full_par".into(),
                        display_name: "Border first + parity + island (multi-core)".into(),
                        description: "All propagators + multi-core root-split.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "gacolor_ac3".into(),
                        display_name: "GAColor + AC-3".into(),
                        description: "Symmetric-alldiff per color + arc-consistency. Strongest baseline propagation.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "gacolor_ac3_par".into(),
                        display_name: "GAColor + AC-3 (multi-core)".into(),
                        description: "GAColor + AC-3 with multi-core root-split.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "gacolor_ac3_ns1".into(),
                        display_name: "GAColor + AC-3 + NS-1".into(),
                        description: "Adds Hopfer 2022 multiset-equality (border-interior color balance).".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "gacolor_ac3_ns1_par".into(),
                        display_name: "GAColor + AC-3 + NS-1 (multi-core)".into(),
                        description: "GAColor + AC-3 + NS-1 with multi-core root-split.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "joe_depth150".into(),
                        display_name: "Joe-Saunders depth-gate (150)".into(),
                        description: "GAColor + AC-3 + NS-1 with Step-8 propagators only at depth ≥ 150.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "joe_depth150_par".into(),
                        display_name: "Joe-Saunders depth-gate (multi-core)".into(),
                        description: "Joe-Saunders depth-gate with multi-core root-split.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "joe_depth150_bp".into(),
                        display_name: "Joe-Saunders + edge-BP value-order".into(),
                        description: "Joe-Saunders depth-gate + vol-12 edge-color BP marginals as value-order. Caller must populate SolveOpts.edge_bp_marginals.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "joe_depth150_bp_par".into(),
                        display_name: "Joe-Saunders + edge-BP (multi-core)".into(),
                        description: "Edge-BP value-order with multi-core root-split.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "joe_depth150_bp_rec".into(),
                        display_name: "Joe-Saunders + edge-BP + hint-rectangle skeleton".into(),
                        description: "joe_depth150_bp + auto-built hint-rectangle path that places the 4 outermost hints + spoke-to-centre cells first. Requires ≥4 hints; no-op otherwise. Vol-14 win on canonical E2.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "joe_depth150_bp_rec_par".into(),
                        display_name: "Joe-Saunders + edge-BP + rectangle (multi-core)".into(),
                        description: "Multi-core variant of joe_depth150_bp_rec.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "joe_depth150_bp_rec_layered".into(),
                        display_name: "Joe-Saunders + edge-BP + layered skeleton".into(),
                        description: "Vol-14 layered hint-rectangle (rect → interior → annulus → border) ordering.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "joe_depth150_bp_rec_layered_par".into(),
                        display_name: "Joe-Saunders + edge-BP + layered (multi-core)".into(),
                        description: "Multi-core variant of joe_depth150_bp_rec_layered.".into(),
                        is_default: false,
                    },
                    // Vol-9 — Verhaard preferred-pieces phase-1 ordering.
                    HeuristicProfileEntry {
                        id: "verhaard_preferred".into(),
                        display_name: "Verhaard preferred-pieces".into(),
                        description: "Loads deferred + worst good-set pieces into early placements. Requires SolveOpts.preferred_pieces.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "verhaard_preferred_par".into(),
                        display_name: "Verhaard preferred-pieces (multi-core)".into(),
                        description: "Multi-core variant of verhaard_preferred.".into(),
                        is_default: false,
                    },
                    // Border-first + GAColor pre-search alldiff feasibility.
                    HeuristicProfileEntry {
                        id: "border_first_gacolor".into(),
                        display_name: "Border first + GAColor".into(),
                        description: "Border-first MRV with symmetric-alldiff per color (lighter than gacolor_ac3).".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "border_first_gacolor_par".into(),
                        display_name: "Border first + GAColor (multi-core)".into(),
                        description: "Multi-core variant of border_first_gacolor.".into(),
                        is_default: false,
                    },
                    // CHESS heuristic from Ansótegui et al. CP'08.
                    HeuristicProfileEntry {
                        id: "chess_gacolor".into(),
                        display_name: "CHESS + GAColor".into(),
                        description: "CHESS variable order (corners → borders → interior spiral by checkerboard parity) + GAColor.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "chess_gacolor_par".into(),
                        display_name: "CHESS + GAColor (multi-core)".into(),
                        description: "Multi-core variant of chess_gacolor.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "chess_gacolor_ac3".into(),
                        display_name: "CHESS + GAColor + AC-3".into(),
                        description: "CHESS variable order + GAColor + arc-consistency.".into(),
                        is_default: false,
                    },
                    // GAColor + symmetry break standalone.
                    HeuristicProfileEntry {
                        id: "gacolor_symbreak".into(),
                        display_name: "GAColor + symbreak".into(),
                        description: "GAColor with rotational-symmetry break only (no AC-3).".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "gacolor_symbreak_par".into(),
                        display_name: "GAColor + symbreak (multi-core)".into(),
                        description: "Multi-core variant of gacolor_symbreak.".into(),
                        is_default: false,
                    },
                    // GAColor + AC-3 with seeded random tie-break, useful
                    // for portfolio diversification.
                    HeuristicProfileEntry {
                        id: "gacolor_ac3_random_par".into(),
                        display_name: "GAColor + AC-3 + random (multi-core)".into(),
                        description: "GAColor + AC-3 with seeded random tie-break.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "gacolor_ac3_lcv".into(),
                        display_name: "GAColor + AC-3 + LCV".into(),
                        description: "GAColor + AC-3 with least-constraining-value value order.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "gacolor_ac3_lcv_par".into(),
                        display_name: "GAColor + AC-3 + LCV (multi-core)".into(),
                        description: "Multi-core variant of gacolor_ac3_lcv.".into(),
                        is_default: false,
                    },
                    // Vol-15 — Blackwood algorithm profiles. Listed for
                    // discoverability but require a BlackwoodSchedule
                    // attachment which is not yet wired into SolveRequest;
                    // server returns InvalidArgument on Solve. Use the
                    // run_e2_blackwood bench harness in the meantime.
                    HeuristicProfileEntry {
                        id: "blackwood_base".into(),
                        display_name: "Blackwood (base) — schedule required, not yet wired".into(),
                        description: "Vol-15 Blackwood 2020 algorithm: heuristic-side schedule + break-index allowance. Server Solve returns InvalidArgument until vol-17 ships schedule attachment. Use run_e2_blackwood bench bin.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "blackwood_base_par".into(),
                        display_name: "Blackwood (base, multi-core) — schedule required, not yet wired".into(),
                        description: "Multi-core variant of blackwood_base. Server-side not yet wired (see blackwood_base).".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "blackwood_raw".into(),
                        display_name: "Blackwood RAW (no exact-match props) — schedule required, not yet wired".into(),
                        description: "Vol-15 break-tolerant Blackwood: drops AC-3/GAColor/NS-1 (unsound under break-index). 55x throughput vs baseline. Server-side not yet wired.".into(),
                        is_default: false,
                    },
                    HeuristicProfileEntry {
                        id: "blackwood_raw_par".into(),
                        display_name: "Blackwood RAW (multi-core) — schedule required, not yet wired".into(),
                        description: "Multi-core variant of blackwood_raw. 650k nps on canonical E2. Server-side not yet wired.".into(),
                        is_default: false,
                    },
                ],
            },
        ];

        Ok(Response::new(ListSolversResponse { entries, schema_version: 1 }))
    }

    async fn health(&self, _: Request<()>) -> Result<Response<HealthResponse>, Status> {
        Ok(Response::new(HealthResponse {
            status: ServingStatus::Serving as i32,
            version: env!("CARGO_PKG_VERSION").into(),
            schema_version: 1,
        }))
    }
}

// Bridge: solver-portfolio uses EventSink trait, but the tonic stream is
// async. We translate via a blocking_send on the tokio channel; if the
// channel is full or closed the solver sees should_continue() = false.
struct ChannelSink {
    tx: mpsc::Sender<Result<wire::SolverEvent, Status>>,
    cancel: Arc<AtomicBool>,
}

impl EventSink for ChannelSink {
    fn emit(&mut self, event: SolverEvent) {
        // try_send to avoid blocking the rayon thread on a slow consumer.
        // If the channel is full we drop the event silently; the throttle
        // layer should keep volume low enough that this is rare.
        let _ = self.tx.try_send(Ok(event_to_pb(event)));
    }

    fn should_continue(&self) -> bool {
        !self.cancel.load(Ordering::Relaxed) && !self.tx.is_closed()
    }
}
