mod api;
mod models;
mod services;

use axum::{
    routing::{get, post},
    Router,
};
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::RwLock;
use tower_http::cors::CorsLayer;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use services::graph::KnowledgeGraph;

pub struct AppState {
    pub graph: Arc<RwLock<KnowledgeGraph>>,
}

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();

    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "knowledge_graph=debug,tower_http=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    let graph = Arc::new(RwLock::new(KnowledgeGraph::new()));
    let state = Arc::new(AppState { graph });

    let app = Router::new()
        .route("/health", get(api::handlers::health_check))
        .route("/api/v1/nodes", get(api::handlers::list_nodes))
        .route("/api/v1/nodes", post(api::handlers::create_node))
        .route("/api/v1/nodes/:id", get(api::handlers::get_node))
        .route("/api/v1/nodes/:id", axum::routing::delete(api::handlers::delete_node))
        .route("/api/v1/edges", get(api::handlers::list_edges))
        .route("/api/v1/edges", post(api::handlers::create_edge))
        .route("/api/v1/query/path", post(api::handlers::find_path))
        .route("/api/v1/query/neighbors", post(api::handlers::find_neighbors))
        .route("/api/v1/query/search", post(api::handlers::search_nodes))
        .route("/api/v1/stats", get(api::handlers::get_stats))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    let port: u16 = std::env::var("PORT")
        .unwrap_or_else(|_| "9010".to_string())
        .parse()
        .expect("PORT must be a valid number");

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("Knowledge Graph starting on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
