# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

T = TypeVar("T")

BASE_DELAY_S = 0.5


class RetryableError(Exception):
    pass


def is_retryable_status(status: int) -> bool:
    return status == 429 or status >= 500


def delay_for(attempt: int) -> float:
    return float(BASE_DELAY_S * 2**attempt * random.uniform(0.8, 1.2))


async def with_retries(
    call: Callable[[], Awaitable[T]],
    max_retries: int,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    attempt = 0
    while True:
        try:
            return await call()
        except (RetryableError, httpx.TimeoutException, httpx.TransportError):
            if attempt >= max_retries:
                raise
            await sleep(delay_for(attempt))
            attempt += 1
