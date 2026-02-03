from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class KnowledgeServiceStatus:
    enabled: bool = False
    llamaindex_available: bool = False
    gkg_available: bool = False
    last_check_error: str | None = None


@dataclass
class SearchResult:
    source_type: str
    source_id: str
    content: str
    relevance_score: float
    metadata: dict = field(default_factory=dict)


@dataclass
class GraphEntity:
    name: str
    entity_type: str
    file_path: str | None = None
    line_number: int | None = None


@runtime_checkable
class KnowledgeServiceProtocol(Protocol):
    async def search(
        self,
        query: str,
        org_id: str,
        source_types: list[str] | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]: ...

    async def get_related_code(
        self,
        entity: str,
        entity_type: str,
        org_id: str,
    ) -> dict[str, list[GraphEntity]]: ...

    async def health_check(self) -> KnowledgeServiceStatus: ...


class KnowledgeService:
    def __init__(
        self,
        llamaindex_url: str,
        gkg_url: str,
        enabled: bool = False,
        timeout: float = 10.0,
        retry_count: int = 2,
    ):
        self._llamaindex_url = llamaindex_url.rstrip("/")
        self._gkg_url = gkg_url.rstrip("/")
        self._enabled = enabled
        self._timeout = timeout
        self._retry_count = retry_count
        self._status = KnowledgeServiceStatus(enabled=enabled)

    async def search(
        self,
        query: str,
        org_id: str,
        source_types: list[str] | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        if not self._enabled:
            logger.debug("knowledge_search_skipped", reason="disabled")
            return []

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._llamaindex_url}/query",
                    json={
                        "query": query,
                        "org_id": org_id,
                        "source_types": source_types or ["code", "jira", "confluence"],
                        "top_k": top_k,
                        "include_metadata": True,
                    },
                )
                response.raise_for_status()
                data = response.json()

                return [
                    SearchResult(
                        source_type=r.get("source_type", "unknown"),
                        source_id=r.get("source_id", ""),
                        content=r.get("content", ""),
                        relevance_score=r.get("relevance_score", 0.0),
                        metadata=r.get("metadata", {}),
                    )
                    for r in data.get("results", [])
                ]
        except httpx.TimeoutException:
            logger.warning("knowledge_search_timeout", query=query[:50])
            return []
        except httpx.HTTPError as e:
            logger.warning("knowledge_search_failed", error=str(e))
            return []
        except Exception as e:
            logger.warning("knowledge_search_error", error=str(e))
            return []

    async def get_related_code(
        self,
        entity: str,
        entity_type: str,
        org_id: str,
    ) -> dict[str, list[GraphEntity]]:
        if not self._enabled:
            logger.debug("knowledge_graph_skipped", reason="disabled")
            return {}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._gkg_url}/graph/related",
                    json={
                        "entity": entity,
                        "entity_type": entity_type,
                        "org_id": org_id,
                        "relationship": "all",
                    },
                )
                response.raise_for_status()
                data = response.json()

                relationships: dict[str, list[GraphEntity]] = {}
                for rel_type, entities in data.get("relationships", {}).items():
                    relationships[rel_type] = [
                        GraphEntity(
                            name=e.get("name", ""),
                            entity_type=e.get("type", ""),
                            file_path=e.get("file"),
                            line_number=e.get("line"),
                        )
                        for e in entities
                    ]
                return relationships
        except httpx.TimeoutException:
            logger.warning("knowledge_graph_timeout", entity=entity)
            return {}
        except httpx.HTTPError as e:
            logger.warning("knowledge_graph_failed", error=str(e))
            return {}
        except Exception as e:
            logger.warning("knowledge_graph_error", error=str(e))
            return {}

    async def health_check(self) -> KnowledgeServiceStatus:
        self._status = KnowledgeServiceStatus(enabled=self._enabled)

        if not self._enabled:
            return self._status

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    resp = await client.get(f"{self._llamaindex_url}/health")
                    self._status.llamaindex_available = resp.status_code == 200
                except Exception:
                    self._status.llamaindex_available = False

                try:
                    resp = await client.get(f"{self._gkg_url}/health")
                    self._status.gkg_available = resp.status_code == 200
                except Exception:
                    self._status.gkg_available = False

        except Exception as e:
            self._status.last_check_error = str(e)
            logger.warning("knowledge_health_check_failed", error=str(e))

        return self._status

    @property
    def is_available(self) -> bool:
        return self._enabled and (
            self._status.llamaindex_available or self._status.gkg_available
        )

    def enable(self) -> None:
        self._enabled = True
        self._status.enabled = True
        logger.info("knowledge_services_enabled")

    def disable(self) -> None:
        self._enabled = False
        self._status.enabled = False
        logger.info("knowledge_services_disabled")


class NoopKnowledgeService:
    async def search(
        self,
        query: str,
        org_id: str,
        source_types: list[str] | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        return []

    async def get_related_code(
        self,
        entity: str,
        entity_type: str,
        org_id: str,
    ) -> dict[str, list[GraphEntity]]:
        return {}

    async def health_check(self) -> KnowledgeServiceStatus:
        return KnowledgeServiceStatus(enabled=False)

    @property
    def is_available(self) -> bool:
        return False

    def enable(self) -> None:
        pass

    def disable(self) -> None:
        pass
