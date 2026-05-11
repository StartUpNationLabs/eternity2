// Eternity II v2 server. Single binary exposing the SolverService over
// gRPC + gRPC-Web on one port (V2_DESIGN.md "Infra — collapse three
// layers into one"). No Envoy.

mod service;

use std::net::SocketAddr;
use tonic::transport::Server;
use tower_http::cors::CorsLayer;
use tracing_subscriber::EnvFilter;

use wire::solver_service_server::SolverServiceServer;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env()
            .add_directive("info".parse().unwrap()))
        .init();

    let addr: SocketAddr = std::env::var("E2_SERVER_BIND")
        .unwrap_or_else(|_| "0.0.0.0:50051".into())
        .parse()?;

    let service = service::SolverServiceImpl::new();
    let svc = tonic_web::enable(SolverServiceServer::new(service));

    tracing::info!("serving on {addr}");
    Server::builder()
        .accept_http1(true)
        .layer(CorsLayer::very_permissive())
        .add_service(svc)
        .serve_with_shutdown(addr, async {
            tokio::signal::ctrl_c().await.ok();
            tracing::info!("received SIGINT; shutting down");
        })
        .await?;
    Ok(())
}
