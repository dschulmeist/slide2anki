"""Tests for retry utilities."""

import pytest

from slide2anki_core.utils.retry import with_retry


class TestRetry:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self) -> None:
        """Test that successful calls don't retry."""
        call_count = 0

        async def success() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await with_retry(success, operation_name="test")

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self) -> None:
        """Test that ConnectionError triggers retry."""
        call_count = 0

        async def fail_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network failed")
            return "success"

        result = await with_retry(
            fail_then_succeed,
            max_attempts=3,
            operation_name="test",
        )

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        """Test that TimeoutError triggers retry."""
        call_count = 0

        async def timeout_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timed out")
            return "success"

        result = await with_retry(
            timeout_then_succeed,
            max_attempts=3,
            operation_name="test",
        )

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self) -> None:
        """Test that exception is raised after max retries."""
        call_count = 0

        async def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await with_retry(
                always_fail,
                max_attempts=3,
                operation_name="test",
            )

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error_not_retried(self) -> None:
        """Test that non-retryable errors are not retried."""
        call_count = 0

        async def value_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid value")

        with pytest.raises(ValueError):
            await with_retry(
                value_error,
                max_attempts=3,
                operation_name="test",
            )

        # Should only be called once since ValueError is not retryable
        assert call_count == 1
