"""Shared utilities for AI Agent System.

DEPRECATED: This module provides backward compatibility.
New code should import directly from config, models, types, clients, or utils.
"""

import sys
from pathlib import Path

# Add project root to path for new module imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Re-export from new locations for backward compatibility

# Config
from config.settings import Settings, settings
from config.constants import *

# Models
from models import *

# Types/Enums
from types.enums import *

# Clients
from clients.redis_queue import RedisQueue
from clients.database import Database

# Utils
from utils.claude import run_claude_streaming, run_claude_json, extract_pr_url
from utils.token import OAuthTokenManager as TokenManager
from utils.logging import get_logger
from utils.metrics import *

# Legacy imports (these are still in shared/ and haven't moved)
try:
    from .github_client import GitHubClient
except ImportError:
    pass

try:
    from .slack_client import SlackClient
except ImportError:
    pass

try:
    from .git_utils import GitUtils
except ImportError:
    pass

try:
    from .database import save_task_to_db
except ImportError:
    pass

__version__ = "2.0.0"
__all__ = [
    # Config
    "Settings",
    "settings",
    # Models (all exported from models/)
    # Types (all exported from types/)
    # Clients
    "RedisQueue",
    "Database",
    # Utils
    "run_claude_streaming",
    "run_claude_json",
    "extract_pr_url",
    "TokenManager",
    "get_logger",
    # Legacy
    "GitHubClient",
    "SlackClient",
    "GitUtils",
    "save_task_to_db",
]
