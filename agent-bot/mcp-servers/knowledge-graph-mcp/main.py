from typing import Any
from fastmcp import FastMCP

from kg_client import KnowledgeGraphClient
from config import get_settings

mcp = FastMCP("Knowledge Graph MCP Server")
kg_client = KnowledgeGraphClient()


@mcp.tool()
async def search_codebase(
    query: str,
    node_types: list[str] | None = None,
    language: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Search the knowledge graph for code entities.

    Args:
        query: Search query (function name, class name, etc.)
        node_types: Filter by node types (function, class, file, module)
        language: Filter by programming language (python, typescript, rust)
        limit: Maximum results to return

    Returns:
        Matching code entities with their relationships
    """
    return await kg_client.search_nodes(query, node_types, language, limit)


@mcp.tool()
async def find_symbol_references(
    symbol_name: str,
    repository: str | None = None,
) -> dict[str, Any]:
    """
    Find all references to a symbol in the codebase.

    Args:
        symbol_name: Name of the symbol (function, class, variable)
        repository: Optional repository to limit search

    Returns:
        All locations where the symbol is referenced
    """
    return await kg_client.find_symbol_references(symbol_name, repository)


@mcp.tool()
async def get_code_structure(
    repository: str,
    path: str | None = None,
) -> dict[str, Any]:
    """
    Get the structure of a repository or directory.

    Args:
        repository: Name of the repository
        path: Optional path within the repository

    Returns:
        File and directory structure with code entities
    """
    return await kg_client.get_file_structure(repository, path)


@mcp.tool()
async def find_dependencies(
    node_id: str,
    direction: str = "outgoing",
) -> dict[str, Any]:
    """
    Find dependencies of a code entity.

    Args:
        node_id: ID of the code entity
        direction: outgoing (what this uses) or incoming (what uses this)

    Returns:
        Related code entities (imports, calls, inherits)
    """
    return await kg_client.get_dependencies(node_id, direction)


@mcp.tool()
async def find_code_path(
    source_id: str,
    target_id: str,
) -> dict[str, Any]:
    """
    Find the relationship path between two code entities.

    Args:
        source_id: ID of the source entity
        target_id: ID of the target entity

    Returns:
        Path of relationships connecting the entities
    """
    return await kg_client.find_path(source_id, target_id)


@mcp.tool()
async def get_code_neighbors(
    node_id: str,
    edge_types: list[str] | None = None,
    depth: int = 1,
) -> dict[str, Any]:
    """
    Get neighboring code entities.

    Args:
        node_id: ID of the code entity
        edge_types: Filter by relationship types (calls, imports, inherits)
        depth: How many levels of neighbors to traverse

    Returns:
        Neighboring code entities and their relationships
    """
    return await kg_client.find_neighbors(node_id, edge_types, "both", depth)


@mcp.tool()
async def get_graph_stats() -> dict[str, Any]:
    """
    Get statistics about the knowledge graph.

    Returns:
        Total nodes, edges, and breakdown by type
    """
    return await kg_client.get_stats()


if __name__ == "__main__":
    settings = get_settings()
    mcp.run(transport="sse", port=settings.port)
