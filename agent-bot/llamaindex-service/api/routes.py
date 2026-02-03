from fastapi import APIRouter
import structlog

from core.models import (
    QueryRequest,
    QueryResponse,
    CodeQueryRequest,
    TicketQueryRequest,
    DocsQueryRequest,
    GraphRelatedRequest,
    GraphRelatedResponse,
    HealthStatus,
)
from core.query_engine import HybridQueryEngine
from core.interfaces import VectorStoreProtocol

logger = structlog.get_logger()


def create_query_router(
    query_engine: HybridQueryEngine,
    vector_store: VectorStoreProtocol,
) -> APIRouter:
    """Create query routes with injected dependencies."""
    router = APIRouter()

    @router.post("/query", response_model=QueryResponse)
    async def hybrid_query(request: QueryRequest) -> QueryResponse:
        logger.info(
            "hybrid_query_started",
            query=request.query[:100],
            org_id=request.org_id,
            source_types=request.source_types,
        )

        response = await query_engine.query(
            query=request.query,
            org_id=request.org_id,
            source_types=request.source_types,
            top_k=request.top_k,
            include_metadata=request.include_metadata,
        )

        logger.info(
            "hybrid_query_completed",
            org_id=request.org_id,
            result_count=response.total_results,
        )

        return response

    @router.post("/query/code", response_model=QueryResponse)
    async def code_query(request: CodeQueryRequest) -> QueryResponse:
        logger.info(
            "code_query_started",
            query=request.query[:100],
            org_id=request.org_id,
        )

        return await query_engine.query_code(
            query=request.query,
            org_id=request.org_id,
            repo_filter=request.repo_filter,
            language=request.language,
            top_k=request.top_k,
        )

    @router.post("/query/tickets", response_model=QueryResponse)
    async def ticket_query(request: TicketQueryRequest) -> QueryResponse:
        logger.info(
            "ticket_query_started",
            query=request.query[:100],
            org_id=request.org_id,
        )

        return await query_engine.query_tickets(
            query=request.query,
            org_id=request.org_id,
            project=request.project,
            status=request.status,
            top_k=request.top_k,
        )

    @router.post("/query/docs", response_model=QueryResponse)
    async def docs_query(request: DocsQueryRequest) -> QueryResponse:
        logger.info(
            "docs_query_started",
            query=request.query[:100],
            org_id=request.org_id,
        )

        return await query_engine.query_docs(
            query=request.query,
            org_id=request.org_id,
            space=request.space,
            top_k=request.top_k,
        )

    @router.post("/graph/related", response_model=GraphRelatedResponse)
    async def graph_related(request: GraphRelatedRequest) -> GraphRelatedResponse:
        logger.info(
            "graph_related_started",
            entity=request.entity,
            entity_type=request.entity_type,
            org_id=request.org_id,
        )

        relationships = await query_engine.get_related_entities(
            entity=request.entity,
            entity_type=request.entity_type,
            org_id=request.org_id,
            relationship=request.relationship,
        )

        return GraphRelatedResponse(
            entity=request.entity,
            entity_type=request.entity_type,
            relationships=relationships,
        )

    @router.get("/collections")
    async def list_collections() -> list[str]:
        return await vector_store.list_collections()

    return router


def create_health_router(
    vector_store: VectorStoreProtocol,
    graph_store_enabled: bool,
    cache_enabled: bool,
    check_graph_store: callable | None = None,
    check_cache: callable | None = None,
) -> APIRouter:
    """Create health check routes."""
    router = APIRouter()

    @router.get("/health", response_model=HealthStatus)
    async def health_check() -> HealthStatus:
        vector_status = "disconnected"
        graph_status: str = "disabled" if not graph_store_enabled else "disconnected"
        cache_status: str = "disabled" if not cache_enabled else "disconnected"
        collections: list[str] = []

        try:
            if await vector_store.health_check():
                vector_status = "connected"
                collections = await vector_store.list_collections()
        except Exception as e:
            logger.error("vector_store_health_check_failed", error=str(e))

        if graph_store_enabled and check_graph_store:
            try:
                if await check_graph_store():
                    graph_status = "connected"
            except Exception as e:
                logger.error("graph_store_health_check_failed", error=str(e))

        if cache_enabled and check_cache:
            try:
                if await check_cache():
                    cache_status = "connected"
            except Exception as e:
                logger.error("cache_health_check_failed", error=str(e))

        status = "healthy" if vector_status == "connected" else "unhealthy"
        if vector_status == "connected" and (
            (graph_store_enabled and graph_status == "disconnected")
            or (cache_enabled and cache_status == "disconnected")
        ):
            status = "degraded"

        return HealthStatus(
            status=status,
            vector_store=vector_status,
            graph_store=graph_status,
            cache=cache_status,
            collections=collections,
        )

    return router
