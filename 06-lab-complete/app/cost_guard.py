from datetime import datetime, timezone

import redis
from fastapi import HTTPException

from app.config import settings


PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1000 * PRICE_PER_1K_INPUT_TOKENS
        + output_tokens / 1000 * PRICE_PER_1K_OUTPUT_TOKENS
    )


class MonthlyCostGuard:
    def __init__(self, monthly_budget_usd: float):
        self.monthly_budget_usd = monthly_budget_usd

    def _key(self, user_id: str) -> str:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        return f"budget:{user_id}:{month}"

    def check(self, client: redis.Redis, user_id: str, estimated_cost_usd: float) -> None:
        key = self._key(user_id)
        current = float(client.get(key) or 0)
        if current + estimated_cost_usd > self.monthly_budget_usd:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Monthly budget exceeded",
                    "used_usd": round(current, 6),
                    "estimated_request_usd": round(estimated_cost_usd, 6),
                    "budget_usd": self.monthly_budget_usd,
                },
            )

    def record(self, client: redis.Redis, user_id: str, cost_usd: float) -> float:
        key = self._key(user_id)
        total = float(client.incrbyfloat(key, cost_usd))
        client.expire(key, 32 * 24 * 60 * 60)
        return total


monthly_cost_guard = MonthlyCostGuard(settings.monthly_budget_usd)
