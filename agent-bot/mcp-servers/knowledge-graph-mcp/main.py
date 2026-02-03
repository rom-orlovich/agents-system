from typing import Any, Literal

from fastmcp import FastMCP

from chroma_client import chroma_client
from config import get_settings
from kg_client import KnowledgeGraphClient

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


@mcp.tool()
async def knowledge_store(
    content: str,
    metadata: dict[str, Any] | None = None,
    collection: str = "default",
    doc_id: str | None = None,
) -> dict[str, Any]:
    """
    Store knowledge in the ChromaDB vector database.

    Args:
        content: The text content to store
        metadata: Optional metadata (tags, source, category, etc.)
        collection: Collection name (default: "default")
        doc_id: Optional document ID (auto-generated if not provided)

    Returns:
        Storage confirmation with document ID
    """
    return await chroma_client.store_document(
        content=content,
        metadata=metadata or {},
        collection_name=collection,
        doc_id=doc_id,
    )


@mcp.tool()
async def knowledge_query(
    query: str,
    n_results: int = 5,
    collection: str = "default",
    filter_metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Query similar knowledge from the ChromaDB vector database.

    Args:
        query: Search query text
        n_results: Number of results to return (1-100)
        collection: Collection to search
        filter_metadata: Optional metadata filters

    Returns:
        List of similar documents with distances
    """
    return await chroma_client.query_documents(
        query=query,
        n_results=n_results,
        collection_name=collection,
        filter_metadata=filter_metadata,
    )


@mcp.tool()
async def knowledge_collections(
    action: Literal["list", "create", "delete"],
    collection: str | None = None,
) -> dict[str, Any]:
    """
    Manage ChromaDB knowledge collections.

    Args:
        action: Operation to perform (list, create, delete)
        collection: Collection name (required for create/delete)

    Returns:
        Collection information or confirmation
    """
    if action == "list":
        return await chroma_client.list_collections()
    elif action == "create":
        if not collection:
            return {"error": "Collection name required for create action"}
        return await chroma_client.create_collection(collection)
    elif action == "delete":
        if not collection:
            return {"error": "Collection name required for delete action"}
        return await chroma_client.delete_collection(collection)
    return {"error": f"Unknown action: {action}"}


@mcp.tool()
async def knowledge_update(
    doc_id: str,
    content: str | None = None,
    metadata: dict[str, Any] | None = None,
    collection: str = "default",
) -> dict[str, Any]:
    """
    Update an existing document in ChromaDB.

    Args:
        doc_id: Document ID to update
        content: New content (optional)
        metadata: New metadata (optional)
        collection: Collection name

    Returns:
        Update confirmation
    """
    return await chroma_client.update_document(
        doc_id=doc_id,
        content=content,
        metadata=metadata,
        collection_name=collection,
    )


@mcp.tool()
async def knowledge_delete(
    doc_id: str,
    collection: str = "default",
) -> dict[str, Any]:
    """
    Delete a document from ChromaDB.

    Args:
        doc_id: Document ID to delete
        collection: Collection name

    Returns:
        Deletion confirmation
    """
    return await chroma_client.delete_document(
        doc_id=doc_id,
        collection_name=collection,
    )


if __name__ == "__main__":
    settings = get_settings()
    mcp.run(transport="sse", port=settings.port)
