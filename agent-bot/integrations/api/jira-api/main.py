"""Jira API service entry point."""

from api.server import create_app
from middleware.auth import AuthMiddleware
from middleware.rate_limiter import RateLimiter
from middleware.error_handler import ErrorHandler
from config.settings import get_settings

settings = get_settings()
app = create_app()

app.add_middleware(
    ErrorHandler,
)

app.add_middleware(
    RateLimiter,
    redis_url=str(settings.redis_url),
    rate_limit=settings.rate_limit_per_second,
)

app.add_middleware(
    AuthMiddleware,
    api_key=settings.jira_api_key.get_secret_value(),
)
