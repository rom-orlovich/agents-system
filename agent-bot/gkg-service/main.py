from fastapi import FastAPI
from contextlib import asynccontextmanager
import structlog

from factory import ServiceContainer, ServiceConfig
from api.routes import create_analysis_router, create_health_router

logger = structlog.get_logger()

container: ServiceContainer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global container
    logger.info("gkg_service_starting")

    config = ServiceConfig()
    container = ServiceContainer(config)
    await container.initialize()

    analysis_router = create_analysis_router(service=container.service)
    health_router = create_health_router(service=container.service)

    app.include_router(analysis_router)
    app.include_router(health_router)

    logger.info("gkg_service_started")
    yield

    await container.shutdown()
    logger.info("gkg_service_stopped")


app = FastAPI(
    title="GKG Service",
    description="Modular GitLab Knowledge Graph service for code entity relationships",
    version="2.0.0",
    lifespan=lifespan,
)


if __name__ == "__main__":
    import uvicorn

    config = ServiceConfig()
    uvicorn.run(app, host=config.host, port=config.port)
