use std::collections::{HashMap, HashSet};
use uuid::Uuid;

use crate::models::{
    Direction, Edge, EdgeType, GraphStats, Node, NodeType, PathResult,
};

use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::algo::dijkstra;

pub struct KnowledgeGraph {
    graph: DiGraph<Uuid, f64>,
    nodes: HashMap<Uuid, Node>,
    edges: HashMap<Uuid, Edge>,
    node_indices: HashMap<Uuid, NodeIndex>,
}

impl KnowledgeGraph {
    pub fn new() -> Self {
        Self {
            graph: DiGraph::new(),
            nodes: HashMap::new(),
            edges: HashMap::new(),
            node_indices: HashMap::new(),
        }
    }

    pub fn add_node(&mut self, node: Node) -> Uuid {
        let id = node.id;
        let idx = self.graph.add_node(id);
        self.node_indices.insert(id, idx);
        self.nodes.insert(id, node);
        id
    }

    pub fn get_node(&self, id: &Uuid) -> Option<&Node> {
        self.nodes.get(id)
    }

    pub fn remove_node(&mut self, id: &Uuid) -> Option<Node> {
        if let Some(idx) = self.node_indices.remove(id) {
            self.graph.remove_node(idx);
            self.edges.retain(|_, e| e.source_id != *id && e.target_id != *id);
            self.nodes.remove(id)
        } else {
            None
        }
    }

    pub fn list_nodes(&self) -> Vec<&Node> {
        self.nodes.values().collect()
    }

    pub fn add_edge(&mut self, edge: Edge) -> Option<Uuid> {
        let source_idx = self.node_indices.get(&edge.source_id)?;
        let target_idx = self.node_indices.get(&edge.target_id)?;

        self.graph.add_edge(*source_idx, *target_idx, edge.weight);
        let id = edge.id;
        self.edges.insert(id, edge);
        Some(id)
    }

    pub fn get_edge(&self, id: &Uuid) -> Option<&Edge> {
        self.edges.get(id)
    }

    pub fn list_edges(&self) -> Vec<&Edge> {
        self.edges.values().collect()
    }

    pub fn get_edges_for_node(&self, node_id: &Uuid) -> Vec<&Edge> {
        self.edges
            .values()
            .filter(|e| e.source_id == *node_id || e.target_id == *node_id)
            .collect()
    }

    pub fn find_path(&self, source_id: &Uuid, target_id: &Uuid) -> Option<PathResult> {
        let source_idx = self.node_indices.get(source_id)?;
        let target_idx = self.node_indices.get(target_id)?;

        let distances = dijkstra(&self.graph, *source_idx, Some(*target_idx), |e| *e.weight());

        if !distances.contains_key(target_idx) {
            return None;
        }

        let mut path = vec![*target_id];
        let mut current = *target_idx;
        let mut visited = HashSet::new();
        visited.insert(current);

        while current != *source_idx {
            let mut found_prev = false;
            for neighbor in self.graph.neighbors_directed(current, petgraph::Incoming) {
                if visited.contains(&neighbor) {
                    continue;
                }
                if let Some(&dist) = distances.get(&neighbor) {
                    let current_dist = distances.get(&current).unwrap();
                    if let Some(edge) = self.graph.find_edge(neighbor, current) {
                        let weight = self.graph.edge_weight(edge).unwrap();
                        if (dist + weight - current_dist).abs() < 0.0001 {
                            current = neighbor;
                            let node_id = self.graph[neighbor];
                            path.push(node_id);
                            visited.insert(neighbor);
                            found_prev = true;
                            break;
                        }
                    }
                }
            }
            if !found_prev {
                break;
            }
        }

        path.reverse();

        let node_names: Vec<String> = path
            .iter()
            .filter_map(|id| self.nodes.get(id).map(|n| n.name.clone()))
            .collect();

        let total_weight = distances.get(target_idx).copied().unwrap_or(0.0);

        Some(PathResult {
            path,
            node_names,
            total_weight,
        })
    }

    pub fn find_neighbors(
        &self,
        node_id: &Uuid,
        edge_types: Option<&[EdgeType]>,
        direction: &Direction,
        depth: usize,
    ) -> Vec<&Node> {
        let mut result = Vec::new();
        let mut visited = HashSet::new();
        let mut current_level = vec![*node_id];
        visited.insert(*node_id);

        for _ in 0..depth {
            let mut next_level = Vec::new();

            for current_id in &current_level {
                let edges: Vec<&Edge> = match direction {
                    Direction::Outgoing => self
                        .edges
                        .values()
                        .filter(|e| e.source_id == *current_id)
                        .collect(),
                    Direction::Incoming => self
                        .edges
                        .values()
                        .filter(|e| e.target_id == *current_id)
                        .collect(),
                    Direction::Both => self
                        .edges
                        .values()
                        .filter(|e| e.source_id == *current_id || e.target_id == *current_id)
                        .collect(),
                };

                for edge in edges {
                    if let Some(types) = edge_types {
                        if !types.contains(&edge.edge_type) {
                            continue;
                        }
                    }

                    let neighbor_id = if edge.source_id == *current_id {
                        edge.target_id
                    } else {
                        edge.source_id
                    };

                    if visited.insert(neighbor_id) {
                        if let Some(node) = self.nodes.get(&neighbor_id) {
                            result.push(node);
                            next_level.push(neighbor_id);
                        }
                    }
                }
            }

            current_level = next_level;
        }

        result
    }

    pub fn search_nodes(
        &self,
        query: &str,
        node_types: Option<&[NodeType]>,
        language: Option<&str>,
        limit: usize,
    ) -> Vec<&Node> {
        let query_lower = query.to_lowercase();

        self.nodes
            .values()
            .filter(|node| {
                let name_match = node.name.to_lowercase().contains(&query_lower);
                let desc_match = node
                    .description
                    .as_ref()
                    .map(|d| d.to_lowercase().contains(&query_lower))
                    .unwrap_or(false);

                let type_match = node_types
                    .map(|types| types.contains(&node.node_type))
                    .unwrap_or(true);

                let lang_match = language
                    .map(|lang| node.language.as_deref() == Some(lang))
                    .unwrap_or(true);

                (name_match || desc_match) && type_match && lang_match
            })
            .take(limit)
            .collect()
    }

    pub fn get_stats(&self) -> GraphStats {
        let mut nodes_by_type: HashMap<String, usize> = HashMap::new();
        let mut edges_by_type: HashMap<String, usize> = HashMap::new();

        for node in self.nodes.values() {
            let type_str = format!("{:?}", node.node_type).to_lowercase();
            *nodes_by_type.entry(type_str).or_insert(0) += 1;
        }

        for edge in self.edges.values() {
            let type_str = format!("{:?}", edge.edge_type).to_lowercase();
            *edges_by_type.entry(type_str).or_insert(0) += 1;
        }

        let total_nodes = self.nodes.len();
        let total_edges = self.edges.len();
        let avg_edges_per_node = if total_nodes > 0 {
            total_edges as f64 / total_nodes as f64
        } else {
            0.0
        };

        GraphStats {
            total_nodes,
            total_edges,
            nodes_by_type,
            edges_by_type,
            avg_edges_per_node,
        }
    }
}

impl Default for KnowledgeGraph {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_and_get_node() {
        let mut graph = KnowledgeGraph::new();
        let node = Node::new("test".to_string(), NodeType::Function);
        let id = node.id;
        graph.add_node(node);

        let retrieved = graph.get_node(&id).unwrap();
        assert_eq!(retrieved.name, "test");
    }

    #[test]
    fn test_add_edge() {
        let mut graph = KnowledgeGraph::new();

        let node1 = Node::new("func1".to_string(), NodeType::Function);
        let node2 = Node::new("func2".to_string(), NodeType::Function);
        let id1 = node1.id;
        let id2 = node2.id;

        graph.add_node(node1);
        graph.add_node(node2);

        let edge = Edge::new(id1, id2, EdgeType::Calls);
        let edge_id = graph.add_edge(edge).unwrap();

        let retrieved = graph.get_edge(&edge_id).unwrap();
        assert_eq!(retrieved.source_id, id1);
        assert_eq!(retrieved.target_id, id2);
    }

    #[test]
    fn test_find_neighbors() {
        let mut graph = KnowledgeGraph::new();

        let node1 = Node::new("A".to_string(), NodeType::Function);
        let node2 = Node::new("B".to_string(), NodeType::Function);
        let node3 = Node::new("C".to_string(), NodeType::Function);
        let id1 = node1.id;
        let id2 = node2.id;
        let id3 = node3.id;

        graph.add_node(node1);
        graph.add_node(node2);
        graph.add_node(node3);

        graph.add_edge(Edge::new(id1, id2, EdgeType::Calls));
        graph.add_edge(Edge::new(id2, id3, EdgeType::Calls));

        let neighbors = graph.find_neighbors(&id1, None, &Direction::Outgoing, 1);
        assert_eq!(neighbors.len(), 1);
        assert_eq!(neighbors[0].name, "B");
    }

    #[test]
    fn test_search_nodes() {
        let mut graph = KnowledgeGraph::new();

        let node1 = Node::new("handleAuth".to_string(), NodeType::Function)
            .with_language("typescript".to_string());
        let node2 = Node::new("processPayment".to_string(), NodeType::Function)
            .with_language("typescript".to_string());

        graph.add_node(node1);
        graph.add_node(node2);

        let results = graph.search_nodes("auth", None, None, 10);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].name, "handleAuth");
    }
}
