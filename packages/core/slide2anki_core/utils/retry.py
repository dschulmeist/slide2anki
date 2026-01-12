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

# Global semaphore for rate limiting concurrent API calls
# This prevents overwhelming the API with too many parallel requests
_api_semaphore: asyncio.Semaphore | None = None
_semaphore_lock = asyncio.Lock()
DEFAULT_MAX_CONCURRENT_CALLS = 5


async def get_api_semaphore(max_concurrent: int = DEFAULT_MAX_CONCURRENT_CALLS) -> asyncio.Semaphore:
    """Get or create the global API rate limiting semaphore.

    Args:
        max_concurrent: Maximum concurrent API calls allowed

    Returns:
        Shared semaphore instance
    """
    global _api_semaphore
    if _api_semaphore is None:
        async with _semaphore_lock:
            if _api_semaphore is None:
                _api_semaphore = asyncio.Semaphore(max_concurrent)
                logger.info(f"Initialized API rate limiter: max {max_concurrent} concurrent calls")
    return _api_semaphore


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RateLimitError,
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


def _format_exception(e: Exception) -> str:
    """Format exception for logging, handling nested/empty exceptions."""
    # Get the exception message
    msg = str(e).strip()

    # If empty, try to get more info
    if not msg:
        msg = type(e).__name__

    # Check for nested exceptions (common in API clients)
    if hasattr(e, "__cause__") and e.__cause__:
        cause_msg = str(e.__cause__).strip()
        if cause_msg:
            msg = f"{msg} (caused by: {cause_msg})"

    # Check for HTTP status codes
    if hasattr(e, "status_code"):
        msg = f"HTTP {e.status_code}: {msg}"
    elif hasattr(e, "code"):
        msg = f"Error {e.code}: {msg}"

    return msg or "Unknown error"


async def with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    operation_name: str = "operation",
    use_rate_limit: bool = True,
    **kwargs: Any,
) -> Any:
    """Execute an async function with retry logic and optional rate limiting.

    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        max_attempts: Maximum number of attempts
        operation_name: Name for logging purposes
        use_rate_limit: Whether to use the global rate limiter
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function

    Raises:
        The last exception if all retries fail
    """
    attempt = 0
    last_exception = None

    # Get semaphore for rate limiting
    semaphore = await get_api_semaphore() if use_rate_limit else None

    async def _execute() -> Any:
        if semaphore:
            async with semaphore:
                return await func(*args, **kwargs)
        return await func(*args, **kwargs)

    async for attempt_ctx in get_async_retry(max_attempts=max_attempts):
        with attempt_ctx:
            attempt += 1
            if attempt > 1:
                logger.info(f"Retrying {operation_name} (attempt {attempt}/{max_attempts})")
            try:
                return await _execute()
            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                error_msg = _format_exception(e)
                logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{max_attempts}): {error_msg}"
                )
                raise  # Let tenacity handle the retry
            except Exception as e:
                # Log non-retryable errors with full details
                error_msg = _format_exception(e)
                logger.error(
                    f"{operation_name} failed with non-retryable error: {error_msg}"
                )
                raise

    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    raise RuntimeError(f"{operation_name} failed after {max_attempts} attempts")
