from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import structlog
import httpx

from config import settings
from models import (
    QueryRequest,
    QueryResponse,
    CodeQueryRequest,
    TicketQueryRequest,
    DocsQueryRequest,
    GraphRelatedRequest,
    GraphRelatedResponse,
    HealthResponse,
    CollectionInfo,
)
from query_engine import HybridQueryEngine
from chroma_client import ChromaClientManager

logger = structlog.get_logger()

chroma_manager: ChromaClientManager | None = None
query_engine: HybridQueryEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global chroma_manager, query_engine
    logger.info("llamaindex_service_starting")

    chroma_manager = ChromaClientManager(settings.chromadb_url)
    await chroma_manager.initialize()

    query_engine = HybridQueryEngine(
        chroma_manager=chroma_manager,
        gkg_url=settings.gkg_url,
        embedding_model=settings.embedding_model,
    )

    logger.info("llamaindex_service_started")
    yield
    logger.info("llamaindex_service_stopping")


app = FastAPI(
    title="LlamaIndex Hybrid Query Service",
    description="Hybrid RAG service combining ChromaDB vectors with GKG graph",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    chromadb_status = "disconnected"
    gkg_status = "disconnected"
    collections: list[str] = []

    if chroma_manager:
        try:
            collections = await chroma_manager.list_collections()
            chromadb_status = "connected"
        except Exception as e:
            logger.error("chromadb_health_check_failed", error=str(e))

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.gkg_url}/health", timeout=5.0)
            if response.status_code == 200:
                gkg_status = "connected"
    except Exception as e:
        logger.error("gkg_health_check_failed", error=str(e))

    status = "healthy" if chromadb_status == "connected" else "unhealthy"
    return HealthResponse(
        status=status,
        chromadb=chromadb_status,
        gkg=gkg_status,
        collections=collections,
    )


@app.post("/query", response_model=QueryResponse)
async def hybrid_query(request: QueryRequest):
    if not query_engine:
        raise HTTPException(status_code=503, detail="Query engine not initialized")

    source_types = request.source_types or ["code", "jira", "confluence"]

    logger.info(
        "hybrid_query_started",
        query=request.query[:100],
        org_id=request.org_id,
        source_types=source_types,
    )

    results = await query_engine.query(
        query=request.query,
        org_id=request.org_id,
        source_types=source_types,
        top_k=request.top_k,
        include_metadata=request.include_metadata,
    )

    logger.info(
        "hybrid_query_completed",
        org_id=request.org_id,
        result_count=len(results),
    )

    return QueryResponse(
        results=results,
        query=request.query,
        total_results=len(results),
        source_types_queried=source_types,
    )


@app.post("/query/code", response_model=QueryResponse)
async def code_query(request: CodeQueryRequest):
    if not query_engine:
        raise HTTPException(status_code=503, detail="Query engine not initialized")

    logger.info(
        "code_query_started",
        query=request.query[:100],
        org_id=request.org_id,
    )

    results = await query_engine.query_code(
        query=request.query,
        org_id=request.org_id,
        filters=request.filters,
        top_k=request.top_k,
    )

    return QueryResponse(
        results=results,
        query=request.query,
        total_results=len(results),
        source_types_queried=["code"],
    )


@app.post("/query/tickets", response_model=QueryResponse)
async def ticket_query(request: TicketQueryRequest):
    if not query_engine:
        raise HTTPException(status_code=503, detail="Query engine not initialized")

    logger.info(
        "ticket_query_started",
        query=request.query[:100],
        org_id=request.org_id,
    )

    results = await query_engine.query_tickets(
        query=request.query,
        org_id=request.org_id,
        filters=request.filters,
        top_k=request.top_k,
    )

    return QueryResponse(
        results=results,
        query=request.query,
        total_results=len(results),
        source_types_queried=["jira"],
    )


@app.post("/query/docs", response_model=QueryResponse)
async def docs_query(request: DocsQueryRequest):
    if not query_engine:
        raise HTTPException(status_code=503, detail="Query engine not initialized")

    logger.info(
        "docs_query_started",
        query=request.query[:100],
        org_id=request.org_id,
    )

    results = await query_engine.query_docs(
        query=request.query,
        org_id=request.org_id,
        filters=request.filters,
        top_k=request.top_k,
    )

    return QueryResponse(
        results=results,
        query=request.query,
        total_results=len(results),
        source_types_queried=["confluence"],
    )


@app.post("/graph/related", response_model=GraphRelatedResponse)
async def graph_related(request: GraphRelatedRequest):
    if not query_engine:
        raise HTTPException(status_code=503, detail="Query engine not initialized")

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


@app.get("/collections", response_model=list[CollectionInfo])
async def list_collections():
    if not chroma_manager:
        raise HTTPException(status_code=503, detail="ChromaDB not initialized")

    collections = await chroma_manager.get_collection_info()
    return collections


@app.post("/index/trigger")
async def trigger_indexing(org_id: str, source_type: str | None = None):
    logger.info(
        "index_trigger_requested",
        org_id=org_id,
        source_type=source_type,
    )
    return {"status": "queued", "org_id": org_id, "source_type": source_type}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
