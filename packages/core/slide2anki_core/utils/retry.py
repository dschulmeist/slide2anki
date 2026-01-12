"""Retry utilities for robust API calls."""

import asyncio
from typing import Any, Callable, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Default retry configuration
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MIN_WAIT = 1  # seconds
DEFAULT_MAX_WAIT = 30  # seconds

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


def get_async_retry(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
) -> AsyncRetrying:
    """Create an async retry context manager.

    Args:
        max_attempts: Maximum number of attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds

    Returns:
        AsyncRetrying context manager
    """
    return AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True,
    )


async def with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    operation_name: str = "operation",
    **kwargs: Any,
) -> Any:
    """Execute an async function with retry logic.

    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        max_attempts: Maximum number of attempts
        operation_name: Name for logging purposes
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function

    Raises:
        The last exception if all retries fail
    """
    attempt = 0
    last_exception = None

    async for attempt_ctx in get_async_retry(max_attempts=max_attempts):
        with attempt_ctx:
            attempt += 1
            if attempt > 1:
                logger.info(f"Retrying {operation_name} (attempt {attempt}/{max_attempts})")
            try:
                return await func(*args, **kwargs)
            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{max_attempts}): {e}"
                )
                raise  # Let tenacity handle the retry

    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    raise RuntimeError(f"{operation_name} failed after {max_attempts} attempts")
