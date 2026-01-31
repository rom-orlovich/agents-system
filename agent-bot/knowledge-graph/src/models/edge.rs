use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "snake_case")]
pub enum EdgeType {
    Contains,
    Imports,
    Calls,
    Inherits,
    Implements,
    Uses,
    DependsOn,
    DefinedIn,
    References,
    Handles,
    Delegates,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Edge {
    pub id: Uuid,
    pub source_id: Uuid,
    pub target_id: Uuid,
    pub edge_type: EdgeType,
    pub weight: f64,
    pub metadata: serde_json::Value,
    pub created_at: DateTime<Utc>,
}

impl Edge {
    pub fn new(source_id: Uuid, target_id: Uuid, edge_type: EdgeType) -> Self {
        Self {
            id: Uuid::new_v4(),
            source_id,
            target_id,
            edge_type,
            weight: 1.0,
            metadata: serde_json::json!({}),
            created_at: Utc::now(),
        }
    }

    pub fn with_weight(mut self, weight: f64) -> Self {
        self.weight = weight;
        self
    }

    pub fn with_metadata(mut self, metadata: serde_json::Value) -> Self {
        self.metadata = metadata;
        self
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateEdgeRequest {
    pub source_id: Uuid,
    pub target_id: Uuid,
    pub edge_type: EdgeType,
    pub weight: Option<f64>,
    pub metadata: Option<serde_json::Value>,
}

impl From<CreateEdgeRequest> for Edge {
    fn from(req: CreateEdgeRequest) -> Self {
        let mut edge = Edge::new(req.source_id, req.target_id, req.edge_type);
        if let Some(weight) = req.weight {
            edge = edge.with_weight(weight);
        }
        if let Some(metadata) = req.metadata {
            edge = edge.with_metadata(metadata);
        }
        edge
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeWithNodes {
    pub edge: Edge,
    pub source_name: String,
    pub target_name: String,
}
