from collections import defaultdict, deque
import time

from fastapi import HTTPException, Request


_requests: dict[str, deque[float]] = defaultdict(deque)


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def _check_bucket(key: str, limit: int, window_seconds: int) -> None:
    now = time.monotonic()
    bucket = _requests[key]

    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
        )

    bucket.append(now)


async def check_rate_limit(
    request: Request,
    endpoint: str,
    limit: int,
    window_seconds: int,
    user_id: int | None = None,
) -> None:
    client_ip = _get_client_ip(request)

    ip_key = f"ip:{client_ip}:{endpoint}"
    _check_bucket(ip_key, limit, window_seconds)

    if user_id is not None:
        user_key = f"user:{user_id}:{endpoint}"
        _check_bucket(user_key, limit, window_seconds)
