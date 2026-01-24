"""CLI access testing utilities."""

import subprocess
import structlog

logger = structlog.get_logger()


async def test_cli_access() -> bool:
    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "json", "--dangerously-skip-permissions", "--", "test"],
            capture_output=True,
            timeout=10,
            text=True
        )
        
        if result.returncode != 0:
            error_text = ""
            if result.stderr:
                error_text += result.stderr.strip()
            if result.stdout:
                if error_text:
                    error_text += "\n" + result.stdout.strip()
                else:
                    error_text = result.stdout.strip()
            
            error_msg = error_text if error_text else "Unknown error"
            logger.warning("CLI test failed", returncode=result.returncode, error=error_msg)
            
            error_lower = error_msg.lower()
            if "invalid api key" in error_lower or "please run /login" in error_lower or "authentication" in error_lower:
                logger.warning("Authentication error detected in CLI test")
                return False
            
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        logger.warning("CLI access test timed out")
        return False
    except FileNotFoundError:
        logger.warning("Claude CLI not found")
        return False
    except Exception as e:
        logger.warning("CLI access test failed", error=str(e))
        return False
