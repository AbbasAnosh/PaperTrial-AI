"""
Logging configuration module.

This module sets up structured logging for the application with different
handlers for different environments and log levels.
"""

import logging
import logging.handlers
import json
import sys
from datetime import datetime
from typing import Any, Dict
from pathlib import Path

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        return json.dumps(log_data)

def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    log_format: str = "json",
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: The minimum log level to record
        log_file: Path to log file (if None, logs to stdout)
        log_format: Log format ("json" or "text")
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Create formatter
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if log file is specified
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set up specific loggers
    loggers = {
        "app": logging.getLogger("app"),
        "app.api": logging.getLogger("app.api"),
        "app.db": logging.getLogger("app.db"),
        "app.auth": logging.getLogger("app.auth"),
        "app.forms": logging.getLogger("app.forms"),
    }

    for logger in loggers.values():
        logger.setLevel(getattr(logging, log_level.upper()))

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: The name of the logger
        
    Returns:
        logging.Logger: The logger instance
    """
    return logging.getLogger(name)

class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter that adds context to log messages."""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process the log message and kwargs to add context."""
        extra = kwargs.get("extra", {})
        if self.extra:
            extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs

def get_context_logger(name: str, **context) -> LoggerAdapter:
    """
    Get a logger adapter with context.
    
    Args:
        name: The name of the logger
        **context: Additional context to add to log messages
        
    Returns:
        LoggerAdapter: The logger adapter with context
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context) 