"""Logging utilities."""

import logging
import os
import sys
from functools import wraps
from typing import Any, Callable, TypeVar

# Configure root logger for the package
_LOG_LEVEL = os.environ.get("SLIDE2ANKI_LOG_LEVEL", "INFO").upper()
_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

F = TypeVar("F", bound=Callable[..., Any])


def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """Get a configured logger.

    Args:
        name: Logger name (typically __name__)
        level: Optional log level override

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)

    if level is not None:
        logger.setLevel(level)
    elif logger.level == logging.NOTSET:
        logger.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))

    return logger


def log_exceptions(logger: logging.Logger) -> Callable[[F], F]:
    """Decorator to log exceptions from a function.

    Args:
        logger: Logger to use for exception logging

    Returns:
        Decorated function that logs exceptions before re-raising
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {e}")
                raise

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {e}")
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
