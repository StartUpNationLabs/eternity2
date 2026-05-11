pub mod v2 {
    tonic::include_proto!("solver.v2");
}

pub mod convert;

pub use v2::*;

#[cfg(test)]
mod tests {
    use super::v2;

    #[test]
    fn event_envelope_roundtrips() {
        use prost::Message;

        let event = v2::SolverEvent {
            schema_version: 1,
            solver_run_id: 42,
            node_id: 7,
            depth: 3,
            timestamp_us: 123_456,
            body: Some(v2::solver_event::Body::Started(v2::Started {
                solver_id: "dlx".into(),
                heuristic_profile: "border_first_lcv".into(),
                puzzle_hash: "deadbeef".into(),
                seed: 1,
                started_wall_us: 0,
                config: None,
            })),
        };

        let bytes = event.encode_to_vec();
        let decoded = v2::SolverEvent::decode(&*bytes).unwrap();
        assert_eq!(decoded.schema_version, 1);
        assert_eq!(decoded.solver_run_id, 42);
    }

    #[test]
    fn path_policy_oneof_variants_compile() {
        let _ = v2::PathConfig {
            path: vec![0, 1, 2],
            hint_positions: vec![],
            hint_pieces: vec![],
            hint_rotations: vec![],
            policy: Some(v2::path_config::Policy::PrefixConstraint(
                v2::PrefixConstraintPath { k: 8 },
            )),
        };
    }
}
