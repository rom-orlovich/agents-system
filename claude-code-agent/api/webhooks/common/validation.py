"""Shared validation utilities for webhook responses."""

import subprocess
from pathlib import Path
import structlog

logger = structlog.get_logger()


def validate_response_format(result: str, format_type: str) -> tuple[bool, str]:
    """
    Validate response format using external script.
    
    Args:
        result: The response text to validate
        format_type: Type of format to validate (e.g., "pr_review", "jira", "slack")
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        script_path = project_root / "scripts" / "validate-response-format.sh"

        if not script_path.exists():
            logger.warning("response_format_validation_script_not_found", script_path=str(script_path))
            return True, ""

        input_text = f"{format_type}\n{result}"

        validation_result = subprocess.run(
            [str(script_path)],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=5,
            cwd=str(project_root)
        )

        if validation_result.returncode != 0:
            error_msg = validation_result.stderr.strip() or "Format validation failed"
            logger.warning("response_format_validation_failed", format_type=format_type, error=error_msg)
            return False, error_msg

        return True, ""
    except Exception as e:
        logger.error("response_format_validation_error", error=str(e), format_type=format_type)
        return True, ""
