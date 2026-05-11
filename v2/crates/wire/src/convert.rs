// Bidirectional conversions between proto wire types and native domain
// types. Kept in `wire` so neither the core crates nor the server need
// to know about prost.

use eternity2_core::{
    Board, CellAssignment, Edges, Hint, Hints, PathPolicy, Piece, Puzzle, Rotation,
};
use eternity2_events::{
    BacktrackCause, EventBody, EventCategory, FinalStats, SamplingCount, SelectionReason,
    SolverEvent,
};
use eternity2_solver_trait::SolveMode;

use crate::v2 as pb;

#[derive(Debug)]
pub enum ConvertError {
    BadRotation(u32),
    BadPieceId(u32),
    BadPolicy,
    BadMode(i32),
    HintArrayMismatch,
    PuzzleBuild(eternity2_core::PuzzleError),
}

impl std::fmt::Display for ConvertError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::BadRotation(r) => write!(f, "invalid rotation {r}; expected 0..3"),
            Self::BadPieceId(id) => write!(f, "piece id {id} doesn't fit u16"),
            Self::BadPolicy => f.write_str("missing or unknown path policy"),
            Self::BadMode(m) => write!(f, "unknown solve mode {m}"),
            Self::HintArrayMismatch => f.write_str(
                "hint_positions / hint_pieces / hint_rotations must have equal length",
            ),
            Self::PuzzleBuild(e) => write!(f, "puzzle: {e}"),
        }
    }
}

impl std::error::Error for ConvertError {}

pub fn puzzle_from_pb(p: pb::Puzzle) -> Result<Puzzle, ConvertError> {
    let mut pieces = Vec::with_capacity(p.pieces.len());
    for piece in p.pieces {
        let id = u16::try_from(piece.id).map_err(|_| ConvertError::BadPieceId(piece.id))?;
        // Edges expected in clockwise order top/right/bottom/left.
        let edges: Vec<u8> = piece.edges.into_iter().map(|c| c as u8).collect();
        let edges_arr = match edges.as_slice() {
            [t, r, b, l] => Edges::new(*t, *r, *b, *l),
            _ => return Err(ConvertError::PuzzleBuild(eternity2_core::PuzzleError::DimensionMismatch {
                expected: 4, got: edges.len(),
            })),
        };
        pieces.push(Piece::new(id, edges_arr));
    }
    Puzzle::new(p.width, p.height, p.color_count, pieces)
        .map_err(ConvertError::PuzzleBuild)
}

pub fn puzzle_to_pb(p: &Puzzle) -> pb::Puzzle {
    pb::Puzzle {
        width: p.width,
        height: p.height,
        color_count: p.color_count,
        pieces: p.pieces().iter().map(|piece| pb::Piece {
            id: u32::from(piece.id),
            edges: piece.edges.as_array().iter().map(|c| u32::from(*c)).collect(),
        }).collect(),
        puzzle_hash: format!("{:016x}", p.fingerprint()),
    }
}

pub fn path_policy_from_pb(c: &pb::PathConfig) -> Result<PathPolicy, ConvertError> {
    use pb::path_config::Policy;
    match &c.policy {
        Some(Policy::Strict(_)) => Ok(PathPolicy::Strict),
        Some(Policy::OrderingPrior(_)) => Ok(PathPolicy::OrderingPrior),
        Some(Policy::PrefixConstraint(pc)) => Ok(PathPolicy::PrefixConstraint { k: pc.k }),
        Some(Policy::Ignored(_)) => Ok(PathPolicy::Ignored),
        None => Err(ConvertError::BadPolicy),
    }
}

pub fn hints_from_pb(c: &pb::PathConfig) -> Result<Hints, ConvertError> {
    if c.hint_positions.len() != c.hint_pieces.len()
        || c.hint_positions.len() != c.hint_rotations.len()
    {
        return Err(ConvertError::HintArrayMismatch);
    }
    let mut hints = Vec::with_capacity(c.hint_positions.len());
    for i in 0..c.hint_positions.len() {
        let rot = Rotation::from_u8(c.hint_rotations[i] as u8)
            .ok_or(ConvertError::BadRotation(c.hint_rotations[i]))?;
        let piece_id = u16::try_from(c.hint_pieces[i])
            .map_err(|_| ConvertError::BadPieceId(c.hint_pieces[i]))?;
        hints.push(Hint { position: c.hint_positions[i], piece_id, rotation: rot });
    }
    Ok(Hints::new(hints))
}

pub fn mode_from_pb(m: i32) -> Result<SolveMode, ConvertError> {
    match pb::SolveMode::try_from(m).unwrap_or(pb::SolveMode::Unspecified) {
        pb::SolveMode::FirstSolution => Ok(SolveMode::FirstSolution),
        pb::SolveMode::AllSolutions => Ok(SolveMode::AllSolutions),
        pb::SolveMode::CountOnly => Ok(SolveMode::CountOnly),
        pb::SolveMode::Unspecified => Ok(SolveMode::FirstSolution),
    }
}

pub fn cell_to_pb(c: &CellAssignment) -> pb::CellAssignment {
    pb::CellAssignment {
        position: c.position,
        piece_id: u32::from(c.piece_id),
        rotation: u32::from(c.rotation.as_u8()),
    }
}

pub fn board_to_pb(b: &Board) -> pb::Board {
    pb::Board {
        cells: b.assignments().iter().map(cell_to_pb).collect(),
    }
}

pub fn final_stats_to_pb(s: &FinalStats) -> pb::FinalStats {
    pb::FinalStats {
        time_ms: s.time_ms,
        nodes: s.nodes,
        backtracks: s.backtracks,
        propagations: s.propagations,
        domain_wipeouts: s.domain_wipeouts,
        max_depth_seen: s.max_depth_seen,
        solutions_found: s.solutions_found,
    }
}

fn selection_reason_to_pb(r: SelectionReason) -> i32 {
    use pb::SelectionReason as P;
    let v = match r {
        SelectionReason::Unspecified => P::Unspecified,
        SelectionReason::Mrv => P::Mrv,
        SelectionReason::Degree => P::Degree,
        SelectionReason::BorderFirst => P::BorderFirst,
        SelectionReason::RareColor => P::RareColor,
        SelectionReason::PathStrict => P::PathStrict,
        SelectionReason::PathPrior => P::PathPrior,
        SelectionReason::PathPrefix => P::PathPrefix,
        SelectionReason::Random => P::Random,
        SelectionReason::DlxColumn => P::DlxColumn,
    };
    v as i32
}

fn backtrack_cause_to_pb(c: BacktrackCause) -> i32 {
    use pb::BacktrackCause as P;
    let v = match c {
        BacktrackCause::Unspecified => P::Unspecified,
        BacktrackCause::DomainWipeout => P::DomainWipeout,
        BacktrackCause::NoMatch => P::NoMatch,
        BacktrackCause::ParityFail => P::ParityFail,
        BacktrackCause::IslandFail => P::IslandFail,
        BacktrackCause::ExhaustedBranch => P::ExhaustedBranch,
    };
    v as i32
}

fn event_category_to_pb(c: EventCategory) -> i32 {
    use pb::EventCategory as P;
    let v = match c {
        EventCategory::VariableSelected => P::VariableSelected,
        EventCategory::ValueTried => P::ValueTried,
        EventCategory::ConstraintPropagated => P::ConstraintPropagated,
        EventCategory::DomainWipeout => P::DomainWipeout,
        EventCategory::BacktrackShallow => P::BacktrackShallow,
        EventCategory::PartialSolution => P::PartialSolution,
        EventCategory::Stats => P::Stats,
    };
    v as i32
}

pub fn event_to_pb(e: SolverEvent) -> pb::SolverEvent {
    use pb::solver_event::Body as B;
    let body = match e.body {
        EventBody::Started { solver_id, heuristic_profile, puzzle_fingerprint, seed, started_wall_us } => {
            B::Started(pb::Started {
                solver_id,
                heuristic_profile,
                puzzle_hash: format!("{puzzle_fingerprint:016x}"),
                seed,
                started_wall_us,
                config: None,
            })
        }
        EventBody::VariableSelected { position, domain_size, score, reason } => {
            B::VariableSelected(pb::VariableSelected {
                position, domain_size, score, reason: selection_reason_to_pb(reason),
            })
        }
        EventBody::ValueTried { position, piece_id, rotation } => {
            B::ValueTried(pb::ValueTried {
                position, piece_id: u32::from(piece_id), rotation: u32::from(rotation.as_u8()),
            })
        }
        EventBody::ConstraintPropagated { from_pos, to_pos, removed_count } => {
            B::ConstraintPropagated(pb::ConstraintPropagated { from_pos, to_pos, removed_count })
        }
        EventBody::DomainWipeout { position } => B::DomainWipeout(pb::DomainWipeout { position }),
        EventBody::Backtrack { from_depth, to_depth, cause } => B::Backtrack(pb::Backtrack {
            from_depth, to_depth, cause: backtrack_cause_to_pb(cause),
        }),
        EventBody::PartialSolution { snapshot_id, positions_cleared, cells } => {
            B::PartialSolution(pb::PartialSolution {
                snapshot_id, positions_cleared,
                cells: cells.iter().map(cell_to_pb).collect(),
            })
        }
        EventBody::Stats(s) => B::Stats(pb::Stats {
            time_ms: s.time_ms,
            nodes: s.nodes,
            backtracks: s.backtracks,
            propagations: s.propagations,
            domain_wipeouts: s.domain_wipeouts,
            current_depth: s.current_depth,
            max_depth_seen: s.max_depth_seen,
            solutions_found: s.solutions_found,
        }),
        EventBody::SampledOut { since_timestamp_us, counts } => {
            B::SampledOut(pb::SampledOut {
                since_timestamp_us,
                counts: counts.into_iter().map(|c: SamplingCount| pb::CategoryCount {
                    category: event_category_to_pb(c.category),
                    count: c.count,
                }).collect(),
            })
        }
        EventBody::Solved { board, final_stats } => B::Solved(pb::Solved {
            board: Some(board_to_pb(&board)),
            final_stats: Some(final_stats_to_pb(&final_stats)),
        }),
        EventBody::Exhausted { final_stats, solutions_found } => B::Exhausted(pb::Exhausted {
            final_stats: Some(final_stats_to_pb(&final_stats)),
            solutions_found,
        }),
        EventBody::TimedOut { final_stats, best_partial, best_depth } => B::TimedOut(pb::TimedOut {
            final_stats: Some(final_stats_to_pb(&final_stats)),
            best_partial: Some(board_to_pb(&best_partial)),
            best_depth,
        }),
        EventBody::Cancelled { final_stats, best_partial, best_depth, solutions_so_far } => {
            B::Cancelled(pb::Cancelled {
                final_stats: Some(final_stats_to_pb(&final_stats)),
                best_partial: Some(board_to_pb(&best_partial)),
                best_depth,
                solutions_so_far: solutions_so_far.iter().map(board_to_pb).collect(),
            })
        }
    };
    pb::SolverEvent {
        schema_version: e.schema_version,
        solver_run_id: e.solver_run_id,
        node_id: e.node_id,
        depth: e.depth,
        timestamp_us: e.timestamp_us,
        body: Some(body),
    }
}
