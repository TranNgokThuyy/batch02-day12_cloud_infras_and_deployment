"""Production-ready AI agent for Day 12.

The application is intentionally stateless: conversation history, rate-limit
windows, and monthly budget usage all live in Redis so multiple agent
instances can serve the same users.
"""
import json
import logging
import re
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import estimate_cost_usd, monthly_cost_guard
from app.rate_limiter import rate_limiter
from utils.mock_llm import ask as llm_ask


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    handlers=[handler],
    force=True,
)
logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

START_TIME = time.time()
MAX_HISTORY_MESSAGES = 12
_is_ready = False
_request_count = 0
_error_count = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info("startup")
    try:
        redis_client.ping()
        _is_ready = True
        logger.info("ready")
    except redis.RedisError as exc:
        _is_ready = False
        logger.error("redis_not_ready: %s", exc)
    yield
    _is_ready = False
    redis_client.close()
    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
    except Exception:
        _error_count += 1
        logger.exception("request_failed")
        raise

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }
        )
    )
    return response


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    history_messages: int
    cost_usd: float
    timestamp: str


def _history_key(user_id: str) -> str:
    return f"history:{user_id}"


def load_history(user_id: str) -> list[dict[str, str]]:
    raw_messages = redis_client.lrange(_history_key(user_id), 0, -1)
    history: list[dict[str, str]] = []
    for raw in raw_messages:
        try:
            history.append(json.loads(raw))
        except json.JSONDecodeError:
            logger.warning("invalid_history_record user_id=%s", user_id)
    return history


def append_history(user_id: str, role: str, content: str) -> None:
    key = _history_key(user_id)
    redis_client.rpush(
        key,
        json.dumps(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )
    redis_client.ltrim(key, -MAX_HISTORY_MESSAGES, -1)
    redis_client.expire(key, settings.history_ttl_seconds)


def build_answer(question: str, history: list[dict[str, str]]) -> str:
    question_lower = question.lower()
    if "what is my name" in question_lower or "what's my name" in question_lower:
        for message in reversed(history):
            if message.get("role") != "user":
                continue
            match = re.search(r"\bmy name is\s+([A-Za-z][A-Za-z '-]{0,60})", message["content"], re.I)
            if match:
                name = match.group(1).strip(" .,!?:;")
                return f"Your name is {name}."
    return llm_ask(question)


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "metrics": "GET /metrics (requires X-API-Key)",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _api_key: str = Depends(verify_api_key),
):
    user_id = body.user_id.strip()
    rate_limiter.check(redis_client, user_id)

    history = load_history(user_id)
    estimated_input_tokens = len(body.question.split()) * 2
    monthly_cost_guard.check(redis_client, user_id, estimate_cost_usd(estimated_input_tokens, 0))

    answer = build_answer(body.question, history)
    estimated_output_tokens = len(answer.split()) * 2
    request_cost = estimate_cost_usd(estimated_input_tokens, estimated_output_tokens)
    monthly_cost_guard.record(redis_client, user_id, request_cost)

    append_history(user_id, "user", body.question)
    append_history(user_id, "assistant", answer)

    logger.info(
        json.dumps(
            {
                "event": "agent_call",
                "user_id": user_id,
                "client": str(request.client.host) if request.client else "unknown",
                "cost_usd": request_cost,
            }
        )
    )

    return AskResponse(
        user_id=user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        history_messages=len(history) + 2,
        cost_usd=round(request_cost, 6),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health", tags=["Operations"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    try:
        redis_client.ping()
    except redis.RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "not ready", "dependency": "redis", "error": str(exc)},
        ) from exc
    if not _is_ready:
        raise HTTPException(status_code=503, detail={"status": "not ready"})
    return {"status": "ready", "redis": "ok"}


@app.get("/metrics", tags=["Operations"])
def metrics(_api_key: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "monthly_budget_usd": settings.monthly_budget_usd,
    }


def _handle_signal(signum, _frame):
    global _is_ready
    _is_ready = False
    logger.info(json.dumps({"event": "signal_received", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    logger.info("starting %s on %s:%s", settings.app_name, settings.host, settings.port)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
