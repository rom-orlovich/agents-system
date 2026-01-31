use serde::{Deserialize, Serialize};
use uuid::Uuid;

use super::{EdgeType, NodeType};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathQuery {
    pub source_id: Uuid,
    pub target_id: Uuid,
    pub max_depth: Option<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NeighborsQuery {
    pub node_id: Uuid,
    pub edge_types: Option<Vec<EdgeType>>,
    pub direction: Option<Direction>,
    pub depth: Option<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Direction {
    Incoming,
    Outgoing,
    Both,
}

impl Default for Direction {
    fn default() -> Self {
        Self::Both
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchQuery {
    pub query: String,
    pub node_types: Option<Vec<NodeType>>,
    pub language: Option<String>,
    pub limit: Option<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathResult {
    pub path: Vec<Uuid>,
    pub node_names: Vec<String>,
    pub total_weight: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphStats {
    pub total_nodes: usize,
    pub total_edges: usize,
    pub nodes_by_type: std::collections::HashMap<String, usize>,
    pub edges_by_type: std::collections::HashMap<String, usize>,
    pub avg_edges_per_node: f64,
}
