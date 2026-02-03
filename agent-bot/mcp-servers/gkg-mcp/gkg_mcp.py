from mcp.server.fastmcp import FastMCP
import httpx
import structlog

from config import settings

logger = structlog.get_logger()

mcp = FastMCP("gkg")


@mcp.tool()
async def analyze_dependencies(
    file_path: str,
    org_id: str,
    repo: str,
    depth: int = 3,
) -> str:
    """
    Analyze dependencies of a file or module.

    Args:
        file_path: Path to the file
        org_id: Organization ID
        repo: Repository name
        depth: How deep to traverse dependencies

    Returns:
        Dependency tree with explanations
    """
    logger.info("analyze_dependencies", file_path=file_path, org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.gkg_url}/analyze/dependencies",
            json={
                "file_path": file_path,
                "org_id": org_id,
                "repo": repo,
                "depth": depth,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("formatted_output", "No dependencies found")


@mcp.tool()
async def find_usages(
    symbol: str,
    org_id: str,
    repo: str = "*",
) -> str:
    """
    Find all usages of a symbol (function, class, variable).

    Args:
        symbol: Symbol name to search for
        org_id: Organization ID
        repo: Repository filter

    Returns:
        List of files and locations where the symbol is used
    """
    logger.info("find_usages", symbol=symbol, org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.gkg_url}/query/usages",
            json={
                "symbol": symbol,
                "org_id": org_id,
                "repo": repo,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        results = response.json()

    formatted = [f"## Usages of `{symbol}`\n"]
    for usage in results.get("usages", []):
        formatted.append(
            f"- {usage.get('file', '?')}:{usage.get('line', '?')} ({usage.get('context', '')})"
        )

    return (
        "\n".join(formatted)
        if len(formatted) > 1
        else f"No usages found for `{symbol}`"
    )


@mcp.tool()
async def get_call_graph(
    function_name: str,
    org_id: str,
    repo: str,
    direction: str = "both",
    depth: int = 2,
) -> str:
    """
    Get the call graph for a function.

    Args:
        function_name: Function name
        org_id: Organization ID
        repo: Repository name
        direction: "callers", "callees", or "both"
        depth: Traversal depth

    Returns:
        Call graph visualization
    """
    logger.info("get_call_graph", function_name=function_name, org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.gkg_url}/graph/calls",
            json={
                "function_name": function_name,
                "org_id": org_id,
                "repo": repo,
                "direction": direction,
                "depth": depth,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("formatted_graph", "No call graph found")


@mcp.tool()
async def get_class_hierarchy(
    class_name: str,
    org_id: str,
    repo: str = "*",
) -> str:
    """
    Get inheritance hierarchy for a class.

    Args:
        class_name: Class name
        org_id: Organization ID
        repo: Repository filter

    Returns:
        Class hierarchy diagram
    """
    logger.info("get_class_hierarchy", class_name=class_name, org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.gkg_url}/graph/hierarchy",
            json={
                "class_name": class_name,
                "org_id": org_id,
                "repo": repo,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("formatted_hierarchy", "No hierarchy found")


@mcp.tool()
async def get_related_entities(
    entity: str,
    entity_type: str,
    org_id: str,
    relationship: str = "all",
) -> str:
    """
    Get entities related to a specific code entity.

    Args:
        entity: Entity name (function, class, module)
        entity_type: Type of entity (function, class, module, file)
        org_id: Organization ID
        relationship: Relationship type (calls, imports, extends, references, all)

    Returns:
        Related entities grouped by relationship type
    """
    logger.info("get_related_entities", entity=entity, org_id=org_id)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.gkg_url}/graph/related",
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

    formatted = [f"## Related Entities for `{entity}` ({entity_type})\n"]

    for rel_type, entities in results.get("relationships", {}).items():
        if entities:
            formatted.append(f"\n### {rel_type.upper()}")
            for ent in entities:
                formatted.append(
                    f"- `{ent.get('name', '?')}` in {ent.get('file', '?')}:{ent.get('line', '?')}"
                )

    return (
        "\n".join(formatted)
        if len(formatted) > 1
        else f"No related entities found for `{entity}`"
    )
