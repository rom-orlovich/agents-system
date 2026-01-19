import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional

class StructuredLogger:
    """A logger that can output both human-readable and JSON logs."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log(self, level: int, message: str, task_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Log a message with optional task_id and structured data."""
        extra = {"task_id": task_id} if task_id else {}
        if data:
            extra.update(data)
            
        log_msg = message
        if extra:
            log_msg = f"{message} | {json.dumps(extra)}"
            
        self.logger.log(level, log_msg)

    def info(self, message: str, task_id: Optional[str] = None, **kwargs):
        self.log(logging.INFO, message, task_id, kwargs)

    def error(self, message: str, task_id: Optional[str] = None, **kwargs):
        self.log(logging.ERROR, message, task_id, kwargs)

    def warning(self, message: str, task_id: Optional[str] = None, **kwargs):
        self.log(logging.WARNING, message, task_id, kwargs)

    def debug(self, message: str, task_id: Optional[str] = None, **kwargs):
        self.log(logging.DEBUG, message, task_id, kwargs)

def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
