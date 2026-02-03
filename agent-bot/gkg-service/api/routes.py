from fastapi import APIRouter, HTTPException
import structlog

from core.models import (
    DependencyRequest,
    DependencyResult,
    UsageRequest,
    UsageResult,
    CallGraphRequest,
    CallGraphResult,
    HierarchyRequest,
    HierarchyResult,
    RelatedRequest,
    RelatedEntitiesResult,
    BatchRelatedRequest,
    IndexRequest,
    HealthStatus,
)
from core.graph_analyzer import GraphAnalyzerService

logger = structlog.get_logger()


def create_analysis_router(service: GraphAnalyzerService) -> APIRouter:
    """Create analysis routes with injected dependencies."""
    router = APIRouter()

    @router.post("/analyze/dependencies", response_model=DependencyResult)
    async def analyze_dependencies(request: DependencyRequest) -> DependencyResult:
        logger.info(
            "analyzing_dependencies",
            file_path=request.file_path,
            org_id=request.org_id,
            repo=request.repo,
        )

        return await service.query_dependencies(
            org_id=request.org_id,
            repo=request.repo,
            file_path=request.file_path,
            depth=request.depth,
        )

    @router.post("/query/usages")
    async def find_usages(request: UsageRequest) -> list[UsageResult]:
        logger.info(
            "finding_usages",
            symbol=request.symbol,
            org_id=request.org_id,
        )

        return await service.find_usages(
            org_id=request.org_id,
            symbol=request.symbol,
            repo=request.repo,
        )

    @router.post("/graph/calls", response_model=CallGraphResult)
    async def get_call_graph(request: CallGraphRequest) -> CallGraphResult:
        logger.info(
            "getting_call_graph",
            function_name=request.function_name,
            org_id=request.org_id,
        )

        return await service.get_call_graph(
            org_id=request.org_id,
            repo=request.repo,
            function_name=request.function_name,
            direction=request.direction,
            depth=request.depth,
        )

    @router.post("/graph/hierarchy", response_model=HierarchyResult)
    async def get_class_hierarchy(request: HierarchyRequest) -> HierarchyResult:
        logger.info(
            "getting_class_hierarchy",
            class_name=request.class_name,
            org_id=request.org_id,
        )

        return await service.get_class_hierarchy(
            org_id=request.org_id,
            class_name=request.class_name,
            repo=request.repo,
        )

    @router.post("/graph/related", response_model=RelatedEntitiesResult)
    async def get_related(request: RelatedRequest) -> RelatedEntitiesResult:
        logger.info(
            "getting_related_entities",
            entity=request.entity,
            entity_type=request.entity_type,
            org_id=request.org_id,
        )

        return await service.get_related_entities(
            org_id=request.org_id,
            entity=request.entity,
            entity_type=request.entity_type,
            relationship=request.relationship,
        )

    @router.post("/graph/batch-related")
    async def batch_related(request: BatchRelatedRequest) -> dict:
        logger.info(
            "batch_related_entities",
            entity_count=len(request.entities),
            org_id=request.org_id,
        )

        return await service.batch_related_entities(
            org_id=request.org_id,
            entities=request.entities,
            depth=request.depth,
        )

    @router.post("/index")
    async def index_repo(request: IndexRequest) -> dict:
        logger.info(
            "indexing_repo",
            repo_path=request.repo_path,
            org_id=request.org_id,
        )

        success = await service.index_repo(
            org_id=request.org_id,
            repo_path=request.repo_path,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Indexing failed")

        return {"status": "indexed", "org_id": request.org_id}

    return router


def create_health_router(service: GraphAnalyzerService) -> APIRouter:
    """Create health check routes."""
    router = APIRouter()

    @router.get("/health", response_model=HealthStatus)
    async def health_check() -> HealthStatus:
        is_healthy = await service.is_healthy()
        indexed_count = await service.get_indexed_count()

        return HealthStatus(
            status="healthy" if is_healthy else "unhealthy",
            analyzer="available" if is_healthy else "unavailable",
            indexed_repos=indexed_count,
        )

    return router
