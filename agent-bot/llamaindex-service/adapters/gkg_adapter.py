import httpx
import structlog

from core.models import GraphEntity

logger = structlog.get_logger()


class GKGGraphStore:
    """GKG service implementation of GraphStoreProtocol."""

    def __init__(self, gkg_url: str):
        self._gkg_url = gkg_url

    async def get_related_entities(
        self,
        entity: str,
        entity_type: str,
        relationship: str,
        org_id: str,
    ) -> dict[str, list[GraphEntity]]:
        """Find entities related to the given entity."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._gkg_url}/graph/related",
                    json={
                        "entity": entity,
                        "entity_type": entity_type,
                        "org_id": org_id,
                        "relationship": relationship,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                result: dict[str, list[GraphEntity]] = {}
                for rel_type, entities in data.get("relationships", {}).items():
                    result[rel_type] = [
                        GraphEntity(
                            name=e.get("name", ""),
                            entity_type=e.get("type", "unknown"),
                            file_path=e.get("file"),
                            line_number=e.get("line"),
                        )
                        for e in entities
                    ]
                return result

        except Exception as e:
            logger.error("gkg_get_related_error", entity=entity, error=str(e))
            return {}

    async def get_dependencies(
        self,
        file_path: str,
        org_id: str,
        depth: int,
    ) -> list[GraphEntity]:
        """Get file dependencies."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._gkg_url}/analyze/dependencies",
                    json={
                        "file_path": file_path,
                        "org_id": org_id,
                        "repo": "*",
                        "depth": depth,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                return [
                    GraphEntity(
                        name=dep.get("path", ""),
                        entity_type=dep.get("type", "file"),
                        file_path=dep.get("path"),
                    )
                    for dep in data.get("dependencies", [])
                ]

        except Exception as e:
            logger.error(
                "gkg_get_dependencies_error", file_path=file_path, error=str(e)
            )
            return []

    async def batch_related(
        self,
        entities: list[dict[str, str]],
        org_id: str,
        depth: int = 1,
    ) -> dict[str, dict]:
        """Get related entities for multiple entities in batch."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._gkg_url}/graph/batch-related",
                    json={
                        "entities": entities,
                        "org_id": org_id,
                        "depth": depth,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error("gkg_batch_related_error", error=str(e))
            return {}

    async def health_check(self) -> bool:
        """Check if GKG service is healthy."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._gkg_url}/health",
                    timeout=5.0,
                )
                return response.status_code == 200
        except Exception:
            return False
