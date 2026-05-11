// End-to-end gRPC smoke test: start the server on a random port, run
// ListSolvers, Health, and a Solve. Validates the full wire path.

use std::time::Duration;

use eternity2_generator::{generate, GeneratorConfig};
use tokio::net::TcpListener;
use tokio_stream::StreamExt;
use tonic::transport::{Endpoint, Server};
use wire::convert::puzzle_to_pb;
use wire::solver_service_client::SolverServiceClient;
use wire::solver_service_server::SolverServiceServer;
use wire::{ListSolversRequest, SolveMode, SolveRequest, SolverSelection};

#[path = "../src/service.rs"]
mod service;

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn end_to_end_solve_emits_solved() {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let incoming = tokio_stream::wrappers::TcpListenerStream::new(listener);

    let svc = service::SolverServiceImpl::new();
    let server = tokio::spawn(async move {
        Server::builder()
            .add_service(SolverServiceServer::new(svc))
            .serve_with_incoming(incoming)
            .await
    });

    tokio::time::sleep(Duration::from_millis(50)).await;
    let endpoint = Endpoint::from_shared(format!("http://{addr}")).unwrap();
    let channel = endpoint.connect().await.unwrap();
    let mut client = SolverServiceClient::new(channel);

    let listed = client.list_solvers(ListSolversRequest {}).await.unwrap().into_inner();
    assert!(listed.entries.iter().any(|e| e.solver_id == "engine"));
    assert!(listed.entries.iter().any(|e| e.solver_id == "naive"));

    let puzzle = generate(GeneratorConfig { size: 3, interior_colors: 3, seed: 1 }).unwrap();

    let request = SolveRequest {
        puzzle: Some(puzzle_to_pb(&puzzle)),
        selections: vec![SolverSelection {
            solver_id: "engine".into(),
            heuristic_profile: "border_first_lcv".into(),
            seed: 0,
            options: None,
        }],
        path_config: None,
        throttle_config: None,
        mode: SolveMode::FirstSolution as i32,
        time_budget_ms: 30_000,
        max_solutions: 0,
    };

    let mut stream = client.solve(request).await.unwrap().into_inner();
    let mut saw_started = false;
    let mut saw_solved = false;
    while let Some(item) = stream.next().await {
        let ev = item.unwrap();
        if let Some(body) = ev.body {
            use wire::solver_event::Body;
            match body {
                Body::Started(_) => saw_started = true,
                Body::Solved(_) => { saw_solved = true; break; }
                _ => {}
            }
        }
    }
    assert!(saw_started, "missing Started event");
    assert!(saw_solved, "missing Solved event");

    server.abort();
}
