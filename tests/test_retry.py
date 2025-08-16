
import pytest

from vaayu.utils import async_retry


@pytest.mark.asyncio
async def test_async_retry_succeeds_after_failures():
    attempts = {"n": 0}

    async def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("fail")
        return "ok"

    result = await async_retry(flaky, retries=5, base_delay=0.01)
    assert result == "ok"
    assert attempts["n"] == 3
