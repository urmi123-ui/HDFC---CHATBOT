from __future__ import annotations

import os
import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, client_ip: str) -> None:
        now = time.time()
        window_start = now - self.window_seconds
        recent = [timestamp for timestamp in self._hits[client_ip] if timestamp >= window_start]
        if len(recent) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again shortly.",
            )
        recent.append(now)
        self._hits[client_ip] = recent


_default_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _default_limiter
    if _default_limiter is None:
        max_requests = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        _default_limiter = RateLimiter(max_requests=max_requests)
    return _default_limiter


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
