from .agents import router as agents_router
from .tasks import router as tasks_router
from .monitoring import router as monitoring_router
from .metrics import router as metrics_router
from .registry import router as registry_router
from .analytics import router as analytics_router

__all__ = [
    "agents_router",
    "tasks_router",
    "monitoring_router",
    "metrics_router",
    "registry_router",
    "analytics_router",
]
