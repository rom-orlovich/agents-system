from fastapi import FastAPI
from contextlib import asynccontextmanager
import structlog

from factory import ServiceContainer, ServiceConfig
from api.routes import create_query_router, create_health_router

logger = structlog.get_logger()

container: ServiceContainer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global container
    logger.info("llamaindex_service_starting")

    config = ServiceConfig()
    container = ServiceContainer(config)
    await container.initialize()

    query_router = create_query_router(
        query_engine=container.query_engine,
        vector_store=container.vector_store,
    )

    health_router = create_health_router(
        vector_store=container.vector_store,
        graph_store_enabled=config.enable_gkg,
        cache_enabled=config.enable_cache,
        check_graph_store=(
            container.graph_store.health_check if container.graph_store else None
        ),
        check_cache=container.cache.health_check if container.cache else None,
    )

    app.include_router(query_router)
    app.include_router(health_router)

    logger.info("llamaindex_service_started")
    yield

    await container.shutdown()
    logger.info("llamaindex_service_stopped")


app = FastAPI(
    title="LlamaIndex Hybrid Query Service",
    description="Modular hybrid RAG service combining vector and graph stores",
    version="2.0.0",
    lifespan=lifespan,
)


if __name__ == "__main__":
    import uvicorn

    config = ServiceConfig()
    uvicorn.run(app, host=config.host, port=config.port)
