# Knowledge Graph Skill

## Purpose
Query code relationships for context and impact analysis.

## Available Queries

### Find Function Callers
find_callers(function_name) -> list of calling locations

### Get Class Hierarchy
get_hierarchy(class_name) -> parents and children

### Impact Analysis
find_affected(file_path) -> files depending on this file

### Test Coverage
find_tests(function_name) -> tests covering this function

## Usage Guidelines
- Query before reading large files
- Use for change risk assessment
- Combine with AST for detail

## MCP Tool Mapping
- get_function_callers -> knowledge_graph_mcp.find_callers
- get_class_hierarchy -> knowledge_graph_mcp.get_hierarchy
- find_affected_by_change -> knowledge_graph_mcp.impact_analysis
