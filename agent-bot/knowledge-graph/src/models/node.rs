use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "snake_case")]
pub enum NodeType {
    Repository,
    File,
    Function,
    Class,
    Module,
    Variable,
    Constant,
    Import,
    Agent,
    Skill,
    Task,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub id: Uuid,
    pub name: String,
    pub node_type: NodeType,
    pub path: Option<String>,
    pub language: Option<String>,
    pub description: Option<String>,
    pub metadata: serde_json::Value,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Node {
    pub fn new(name: String, node_type: NodeType) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            name,
            node_type,
            path: None,
            language: None,
            description: None,
            metadata: serde_json::json!({}),
            created_at: now,
            updated_at: now,
        }
    }

    pub fn with_path(mut self, path: String) -> Self {
        self.path = Some(path);
        self
    }

    pub fn with_language(mut self, language: String) -> Self {
        self.language = Some(language);
        self
    }

    pub fn with_description(mut self, description: String) -> Self {
        self.description = Some(description);
        self
    }

    pub fn with_metadata(mut self, metadata: serde_json::Value) -> Self {
        self.metadata = metadata;
        self
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateNodeRequest {
    pub name: String,
    pub node_type: NodeType,
    pub path: Option<String>,
    pub language: Option<String>,
    pub description: Option<String>,
    pub metadata: Option<serde_json::Value>,
}

impl From<CreateNodeRequest> for Node {
    fn from(req: CreateNodeRequest) -> Self {
        let mut node = Node::new(req.name, req.node_type);
        if let Some(path) = req.path {
            node = node.with_path(path);
        }
        if let Some(language) = req.language {
            node = node.with_language(language);
        }
        if let Some(description) = req.description {
            node = node.with_description(description);
        }
        if let Some(metadata) = req.metadata {
            node = node.with_metadata(metadata);
        }
        node
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeResponse {
    pub node: Node,
    pub edge_count: usize,
}
