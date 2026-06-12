import time

import redis
from fastapi import HTTPException

from app.config import settings


class RedisRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds

    def check(self, client: redis.Redis, user_id: str) -> dict:
        now = time.time()
        key = f"rate:{user_id}"
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, now - self.window_seconds)
        pipe.zcard(key)
        _, current = pipe.execute()

        if current >= self.limit:
            oldest = client.zrange(key, 0, 0, withscores=True)
            retry_after = self.window_seconds
            if oldest:
                retry_after = max(1, int(oldest[0][1] + self.window_seconds - now) + 1)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": self.limit,
                    "window_seconds": self.window_seconds,
                    "retry_after_seconds": retry_after,
                },
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(retry_after),
                },
            )

        member = f"{now}:{time.perf_counter_ns()}"
        pipe = client.pipeline()
        pipe.zadd(key, {member: now})
        pipe.expire(key, self.window_seconds)
        pipe.execute()

        return {
            "limit": self.limit,
            "remaining": self.limit - current - 1,
            "window_seconds": self.window_seconds,
        }


rate_limiter = RedisRateLimiter(settings.rate_limit_per_minute)
