---
name: knowledge-graph
description: Semantic code discovery and navigation using knowledge graph. Use when searching code by meaning, finding dependencies, analyzing call graphs, or discovering symbol references across codebases.
---

# Knowledge Graph Skill

Access to GitLab Knowledge Graph (gkg) for semantic code discovery. Indexes code structure including files, classes, functions, and their relationships.

## Quick Reference

- **Templates**: See [templates.md](templates.md) for reporting knowledge graph results

## Available Actions

### search_codebase

Search for code entities by name or pattern.

**Parameters:**

- `query` (required): Search query (function name, class name, etc.)
- `node_types` (optional): Filter by types - `function`, `class`, `file`, `module`
- `language` (optional): Filter by language - `python`, `typescript`, `rust`, `ruby`
- `limit` (optional): Maximum results (default: 20)

**Example:**

```json
{
  "action": "search_codebase",
  "parameters": {
    "query": "handleAuth",
    "node_types": ["function"],
    "language": "typescript"
  }
}
```

### find_symbol_references

Find all usages of a symbol across the codebase.

**Parameters:**

- `symbol_name` (required): Name of the function, class, or variable
- `repository` (optional): Limit search to specific repository

**Example:**

```json
{
  "action": "find_symbol_references",
  "parameters": {
    "symbol_name": "processPayment"
  }
}
```

### get_code_structure

Get the file and directory structure of a repository.

**Parameters:**

- `repository` (required): Name of the repository
- `path` (optional): Specific path within the repository

**Example:**

```json
{
  "action": "get_code_structure",
  "parameters": {
    "repository": "agent-bot",
    "path": "src/services"
  }
}
```

### find_dependencies

Find what a code entity imports, calls, or inherits from.

**Parameters:**

- `node_id` (required): ID of the code entity from a previous search
- `direction` (optional): `outgoing` (what this uses) or `incoming` (what uses this)

**Example:**

```json
{
  "action": "find_dependencies",
  "parameters": {
    "node_id": "uuid-of-module",
    "direction": "outgoing"
  }
}
```

### find_code_path

Find the relationship path between two code entities.

**Parameters:**

- `source_id` (required): ID of the source entity
- `target_id` (required): ID of the target entity

**Example:**

```json
{
  "action": "find_code_path",
  "parameters": {
    "source_id": "uuid-of-caller",
    "target_id": "uuid-of-callee"
  }
}
```

### get_code_neighbors

Get neighboring code entities at a specified depth.

**Parameters:**

- `node_id` (required): ID of the code entity
- `edge_types` (optional): Filter by relationship - `calls`, `imports`, `inherits`, `uses`
- `depth` (optional): How many levels to traverse (default: 1)

**Example:**

```json
{
  "action": "get_code_neighbors",
  "parameters": {
    "node_id": "uuid-of-class",
    "edge_types": ["inherits", "implements"],
    "depth": 2
  }
}
```

### get_graph_stats

Get statistics about the knowledge graph.

**Example:**

```json
{
  "action": "get_graph_stats",
  "parameters": {}
}
```

## MCP Integration

This skill integrates with the knowledge-graph MCP server running on port 9005. The MCP server provides the following tools:

| MCP Tool                 | Skill Action           |
| ------------------------ | ---------------------- |
| `search_codebase`        | search_codebase        |
| `find_symbol_references` | find_symbol_references |
| `get_code_structure`     | get_code_structure     |
| `find_dependencies`      | find_dependencies      |
| `find_code_path`         | find_code_path         |
| `get_code_neighbors`     | get_code_neighbors     |
| `get_graph_stats`        | get_graph_stats        |

## Node Types

| Type        | Description                 |
| ----------- | --------------------------- |
| `file`      | Source code file            |
| `directory` | Directory or folder         |
| `module`    | Python/JS module            |
| `class`     | Class definition            |
| `function`  | Function or method          |
| `variable`  | Global variable or constant |
| `interface` | Interface or protocol       |

## Edge Types

| Type         | Description              |
| ------------ | ------------------------ |
| `imports`    | Import relationship      |
| `calls`      | Function call            |
| `inherits`   | Class inheritance        |
| `contains`   | Parent-child containment |
| `uses`       | Generic usage            |
| `implements` | Interface implementation |

## Workflow Example

1. Search for a function:

   ```
   search_codebase(query="processPayment", node_types=["function"])
   ```

2. Get its dependencies:

   ```
   find_dependencies(node_id="<result_id>", direction="outgoing")
   ```

3. Find what calls it:

   ```
   find_dependencies(node_id="<result_id>", direction="incoming")
   ```

4. Explore neighbors:
   ```
   get_code_neighbors(node_id="<result_id>", depth=2)
   ```
