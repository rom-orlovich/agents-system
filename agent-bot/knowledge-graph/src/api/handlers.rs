use std::sync::Arc;

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use uuid::Uuid;

use crate::{
    models::{
        CreateEdgeRequest, CreateNodeRequest, Direction, Edge, EdgeWithNodes,
        GraphStats, NeighborsQuery, Node, NodeResponse, PathQuery, PathResult,
        SearchQuery,
    },
    AppState,
};

pub async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "healthy",
        "service": "knowledge-graph"
    }))
}

pub async fn list_nodes(
    State(state): State<Arc<AppState>>,
) -> impl IntoResponse {
    let graph = state.graph.read().await;
    let nodes: Vec<&Node> = graph.list_nodes();
    Json(serde_json::json!({
        "nodes": nodes,
        "count": nodes.len()
    }))
}

pub async fn create_node(
    State(state): State<Arc<AppState>>,
    Json(req): Json<CreateNodeRequest>,
) -> impl IntoResponse {
    let node: Node = req.into();
    let id = {
        let mut graph = state.graph.write().await;
        graph.add_node(node.clone())
    };

    (
        StatusCode::CREATED,
        Json(serde_json::json!({
            "id": id,
            "node": node
        })),
    )
}

pub async fn get_node(
    State(state): State<Arc<AppState>>,
    Path(id): Path<Uuid>,
) -> impl IntoResponse {
    let graph = state.graph.read().await;

    match graph.get_node(&id) {
        Some(node) => {
            let edge_count = graph.get_edges_for_node(&id).len();
            Json(serde_json::json!(NodeResponse {
                node: node.clone(),
                edge_count,
            }))
            .into_response()
        }
        None => (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "error": "Node not found" })),
        )
            .into_response(),
    }
}

pub async fn delete_node(
    State(state): State<Arc<AppState>>,
    Path(id): Path<Uuid>,
) -> impl IntoResponse {
    let mut graph = state.graph.write().await;

    match graph.remove_node(&id) {
        Some(_) => Json(serde_json::json!({
            "status": "deleted",
            "id": id
        }))
        .into_response(),
        None => (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "error": "Node not found" })),
        )
            .into_response(),
    }
}

pub async fn list_edges(
    State(state): State<Arc<AppState>>,
) -> impl IntoResponse {
    let graph = state.graph.read().await;
    let edges: Vec<EdgeWithNodes> = graph
        .list_edges()
        .iter()
        .filter_map(|edge| {
            let source = graph.get_node(&edge.source_id)?;
            let target = graph.get_node(&edge.target_id)?;
            Some(EdgeWithNodes {
                edge: (*edge).clone(),
                source_name: source.name.clone(),
                target_name: target.name.clone(),
            })
        })
        .collect();

    Json(serde_json::json!({
        "edges": edges,
        "count": edges.len()
    }))
}

pub async fn create_edge(
    State(state): State<Arc<AppState>>,
    Json(req): Json<CreateEdgeRequest>,
) -> impl IntoResponse {
    let edge: Edge = req.into();
    let mut graph = state.graph.write().await;

    match graph.add_edge(edge.clone()) {
        Some(id) => (
            StatusCode::CREATED,
            Json(serde_json::json!({
                "id": id,
                "edge": edge
            })),
        )
            .into_response(),
        None => (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "error": "Source or target node not found"
            })),
        )
            .into_response(),
    }
}

pub async fn find_path(
    State(state): State<Arc<AppState>>,
    Json(query): Json<PathQuery>,
) -> impl IntoResponse {
    let graph = state.graph.read().await;

    match graph.find_path(&query.source_id, &query.target_id) {
        Some(result) => Json(serde_json::json!(result)).into_response(),
        None => (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "error": "No path found" })),
        )
            .into_response(),
    }
}

pub async fn find_neighbors(
    State(state): State<Arc<AppState>>,
    Json(query): Json<NeighborsQuery>,
) -> impl IntoResponse {
    let graph = state.graph.read().await;

    let direction = query.direction.unwrap_or_default();
    let depth = query.depth.unwrap_or(1);
    let edge_types = query.edge_types.as_deref();

    let neighbors = graph.find_neighbors(&query.node_id, edge_types, &direction, depth);

    Json(serde_json::json!({
        "neighbors": neighbors,
        "count": neighbors.len()
    }))
}

pub async fn search_nodes(
    State(state): State<Arc<AppState>>,
    Json(query): Json<SearchQuery>,
) -> impl IntoResponse {
    let graph = state.graph.read().await;

    let limit = query.limit.unwrap_or(20);
    let node_types = query.node_types.as_deref();
    let language = query.language.as_deref();

    let results = graph.search_nodes(&query.query, node_types, language, limit);

    Json(serde_json::json!({
        "results": results,
        "count": results.len()
    }))
}

pub async fn get_stats(
    State(state): State<Arc<AppState>>,
) -> impl IntoResponse {
    let graph = state.graph.read().await;
    let stats = graph.get_stats();
    Json(stats)
}
