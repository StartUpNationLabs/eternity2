use eternity2_core::{Hints, PathPolicy, Puzzle};
use eternity2_events::{BufferSink, SolverEvent};
use eternity2_generator::{generate, GeneratorConfig};
use eternity2_solver_naive::{NaiveSolver, Traversal};
use eternity2_solver_trait::{SolveMode, SolveOpts, SolveOutcome, Solver};
use serde::{Deserialize, Serialize};
use wasm_bindgen::prelude::*;

#[derive(Serialize, Deserialize)]
pub struct GenerateInput {
    pub size: u32,
    pub interior_colors: u32,
    pub seed: u64,
}

#[derive(Serialize)]
pub struct PieceDto {
    pub id: u32,
    pub edges: [u32; 4],
}

#[derive(Serialize)]
pub struct PuzzleDto {
    pub width: u32,
    pub height: u32,
    pub color_count: u32,
    pub pieces: Vec<PieceDto>,
    pub fingerprint: u64,
}

fn puzzle_to_dto(puzzle: &Puzzle) -> PuzzleDto {
    PuzzleDto {
        width: puzzle.width,
        height: puzzle.height,
        color_count: puzzle.color_count,
        pieces: puzzle.pieces().iter().map(|p| PieceDto {
            id: u32::from(p.id),
            edges: p.edges.as_array().map(u32::from),
        }).collect(),
        fingerprint: puzzle.fingerprint(),
    }
}

#[wasm_bindgen(js_name = generatePuzzle)]
pub fn generate_puzzle(input: JsValue) -> Result<JsValue, JsValue> {
    let input: GenerateInput = serde_wasm_bindgen::from_value(input)
        .map_err(|e| JsValue::from_str(&format!("invalid input: {e}")))?;
    let puzzle = generate(GeneratorConfig {
        size: input.size,
        interior_colors: input.interior_colors,
        seed: input.seed,
    }).map_err(|e| JsValue::from_str(&format!("generator: {e:?}")))?;
    let ser = serde_wasm_bindgen::Serializer::new()
        .serialize_large_number_types_as_bigints(true);
    puzzle_to_dto(&puzzle).serialize(&ser)
        .map_err(|e| JsValue::from_str(&format!("serialize: {e}")))
}

#[derive(Serialize, Deserialize)]
pub struct SolveInput {
    pub puzzle: PuzzleDtoIn,
    pub traversal: String,           // "row_by_row" | "spiral"
    pub time_budget_ms: u64,
    pub all_solutions: bool,
}

#[derive(Serialize, Deserialize)]
pub struct PuzzleDtoIn {
    pub width: u32,
    pub height: u32,
    pub color_count: u32,
    pub pieces: Vec<PieceDtoIn>,
}

#[derive(Serialize, Deserialize)]
pub struct PieceDtoIn {
    pub id: u32,
    pub edges: [u32; 4],
}

#[derive(Serialize)]
pub struct CellAssignmentDto {
    pub position: u32,
    pub piece_id: u32,
    pub rotation: u32,
}

#[derive(Serialize)]
#[serde(tag = "outcome", rename_all = "snake_case")]
pub enum SolveResult {
    Solved { board: Vec<CellAssignmentDto>, events: Vec<EventDto> },
    Exhausted { events: Vec<EventDto> },
    TimedOut { best_partial: Vec<CellAssignmentDto>, best_depth: u32, events: Vec<EventDto> },
    Error { message: String },
}

#[derive(Serialize)]
pub struct EventDto {
    pub node_id: u64,
    pub depth: u32,
    pub timestamp_us: u64,
    pub kind: String,
}

fn event_kind(e: &SolverEvent) -> &'static str {
    use eternity2_events::EventBody::*;
    match e.body {
        Started { .. } => "started",
        VariableSelected { .. } => "variable_selected",
        ValueTried { .. } => "value_tried",
        ConstraintPropagated { .. } => "constraint_propagated",
        DomainWipeout { .. } => "domain_wipeout",
        Backtrack { .. } => "backtrack",
        PartialSolution { .. } => "partial_solution",
        Stats(_) => "stats",
        SampledOut { .. } => "sampled_out",
        Solved { .. } => "solved",
        Exhausted { .. } => "exhausted",
        TimedOut { .. } => "timed_out",
        Cancelled { .. } => "cancelled",
    }
}

#[wasm_bindgen(js_name = solveNaive)]
pub fn solve_naive(input: JsValue) -> Result<JsValue, JsValue> {
    let input: SolveInput = serde_wasm_bindgen::from_value(input)
        .map_err(|e| JsValue::from_str(&format!("invalid input: {e}")))?;
    let pieces = input.puzzle.pieces.into_iter().map(|p| {
        let edges = p.edges.map(|c| c as u8);
        eternity2_core::Piece::new(
            p.id as u16,
            eternity2_core::Edges::new(edges[0], edges[1], edges[2], edges[3]),
        )
    }).collect();
    let puzzle = Puzzle::new(input.puzzle.width, input.puzzle.height, input.puzzle.color_count, pieces)
        .map_err(|e| JsValue::from_str(&format!("puzzle: {e}")))?;

    let traversal = match input.traversal.as_str() {
        "spiral" => Traversal::Spiral,
        _ => Traversal::RowByRow,
    };
    let mut solver = NaiveSolver::new(traversal, true);

    let opts = SolveOpts {
        mode: if input.all_solutions { SolveMode::AllSolutions } else { SolveMode::FirstSolution },
        path: Vec::new(),
        path_policy: PathPolicy::Ignored,
        hints: Hints::default(),
        seed: 0,
        time_budget_ms: input.time_budget_ms,
        max_solutions: 0,
        solver_run_id: 0,
        excluded_pieces: Vec::new(),
        preferred_pieces: Vec::new(),
        edge_bp_marginals: None,
        batch_hint_application: false,
    };

    let mut sink = BufferSink::new();
    let outcome = solver.solve(&puzzle, &opts, &mut sink);

    let events: Vec<EventDto> = sink.events.iter().map(|e| EventDto {
        node_id: e.node_id,
        depth: e.depth,
        timestamp_us: e.timestamp_us,
        kind: event_kind(e).into(),
    }).collect();

    let result = match outcome {
        SolveOutcome::Solved(board) => SolveResult::Solved {
            board: board.assignments().into_iter().map(|c| CellAssignmentDto {
                position: c.position,
                piece_id: u32::from(c.piece_id),
                rotation: u32::from(c.rotation.as_u8()),
            }).collect(),
            events,
        },
        SolveOutcome::AllSolutions(boards) => {
            let first = boards.into_iter().next();
            if let Some(b) = first {
                SolveResult::Solved {
                    board: b.assignments().into_iter().map(|c| CellAssignmentDto {
                        position: c.position,
                        piece_id: u32::from(c.piece_id),
                        rotation: u32::from(c.rotation.as_u8()),
                    }).collect(),
                    events,
                }
            } else {
                SolveResult::Exhausted { events }
            }
        }
        SolveOutcome::Exhausted => SolveResult::Exhausted { events },
        SolveOutcome::TimedOut { best_partial, best_depth } => SolveResult::TimedOut {
            best_partial: best_partial.assignments().into_iter().map(|c| CellAssignmentDto {
                position: c.position,
                piece_id: u32::from(c.piece_id),
                rotation: u32::from(c.rotation.as_u8()),
            }).collect(),
            best_depth,
            events,
        },
        SolveOutcome::Cancelled { .. } => SolveResult::Error { message: "cancelled (not reachable in wasm sync path)".into() },
        SolveOutcome::Error(m) => SolveResult::Error { message: m },
    };

    let ser = serde_wasm_bindgen::Serializer::new()
        .serialize_large_number_types_as_bigints(true);
    result.serialize(&ser)
        .map_err(|e| JsValue::from_str(&format!("serialize: {e}")))
}
