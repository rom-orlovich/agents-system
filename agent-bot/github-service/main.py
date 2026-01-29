from fastapi import FastAPI
import structlog
from api.routes import router

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

app = FastAPI(
    title="GitHub Service",
    description="GitHub API integration microservice",
    version="1.0.0",
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "github-service"}
