"""
Shared Utilities
================
Common utility functions.
"""

import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def validate_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Validate a webhook signature (HMAC-SHA256)."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to URL-friendly slug."""
    # Remove special characters and convert spaces to hyphens
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:max_length]


def format_branch_name(ticket_id: str, summary: str) -> str:
    """Format a branch name from ticket ID and summary."""
    slug = slugify(summary, max_length=50)
    return f"feature/{ticket_id.lower()}-{slug}"


def load_json_file(path: Path) -> dict:
    """Load JSON from a file."""
    with open(path) as f:
        return json.load(f)


def save_json_file(path: Path, data: Any):
    """Save data as JSON to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def extract_json_from_text(text: str) -> dict | None:
    """Extract JSON object from text (e.g., Claude response)."""
    # Try to find JSON block
    json_match = re.search(r"```json?\s*([\s\S]*?)\s*```", text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return None


def setup_logging(level: str = "INFO"):
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
