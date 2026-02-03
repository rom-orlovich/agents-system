from mcp.server.fastmcp import FastMCP
import httpx
import structlog

from config import settings

logger = structlog.get_logger()

mcp = FastMCP("llamaindex")


@mcp.tool()
async def knowledge_query(
    query: str,
    org_id: str,
    source_types: str = "code,jira,confluence",
    top_k: int = 10,
) -> str:
    """
    Query the knowledge base using hybrid search (vectors + graph).

    Args:
        query: Natural language query
        org_id: Organization ID to scope the search
        source_types: Comma-separated list of sources (code, jira, confluence)
        top_k: Number of results to return

    Returns:
        Formatted search results with context
    """
    logger.info("knowledge_query", query=query[:100], org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.llamaindex_url}/query",
            json={
                "query": query,
                "org_id": org_id,
                "source_types": source_types.split(","),
                "top_k": top_k,
                "include_metadata": True,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        results = response.json()

    formatted = []
    for i, result in enumerate(results.get("results", []), 1):
        formatted.append(
            f"""
### Result {i} ({result['source_type']}) - Score: {result['relevance_score']:.3f}
**Source:** {result['source_id']}
```
{result['content'][:2000]}
```
"""
        )

    return "\n".join(formatted) if formatted else "No relevant results found."


@mcp.tool()
async def code_search(
    query: str,
    org_id: str,
    repo_filter: str = "*",
    language: str = "*",
    top_k: int = 10,
) -> str:
    """
    Search code across indexed repositories.

    Args:
        query: Code or natural language query
        org_id: Organization ID
        repo_filter: Repository glob pattern (e.g., "backend-*")
        language: Programming language filter
        top_k: Number of results

    Returns:
        Relevant code snippets with file paths
    """
    logger.info("code_search", query=query[:100], org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.llamaindex_url}/query/code",
            json={
                "query": query,
                "org_id": org_id,
                "filters": {"repo": repo_filter, "language": language},
                "top_k": top_k,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        results = response.json()

    formatted = []
    for result in results.get("results", []):
        meta = result.get("metadata", {})
        formatted.append(
            f"""
**{meta.get('repo', 'unknown')}/{meta.get('file_path', 'unknown')}** (lines {meta.get('line_start', '?')}-{meta.get('line_end', '?')})
```{meta.get('language', '')}
{result['content']}
```
"""
        )

    return "\n".join(formatted) if formatted else "No code matches found."


@mcp.tool()
async def find_related_code(
    entity: str,
    entity_type: str,
    org_id: str,
    relationship: str = "all",
) -> str:
    """
    Find code related to a specific entity using the knowledge graph.

    Args:
        entity: Entity name (function, class, module)
        entity_type: Type of entity (function, class, module, file)
        org_id: Organization ID
        relationship: Relationship type (calls, imports, extends, all)

    Returns:
        Related code entities with relationship context
    """
    logger.info("find_related_code", entity=entity, org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.llamaindex_url}/graph/related",
            json={
                "entity": entity,
                "entity_type": entity_type,
                "org_id": org_id,
                "relationship": relationship,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        results = response.json()

    formatted = ["## Related Code Entities\n"]
    for rel_type, entities in results.get("relationships", {}).items():
        formatted.append(f"\n### {rel_type.upper()}\n")
        for ent in entities:
            formatted.append(f"- `{ent.get('name', '?')}` in {ent.get('file', '?')} (line {ent.get('line', '?')})")

    return "\n".join(formatted)


@mcp.tool()
async def search_jira_tickets(
    query: str,
    org_id: str,
    project: str = "*",
    status: str = "*",
    top_k: int = 10,
) -> str:
    """
    Search Jira tickets using semantic search.

    Args:
        query: Natural language query
        org_id: Organization ID
        project: Project key filter
        status: Status filter (Open, In Progress, Done, *)
        top_k: Number of results

    Returns:
        Relevant Jira tickets with summaries
    """
    logger.info("search_jira_tickets", query=query[:100], org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.llamaindex_url}/query/tickets",
            json={
                "query": query,
                "org_id": org_id,
                "filters": {"project": project, "status": status},
                "top_k": top_k,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        results = response.json()

    formatted = []
    for result in results.get("results", []):
        meta = result.get("metadata", {})
        labels = meta.get("labels", [])
        if isinstance(labels, str):
            labels = [labels]
        formatted.append(
            f"""
**[{meta.get('key', '?')}] {meta.get('summary', 'No summary')}**
- Status: {meta.get('status', '?')} | Priority: {meta.get('priority', '?')}
- Labels: {', '.join(labels) if labels else 'None'}

{result['content'][:500]}...
"""
        )

    return "\n".join(formatted) if formatted else "No matching tickets found."


@mcp.tool()
async def search_confluence(
    query: str,
    org_id: str,
    space: str = "*",
    top_k: int = 10,
) -> str:
    """
    Search Confluence documentation.

    Args:
        query: Natural language query
        org_id: Organization ID
        space: Space key filter
        top_k: Number of results

    Returns:
        Relevant documentation excerpts
    """
    logger.info("search_confluence", query=query[:100], org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.llamaindex_url}/query/docs",
            json={
                "query": query,
                "org_id": org_id,
                "filters": {"space": space},
                "top_k": top_k,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        results = response.json()

    formatted = []
    for result in results.get("results", []):
        meta = result.get("metadata", {})
        formatted.append(
            f"""
**{meta.get('page_title', 'Unknown')}** ({meta.get('space', '?')})
Last updated: {meta.get('last_modified', 'Unknown')}

{result['content'][:1000]}...
"""
        )

    return "\n".join(formatted) if formatted else "No documentation found."
