from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import structlog

from config import settings
from models import (
    DependencyRequest,
    DependencyResponse,
    UsageRequest,
    UsageResponse,
    CallGraphRequest,
    CallGraphResponse,
    HierarchyRequest,
    HierarchyResponse,
    RelatedRequest,
    RelatedResponse,
    BatchRelatedRequest,
    IndexRequest,
    HealthResponse,
)
from gkg_wrapper import GKGWrapper

logger = structlog.get_logger()

gkg: GKGWrapper | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global gkg
    logger.info("gkg_service_starting")

    gkg = GKGWrapper()
    is_available = await gkg.is_available()

    if is_available:
        logger.info("gkg_binary_available")
    else:
        logger.warning("gkg_binary_not_found", path=settings.gkg_binary)

    logger.info("gkg_service_started")
    yield
    logger.info("gkg_service_stopping")


app = FastAPI(
    title="GKG Service",
    description="GitLab Knowledge Graph service for code entity relationships",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    if not gkg:
        return HealthResponse(
            status="unhealthy",
            gkg_binary="missing",
            indexed_repos=0,
        )

    is_available = await gkg.is_available()
    indexed_count = await gkg.get_indexed_repos_count()

    return HealthResponse(
        status="healthy" if is_available else "unhealthy",
        gkg_binary="available" if is_available else "missing",
        indexed_repos=indexed_count,
    )


@app.post("/analyze/dependencies", response_model=DependencyResponse)
async def analyze_dependencies(request: DependencyRequest):
    if not gkg:
        raise HTTPException(status_code=503, detail="GKG service not initialized")

    logger.info(
        "analyzing_dependencies",
        file_path=request.file_path,
        org_id=request.org_id,
        repo=request.repo,
    )

    result = await gkg.query_dependencies(
        org_id=request.org_id,
        repo=request.repo,
        file_path=request.file_path,
        depth=request.depth,
    )

    return DependencyResponse(
        file_path=request.file_path,
        repo=request.repo,
        dependencies=result["dependencies"],
        formatted_output=result["formatted_output"],
    )


@app.post("/query/usages", response_model=UsageResponse)
async def find_usages(request: UsageRequest):
    if not gkg:
        raise HTTPException(status_code=503, detail="GKG service not initialized")

    logger.info(
        "finding_usages",
        symbol=request.symbol,
        org_id=request.org_id,
    )

    usages = await gkg.find_usages(
        org_id=request.org_id,
        symbol=request.symbol,
        repo=request.repo,
    )

    return UsageResponse(
        symbol=request.symbol,
        usages=usages,
    )


@app.post("/graph/calls", response_model=CallGraphResponse)
async def get_call_graph(request: CallGraphRequest):
    if not gkg:
        raise HTTPException(status_code=503, detail="GKG service not initialized")

    logger.info(
        "getting_call_graph",
        function_name=request.function_name,
        org_id=request.org_id,
    )

    result = await gkg.get_call_graph(
        org_id=request.org_id,
        repo=request.repo,
        function_name=request.function_name,
        direction=request.direction,
        depth=request.depth,
    )

    return CallGraphResponse(
        function_name=request.function_name,
        callers=result["callers"],
        callees=result["callees"],
        formatted_graph=result["formatted_graph"],
    )


@app.post("/graph/hierarchy", response_model=HierarchyResponse)
async def get_class_hierarchy(request: HierarchyRequest):
    if not gkg:
        raise HTTPException(status_code=503, detail="GKG service not initialized")

    logger.info(
        "getting_class_hierarchy",
        class_name=request.class_name,
        org_id=request.org_id,
    )

    result = await gkg.get_class_hierarchy(
        org_id=request.org_id,
        class_name=request.class_name,
        repo=request.repo,
    )

    return HierarchyResponse(
        class_name=request.class_name,
        parents=result["parents"],
        children=result["children"],
        formatted_hierarchy=result["formatted_hierarchy"],
    )


@app.post("/graph/related", response_model=RelatedResponse)
async def get_related(request: RelatedRequest):
    if not gkg:
        raise HTTPException(status_code=503, detail="GKG service not initialized")

    logger.info(
        "getting_related_entities",
        entity=request.entity,
        entity_type=request.entity_type,
        org_id=request.org_id,
    )

    relationships = await gkg.get_related_entities(
        org_id=request.org_id,
        entity=request.entity,
        entity_type=request.entity_type,
        relationship=request.relationship,
    )

    return RelatedResponse(
        entity=request.entity,
        entity_type=request.entity_type,
        relationships=relationships,
    )


@app.post("/graph/batch-related")
async def batch_related(request: BatchRelatedRequest):
    if not gkg:
        raise HTTPException(status_code=503, detail="GKG service not initialized")

    logger.info(
        "batch_related_entities",
        entity_count=len(request.entities),
        org_id=request.org_id,
    )

    results = await gkg.batch_related_entities(
        org_id=request.org_id,
        entities=request.entities,
        depth=request.depth,
    )

    return results


@app.post("/index")
async def index_repo(request: IndexRequest):
    if not gkg:
        raise HTTPException(status_code=503, detail="GKG service not initialized")

    logger.info(
        "indexing_repo",
        repo_path=request.repo_path,
        org_id=request.org_id,
    )

    result = await gkg.index_repo(
        org_id=request.org_id,
        repo_path=request.repo_path,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Indexing failed"))

    return {"status": "indexed", "org_id": request.org_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
